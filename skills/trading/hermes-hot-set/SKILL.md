---
name: hermes-hot-set
description: How Hermes picks the "best" trade from the hot-set for live execution — signal_compactor → hotset.json → decider_run → HL execution pipeline, including ranking, filtering, and approval logic.
tags: [hot-set, signal-compactor, decider-run, trade-selection, hermes-pipeline]
triggers:
  - [hot-set has 0 tokens — starvation after WR filter]
  - "all signals blocked by WR gate at signal_compactor"
  - "price_collector down → all signals report 'stale price_history' → hotset stays empty"  # Bug 20
  - "LTC SHORT: WR=33% (3 trades) blocked — wrong diagnostic path"  # 2026-05-26
  - "single source signals re firing trades"
  - "two entries for same token in hotset"
  - "MON SHORT opened twice"
  - "signals.json APPROVED has single-source but hotset.json is clean"
  - "PENDING rows getting promoted to APPROVED without confluence check"
  - "entries_count stale causing confluence bypass"
  - "signals.json shows INJ APPROVED but not in hotset.json"
  - "XRP was executed as a live trade but not in hot-set"  # 2026-05-18
  - "token executed but not in hotset.json — how did it get through?"
  - "hotset.json has entries but no live trades opening — decider_run returns 0,0"  # 2026-05-21: preserve path vs get_approved_signals disconnect
  - "only 1 unique types {mtp-zscore-} — need 2+ — hotset stays empty despite valid signals"  # 2026-05-28: confluence gate starvation
  - "accel-300 signals all blocked confluence gate 0 tokens hotset"  # 2026-06-09: pure accel-300 standalone bypass needed
  - "signals not firing no new trades confluence"  # 2026-06-09: confluence gate blocking standalone signals
  - "hot-set empty 0 tokens confluence starvation"  # 2026-06-15: RS signal collapse bug — rs-r12,rs-r8 all collapse to single 'rs' type → blocked; 200 expired single-source signals; bypass disabled; RS signals too sparse to pair with accel-300 in 5-min window
  - "accel-300 standalone bypass at conf=70 passed ALL pure accel-300 (capped at 70) → massive losses → reverted to ACCEL_300_STANDALONE_BYPASS_ENABLED=False"  # 2026-06-09
  - "confluence gate requires 2+ unique signal types — no bypass, no exceptions. Signals must always have confluence. Period."  # 2026-06-09
author: T
created: 2026-05-11
---

# Hermes Hot-Set Signal Pipeline

How a signal in `hotset.json` becomes a live trade on Hyperliquid.

## Pipeline Overview

```
Signal Script → signals_hermes_runtime.db
                        ↓
              signal_compactor.py (every 1 min)
                        ↓ writes
              /var/www/hermes/data/hotset.json
                        ↓ reads
              decider_run.py (every 1 min)
                        ↓ writes APPROVED
              signals DB (decision='APPROVED')
                        ↓
              HL order execution
```

Key files:
- `signal_compactor.py` — sole APPROVAL authority (as of 2026-04-16). Writes hotset.json.
- `decider_run.py` — reads hotset.json, enforces filters, writes APPROVED to DB. **Never writes hotset.json.**
- `hl-sync-guardian.py` — reads APPROVED signals from DB, executes on HL.

## How Signal_compactor Builds the Hot-Set

### Score Formula (signal_compactor.py:195-243)

```python
score = confidence
      × survival_bonus    (1 + cr*0.15, only if cr>0 AND age_m<5)
      × staleness_mult   max(0, 1.0 - age_m*0.2) → 0 at 5min
      × reg_mult          +50% aligned / -50% counter-regime / -50% NEUTRAL or no-data
      × source_mult       (from _get_source_weight)
      × speed_mult        +15% if speed_percentile >= 80
```

### Hot-Set Survivor Rules (signal_compactor.py)

A token enters the hot-set if:
1. Has 2+ sources (confluence requirement)
2. Final score > 0 after all multipliers
3. Not in LONG_BLACKLIST (for LONG) or SHORT_BLACKLIST (for SHORT)

Tokens that survive multiple compaction cycles get `survival_round += 1` (incremented vs. previous hot-set).

## How decider_run Picks the "Best" Trade

**Sorting (decider_run.py:921-922):**
```python
hotset_sorted = sorted(hotset,
    key=lambda s: (-s.get('survival_round', 0), -s.get('confidence', 0)))
```

- **Primary:** survival_round DESC — more cycles = proven against market volatility
- **Tiebreaker:** confidence DESC

Since most entries have survival_round=1, tiebreaker is raw confidence.

### Filters Applied to Each Token (in order)

1. **Blacklist check** — LONG_BLACKLIST / SHORT_BLACKLIST (defense-in-depth)
2. **Cooldown check** — 2+ failures in 1hr → 1hr block
3. **Open position check** — already has position → skip
4. **Already APPROVED check** — don't double-approve
5. **Overextended filter** — vel_5m > +3% blocks LONG (except bottoming+LONG)
6. **Wave-alignment multiplier** — adjusts effective confidence
7. **Counter-trend trap penalty** — z-score + regime conflict → penalty
8. **Minimum threshold** — effective_conf must be >= 55 after all adjustments

### Two-Gate Architecture: Why APPROVED ≠ hot-set

**Gate 1 — Confluence gate (signal_compactor.py ~495)**:
- Requires 2+ distinct signal source types for same token+direction
- Groups signals by token+direction within 5-min window
- Merges multiple sources into single DB row with `source='accel-300+,rs-sNNN'`
- Single-source signals (no comma in source) never pass → stay PENDING

**Gate 2 — Scoring/rank gate (signal_compactor.py ~649)**:
- Scores ALL signals passing Gate 1
- Takes TOP-10 by score → writes hotset.json
- Remaining #11+ signals stay in DB as APPROVED but not in hotset.json

**Gate 3 — Execution gate (decider_run.py ~1474)**:
- Reads _hot_tokens from hotset.json
- Iterates APPROVED signals from DB
- Only executes if token ∈ _hot_tokens
- APPROVED but not in hotset.json = permanently skipped this cycle

