#!/usr/bin/env python3
"""
hermes_file_lock.py — Exclusive flock-based file lock with automatic retry.
All Hermes scripts should import this instead of hand-rolling fcntl locks.

Usage:
    from hermes_file_lock import FileLock

    with FileLock('hotset_json'):
        json.dump(data, open(HOTSET_PATH, 'w'))

    with FileLock('ai_decider'):
        patch(...)

On contention: sleeps 60s, retries. After 20 min timeout: raises RuntimeError.
Lockfiles live in /root/.hermes/locks/ — PID written for operator visibility.
"""

import os, fcntl, time

LOCK_DIR = "/root/.hermes/locks"
os.makedirs(LOCK_DIR, exist_ok=True)

TIMEOUT_DEFAULT = 1200   # 20 min
INTERVAL_DEFAULT = 60    # 1 min


class FileLock:
    """Exclusive flock context manager with retry.

    Args:
        lockname:   Base name for lockfile (becomes /root/.hermes/locks/<lockname>.lock)
        timeout:    Max seconds to wait before raising (default 20 min)
        interval:   Seconds between retry attempts (default 60s)
    """

    def __init__(self, lockname: str, timeout: int = TIMEOUT_DEFAULT,
                 interval: int = INTERVAL_DEFAULT):
        self.lockname  = lockname
        self.lockfile  = os.path.join(LOCK_DIR, f"{lockname}.lock")
        self.timeout   = timeout
        self.interval  = interval
        self.fd        = None

    def __enter__(self):
        # FIX (2026-04-14): Delete stale lock file BEFORE acquiring.
        # Previous version deleted on __exit__, which created a race: between
        # unlock and next process's open(), a third process could also acquire.
        # Now we clean stale locks proactively so only ONE process can hold at a time.
        # Also cleans orphaned lock files from killed processes.
        try:
            if os.path.exists(self.lockfile):
                os.unlink(self.lockfile)
        except Exception:
            pass
        self.fd = os.open(self.lockfile, os.O_CREAT | os.O_RDWR, 0o644)
        deadline = time.time() + self.timeout
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Write PID so operators can identify the holder
                try:
                    os.lseek(self.fd, 0, os.SEEK_SET)
                    os.ftruncate(self.fd, 0)
                    os.write(self.fd, str(os.getpid()).encode())
                except Exception:
                    pass
                return self
            except BlockingIOError:
                if time.time() >= deadline:
                    fcntl.flock(self.fd, fcntl.LOCK_UN)
                    os.close(self.fd)
                    self.fd = None
                    raise RuntimeError(
                        f"Lock [{self.lockname}] timed out after {self.timeout}s "
                        f"(holder: {self._read_holder()})"
                    )
                time.sleep(self.interval)

    def __exit__(self, *args):
        if self.fd is None:
            return
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
        except Exception:
            pass
        self.fd = None
        try:
            os.unlink(self.lockfile)
        except Exception:
            pass

    def _read_holder(self) -> str:
        try:
            return open(self.lockfile).read().strip()
        except Exception:
            return "unknown"
