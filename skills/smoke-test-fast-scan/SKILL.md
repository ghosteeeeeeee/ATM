---
name: smoke-test-fast-scan
description: Run Hermes smoke_test.py without timing out on huge log files; diagnose real pipeline failures vs false alarms.
---

# Running smoke_test.py on Hermes without timing out

## When to use this

You're about to run `python3 /root/.hermes/scripts/smoke_test.py` and want it to actually finish, OR you're debugging a specific check that's failing.

## Why this exists

`pipeline.log` is **1.3 GB / 18+ million lines** (verified 2026-07-13). The original smoke_test.py used `read_text().splitlines()` on this file in two checks. The full suite timed out at 60s with zero output. Individual checks on the log file alone took >5s each.

## Quick reference

| Task | Command |
|---|---|
| Full suite (now ~0.7s, all checks pass on healthy pipeline) | `python3 /root/.hermes/scripts/smoke_test.py` |
| Just critical checks | `python3 smoke_test.py --critical` |
| Auto-heal failures | `python3 smoke_test.py --heal` |
| Run only checks for one script | `python3 smoke_test.py --target signal_compactor.py` |
| **Individual check (debug a specific failure)** | `python3 -c "from smoke_test import check_X; print(check_X())"` |

## Pitfalls & false alarms (verified 2026-07-13)

1. **`/tmp/hermes-pipeline.lock` is stale (>10 min)** — does NOT mean the pipeline is stuck.
   `hermes-pipeline.timer` is `Type=oneshot` (spawns fresh python per tick, exits cleanly).
   The lock file is ORPHANED DEBRIS from a prior crashed run. The check now verifies the
   pipeline is actively logging fresh "Pipeline done" / "Pipeline LIVE" lines before flagging.

2. **`hermes-pump-hunter.service` "inactive"** — false alarm. It's `Type=oneshot` and
   exits with SUCCESS after each tick. The TIMER is what should be active, and it is.

3. **`price_data_fresh` "Prices stale"** — false alarm if you only check `prices.json`.
   Real price storage is `hl_cache.json` (price_collector cache) + candle DBs.
   The check now accepts any of: prices.json / hl_cache.json / candles.db / signals_hermes.db.

4. **`check_pipeline_log_errors` was reading 1.3GB into RAM** — fixed to use
   `subprocess.run(['tail', '-n', N, ...])` which streams the tail instantly.

5. **`check_no_flapping` had same problem** — also fixed to use tail subprocess.

## Diagnosing a specific failing check

If `python3 smoke_test.py` exits 1, identify WHICH check failed first:

```bash
python3 /root/.hermes/scripts/smoke_test.py 2>&1 | grep FAIL
```

Then run just that check with debug output:

```bash
python3 -c "
import time
from smoke_test import check_<name>
t = time.time()
ok, msg = check_<name>()
print(f'  [{\"PASS\" if ok else \"FAIL\"}] {msg}  ({time.time()-t:.2f}s)')
"
```

Common checks to inspect:
- `check_pipeline_log_errors` — tail of pipeline.log
- `check_price_data_fresh` — checks prices.json / hl_cache.json / candle DBs
- `check_hotset_exists` — /var/www/hermes/data/hotset.json
- `check_stale_locks` — /tmp/hermes-*.lock + /root/.hermes/locks/*.lock
- `check_trading_timers` — runs `systemctl is-active` on 12 timers + services

## Pipeline state quick-check (without smoke_test)

If smoke_test is misbehaving or you want a quick sanity look:

```bash
# Pipeline active?
tail -5 /root/.hermes/logs/pipeline.log
# Latest pipeline done line tells you last successful cycle

# Timers state
systemctl list-timers --all | grep hermes-

# Prices fresh?
stat -c '%y' /var/www/hermes/data/hl_cache.json
stat -c '%y' /root/.hermes/data/candles.db
stat -c '%y' /root/.hermes/data/signals_hermes.db

# Hotset fresh?
stat -c '%y' /var/www/hermes/data/hotset.json
```

## What "healthy" looks like (2026-07-13 baseline)

- All 15 checks PASS, total runtime ~0.7s
- `pipeline_errors`: no errors
- `pipeline_not_stuck`: "lock is orphan debris (Xmin old, but pipeline active at HH:MM:SS)"
- `price_data_fresh`: "<source> OK (Ns)"
- `signal_db`: SQLite, ~1600 rows
- `hotset_exists`: <60s old (signal_compactor writes every 1min)
- `trading_timers`: all 12 timers/services active
- `profit_monster_fires`: <1800s ago
- `pump_hunter_log`: <600s ago

## Don't do this

- ❌ Don't `read_text()` on `pipeline.log` in Python — always use `subprocess.run(['tail', ...])`
- ❌ Don't add `hermes-pump-hunter.service` to `TRADING_SERVICES` — it's oneshot
- ❌ Don't trust `prices.json` as the only price source — check `hl_cache.json` too
- ❌ Don't trust an old `hermes-pipeline.lock` as proof the pipeline is stuck