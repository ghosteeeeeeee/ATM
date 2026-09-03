=== Signal Performance Report ===
Generated: 2026-09-03 (automated 6h check)

## System Summary
- 24h: 49 trades, 61.2% WR, -$0.70 PnL
- 7d: 396 trades, 52.8% WR, -$2.36 PnL

## KILLED (executed this cycle)
None — all weak signals already killed in prior cycles.

## Pending Kill (CEO_PROTECTED)
| Signal | Dir | WR (24h) | PnL (24h) | Trades | Action |
|--------|-----|----------|-----------|--------|--------|
| accel-300-v3-long+ | LONG | 25.0% | -$0.48 | 4 | KILL after 2026-09-04 05:00 UTC (CEO protection expires) |

## BOOSTED (executed this cycle)
| Signal | Dir | WR (24h) | PnL (24h) | Trades | Action |
|--------|-----|----------|-----------|--------|--------|
| ema300-dip | LONG | 71.4% | +$0.19 | 14 | Already in hot-set, performing well |
| bb-bounce-v2-long+ | LONG | 76.9% | +$0.20 | 13 | Already in hot-set, performing well |

## LOSERS (watch list — no 24h kill trigger)
| Signal | Dir | WR (7d) | PnL (7d) | Trades | Status |
|--------|-----|---------|----------|--------|--------|
| accel-300-v3-long+ | LONG | 35.0% | -$1.18 | 20 | CEO_PROTECTED until 09-04. KILL on expiry. |
| range-reversion-long+ | LONG | 16.7% | -$0.62 | 6 | Already killed 09-02. NEVER_REENABLE. |
| confluence-,ichimoku- | SHORT | 28.6% | -$0.46 | 7 | ICHIMOKU master=False. Dead. |
| r2-trend-long3 | LONG | 33.3% | -$0.46 | 9 | Already killed 09-03. NEVER_REENABLE. |
| macd-div- | SHORT | 46.2% | -$0.36 | 13 | Already killed. NEVER_REENABLE. |
| accel-300-v2-short- | SHORT | 27.3% | -$0.20 | 11 | ACCEL_300_V2_ENABLED=False. Dead. |

## WINNERS
| Signal | Dir | WR (7d) | PnL (7d) | Trades | Status |
|--------|-----|---------|----------|--------|--------|
| accel-300-v2- | SHORT | 52.8% | +$1.46 | 72 | Active. Top performer. |
| bb-bounce-v2-long+ | LONG | 76.9% | +$0.20 | 13 | Active. Strong WR. |
| ema300-dip | LONG | 71.4% | +$0.19 | 14 | Active. Consistent. |
| bb-bounce-short | SHORT | 63.8% | +$0.06 | 58 | Active. High volume, break-even PnL. |

## ISSUES
- **No direction mismatches** found (24h)
- **System slightly negative** (-$0.70/24h, -$2.36/7d) — mostly from accel-300-v3-long+ bleeding
- **accel-300-v3-long+** is the #1 drag: 25% WR, -$0.48 in 24h, -$1.18 in 7d. CEO protection expires 2026-09-04 05:00 UTC — MUST be killed on expiry.
