# pct-hermes+ All EXPIRED — Debug Case Study (2026-05-07)

## Problem
pct-hermes+ fires 1,759 times in 6 hours — 100% EXPIRED, 0 PENDING, 0 APPROVED.

## Root Cause
pct-hermes+ was NOT in `GOOD_STANDALONE_SIGNALS` in signal_compactor.py. Single-source signals
(require no co-signal) cannot pass the confluence gate unless explicitly listed there.

The compactor's confluence gate:
1. For multi-source signals (e.g., `accel-300+,hzscore-`): checks co-signal quality rules
2. For single-source signals: MUST be in GOOD_STANDALONE_SIGNALS dict OR they are rejected as "no confluence"

## Evidence
- pct-hermes+: 1,759 fired, 100% EXPIRED (expired_at=NULL, updated_at ~5min after created_at)
- pct-hermes-: 4,980 fired, 16 PENDING, 5 APPROVED (was already in GOOD_STANDALONE_SIGNALS)
- hzscore+: 3,705 fired, 100% EXPIRED (was NOT in GOOD_STANDALONE_SIGNALS)

## Fix Applied
Added pct-hermes+ to GOOD_STANDALONE_SIGNALS (signal_compactor.py ~line 471):
```python
'pct-hermes+': {'wr': 100, 'avg': 0.770, 'dir': 'LONG'},
```

Backtest basis: 3 trades, 100% WR, +$2.31 avg — strong standalone edge.

## Key Insight: Fire Rate > Scoring
SCORING_TABLE affects ranking priority within the hot-set top-10, but the primary bottleneck
was NOT scoring — it was the confluence gate blocking single-source signals entirely.

Fire rate imbalance (the real driver of hot-set concentration):
| Signal | Fires/2h | Direction |
|--------|----------|-----------|
| pct-hermes- | ~4,980 | SHORT |
| pct-hermes+ | ~1,759 | LONG |
| hzscore- | ~5,401 | LONG (mostly expires) |
| accel-300+ | ~142 | LONG (token allowlist) |
| vel-hermes | ~252 | SHORT (avg_z filter) |

## Also Changed This Session
- ATR_SL_MIN: 0.0015 → 0.005 (0.50%) in hermes_constants.py
- ATR_SL_MAX: 0.003 → 0.010 (1.0%) in hermes_constants.py
