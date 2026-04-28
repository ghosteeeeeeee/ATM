---
name: gap-300-signal-debug
description: Debug gap-300 signal issues — direction-flip bug, collapse-guard bug, latency, and momentum filter
triggers:
  - gap-300 signal firing in wrong direction
  - position opened against the dominant gap trend
  - "gap-300+ fired but gap is clearly SHORT"
  - gap-300 fires on stale crossing after data discontinuity
  - gap-300 signal fires but price already moved away
  - strong trend move on chart but gap-300 fired too late or not at all
  - gap-300 is the only signal source but gets blocked by confluence gate
  - gap-300 fires but 1m momentum is against the direction (falling knife)
  - losing trade on gap-300+ when price was already reversing down
  - gap-300 fires 3+ hours after the actual EMA/SMA crossing event
  - signal has bars_since > 20 (crossing is temporally stale)
  - position opened but gap was below threshold at entry time
---

# Bug 1: Direction-Flip — gap-300 Returns Stale Direction

## The Bug

`gap300_signals.py::detect_gap_cross()` finds the **first** threshold crossing (oldest → newest bars) and returns it. It checks that the gap is still **widening** at the most recent bar, but does NOT check whether the gap has **flipped direction** since the crossing.

**Example timeline:**
- 20:46 — Gap crosses LONG at 0.0517%, signal returns LONG
- 22:46 — Gap crosses SHORT at 0.0515%, signal still returns LONG (first crossing wins)
- 01:02 — Gap is 0.25% SHORT, but signal still says LONG
- Trade opened LONG on a SHORT gap

## Symptoms
- `gap-300+` or `gap-300-` fires despite the current gap being the opposite direction
- Confirmed by checking `raw_gaps[-1]` (current bar) vs `raw_gaps[i]` (crossing bar)
- Open position goes against the clearly dominant gap direction

## Root Cause (gap300_signals.py, lines ~196-227)
```python
# The loop returns on the FIRST crossing found — no direction-flip check:
for i in range(len(gap_pcts)):
    gap_pct_prev = gap_pcts[i - 1]
    if gap_pct_prev >= MIN_GAP_PCT:
        continue  # Already above threshold? skip
    if gap_pct < MIN_GAP_PCT:
        continue  # Still below? skip
    if gap_pcts[-1] <= gap_pct:
        continue  # Not widening? skip
    # Direction from crossing bar only — NO check of current direction
    direction = 'LONG' if raw_gaps[i] > 0 else 'SHORT'
    return {'direction': direction, ...}  # Returns stale direction!
```

## The Fix
Add a direction-flip guard after determining direction:
```python
direction = 'LONG' if raw_gaps[i] > 0 else 'SHORT'

# BUG-FIX: Verify current gap direction matches the crossing direction.
# The gap may have crossed LONG hours ago but since flipped SHORT.
if raw_gaps[-1] is not None and (raw_gaps[-1] > 0) != (raw_gaps[i] > 0):
    continue  # Direction flipped since crossing — stale signal, skip
```

## How to Verify
```python
from gap300_signals import detect_gap_cross, _get_1m_prices, _ema_series, _sma_series, PERIOD, MIN_GAP_PCT

prices = _get_1m_prices("TOKEN", lookback=700)
closes = [p['price'] for p in prices]
n = len(closes)
ema_s = _ema_series(closes, PERIOD)
sma_s = _sma_series(closes, PERIOD)
raw_gaps = [ema_s[i] - sma_s[i] if ema_s[i] and sma_s[i] else None for i in range(n)]

# raw_gaps[i] at crossing, raw_gaps[-1] at current bar
# If signs differ, the signal is stale
# e.g. raw_gaps[320] = +0.0009 (LONG), raw_gaps[-1] = -0.0054 (SHORT) = FLIPPED
```

## Also Check: Why Did the Signal Survive So Long?
If the signal was created at one time but executed much later:
- Check `hot_cycle_count` and `compact_rounds` in `signals` table
- `compact_rounds=0` but `hot_cycle_count=N` means signal bypassed compactor survival scoring
- The signal compactor (`signal_compactor.py`) runs compaction rounds — signals need `compact_rounds >= 1` to survive properly
- If `compact_rounds=0`, the signal entered hot-set without going through survival logic

