---
name: atr-sl-k-debug
description: Root-cause debugging of ATR SL stops being hit immediately — compute k multiplier per token to find systematic parameter failures vs code bugs.
tags: [atr, stop-loss, position-manager, k-multiplier, debugging]
---

# ATR SL K-Debug Skill

## When to Use
When trades are consistently hitting ATR SL stops immediately (e.g., 13+ consecutive losses with `atr_sl_hit` exit reason), and you need to find the root cause — whether it's a code bug, a stale ATR cache, or bad k multiplier parameters.

## The Investigation Pattern
Use this 4-step diagnostic loop to compute actual k values for all losing tokens:

```python
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from position_manager import _force_fresh_atr, _atr_sl_k_scaled, _atr_multiplier
from signal_gen import get_momentum_stats
from speed_tracker import get_token_speed

# Get entries from PostgreSQL
import subprocess
result = subprocess.run([
    'psql', '-U', 'postgres', '-d', 'brain', '-t', '-c',
    "SELECT token, direction, entry_price FROM trades WHERE status = 'closed' AND close_reason = 'atr_sl_hit' ORDER BY created_at DESC LIMIT 20"
], capture_output=True, text=True)

entries = {}
for line in result.stdout.strip().splitlines():
    parts = [p.strip() for p in line.split('|')]
    if len(parts) >= 3:
        token, direction, entry = parts[0], parts[1], float(parts[2])
        if token not in entries:  # keep most recent
            entries[token] = (direction, entry)

for token, (direction, entry) in entries.items():
    atr = _force_fresh_atr(token)
    ms = get_momentum_stats(token)
    sd = get_token_speed(token)
    speed = sd.get('speed_percentile', 50) if sd else 50
    if not atr:
        print(f'{token}: NO ATR — check cache')
        continue
    atr_pct = atr / entry
    k_base = _atr_multiplier(token, atr_pct)
    k = _atr_sl_k_scaled(token, direction, atr_pct, speed, ms)
    sl_pct = k * atr_pct
    sign = -1 if direction == 'SHORT' else 1
    loss_5x = sl_pct * 5 * 100
    print(f"{token} {direction}: entry={entry} atr={atr:.4f} atr_pct={atr_pct*100:.3f}% k={k:.2f} sl={sl_pct*100:.3f}% loss@5x={sign*loss_5x:.2f}% phase={ms.get('phase')} z={ms.get('avg_z')}")
```

## Key Findings to Look For

### Pattern 1: phase='quiet' everywhere → k_base too low
If all losing tokens have `phase='quiet'` and k=1.0, the `_atr_sl_k_scaled` is returning base_k with no multiplier. Check the PHASE_TIER map:
```
'neutral': 0, 'building': 1, 'quiet': ???  # quiet might not be in the map!
```

### Pattern 2: k=1.0 but phase='accelerating' → bug in phase multiplier
Check `_atr_sl_k_scaled` — if phase >= 2 (accelerating+), should return `base_k * mult` (1.5-2.5). If k=1.0, the phase path is not being reached.

### Pattern 3: stale ATR cache
```bash
python3 -c "
import json, time
cache = json.load(open('/root/.hermes/data/atr_cache.json'))
print('Updated:', time.time() - cache.get('_updated', 0), 's ago')
for t in ['TAO','BTC','ETH']:
    v = cache.get(t, {})
    print(f'  {t}: atr={v.get('a')} price={v.get('p')}')
"
```
Stale or missing ATR = falls back to hardcoded 0.25 k in atr_dry_run.py (but production uses `_force_fresh_atr`).

### Pattern 4: Market regime mismatch
Check regime. If `overall='SHORT_BIAS'` and you have LONG positions, that's your problem — the regime filter should block counter-regime trades.

## ATR K Multiplier Map (from _atr_multiplier)
```
atr_pct < 1.0%  → k=1.0  (LOW_VOL)
atr_pct 1-3%    → k=2.0  (NORMAL)
atr_pct > 3.0%  → k=2.5  (HIGH_VOL)
```

## ATR Phase Multipliers (from _atr_sl_k_scaled)
**⚠️ UPDATED 2026-04-27 — multipliers are MUCH SMALLER than previously documented.**

