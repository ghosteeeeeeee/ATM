# Daily Orchestrator Report — 2026-08-17 (76th run)

## Pipeline Status
- **24h:** 41T | 61.0% WR | +$0.40 PnL
- **7d:** 406T | 49.8% WR | -$2.23 PnL
- **Open:** 2 trades (HYPE -0.23%, BABY flat)
- **Aug 17 daily:** 29T | 58.6% WR | +$0.26 (GREEN DAY)

## Signal Breakdown (7d)

| Signal | Trades | WR | PnL | Status |
|--------|--------|-----|-----|--------|
| profit-monster-trail | 205T | 88.8% | +$8.01 | DOMINANT |
| atr_sl | 165T | 0.6% | -$11.01 | IMPROVING (41→8 daily) |
| ct-hot+ legacy | 1T | — | +$0.09 | CLEARED |
| guardian_orphan | 8T | 25% | -$0.09 | FIXED (was 9T/7d) |
| Other | 27T | — | +$0.77 | — |

## PM_TRAIL Daily Trend
| Date | Trades | WR | PnL |
|------|--------|-----|-----|
| Aug 17 | 19T | 89.5% | +$0.90 |
| Aug 16 | 19T | 84.2% | +$0.55 |
| Aug 15 | 20T | 65.0% | +$0.71 |
| Aug 14 | 50T | 80.0% | +$1.37 |
| Aug 13 | 23T | 100% | +$0.90 |
| Aug 12 | 55T | 98.2% | +$2.73 |
| Aug 11 | 18T | 100% | +$0.82 |

## ATR_SL Daily Trend
| Date | Trades | WR | PnL |
|------|--------|-----|-----|
| Aug 17 | 8T | 0% | -$0.49 |
| Aug 16 | 18T | 5.6% | -$0.90 |
| Aug 15 | 20T | 0% | -$1.42 |
| Aug 14 | 28T | 0% | -$2.30 |
| Aug 13 | 28T | 0% | -$2.27 |
| Aug 12 | 41T | 0% | -$2.72 |

## Team Activity
- **health_monitor:** All clear. Pipeline healthy, no errors, 41 trades +3.45% PnL today. Stale heartbeats for defunct services (expected).
- **auto_1hr:** No changes needed. Killed range_breakout_short (0% WR 3T). Monitoring bb_bounce+ (2T, auto-kill at 3T).
- **signal_reporter:** System profitable 61% WR +$0.41 (48h). No kills needed — all clear losers already eliminated.

## Implemented Today
- range_breakout_short KILLED by auto-1hr (0% WR 3T, -$0.17)
- No manual implementation needed — system self-managing

## Critical Issues
- None. System running smoothly.

## Monitoring
- bb_bounce+ 2T 50% WR -$0.04 — below 3T auto-kill threshold
- ATR_SL 8T/24h — must stay <15/day
- PM_TRAIL 88.8% WR — must hold >80%

## Next Steps
1. Continue monitoring PM_TRAIL edge and ATR_SL count
2. SHORT side signals needed for SHORT_BIAS regime (backlog)
3. Higher-TF regime for confluence (backlog)
