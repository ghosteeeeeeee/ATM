## CEO Report — 2026-08-08

### Diagnosis

**24h: +$0.21 (58% WR, 50 trades)** — slightly positive, recent fixes working.

**7d: -$8.77 (38.6% WR, 407 trades)** — but most losses are from dead signals with legacy trades:
- inv-accel-300-: -$2.06 (30 trades, 16.7% WR) — DISABLED
- zscore-rising: -$2.38 (70 trades, 25.6% WR) — DISABLED  
- vel-hermes: -$1.14 (58 trades, 31% WR) — DISABLED
- pattern_wolf: -$1.28 (11 trades, 10% WR) — DISABLED

These are historical — no new trades from these signals.

### Root Cause

1. **SHORT signals bleeding** — $-7.39 over 7d (32.2% WR) vs LONG at $-1.38 (48.1% WR). SHORT blacklist exists but may need expansion.

2. **bb_bounce+ confluence is excellent** — 88.9% WR, $0.38 in 24h. This is the star performer.

3. **ATR SL widening (1.0% → 1.2%)** — applied 2026-08-08 00:30. Need 24h window to measure impact.

### Fix Applied

**No changes this run.** Recent fixes need time to show impact:
- ATR SL widened (22/22 SL hits at exactly 1.0% = too tight)
- RETURN_EXHAUSTION_MINUS disabled (14 trades, -$0.64)
- Dead signals killed (inv-accel-300, zscore-rising, vel-hermes, pattern_wolf)

### Verification

- 24h positive ($0.21) despite legacy SHORT trades
- bb_bounce+,range_finder+ LONG: 9 trades, $0.38, 88.9% WR
- hzscore+,return_exhaustion_long LONG: 12 trades, $0.18, 58.3% WR
- Pipeline healthy, 5 open positions, +2.13% portfolio PnL

### Next Actions

1. **Monitor** — ATR SL impact over next 24h
2. **Monitor** — bb_bounce+ confluence sustainability
3. **Consider** — Expanding SHORT blacklist if bleeding continues
4. **No flag changes** — recent fixes need evaluation window
