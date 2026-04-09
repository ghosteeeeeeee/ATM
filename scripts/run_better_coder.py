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
import fcntl
import subprocess
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
        # First, clean up any stale lock files from dead processes
        if os.path.exists(LOCK):
            try:
                with open(LOCK, 'r') as f:
                    old_pid = f.read().strip()
                if old_pid:
                    try:
                        # Check if process is still alive
                        os.kill(int(old_pid), 0)
                    except (ProcessLookupError, ValueError, PermissionError):
                        # Process is dead or we can't send signal - stale lock, remove it
                        os.unlink(LOCK)
            except (IOError, OSError, ValueError):
                # Can't read lock file - remove it
                os.unlink(LOCK)

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
        """Execute MCP tools directly.

        Tool parameter mapping:
        - read_file: expects 'path', 'offset', 'limit'
        - write_file: expects 'path', 'content'
        - search_code: expects 'pattern', 'path', 'file_glob'
        - execute_command: expects 'command', 'timeout', 'workdir'

        The worker passes {'task': self.task} as params, so we need to
        extract the meaningful content and map it to the appropriate tool param.
        """
        from server import read_file, write_file, search_code, execute_command
        import re

        # The task description from worker
        task = params.get('task', '')

        # Map tool_name to function and parameter extraction
        tool_map = {
            'read_file': (read_file, ['path', 'offset', 'limit']),
            'write_file': (write_file, ['path', 'content']),
            'search_code': (search_code, ['pattern', 'path', 'file_glob']),
            'execute_command': (execute_command, ['command', 'timeout', 'workdir']),
        }

        if tool_name not in tool_map:
            return '{"isError": true, "error": "unknown_tool"}'

        func, expected_params = tool_map[tool_name]

        # Extract meaningful parameters from task description
        # Worker only passes {'task': task_description} so we parse it
        kwargs = {}

        if tool_name == 'read_file':
            # Try to extract a file path from the task
            # Patterns like "read file /path/to/file", "cat /path", "view /path"
            path_match = re.search(r'(?:read|cat|view|show|open|inspect|check)\s+(?:file\s+)?[\'"]?([/\w\.\-_]+)', task, re.IGNORECASE)
            if path_match:
                kwargs['path'] = path_match.group(1)
            elif 'path' in params:
                kwargs['path'] = params['path']
            else:
                kwargs['path'] = task  # Fallback: treat entire task as path

        elif tool_name == 'write_file':
            # Try to extract path and content from params or task
            if 'path' in params:
                kwargs['path'] = params['path']
            if 'content' in params:
                kwargs['content'] = params['content']
            else:
                kwargs['content'] = task  # Fallback: use task as content

        elif tool_name == 'search_code':
            # Try to extract pattern from task
            # Patterns like "search for pattern", "find 'pattern'", "grep 'pattern'"
            pattern_match = re.search(r'(?:search|find|grep|lookup|locate)\s+(?:for\s+)?[\'"]?([^\'"]+)[\'"]?', task, re.IGNORECASE)
            if pattern_match:
                kwargs['pattern'] = pattern_match.group(1)
            elif 'pattern' in params:
                kwargs['pattern'] = params['pattern']
            else:
                kwargs['pattern'] = task  # Fallback: use task as pattern

            if 'path' in params:
                kwargs['path'] = params['path']
            if 'file_glob' in params:
                kwargs['file_glob'] = params['file_glob']

        elif tool_name == 'execute_command':
            # Extract command from task
            # Patterns like "run command X", "execute X", "run X"
            if 'command' in params:
                kwargs['command'] = params['command']
            else:
                # Extract command after verbs like run, execute, build, test
                cmd_match = re.search(r'(?:run|execute|build|test|install|compile)\s+(.+)', task, re.IGNORECASE)
                if cmd_match:
                    kwargs['command'] = cmd_match.group(1).strip()
                else:
                    kwargs['command'] = task  # Fallback: use task as command

            if 'timeout' in params:
                kwargs['timeout'] = params['timeout']
            if 'workdir' in params:
                kwargs['workdir'] = params['workdir']

        # Filter to only expected params and call function
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in expected_params}
        result = await func(**filtered_kwargs)
        return result
    
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


def check_disk_space(min_free_mb=500):
    """Check disk space on /root and /tmp. Returns (ok, message)."""
    import shutil
    
    for path, name in [('/root', 'root'), ('/tmp', 'tmp')]:
        try:
            usage = shutil.disk_usage(path)
            free_gb = usage.free / (1024**3)
            free_mb = usage.free / (1024**2)
            if free_mb < min_free_mb:
                msg = f'WARN: Low disk space on /{name}: {free_mb:.0f}MB free (min {min_free_mb}MB)'
                log(msg)
                return False, msg
            log(f'Disk check OK: /{name} has {free_gb:.2f}GB free')
        except Exception as e:
            log(f'WARN: Could not check disk space on {path}: {e}')
    
    return True, 'disk space OK'


def main():
    # Check disk space before running
    ok, msg = check_disk_space(500)
    if not ok:
        log(f'Disk space too low — skipping this cycle. {msg}')
        sys.exit(0)
    
    lock_fd = acquire_lock()
    if lock_fd is None:
        log('Another instance is running — skipping this cycle')
        sys.exit(0)
    
    try:
        asyncio.run(run_better_coder())

        # Post-run smoke test: check any scripts modified in the last 30 minutes
        # Use --heal to attempt self-healing before reporting failure
        smoke_script = "/root/.hermes/scripts/smoke_test.py"
        smoke_result = subprocess.run(
            [sys.executable, smoke_script, "--changed-since", "30", "--heal"],
            capture_output=False,
            timeout=120
        )
        if smoke_result.returncode != 0:
            log(f'SMOKE TEST FAILED — infrastructure issues remain after auto-heal attempts')
        else:
            log(f'Smoke test PASSED — all changed-script checks OK (auto-healed if needed)')

    except Exception as e:
        log(f'Error running Better Coder: {e}')
    finally:
        release_lock(lock_fd)


if __name__ == '__main__':
    main()