**The timing miss**: signals_runner runs in BACKGROUND (non-blocking). signal_compactor runs SYNCHRONOUSLY in same pipeline cycle. New signals generated by signals_runner may not appear in hotset.json until the NEXT compaction cycle. This creates a ~1-5 min lag where a signal is APPROVED but not in hotset.json.

### Two-Stage Regime Filtering (Critical — Often Misunderstood)

Stage 1 is in signal_compactor (scoring, every 1 min):
  reg_mult = 1.50 if aligned, 0.50 if counter-regime, 0.50 if NEUTRAL, 0.50 if no-data

Stage 2 is in decider_run (approval, every 1 min):
  Counter-regime: penalty = regime_conf × 0.4, capped at 30pts, with survival-round forgiveness (+2pts/round, cap 10)
  NEUTRAL: flat 10pt penalty, +2pts/survival round forgiveness (cap 6 net)
  Tokens with effective_conf < 55 after penalties are blocked.

When T asks "is regime filtering too tight?" — check the actual hot-set state first.
The system is working correctly if: hot-set has 5-20 entries, all-round=1, NEUTRAL-dominated,
and regime_5m.json shows fresh data (<15 min old) with 101/105 tokens NEUTRAL.
Do NOT blame regime filtering for normal trade volumes — verify the premise first.

> **Common misdiagnosis (2026-05-11):** Regime filtering was NOT the cause of trade sparsity.
> The WR filter became blind because archive-trades.py deleted 361 trades from PostgreSQL,
> making all tokens default to WR=50% (count=0). Tokens with losing history passed the
> filter because their trade counts were gone. See `hermes-signal-debugging` skill
> for the full post-mortem.

### 1m Linear Regression Regime — IMPLEMENTED 2026-05-11 (DISABLED)

**signal_compactor.py** — `get_regime_1m()` added (line 72):
- Linear regression slope of last 100 × 1m candles from `candles.db` → `candles_1m`
- R² confidence (0-100%) determines regime certainty
- slope > 0 → LONG_BIAS, slope < 0 → SHORT_BIAS, else NEUTRAL
- Used for scoring and hot-set entry regime field
- Old `get_regime_5m()` kept for backward compat but marked DEPRECATED

**decider_run.py** — `_get_regime_1m()` added (line 71):
- Computed fresh per token per execution cycle (no stale JSON lag)
- Replaces hotset.json regime lookups at execution time (counter-trend trap + regime filter)
- Applied at line 1689 (_check_counter_trend_trap) and line 1711 (regime filter)

**Impact**: 1m LR is noisier/more responsive than 5m slope. Tokens that showed NEUTRAL now show directional bias (COMP LONG_BIAS 63%, CAKE SHORT_BIAS 53%). Counter-regime penalties fire more often. Low R² (<30%) signals get minimal penalty — regime is unreliable noise.

**⚠️ DISABLED 2026-05-11:** Produces noisy SHORT_BIAS readings on ranging tokens. The implementation exists but is commented out in both signal_compactor.py and decider_run.py. To re-enable:
1. Uncomment `get_regime_1m()` in signal_compactor.py
2. Uncomment `_get_regime_1m()` block in decider_run.py (~line 1703-1751)
3. Remove `_get_regime_5m()` fallback in decider_run.py

**R² thresholds to watch**: tokens with R² 1-5% (AVNT, ATOM, AVAX, EIGEN) have essentially flat price action — regime is noise. Consider adding a minimum R² floor (e.g., 20%) to avoid whipsaw regime assignments.

**Per-coin regime filtering approach (2026-05-11):** T's preference is to filter based on 1m LR regime rather than hard-blocking counter-regime signals. Strong counter-regime signals should escalate (replace original direction), weak ones should de-escalate. This requires `_get_regime_1m()` to be re-enabled and wired into the scoring.

### Effective Confidence Calculation (decider_run.py:1068)

```python
effective_conf = sig_conf × wave_mult + speed_pts
```

**Wave phase multipliers:**

| Wave | Direction | Mult | Tag |
|------|-----------|------|-----|
| bottoming | LONG | 1.15 | 🌱 reversal bounce |
| decelerating | SHORT | 1.15 | ⬇️ riding reversal down |
| accelerating | LONG | 1.10 | ⬆️ momentum continuation |
| falling | SHORT | 1.10 | 🔻 falling with momentum |
| accelerating/decelerating | counter | 0.88 | hard to enter |
| bottoming | SHORT | 0.70 | 🌱 catching falling knife |
| falling | LONG | 0.70 | 🔻 fighting strong down |

**Speed percentile contribution:**
```python
speed_factor = (speed_pctl - 50) / 100
speed_pts = speed_factor × 0.15 × sig_conf
# pctl 100 → +6 pts, pctl 50 → 0 pts, pctl 0 → -6 pts
```

### Rate Limiting

Max **3 new approvals per minute**. If top 3 all pass, 4th-10th are skipped this cycle.

## Key Finding (2026-05-11)

The hot-set display in TUI (or wherever T sees the hot-set) shows **base confidence** from signal_compactor. The **effective confidence** that actually determines approval is post-wave-mult + speed-pts calculation done in decider_run. A token with 79% base confidence but speed_pctl=99 can outrank one with 83% base confidence after speed boost is applied.

## Debugging Commands

```bash
# Check for stuck APPROVED signals (age > 5 min = broken expiry)
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, created_at, 
   (julianday('now') - julianday(created_at)) * 1440 AS age_min
   FROM signals WHERE decision='APPROVED' ORDER BY age_min DESC LIMIT 20;"

# Check hot-set contents
cat /var/www/hermes/data/hotset.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'hotset: {len(d.get(\"hotset\",[]))} entries')"

# Check compactor timer status
systemctl list-timers | grep signal-compactor

# Pipeline journal — authoritative source for execution decisions
journalctl -u hermes-pipeline.service --since "10 minutes ago" --no-pager | grep -iE "🔥|HOT-SET|decider|DECIDER|enter|execute"

# Direct hot-set snapshot (exact token list at a point in time)
cat /var/www/hermes/data/hotset.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'hotset: {len(d[\"hotset\"])} entries')
for e in d['hotset']:
    print(f'  {e[\"token\"]} {e[\"direction\"]} conf={e.get(\"confidence\",\"?\")} src={e.get(\"source\",\"?\")[:50]}')
"

# Full pipeline journal for a time range (good for tracing specific tokens)
journalctl -u hermes-pipeline.service --since "2026-05-18 18:00" --no-pager | grep -iE "execute|enter|xrp|🔥|HOT|decider|open.*5/5" | head -60
```

