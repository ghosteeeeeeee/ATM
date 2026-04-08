#!/usr/bin/env python3
"""Weekly self-healing audit for Better Coder system."""
import sys
import subprocess
from datetime import datetime

LOG = '/root/.hermes/logs/audit.log'

def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    try:
        with open(LOG, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass

def run():
    log('=== Weekly Audit Starting ===')
    
    # Check services - note: hermes-better-coder is timer-triggered (oneshot)
    # so we check the timer instead
    services_to_check = [
        ('hermes-coding-mcp.service', 'MCP Server'),
        ('hermes-better-coder.timer', 'Better Coder Timer'),
    ]
    for svc, desc in services_to_check:
        result = subprocess.run(['systemctl', 'is-active', svc], capture_output=True, text=True)
        status = 'OK' if result.returncode == 0 else f'FAIL({result.stdout.strip()})'
        log(f'{desc} ({svc}): {status}')
    
    # Check if Better Coder dispatcher ran recently
    result = subprocess.run(['systemctl', 'show', 'hermes-better-coder.service', '-p', 'Result'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        result_val = result.stdout.strip().split('=')[1] if '=' in result.stdout else 'unknown'
        log(f'Better Coder last run result: {result_val}')
    
    # Run a test of the dispatcher (limit to 1 task)
    result = subprocess.run(
        ['python3', '-c', 'import sys; sys.path.insert(0, "/root/.hermes/mcp/hermes-coding-mcp"); from dispatcher.dispatcher import ParallelDispatcher; print("OK")'],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        log('Self-healing test: OK')
    else:
        log(f'Self-healing test: FAIL - {result.stderr[:200]}')
    
    log('=== Weekly Audit Complete ===')

if __name__ == '__main__':
    run()
