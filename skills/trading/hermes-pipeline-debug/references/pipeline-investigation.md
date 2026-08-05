---
name: pipeline-investigation
description: Investigative approach when pipeline data sources are empty, missing, or unexpected. Use when standard queries return no data — discover what's actually there and adapt.
category: trading
author: Hermes
created: 2026-04-12
---

# Pipeline Investigation

Use when a pipeline review or data audit hits empty data sources. The key insight: **empty is a finding, not a stop sign**.

## When to Use

- Standard signals DB returns 0 rows
- Expected tables don't exist
- Data in a different location than documented
- Need to pivot approach mid-investigation

## Methodology

### Step 1 — Verify the Right File

**CRITICAL: Multiple candidate DBs exist — check size and tables, don't assume paths.**

```
# Check all SQLite DBs in project (note sizes — 0 bytes = empty/wrong DB)
ls -la /root/.hermes/*.db /root/.hermes/data/*.db /root/.hermes/scripts/*.db 2>/dev/null

# The signals DB is NOT at scripts/signals.db (it's 0 bytes, a placeholder)
# The REAL signals DB is derived from paths.py:
#   RUNTIME_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
#   HERMES_DATA = /root/.hermes/data
#   → actual path: /root/.hermes/data/signals_hermes_runtime.db

# Always verify via paths.py when in doubt:
grep "RUNTIME_DB\|HERMES_DATA" /root/.hermes/scripts/paths.py

# Check the actual signals DB
sqlite3 /root/.hermes/data/signals_hermes_runtime.db ".tables"
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT COUNT(*) FROM signals"

# Check PostgreSQL tables
psql brain -U postgres -h /var/run/postgresql -c "\\dt"
```

### Step 2 — Probe for Active Data

```
# Is predictions.db active? Check most recent entry
sqlite3 /root/.hermes/data/predictions.db "SELECT MAX(created_at) FROM predictions"

# Check mtime of all data files — newest = most active
ls -lat /root/.hermes/data/*.db /root/.hermes/data/*.json | head -20
```

### Step 3 — Check What the Pipeline is ACTUALLY Writing

```
# The most recently modified file is likely the active one
# predictions.db at 16MB = active output (128K+ rows)
# signals_hermes_runtime.db at 86KB with 0 rows = dead

# Also check JSON archives
ls -la /root/.hermes/data/closed_trades_archive.json
python3 -c "import json; d=json.load(open(f)); print(len(d), 'rows')"
```

### Step 4 — Check Pipeline Processes

```
ps aux | grep -E "signal_gen|decider|guardian|ai_decider|predictor" | grep -v grep
```

If no relevant processes running, signal generation may be disabled.

### Step 5 — Document Discrepancy

When you find the data is somewhere unexpected:
- Note the actual active DB path vs documented path
- Update brain/trading.md with correction
- Report the discrepancy as a HIGH finding

## Key Lesson

**The skill's documented DB path was wrong.** This happens frequently when:
- Pipeline was refactored but docs weren't updated
- Multiple DBs exist (runtime vs archive)
- DB path changed in a config update

**Never assume the documented path is correct.** Always verify existence + row count + recency.

## Critical Pattern: Data Type vs Data Presence

**A data source can be populated but completely wrong for your purpose.**

Symptom: Table has rows, queries succeed, but indicator output is all zeros / no crossovers / no signals.

Example: `price_history` table in `signals_hermes_runtime.db` has ~118 rows/minute — looks active. But it stores `allMids` snapshots (orderbook mid-price), NOT Hyperliquid trade ticks. Each row is one mid-price per token per snapshot. When built into 15m candles: every OHLCV bar = `open=high=low=close` (one price, no H-L range). MACD on a flat candle line = no crossovers = no signals.

Diagnosis:
```python
# Check what price_history actually stores
import sqlite3
sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db').execute(
    "SELECT sql FROM sqlite_master WHERE name='price_history'"
).fetchone()

# Check schema — if no 'size' or 'side' column, it's orderbook data not trades
# Check row count per minute to confirm density
```