## Diagnostic Checklist: Token Executed But Not In Hot-Set

When T reports "XRP was just executed as a live trade (it was not in the hot-set)" — follow this sequence:

1. **Check pipeline journal (authoritative)** — not trading.log, not the hot-set file:
   ```
   journalctl -u hermes-pipeline.service --since "10 minutes ago" --no-pager | grep -iE "execute|enter|xrp"
   ```
   Zero log entries = no pipeline execution. Any execution must come from outside the pipeline.

2. **Check hot-set at the time** — trace what was in hotset.json during the window:
   ```
   grep "18:11\|18:12\|18:13" /var/www/hermes/logs/trading.log | grep -iE "HOTSET-WRITE|xrp"
   ```
   Also: grep the trading.log for CONFLUENCE-GATE-BLOCK entries for the token in the minutes before the reported execution.

3. **Enumerate execution paths** — there are exactly 5 ways a trade can reach HL:
   - **Pipeline (normal):** signal_compactor → hotset.json → decider_run → brain.py → HL
   - **Pump Hunter:** pump_hunter.py writes directly to PostgreSQL `brain.trades` (bypasses hot-set)
   - **Cascade Flip:** position_manager.py (CASCADE_FLIP_ENABLED must be True)
   - **Manual:** direct HL UI / API call outside Hermes
   - **Other script:** grep all .py files for `place_order\|market_open` outside the known paths

4. **Check for bypass evidence** — pump_hunter is the only legitimate hot-set bypass:
   ```
   grep -rn "pump_hunter\|market_open\|place_order" /root/.hermes/scripts/*.py | \
     grep -v "ai_decider\|decider_run\|hl-sync\|position_manager\|hyperliquid_exchange"
   ```

5. **The hard rule:** No execution path exists that bypasses hotset.json. If the token is not in hotset.json, it does not execute through the Hermes pipeline. The pipeline journal is the source of truth.

## Key Finding (2026-05-11)

## Anti-Patterns Observed

- All tokens in hot-set with `accel-300+, rs-sXX` — both signals fire in neutral market, self-canceling at RS level (RS Model B should fix this)
- All survival_round=1 — no tokens survived 2+ cycles, market too volatile for RS signals
- RSI=98.2 on ONDO → would be blocked by overextended filter even though base conf=81.7%
## References
- `references/hot-set-signal-quality-predictors-2026-05-25.md` — post-confluence signal quality: signal type dominance, leverage correlation, time-to-execution, SHORT zscore threshold
- [rs-signal-compaction-death-2026-05-28](./references/rs-signal-compaction-death-2026-05-28.md) — RS signals dying in compaction (compaction_stale_5min); 102 expired, 1 PENDING (W); confluence requirement killing single-source RS signals
- [confluence-standalone-bypass-jun-2026](./references/confluence-standalone-bypass-jun-2026.md) — pure accel-300 blocked by confluence gate (2026-06-09); standalone bypass added; RS_TOUCH_HARD_CAP raised 150→180; all hardcoded values moved to hermes_constants
- [hotset-starvation-wr-filter](./references/hotset-starvation-wr-filter.md)
- [decider-duplicate-entry-bug](./references/decider-duplicate-entry-bug.md) — duplicate entries in same pipeline run; per-run token dedup lock; profit-monster cooldown bypass
- [short-sl-anchor-bug](./references/short-sl-anchor-bug.md) — SHORT SL below entry; position_manager anchor fix for new/in-profit SHORTs
- [preserve-path-no-db-approve](./references/preserve-path-no-db-approve.md) — preserve path writes JSON but skips DB APPROVED upsert → decider_run sees nothing

## Critical Failure Modes

### zscore-pump Misses Gradual 4-5% Pumps (lookback=100 too wide) — 2026-05-22

**Symptom:** FET rallied 5.14% over 4 hours (0.19335 → 0.20328). zscore-pump fired 3 LONG signals at 03:08, 03:18, 03:23 with z=2.0-2.2 (barely above threshold=2.0). Signals EXPIRED before the 03:25-03:36 surge to 0.203. No trade was placed.

**Root cause — dual:**
1. **lookback=100 is too wide** for gradual sustained moves. A 5% pump distributed over 100 × 1m bars produces z < 2.0 — the z-score never spikes because the rise is too smooth. Simulated:
   - lookback=100: **0 signals** in the entire 4-hour window
   - lookback=50: first signal at 02:08, z=3.23, price 0.19631 (65 min earlier, 3.5% move remaining)
   - lookback=30: first signal at 01:16, z=5.02, price 0.19468 (112 min earlier, 4.4% move remaining)

2. **CONFLUENCE_REQUIRED=True** blocked the borderline zscore-pump+ signals (z=2.0-2.2, single-source) from entering hot-set. Even if lookback were lower and z were higher, single-source zscore-pump+ would be blocked.

**What would have caught it:**
- `ZSCORE_PUMP_LOOKBACK = 50` (instead of 100) → fires at 02:08, z=3.23
- `CONFLUENCE_REQUIRED = False` → zscore-pump+ passes to hot-set

**Key constants in hermes_constants.py:**
```
ZSCORE_PUMP_LOOKBACK       = 100   # TOO WIDE — change to 50
ZSCORE_PUMP_THRESHOLD     = 2.0   # borderline at lookback=100
ZSCORE_PUMP_DIVERGENCE_*  = ...   # not relevant here — z was rising, not falling
CONFLUENCE_REQUIRED        = True  # blocks single-source zscore-pump+ from hot-set
```

