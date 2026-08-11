## CEO Report — 2026-08-11

### Verified Numbers (24h)
- 58 trades, PnL: -$0.33, WR: 41.4%
- Worst losers: `bb_bounce+,range_finder+` (LONG, +$0.71 over 7d but -0.10 recent), `ma100-cross,return_exhaustion-` (-$0.28), `hzscore-,return_exhaustion-` (-$0.18)
- Best: `bb_bounce+,hzscore+` (+$0.23, 50% WR), `bb_bounce` LONG (+$0.24, 57.1% WR), `bb_bounce+,range_finder+` (+$0.71, 58.5% WR)

### Diagnosis
NORMAL regime is the biggest loser per 30d backtest (-$0.82). Most signals bleed there. HIGH regime is the only profitable one (+$0.17). The existing REGIME_SIGNALS was stale — signals like `tl_break+`, `tl_break-`, `accel-300-`, `ma_cross` were in NORMAL but aren't profitable there.

### Fix Applied
Updated `REGIME_SIGNALS` in `volatility_gate.py` from 30d backtest (861 trades):
- FLAT: mean reversion only (bb_bounce variants)
- NORMAL: restricted to 3 profitable combos (bb_bounce+,range_finder+, bb_bounce+,hzscore+, tl_break)
- HIGH: breakout signals (bb_bounce+,range_finder+, tl_break, accel-300-vel)
- EXTREME: continuation (continuation+,hzscore+, hzscore+,mover+, bb_bounce)

### Verification
30d backtest: 861 trades, only positive-PnL signal/regime combos included. Next: monitor regime performance over next 48h.
