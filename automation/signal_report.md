=== Signal Performance Report ===
Generated: 2026-09-26 17:12 UTC | Period: Last 6h / 24h / 7d

## STATUS: SYSTEM STARVED — 0 TRADES IN 38.7 HOURS

Pipeline runs every minute, 1018 signals generated in 24h, but compactor kills ALL of them.
Only 3 signals pass confluence gate per cycle, all blocked by downstream filters.

### Blockage Chain (every cycle):
1. USUAL SHORT (rs-r38): RR-HARD BLOCK — R:R=0.46 < 0.7 (risk > reward)
2. ADA SHORT (mover-): RSI floor — RSI=23.0 < 50 (extreme oversold SHORT block)
3. BCH LONG (rs-s33,rs-s38): HALL-SHAME — 30d LONG WR=42.9% < 55%
4. POL LONG (oversold-bounce+): CONFLUENCE-GATE — single-type not in standalone bypass

---

## KILLED (executed): None
No signals met kill criteria (WR<30% with 5+ trades AND PnL<-$0.10 in 24h).
Zero trades in 24h window — nothing to evaluate.

## BOOSTED (executed): None
No signals met boost criteria (WR>55% with 5+ trades in 24h).

---

## 7-DAY PERFORMANCE (broader window since 24h empty):

### LOSERS (watch list — already regime-gated):
| Signal | Dir | WR | PnL | Trades | Regime Status |
|--------|-----|-----|-----|--------|---------------|
| mover+ | LONG | 25.0% | -$1.19 | 8 | EXTREME=0.0x (added Sep 23) |
| pullback-entry- | SHORT | 40.9% | -$1.16 | 22 | NORMAL=0.0x (already blocked) |
| pump-chain- | SHORT | 45.5% | -$0.93 | 33 | EXTREME/HIGH=0.0x (already blocked) |
| accel-300-breakout | SHORT | 28.6% | -$0.12 | 7 | EXTREME only, tiny sample |

### WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 60.0% | +$0.70 | 5 | EXTREME=70%WR +$1.51 |
| continuum-osc+ | LONG | 75.0% | -$0.05 | 4 | Tiny sample, borderline |
| doji-bottom-long | LONG | 50.0% | -$0.04 | 4 | Breakeven |

---

## SIGNAL INVERSIONS: None found

## ISSUES:
1. **CRITICAL: System idle 38.7 hours** — hotset.json empty every cycle. Signals generated but all killed by filters. Root cause: current market conditions produce signals that fail RR-engine (low R:R), RSI floor (oversold SHORTs), and Hall of Shame (low WR tokens).
2. **Starvation is a filter tuning issue, not a signal quality issue** — 1018 signals in 24h proves signal generation works. The funnel is too tight for current conditions.
3. **No regime changes needed** — existing blocks (Mover EXTREME=0.0, Pullback NORMAL=0.0, Pump_Flow EXTREME/HIGH=0.0) are correctly targeting losing regimes.

---

## Daily Summary:
| Date | Trades | PnL | WR |
|------|--------|-----|-----|
| Sep 19 | 9 | +$0.25 | 55.6% |
| Sep 20 | 27 | +$2.28 | 66.7% |
| Sep 21 | 28 | -$1.12 | 25.0% |
| Sep 22 | 24 | -$2.21 | 29.2% |
| Sep 23 | 32 | -$0.20 | 46.9% |
| Sep 24 | 31 | -$2.58 | 32.3% |
| Sep 25 | 1 | +$0.05 | 100% |
| Sep 26 | 0 | $0.00 | — |
