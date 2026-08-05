# rs-s-broken 24h Failure Analysis (2026-06-03)

**Source**: `signals_hermes_runtime.db` → `signal_outcomes` table
**Window**: last 24h from 2026-06-03 ~20:15 UTC

## Key Numbers

| Metric | Value |
|--------|-------|
| Total trades | 136 |
| Winners | 2 (BCH SHORT ×2) |
| Losers | 134 |
| Win rate | **1.5%** |
| Avg PnL | -1.250% |

## Direction Breakdown

| Direction | Trades | Wins | Avg PnL |
|-----------|--------|------|---------|
| SHORT | 112 | 2 | -1.217% |
| LONG | 24 | 0 | -1.401% |

## By Signal Type — All Losing

| Signal Type | Trades | WR | Avg PnL |
|-------------|--------|----|---------|
| `accel-300-,rs-s-broken` | **68** | **3%** | **-1.142%** |
| `rs-r*,rs-s-broken` (any rs-r + broken) | 13 | 0% | -1.2 to -1.9% |
| `accel-300+,rs-s*` (LONG) | 13 | 0% | -0.5 to -1.9% |
| `accel-300-,rs-r*` | 10 | 0% | -1.2 to -1.7% |
| Pure rs-r | 5 | 0% | -0.8 to -1.6% |

## The `rs-s-broken` Structural Failure

### Mechanism

`rs-s-broken` fires SHORT when:
1. A support level was breached (price fell through it)
2. Price is now **below** the broken level
3. Price bounces back toward the broken level and approaches it
4. System fires SHORT, expecting rejection at the broken level

### Why It Fails in Downtrending Markets

In a downtrend, price breaks a support level and continues falling. Hours later, price rallies back toward the broken level — the bounce confirmation (`bounces=True`) fires because price DID bounce at that depth. But the bounce is a dead cat bounce within the downtrend, not a reversal. The SHORT entry happens at the broken level, price rallies briefly then continues down → SL hit.

**The core issue**: bounce confirmation only checks "did price bounce at this level's depth," not "is this bounce strong enough to reverse the downtrend." In a strong downtrend, every minor pullback satisfies the bounce condition.

### The 2 Winners (BCH SHORT)

BCH SHORT (accel-300-, rs-s-broken) won both times with +5.2% and +4.3%. BCH appears to have had a genuine rejection at the broken level — the downtrend was not as entrenched, or the level held as resistance more cleanly.

## Confirmed Bug: price=0 in rs.py add_signal()

**File**: `signals/rs.py` line 774
**Status**: CONFIRMED by ai-engineer subagent
**Fix**: Added `price=price` to the add_signal call

```python
# BEFORE (missing price):
sid = add_signal(
    token=token.upper(),
    direction=sig['direction'],
    signal_type=RS_SIGNAL_TYPE,
    source=sig['source'],
    confidence=sig['confidence'],
)

# AFTER (fixed):
sid = add_signal(
    token=token.upper(),
    direction=sig['direction'],
    signal_type=RS_SIGNAL_TYPE,
    source=sig['source'],
    confidence=sig['confidence'],
    price=price,  # ← FIXED
)
```

**Impact**: All 62 pending LONG signals and 63 pending rs-s-broken SHORT signals had `price=0`. The compactor's price gate rejects any signal with `price <= 0` from entering hot-set. This was a data capture bug, not a directional bias — it affected both SHORTs and LONGs equally.

## Proposed Fixes (in priority order)

### Fix 1: Distance Gate for rs-s-broken (highest impact)

**Location**: `signals/rs.py`, broken support SHORT path (line 561)

Add a gate: if price is more than N ATRs below the broken level, suppress the SHORT.

```python
RS_BROKEN_MAX_DISTANCE = 1.5  # ATRs — level too far below to be valid SHORT target

if broken:
    broken_distance = (price - level) / atr  # positive = price below level
    if broken_distance > RS_BROKEN_MAX_DISTANCE:
        continue  # skip — level is irrelevant, price fell too far
```

This prevents SHORTing a level that was broken hours ago and is now far below price.

### Fix 2: Regime Slope Filter for LONGs

**Location**: `signals/rs.py`, support LONG path

In a NEUTRAL regime with negative slope, LONGs are counter-trend. Apply a confidence penalty:

```python
if direction == 'LONG' and regime == 'NEUTRAL' and regime_slope < 0:
    confidence = confidence * 0.60  # suppress counter-trend LONGs
```

### Fix 3: Distance Decay for Confidence

Within the broken path, decay confidence as distance increases:

```python
distance_penalty = max(0.70, 1.0 - (broken_distance * 0.15))
confidence = confidence * distance_penalty
```

### Fix 4: Stronger Bounce Requirement for Broken Path

Require `bounces >= 2` for rs-s-broken SHORT, or raise `_BOUNCE_THRESH_ATR` to 1.5-2.0 ATR specifically for broken levels.

## Database Query for Signal Outcomes

```python
# signals_hermes_runtime.db → signal_outcomes table
# Columns: id, token, direction, signal_type, is_win, pnl_pct, pnl_usdt,
#          confidence, created_at, closed_at

import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()

c.execute("""
    SELECT token, direction, signal_type, is_win, pnl_pct, confidence, created_at
    FROM signal_outcomes
    WHERE closed_at > datetime('now', '-24 hours')
    ORDER BY pnl_pct ASC
""")
```

## Related Files

- `signals/rs.py` — RS signal generation, 824 lines, 12+ patches applied
- `signals/accel_300.py` — accel-300 signal, generates `accel-300+/−` co-signals
- `signal_compactor.py` — hot-set selection, confluence enforcement, price gate
- `signals_hermes_runtime.db` — live signal storage including `signal_outcomes`