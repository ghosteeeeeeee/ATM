# Plan: Deep Integration of True-MACD (Wave Counting + Velocity) into Hermes Trading System

## Goal

Wire the true-MACD engine — wave counting, MACD line velocity, and macro roll-over detection — into the core signal generation and decision pipeline so it guides entries, not just warns. Also diagnose why the hot-set is empty.

---

## Context

### What's built (as of 2026-04-06)

`macd_rules.py` now exposes via `cascade_entry_signal()`:

| Field | Purpose |
|---|---|
| `current_wave_number` | Which wave of current direction we're in (1 = fresh, 3-4 = tired) |
| `macd_line_velocity` | Rate of change of MACD line (speedometer: + = building, - = weakening) |
| `histogram_rate` | Rate of change of histogram (acceleration) |
| `macd_cross_count_bull/bear` | Total bull/bear crosses in last 20 candles |
| `macro_4h_opposing_long/short` | 4H MACD crossed against your direction within 20 candles |
| `macro_4h_wave_number` | Which wave 4H is in |
| `cascade_long_allowed / short_allowed` | Whether cascade blocks entry |

### The hot-set is empty — why

Two separate problems:

**Problem A (root cause):** Signal generation has gone quiet. All recent signals (last 6h) are PAXG which is already executed. Zero new signals created. Pipeline may have stalled.

**Problem B (when pipeline is running):** The cascade gates may be too restrictive. For tokens like NIL/INIT (which show clean LONG setups), `cascade_entry_signal` returns `entry_block_reason=None` but `ai_decider` still blocks them. Likely candidates: `momentum_score=0` from speed_tracker, or regime filter, or confidence < 70%.

### The 3-4 wave concept in code

```
Wave 1: First break of opposite trend → uptrend STARTED but fragile
Wave 2: First correction within trend → normal, good entry
Wave 3: Second correction → still valid but weakening
Wave 4+: Final correction before reversal → counter-wave has real chance
```

MACD line velocity tells you if the wave is accelerating or decelerating.

---

## Step-by-Step Plan

### PHASE 1: Diagnose Hot-Set Emptiness

**Step 1.1: Verify signal_gen is running**
```bash
# Check if signal_gen has been generating signals recently
cd /root/.hermes/scripts && python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()
c.execute(\"SELECT MAX(created_at), COUNT(*) FROM signals WHERE created_at > datetime('now','-12 hours')\")
print(c.fetchone())
c.execute(\"SELECT COUNT(*) FROM signals WHERE decision='PENDING' AND executed=0\")
print('pending:', c.fetchone()[0])
conn.close()
"
```

If `created_at` is stale (>1h ago for any row), signal_gen has stalled. Check cron or pipeline.

**Step 1.2: Check why NIL/INIT cascade returns None but don't enter hot-set**

NIL cascade returns `entry_block_reason=None`, `LONG_allowed=False`. The block is at the `long_allowed` boolean, not `entry_block_reason`. Read the cascade logic at lines 694-707 to confirm:

```python
long_allowed = (
    m15_bull
    and (m1h_bull or m4h_bull)
    and not s4h_regime_bear
)
```

For NIL: 15m is BULL (True), 1h is BULL (True), 4h regime is BULL (so `not s4h_regime_bear` is True). `long_allowed = True and True and True` = **True**. But output shows `LONG_allowed=False`.

Contradiction means either:
- `m15_bull` is False (histogram not positive even if macd_above=True), OR
- The block is coming from a different layer (ai_decider regime filter, speed filter, etc.)

**Action:** Run `cascade_entry_signal('NIL')` and print all intermediate booleans to find exact blocking point.

---

### PHASE 2: Calibrate Cascade Gates

**Problem:** The cascade is blocking BOTH directions for most tokens right now. `4h_bull_macd_still_opposing_short` fires when 4H regime=BULL and 15m wants SHORT — but this is the CORRECT short setup (riding the 4H downtrend after a bounce). The logic is backwards here.

**Current (problematic) logic:**
```python
elif m15_bear and m4h_bull:
    short_block = '4h_bull_macd_still_opposing_short'
```

**Interpretation:** "4H is BULL so short is dangerous." But this ignores:
- The short is CORRECT if 4H just rolled over and 15m/1h confirm
- "macro opposition" is what actually tells you if the short is a hope dump

