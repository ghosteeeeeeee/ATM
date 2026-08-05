---
name: hermes-pipeline-debug
description: Debug frozen or misbehaving Hermes pipeline — frozen hot-set, stale signals, lock contention, data gaps, and pipeline timing bugs.
---

# Hermes Pipeline Debug

Comprehensive debugging guide for frozen or misbehaving Hermes trading pipeline.

---

## Quick Reference: smoke_test FAIL Triage

smoke_test.py reports several categories of FAIL. Each has a different resolution path:

| Check | What it means | Resolution |
|-------|---------------|------------|
| `pipeline_not_stuck` | Lock exists >10min + no holder | Bug 17: Lock fd not closed → stale mtime; `rm /tmp/hermes-pipeline.lock` + fix applied |
| `stale_locks` | Lock file age > threshold + no living holder | Same as above — orphaned mtime from uncleared fd |
| `price_data_fresh` | prices.json age > 180s | Root cause was TIMESTAMP ORDERING, not data lag. `save_prices()` wrote BEFORE ~90s aggregation, making file always appear 90-180s old. Fix: second `save_prices()` call after aggregation in `price_collector.py`. signal_gen reads `latest_prices` SQLite (fresh), NOT prices.json. |
| `trading_timers` | `hermes-pump-hunter.service=inactive` | Bug 18: Type=oneshot always "inactive" — use `is-enabled` not `is-active` |
| `live_mode=unknown` | live_mode file not in expected location | Check `hype_live_trading.json` directly |

**Key diagnostic commands:**
```bash
# Orphaned lock?
lsof /tmp/hermes-pipeline.lock
ps aux | grep hl-sync-guardian | grep -v grep  # guardian alive = pipeline fine

# Price collector lagging?
systemctl status hermes-price-collector.service
journalctl -u hermes-price-collector.service --since "5 minutes ago" | tail -5

# Verify prices.json timestamp fix
python3 -c "import json,time; d=json.load(open('/root/.hermes/data/prices.json')); print(f'Age: {time.time()-d[\"updated\"]:.0f}s')"
```

**Canonical truth:** `journalctl -u hermes-pipeline --since "90 seconds ago"` > pipeline.log > lock file.
Stale lock + active systemd timer + guardian alive = orphaned lock, NOT stuck pipeline.
Price lag between runs self-resolves — don't restart on < 3min staleness.

---

## 1. Current Pipeline Architecture (Updated 2026-05-08)

```
systemd timer (every 1 min)
  └── run_pipeline.py
        ├── signal_compactor.py    (STEPS_EVERY_MIN — hot-set compaction, ~1 min)
        ├── breakout_engine.py    (STEPS_EVERY_MIN — ~60s timeout)
        ├── signals_runner.py     (BACKGROUND via run_bg() — non-blocking)
        │     └── signals/*.py    (27 signal scripts from signals/__init__.py registry)
        ├── decider_run.py        (STEPS_EVERY_MIN — checks guardian-closing-markers.json)
        ├── position_manager.py   (STEPS_EVERY_MIN)
        └── hermes-trades-api.py  (STEPS_EVERY_MIN)
```

**DEFUNCT (do not use):**
- `ai_decider.py` — removed 2026-04-16 (LLM compactor, replaced by signal_compactor.py)
- `signal_gen.py` — removed 2026-05-06 (inline signals replaced by signals_runner + signals/ module)
- `price_collector` — NOT in pipeline steps (runs exclusively via hermes-price-collector.timer)