**Diagnostic:**
```python
# Simulate zscore-pump detection offline with different lookbacks
import statistics
# Fetch FET price_history for last 4h, compute rolling z-score at lookback=30/50/100
```

**Related:** `references/zscore-pump-gradual-move-bug.md` — full price history + simulation data.
**Related:** `references/same-timeframe-confluence-illusion-2026-05-21.md` — zscore-pump+RS combos lose vs RS alone; all same-timeframe signals read the same price_history and amplify noise together.

### WR Filter Cache — `_dir_wr_cache` Diverges from PostgreSQL (2026-05-26)

**The problem:** Using `psql` or a standalone Python script to directly query PostgreSQL for WR stats can give **different results** than what signal_compactor sees live. This is not a data inconsistency — it's a caching artifact.

`_get_token_wr()` in signal_compactor uses module-level cache `_dir_wr_cache`:
```python
_dir_wr_cache = {}    # (token, direction) -> (wr, count, timestamp)
_DIR_WR_CACHE_TTL = 300  # 5 min cache
```

The cache is populated when signal_compactor runs in the live pipeline. It persists inside that Python process (which runs continuously), NOT across separate python3 invocations. A standalone `psql` query hits PostgreSQL directly with an empty cache every time.

**This means:**
- Live pipeline: LTC SHORT with 3 trades, WR=33% is correctly blocked by the cache
- Direct psql query: same data, same result — they DO agree if queried at the same time
- Timing window mismatch: if a new trade closes just before the psql query but the cache hasn't refreshed (cache TTL hasn't expired), they diverge

**Key insight from 2026-05-26:**
```
LTC SHORT: total=3, wins=1, WR=33.3%
  oldest=2026-05-22, newest=2026-05-26 01:32
  All 3 trades within last 7 days → should be blocked
```
The WR filter IS working correctly. My initial "wrong answer" was from relying on the wrong diagnostic path (`hotset.json` was empty at that moment, so I assumed no cooldown existed).

**Diagnostic — verify cache vs PostgreSQL agreement:**
```bash
# Method 1: query PostgreSQL directly (authoritative for live pipeline)
python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', connect_timeout=5)
cur = conn.cursor()
cur.execute('''
    SELECT token, direction, COUNT(*) as total,
           SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins
    FROM trades
    WHERE status = '\''closed'\''
      AND close_time >= NOW() - INTERVAL '\''7 days'\''
      AND token = '\''LTC'\''
    GROUP BY token, direction
''')
rows = cur.fetchall()
# wr filter threshold: <50% WR AND >=3 trades → blocked
for r in rows:
    wr = round((r[3] or 0) / r[2] * 100, 1) if r[2] > 0 else 50.0
    blocked = r[2] >= 3 and wr < 50
    print(f'{r[0]} {r[1]}: total={r[2]}, wins={r[3]}, WR={wr:.1f}% → {\"BLOCKED\" if blocked else \"passing\"}')
"

# Method 2: check what signal_compactor actually sees at this moment
# (can only be done by reading the live cache state, not from standalone psql)
```

**Fix:** The cache TTL of 300s is short enough that a direct PostgreSQL query is always accurate within minutes. Always query PostgreSQL directly for definitive answers — never trust `hotset.json` alone for cooldown state.

### WR Filter Blindness After Archive (2026-05-11)

`_get_token_wr()` in signal_compactor reads from **PostgreSQL** (`brain.trades` table, 7-day window).
`archive-trades.py --apply` deletes closed trades from PostgreSQL after archiving.
After archive: PostgreSQL has 0-2 closed trades for most tokens → `wr_count=0 < 3` → WR filter never fires → all tokens pass.

### price_collector Crash → Complete Signal Starvation (Bug 20, 2026-05-27)

**Symptom:** hot-set stays `[]` despite pipeline running normally. All signals report
"stale price_history" for ALL tokens simultaneously. Zero signals, zero trades.

**Root cause:** `hermes-price-collector.service` is `Type=oneshot` with ~100s runtime,
but its timer fires every 60s. The service exits and the timer re-fires before completion →
two instances run simultaneously → `sqlite3.OperationalError: database is locked` →
crash → `signals_hermes.db` price_history goes stale → all signal scripts skip all tokens.

**Cascade:**
1. `price_history` table stops updating
2. `mtp_zscore.py` (120s staleness gate) skips ALL tokens
3. All other signal scripts also skip (shared `signals_hermes.db` price data)
4. `signal_compactor` gets 0 signals → hotset writes `{"hotset": [], ...}`
5. `decider_run` approves nothing → 0 trades

**Fix:** Change timer to `OnUnitActiveSec=2min` (>= script runtime):
```
sudo systemctl edit hermes-price-collector.timer
# [Timer]
# OnUnitActiveSec=2min
```

**Diagnostic:**
```
# Check for overlapping instances
ps aux | grep price_collector | grep -v grep  # should be exactly 1

# Check price_history freshness
python3 -c "
import sqlite3, datetime
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
c.execute('SELECT MAX(timestamp) FROM price_history')
row = c.fetchone()
age = (datetime.datetime.now().timestamp() - (row[0] or 0))
print(f'Age: {age:.0f}s (threshold=120s) — {\"STALE\" if age > 120 else \"FRESH\"}')"
```

See `hermes-pipeline-debug` skill → Bug 20 for full incident report.

The archive SQLite (`/root/.hermes/archive/trades_analysis.db`) has all 361 historical trades with correct win/loss data.
Fix: change `_get_token_wr` to query `trades_analysis.db` instead of PostgreSQL.

**Detection:** Run `signal_compactor.py --dry` — if all tokens show `WR=N/A (0 trades)`, the WR gate is blind.

### Signal Compactor Timer Death → Stuck APPROVED Signals (2026-05-12)

`hermes-signal-compactor.timer` was **disabled since April 29** (`Deactivated successfully`).
When the timer is dead:
- signal_compactor never runs → APPROVED signals **never expire**
- old signals accumulate in signals DB indefinitely
- decider_run processes them but they never leave APPROVED state
- hotset.json goes STALE (compactor writes it, timer keeps it alive but stale)

