=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-10-07 ~11:00 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No signal met kill criteria (WR<30% + 5+ trades + PnL<-$0.10) |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No signal met boost floor (WR>55% + 5+ trades + multi-token) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 0.0% | -$0.21 | 2 | WATCH — 0/2 last 24h, both hard_max_loss (LDO, IMX). Below 5-trade kill floor. Regime all-time: EXTREME 48.3% (60t, +$2.07), HIGH 37.0% (27t, +$0.11), NORMAL 20% (5t, -$0.35). NORMAL regime is weakest — candidate for volatility_gate multiplier if it recurs. |
| pump-chain- | SHORT | 42.9% | +$0.94 | 7 | WATCH 6h only — 0/3 last 6h (-$0.16), but 24h still net positive from APT +$0.53 / LTC +$0.61. Regime: EXTREME 51.1%, NORMAL 75%, HIGH 46.2% (-$0.42 all-time). HIGH regime is the drag — if negative streak continues, gate HIGH only, do NOT blanket-kill (wins in EXTREME + NORMAL). |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| oversold-bounce+ | LONG | 100.0% | +$0.24 | 2 | Healthy — ZRO +$0.23, ENS +$0.01. Too few trades to boost. |
| mover+ | LONG | 100.0% | +$0.10 | 1 | Healthy — AVAX +$0.10. Too few trades to boost. |
| pump-chain- | SHORT | 42.9% | +$0.94 | 7 | Net positive despite mid WR — trail exits working (APT trail_sl, LTC atr_trail_hit). |

ISSUES:
- Direction inversions last 24h: 0 found. Clean.
- 24h closed volume is low (12 trades total) — most signals below statistical floors. No action justified.
- pump-chain+ NORMAL-regime trades are the structural weak spot (20% WR, 5 trades all-time). If NORMAL-regime losses repeat next cycle, add 0.0x multiplier in volatility_gate_v2.py for pump-chain+ NORMAL rather than disabling the signal.
- 6h window showed both pump-chain variants at 0% WR with hard_max_loss exits — execution/stop behavior worth a look, but 24h aggregate does not support a kill.
