# Signal Quality Session — 2026-05-07

## Session Summary

T reported: signals are garbage, coin instantly reverses after entry, losing money faster after ATR SL tightening. Wanted signal-by-signal audit and combo improvement.

## Findings

### The Real Problem: Signal Quality, Not ATR

T had tightened ATR params thinking the problem was risk management. Real problem: signals were wrong. Tighter SL = faster losses on bad entries.

### Signal Thresholds Were Too Loose

| Signal | Parameter | Old | New | Notes |
|--------|-----------|-----|-----|-------|
| pct-hermes | PCT_RANK_THRESH | 80 | **95** | Only fire at top/bottom 5% of range |
| vel-hermes | VEL_ABS_THRESHOLD | 0.03 | **0.04** | Was going to 0.06 but blocked all combos |
| hzscore | MIN_Z_VALUE (new) | none | **0.4** | Filter chop-zone readings |
| accel-300 | PERSISTENCE_BARS | 3 | **2** | Fire earlier |

### Critical Bug: pct-hermes Confidence Was Broken

```python
# OLD — capped at 60, pct=88 and pct=100 both returned conf=60:
pct_conf = min(60, max(50, (pct_val - 72) * 1.25 + 50))

# FIXED — pct=95 → conf=70, pct=100 → conf=95:
pct_conf = min(95, max(70, 70 + (pct_val - PCT_RANK_THRESH) * 5))
```

### Critical Bug: Signals Never Combined (Window Too Tight)

- pct_hermes runs every **1 min** → 127 fires in 10 min
- hzscore runs every **5 min** → 0 fires in same 10 min (timestamp mismatch)
- Even when both fired, timestamps were 4 min apart → outside 5-min window → no combo
- **Fix**: 5 min → **15 min** compaction window

### Critical Bug: Co-Signal Gate WR >= 40 Was Wrong Filter

pct-hermes- had 35% WR but +0.221% avg — profitable. Gate was blocking it.
**Fix**: `avg_pnl >= 0` instead of `WR >= 40`.

### Confluence Gate WR/PnL Data (from 742 trades)

**SHORT — What Works:**
- `hzscore+,pct-hermes-,vel-hermes-` (3-signal): 49 trades, **47% WR, +0.466% avg** ✅
- `hzscore+,pct-hermes-` (2-signal): 130 trades, **33% WR, +0.177% avg** ❌
- `hzscore+,vel-hermes-` without pct-hermes-: **20% WR** → poison, blocked

**LONG — What Works:**
- `accel-300+,hzscore-`: 30 trades, **37% WR, +0.661% avg** ✅
- `accel-300+` alone: 31% WR, +0.405% avg — coin flip, needs hzscore-
- `hzscore-` alone: 38% WR, +0.318% avg ✅

**The support level (rs-s###) matters** — accel-300+,hzscore- with rs-s support = winners. Without = losers.

## Changes Made

| File | Change |
|------|--------|
| `signals/pct_hermes.py` | PCT_RANK_THRESH 80→95; confidence formula fixed |
| `signals/vel_hermes.py` | VEL_ABS_THRESHOLD 0.03→0.04 |
| `signals/hzscore.py` | Added MIN_Z_VALUE=0.4 |
| `signals/accel_300.py` | PERSISTENCE_BARS 3→2 |
| `signal_compactor.py` | Window 5→15 min; WR>=40 → avg_pnl>=0 |

## Still Broken

- **accel-300**: 0 signals in 2 hours — investigate why
- **vel_hermes**: 17 signals in 2 hours — very sparse even at 0.04
- **3-signal SHORT combo**: requires hzscore + pct_hermes + vel_hermes all within 15 min for same token — still rare
- **LONG side**: accel-300+ is the crown jewel but not firing; no strong LONG signal