**Symptoms:** APEX SHORT, ZK LONG, LTC SHORT, FIL SHORT, SKY SHORT all stuck as APPROVED for 1+ hours.

**Fix:**
```bash
systemctl enable hermes-signal-compactor.timer
systemctl start hermes-signal-compactor.timer
```

**Verification:**
```bash
systemctl list-timers | grep signal-compactor
# Should show "active (waiting)" not "inactive (dead)"
```

### pump_hunter Bypasses Hot-Set (2026-05-12)

`pump_hunter.py` writes directly to PostgreSQL `brain.trades` table — **bypasses the entire hot-set pipeline**.
### HH_HL Breakout Threshold Too Loose — Bounce-Point Entries (2026-05-12)

**Symptom:** BERA SHORT, COMP LONG, NIL LONG closed instantly at or near entry — price reversed immediately after position opened at the top of a bounce.

**Root cause:** `HH_HL_BREAKOUT_THRESHOLD = 0.0005` (0.05%) was too loose.
- BERA @ $0.40 only needs $0.0002 to trigger — catches micro-noise at bounce tops, not structural breakouts.
- COMP @ $24.50 needs $0.012 to trigger — similarly tight.
- The threshold was catching the upward micro-spike at the top of the bounce, not a genuine structural breakdown.

**Fix applied (hermes_constants.py line 357):**
```python
HH_HL_BREAKOUT_THRESHOLD = 0.0015   # was 0.0005 (0.05%)
# 0.15% = $0.0006 for BERA, $0.0368 for COMP — requires genuine structural breakout
```

**Range-position filter (signals/hh_hl.py lines 254-261):** Still using 1 ATR threshold, which is loose for tight-range tokens. For BERA with 0.22% range and $0.000065 ATR, price at 37% up from range bottom was NOT blocked (threshold was high20 - ATR = 0.406675 vs actual 0.406170). Consider tightening to 0.5 ATR or price-within-20%-of-range as follow-up.

**All HH_HL constants must live in hermes_constants.py** — verified at lines 354-373. Import chain confirmed:
```python
# hh_hl.py line 24-32:
from hermes_constants import (
    HH_HL_LOOKBACK, HH_HL_SWING_WINDOW, HH_HL_MIN_SEP,
    HH_HL_BREAKOUT_THRESHOLD, HH_HL_ATR_ENTRY_MIN,
    HH_HL_SL_ATR_MULT, HH_HL_TP_ATR_MULT,
    ...
)
```
Used at lines 238, 243 (breakout threshold comparison).

### `_filter_safe_prev_hotset` — Missing Open-Position Check (2026-05-12)

**Location:** `signal_compactor.py` `_filter_safe_prev_hotset()` ~line 1289

**Problem:** When preserving previous hot-set entries, there was **no open-position check**. A token that guardian just traded could have its stale hot-set entry preserved and re-enter hot-set after the trade was placed.

**Fix applied:**
```python
live_open = _get_open_tokens()
if tok.lower() in live_open:
    continue  # skip — token already has open position
```

### Merge Step Bypasses Confluence Gate — Single-Source Leak (2026-05-12, updated)

**Location:** signal_compactor.py lines 938-964 (merge/preserve step) + `_filter_safe_prev_hotset()` line 1333-1336

**Symptom:** Confluence gate is WORKING (logs show single-source blocked at CONFLUENCE-GATE-BLOCK), but single-source signals still reach `decision=APPROVED` in DB.

**Root cause (prior session):** The merge step preserves entries from prev_hotset via `_filter_safe_prev_hotset()`. Entries created BEFORE the confluence patch was deployed already have `decision=APPROVED` in the DB. The merge step re-approves them.

**Root cause (this session — preservation-merge bypass):** Even after `_filter_safe_prev_hotset()` was hardened with a confluence check, preserved entries were added directly to `db_by_key` at line 955 (`db_by_key[key] = pe`) bypassing any final confluence guard. Then `hotset_final = list(db_by_key.values())` included those entries without re-checking source count.

**Two hard blocks applied 2026-05-12:**

1. **DB path final guard** (signal_compactor.py line ~929) — before `hotset_final.append(entry)`:
   ```python
   if len(src_parts) < 2:
       log(f"  🚫 [HOTSET-FINAL-BLOCK] ...SINGLE-SOURCE BLOCKED at final guard...")
       continue
   hotset_final.append(entry)
   ```

2. **Preservation merge guard** (signal_compactor.py line ~957) — before `db_by_key[key] = pe`:
   ```python
   if len(pe_parts) < 2:
       log(f"  🚫 [PRESERVE-MERGE-BLOCK] ...SINGLE-SOURCE BLOCKED at merge...")
       continue
   db_by_key[key] = pe
   ```

### PENDING→APPROVED Transition Bypasses Confluence Gate — Third Leak (2026-05-12)

**Location:** signal_compactor.py ~line 1037-1049

**Symptom:** ME LONG executed at 16:49:20 with `source='accel-300+'` (single-source) despite all confluence gates being in place. No CONFLUENCE-GATE-BLOCK entries in logs for ME at that time.

**Root cause:** The PENDING→APPROVED promotion loop at line ~1040 promotes ANY PENDING row whose token+direction is in `top10_keys` to APPROVED — with NO confluence check. This loop operates on ALL PENDING rows in the DB, not just newly-generated ones.

The flow that created the single-source APPROVED:
1. A multi-source `accel-300+,rs-sXX` PENDING row existed (passed confluence originally)
2. The rs-signal stopped firing (signal expired)
3. `add_signal()` created a NEW single-source PENDING row for the same token+direction when the rs expired and re-fired within the 5-min merge window (or the 5-min window had already passed from the prior multi-source entry)
4. The new single-source PENDING row was picked up by the PENDING→APPROVED loop at line 1040
5. Since ME was in top10_keys, it was immediately promoted to APPROVED — bypassing `_filter_new_signals()` confluence gate entirely

**Fix applied (2026-05-12):** `source` column added to SELECT query at line 1019. Loop unpacks `source` at line 1037. Confluence check added before promotion:

```python
for sid, tok, d, cr, ck, sig_created_at, source in all_sig_rows:
    key = f"{tok.upper()}:{d.upper()}"
    if key in top10_keys:
        # ── CONFLUENCE CHECK (2026-05-12) ─────────────────────────────────
        src_parts = [p.strip() for p in (source or '').split(',') if p.strip()]
        if len(src_parts) < 2:
            log(f"  🔒 [PENDING-APPROVE-BLOCK] {tok}:{d} single-source blocked from APPROVE — src='{source}' parts={len(src_parts)} — need 2+ for confluence")
            continue
```

**Why this is the most dangerous gap:** The confluence gate at line ~537 only fires on NEW `add_signal()` writes. The PENDING→APPROVED loop operates on ALL existing PENDING rows regardless of how they entered PENDING state. A row written before the confluence requirement was enforced, or one that arrived via any other path, could be promoted without ever passing through `_filter_new_signals()`.

**Defense stack** (outer to inner):
1. `_filter_new_signals()` confluence gate at line ~537 (blocks new single-source DB entries)
2. DB path final guard at line ~929 (blocks single-source from DB path before hotset_final)
3. Preservation merge guard at line ~957 (blocks single-source from preservation before merge)
4. **PENDING→APPROVED block at line ~1047** (blocks single-source from PENDING promotion) ← NEW

**Diagnostic:**
```bash
# Verify PENDING-APPROVE-BLOCK is firing
grep "PENDING-APPROVE-BLOCK" /var/www/hermes/logs/trading.log

# Check APPROVED rows with single-source
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, source, decision, created_at FROM signals \
   WHERE decision='APPROVED' AND source NOT LIKE '%,%';"

# Check PENDING rows with single-source
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, source, created_at FROM signals \
   WHERE decision='PENDING' AND source NOT LIKE '%,%';"
```

### All Three Confluence Defense Layers (2026-05-12)

**Layer 1 — New signal entry (`_filter_new_signals`):** Single-source signals blocked at DB write time. Log: `🔒 CONFLUENCE-GATE-BLOCK`.

**Layer 2 — Hot-set finalization:** Two hard blocks:
- DB path final guard (line ~929): single-source from DB path blocked. Log: `🚫 [HOTSET-FINAL-BLOCK]`
- Preservation merge guard (line ~957): single-source from preservation path blocked. Log: `🚫 [PRESERVE-MERGE-BLOCK]`

**Layer 3 — PENDING→APPROVED promotion (line ~1047):** Single-source PENDING rows blocked from becoming APPROVED. Log: `🔒 [PENDING-APPROVE-BLOCK]`

**Note on stale APPROVED rows:** Even with all three layers in place, APPROVED rows written BEFORE the fix was applied remain in the DB. These stale single-source rows will appear in `signals.json` approved list until the next compaction expires them. They will NOT execute because decider_run's execution gate only trades tokens in hotset.json (`hot_set` type). The `approved` list in signals.json includes both hot_set entries AND direct DB APPROVED rows, but only hot_set tokens are executable.

### Confluence Gate Starvation After Blacklist Expansion (2026-05-28)

The blacklist (`SHORT_BLACKLIST` + `LONG_BLACKLIST` = 130 tokens) shrinks the trading universe from ~230 to ~92 tokens. This is fine for execution but creates a signal generation problem: **when only 1 signal type fires (mtp_zscore) and confluence requires 2+, the hot-set goes empty even though prices are fresh**.

Symptom: price_collector working fine (92 tokens updated), mtp_zscore generating valid signals (STBL SHORT z=-2.174 conf=85%), but hotset stays `[]` with:
```
🔒 [CONFLUENCE-GATE-BLOCK] STBL SHORT: only 1 unique types {mtp-zscore-} — need 2+
```

The price_collector fix restored data freshness. The confluence gate is now correctly filtering on signal quality. **The bottleneck is signal diversity**, not data availability. Other signal types (rs, zscore_pump) need to fire for the same coin+direction to reach the 2-source threshold.

This is a design choice, not a bug — confluence is working as intended. But when the blacklist cuts the universe by 60%, and only one signal type fires reliably, signal starvation is the result.

To manually expire stale single-source APPROVED rows:
```bash
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "UPDATE signals SET decision='EXPIRED', expired_at=CURRENT_TIMESTAMP \
   WHERE decision='APPROVED' AND source NOT LIKE '%,%' AND executed=0;"
```

### RS Signals Dying in Compaction — `compaction_stale_5min` Expiry (2026-05-28)

**Symptom:** signals/rs.py was generating signals (70 RS signals on 2026-05-28, 33 on 2026-05-27) but hot-set stays `[]` with only 1 PENDING signal (W). 102 RS signals are EXPIRED with `decision_reason='compaction_stale_5min'`.

**Root cause:** signal_compactor.py lines 391-400 expire PENDING signals older than 5 minutes that haven't achieved confluence:
```python
UPDATE signals SET decision='EXPIRED', decision_reason='compaction_stale_5min', ...
WHERE decision='PENDING' AND created_at < datetime('now', '-5 minutes')
```
RS is a **single-source signal** — when it fires for a coin, it has no co-signal within 5 min → expires. Only W (2026-05-28 04:55:29) survived. All others were killed before a second signal type could arrive for the same coin+direction.

**Key diagnostics:**
```bash
# Check RS signal generation vs expiry rate
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT decision, COUNT(*) FROM signals WHERE signal_type='support_resistance' \
   AND created_at >= datetime('now', '-24 hours') GROUP BY decision;"

# Check why signals expire — should show 'compaction_stale_5min'
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT decision_reason, COUNT(*) FROM signals WHERE signal_type='support_resistance' \
   AND decision='EXPIRED' GROUP BY decision_reason;"

# Check PENDING signal age — young signals may still get co-signals
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, created_at, (julianday('now') - julianday(created_at))*1440 AS age_min \
   FROM signals WHERE decision='PENDING' AND signal_type='support_resistance';"
```