```sql
SELECT id, token, decision, source, compact_rounds, hot_cycle_count, created_at, updated_at
FROM signals WHERE token='MORPHO' ORDER BY created_at DESC LIMIT 10;
```

## Related Files
- `/root/.hermes/scripts/gap300_signals.py` — `detect_gap_cross` source
- `/root/.hermes/scripts/ma_cross_5m.py` — similar EMA/SMA cross logic, check for same bug pattern

---

# Bug 2: Collapse Guard — gap-300 Fires on Stale Peak After Data Discontinuity

## The Bug

`detect_gap_cross()` widening check compares `gap_pcts[-1]` against the **crossing bar** only, not against the **recent peak**. When price_history has a data discontinuity before the fetched window, EMA(300) becomes stale (calculated from old prices) while SMA(300) recalculates from current prices. This creates a phantom "widening" gap — the gap appears to widen when it has actually collapsed from a prior peak.

**Example timeline (MET):**
- Gap peaks at 0.1946% (bar 387) hours before signal
- Data discontinuity in price_history: bar[0] starts 18:03 UTC, prior data ended ~14:00 UTC (~4h gap)
- At signal time: gap_pcts[-1]=0.0549%, crossing bar=0.0523% → still widening → fires
- But gap has collapsed 72% from its 60-bar peak → signal is stale

## Symptom
Signal fires but price has already moved away from the signal price. Signal appears legitimate in hot-set but position opens at a loss.

## Root Cause
File: `/root/.hermes/scripts/gap300_signals.py`, `detect_gap_cross()`

The widening check block (inside `if gap_pcts[i] < 0 and gap_pcts[-1] < gap_pcts[i]:`) only compares against the crossing bar. It does NOT check if the gap has pulled back significantly from recent levels.

## The Fix: Collapse Guard

Inside the existing widening check, add after the crossing is identified:

```python
if gap_pcts[i] < 0 and gap_pcts[-1] < gap_pcts[i]:
    # BUG-FIX: Collapse guard — skip if gap has collapsed from recent peak
    peak_60 = max(gap_pcts[max(0, len(gap_pcts)-60):])
    if peak_60 > 0 and gap_pcts[-1] < peak_60 * 0.70:
        continue  # skip: gap has collapsed from recent peak
    # ... existing widening logic continues
```

**Parameters:**
- 60-bar rolling peak (~1 hour of 1m data) — meaningful recent window
- 30% collapse threshold: skip if current gap < 70% of peak
- Must be inside the existing widening check block (not outside)

## Failed Approaches (Lessons)

**Bar-gap detector**: Tried checking for individual 1m bar gaps >150s within the window. FAILED because the data discontinuity was between bar[401] and bar[697] — each individual bar gap was <150s, but the aggregate window span was short. The gap was BEFORE the fetched window, not within consecutive bars.

**Window-span check**: Tried checking if 700-bar span was >> expected (17.5h). PARTIALLY FAILED because 700 continuous bars spanning 8.94h passes the threshold — the window itself is valid, only the EMA is stale.

**Why they failed**: The root cause is EMA staleness after a data discontinuity *before* the fetched window, not an internal bar gap. The collapse guard catches the symptom directly: the gap has fallen from a recent peak regardless of cause.

## How to Debug

```python
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = conn.cursor()

# Step 1: Get price_history around signal time
cur.execute("""
    SELECT timestamp, ema300, sma300, close
    FROM price_history
    WHERE token='MET' AND timeframe='1m'
    ORDER BY timestamp DESC LIMIT 800
""")

# Step 2: Check for data discontinuity (large timestamp gaps)
cur.execute("""
    SELECT timestamp FROM price_history
    WHERE token='MET' AND timeframe='1m'
    ORDER BY timestamp DESC LIMIT 700
""")
bars = [r[0] for r in cur.fetchall()]
diffs = [bars[i-1] - bars[i] for i in range(1, len(bars))]
print(f"Max bar gap: {max(diffs)}s")  # >>60s means discontinuity

# Step 3: Calculate collapse ratio
# gap_pcts = [(e - s) / s for e, s in zip(ema_list, sma_list)]
peak_60 = max(gap_pcts[max(0, len(gap_pcts)-60):])
latest = gap_pcts[-1]
print(f"Collapse: {latest/peak_60:.1%}")  # <70% = collapse guard triggers
```

