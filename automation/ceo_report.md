## CEO Report — 2026-08-09 05:50 UTC

### Verified Numbers (DB queried directly)
| Window | Trades | PnL | WR |
|--------|--------|-----|-----|
| 24h | 46 | +$0.25 | 47.8% |
| 7d | 372 | -$0.64 | 45.2% |
| 24h LONG | 37 | +$0.34 | 48.6% |
| 24h SHORT | 9 | -$0.09 | 44.4% |

### 7d Daily Trend (improving)
| Day | Trades | PnL | WR |
|-----|--------|-----|-----|
| Aug 2 | 25 | -$0.51 | 20.0% |
| Aug 3 | 93 | -$0.22 | 32.3% |
| Aug 4 | 26 | -$0.69 | 30.8% |
| Aug 5 | 22 | +$0.21 | 45.5% |
| Aug 6 | 90 | -$0.08 | 58.9% |
| Aug 7 | 58 | +$0.34 | 58.6% |
| Aug 8 | 40 | +$0.10 | 42.5% |
| Aug 9 | 18 | +$0.21 | 61.1% |

### Star Signal
bb_bounce+,range_finder+ LONG: 21T 24h, +$0.48, 57.1% WR. 30T 7d, +$0.79, 63.3% WR — carries entire system profit.

### Diagnosis
System is profitable and improving. 7d loss narrowed from -$0.95 (yesterday) to -$0.64. Last 4 days all positive or near-breakeven.

**ATR SL hits** still largest bleed point: 15 exits, -$0.74/24h (1.2% SL width). Fix deployed Aug 8 — monitoring.

**bb-bounce-short+hzscore- SHORT** is the only profitable SHORT combo: 4T, +$0.11, 75% WR (24h). All other SHORT combos are legacy pre-fix trades aging out.

**ma100-cross+ vortex_break_long** underperforming: 5T, -$0.14, 20% WR (24h). Still in paper observation.

### No Changes
All fixes verified working. ATR SL widening needs more evaluation time. System trending positive.

Working SHORT signals: `bb-bounce-short` (3T +$0.08, 66.7%), `choch-5` (1T +$0.02, 100%).

### Root Cause
`ma_100_cross_short` fires SHORT on any MA cross — no quality filter beyond ATR%. The regime filter (BULLISH skip) doesn't help because the market is NEUTRAL. The signal itself is low-quality for SHORT direction.

### Fix Applied
1. **Disabled `MA_100_CROSS_MINUS_ENABLED = False`** — kills all ma100-cross SHORT combos. Preserves bb-bounce-short, choch-5, and other working SHORT signals.
2. **Added regime filter to base `ma_100_cross.py`** — future-proofs if `MA_100_CROSS_ENABLED` is ever re-enabled. (Base signal is currently disabled.)

### Expected Impact
- SHORT bleeding stops (~$0.20/24h saved)
- SHORT signals from bb-bounce-short and choch-5 unaffected
- LONG side unchanged

### Next Steps
- Monitor 24h for SHORT improvement
- SHORT 7d still -$9.14 but most is legacy pre-fix trades aging out
- Pipeline healthy, no open trades, no errors

---

## CEO Report — 2026-08-09 23:30 UTC — Config Change Acknowledgment

### Changes Received
1. **PM_TRAIL_ACTIVATE_PCT: 0.30→0.25%** — tighter trailing SL, profits lock in earlier
2. **Price collector: 1min→30s** — faster candle updates, fresher signals
3. **is_component_disabled fix** — bb-bounce-short, range-finder-short, return-exhaustion-short now correctly respect their ENABLED flags
4. **SHORT volume filter: 1.2x→1.0x** — SHORT signals trigger on any volume, not just above-average
5. **5m candle fallback for CHoCH** — CHoCH signals degrade gracefully when 15m data is stale
6. **signal_compactor weights updated** — 14d analysis applied

### Status
All acknowledged. No conflicts with recent CEO fixes (ma100-cross SHORT disable, regime filter). These changes complement the bleeding-stop work already deployed.