**Two failure modes for signal death — know which one you're debugging:**
1. **Generation failure** — signal script never fires for the coin (check: `SELECT signal_type, COUNT(*) ... GROUP BY signal_type` for last 60 min)
2. **Compaction expiry** — signal generates but dies in 5-min window before co-signal arrives (check: `decision_reason='compaction_stale_5min'` pattern)

These require different fixes. Generation failure = check price_history freshness + signal-specific logic. Compaction expiry = address confluence timing (either reduce 5-min window or increase signal diversity so 2nd source arrives faster).

**Note on RS signal count:** RS signals only started appearing 2026-05-27 — before that, zero RS signals existed in the DB. The user's report of "previously producing many signals and then stopped" likely refers to PENDING hot-set survivors, not total generated signals. Total generated was always low (one-source signals were getting through before the confluence fix was hardened, or RS was just added recently).

### hh_hl Option C — Range-Position Filter (2026-05-12)

**Requirement change (signal_compactor.py):**

- **HH-HL breakout is required** for ALL entries (LONG needs `hhh-longN`, SHORT needs `hhh-shortN`). No hh_hl = signal skipped before scoring.
- **Trend purity is NOT a hard requirement** — it's a +50% score bonus when present (`trend_purity+` for LONG, `trend_purity-` for SHORT).

This replaces the previous "trend_purity hard-required for all entries" approach. Signals without trend_purity can still enter the hot-set if they have hh_hl, but won't get the ranking boost. Signals WITH trend_purity+hh_hl rank 1.5x higher in top-10 selection.

**Score formula updated:**
```python
# In main scoring loop (line ~643):
has_hh_hl = any(p.startswith('hhh-') for p in source_parts)
if not has_hh_hl:
    continue  # skip — hh_hl required

has_trend_purity = ('trend_purity+' in source_parts or 'trend_purity-' in source_parts)
tp_bonus_mult = 1.50 if has_trend_purity else 1.0  # applied at ranking

# At ranking (line ~701):
for s in scored:
    s['score'] = s['score'] * s.get('tp_bonus_mult', 1.0)
scored.sort(key=lambda x: x['score'], reverse=True)
```

**Also updated in `_filter_safe_prev_hotset` (line ~1305):** Same hh_hl required + tp bonus logic applied to preserved entries from previous hot-set.

### hh_hl Option C — Range-Position Filter (2026-05-12)

`signals/hh_hl.py` — SHORT now blocked if `price > recent_high - atr` (price is within 1 ATR of the 20-bar high = bounce territory, not a clean breakdown).

LONG blocked if `price < recent_low + atr` (price is too close to recent low = no breakout room).

Both directions now require clean breakouts at range boundaries, not bounce-at-edge entries.

```
# Quick diagnostic
psql -h /var/run/postgresql -U postgres -d brain -c \
  "SELECT COUNT(*) FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '7 days';"
# If 0-2 rows, WR filter is blind — tokens with losing history are passing through
```

### Multi-File Refactor: `paths.py` → `hermes_constants` Import Hazard

When rewriting imports from `paths` to `hermes_constants` (e.g., `cascade_flip.py` importing `RUNTIME_DB`, `FLIP_COUNTS_FILE`, `LOSS_COOLDOWN_FILE`):

**Always verify the constants exist in `hermes_constants` BEFORE patching the import statement.**

Failure sequence:
1. `cascade_flip.py` line 29: `from hermes_constants import RUNTIME_DB, FLIP_COUNTS_FILE, LOSS_COOLDOWN_FILE, ...`
2. These 3 constants were in `paths.py` but NOT in `hermes_constants` → ImportError at module load
3. cascade_flip is imported by position_manager → cascade_flip import fails → position_manager fails → pipeline crashes

Fix: add the path constants to `hermes_constants.py` FIRST (HERMES_DATA, WWW_DATA, RUNTIME_DB, LOSS_COOLDOWN_FILE, FLIP_COUNTS_FILE), then patch the imports.

### accel-300+ Parameter Regression (2026-05-11)

2026-05-10 changes to `accel_300.py` made the signal too loose:
- `MIN_GAP_PCT`: 0.20 → 0.15 (weaker breakouts accepted)
- `MIN_GAP_GROWTH_PCT`: 0.05 → 0.03 (marginal acceleration accepted)
- `TIMING FIX`: fire on bars 0-3 after EMA cross (entry at moment of maximum uncertainty)

**Result:** 8 tokens entered LONG simultaneously at ~20:02 in a sideways market — market-wide burst, all closed via atr_sl_hit with small losses.

**Reverted 2026-05-11:** MIN_GAP_PCT→0.20, MIN_GAP_GROWTH_PCT→0.05, `bars_since_cross >= 1` hard requirement added.

When tightening accel-300+ parameters: verify no regression in trending markets (parameters were loosened to catch trending breakouts that were being missed).

## Related Skills

- `hermes-pipeline-debug` — debug frozen/broken pipeline
- `trading-system-audit` — full codebase audit
- `self-contained-signals` — signals that own their own position lifecycle (custom exits, parallel to guardian)

---

## Archival & Data Architecture

*Consolidated from `archive-trade-signal-join` skill (archived 2026-05-22). See also `references/archive-data-architecture.md` for full reference.*

### The Atomic Capture Problem

Trades and signals were archived independently with no join key. When analyzing which signals fired for which winners, ~54% of trades had no signal data:
- Signals → `signals_YYYY-MM.jsonl.gz`
- Trades → `trades_archive_*.json`
- Post-hoc time matching only worked when signals happened to be captured

Additionally, `brain.py:add_trade()` stored only `signal` (combo_key) and `confidence` — none of the actual indicator values.

### PostgreSQL Signal Columns (Atomic Capture at Entry)

New trades capture full signal context via 13 new columns in `brain.trades`:

```sql
ALTER TABLE trades ADD COLUMN signal_z_score REAL;
ALTER TABLE trades ADD COLUMN signal_rsi_14 REAL;
ALTER TABLE trades ADD COLUMN signal_macd_hist REAL;
ALTER TABLE trades ADD COLUMN signal_macd_value REAL;
ALTER TABLE trades ADD COLUMN signal_macd_signal REAL;
ALTER TABLE trades ADD COLUMN signal_momentum_state TEXT;
ALTER TABLE trades ADD COLUMN signal_z_score_tier TEXT;
ALTER TABLE trades ADD COLUMN signal_decision TEXT;
ALTER TABLE trades ADD COLUMN signal_leverage INTEGER;
ALTER TABLE trades ADD COLUMN signal_created_at TIMESTAMPTZ;
ALTER TABLE trades ADD COLUMN test_sl_variant TEXT;
ALTER TABLE trades ADD COLUMN test_timing_variant TEXT;
ALTER TABLE trades ADD COLUMN test_trailing_variant TEXT;
```

`decider_run.py` passes hotset signal values at the `execute_trade()` call site:
```python
success, msg = execute_trade(
    ...,
    signal_z_score=sig.get('z_score'),
    signal_rsi_14=sig.get('rsi_14'),
    signal_macd_hist=sig.get('macd_hist'),
    signal_momentum_state=sig.get('momentum_state'),
    signal_z_score_tier=sig.get('z_score_tier'),
    signal_decision=sig.get('decision'),
    test_sl_variant=ab.get('sl_variant'),
    test_timing_variant=ab.get('entry_variant'),
    test_trailing_variant=ab.get('ts_variant'),
)
```

### ⚠️ Preferred: JSONB Catch-All Instead of Per-Signal Columns

**Per-signal columns are deprecated.** The d31692f INSERT bug (42 expressions for 41 columns — `NOW()` counts as 1, not a placeholder) silently broke ALL live trading for a full day.

New signals should use JSONB catch-all columns:
```sql
ALTER TABLE trades ADD COLUMN _signal_metadata JSONB;  -- all signal values
ALTER TABLE trades ADD COLUMN _exp_metadata    JSONB;  -- A/B test variants
```

See `new-signal-implementation` skill, section 7 for full architecture.

### ⚠️ PostgreSQL Connection
- Host: `/var/run/postgresql` (Unix socket)
- DB: `brain`, User: `postgres`

### Archive Locations
- Trades JSON: `/root/.hermes/archive/trades/trades_archive_YYYY-MM-DD.json.gz`
- Signals JSON: `/root/.hermes/archive/signals/signals_YYYY-MM.jsonl.gz` (legacy, one file per month)
- Analysis SQLite: `/root/.hermes/archive/trades_analysis.db`

### archive-trades.py Modes

| Flag | Action |
|------|--------|
| `--dry-run --limit N` | Preview N trades, no file/DB touch |
| `--apply` | Archive closed → gzip JSONL + append to SQLite |
| `--rebuild-db` | Wipe trades_analysis.db, rebuild from all JSON archives |

**CRITICAL: No DELETE from PostgreSQL.** `--apply` is append-only (safe to run on live system).

### ⚠️ archive-trades.py has NO systemd timer (2026-05-15)

It runs manually or via `--apply` but is **NOT on any systemd timer**. This causes the related `hermes-archive-signals.timer` to run `archive-signals.py --apply` (different script), not `archive-trades.py`.

**Symptom:** `trades_analysis.db` goes stale — 205-trade gap observed 2026-05-15 while PostgreSQL had 410 closed trades.
**Fix:** Run `python3 archive-trades.py --apply` manually or add a systemd timer.

### Key Bug History (archive-trades.py)

| Bug | Symptom | Fix |
|-----|---------|-----|
| `direction` missing from `SQLITE_TRADE_COLS` | 195 trades with `direction=NULL` | Recovered from gzip JSON archives |
| `hl_notional_usdt` missing from 3 locations | Column dropped, no HL notional data | Added to ADD_COLUMNS, CREATE TABLE, SQLITE_TRADE_COLS |
| `db_is_new` guard blocked signal append | Signals stopped appending on incremental runs | Moved block outside `db_is_new` guard, changed to `INSERT OR IGNORE` |
| Boolean not SQLite INTEGER compatible | `True`/`False` rejected by INTEGER columns | `_int_safe()` conversion |
| JSONB `dict` not serialized | `str(dict)` produces Python repr | `json.dumps(dict)` via `_json_safe()` |

### PostgreSQL → SQLite Column Name Mapping

PostgreSQL and SQLite column names differ for signal/exp fields:
- PostgreSQL `signal_z_score` → SQLite `_signal_z_score`
- PostgreSQL `test_sl_variant` → SQLite `_exp_sl_variant`

Always use `SQLITE_SCHEMA_COLS` as the authoritative column list for all SQLite operations.

### Type Safety Helpers

```python
def _json_safe(v):
    if isinstance(v, Decimal): return float(v)
    if isinstance(v, datetime): return v.isoformat()
    if isinstance(v, dict): return json.dumps(v)
    if isinstance(v, bool): return int(v)
    return v

def _int_safe(v):
    if isinstance(v, bool): return int(v)
    return v
```

### WR Data Lives in PostgreSQL

`_get_token_wr()` in signal_compactor queries **PostgreSQL** (`brain.trades`, 7-day window).
`archive-trades.py --apply` does NOT delete from PostgreSQL, so WR data stays available.

**⚠️ Warning:** If archive ever did delete from PostgreSQL, `_get_token_wr()` would return default values (WR=50%, count=0) for tokens with no recent trades. Tokens with losing history would pass the WR filter because their trade counts are gone. See `references/hotset-starvation-wr-filter.md` for full post-mortem.

### ⚠️ Verify INSERT Column Balance After Any `add_trade()` Change

`brain.py`'s `add_trade()` INSERT had a **42 expressions for 41 columns** mismatch that silently broke all live trading. `NOW()` in SQL counts as 1 expression, not a placeholder. Always verify:
```python
with open('/root/.hermes/scripts/brain.py', 'rb') as f:
    content = f.read()
idx = content.find(b'INSERT INTO trades')
end = content.find(b'RETURNING id', idx)
block = content[idx:end]
vals = block[block.find(b'VALUES'):]
placeholders = vals.count(b'%s')
now_exprs = 1 if b'NOW()' in vals else 0
# Count columns from column list, compare to placeholders + now_exprs
```