## Verification
After applying fix:
```bash
cd /root/.hermes && python3 scripts/gap300_signals.py
```
- Stale signal should NOT appear
- Legitimate signals at/near their 60-bar peak should still fire

## Key Files
- `/root/.hermes/scripts/gap300_signals.py` — main signal script
- `/root/.hermes/scripts/gap300_5m_signals.py` — 5m EMA300 gap acceleration signal
- `/root/.hermes/scripts/backtest_gap300.py` — backtest script (state machine)
- `/root/.hermes/data/signals_hermes.db` — price_history table (ema300, sma300, close)
- `/root/.hermes/data/signals_hermes_runtime.db` — signals/decisions tables

---

# Additional Bugs Found (2026-04-27 Audit)

## Bug A: Off-by-One Persistence Check — gap300_5m_signals.py:196

The 5m signal's persistence check only verifies 2 of the intended 3 bars:

```python
# BEFORE (buggy):
for k in range(1, PERSISTENT_BARS):   # PERSISTENT_BARS=3 → [1,2] = 2 bars

# AFTER (fixed):
for k in range(1, PERSISTENT_BARS + 1):  # → [1,2,3] = 3 bars
```

Impact: gap300_5m signals fire with weaker persistence confirmation than designed. Fix is a one-line change.

---

## Bug B: Backtest vs Live Opposite-Cross Discrepancy — backtest_gap300.py

The backtest's TRACKING opposite-cross condition is stricter than live:

| | Backtest | Live (gap300_signals.py:304) |
|---|---|---|
| TRACKING opposite-cross | `gap_prev < MIN_GAP_PCT <= cur_gap` AND `raw_gap * opp_sign > 0` | `cur_raw * opp_sign < 0` only |

The backtest requires the gap to also cross above MIN_GAP_PCT on the new side. The live system flips direction on any sign change. This means backtest results may **underestimate** live direction-flip frequency. The live behavior is intentional (docstring: "ALLOW on any sign flip").

---

## Bug C: EMA Seed Uses SMA Instead of First Value — gap300_signals.py:61

```python
ema_val = sum(values[:period]) / period   # Uses SMA of first 300 as seed
```

Standard EMA(300) seeds with the first closing price. Using SMA of the first 300 as the seed is technically incorrect (though the difference is small for 300-period EMA). Low severity — not causing trading losses.

---

## Bug D: Dead cross_ts Field — gap300_signals.py

`cross_ts` is stored in `gap300_state` table and written on every state transition (lines 296, 310, 360), but never:
- Loaded back from the state dict in `scan_gap300_state`
- Used in any decision logic
- Referenced in the backtest

It is dead weight. Either remove it or use it for something meaningful (e.g., maximum crossing age tracking, analogous to Bug 5 in the old design).


---

# Bug 4: Momentum Filter — gap-300 Fires on a Falling Knife

## The Problem

`gap-300_signals.py` fires when the EMA(300)/SMA(300) gap crosses above threshold AND is still widening. But it does NOT check whether short-term price momentum agrees with the direction. The gap can widen because price has been falling for hours (EMA diverging upward from a lagging SMA) — yet the most recent 10 bars are already reversing down.

**MET case study (2026-04-27):**
- `gap-300+` LONG fires at conf=88, gap=0.139%
- 1m return over last 10 bars: **-0.59%** (price already reversing down)
- Trade entered LONG, price continued dropping
- Loss was NOT from gap-300 direction being wrong — gap was legitimately bullish
- Loss was from entering at the END of the gap-widening, just as momentum was reversing

**ZEN case study (2026-04-27):**
- `gap-300-` SHORT fires
- 1m return over last 10 bars: -0.24%
- But ZEN's loss came from `accel-300+` signals, not gap-300 alone

The pattern: gap-300 uses a 300-bar (5-hour) lookback — it captures the long-term drift but is blind to short-term reversals. By the time the gap widens enough to fire, price may already be turning.

## Symptom

- gap-300 signal fires with high confidence
- 1m return over last 10 bars is **opposite** to the signal direction
- Trade opens, price continues against the direction
- The gap IS real and widening — this isn't a stale crossing, it's a reversal catching up

## Root Cause