Fix: Use `candles/*.json` (Binance OHLCV) for candle-based indicators. `price_history` is for orderbook analysis only.

**Rule: Before assuming the indicator logic is broken, verify the data type matches what the indicator needs.** Trade ticks → volume/price indicators. OHLCV candles → MACD/RSI/EMA. Orderbook snapshots → spread/mid analysis.

## Pattern: Warmup Mismatch with Short Data

**Symptom:** Indicator has no crossovers despite seemingly adequate data. `h_4h` or `s_4h` is `None` for every crossing.

Cause: A conservative warmup floor (e.g., `warmup=98` for 90-day data) is hardcoded as the loop start. But the actual `PrecomputedMACD.warmup = slow - 1 + signal` (e.g., slow=65, sig=15 → warmup=79). With short candle files (500 Binance candles ≈ 31 4H bars), `i // bars_per_4h` maps every index past valid 4H data.

Fix: Use `max(floor_warmup, pm_15m.warmup)` — the actual per-config warmup, not the conservative floor. The conservative floor was designed for 90-day data with ~5,400 4H candles; it is too aggressive for 31-candle datasets.

## Pattern: Counter-Regime Signals Hard-Blocked Instead of Gracefully De-Escalating

**Symptom:** Counter-regime signals disappear from hot-set without passing through de-escalation. Confidence drops to 0 and signal is marked executed immediately, blocking the slot.

**Root cause:** Two-layer hard-blocks:
1. `ai_decider.py` line ~2696: `if direction opposes regime: confidence = 0` — kills signal before it reaches decider
2. `decider_run.py` Cases 2/3/4: `mark_signal_executed(token, direction)` called, then `continue` — exits signal from hot-set without de-escalation path

**Correct pattern:** Penalize but don't hard-block. Signal should stay alive and exit via the 5-cycle de-escalation mechanism (APPROVED → PENDING via counter-signals in ai_decider RULE 1).

**Fix in ai_decider.py:**
```python
# WRONG (hard-block):
if direction opposes regime:
    confidence = 0

# RIGHT (graceful penalty — signal stays alive):
if direction opposes regime:
    penalty = 10 + int(regime_confidence * 15)
    escalation = min(survival_rounds * 2, 10)  # reward veterans
    confidence = max(0, confidence - penalty + escalation)
```

**Fix in decider_run.py Cases 2/3/4:**
```python
# WRONG (hard-block — marks executed, blocks slot):
if weak_condition:
    mark_signal_executed(token, direction)  # DON'T
    continue

# RIGHT (graceful — signal stays APPROVED, de-escalates via 5-cycle counter-signal rule):
if weak_condition:
    continue  # No mark_signal_executed — let de-escalation handle it
```

**BLACKLIST hard-blocks are legitimate** (delisted/unsafe tokens). Only counter-regime/weak-regime signals should be graceful.

**Verification:**
```bash
grep -n "mark_signal_executed" /root/.hermes/scripts/decider_run.py
# Cases 0,1 are legitimate (delisted, blindspot). Cases 2,3,4 should NOT appear.
```

## Pattern: Hot-Set Iteration Order Bypasses Survival Priority

**Symptom:** Veterans (high survival_round) get rate-limited before being approved, while fresh signals steal their slots. TIA(r6) waiting while ETC(r0) executes.

**Root cause:** Hot-set was iterated in JSON array order:
```python
# WRONG:
for hot_sig in hotset:  # unsorted
    approve(hot_sig)  # first in array wins, not most veteran
```

**Correct pattern:** Sort by survival_round DESC, confidence DESC before iteration:
```python
# RIGHT:
hotset_sorted = sorted(hotset,
    key=lambda s: (-s.get('survival_round', 0), -s.get('confidence', 0)))
for hot_sig in hotset_sorted:
    approve(hot_sig)  # most veteran first — rate limit hits fresh signals, not veterans
```