Multipliers < 1.0 mean TIGHTER SL than base. Applied to base_k=1.0, these produce very small raw sl_pct values that are then rescued by the MIN_SL_PCT_TRAILING floor:
```
phase < 2 (neutral/building):  k = base_k (no change)
phase == 2 (accelerating):     k = base_k × mult
                                 mult = K_PHASE_ACCEL_STALL = 0.15 (stalling + accelerating)
                                 mult = K_PHASE_ACCEL_FAST  = 0.05 (pctl≥70, fast momentum)
                                 mult = K_PHASE_ACCEL_SLOW  = 0.10 (pctl<70, slow momentum)
phase == 3 (exhaustion):       k = base_k × mult
                                 mult = K_PHASE_EXH_STALL = 0.25 (stalling exhaustion)
                                 mult = K_PHASE_EXH_FAST  = 0.15 (fast exhaustion)
                                 mult = K_PHASE_EXH_SLOW  = 0.10 (slow exhaustion)
phase == 4 (extreme):           k = base_k × mult
                                 mult = K_PHASE_EXT_STALL = 0.10 (stalling extreme)
                                 mult = K_PHASE_EXT_FAST  = 0.05 (fast extreme)
```

### Pattern 5: Phase misclassification — signal uses different momentum than ATR engine

**Symptom**: `trend_purity+` fires with accelerating momentum (percentile_long=95.5, phase detected as accelerating), but `_atr_sl_k_scaled` returns k=1.0 with phase='quiet' (overall percentile=1.1). ACCELERATING k multipliers (0.05–0.15) never fire.

**Root cause**: Two different momentum systems:
- `get_momentum_stats()` uses **overall percentile** (percentile from full z-score distribution) → `detect_phase()` → `phase='quiet'`
- `trend_purity+` signal uses **direction-specific percentile_long/percentile_short** (from `percentile_long=95.5`, percentile_short=5.0) → phase='accelerating' at signal time

The phase detector uses `percentile` (overall), NOT `percentile_long`. For PENGU: `percentile=1.1` (< PHASE_BUILDING=60) → 'quiet', but `percentile_long=95.5` → the LONG direction is actually in strong momentum.

**Diagnosis**:
```python
from signal_gen import get_momentum_stats
ms = get_momentum_stats('PENGU')
# Returns: {'percentile': 1.1, 'percentile_long': 95.5, 'phase': 'quiet', ...}
# phase='quiet' → _atr_sl_k_scaled returns base_k=1.0 without phase multiplier
# But signal used percentile_long=95.5 → accelerating momentum
```

**Effect**: PENGU's k=1.250 (NORMAL_VOL, ATR%=1.26%) with NO acceleration multiplier applied. Both SL and TP hit their ACCEL phase floors (0.20% and 0.50%). To get tighter stops, the phase misclassification must be resolved — either by using direction-specific percentile for phase detection, or by lowering `ATR_TP_MIN_ACCEL`.

**T's "book profit fast" philosophy depends on this working**: T's entire SL/TP tightening mechanism (`ATR_SL_MIN_ACCEL=0.20%`, `ATR_TP_MIN_ACCEL=0.50%`) is designed to apply during ACCELERATING phase. If `detect_phase` returns 'quiet' for a token that `trend_purity+` flagged as accelerating, these floors never engage and SL ends up 1-2% away from peak — completely contradicting the "first candle against us, we're out" philosophy.

**The practical impact (2026-04-28 on PENGU)**: Entry $0.010039 via `trend_purity+` at 05:10. At entry, `percentile_long=95.5` (strong bullish momentum) — signal fires. But `_atr_sl_k_scaled` reads `percentile=1.1` (overall z-score, below PHASE_BUILDING=60) → phase='quiet' → k=1.25 (NORMAL_VOL, no acceleration multiplier). Result: SL=$0.010328 = 1.39% below peak of $0.010474. This is exactly the "too loose" behavior T's philosophy is designed to prevent.

**FIX APPLIED (2026-04-28)**: The phase misclassification has a concrete code fix — override `phase` in `_atr_sl_k_scaled` using direction-specific percentile.

The function already computes `pct = percentile_long/short` for stall detection but discards it for phase classification. The fix re-runs `detect_phase(pct, velocity)` with the direction-specific percentile:

```python
# In _atr_sl_k_scaled() — replace the phase assignment block:
# OLD (broken):
phase_str = momentum_stats.get('phase', 'neutral')  # from overall percentile
...
phase = PHASE_TIER.get(phase_str, PHASE_TIER_NEUTRAL)  # wrong phase

# NEW (fixed):
phase = detect_phase(pct, velocity)  # direction-specific percentile
phase_tier = PHASE_TIER.get(phase, PHASE_TIER_NEUTRAL)  # rename to avoid shadowing
# Then use phase_tier for all integer comparisons (>=, == checks)
```