`detect_gap_cross()` in `gap300_signals.py` checks:
1. Gap crossed threshold at bar `i` ✅
2. Gap still widening at most recent bar ✅
3. Gap hasn't collapsed from recent peak ✅
4. **Missing: does recent price momentum confirm the gap direction?** ❌

## The Fix (applied 2026-04-27)

Added momentum filter inside `detect_gap_cross()`, after the widening check and before the collapse guard:

```python
# ── MOMENTUM FILTER ───────────────────────────────────────────────────────
# Require short-term momentum to agree with the gap direction.
# Direction is from raw_gaps[i] at the crossing bar.
# If gap is widening LONG but the last 10 bars returned negative, the gap
# is closing/collapsing rather than extending — price is reversing against
# the signal. This catches the "falling knife" pattern: gap fires because
# EMA-SMA crossed bullish hours ago, but price has since reversed down.
# Use 1m return over last 10 bars (10 minutes) as momentum proxy.
MOMENTUM_BARS = 10
if len(closes) >= MOMENTUM_BARS:
    dir_sign = 1 if raw_gaps[i] > 0 else -1   # LONG=+1, SHORT=-1
    ret = (closes[-1] / closes[-MOMENTUM_BARS] - 1) * 100
    # Skip if momentum disagrees with direction
    if dir_sign > 0 and ret < 0:
        continue
    if dir_sign < 0 and ret > 0:
        continue
```

**Note**: `direction` is assigned AFTER the momentum filter check (at line ~267), so the filter uses `raw_gaps[i]` directly to determine sign. `dir_sign = 1 if raw_gaps[i] > 0 else -1`.

## How to Verify

```python
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from gap300_signals import detect_gap_cross, _get_1m_prices

prices = _get_1m_prices("TOKEN", lookback=700)
closes = [p['price'] for p in prices]

MOMENTUM_BARS = 10
ret = (closes[-1] / closes[-MOMENTUM_BARS] - 1) * 100
print(f"1m return last {MOMENTUM_BARS}: {ret:+.4f}%")

sig = detect_gap_cross("TOKEN", prices, closes[-1])
if sig:
    print(f"Signal: {sig['direction']} gap={sig['gap_pct']}%")
    blocked = (sig['direction'] == 'LONG' and ret < 0) or (sig['direction'] == 'SHORT' and ret > 0)
    print(f"Blocked by momentum: {blocked}")
```

## Gap-300 vs gap300_5m: Which Has This Problem?

- **gap300_signals.py** (1m EMA-SMA): YES — vulnerable to this. 5-hour lookback is blind to short-term reversals.
- **gap300_5m_signals.py**: NO — already has momentum via its `ACCEL_THRESH` (0.30% gap above rolling average) and `TREND_PURITY` (55% of bars above their avg gap) checks. The acceleration requirement inherently requires the gap to be growing, not just wide.

## Relationship to morpho-postmortem

The same "falling knife" pattern was found and fixed for RSI signals in `signal_gen.py` during the MORPHO post-mortem (2026-04-15). There, RSI ≤ 30 + velocity < 0 was penalizing -2 pts instead of awarding +3 pts. The gap-300 momentum filter applies the SAME logic: don't trust a signal whose short-term momentum is already reversing against it.

See: `morpho-postmortem` skill, Bug 1 (Falling Knife Detection).

## Pitfalls
- `direction` variable is assigned AFTER the momentum filter check — always use `raw_gaps[i]` directly for direction in the momentum filter block
- The collapse guard (Bug 2) runs AFTER the momentum filter — a collapsing gap that still has momentum alignment may still fire (this is intentional, collapse guard is a separate concern)
- Use 10 bars (10 minutes) for 1m data — sufficient to catch intrabar reversal without being too noisy
## The Failure Mode

gap-300 is mechanically correct but **temporally misaligned** for catching early breakout moves. Its 300-bar (5-hour) EMA/SMA lookback means:
1. The signal fires based on price comparison 5 hours ago vs now
2. By the time gap crosses threshold and widens enough to fire, the initial breakout move is already underway
3. If it's the only signal source firing (no confluence), the compactor's confluence gate blocks it at conf=58

**SNX case study:**
- SNX started moving at ~23:00 UTC
- gap-300+ fired at 04:38 UTC (conf=58) — after SNX had already run +5.6%
- gap-300 was the ONLY signal source at that time
- Confluence gate (requires 2+ sources) blocked it from reaching the hot-set
- By the time additional signals appeared (zscore_momentum at 07:00), SNX had already retraced

