## CEO Report — 2026-08-13

### Diagnosis
24h: 103T, -$0.52, 51.5% WR — RED. 7d: ~460T, +$0.38, 53.0% WR — barely positive. Daily declining: Aug 9 +$0.62 → Aug 10 -$0.10 → Aug 11 -$0.33 → Aug 12 +$0.49 (recovery) → Aug 13 17T -$0.73 (35.3% WR — tiny sample, noise). Stars7d intact (5 profitable): range_breakout_short 15T +$0.43 66.7%, bb_bounce+,range_finder+ 53T +$0.71 58.5%, hzscore+,mover+ 5T +$0.17 80%, bb_bounce+,hzscore+ 34T +$0.22 50%, bb-bounce-short,hzscore- 18T +$0.14 61.1%.

### Root Cause
accel-300- SHORT: 35T 57.1% WR but **inverted R:R** — avg_win $0.048 vs avg_loss $0.075. WR masks bleed. 24h: 15T -$1.13 (worst signal). ATR SL hit dominant exit: 173T -$10.29/7d. No single catastrophic bleed — distributed losses across many signals.

### Fix Applied
**DISABLED ACCEL_300_MINUS_ENABLED** (hermes_constants.py:1015). Reason: inverted R:R makes this signal a net negative despite decent WR. Re-enable if avg_win/avg_loss ratio improves >1.0.

### Verification
Monitor 48h: daily PnL, SHORT7d total, accel-300- execution (should stop firing). 6 open trades (5 accel-300- SHORT) will close naturally.