**Lock files:** `/tmp/hermes-pipeline.lock` (pipeline), `/tmp/hermes-guardian.lock` (guardian),
`/tmp/candle-predictor.lock` (candle_predictor — same Pattern A as the pipeline lock; a
foreground-timeout kill leaves the lock held by the now-dead PID. The script does not check
PID liveness on lock acquire. `pgrep -af candle_predictor` returns empty → `rm` the lock and
re-run. See `candle-predictor-tuner/references/running-predictor.md` → "Stale Lock From Killed
Run" for the full diagnostic and the stale-vs-Ollama-crash differentiation table.)

**DBs:**
- SQLite: `/root/.hermes/data/signals_hermes_runtime.db` (signals, token_speeds)
- SQLite: `/root/.hermes/data/candles.db` (OHLCV candles — 1m/5m/15m/1h/4h, all stale since ~May 28 backfill)
- SQLite: `/root/.hermes/data/signals_hermes.db` (price_history + latest_prices — 87 fresh tokens, 143 stale)
- PostgreSQL: `host=/var/run/postgresql database=brain user=postgres` (trades)

**Hot-set path:** `/var/www/hermes/data/hotset.json` (NOT /root/.hermes/hot-set.json)

---

## 2. Frozen Pipeline Diagnosis

### Step 1 — Check Running Processes
```bash
ps aux | grep -E "signal_gen|decider|guardian|ai_decider|predictor|hl-sync" | grep -v grep
systemctl status hermes-pipeline.timer
systemctl status hermes-signal-compactor.timer
```

### Step 1b — Timer Disabled vs Script Dead
```bash
systemctl status hermes-signal-compactor.timer | grep "Active:"
# → "inactive (dead)" = TIMER DISABLED, not just waiting
# → "active (waiting)" = timer IS running

journalctl -u hermes-signal-compactor.service --since "24 hours ago" | tail -5
# No entries = timer has NOT fired in 24h → signal_compactor never runs
```

**Why this matters:** The compactor IS the hot-set builder. If its timer is disabled:
- hotset.json goes STALE
- APPROVED signals in DB NEVER expire
- old signals accumulate indefinitely

### Step 2 — Lock Files
```bash
ls -la /root/.hermes/locks/
lsof /tmp/hermes-pipeline.lock
```

### Step 3 — Hot-set Freshness
```bash
stat /var/www/hermes/data/hotset.json | grep Modify
```

### Step 4 — Pipeline Log
```bash
tail -30 /root/.hermes/logs/pipeline.log
```

### Lock Contention Patterns

**Pattern A — fcntl lock persists after kill:**
Lock file left behind when process killed. Fix: `rm /tmp/hermes-pipeline.lock`

**Pattern B — FileLock three-way race:**
Timer fires → decider_run starts → FileLock held → BLOCKS subsequent runs.
Fix: Use fcntl locks instead of FileLock.

**Pattern C — Pipeline fires 10-min steps every minute:**
The `every_10` guard was accidentally removed from `run_pipeline.py`.
```bash
grep -n "minute % 10\|every_10\|STEPS_EVERY" /root/.hermes/scripts/run_pipeline.py
```

---

## 3. Known Bug Patterns

### Bug 13 — smoke_test no_flapping false alarm (2026-05-16)

**Symptom:** smoke_test FAIL: "Pipeline flapping: 60 cycles in last 60min (>55 threshold)"
but pipeline is NOT flapping — every cycle completes cleanly.

**Root cause:** Threshold `> 55` is too low. A healthy 1-cycle-per-minute pipeline
produces exactly 60 cycles per hour. The check flags a fully healthy pipeline every time.

**Fix in smoke_test.py `check_no_flapping()`:** Change `> 55` to `> 65`.

**Diagnosis:**
```bash
journalctl -u hermes-pipeline --since "60 minutes ago" | grep -E "Pipeline done|CRITICAL|ERROR|Restarting" | tail -30
# Should show: all "Pipeline done (LIVE)" — no errors, no restarts
```

---

### Bug 14 — Prices stale but no lock (2026-05-16)

**Symptom:** smoke_test FAIL: "Prices stale: 207s old" but no pipeline lock.
Pipeline is cycling normally.

**Root cause:** Price_collector service may be lagging or dead. NOT a pipeline lock issue.

**Fix:**
```bash
systemctl status hermes-price-collector.service
journalctl -u hermes-price-collector.service --since "5 minutes ago" | tail -20
sudo systemctl restart hermes-price-collector.service
```

---

### Bug 17 — Lock fd not closed causes persistent stale lock (2026-05-17)

**Symptom:** `pipeline_not_stuck` and `stale_locks` FAIL alternately — sometimes PASS,
sometimes "53min old lock, no holder". Lock file mtime advances ~60s each pipeline cycle.
Pipeline itself is healthy.

**Root cause (Linux/POSIX fcntl behavior):**

`run_pipeline.py` acquired an `flock` lock on `/tmp/hermes-pipeline.lock` but never called
`os.close(lock_fd)`. Since `signals_runner` is forked via `run_bg()` with
`start_new_session=True`, the lock fd is duplicated into the child via `fork()`.
Closing the PARENT's fd releases the flock when the reference count hits zero — but since
the child held a copy, the lock was effectively held for the full pipeline duration (~60s).

The stale mtime reflects when the file was CREATED (first acquire with `os.O_CREAT`), not
when the lock was acquired. mtime does not update on lock acquire-only. This made the lock
appear old even when legitimately held by a live process.

**The fix** (applied 2026-05-17 to `run_pipeline.py:176`):
```python
lock_fd = os.open(LOCK, os.O_CREAT | os.O_RDWR)
fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
os.close(lock_fd)  # ← releases the fcntl advisory lock immediately
# ... then fork signals_runner as a background process ...
```

**Key insight:** The lock file on disk persists (next run reuses via `os.O_CREAT`), but the
advisory `flock` is released immediately. The lock file mtime reflects FILE creation, not
lock acquisition. By closing the fd immediately, no process holds the lock, and subsequent
pipeline runs can acquire it cleanly.

**Pattern to avoid:** Do NOT hold an flock fd across a fork without closing it in the
parent immediately. Always close after acquiring if you don't need the fd for the duration.
The lock file on disk is for subsequent runs to find via `O_CREAT` — it is NOT what's being
locked; the flock is the actual inter-process mutex.

**Verification after fix:**
```bash
python3 /root/.hermes/scripts/smoke_test.py
# Should always PASS — no more stale lock false positives
tail /root/.hermes/logs/pipeline.log
```

---

### Bug 18 — Type=oneshot services always report "inactive" (2026-05-17)

**Symptom:** `trading_timers` check FAILS with `hermes-pump-hunter.service=inactive` even
though the service runs successfully every minute (status=0/SUCCESS in journal).

### Bug 19 — Pipeline/price_collector race causes stale price_history in signals (2026-05-18)

**Symptom:** zscore-pump and rs report "stale price_history" for MORPHO/SNX/UMA simultaneously.
All tokens show identical last_ts — a global timing gap, not token-specific.

**Root cause:** price_collector writes price_history to signals_hermes.db FIRST (lines 2148-2153),
then does expensive Binance candle backfills (~90s). signals_runner fires in the same timer
cycle and races against the backfill. Last committed write is 60-90s old → fails 120s gate.

**Fix A:** signals_runner must wait for price_collector to complete before scanning DB.
**Fix B:** `_force_fresh_atr()` line 1396: change `if atr is None and stale_cached_atr is None:`
to `if atr is None:` — Binance fallback fires even when stale cache exists but HL failed,
preventing `_collect_atr_updates` from skipping tokens with no ATR.

See `references/price-history-race-2026-05-18.md`.

## Bug 20 — price_collector Type=oneshot overlap crash: "database is locked" (2026-05-27)

**Symptom:** All signals report "stale price_history (last ts X), skipping" for ALL tokens
simultaneously. hotset stays empty. Pipeline runs normally but decider approves nothing.
journalctl shows repeated:
```
sqlite3.OperationalError: database is locked
hermes-price-collector.service: Failed with result 'exit-code'.
```

**Root cause:** `hermes-price-collector.service` is `Type=oneshot` but runtime is ~100s.
Timer (`hermes-price-collector.timer`) fires every 60s. Since oneshot exits after each run,
next timer fires before previous run finished → two instances run simultaneously →
both try `INSERT OR REPLACE` on signals_hermes.db → second one hits "database is locked" →
crashes → price data goes stale → all signals skip → zero trades.

**Cascading effect:**
1. price_collector crashes → price_history goes stale
2. All signal scripts check `if (now - most_recent_ts) > 120` → every token skipped
3. signal_compactor gets 0 signals → hotset stays `[]`
4. decider_run approves nothing → no trades

Blacklist optimization — `_aggregate_tf` skip (2026-05-28): Adding blacklist filter to `save_prices()` reduced tokens from ~190 → ~92, runtime from 100s+ → ~30s. But `_aggregate_tf` still iterated over ALL 171 tokens (including ~79 blacklisted) firing ~5 queries × 4 TFs = ~2,600 wasted queries/run. Two-phase fix applied to `price_collector.py`:

Phase 1 — filter `last_closed_dict` before token loop:
```python
skip = SHORT_BLACKLIST | LONG_BLACKLIST
last_closed_dict = {k: v for k, v in last_closed_dict.items() if k not in skip}
```

Phase 2 — filter `dev_rows` before writing developing candles:
```python
dev_rows = [row for row in dev_rows if row[0] not in skip]
```

Result: ~2,600 eliminated queries per run. candles.db stats: 3.4GB, 865K pages, 53 free pages (0.006% — minimal fragmentation, VACUUM won't meaningfully shrink). Tables: candles_5m=17.5M, candles_1m=10M, candles_15m=820K, candles_1h=270K, candles_4h=82K. 171 unique tokens in candles.db. Indexes already optimal (`token, ts DESC`).

**Root cause of residual slowness after blacklist fix (Bug 20d — 2026-05-28):** `candles_5m GROUP BY` alone takes **6.9s**. This is a `MAX(ts) FROM candles_5m WHERE is_closed=1 GROUP BY token` across 17.5M rows. The `idx_candles_5m_ts(token, ts DESC)` index does not help because `is_closed=1` filter is not indexed — SQLite does a full table scan. Same pattern on all 3 remaining TFs. No VACUUM or index tuning needed (minimal free pages).

**Fix:** Add partial index per TF:
```sql
CREATE INDEX IF NOT EXISTS idx_candles_5m_closed ON candles_5m(token, ts) WHERE is_closed=1;
-- Same for candles_15m, candles_1h if they show similar slowdown
```

Measured phase timings (2026-05-28):
```
hype_cache fetch:         0.1s
upsert_prices (230 rows): 5.7s   ← signals_hermes.db write (1.25GB)
price_history GROUP BY:   1.3s   ← 15.7M rows, fast
candles_5m GROUP BY:      6.9s   ← 17.5M rows — SLOWEST (is_closed not indexed)
candles_15m GROUP BY:    0.6s
candles_1h GROUP BY:      0.1s
─────────────────────────────────
TOTAL aggregation setup:  8.3s
```

**Remaining issue after blacklist fix:** Timer still at 1min. Multiple concurrent aggregators still cause pile-up (see Section 4 below). Next fix: change `OnUnitActiveSec=2min` on `hermes-price-collector.timer`.

### Bug 20c — 4h candle aggregation disabled (2026-05-28)

**Decision:** `candles_4h` table is written by `price_collector` but USED BY ZERO active trading signals.

Active signal TF usage (from live signals.json + signal registry):
- `mtp_zscore_long/short` (51 live signals): **price_history only**, no candles
- `support_resistance` (160 live signals): **price_history only**, no candles
- `zscore_pump_long/short`: **price_history only**, no candles

Only `guppy.py` reads `candles_4h`, but guppy signals are not in the live hot-set.

**Disabled 2026-05-28:** Removed `(14400, 'candles_4h')` from `_aggregate_tf` loop in `price_collector.py`.
Now aggregates only 3 TFs: `candles_5m` (17.5M rows), `candles_15m` (820K rows), `candles_1h` (270K rows).
Expected improvement: ~25% less aggregation time, candles.db won't grow 4h data further.

**Note:** Do NOT confuse `candles_4h` (candle data for guppy signals) with the `4h-regime-scanner.timer` (regime classification). The regime scanner is independent and still runs.

### Bug 21b — HL API wallet revoked: market_close error treated as success (2026-06-18)

**Symptom:** Guardian detects breach, fires `close_position_hl()`, `market_close` returns API error, but guardian logs `[PASS]` and treats the close as successful. Position is left open on HL but guardian never retries. Signal compactor continuously re-queues the token (closing marker not set), but position never closes.

**Root cause:** HL wallet was revoked/replaced. API calls return:
```
{'status': 'err', 'response': 'User or API Wallet 0x5ab4ac1b62a255284b54230b980aba66d882d80a does not exist.'}
```
But `hl-sync-guardian.py` `_check_and_close_breached_trades()` logs this as PASS and continues. The error is treated as a successful close.

**Cascading failure chain:**
1. `market_close` fails (API auth invalid) — no closing order sent to HL
2. Guardian logs `[PASS]` — closing marker NEVER set in `guardian-closing-markers.json`
3. Next cycle: position still on HL, guardian reconciles it back into DB
4. `SELF-CLOSE` checks again — wrong TP/SL computed (guardian_tp=1.926 vs correct TP=1.884)
5. Price hasn't breached wrong TP → no retry
6. Guardian marks trade as " reconciled from HL" every 60s — infinite loop
7. Position stays open, bleeding with 5x leverage

**Key evidence from logs:**
```
17:39:18 [WARN] [SELF-CLOSE] MORPHO BREACH (SHORT): guardian_tp (px=1.92165 <= tp=2.0038638)
17:39:18 [INFO] market_close returned: {'status': 'err', 'response': 'User or API Wallet ... does not exist.'}
17:39:18 [PASS] [SELF-CLOSE] MORPHO market close OK    ← BUG: error treated as success
17:39:54 [FAIL] No HL close fills found for MORPHO after 6 polls (30s)
```
Guardian log: `/root/.hermes/logs/sync-guardian.log` (not `/var/www/hermes/data/guardian.log`).

**Diagnostic:**
```bash
# Test if HL API wallet is valid
python3 -c "
import sys; sys.path.insert(0,'/root/.hermes/scripts')
from hyperliquid_exchange import get_exchange
ex = get_exchange()
print(ex.exchange.account_address)
"

# Check guardian closing markers
cat /root/.hermes/data/guardian-closing-markers.json
```

**Fix:** Restore valid HL API wallet credentials. Verify with:
```bash
python3 -c "
import sys; sys.path.insert(0,'/root/.hermes/scripts')
from hyperliquid_exchange import place_order
# If wallet invalid: {'success': False, 'message': 'does not exist'}
# If wallet valid: order goes through
"
```

### Bug 21c — accel-300 fires SHORT on counter-regime data (price above EMA300)

**Symptom:** `accel-300-,rs-s-broken` or `accel-300-,rs-r74` fires SHORT for tokens trading consistently ABOVE EMA300. Confluence passes (2 unique signal types: `accel_300` + `rs`), so trade executes. Trade loses.

**Root cause:** `signals_hermes.db` `price_history` table has gap periods where no entries exist for specific tokens. When `accel_300.py` runs during a gap, it reads stale data and computes a phantom negative `gap_pct`. The signal fires with `value` showing the RS signal's confidence score (not a valid gap_pct) — evidence of merged signal data corruption in the DB.

**Confirmed cases:**
- SKY SHORT at 20:13 EDT: price was +0.82% above EMA300 (HL API verified), but `accel-300-` fired SHORT
- SKY `price_history` has a 33-minute gap (22:50–23:23 UTC on 2026-06-18), exactly covering the signal execution window
- XMR SHORT: `value=-0.1414` (gap_pct), price at signal time unknown but XMR had been above EMA300

**Why confluence doesn't catch it:** The signal compactor's `NON_DIRECTIONAL_PREFIXES` does NOT include `accel-300`. The `accel-300+` and `accel-300-` are treated as genuinely directional. But when price_history has a gap, `accel-300-` is reading stale data and the direction is meaningless.

**Fix:** `accel_300.py` has a bar-to-bar gap guard (lines 189–198) that returns `[]` on gap detection. But if the gap is in `price_history` itself (no rows returned for the lookback window), not in bar-to-bar spacing, the guard doesn't fire. Need to add a check: if the lookback window has fewer than `lookback - 5` rows, treat as insufficient data and return `[]`.

**Diagnostic:**
```bash
# Check price_history completeness for a token
python3 -c "
import sqlite3, time
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
token = 'SKY'
c.execute('SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM price_history WHERE token=?', (token,))
cnt, mn, mx = c.fetchone()
now = time.time()
print(f'{token}: {cnt} rows, age={(now-mx)/60:.0f}min, span={(mx-mn)/3600:.1f}h')
# If span < 5h but cnt > 10000: data compressed/gapped
"
```

### Bug 21 — HL SDK IndexError breaks all trading (2026-05-30)

**Symptom:** Hot-set has strong signals but no new trades open. `mirror_open()` fails silently.
Decider_run fires every cycle, calls `brain.py` for each hot-set token, but every call fails.
Guardian shows `HL returned empty` for days.

**Root cause (wallet revocation — 2026-06-18):** The HL wallet was revoked/replaced. New credentials
were in `.secrets.local` but `hyperliquid_exchange.py` line 24 explicitly filtered out `SIGNING_WALLET_ADDRESS`
from the secrets load, then hardcoded the old address. `mirror_open` returned `{'success': False,
'message': 'User or API Wallet 0x... does not exist.'}` — error went to stdout, not stderr, so
decider_run saw `RC=1` with empty stderr.

**Fix (2026-06-18):**
1. `.secrets.local` — already had correct values (just being ignored)
2. Remove `SIGNING_WALLET_ADDRESS` from filter blocklist at `hyperliquid_exchange.py` line ~24
3. Change hardcoded address to `globals().get("SIGNING_WALLET_ADDRESS", "")` at line ~28

**Diagnostic — first thing to try:**
```python
python3 -c "
import sys; sys.path.insert(0,'/root/.hermes/scripts')
from hyperliquid_exchange import mirror_open
r = mirror_open('ONDO', 'SHORT', 0.35, leverage=5)
print(r)
"
# {'success': True} = wallet working
# {'success': False, 'message': 'does not exist'} = wallet revoked/invalid
```

**See also:** `references/hl-wallet-revoked-2026-06-18.md`

**Symptom:** Hot-set has strong signals (SKY SHORT 80%, FET LONG 82%, BCH LONG 76%, ADA LONG 80%, GALA LONG 82%) but no new trades open. Decider_run fires every cycle, calls `mirror_open()` for SKY, but `get_exchange()` → `Exchange()` → `Info.__init__` crashes with `IndexError: list index out of range`. Trade never reaches HL. Next cycle tries again — same failure. Infinite retry loop.

**Root cause:** HL changed their `/info` API — `meta` endpoint returns `{"universe": [...], "marginTables": [...], "collateralToken": ...}` with no `tokens` key. SDK's `Info.__init__` does `spot_meta["tokens"][base]` and crashes. All HL SDK communication is dead.

**Impact:**
- `get_open_hype_positions_curl()` → returns `{}` (empty) — guardian can't see positions
- `place_order()` → crashes at `get_exchange()` → REST fallback hits 422 at nonce endpoint
- `profit_monster` → sees 0 positions in profit range (prices go stale)
- `sync_pnl_from_hype` → fails with `float - str` type error (prices.json has string values)

**Fix applied (position reading):** `hyperliquid_exchange.py` `get_open_hype_positions_curl()` — direct REST fallback using `clearinghouseState` endpoint (no SDK needed). Verified working: PEOPLE/MERL/IP/LINEA all return correctly.

**Fix attempted (trading — FAILS):** `place_order()` REST fallback builds order action + signs with `sign_l1_action()` (works) but nonce endpoint returns 422 to plain `requests.post()`. SDK's internal `API.post()` uses a session that plain requests doesn't replicate.

**Recovery path:** 1) HL fixes nonce endpoint, 2) SDK gets updated, or 3) patch `/usr/local/lib/python3.12/dist-packages/hyperliquid/info.py` locally (pip reinstall wipes it). For trading to resume, one of these must happen.

