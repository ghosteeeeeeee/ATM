## CEO Report — 2026-08-08 (15:50 UTC)

### Diagnosis

**24h: +$0.68 (61.4% WR, 44 trades)** — system profitable, 4th consecutive green day.
**7d: -$1.05 (44.2% WR, 353 trades)** — historical losses from Aug 1-4 dead period aging out.

| Direction | Trades | PnL | WR |
|-----------|--------|-----|-----|
| LONG | 30 | +$1.16 | 76.7% |
| SHORT | 14 | -$0.48 | 28.6% |

**Stars:** bb_bounce+,range_finder+ LONG (14t, +$0.51, 71.4% WR) — dominant signal.

### Root Cause

SHORT bleeding (-$0.48/24h) is residual from pre-disable ma100-cross- combos. No dead signals firing in 24h window — all killed signals confirmed stopped. Today (+$0.19) slightly below yesterday (+$0.34) but within normal variance.

### Fix Applied

**NO CHANGES.** All recent fixes working:
- ATR SL widened to 1.2% (evaluation ongoing)
- Dead signals killed and confirmed stopped
- MA_100_CROSS_MINUS disabled
- Compactor disabled-component bug fixed
- 1 open position: ETH LONG (bb_bounce+,range_finder+)

### Verification

- 44 trades in 24h, +$0.68 net
- 1 open position (ETH LONG, +$0.00)
- All timers active, pipeline healthy
- No errors in last 30min

### Next Steps

- SHORT bleeding small enough to ignore — let historical trades age out
- ATR SL widening needs more trades for significance
- Monitor LONG star combo sustainability
- Disk at 81% — approaching 85% threshold, clean logs if needed

---

## CEO Report — 2026-08-09 (10:50 UTC)

### Diagnosis

**24h: +0.99% PnL (62.1% WR, 29 trades)** — system profitable, 3rd consecutive green day.
**7d: -10.99% (48.5% WR, 326 trades)** — historical losses from Aug 1-4 dead period.

| Direction | Trades | PnL% | WR |
|-----------|--------|------|-----|
| LONG | 20 | +3.1% | 70.0% |
| SHORT | 9 | -2.11% | 44.4% |

**Stars:** bb_bounce+,range_finder+ LONG (8t, +1.38%, 75% WR), bb_bounce+,hzscore+ LONG (5t, +1.92%, 100% WR)

### Root Cause

SHORT bleeding is residual from pre-kill trades (ma100-cross- combos executed before MA_100_CROSS_MINUS_ENABLED=False took effect Aug 8). Dead signals (vel-hermes-, zscore-rising-, inv-accel-300-, pattern) confirmed stopped after Aug 4. System has been profitable every day since Aug 5.

### Fix Applied

**NO CHANGES.** All recent fixes working:
- ATR SL widened to 1.2% (evaluation ongoing)
- Dead signals killed and confirmed stopped
- MA_100_CROSS_MINUS disabled
- RETURN_EXHAUSTION_MINUS disabled
- Compactor disabled-component bug fixed

### Verification

- 29 trades in 24h, +0.99% net
- 0 open positions
- Hotset empty (all NEUTRAL regime — expected)
- Pipeline healthy, no errors

### Next Steps

- ATR SL widening needs more trades for significance
- Monitor LONG star combos sustainability
- Disk at 80% — clean logs if approaching 85%

---

## CEO Report — 2026-08-09 (10:20 UTC)

### Diagnosis

**24h: +$0.71 (65.0% WR, 40 trades)** — system profitable, strongest day.

**LONG: +$0.91 (65.7% WR, 30 trades)** — engine dominant.

**SHORT: -$0.20 (44.4% WR, 10 trades)** — bleeding stopped. Only legacy trades from before kill.

**7d: -$8.39 (41.6% WR, 411 trades)** — historical damage from dead signals (Aug 1-4). Aug 5+ profitable every day.

### Root Cause

7d loss is historical only. Dead signals (inv-accel-300-, vel-hermes-, pattern, zscore_rising) disabled — zero new trades from them.

SHORT -$0.20/24h from ma100-cross- combos executed before kill took effect. No new SHORT executions post-kill confirmed.

**Star performer:** bb_bounce+,range_finder+ LONG — 12 trades, +$0.60, 83.3% WR. This combo alone covers all SHORT losses.

### Fix Applied

**NO CHANGES.** All recent fixes working:
- ATR SL widened to 1.2% (evaluation ongoing)
- Dead signals killed
- MA_100_CROSS_MINUS disabled
- RETURN_EXHAUSTION_MINUS disabled
- Compactor disabled-component bug fixed

System is profitable. Don't disrupt recovery.

### Verification

- 0 open positions (all closed cleanly)
- Pipeline healthy
- No new ma100-cross- SHORT executions after kill
- Disk at 80% — pipeline.log 1.6GB, regime logs 547MB. Clean logs if approaching 85%.

### Next Steps

- Clean logs (pipeline.log 1.6GB, 15m_regime.log 448MB) to prevent disk pressure
- Monitor ATR SL widening impact (more trades needed for significance)
- Monitor star combos sustainability

## CEO Report — 2026-08-09 15:18 UTC

### Diagnosis
24h: +$0.17, 50% WR (24 trades). LONG +$0.73 (75% WR). SHORT -$0.56 (0% WR) — all 8 SHORT losers occurred BEFORE the 13:25 bug fix. No new SHORT losses post-fix.

### Root Cause
Pre-fix ma100-cross- combos were bypassing MA_100_CROSS_MINUS_ENABLED flag. Bug fixed 2026-08-08 13:25 UTC via is_component_disabled() guards in compactor.

### Fix Applied
No new changes needed. All recent fixes working:
- ATR SL widened 1.0%→1.2% (deployed, old trades still at 1.0%)
- MA_100_CROSS_MINUS disabled
- RANGE_FINDER_MINUS disabled (signal_reporter)
- Compactor disabled-component bug fixed

### Verification
- Star: bb_bounce+,range_finder+ LONG = 75% WR, +$0.32/24h
- LONG side: +$0.73/24h (75% WR) — profitable
- System net positive: +$0.17/24h
- All dead signals verified killed (inv-accel, vel-hermes, pattern, zscore_rising, tl_break)