**Also**: Add `detect_phase` to the existing inline import in `_atr_sl_k_scaled`:
```python
from signal_gen import PHASE_BUILDING, PHASE_ACCELERATING, PHASE_EXHAUSTION, PHASE_EXTREME, detect_phase
```
Without this import, the fix raises `NameError: name 'detect_phase' is not defined`.

**Also**: All integer phase comparisons must use `phase_tier` (the renamed variable) instead of `phase`:
```python
# OLD (broken — comparing string to int):
if phase < PHASE_TIER_ACCELERATING:

# NEW (correct):
if phase_tier < PHASE_TIER_ACCELERATING:
```
The patch renames `phase = PHASE_TIER.get(phase_str, ...)` to `phase_tier = PHASE_TIER.get(phase, ...)` and updates all downstream comparisons (`>=`, `==`) to use `phase_tier`.

**Result for PENGU LONG (2026-04-28)**: `percentile_long=95.5, velocity=-0.024` → `detect_phase(95.5, -0.024)='extreme'` → `stalling=True` (velocity<0) → `K_PHASE_EXT_STALL=0.10` → `k=1.250×0.10=0.125` → SL = 0.08% below peak (vs 1.39% before fix).

## Pattern 7: `is_new_trade` Gate Suppressing Phase Multiplier (NEW — 2026-04-28)

**Symptom**: A directionally-strong trade (`percentile_long=100` → `phase='extreme'`) opens but immediately goes against entry. SL is hit at a small loss despite strong directional conviction. k remains at base_k=1.250 with no phase multiplier, even though `_atr_sl_k_scaled` fix is applied.

**Root cause** (`position_manager.py` lines 1614-1624): The `is_new_trade` gate fires when `highest_price == entry` (within 0.1%). This gate was designed to give fresh positions breathing room — but combined with the `highest_price` bug (stuck at entry), it triggers for ALL new positions AND suppresses the phase multiplier:

```python
if is_new_trade:
    k = _dr_atr(token, atr_pct)  # ← ignores _atr_sl_k_scaled result!
    MIN_SL_PCT_TRAILING = ATR_SL_MIN_INIT  # 0.50% floor (was ATR_SL_MIN_ACCEL=0.20%)
```

The `_atr_sl_k_scaled` function is NOT called at all — its result (tight k=0.125 from phase='extreme') is discarded and replaced with base_k=1.250.

**The failure chain for S LONG (2026-04-28)**:
1. S opens LONG at $0.046994
2. Price immediately drops to $0.046939 → going wrong direction
3. `highest_price` stuck at entry (bug in `refresh_current_prices` LONG branch)
4. `is_new_trade = True` fires (peak == entry)
5. k=1.250 applied, SL floor=0.50% → SL = $0.046759
6. $0.046759 < $0.046939 (current) → SL breached → closed at -0.13%
7. Phase multiplier (k=0.125) never got a chance to fire

**Three interacting bugs**:
- Bug 1: `highest_price` stuck at entry for LONG (refresh_current_prices)
- Bug 2: `is_new_trade` gate fires when peak==entry, ignores phase multiplier
- Bug 3: Phase used overall percentile instead of direction-specific (Pattern 5 fix)

**Fix priority**: Bug 1 (peak tracking) must be fixed first. Bug 2 and Bug 3 compound when peak is stuck — fixing both is necessary for the phase multiplier to work on new trades.

**Workaround**: Close and re-enter the trade once price establishes a real peak. The `is_new_trade` gate only fires when `|peak - entry| / entry < 0.001` (0.1%). A 0.1% move above entry clears this gate and the phase multiplier engages.

**Prevention**: The `is_new_trade` gate should not bypass `_atr_sl_k_scaled` entirely. It should still call `_atr_sl_k_scaled` but use INIT floors (0.50%/0.75%) instead of ACCEL floors (0.20%/0.50%) as the minimum. The k multiplier (phase-based tightening) should still apply — it just shouldn't result in razor-thin stops for brand new trades.

## Pattern 6: MIN_SL_PCT_TRAILING Floor Mismatch

**Symptom:** Brand new positions (ORDI, ZK) get 0.20% SL instead of ~1.0%. ATR% is reasonable (0.43–0.52%) but SL is pinned at the acceleration floor.

