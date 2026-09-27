=== Signal Performance Report ===
Period: 2026-09-27 11:15 UTC | 7d window (24h has only 1 trade — insufficient data)

## PIPELINE STATUS: IDLE (correct behavior)

BTC regime: **NEUTRAL** — system correctly suppressing most trades.
- 1 trade in last 24h (continuum_engine ORPHAN_PAPER, $0.00)
- 0 open positions
- hotset.json: empty (0 signals survived compaction)
- Compactor dry run: 8 signals in window, 2 passed safety filters, 0 passed all gates

### Why idle?
1. NEUTRAL regime blocks most LONG signals without standalone bypass
2. YGG LONG: passes confluence but killed by RR-ENGINE (R:R 0.86 < 2.0) and VOL-FLOOR
3. SYRUP SHORT: blocked by HALL-SHAME (30d SHORT WR 50% < 55%)
4. This is EXPECTED — system is designed to be conservative in flat markets

## KILLED (executed previously — confirmed still dead)

| Signal | Dir | 7d WR | 7d PnL | Status |
|--------|-----|-------|--------|--------|
| pullback-entry- | SHORT | 23.1% | -$1.54 | ✅ PULLBACK_ENTRY_MINUS_ENABLED=False |
| mover+ | LONG | 25.0% | -$1.19 | ✅ MOVER_PLUS_ENABLED=False |
| accel-300-breakout | SHORT | 28.6% | -$0.12 | ✅ ACCEL_300_BREAKOUT_ENABLED=False |
| pump-chain- (V5) | SHORT | 45.5% | -$0.93 | ✅ PUMP_CHAIN_V5_SHORT_ENABLED=False |

## BOOSTED (executed)

| Signal | Dir | 7d WR | 7d PnL | 30d WR | 30d PnL | Status |
|--------|-----|-------|--------|--------|---------|--------|
| volume-breakout-long+ | LONG | 50.0% | +$0.62 | — | — | ✅ Active, small sample (4T) |
| continuum-osc+ | LONG | 75.0% | -$0.05 | — | — | ✅ Active, tiny PnL |

## WATCH LIST

| Signal | Dir | 7d WR | 7d PnL | 30d WR | 30d PnL | Status |
|--------|-----|-------|--------|--------|---------|--------|
| pump-chain+ | LONG | 32.0% | -$0.42 | 41.3% | +$0.95 | ⚠️ 7d cold, 30d profitable. Keep but monitor. |
| bb-bounce-v2-long+ | LONG | 41.7% | -$0.26 | 41.2% | -$0.71 | ⚠️ CEO re-enabled 2026-09-22. 30d WR 41.2% < 55% HALL-SHAME. Monitor. |
| doji-bottom-long | LONG | 33.3% | -$0.34 | — | — | ⚠️ 3T only. Regime: HIGH 75%WR, NORMAL 50%WR. Too few for action. |

## LOSERS (all regimes losing, no action needed — already killed)

| Signal | Dir | 7d WR | 7d PnL | Regime Breakdown |
|--------|-----|-------|--------|------------------|
| pullback-entry- | SHORT | 23.1% | -$1.54 | EXTREME 0%WR -$0.91, HIGH 43%WR -$0.19, NORMAL 0%WR -$0.44 |
| mover+ | LONG | 25.0% | -$1.19 | EXTREME 0%WR -$1.04, HIGH 40%WR -$0.15 |

## WINNERS (7d)

| Signal | Dir | 7d WR | 7d PnL | Trades |
|--------|-----|-------|--------|--------|
| volume-breakout-long+ | LONG | 50.0% | +$0.62 | 4 |
| continuum-osc+ | LONG | 75.0% | -$0.05 | 4 |

## ISSUES

- **Zero signal inversions** — no direction mismatches found
- **Pipeline idle by design** — NEUTRAL regime is working correctly. System suppresses low-confidence trades in flat markets.
- **No new kills executed** — all losing signals were already killed in previous reports
- **bb-bounce-v2-long+** below HALL-SHAME threshold (41.2% WR < 55%) but CEO explicitly re-enabled — do NOT kill without CEO approval
- **Low trade volume** is a regime state, not a bug. When BTC transitions to HIGH/EXTREME, volume will increase.
