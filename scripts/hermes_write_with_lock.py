#!/usr/bin/env python3
"""
hermes_write_with_lock.py — Write a file with exclusive flock lock.
Prevents concurrent writes from colliding (two agents/cron jobs writing same file).

Usage:
  cat content.txt | python3 hermes_write_with_lock.py <lockname> <target_file>
  python3 hermmes_write_with_lock.py context.md /root/.hermes/CONTEXT.md << 'EOF'
  content here
  EOF

Lock files: /root/.hermes/locks/<lockname>.lock
Timeout: 30s wait, 5s polling, SKIPPED (exit 0) on timeout.
"""
import sys, os, fcntl, time

lockname = sys.argv[1] if len(sys.argv) > 1 else sys.exit(1)
target   = sys.argv[2] if len(sys.argv) > 2 else sys.exit(1)
max_wait = 30
interval = 5

LOCK_DIR = "/root/.hermes/locks"
os.makedirs(LOCK_DIR, exist_ok=True)

lockfile = os.path.join(LOCK_DIR, f"{lockname}.lock")

fd = os.open(lockfile, os.O_CREAT | os.O_RDWR)
for _ in range(max_wait // interval):
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        break
    except BlockingIOError:
        try:
            holder = open(lockfile).read().strip()
        except:
            holder = "unknown"
        print(f"Locked by [{holder}], waiting...", file=sys.stderr)
        time.sleep(interval)
else:
    print(f"SKIPPED: {target} still locked after {max_wait}s", file=sys.stderr)
    os.close(fd)
    sys.exit(0)

# Write PID so we know who holds it
open(lockfile, 'w').write(str(os.getpid()))

# Read content from stdin and write to target
content = sys.stdin.read()
with open(target, 'w') as f:
    f.write(content)

fcntl.flock(fd, fcntl.LOCK_UN)
os.close(fd)
os.unlink(lockfile)
print(f"Wrote {len(content)} bytes to {target}", file=sys.stderr)
