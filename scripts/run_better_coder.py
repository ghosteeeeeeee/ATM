#!/usr/bin/env python3
"""
run_better_coder.py — Better Coder Parallel Dispatcher
Runs every 30 min via hermes-pipeline cron (or standalone).
Reads open tasks from brain/TASKS.md and executes via ParallelDispatcher.
"""
import sys
import os
import asyncio
import re
from datetime import datetime

# Add the MCP server directory to path
sys.path.insert(0, '/root/.hermes/mcp/hermes-coding-mcp')

from dispatcher.dispatcher import ParallelDispatcher

TASKS_FILE = '/root/.hermes/brain/TASKS.md'
LOG_FILE = '/root/.hermes/logs/better-coder.log'
LOCK = '/tmp/hermes-better-coder.lock'


def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def acquire_lock():
    """Acquire a file lock to prevent concurrent runs."""
    try:
        lock_fd = open(LOCK, 'w')
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        return lock_fd
    except (IOError, OSError):
        return None


def release_lock(lock_fd):
    """Release the file lock."""
    try:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        lock_fd.close()
        os.unlink(LOCK)
    except Exception:
        pass


def extract_open_tasks(tasks_file):
    """Extract open tasks from TASKS.md."""
    try:
        with open(tasks_file, 'r') as f:
            content = f.read()
    except Exception as e:
        log(f'Could not read {tasks_file}: {e}')
        return []

    tasks = []
    # Match lines like: ### [ ] Task description
    # Or: - [ ] Task description  
    pattern = re.compile(r'^#{1,3}\s+\[\s+\]|^-\s+\[\s+\]\s+(.+)', re.MULTILINE)
    
    for match in pattern.finditer(content):
        task = match.group(1) if match.group(1) else content[match.start():match.end()]
        # Clean up the task text
        task = re.sub(r'^#{1,3}\s+\[\s+\]\s+', '', task).strip()
        if task and len(task) > 10:  # Skip short/empty tasks
            tasks.append(task)

    return tasks[:20]  # Limit to 20 tasks max


async def run_better_coder():
    """Run the Better Coder dispatcher."""
    log('=== Better Coder Dispatcher Starting ===')
    
    tasks = extract_open_tasks(TASKS_FILE)
    if not tasks:
        log('No open tasks found in TASKS.md')
        return
    
    log(f'Found {len(tasks)} open tasks')
    
    async def tool_executor(tool_name, params):
        """Execute MCP tools directly."""
        from server import read_file, write_file, search_code, execute_command
        
        tool_map = {
            'read_file': read_file,
            'write_file': write_file,
            'search_code': search_code,
            'execute_command': execute_command,
        }
        
        if tool_name in tool_map:
            result = await tool_map[tool_name](**params)
            return result
        return '{"isError": true, "error": "unknown_tool"}'
    
    dispatcher = ParallelDispatcher(
        tasks=tasks,
        tool_executor=tool_executor,
        max_concurrent=2
    )
    
    result = await dispatcher.run()
    
    log(f'Dispatcher completed: {result.completed}/{result.total_tasks} tasks')
    log(f'  Completed: {result.completed}, Escalated: {result.escalated}, Failed: {result.failed}')
    log(f'  Duration: {result.total_duration_seconds:.2f}s')
    log(f'  Conflicts: {len(result.conflicts)}')
    
    return result


def main():
    lock_fd = acquire_lock()
    if lock_fd is None:
        log('Another instance is running — skipping this cycle')
        sys.exit(0)
    
    try:
        asyncio.run(run_better_coder())
    except Exception as e:
        log(f'Error running Better Coder: {e}')
    finally:
        release_lock(lock_fd)


if __name__ == '__main__':
    main()