**Root cause:** `_collect_atr_updates()` uses `MIN_SL_PCT_TRAILING = ATR_SL_MIN_ACCEL = 0.20%` for ALL positions, including brand new ones. The `K_PHASE_ACCEL_*` multipliers (0.05–0.15) compress the raw sl_pct to near-zero (0.05–0.06%), then the too-low floor rescues them only to 0.20%.

**Trace:**
```
ORDI: phase=accelerating, speed_pctl=18.5 (<70), velocity=+0.0134 (not stalling)
  → K_PHASE_ACCEL_SLOW = 0.10 applied to base_k=1.0
  → sl_pct = 0.10 × 0.516% (ATR%) = 0.052%
  → MIN_SL_PCT_TRAILING = ATR_SL_MIN_ACCEL = 0.20%  ← floor pins SL here
  → FINAL: 0.20% SL
```

**The bug:** `ATR_SL_MIN_ACCEL` (0.20%) is designed for the acceleration-phase "first candle against us, we're out" behavior — mid-trade. But `_collect_atr_updates()` applies this same floor to brand new positions immediately after opening, overriding what `get_trade_params()` computed at entry (`ATR_SL_MIN_INIT = 1.0%`).

**Fix:** `MIN_SL_PCT_TRAILING` in `_collect_atr_updates()` should distinguish:
- New position (just opened): use `ATR_SL_MIN_INIT = 1.0%`
- Acceleration phase (mid-trade, first candle against us): use `ATR_SL_MIN_ACCEL = 0.20%`

**Also:** `hermes_constants.py` lines 186-187 have wrong comments:
```
ATR_SL_MIN_INIT = 0.01  # 0.05% ← comment WRONG (should be 1.0%)
ATR_SL_MAX_INIT = 0.01  # 5% cap ← comment WRONG (should be 1.0%)
```

**⚠️ Common fix gotcha — variable shadowing within the loop:**
After applying the INIT-floor fix, if `new_sl` in the dict is still the old (tight) value, a duplicate variable assignment may be overwriting your correct value. In `_collect_atr_updates()`:
1. `_atr_computed_new_sl = new_sl` is saved BEFORE the tighten gate (line ~1643) — correct
2. If the same variable is assigned AGAIN AFTER the tighten gate (line ~1732), the second assignment overwrites the first with the already-overwritten `new_sl` value
3. Always `grep -n "_atr_computed_new_sl\|def.*new_sl" position_manager.py` to check for duplicates
4. Verify with a dry-run that prints the dict's `new_sl` before `_persist_atr_levels()` runs

**Diagnostic query:**
```python
# Check actual SL% vs ATR% for all open positions
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from position_manager import get_db_connection, _pm_get_atr
conn = get_db_connection()
cur = conn.cursor()
cur.execute("SELECT token, direction, entry_price, stop_loss FROM trades WHERE status='open'")
for row in cur.fetchall():
    token, direction, entry, sl = row
    if entry > 0:
        sl_pct = abs(float(sl) - float(entry)) / float(entry) * 100
        atr = _pm_get_atr(token)
        atr_pct = (atr / float(entry) * 100) if atr else None
        print(f'{token}: SL={sl_pct:.3f}%, ATR={atr_pct:.3f}%' if atr_pct else f'{token}: SL={sl_pct:.3f}%, ATR=NONE')
conn.close()
```

**Constants to check in `hermes_constants.py`:**
```
ATR_SL_MIN_INIT    = 0.01   # 1.0% — initial entry SL floor  ← correct value, wrong comment
ATR_SL_MAX_INIT    = 0.01   # 1.0% — initial entry SL cap   ← both INIT values are 1%
ATR_SL_MIN_ACCEL   = 0.002  # 0.20% — acceleration phase floor (mid-trade)
ATR_SL_MIN         = 0.005  # 0.50% — normal trailing floor
```

## File Paths
- ATR cache: `/root/.hermes/data/atr_cache.json`
- Position manager: `/root/.hermes/scripts/position_manager.py`
- ATR dry-run (diagnostic): `/root/.hermes/scripts/atr_dry_run.py` — NOTE: has its own hardcoded k=0.25 for low atr_pct, not used in production
- PostgreSQL: `psql -U postgres -d brain`

## Critical Note
The `get_momentum_stats()` returns `price=0` in the returned dict (it's cached stats, not current price). Use the entry price from the DB or the `price` field from the ATR cache, NOT from momentum_stats, when computing atr_pct.