**Also:** Use `survival_round` (from hotset.json), NOT `review_count` or `compact_rounds` (from DB) for iteration priority. The JSON is the canonical source.

**Verification:**
```bash
# Check hot-set iteration order in signals.log:
grep "HOT-SET iteration order" /var/www/hermes/logs/signals.log | tail -5
# Should show r6, r4, r4, r3, r0... not random JSON order
```

## Pattern: _exec_score Tuple Tiebreaker Returns Same Value as Primary

**Symptom:** Execution tiebreaker always picks the wrong signal — two signals with identical confidence get sorted randomly instead of by survival rounds.

**Root cause:** `_exec_score` returned `(conf, conf * speed_mult * z_mult)` — both tuple elements are identical numbers:
```python
# WRONG — both elements are the same value (conf):
def _exec_score(...):
    return (final_confidence, final_confidence * speed_mult * z_mult)
```

**Fix:**
```python
# RIGHT — primary=confidence, tiebreaker=survival rounds (battle-tested over fresh-fast):
def _exec_score(hot_sig, final_confidence, ...):
    hot_rounds = hot_sig.get('survival_round', 0)
    return (final_confidence, hot_rounds)
```

**Why hot_rounds not speed/z?** Speed and z-score favor fresh high-volatility signals. Survival rounds favor signals that have proven themselves through market volatility. T's preference: veterans over fresh-fast.

## Pattern: Gatekeeper Script Never Runs Automatically (Pipeline Deadlock)

**Symptom:** Signals are APPROVED by signal_compactor (compact_rounds increments) but never graduate to trades. DB shows: 27 APPROVED signals with `hot_cycle_count=0`. The guardian and hype-sync gates both check `hot_cycle_count >= 1` before allowing `mirror_open`.

**Root cause:** Two components share responsibility for the hot-set graduation gate:

1. `hype-sync.py` — intended to increment `hot_cycle_count` for APPROVED signals
2. `hl-sync-guardian.py` — the actual execution path, checks `hot_cycle_count >= 1` at line ~1902
3. `signal_compactor.py` (every 5 min via systemd timer) — APPROVES signals and increments `compact_rounds` but does NOT increment `hot_cycle_count`

The problem: `hype-sync.py` has NO systemd timer. It was written to do the `hot_cycle_count` increment but never runs automatically. The only scheduled component (`signal_compactor.py`) does everything EXCEPT update `hot_cycle_count`. Result: the gate is permanently closed.

**Diagnosis:**
```bash
# Check if hype-sync has a systemd timer
systemctl list-timers | grep hype
# Expected: NOTHING — this is the bug

# Check signal state in DB
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT hot_cycle_count, compact_rounds, decision, COUNT(*) \
   FROM signals GROUP BY hot_cycle_count, compact_rounds, decision"
# EXPECTED: hot_cycle_count >= 1 for all APPROVED signals
# ACTUAL: 27 APPROVED with hot_cycle_count=0, compact_rounds=1

# Confirm hype-sync gate in guardian
grep -n "hot_cycle_count" /root/.hermes/scripts/hl-sync-guardian.py
# Line ~1902: WHERE hot_cycle_count >= 1 — this is the blocker
```

**Fix in signal_compactor.py:** After the APPROVED UPDATE, also sync `hot_cycle_count`:
```python
if approved_ids:
    placeholders_hcc = ','.join(['?' for _ in approved_ids])
    c.execute(f"""
        UPDATE signals
        SET hot_cycle_count = COALESCE(hot_cycle_count, 0) + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id IN ({placeholders_hcc})
    """, approved_ids)
```
This makes `signal_compactor.py` the authoritative updater (it already runs every 5 min via systemd timer).

**Also:** Add a systemd timer for `hype-sync.py` as a belt-and-suspenders approach.

---

## Pattern: trades.json Uses "open" Key Not "open_trades"

**Symptom:** Script tries `trades['open_trades']` and gets KeyError. The file has `"open"` and `"closed"` keys, not `"open_trades"`.

