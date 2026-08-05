# Win-Rate Collapse: 55% → 40% (accel-300 + RS, June 2026)

## Root Cause Diagnosis

**96h, 370 trades — the exit is broken, not the entry.**

### Close Reason Breakdown
```
atr_sl_hit:        208 trades (56%) | WR=1.9%  | avg=-0.82%  ← KILLER
profit-monster:    145 trades (39%) | WR=100%  | avg=+1.06%  ← works fine
guardian_sl:        13 trades  (4%) | WR=0.0%  | avg=-0.92%
```

**Pattern:** Losses are ~1.5x bigger than winners. At 40% WR with 3:1 loss/win ratio: `0.4×(+1%) < 0.6×(-1.5%)` = net negative.

### Signal-Level Breakdown (96h)
- `accel-300+,rs-s-N` (LONG, intact support): ~90 trades, WR ~12% — BLEEDING
- `accel-300-,rs-s-broken` (SHORT, broken resistance): 191 trades, WR=48.7% — BEST signal
- `accel-300-,rs-r-N` (SHORT, resistance levels): ~88 trades, mixed

## What Changed (recent accel-300 modifications)

### 1. CHOP FILTER LOOSENED — critical
```python
# hermes_constants.py lines 490-492
ACCEL_300_CHOP_CROSS_GAP_PCT = 0.18  # was 0.10 — now fires in more chop
ACCEL_300_CHOP_EMA_ANGLE_PCT  = 0.07  # was 0.04
ACCEL_300_CHOP_AVG_GAP_PCT    = 0.90  # was 0.50
```
Looser values = accel-300 fires in choppy conditions. Original tight values protected against false breakouts. The loosening floods the system with marginal signals.

### 2. STALE_BARS = 100 too generous
```python
ACCEL_300_STALE_BARS = 100  # was 20 — allows ancient cross signals
```
A cross from 100 bars ago (~100 min) is stale. In choppy markets, price was far from EMA at cross then mean-reverted. Signal fires at pullback, gap decays, SL hits.

### 3. MIN_GAP_PCT_SHORT = 0.15 too low
```python
MIN_GAP_PCT_SHORT = 0.15  # SHORT fires when only 0.15% below EMA
```
In chop, price flips above/below EMA constantly on small moves. Signal fires on the dip, price mean-reverts back above EMA, SL hits.

### 4. RS touch minimum too low
```python
RS_MIN_TOUCHES = 5  # weak levels break easily
```
Levels with 5-10 touches are structurally weak. Accel-300 LONG fires near weak support → breaks immediately → SL hits.

## Proposed Constant Tweaks (hermes_constants.py)

| Constant | Current | Proposed | Rationale |
|---|---|---|---|
| `ACCEL_300_CHOP_CROSS_GAP_PCT` | 0.18 | **0.22** | Only fire when gap at cross >0.22% — stronger trend start |
| `ACCEL_300_CHOP_EMA_ANGLE_PCT` | 0.07 | **0.10** | Only fire when 50-bar EMA angle >0.10% — confirmed trend |
| `ACCEL_300_STALE_BARS` | 100 | **60** | Max 60 bars (1h) since EMA cross — no ancient signals |
| `MIN_GAP_PCT_SHORT` | 0.15 | **0.20** | Only SHORT when price is 0.20%+ below EMA — stronger signal |
| `RS_MIN_TOUCHES` | 5 | **8** | Only trade from levels with 8+ historical touches |

## Expected Impact

- **~30-40% fewer signals** (quality over quantity)
- **SL hit rate drops** from 56% toward 30-40%
- **Win rate rises** from 40% toward 55-65%
- LONG side improves most (currently worst performing)
- `accel-300-,rs-s-broken` (SHORT, broken resistance) remains the best signal — protect it

## Key Lesson

**The ATR exit is working as designed — the problem is signal quality entering bad trades.**
56% of all trades hitting atr_sl_hit at 1.9% WR means the signals themselves are marginal.
Tightening the entry filters (chop, gap, stale, RS touches) reduces bad entries → fewer SL hits → higher win rate.