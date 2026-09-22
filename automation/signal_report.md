=== Signal Performance Report ===
Period: Last 6h | 24h | Generated: 2026-09-22 22:45 UTC

## 24h Summary
Total closed trades: 25 (6h: 4)

## KILLED (executed):
None — no signals met blanket-kill criteria.

## REGIME BLOCKS (executed):
None — existing blocks already cover losing regimes.
- pullback-entry- SHORT: Already blocked in NORMAL (0.0x). Wins in HIGH (53.4% WR) and EXTREME (55.2% WR). 24h losses are noise.
- pump-chain+ LONG: Already blocked in NORMAL (Pump_Flow 0.0x). Wins in EXTREME (46.9% WR). 24h losses are noise.

## BOOSTED (executed):
None — no signals met boost criteria.

## FAMILY_MAP FIXES (executed):
- Added `pump-chain`, `pump-chain+`, `pump-chain-` to `Pump_Flow` family (were mapping to `Other`)
- Added `bb-bounce-v2-long`, `bb-bounce-v3-long` to `Bollinger` family
- Added `continuation` to `Continuation` family
- Added `grind-breakout` to `Grind_Breakout` family
- Added `mover` to `Mover` family
- Added `doji-bottom-long` to `Exhaustion` family

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 0.0% | -$1.54 | 6 | Watch — all-time wins in HIGH/EXTREME, 24h bad luck |
| pump-chain+ | LONG | 16.7% | -$0.85 | 6 | Watch — all-time wins in EXTREME, 24h bad luck |
| pump-chain- | SHORT | 33.3% | -$0.38 | 6 | Watch — all-time wins in all regimes, 24h noise |

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| (no signal won 3+ trades in 24h) | | | | | |

## ISSUES:
- **FAMILY_MAP gap fixed**: `pump-chain+` and `pump-chain-` were mapping to `Other` instead of `Pump_Flow`. This meant the existing NORMAL regime block (Pump_Flow 0.0x) was NOT blocking these signals. Fixed by adding hyphen variants to Pump_Flow family.
- **No signal inversions detected** in 24h window.
- **Low trade volume**: Only 25 trades in 24h, 4 in 6h. Market may be quiet.
- **All 24h losers are losing in regimes where they win all-time** — classic noise, not signal decay.
