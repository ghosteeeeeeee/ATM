=== Signal Performance Report ===
Period: 2026-09-27 05:09 UTC | 6h: 0 trades closed | 24h: 0 trades closed | 7d window used

## Pipeline Status
- Signals generated: 156 (6h) | 956 (24h)
- Trades closed: 0 (6h) | 1 (24h) — continuum_engine LONG BTC, $0.00
- Open positions: 0
- Live trading: ENABLED (kill switch: True)
- Hotset: 0 tokens (signals passing filters but not executing)
- **Note:** Pipeline is generating signals but none are reaching execution. Normal when signals don't pass context gate, volatility gate, and position limits.

## KILLED (executed — all already disabled)
| Signal | Dir | WR | PnL | Trades | Action | Date |
|--------|-----|-----|-----|--------|--------|------|
| range_reversion+ | LONG | 16.7% | -$0.62 | 6/30d | DISABLED | 2026-09-02 |
| pullback-entry+ | LONG | 16.7% | -$0.57 | 6/30d | DISABLED | 2026-09-10 |
| ema300-dip-long | LONG | 20.0% | -$0.55 | 5/30d | DISABLED | 2026-09-15 |
| grind-trend- | SHORT | 20.0% | -$0.38 | 5/30d | DISABLED | 2026-09-19 |
| accel-300-breakout | SHORT | 28.6% | -$0.12 | 7/7d | DISABLED | 2026-09-23 |

**No new kills needed.** All underperformers already disabled in hermes_constants.py.

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb_bounce_v2_long | LONG | 74.0% | +$2.08 | 73/30d | Already enabled, top performer |
| pump_chain | LONG | 68.3% | +$1.11 | 41/30d | Already enabled |
| volume-breakout-long+ | LONG | 66.7% | +$1.46 | 18/30d | Already enabled |
| open_skies | LONG | 63.2% | +$1.56 | 19/30d | Already enabled |
| rr-struct+ | LONG | 73.3% | +$0.59 | 15/30d | Already enabled |
| mover- | SHORT | 77.8% | +$0.52 | 9/30d | Already enabled |

**No boosts needed.** Top performers already at full allocation.

## REGIME-BLOCKED (have winning regime, losing in others)
| Signal | Dir | WR | PnL | Winning Regime | Losing Regime | Action |
|--------|-----|-----|-----|----------------|---------------|--------|
| pullback-entry- | SHORT | 52.1% | +$0.35/30d | EXTREME 55%, HIGH 53% | NORMAL 47% | Blocked NORMAL via VOL_PHASE_MULTS |
| accel_300_v2_short | SHORT | 27.3% | -$0.20/30d | EXTREME 37.5% +$0.06 | HIGH 0% -$0.26 | Blocked EXTREME (family-level), but EXTREME is winning — mismatch |
| accel-300-v4-short- | SHORT | 20.0% | -$0.26/30d | EXTREME 33% +$0.05 | HIGH 0% -$0.31 | Same mismatch as above |

## LOSERS (watch list — already killed or regime-blocked)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 26.7% | -$1.59 | 15/7d | Regime-blocked NORMAL, winning in EXTREME/HIGH |
| mover+ | LONG | 25.0% | -$1.19 | 8/7d | Mover 0.0x in EXTREME, but 3 EXTREME trades in 7d (pre-block) |
| accel-300-breakout | SHORT | 28.6% | -$0.12 | 7/7d | Already DISABLED |
| ema300_dip_short | SHORT | 41.7% | -$1.48 | 24/30d | DISABLED |
| accel_300_v3_long | LONG | 43.6% | -$1.41 | 39/30d | Accelerate 0.0x EXTREME, still losing |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb_bounce_v2_long | LONG | 74.0% | +$2.08 | 73/30d | Healthy |
| volume-breakout-long+ | LONG | 66.7% | +$1.46 | 18/30d | Healthy |
| open_skies | LONG | 63.2% | +$1.56 | 19/30d | Healthy |
| pump_chain | LONG | 68.3% | +$1.11 | 41/30d | Healthy |
| rr-struct+ | LONG | 73.3% | +$0.59 | 15/30d | Healthy |
| mover- | SHORT | 77.8% | +$0.52 | 9/30d | Healthy |
| doji-bottom-long | LONG | 66.7% | +$0.40 | 6/30d | Healthy |
| continuation | LONG | 83.3% | +$0.05 | 6/30d | Healthy (small sample) |

## ISSUES
1. **No trades executing** — Pipeline generating 956 signals/day but 0 trades in 24h. Signals not passing context gate + volatility gate + position limits. Investigate if filters are too tight.
2. **Accelerate family EXTREME mismatch** — accel_300_v2_short and accel-300-v4-short- are profitable in EXTREME (+$0.06, +$0.05) but blocked there by family-level `Accelerate: 0.0` in volatility_gate_v2.py. Meanwhile they lose in HIGH where they're allowed. The EXTREME block was set for LONG variants (accel_300_v3_long). Consider making the block directional or removing it for SHORT.
3. **No signal inversions** — None found in 24h or 7d window.
4. **Hotset empty** — 0 tokens in hotset.json. May indicate compactor isn't finding qualifying signals.
