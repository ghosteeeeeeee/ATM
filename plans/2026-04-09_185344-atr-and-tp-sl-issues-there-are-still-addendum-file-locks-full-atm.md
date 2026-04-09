# Hermes File Locking — Complete ATM Scripts Inventory

## Lockable Files

Priority = how many agents/scripts write to the file simultaneously. All locks use `fcntl.flock`, retry every 60s, timeout 20 min.

### CRITICAL (multiple agents writing) — needs FileLock on every write

| Lock name | File | Writers |
|---|---|---|
| `hotset_json` | `/var/www/hermes/data/hotset.json` | `ai_decider.py`, `decider_run.py` |
| `hotset_last_updated` | `/var/www/hermes/data/hotset_last_updated.json` | `ai_decider.py`, `decider_run.py` |
| `trades_json` | `/var/www/hermes/data/trades.json` | `position_manager.py`, `hl-sync-guardian.py`, `decider_run.py`, `batch_tpsl_rewrite.py` |
| `signals_json` | `/var/www/hermes/data/signals.json` | `hermes-trades-api.py`, `signal_gen.py`, `ai_decider.py` |
| `loss_cooldowns_json` | `/var/www/hermes/data/loss_cooldowns.json` | `decider_run.py`, `position_manager.py`, `hl-sync-guardian.py` |
| `trailing_stops_json` | `/var/www/hermes/data/trailing_stops.json` | `position_manager.py`, `batch_tpsl_rewrite.py`, `hl-sync-guardian.py` |
| `flip_counts_json` | `/var/www/hermes/data/flip_counts.json` | `decider_run.py`, `position_manager.py` |
| `recent_trades_json` | `/var/www/hermes/data/recent_trades.json` | multiple |

### HIGH (cron-triggered pipeline scripts writing shared state)

| Lock name | File | Writers |
|---|---|---|
| `ai_decider` | `ai_decider.py` | pipeline (10m cron) + interactive agents |
| `decider_run` | `decider_run.py` | pipeline (1m cron) + interactive agents |
| `position_manager` | `position_manager.py` | pipeline (1m cron) + interactive agents |
| `hl_sync_guardian` | `hl-sync-guardian.py` | systemd service + interactive agents |
| `signal_gen` | `signal_gen.py` | pipeline (1m cron) + interactive agents |
| `hermes_trades_api` | `hermes-trades-api.py` | pipeline (1m cron) |
| `batch_tpsl_rewrite` | `batch_tpsl_rewrite.py` | cron (1m) |
| `hyperliquid_exchange` | `hyperliquid_exchange.py` | all HL interactions |
| `run_pipeline` | `run_pipeline.py` | systemd timer + interactive agents |

### MEDIUM (database — use SQLite WAL mode, advisory locks via Python threading locks)

| Lock name | Target |
|---|---|
| `signals_db` | `signals_hermes.db` / `signals_hermes_runtime.db` |
| `brain_db` | `brain.db` |

### LOW (read-only or rarely written, but still listed for completeness)

| Lock name | File |
|---|---|
| `hype_live_trading` | `/var/www/hermes/data/hype_live_trading.json` |
| `pipeline_heartbeat` | `/var/www/hermes/data/pipeline_heartbeat.json` |
| `context_md` | `CONTEXT.md` |
| `brain_trading_md` | `brain/trading.md` |

---

## Implementation: hermes_file_lock.py

```python
# /root/.hermes/scripts/hermes_file_lock.py
import os, fcntl, time

LOCK_DIR = "/root/.hermes/locks"
os.makedirs(LOCK_DIR, exist_ok=True)

class FileLock:
    def __init__(self, lockname: str, timeout: int = 1200, interval: int = 60):
        self.lockname = lockname
        self.lockfile = os.path.join(LOCK_DIR, f"{lockname}.lock")
        self.timeout = timeout
        self.interval = interval
        self.fd = None

    def __enter__(self):
        self.fd = os.open(self.lockfile, os.O_CREAT | os.O_RDWR, 0o644)
        deadline = time.time() + self.timeout
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                open(self.lockfile, 'w').write(str(os.getpid()))
                return self
            except BlockingIOError:
                if time.time() >= deadline:
                    raise RuntimeError(f"Lock [{self.lockname}] timed out after {self.timeout}s")
                time.sleep(self.interval)

    def __exit__(self, *args):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
        self.fd = None
        try: os.unlink(self.lockfile)
        except: pass
```

### Usage pattern

```python
from hermes_file_lock import FileLock

with FileLock('hotset_json'):
    data = json.load(open(HOTSET_PATH))
    # modify
    json.dump(data, open(HOTSET_PATH, 'w'))

with FileLock('ai_decider'):
    patch_ai_decider()

with FileLock('decider_run'):
    patch_decider_run()
```

### If locked: retry-and-continue pattern

```python
def write_with_lock(path: str, content: str, lockname: str):
    try:
        with FileLock(lockname):
            open(path, 'w').write(content)
    except RuntimeError:
        print(f"[WARN] {path} locked for 20 min — skipping, will retry next cycle")
        return False
    return True
```

---

## Step-by-Step Plan

1. Create `hermes_file_lock.py` (30 lines)
2. Audit each of the 9 core scripts for JSON/data file writes — wrap with `with FileLock('name'):`
3. Audit each of the 9 high-priority scripts — wrap code edits (not just data writes) with `FileLock`
4. Add `LOCK = '/root/.hermes/locks/ai_decider.lock'` to `ai_decider.py` (replace existing `/tmp/` path)
5. Add `LOCK = '/root/.hermes/locks/hl_sync_guardian.lock'` to `hl-sync-guardian.py`
6. Verify no circular lock dependencies (A needs B needs A)
7. Smoke test — run pipeline + manual edit simultaneously

## Circular Dependency Check

Known lock ordering (acquire in this order only):
```
data-file locks (hotset_json, trades_json, ...) → script locks (ai_decider, decider_run, ...)
```

Never hold a data-file lock while acquiring a script lock.

## Risks

- **Risk:** Deadly embrace (A holds hotset_json, wants ai_decider; B holds ai_decider, wants hotset_json)
- **Mitigation:** Strict lock ordering above. All scripts acquire data-file locks FIRST, script locks SECOND.
- **Risk:** 20-min timeout too long — masks a real crash
- **Mitigation:** PID written to lockfile so operator can see who holds it and kill if needed
