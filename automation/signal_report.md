# Signal Performance Report
Generated: 2026-08-11 19:30 UTC

## 6h Performance
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| trend_momentum_near_sma+ | LONG | 3 | 0.0% | -$0.35 |
| hzscore+ | LONG | 5 | 60.0% | -$0.01 |
| hzscore- | SHORT | 2 | 50.0% | +$0.01 |
| hzscore+,trend_momentum_near_sma+ | LONG | 2 | 50.0% | +$0.01 |

## 24h Performance (3+ trades)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| trend_momentum_near_sma+ | LONG | 3 | 0.0% | -$0.35 |
| bb_bounce+,hzscore+ | LONG | 6 | 16.7% | -$0.18 |
| hzscore+ | LONG | 5 | 60.0% | -$0.10 |

## KILLED (executed): None
No signals met all kill criteria (WR<30%, 5+ trades, active>24h, PnL<-$0.10).

## BOOSTED (executed): None
No signals met all boost criteria (WR>55%, 5+ trades, PnL>$0.05, consistent across tokens).

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| trend_momentum_near_sma+ | LONG | 0.0% | -$0.35 | 3 | **BUG: contrarian flip not applied** |
| bb_bounce+,hzscore+ | LONG | 16.7% | -$0.18 | 6 | 24h bad streak, all-time 48.5% WR +$0.20 |
| hzscore+ | LONG | 60.0% | -$0.01 | 5 | Good WR, breakeven PnL |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| hzscore+,mover+ | LONG | 80.0% | +$0.17 | 5 | Strong |
| hzscore-,range_breakout- | SHORT | 100.0% | +$0.10 | 2 | Strong |
| bb_bounce+,range_finder+ | LONG | 58.5% | +$0.71 | 53 | System workhorse |

## Signal Inversions: None found

## Issues

### FIXED: Contrarian flip not applied to trend_momentum_near_sma
- **Root cause:** `signal_compactor.py:765` contrarian flip was only in the confluence gate section. Standalone `trend_momentum_near_sma+` signals bypass this via the backtested standalone path (HOTSET-FINAL-BYPASS, PRESERVE-MERGE-BYPASS, PENDING-APPROVE-BYPASS, SAFETY-FILTER-BYPASS) — a completely separate code path that never reached the flip.
- **Fix:** Added contrarian flip to all 4 bypass paths in signal_compactor.py (lines 1179, 1229, 1424, 1585). Signals will now be flipped to SHORT before reaching decider_run.
- **Impact:** 0% WR, -$0.35 on 3 trades — should improve to ~50%+ WR once flip is active.

### MEGA token: Recent cluster of losses
- 4 of last 6 `bb_bounce+,hzscore+` trades on MEGA hit ATR SL
- MEGA already blacklisted (line 132: "5 trades, 0% WR, -$0.23 — low-price noise coin")
- Blacklist is working — no new MEGA trades should fire

## Full History (all-time winners)
| Signal | Trades | WR | PnL |
|--------|--------|-----|-----|
| accel-300-,rs-s-broken | 1025 | 46.2% | +$6.22 |
| bb_bounce+,range_finder+ | 53 | 58.5% | +$0.71 |
| tl_break_long | 94 | 37.2% | +$0.58 |
| bb_bounce+,hzscore+ | 33 | 48.5% | +$0.20 |
| bb_bounce | 27 | 51.9% | +$0.33 |
| hzscore+,mover+ | 5 | 80.0% | +$0.17 |
| inv-accel-300+,tl_break_long | 8 | 12.5% | +$0.13 |