**Fix:** Change the block logic to:
1. **Remove the `m4h_bull` block for shorts** — the 4H regime alone doesn't determine if a short is valid
2. **Instead use `macro_4h_opposing_short`** — this specifically checks if 4H recently crossed bear (i.e., 4H IS bearish now, so shorting aligns with macro)
3. **Block SHORT only when `macro_4h_opposing_short=False` AND `m4h_bull=True`** — meaning 4H is still aggressively bullish and you're trying to short a bounce that's still within the 4H bull trend

Wait — let me re-read the data:

```
ETH: m4h_bull=True (4h macd_above=True, hist=+6.83), 15m=m1h_bear, cascade_dir=SHORT
→ 4H is BULL, 15m/1h want SHORT → short is "hope dump" vs 4H bull
→ macro_opposing_short=True (4H stale bull cross) → 4H MACD was bullish, now just stale
→ THIS short is a HOPE DUMP — block unless wave number is high
```

But the `short_block` only fires when `cascade_direction == 'SHORT'` AND `short_allowed == False`. For ETH, `short_allowed=False` because:
```python
short_allowed = m15_bear and (m1h_bear or m4h_bear) and not s4h_regime_bull
```
= True and False (1h not bearish) and False = **False**

So ETH short is blocked by the `short_allowed` formula, not by `short_block`. Good — the `short_block` label never fires for ETH.

For NIL: cascade_dir=LONG, long_allowed=False (somehow), so short_block isn't relevant either.

**Action Items for Cascade Calibrations:**

1. **Add wave number to `long_allowed`/`short_allowed` logic**: Allow the trade if wave >= 3 even when larger TF opposes, because deep-wave setups are real reversals:
   ```python
   # If 4H is in wave 3-4, allow counter-wave entries even if regime opposes
   deep_wave_4h = s_4h and s_4h.current_wave_number >= 3
   ```

2. **Use velocity to gate stale crosses**: If 4H is stale-bull (crossover_age > 5) but `macd_line_velocity` is very negative, the trend has genuinely broken — don't block the counter-trend trade:
   ```python
   # If 4H staleness is > 5 candles AND velocity is strongly negative → 4H trend broken
   if s_4h and s_4h.crossover_age > 5 and s_4h.macd_line_velocity < -0.5:
       # 4H momentum has shifted — don't block counter-trend
       s4h_regime_bull = False  # override
   ```

3. **Tighten the block reasons**: The `short_block`/`long_block` should ONLY fire for "early entry danger" (15m flipped but 1h/4h not confirmed), not for macro-tide conflicts.

---

### PHASE 3: Wire Wave + Velocity into ai_decider Hot-Set Filters

The hot-set builder in `ai_decider.py` (lines 1415-1518) applies these filters in order:
1. BLACKLIST filters (SHORT/LONG blocklists)
2. Solana-only / delisted
3. Regime filters (must have regime, not NEUTRAL, not counter-regime)
4. **SPEED filter** — `momentum_score != 0` — this is where wave matters
5. **CASCADE filter** — `cascade_long_allowed / short_allowed`
6. Escape valve: conf>=90 AND reg_conf>=70 AND regime confirms direction

**Step 3.1: Add wave number to speed filter**

Current:
```python
if momentum is None or momentum == 0.0:
    print(f"  🚫 [HOTSET-FILTER] {tkn} {direction}: momentum=0% — speed stalled")
    continue
```

Proposed — allow through if wave >= 3 (deep wave reversal has momentum even if speed tracker says 0):
```python
_wave_ok = spd.get('wave_number', 0) >= 3 if spd.get('wave_number') else False
if momentum is None or momentum == 0.0:
    if not _wave_ok:
        print(f"  🚫 [HOTSET-FILTER] {tkn} {direction}: momentum=0% — speed stalled")
        continue
    else:
        print(f"  ⚠️  [WAVE-OVERRIDE] {tkn} {direction}: momentum=0% but wave={spd['wave_number']} — deep reversal, allowing")
```

**Step 3.2: Add velocity to escape valve**