**Schema:**
```python
trades = {
    "updated": unix_ts,
    "open_count": int,      # e.g., 9
    "closed_count": int,    # e.g., 31
    "open": [...],          # list of open position dicts
    "closed": [...]
}
```

Also: `sync-guardian` may show 10/10 positions while trades.json shows 9 — the 10th is a Hyperliquid-only position not tracked in trades.json.

## Pattern: Scoring Function Scores 0 for Normal Market Conditions (Silent Signal Famine)

**Symptom:** signal_gen.py runs without errors but produces 0 signals. All source functions (pattern_scanner, fast_momentum, mtf_momentum, etc.) execute and write to DB, but `compute_score()` returns low values that never hit ENTRY_THRESHOLD. Historical signals exist (proof the pipeline worked before), but new signals stop appearing.

**Root cause:** A percentile scoring function gates signals to near-zero under normal conditions.

**Example:** `pct_long_score_fn` in signal_gen.py:
```python
def pct_long_score_fn(pct_long):
    if pct_long >= 65: return 0      # rally → reject
    if pct_long >= 50: return 0      # NORMAL MARKET → 0 points!
    if pct_long >= 20: return ...     # dump → moderate points
```

Most tokens sit at pct_long=40-65 (normal conditions). The function gives them 0 points, making the maximum achievable `compute_score()` too low to hit the entry threshold.

**Discovery method:**
1. Run `timeout 60 python3 scripts/signal_gen.py` → `=== Done: 0 signals`
2. Search all signal sources: `grep -n "_run_.*signal" signal_gen.py | grep -v "#"` — all source functions exist
3. `SELECT source, COUNT(*) FROM signals GROUP BY source ORDER BY COUNT DESC` — signals ARE being written
4. Trace `compute_score()` manually for top-scoring tokens → score stays 0-45, threshold is 60
5. Find the bottleneck: `grep -A20 "def pct_long_score_fn" signal_gen.py` → pct_long >= 50 returns 0

**Fix:**
```python
# WRONG — scores 0 for pct_long 50-65 (most tokens in normal markets):
if pct_long >= 50: return 0

# RIGHT — linear range for normal market conditions:
if pct_long >= 65: return 0       # rally
elif pct_long >= 50: return 20    # slightly bullish (was 0)
elif pct_long >= 35: return 40     # neutral
elif pct_long >= 20: return 60    # oversold
```

**Also check:** ENTRY_THRESHOLD may have been raised from 50→60 during a refactor. After fixing the scoring function, lower it back to 50 if scores are still 45-55.

**Also check:** quiet phase gate may be too strict (e.g., `pct_long <= 40`). Tokens with pct_long=43-45 get rejected. Loosen to `pct_long <= 45`.

## Pattern: `get_ohlcv_1m` Returns 7+ Day Stale Data — Fix Was Worse Than Original

**Symptom:** gap-300- fires phantom SHORT signals for tokens with no recent price action (XMR at $371 showed SHORT from gap-300-). Signal fires correctly for BTC/ETH but tokens with stale data get wrong-direction signals.

**Root cause:** Signal scripts used `get_ohlcv_1m()` from `signal_schema.py` which reads from `ohlcv_1m` table in `signals_hermes.db`. This table was 178-183 HOURS stale (7+ days). Meanwhile `candles_1m` in `candles.db` was only 0.3 hours stale. A "fix" that switches from `candles.db` to `get_ohlcv_1m` is actually WORSE.

**Data freshness hierarchy (as of 2026-04-23):**
| Source | Table | Freshness | Use For |
|--------|-------|-----------|---------|
| `signals_hermes.db` | `price_history` | **<1 min ✓** | **ONLY live signal generation** |
| `candles.db` | `candles_1m` | 0.3h | Volume (only for volume_hl_signals) |
| `candles.db` | `candles_5m` | 0.1h ✓ | R2_rev_5m (fresh) |
| `signals_hermes.db` | `ohlcv_1m` | **178h ✗** | **DO NOT USE — 7+ days stale** |

