#!/usr/bin/env python3
"""
hermes_file_lock.py — Exclusive flock-based file lock with automatic retry.
All Hermes scripts should import this instead of hand-rolling fcntl locks.

Usage:
    from hermes_file_lock import FileLock

    with FileLock('hotset_json'):
        # Atomic write: write to temp file, then os.replace()
        import tempfile
        tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(HOTSET_PATH))
        try:
            with os.fdopen(tmp_fd, 'w') as tmp_f:
                json.dump(data, tmp_f)
            os.replace(tmp_path, HOTSET_PATH)
        except Exception:
            os.unlink(tmp_path)
            raise

    with FileLock('ai_decider'):
        patch(...)

On contention: sleeps 60s, retries. After 20 min timeout: raises RuntimeError.
Lockfiles live in /root/.hermes/locks/ — PID written for operator visibility.
"""

import os, fcntl, time

from paths import *
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


# ── Atomic JSON Write ─────────────────────────────────────────────────────────

def atomic_write_json(data, path):
    """Write JSON data atomically using temp file + os.replace.
    
    Prevents corruption from crashes mid-write. The old file is only
    replaced after the new file is fully written and synced.
    
    Usage:
        from hermes_file_lock import atomic_write_json
        atomic_write_json({'key': 'value'}, '/path/to/file.json')
    """
    import json
    import tempfile
    
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    
    # Write to temp file in same directory (same filesystem for atomic replace)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name or '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise


def load_json(path, default=None):
    """Load JSON file safely, returning default on any error."""
    import json
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default