**Verification:**
```bash
cd /root/.hermes/scripts && python3 -c "
from hyperliquid_exchange import get_open_hype_positions_curl
pos = get_open_hype_positions_curl()
for coin, data in pos.items():
    print(f'{coin}: {data}')
"
# Should show: PEOPLE, MERL, IP, LINEA with entry_px and unrealized_pnl
# If empty → IndexError still in effect
```

**Decision:** `candles_4h` table is written by `price_collector` but USED BY ZERO active trading signals.

Active signal TF usage (from live signals.json + signal registry):
- `mtp_zscore_long/short` (51 live signals): **price_history only**, no candles
- `support_resistance` (160 live signals): **price_history only**, no candles
- `zscore_pump_long/short`: **price_history only**, no candles

Only `guppy.py` reads `candles_4h`, but guppy signals are not in the live hot-set.

**Disabled 2026-05-28:** Removed `(14400, 'candles_4h')` from `_aggregate_tf` loop in `price_collector.py`.
Now aggregates only 3 TFs: `candles_5m` (17.5M rows), `candles_15m` (820K rows), `candles_1h` (270K rows).

Expected improvement: ~25% less aggregation time, candles.db won't grow 4h data further.

**Note:** Do NOT confuse `candles_4h` (candle data for guppy signals) with the `4h-regime-scanner.timer` (regime classification). The regime scanner is independent and still runs.

