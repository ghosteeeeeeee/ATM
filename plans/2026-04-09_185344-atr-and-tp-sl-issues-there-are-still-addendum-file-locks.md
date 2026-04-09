# Hermes File Locking Plan

## Goal
Prevent concurrent writes from multiple agents (cron, subagents, manual runs) to the same Hermes file. When a file is locked, the caller retries in 1 minute rather than failing or overwriting.

## Context

`hermes_write_with_lock.py` exists as a CLI pipe utility, but it's not usable as a Python import for other modules. Several scripts already use `fcntl.flock` directly (`run_pipeline.py`, `ai_decider.py`, `hl-sync-guardian.py`, etc.), but there's no shared standard.

For the ATR/TP-SL plan, these files will be modified and need locking:
- `decider_run.py` — export `_atr_multiplier` (ATR table)
- `position_manager.py` — import from decider_run
- `batch_tpsl_rewrite.py` — import from decider_run
- `hyperliquid_exchange.py` — add `clean_all_tpsl_orders`
- `hl-sync-guardian.py` — call clean + fix close race

If two agents (e.g., a cron subagent and your interactive session) write these simultaneously, git will see conflicting writes.

---

## Proposed Approach

Create `hermes_file_lock.py` — a reusable module-level context manager:

```python
# hermes_file_lock.py
LOCK_DIR = "/root/.hermes/locks"
os.makedirs(LOCK_DIR, exist_ok=True)

class FileLock:
    """Exclusive flock context manager. Retry every 60s for up to 20 minutes."""
    def __init__(self, lockname: str, timeout: int = 1200, interval: int = 60):
        self.lockfile = os.path.join(LOCK_DIR, f"{lockname}.lock")
        self.timeout = timeout
        self.interval = interval
        self.fd = None

    def __enter__(self):
        os.makedirs(LOCK_DIR, exist_ok=True)
        self.fd = os.open(self.lockfile, os.O_CREAT | os.O_RDWR)
        deadline = time.time() + self.timeout
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                open(self.lockfile, 'w').write(str(os.getpid()))
                return self
            except BlockingIOError:
                if time.time() >= deadline:
                    raise RuntimeError(f"Lock {self.lockname} timed out after {self.timeout}s")
                time.sleep(self.interval)

    def __exit__(self, *args):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
        self.fd = None
        try: os.unlink(self.lockfile)
        except: pass
```

Usage in any script:
```python
from hermes_file_lock import FileLock

with FileLock('decider_run'):
    # exclusively write to decider_run.py
    patch(...)
```

On lock contention: sleeps 60s, retries. After 20 min timeout: raises.

---

## Step-by-Step Plan

### Step 1: Create `/root/.hermes/scripts/hermes_file_lock.py`
- `FileLock` class with `fcntl.flock` (LOCK_EX | LOCK_NB)
- PID written to lockfile so operators can see who holds it
- Configurable timeout (default 20 min) and retry interval (default 60s)
- Cleanup on __exit__ (unlink lockfile)

### Step 2: Add lock guards to files being modified for ATR plan
For each file in the ATR/TP-SL plan, wrap write operations with `with FileLock('<filename>'):`:

| File | Lock scope |
|---|---|
| `decider_run.py` | Around the k-mult exporter patch |
| `position_manager.py` | Around `_pm_atr_multiplier` replacement |
| `batch_tpsl_rewrite.py` | Around `compute_sl_tp` replacement |
| `hyperliquid_exchange.py` | Around `clean_all_tpsl_orders` addition |
| `hl-sync-guardian.py` | Around `reconcile_tp_sl` edits and close race fix |

### Step 3: Update `ai_decider.py` — already has a lock but uses a different path
- Currently uses `/tmp/ai-decider.lock` — switch to `/root/.hermes/locks/ai_decider.lock`
- Use same `FileLock` class for consistency

### Step 4: Update `hl-sync-guardian.py`
- Replace existing `_LOCK_FILE = '/tmp/hermes-guardian.lock'` with `FileLock('hl_sync_guardian')` pattern
- Use `/root/.hermes/locks/hl_sync_guardian.lock` for consistency

### Step 5: Create a decorator for convenience
```python
def locked(lockname: str):
    """Decorator: with FileLock(lockname): wrapped_function()"""
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            with FileLock(lockname):
                return f(*args, **kwargs)
        return wrapper
    return deco
```

---

## Files Likely to Change / Create

| File | Change |
|---|---|
| `/root/.hermes/scripts/hermes_file_lock.py` | **NEW** — create `FileLock` class |
| `/root/.hermes/scripts/decider_run.py` | Wrap k-table export in `FileLock('decider_run')` |
| `/root/.hermes/scripts/position_manager.py` | Wrap `_pm_atr_multiplier` import swap in `FileLock('position_manager')` |
| `/root/.hermes/scripts/batch_tpsl_rewrite.py` | Wrap `compute_sl_tp` import swap in `FileLock('batch_tpsl_rewrite')` |
| `/root/.hermes/scripts/hyperliquid_exchange.py` | Wrap `clean_all_tpsl_orders` addition in `FileLock('hyperliquid_exchange')` |
| `/root/.hermes/scripts/hl-sync-guardian.py` | Wrap `reconcile_tp_sl` edits + `close_position_hl` race fix in `FileLock('hl_sync_guardian')` |

## Lock-to-File Mapping (authoritative list)

| Lock name | File(s) protected |
|---|---|
| `decider_run` | `decider_run.py` |
| `position_manager` | `position_manager.py` |
| `batch_tpsl_rewrite` | `batch_tpsl_rewrite.py` |
| `hyperliquid_exchange` | `hyperliquid_exchange.py` |
| `hl_sync_guardian` | `hl-sync-guardian.py` |
| `ai_decider` | `ai_decider.py` |
| `brain_trading` | `brain/trading.md` |
| `context_md` | `CONTEXT.md` |

## Risks / Tradeoffs

- **Risk:** Scripts that run very long (e.g., `ai_decider`) hold locks for minutes → other agents wait. This is acceptable since retry is automatic.
- **Tradeoff:** Lock timeout of 20 min is long — could mask a real deadlock. If lock never releases (crash), the lockfile persists but `fcntl.flock` will still grab it since it's a BSD-style lock (not POSIX).
- **Design note:** `fcntl.flock` is process-level, not machine-level (doesn't work over NFS). On a single server this is fine.

## Validation

1. Run two instances of any script — second should block and wait 60s
2. Kill a holding process — next waiter should acquire immediately after
3. Check `/root/.hermes/locks/` — lockfiles are created and removed correctly
4. After deployment, run `smoke_test.py --critical` — no lock-related failures