**Critical bug in `get_ohlcv_1m`:** Uses `open_time > cutoff` where `open_time` is milliseconds but `cutoff = time.time()` is seconds. This makes the comparison always TRUE for old data (ms value >> seconds value), so stale entries are NOT filtered out.

**Fix pattern (applied to all signal scripts 2026-04-23):**
```python
# WRONG — reads stale ohlcv_1m (178h old):
from signal_schema import get_ohlcv_1m
candles = get_ohlcv_1m(token, lookback_minutes=lookback)

# RIGHT — read price_history directly (fresh <1 min):
_PRICE_DB = '/root/.hermes/data/signals_hermes.db'

def _get_candles_1m(token: str, lookback: int = 400) -> list:
    conn = sqlite3.connect(_PRICE_DB, timeout=10)
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, price FROM (
            SELECT timestamp, price
            FROM price_history
            WHERE token = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ) sub
        ORDER BY timestamp ASC
    """, (token.upper(), lookback))
    rows = c.fetchall()
    conn.close()
    if not rows:
        return []
    # Freshness guard — skip if > 5 minutes old
    if (time.time() - rows[-1][0]) > 300:
        return []
    # Synthesize OHLCV from price (price = close = open = high = low)
    return [{'open_time': r[0], 'open': r[1], 'high': r[1],
             'low': r[1], 'close': r[1], 'volume': 0.0} for r in rows]
```

**Important: The `data/` subdirectory path is wrong.** Scripts under `/root/.hermes/scripts/` must use the absolute path `/root/.hermes/data/signals_hermes.db` — the `data/` subdirectory doesn't exist under `scripts/`. Using `os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', ...)` resolves to the wrong path.

**Diagnosis:**
```python
# Check ohlcv_1m freshness
import sqlite3, time
from datetime import datetime as dt
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
c.execute("SELECT token, MAX(open_time), COUNT(*) FROM ohlcv_1m GROUP BY token ORDER BY MAX(open_time) DESC LIMIT 5")
now = time.time()
for row in c.fetchall():
    age_h = (now - row[1]/1000) / 3600  # open_time is milliseconds
    print(f"{row[0]}: max_open_time={row[1]} age={age_h:.1f}h")
conn.close()

# Check price_history freshness (should be <2 min)
conn2 = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c2 = conn2.cursor()
c2.execute("SELECT token, MAX(timestamp), COUNT(*) FROM price_history GROUP BY token ORDER BY MAX(timestamp) DESC LIMIT 3")
for row in c2.fetchall():
    age_min = (now - row[1]) / 60
    print(f"{row[0]}: max_ts={dt.fromtimestamp(row[1])}, age={age_min:.1f}min")
```

**Files affected and fixed (2026-04-23):**
- gap300_signals.py, ma_cross_signals.py, ma_fast_signals.py, zscore_momentum.py, rs_signals.py, r2_trend_signals.py, macd_1m_signals.py, volume_1m_signals.py, ma300_candle_confirm_signals.py, macd_rules.py, pattern_scanner.py — all now read `price_history` directly
- volume_hl_signals.py — price from `price_history`, volume from `candles_1m` (acceptable 0.3h staleness for volume)

## Pattern: Internal Data Gaps Cause Stale Signal Firing (Unordered Bar Inserts)

**Symptom:** gap-300 fires a signal based on a cross from 9 hours ago. Signal is technically valid (cross above threshold, still widening, direction matches), but the "latest" bar in the window is 3 hours stale. Price drops before the trade executes.

**Root cause:** `price_history` receives bars out of order (not strictly timestamp-ascending). The freshness guard checks `now - rows[-1][0] < 120s` where `rows[-1]` is the last row returned by the subquery — but this is the most recently INSERTED row, not the most recent TIMESTAMP. If bars arrive late or out of order, `rows[-1].timestamp` can be hours older than `now`, yet the bar-to-bar gap check only compares adjacent rows (41 seconds) — appearing fresh.

The gap-300 signal then sees:
- Latest bar: 23:10 UTC, gap_pct=0.0549%, direction=LONG
- Gap was **collapsing** for hours (gap_pct[-2]=0.0600% > gap_pcts[-1]=0.0549%)
- But the widening check only compares against the **crossing bar** (0.0523%), not recent bars
- gap_pcts[-1]=0.0549% > 0.0523% → "still widening" → fires incorrectly

**Diagnosis:**
```python
import sqlite3, time
from datetime import datetime as dt

conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
c.execute('''
    SELECT timestamp, price FROM price_history
    WHERE token = ? AND timestamp <= ?
    ORDER BY timestamp DESC LIMIT 5
''', ('MET', signal_ts))
rows = c.fetchall()
conn.close()

now = time.time()
print(f"now = {now} = {dt.fromtimestamp(now)}")
for r in rows:
    bar_age_min = (now - r[0]) / 60
    print(f"  bar ts={r[0]} = {dt.fromtimestamp(r[0])}, age={bar_age_min:.1f}min, price={r[1]}")
```

**Fix in gap300_signals.py `_get_1m_prices`:**
```python
# After fetching rows, replace with timestamp-sorted last bar check:
rows = list(reversed(rows))
most_recent_ts = rows[-1][0]
now = time.time()
bar_age = now - most_recent_ts

# Guard A: bar-to-bar gap (existing)
for i in range(1, len(rows)):
    bar_gap = rows[i][0] - rows[i-1][0]
    ...

# Guard B: absolute bar age (NEW — catches unordered inserts)
if bar_age > 300:  # 5 minutes
    print(f"  [gap300] {token}: latest bar is {bar_age:.0f}s old, skipping")
    return []
```

**Also:** The same bug affects any signal using `price_history` with a `<= now` query. Always verify that `rows[-1].timestamp` is recent relative to `now`, not just that the bar-to-bar gap is small.

**Files affected:** gap300_signals.py, any script using `_get_1m_prices()` or equivalent timestamp-`<=now` pattern.

## Pattern: Silent Exception Swallowing in Signal Source Scripts (0 Signals)

**Symptom:** Pipeline runs without crashing, but a signal source (e.g., `volume_1m`) emits 0 signals every cycle. Pipeline log shows:
```
volume_1m get_candles EXCEPTION: 'sqlite3.Connection' object has no attribute 'fetchall'
Confluence: 0 confluence signals added
```
All other steps complete normally. The exception is silently caught and returns `[]`.

**Root cause:** `except Exception as e: print(f"...EXCEPTION: {e}"); return []` — the error is logged but execution continues as if the source had no signals. If multiple tokens fail this way, the entire signal source produces nothing.

**Common bug:** Using `conn.fetchall()` instead of `cursor.fetchall()` on a `sqlite3.Connection` object.

**Diagnosis:**
```bash
# Find all EXCEPTION lines in pipeline log
grep "EXCEPTION" /root/.hermes/logs/pipeline.log | head -20

# Find the failing script and function
grep -rn "EXCEPTION\|except Exception" /root/.hermes/scripts/volume_1m_signals.py

# Check which signal sources exist
grep -rn "def scan_\|def get_candles\|def .*signal" /root/.hermes/scripts/signal_gen.py | grep "from"

# Manually test the failing function
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from volume_1m_signals import get_candles
print(get_candles('BTC', limit=11))
"
```

**Fix:** The `except Exception` is intentional (continues scanning other tokens). Fix the underlying bug inside the try block.

**Prevention:** Add syntax-only verification step in signal source imports:
```bash
python3 -m py_compile /root/.hermes/scripts/volume_1m_signals.py && echo "Syntax OK"
```

---

## Pattern: Phantom Paper Entries — Pipeline Stall with No HL Trade

**Symptom:** `trades.json` shows an open position (e.g., `MORPHO LONG entry=1.8505`) but HL has no corresponding position. The guardian and position_manager keep trying to manage a non-existent position. Pipeline continues running but guardian behavior is erratic.

**Root cause:** A trade was recorded in paper but never executed on HL, OR was closed on HL without updating trades.json. The guardian reads trades.json as the source of truth for open positions and tries to manage entries that don't exist on-chain.

**Diagnosis:**
```bash
# Use hype-paper-sync.py — dry run first
cd /root/.hermes/scripts && python3 hype-paper-sync.py

