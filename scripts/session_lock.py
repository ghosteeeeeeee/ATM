#!/usr/bin/env python3
"""Session lock manager for Hermes trading system.

Usage:
    python3 session_lock.py lock    # Create lock (human session active)
    python3 session_lock.py unlock  # Remove lock (session ended)
    python3 session_lock.py check   # Check if lock is active
"""
import sys
import os
import time

LOCK_FILE = '/tmp/hermes-session-active.lock'
LOCK_TTL = 3600  # 1 hour

def lock():
    """Create session lock."""
    with open(LOCK_FILE, 'w') as f:
        f.write(f'active\nstarted={time.time()}\npid={os.getpid()}\n')
    print(f'Session lock created: {LOCK_FILE}')

def unlock():
    """Remove session lock."""
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)
        print(f'Session lock removed: {LOCK_FILE}')
    else:
        print('No lock file to remove')

def check():
    """Check if lock is active (not expired)."""
    if not os.path.exists(LOCK_FILE):
        print('NO LOCK — CEO can make changes')
        return False
    
    try:
        with open(LOCK_FILE) as f:
            content = f.read()
        
        # Parse start time
        for line in content.split('\n'):
            if line.startswith('started='):
                start_time = float(line.split('=')[1])
                age = time.time() - start_time
                if age > LOCK_TTL:
                    print(f'LOCK EXPIRED ({age/60:.0f}min old, TTL={LOCK_TTL/60:.0f}min)')
                    os.remove(LOCK_FILE)
                    return False
                else:
                    print(f'LOCK ACTIVE ({age/60:.0f}min old, expires in {(LOCK_TTL-age)/60:.0f}min)')
                    return True
    except Exception:
        pass
    
    print('LOCK ACTIVE (unreadable)')
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    if cmd == 'lock':
        lock()
    elif cmd == 'unlock':
        unlock()
    elif cmd == 'check':
        check()
    else:
        print(f'Unknown command: {cmd}')
        print(__doc__)
