# Signal Performance Report
**Generated:** 2026-09-26 05:10 UTC | **Period:** 6h (none), 24h (none), 72h, 7d

## Pipeline Status
- **Last trade closed:** 2026-09-25 02:26 UTC (continuum-osc+ LONG, +$0.05)
- **Trades in 48h:** 20 created, 24 closed
- **Trades in 24h:** 0 (gap since Sep 25)
- **Trades in 6h:** 0
- **Total closed trades:** 5,325

---

## KILLED (executed this cycle)

None — all underperformers already killed in prior reports.

### Already Disabled (confirmed still False)
| Signal | Flag | Killed | Reason |
|--------|------|--------|--------|
| mover+ LONG | `MOVER_PLUS_ENABLED` | 2026-09-24 | 0% WR, -$1.11 (72h). All losses via ATR SL. |
| accel-300-breakout SHORT | `ACCEL_300_BREAKOUT_ENABLED` | 2026-09-23 | 28.6% WR, -$0.12. In NEVER_REENABLE. |
| grind-trend+ LONG | `GRIND_TREND_PLUS_ENABLED` | 2026-09-19 | 35.7% WR, -$0.21 (7d) |
| grind-trend- SHORT | `GRIND_TREND_MINUS_ENABLED` | 2026-09-19 | 20% WR, -$0.38 (24h) |
| pullback-entry- SHORT | `PULLBACK_ENTRY_MINUS_ENABLED` | pre-2026-09-25 | 39.1% WR, -$1.31 (7d). Worst PnL. |
| pump-chain- SHORT | `PUMP_CHAIN_V5_SHORT_ENABLED` | 2026-09-25 | 45.5% WR, -$0.93 (7d). CEO killed. |

---

## BOOSTED (executed this cycle)

None — no signal meets all boost criteria (WR > 55%, 5+ trades, PnL > $0.05) in recent windows.

### Closest to Boost
| Signal | Dir | WR | PnL | Trades | Window | Notes |
|--------|-----|-----|-----|--------|--------|-------|
| volume-breakout-long+ | LONG | 100% | +$0.20 | 1 | 72h | Too few trades (1) |
| continuum-osc+ | LONG | 75% | -$0.05 | 4 | 72h | Tiny loss, good WR, under-traded |
| grind-trend+ | LONG | 83.3% | +$0.47 | 6 | 7d | Already killed by CEO |

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Window | Status |
|--------|-----|-----|-----|--------|--------|--------|
| pullback-entry- | SHORT | 39.1% | -$1.31 | 23 | 7d | DISABLED — 25% WR in NORMAL, 33% in EXTREME |
| pump-chain- | SHORT | 48.1% | -$0.55 | 27 | 72h | DISABLED — CEO killed Sep 25 |
| bb-bounce-v2-long+ | LONG | 33.3% | -$0.25 | 9 | 72h | **ENABLED** — CEO re-enabled Sep 22. 30d: 74% WR, +$2.08. Short-term variance. |
| accel-300-breakout | SHORT | 28.6% | -$0.12 | 7 | 72h | DISABLED |
| continuum-osc+ | LONG | 75% | -$0.05 | 4 | 72h | ENABLED — marginal, tiny loss |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Window | Status |
|--------|-----|-----|-----|--------|--------|--------|
| volume-breakout-long+ | LONG | 100% | +$0.20 | 1 | 72h | ENABLED — insufficient sample |
| grind-trend+ | LONG | 83.3% | +$0.47 | 6 | 7d | KILLED by CEO |

---

## ISSUES

- **Pipeline execution failures:** Pipeline is running but trades failing to execute (rc=1). Latest attempt: BLUR LONG via bb-bounce-v2-long+ at05:12 UTC — `decider_run: FAILED`. Traceback at `decider_run.py:4358`. No open positions (0/6). This is an execution bug, not a signal problem.
- **No signal inversions detected** in any window.
- **bb-bounce-v2-long+** is the only active losing signal. CEO rationale for keeping it:30-day 74% WR. Recent 33.3% over9 trades is within normal variance — no action needed unless it persists beyond 7d.