**Result:** System had 1 signal (gap-300+) but it was blocked. 19 other signals existed in the signals DB but all had `decision=EXPIRED`. SNX never entered the hot-set despite a +7.4% move.

## Symptoms
- Strong trend move visible on the chart but gap-300 fires late (after the initial leg)
- gap-300 is the only signal source for a token that is clearly trending
- Signal appears in signals DB with high confidence but `decision=SKIPPED` or `decision=EXPIRED`
- Confluence avg_conf is ~58% (gap-300 alone) — below the 2-source threshold

## Root Cause
gap-300 is a **trend-confirmation** signal, not a **breakout-catch** signal. Its design:
- Waits for EMA(300) and SMA(300) to diverge meaningfully
- This requires sustained directional pressure over hours
- Fast breakouts often exhaust the initial move before the gap widens enough to fire

This is a **design limitation**, not a code bug. The signal works correctly — it just fires too late for early-entry purposes on fast breakouts.

## Why Confluence Gate Blocks It
The signal compactor requires 2+ sources for high-confidence entries:
```
gap-300+ (conf=58, single source) → BLOCKED by confluence gate
gap-300+ + zscore_momentum+ (conf=88, 2 sources) → reaches hot-set
```
When gap-300 fires early (alone), it doesn't make it past compaction.

## How to Diagnose

```python
import sqlite3, datetime

sig_db = "/root/.hermes/data/signals_hermes_runtime.db"
conn = sqlite3.connect(sig_db)
cur = conn.cursor()

# Check what signals fired for the token around the move
cur.execute("""
    SELECT token, signal_type, direction, confidence, decision,
           created_at, updated_at
    FROM signals
    WHERE token='SNX' AND created_at > datetime('now', '-14 hours')
    ORDER BY created_at
""")
for row in cur.fetchall():
    print(row)

# Check hot-set compaction for this token
cur.execute("""
    SELECT token, source, decision, confidence, hot_cycle_count,
           compact_rounds, created_at
    FROM signals
    WHERE token='SNX' AND decision IN ('APPROVED','EXECUTED','SKIPPED')
    ORDER BY created_at DESC LIMIT 20
""")

# Check price history to verify gap-300's lookback
price_db = "/root/.hermes/data/signals_hermes.db"
pcur = sqlite3.connect(price_db).cursor()
pcur.execute("""
    SELECT timestamp, ema300, sma300, close
    FROM price_history
    WHERE token='SNX' AND timeframe='1m'
    ORDER BY timestamp DESC LIMIT 10
""")
for row in pcur.fetchall():
    print(f"  {row}")
```

## Potential Solutions

1. **Short-lookback variant** — Create `gap-60` or `gap-120` for faster breakout detection (gap-120 ≈ 2-hour lookback, catches moves earlier)
2. **Gap-300 as early alert** — Use gap-300 firing as a "watch for confluence" flag, not an entry signal
3. **Single-source exemption** — Allow gap-300 through without confluence requirement when gap is large (e.g., >0.15%) and widening fast
4. **Reduce confluence threshold** — Lower from 2-source to 1-source for gap-300 when it has very high gap_pct (e.g., >0.20%)

## Diagnostic Checklist

When a token trends hard but gap-300 doesn't reach the hot-set:
- [ ] Check signals DB: did gap-300 fire? what was its conf?
- [ ] Was it blocked by the confluence gate (single source)?
- [ ] Check price_history: how many valid bars at signal time?
- [ ] Check EMA/SMA gap magnitude: is it large (>0.10%) or barely over threshold?
- [ ] Was there a data discontinuity before the window (warmup issue)?
- [ ] Check regime at signal time: was it UPTREND or NEUTRAL?

---

## Bug 5: Staleness-on-Repeated-Fire — First Crossing Becomes Hours-Old Stale Signal

### The Bug

`detect_gap_cross()` captures the **first** threshold crossing (oldest → newest bars) and returns it. After returning, a 10-minute cooldown fires the signal again if gap is still widening. After cooldown expires, the signal re-fires again if conditions still hold.