The escape valve lets high-confidence signals through cascade blocks. Add velocity:
```python
vel_ok = spd.get('macd_line_velocity', 0.0) > 0.0  # momentum building
escape = (
    conf >= 90.0 and
    _tok_rc >= 70.0 and
    vel_ok and
    (_tok_regime == 'LONG_BIAS' and dir_upper == 'LONG' or
     _tok_regime == 'SHORT_BIAS' and dir_upper == 'SHORT')
)
```

**Step 3.3: Add cascade wave info to hotset output**

The hotset.json already includes wave_phase and is_overextended. Add:
- `wave_number`: current wave of 4H
- `macd_line_velocity`: speedometer value
- `histogram_rate`: momentum acceleration

This data then flows to decider-run for position sizing.

---

### PHASE 4: Wire Wave + Velocity into decider-run (Position Sizing)

Currently `decider-run.py` reads hotset.json and executes approved signals with fixed or ATR-based SL/TP. Add wave-aware position sizing:

```python
# Position size multipliers based on wave number
WAVE_SIZE_MULT = {
    1: 1.0,   # Wave 1: fresh break, full size
    2: 0.85,  # Wave 2: correction, slightly smaller
    3: 0.65,  # Wave 3: deeper correction, reduce
    4: 0.40,  # Wave 4: tired trend, small size or skip
}

# Velocity adjustment: accelerating trends get larger size
if vel > 0.5:
    size_mult *= 1.2  # boost for accelerating momentum
elif vel < -0.3:
    size_mult *= 0.7  # reduce for decelerating
```

Add to the signal dict in hotset.json:
```python
hotset.append({
    ...
    'wave_number': s_4h.current_wave_number,
    'macd_line_velocity': s_4h.macd_line_velocity,
    'histogram_rate': s_4h.histogram_rate,
    'cascade_score': r['cascade_score'],
})
```

---

### PHASE 5: Add True-MACD to signal_gen.py (Signal Creation)

`signal_gen.py` creates signals. Add wave+velocity to signal features so they can be used in A/B testing and pattern learning.

Add to signal features logged:
```python
'wave_number': state_15m.current_wave_number,
'macd_line_velocity_15m': state_15m.macd_line_velocity,
'macd_line_velocity_1h': state_1h.macd_line_velocity,
'macd_line_velocity_4h': state_4h.macd_line_velocity,
'4h_wave_number': state_4h.current_wave_number,
'cross_count_bull_4h': state_4h.macd_cross_count_bull,
'cross_count_bear_4h': state_4h.macd_cross_count_bear,
```

---

## Files to Change

| File | Changes |
|---|---|
| `/root/.hermes/scripts/macd_rules.py` | Phase 2: Calibrate cascade gates (long_allowed/short_allowed), wave+velocity in block logic |
| `/root/.hermes/scripts/ai_decider.py` | Phase 3: Wave-aware speed filter, velocity in escape valve, wave in hotset output |
| `/root/.hermes/scripts/decider-run.py` | Phase 4: Wave+velocity position sizing |
| `/root/.hermes/scripts/signal_gen.py` | Phase 5: Log wave+velocity features on signal creation |
| `/root/.hermes/brain/trading.md` | Document new integration, add surf.md reference |

---

## Key Open Questions

1. **Why did signal_gen stop generating?** Need to check cron/pipeline logs
2. **Why does NIL show LONG_allowed=False in output but cascade formula suggests True?** Need intermediate debug print
3. **Should wave number override momentum=0 filter always, or only when conf>=85%?** TBD
4. **Should velocity affect entry ALLOWED or just SIZE?** Suggest: velocity only affects SIZE, not entry permission (keep logic clean)
5. **What wave threshold triggers size reduction?** Suggested: wave 3+ → reduce, wave 4+ → reduce significantly or skip

---

## Verification

After each phase:
```bash
cd /root/.hermes/scripts && python3 -c "
from macd_rules import cascade_entry_signal
# Before: tokens should show non-None wave numbers and populated velocity
for t in ['ETH','NIL','INIT','DYDX']:
    r = cascade_entry_signal(t)
    s4h = r['mtf_result']['tf_states']['4h']
    print(f'{t}: 4h_wave={s4h.current_wave_number} vel={s4h.macd_line_velocity:+.2f} LONG={r[\"cascade_long_allowed\"]} SHORT={r[\"cascade_short_allowed\"]}')
"
```

After Phase 3, check hotset.json has wave_number field.
After Phase 4, check executed trades have wave-aware sizing.