### Bug 20b — Concurrent candle aggregator pile-up (2026-05-28)

price_collector is NOT the only aggregator touching candles.db and signals_hermes.db simultaneously:

| Script | Timer | Target DBs |
|--------|-------|-----------|
| `price_collector.py` | hermes-price-collector.timer (1min) | signals_hermes.db + candles.db |
| `_aggregate_1m.py` | hermes-1m-candle.timer (1min) | signals_hermes.db + candles.db |
| `_aggregate_5m.py` | hermes-5m-candle.timer (5min) | signals_hermes.db + candles.db |

All three connect with `PRAGMA journal_mode=WAL`. When they overlap, WAL mode causes writers to block each other. Any one holding a write transaction will cause "database is locked" in the others.

**When to suspect this:** price_collector exits cleanly in ~30s when run alone but times out or hits "database is locked" when run under systemd with all timers active.

**Fix:** Mask competing timers during price_collector runs, or increase price_collector interval to 2min so runs don't overlap:
```bash
systemctl mask hermes-1m-candle.timer hermes-5m-candle.timer
# Or change price_collector timer:
sed -i 's/OnUnitActiveSec=1min/OnUnitActiveSec=2min/' /etc/systemd/system/hermes-price-collector.timer
systemctl daemon-reload
systemctl restart hermes-price-collector.timer
```