The problem: **the initial crossing event can be hours old**, yet the signal keeps re-firing because the gap is still technically widening (from 0.05% to 0.13%), even though the crossing itself happened long ago.

**Example timeline:**
- 12:15 — GAP crosses LONG threshold (first crossing captured)
- 15:12 — Signal fires again (gap still widening from 0.05% to 0.08%)
- 15:43 — Position opened — but GAP was 0.031% at entry time, BELOW the 0.05% threshold
- The signal was based on a crossing that happened **3.5 hours earlier**

The `bars_since` field tracks how long ago the crossing happened, but **it is not used as a staleness filter** — the code only checks if gap is still widening, not if the crossing is recent.

### Root Cause

File: `/root/.hermes/scripts/gap300_signals.py`, `detect_gap_cross()`

The function has no maximum age for the crossing event. Once a crossing is found and the gap hasn't collapsed, the signal fires indefinitely.

### The Fix: Staleness Cap

Add a maximum age check inside the existing crossing-return block:

```python
MAX_CROSSING_AGE_BARS = 20  # ~20 minutes of 1m bars

if i < len(gap_pcts) - MAX_CROSSING_AGE_BARS:
    continue  # Crossing is too old — skip stale signal
```

Place this after the direction-flip check (Bug 1) but before the widening check.

**Parameters:**
- 20 bars ≈ 20 minutes — crosses that happened more than 20 minutes ago are treated as stale
- Allows legitimate signals that fire within 20 minutes of the crossing
- Prevents signals that fire 3+ hours after the actual crossing

### How to Verify

```python
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from gap300_signals import detect_gap_cross, _get_1m_prices

prices = _get_1m_prices('TOKEN', lookback=700)
closes = [p['price'] for p in prices]
sig = detect_gap_cross('TOKEN', prices, closes[-1])
if sig:
    # bars_since tells you how old the crossing is
    print(f"Signal: {sig['direction']}, crossing age: {sig['bars_since']} bars")
    if sig['bars_since'] > 20:
        print("WOULD BE BLOCKED by staleness cap")
```

### Why This Is Different from the Direction-Flip Bug

- **Direction-flip bug**: The crossing happened recently but the gap FLIPPED to the opposite direction. The signal says LONG but current gap is SHORT.
- **Staleness-on-repeated-fire**: The crossing happened long ago, the gap hasn't flipped, but the crossing event is temporally irrelevant — it's a historical snapshot being treated as a fresh signal.

## Pitfalls
- `gap_pcts` values are signed: negative for SHORT, positive for LONG. Preserve sign in collapse calculations.
- The collapse guard must be placed **inside** the existing widening check block.
- Never use `abs(gap_pcts)` in the widening check — the sign indicates direction.


---

# Proper Fix: State Machine Redesign (2026-04-27)

**Status: SPEC complete, backtest validated, NOT YET IMPLEMENTED.**

The individual bug fixes above (direction-flip guard, collapse guard, staleness cap, momentum filter) are **local patches** to a fundamentally broken design. The real fix is a state machine that tracks the signal lifecycle from cross detection through fire to replacement. See: `/root/.hermes/SPEC-gap300-redesign.md`

## Why the One-Shot Design Is Broken

The original `detect_gap_cross()` finds the **first** threshold crossing (oldest → newest) and returns it. After returning, the scanner re-calls it every 1-10 minutes. Since the crossing bar is always the same, the function returns the **same stale signal** indefinitely as long as the gap is still widening — even if the crossing happened hours ago.

**Example:** GAS crossed LONG at 20:46. At 23:46 the scanner re-calls `detect_gap_cross()`. It finds the same crossing (bar index unchanged), gap is still widening → returns LONG again. This repeats every scan for 3+ hours.

## State Machine Design

Five states:

```
NO_SIGNAL
  │ (cross detected)
  ↓
TRACKING_LONG / TRACKING_SHORT  ← waiting for conditions
  │ (gap widens bar-over-bar + momentum agrees)
  ↓
SIGNAL_ACTIVE_LONG / SIGNAL_ACTIVE_SHORT  ← firing
  │ (gap contracts → back to TRACKING)
  │ (opposite cross → replace with new TRACKING)
  │ (gap collapses → NO_SIGNAL)
  ↓
NO_SIGNAL
```

