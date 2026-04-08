#!/usr/bin/env python3
"""Daily disk space health check for Better Coder system."""
import shutil
import subprocess
from datetime import datetime

LOG = '/root/.hermes/logs/health-check.log'
MIN_FREE_MB = 500

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
    log('=== Daily Health Check ===')
    
    alert = False
    for path, name in [('/root', 'root'), ('/tmp', 'tmp')]:
        try:
            usage = shutil.disk_usage(path)
            free_mb = usage.free / (1024**2)
            free_gb = usage.free / (1024**3)
            
            if free_mb < MIN_FREE_MB:
                log(f'ALERT: Low disk space on /{name}: {free_mb:.0f}MB free')
                alert = True
                # Try cleanup
                subprocess.run(['find', '/tmp', '-type', 'f', '-name', '*.tmp', '-mtime', '+1', '-delete'],
                             capture_output=True, timeout=10)
            else:
                log(f'OK: /{name} has {free_gb:.2f}GB free')
        except Exception as e:
            log(f'ERROR checking {path}: {e}')
    
    if alert:
        log('Health check: ALERT - low disk space detected')
    else:
        log('Health check: OK')
    
    log('=== Daily Health Check Complete ===')

if __name__ == '__main__':
    run()
