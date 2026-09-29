# === Signal Performance Report ===
**Period:** 2026-09-29 ~12:00 UTC | Last 6h + 24h + 7d context

## System Totals
| Period | Trades | WR | PnL |
|--------|--------|-----|-----|
| 6h | 6 | 83.3% | +$0.59 |
| 24h | 16 | 75.0% | +$0.89 |

## KILLED (executed)
None — no signal meets kill criteria (5+ trades, <30% WR, 24h).

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 100% | +$0.81 | 5 (24h) | Monitor — already strong, no boost needed |

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 0% | -$1.54 | 6 (7d) | ⚠️ COLD STREAK — all-time 119T 52.1% WR +$0.35. NORMAL already blocked. HIGH+EXTREME both 0% this week. Historical data supports signal — bad week, not broken. |
| mover+ | LONG | 16.7% | -$0.95 | 6 (7d) | ⚠️ POTENTIAL KILL — all-time 21T 57.1% WR but -$0.85 total. Losses > wins. EXTREME 2T 0% -$0.67. Low sample (21T all-time). Needs monitoring. |
| pump-chain+ | LONG | 0% | -$0.76 | 3 (7d) | Insufficient sample. All-time 80T 41.3% WR +$0.95. Dead hours already block worst hours. |
| accel-300-breakout | SHORT | 28.6% | -$0.12 | 7 (7d) | BLACKLISTED 2026-09-28 — no new trades since. 7T are pre-blacklist residuals. |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 100% | +$0.81 | 5 (24h) | STRONG — 58.8% WR 7d, +$0.51. EXTREME regime 52.2% all-time. |
| doji-bottom-long | LONG | 100% | +$0.16 | 1 (24h) | Single trade, too early to judge |
| rs-s94 | LONG | 100% | +$0.07 | 1 (24h) | Single trade |
| rs-s38 | LONG | 100% | +$0.09 | 1 (24h) | Single trade |
| rs-s56 | LONG | 100% | +$0.19 | 1 (24h) | Single trade |

## ISSUES
- **No signal inversions** found (24h)
- **accel-300-breakout** blacklisted 2026-09-28 — 7T pre-blacklist trades still in DB showing 28.6% WR. Blacklist is working (no new trades since).
- **pullback-entry- SHORT cold streak** — 0% WR this week on HIGH+EXTREME (normally profitable regimes). All-time data supports signal. Recommend watching, not killing.

## Regime Context (7d)
| Regime | SHORT WR | SHORT PnL | Notes |
|--------|----------|-----------|-------|
| EXTREME | 56.5% | +$3.44 | Best SHORT regime |
| HIGH | 42.9% | -$3.33 | Dead zone — 39% of all trades |
| NORMAL | 44% | -$0.79 | Struggling |

## Next Actions
1. Monitor pullback-entry- — if 14d WR drops below 45%, consider regime-specific kill
2. Watch mover+ — if 7d WR stays below 25% with 10+ trades, kill
3. No immediate kills or boosts required