**Key design decisions:**
- Cross detected → TRACKING (recording the cross level, not firing yet)
- Gap widens bar-over-bar (`gap_pct[current] > gap_pct[prev]`) + momentum agrees → FIRE
- Gap contracts → back to TRACKING (ball is in play, waiting)
- Gap collapses 30%+ from peak → back to TRACKING (ball in play, peak NOT reset)
- Opposite cross → replace tracked cross (no minimum time, widening condition acts as filter)
- Gap below 0.05% → NO_SIGNAL (complete reset)
- Fire continuously while gap is widening, stop when it contracts

## Peak-Not-Reset: The Critical Insight

When the gap **collapses** from its peak, the peak is NOT reset. The original peak is preserved. Re-firing requires the gap to widen back to the **original peak level**, not just off the floor.

**Why:** A collapse to 0.03% followed by re-widening to 0.06% should fire, but only if 0.06% ≥ original peak. If the original peak was 0.20%, the re-widening to 0.06% does NOT re-fire because it hasn't reached 0.20%. This is a **higher bar** for re-firing, which is the correct behavior — we want sustained widening, not just bounce-off-floor.

**Implementation:** Track `tracked_gap_pct` (at cross detection) and `peak_gap_pct` (highest gap seen since tracking started). On collapse: `tracked_gap_pct` stays at the original crossing level; `peak_gap_pct` stays at the highest point. Re-fire only when `gap_pct >= peak_gap_pct` AND gap is still widening.

## Backtest Script

`/root/.hermes/scripts/backtest_gap300.py` — full state machine simulation on historical data.

```python
# Key parameters:
PERIOD = 300           # 5m EMA/SMA
MIN_GAP_PCT = 0.05     # threshold %
COLLAPSE_PCT = 0.70   # fire if gap > peak * 0.70
MOMENTUM_BARS = 10     # 1m return over last 10 bars
COOLDOWN_MIN = 5       # minutes between re-fires
LOOKBACK = 700        # 1m bars (~11.7 hours)

# Confidence formula (keep existing):
# 60 + min(15, (gap_pct - 0.05) × 200) = 60-75 range
```

## Parameter Sweep Results

| COLLAPSE_PCT | Fires  | Notes |
|---|---|---|
| 0.60 | 2,147 | Too loose — fires on minor recoveries |
| 0.70 | 2,080 | Recommended default |
| 0.80 | 1,973 | |
| 0.90 | 1,874 | Too tight — misses valid re-fires |

| COOLDOWN_MIN | Fires  | Notes |
|---|---|---|
| 3 | 2,602 | Too frequent |
| 5 | 2,080 | Recommended default |
| 10 | 1,644 | Too sparse |
| 15 | 1,475 | |

| MOMENTUM_BARS | Fires  | Notes |
|---|---|---|
| 5 | 2,210 | Too noisy |
| 10 | 2,080 | Recommended default |
| 20 | 2,008 | |
| 30 | 1,863 | Too lagging |

**Recommended defaults:** COLLAPSE_PCT=0.70, COOLDOWN_MIN=5, MOMENTUM_BARS=10

## Observed Regimes in Backtest

- **Sustained trends** (early period): 24-72hr continuous fires — gap-300 catches the whole trend
- **Choppy regime** (later period): 5-15min pulses — gap-300 fires on each widening pulse, stops on contraction

## Open Questions

1. Should gap-300 fire on tokens that already have open positions? (Current: scanner skips open positions — confirmed at `gap300_signals.py` line 320)
2. Confirm final parameters after sweep results (user said "we can make it 5 mins" but did not explicitly confirm post-sweep)

## Implementation Notes

- State must be persisted (DB table or memory) and updated every scan tick
- The scanner (`scan_gap300_signals`) already skips open positions — implementation must preserve this
- Cooldown tracked per token+direction, starts from last **fire** (not from tracking start)
- The `scan_gap300_signals` function applies all guards (blacklists, open positions, cooldowns, price age) — implementation must slot into this flow

## Key Files
- `/root/.hermes/scripts/gap300_signals.py` — original (broken) signal logic
- `/root/.hermes/SPEC-gap300-redesign.md` — full state machine specification
- `/root/.hermes/scripts/backtest_gap300.py` — backtest simulation script
- `/root/.hermes/data/signals_hermes.db` — price_history table (Unix timestamps)