# Expected output for phantom entry:
# Paper HL positions: 1
#   MORPHO LONG entry=1.8505
# HL open positions: 0
# MORPHO: in paper but NOT on HL → removing phantom entry
```

**Fix — dry run then apply:**
```bash
cd /root/.hermes/scripts && python3 hype-paper-sync.py --apply
```

**Post-fix verification:**
```bash
# Confirm trades.json is clean
python3 -c "
import json
t = json.load(open('/var/www/hermes/data/trades.json'))
print('Open positions:', len(t.get('open', [])))
print('Open:', [p['token'] for p in t.get('open', [])])
"
```

**If the phantom entry keeps re-appearing:** The guardian is re-inserting it from postgres. Check:
1. Kill guardian: `kill $(pgrep -f hl-sync-guardian)`
2. Check postgres: `psql brain -U postgres -h /var/run/postgresql -t -c "SELECT id, token, status FROM trades WHERE token='MORPHO' AND status='open'"`
3. If found: `UPDATE trades SET status='closed' WHERE token='MORPHO' AND status='open'`
4. Restart guardian after fixing trades.json

---

## Pattern: Regime Filter Rejects Everything When 4H Data Is Short

**Symptom:** All backtest results have `h_4h is None`, and every entry is rejected by the 4H regime filter.

Cause: The regime filter checks `if h_4h is not None and h_4h < 0: reject`. When `h_4h is None` (4H not warm yet), it falls through to the next condition — but if the next condition also rejects on `None`, valid entries are excluded.

Fix: When `h_4h is None`, treat it as "not yet positive but don't reject" — only reject if we have a valid 4H reading that is negative. The distinction: `None` means "I don't know yet", not "it's bearish".

## Additional Pattern: Stale hotset.json from Pipeline Double-Fire

**Symptom:** `hotset.json` is 30+ minutes stale. Log shows "hotset.json stale (N seconds) — blocking new approvals". The file exists but hasn't been updated since yesterday.

**Diagnosis:**
```bash
# Check modification time
stat /var/www/hermes/data/hotset.json | grep Modify

# Check for duplicate ai_decider processes
ps aux | grep ai_decider | grep -v grep

# Check the log for concurrent runs
grep "Running ai_decider" /root/.hermes/logs/pipeline.log

# Look for timestamps — if two run entries appear within minutes, that's the bug
grep "20:10.*ai_decider\|20:11.*ai_decider" /root/.hermes/logs/pipeline.log
```

**Root cause:** `run_pipeline.py` ran 10-minute steps (ai_decider) in a non-blocking loop. The systemd timer fires every 60s, but ai_decider takes 10+ minutes. A second pipeline trigger fires while the first ai_decider is still running. Two ai_decider instances race to write `hotset.json`.

**Fix:** Two-part:
1. Change to blocking `subprocess.run` for all pipeline steps
2. Add psutil process guard to skip if step already running

This is Pattern #12 in `systematic-debugging`.

## Output Template

```
PIPELINE INVESTIGATION — <date>
Expected DB: <documented path> → Found: <actual state>
Actual active DB: <path> with <N> rows

CRITICAL FINDINGS:
1. [Empty DB] signals_hermes_runtime.db has 0 rows — pipeline not writing here
2. [Active data] predictions.db has 128K rows — actual output location
3. [Directional bias] 8.6x LONG ratio discovered

Action items:
- Fix signal attribution in closed_trades_archive
- Audit candle_predictor.py DOWN prediction logic
```

## Files
- Report output: `/root/.hermes/pipeline_health_report_YYYY-MM-DD.txt`