Also apply blacklist filter to `_aggregate_1m.py` and `_aggregate_5m.py` (same pattern as price_collector):
```python
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
skip = SHORT_BLACKLIST | LONG_BLACKLIST
# In the token iteration loop:
if token in skip:
    continue
```

### Bug 18

```bash
# Step 1: Check what the timer file claims
systemctl cat hermes-pipeline.timer | grep OnCalendar

# Step 2: Check internal gating in script
grep -n "minute % 10\|every_10\|STEPS_EVERY" /root/.hermes/scripts/run_pipeline.py

# Step 3: Verify actual recent executions
journalctl -u hermes-pipeline.service --since "1 hour ago" | grep Pipeline

# Step 4: Check pipeline log timestamp spacing
tail -20 /root/.hermes/logs/pipeline.log
```

---

## References

See the following reference skills for detailed sub-process debugging:
- `references/hl-position-api-return-shapes.md` — **CRITICAL**: `get_open_hype_positions_curl()` returns `{coin: {size, direction, entry_px, unrealized_pnl, leverage}}` (a DICT), NOT a list of dicts. Calling `p.get("token")` on it throws `'str' object has no attribute 'get'`. WASP had this bug (wasp.py:777) until patched 2026-07-13. Use `.keys()` for token names, `.items()` for records. `entry_px` can be None (HL returns null) — never coerce to 0.
- **NEW 2026-07-14: `references/compactor-dead-signal-flood-2026-07-14.md`** — When the pipeline is "running" (candle_predictor + signals_runner + price_collector all alive) but hotset.json stays `{"hotset":[], "compaction_cycle": <inflated>}`: the compactor is dead, signals are stranded, and the candle_predictor is amplifying them with no dedup. Includes schema correction for `signals.json` (it's a dict, not a list).
- "signal_compactor.py line 843: `c.execute(sql, token, direction, side, amount, price, lev, strategy, server, now, now)` — sqlite3.Cursor.execute() takes at most 2 args (sql + params sequence), called with 11 positional args. TypeError. Crashes every run. Hot-set never compacts. PRIMARY pipeline blocker. Fix: c.execute(sql, (token, direction, side, amount, price, lev, strategy, server, now, now))"
- [references/pipeline-investigation.md](references/pipeline-investigation.md) — investigative approach for empty/missing data sources
- [references/post-reboot-health-check.md](references/post-reboot-health-check.md) — correct post-reboot verification sequence
- [references/rs-price-source-verification-2026-06-08.md](references/rs-price-source-verification-2026-06-08.md) — confirmed RS uses price_history (not candles.db), 143 stale tokens from HL universe gap, blacklist guards verified correct
- [references/guardian-duplicate-orphan-trades-2026-06-12.md](references/guardian-duplicate-orphan-trades-2026-06-12.md) — 5 compounding bugs causing duplicate ADA/MET trades; Step 6 + pending retry state machine, `_CLOSED_HL_COINS` invariants