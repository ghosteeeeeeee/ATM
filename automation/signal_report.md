=== Signal Performance Report ===
Period: 2026-09-26 23:09 UTC | Last 6h: 0 trades | Last 24h: 0 trades | Last 48h: 0 trades
Total closed trades in DB: 5,325

**⚠️ QUIET PERIOD: No trades closed in 48h. Last close: 2026-09-25 02:26 UTC.**
Pipeline running normally. 0 open positions. No errors in logs.

---

## KILLED (executed this cycle)
None — no trades in 24h window to evaluate.

## BOOSTED (executed this cycle)
None — winners already enabled.

## TUNING CANDIDATES (regime-based)
| Signal | Dir | Regime | WR | PnL | Action |
|--------|-----|--------|-----|-----|--------|
| bb_bounce_short | SHORT | EXTREME | 77.8% | +$0.48 | Candidate: re-enable with EXTREME-only filter |
| bb_bounce_short | SHORT | HIGH | 52.9% | -$0.54 | Block in HIGH |
| bb_bounce_short | SHORT | NORMAL | 55.2% | -$0.44 | Block in NORMAL |
| open_skies | LONG | EXTREME | 77.8% | +$1.83 | Candidate: re-enable with EXTREME-only filter |
| accel_300_v | SHORT | HIGH | 34.8% | -$0.49 | Monitoring — net +$1.31/30d, not worth blocking |

## LOSERS (watch list — all already disabled)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ct_hot | LONG | 38.4% | -$4.07 | 99 | DISABLED (COIN_TRACKER_HOT_ENABLED=False) |
| accel_300+,rs_s | LONG | 37.8% | -$2.91 | 275 | DISABLED (ACCEL_300_PLUS_ENABLED=False) |
| ema300_dip_short | SHORT | 41.7% | -$1.48 | 24 | DISABLED (EMA300_DIP_SHORT_ENABLED=False) |
| accel_300_v3_long | LONG | 43.6% | -$1.41 | 39 | DISABLED in EXTREME via volatility_gate_v2 |
| accel_300+,rs_s,rs_s | LONG | 25.9% | -$1.21 | 27 | No regime data — combo signal |
| trend_purity+ | LONG | 36.4% | -$0.90 | 11 | DISABLED (TREND_PURITY_ENABLED=False) |
| mover+ | LONG | 57.1% | -$0.85 | 21 | DISABLED (MOVER_PLUS_ENABLED=False) |
| slow_grind | LONG | 40.0% | -$0.80 | 15 | DISABLED (SLOW_GRIND_LONG_ENABLED=False) |
| hl_copy_trader | SHORT | 16.7% | -$0.76 | 6 | DISABLED (HL_COPY_TRADING_ENABLED=False) |

## WINNERS (30d, 5+ trades)
| Signal | Dir | WR | PnL | Trades | Avg PnL | Status |
|--------|-----|-----|-----|--------|---------|--------|
| bb_bounce_v2_long | LONG | 74.0% | +$2.08 | 73 | +$0.029 | ✅ ENABLED — star performer |
| open_skies | LONG | 63.2% | +$1.56 | 19 | +$0.082 | ⚠️ DISABLED — EXTREME-only candidate |
| volume-breakout-long+ | LONG | 66.7% | +$1.46 | 18 | +$0.081 | ✅ ENABLED |
| accel_300_v | SHORT | 52.4% | +$1.31 | 63 | +$0.021 | ✅ ENABLED |
| pump_chain | LONG | 68.3% | +$1.11 | 41 | +$0.027 | ✅ ENABLED |
| pump-chain+ | LONG | 41.3% | +$0.95 | 80 | +$0.012 | ✅ ENABLED |
| rr-struct+ | LONG | 73.3% | +$0.59 | 15 | +$0.039 | ✅ ENABLED |
| mover- | SHORT | 77.8% | +$0.52 | 9 | +$0.058 | ✅ ENABLED |
| doji-bottom-long | LONG | 66.7% | +$0.40 | 6 | +$0.067 | ✅ ENABLED |

## ISSUES
- **No trades in 48h** — pipeline running, 0 positions open. Likely market conditions not meeting signal thresholds.
- **No signal inversions found** (checked 24h).
- **bb_bounce_short** has 77.8% WR in EXTREME but negative PnL overall — strong candidate for EXTREME-only re-enable.
- **open_skies** has 77.8% WR in EXTREME, +$1.83 — strong candidate for EXTREME-only re-enable. Currently fully disabled.
- **mtp_zscore_,rs_r SHORT** — 58 trades, 50% WR, -$0.75. All-time breakeven. No regime data (None). Watching.
