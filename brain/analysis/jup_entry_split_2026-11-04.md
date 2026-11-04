# HARVEST artifact #6 — jup_yolo entry quality: winners vs HML vs other losses (round 9, 2026-11-04)
30d jup trades n=131 (all directions).

## WIN: n=76 avg_pnl=+0.061
  entry RSI: p50=50 n=75
  vol_regime: {'HIGH': 30, 'NORMAL': 25, 'EXTREME': 11, 'FLAT': 10}

## HML: n=22 avg_pnl=-0.145
  entry RSI: p50=55 n=20
  vol_regime: {'NORMAL': 11, 'HIGH': 10, 'EXTREME': 1}

## OTHER_LOSS: n=33 avg_pnl=-0.099
  entry RSI: p50=52 n=32
  vol_regime: {'HIGH': 15, 'NORMAL': 10, 'EXTREME': 6, 'FLAT': 2}

## Candidate entry filter (pre-registered bar — for CEO, NOT shipped):
- Hypothesis from the split above: HML entries cluster in specific vol_regime/RSI cells vs winners.
- Bar to ship (shadow first): 14d shadow-joined n>=20, net >= +$0.50, gross WR not down, fk <20%.
