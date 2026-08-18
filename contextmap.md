# Context Map — Signal Registry

**Last updated: 2026-08-18 (Daily Orchestrator)**

Quick reference for agent sessions. Maps signals → flags → status → key params.

## Enabled Signals (actively trading)

| Signal | File | Flags | Direction | WR (7d) | PnL (7d) | Notes |
|--------|------|-------|-----------|---------|----------|-------|
| bb_bounce+ | bb_bounce.py | BB_BOUNCE_PLUS_ENABLED=True | LONG | 58.3% | +$0.21 | Top performer. Confluence signal. |
| bb_bounce- | bb_bounce.py | BB_BOUNCE_MINUS_ENABLED=False | SHORT | — | — | Disabled. |
| bb_bounce_short | bb_bounce_short.py | BB_BOUNCE_SHORT_ENABLED=True | SHORT | ~50% | +$0.14 | SHORT-specific with regime filter. |
| hl_copy_trader | (standalone bypass) | STANDALONE_BYPASS | LONG | — | — | Copy-trading, bypasses confluence. |
| r2_trend_long2 | r2_trend_long.py | R2_TREND_LONG_ENABLED=True | LONG | 64.7% | +$0.19 | Strong. Catches slow grinds (R²>0.6). |
| r2_trend_long3 | r2_trend_long.py | R2_TREND_LONG_ENABLED=True | LONG | 33.3% | -$0.15 | Borderline. Can't disable individually. |
| r2_trend_long4 | r2_trend_long.py | R2_TREND_LONG_ENABLED=True | LONG | 55.6% | $0.00 | Break-even. |
| return_exhaustion+ | return_exhaustion.py | RETURN_EXHAUSTION_PLUS_ENABLED=True | LONG | 71.4% | +$0.32 | Top performer. Extreme negative reversion. |
| return_exhaustion_short | return_exhaustion_short.py | RETURN_EXHAUSTION_SHORT_ENABLED=True | SHORT | — | — | SHORT-specific. |
| stop_hunt_reversal_long+ | stop_hunt_reversal_long.py | STOP_HUNT_REVERSAL_LONG_PLUS_ENABLED=True | LONG | ~75% | +$0.06 | Good. |
| spike_exhaustion_short | spike_exhaustion_short.py | SPIKE_EXHAUSTION_SHORT_ENABLED=True | SHORT | — | — | SHORT-specific. |
| rs | rs.py | RS_ENABLED=True | LONG | — | — | Re-enabled Aug 6. Support/resistance. |
| r2_trend_short | r2_trend_short.py | R2_TREND_SHORT_ENABLED=True | SHORT | — | — | Downtrend detector. |
| hmacd_bare+ | hmacd.py | HMACD_PLUS_ENABLED=True | LONG | — | — | 15m+1H histogram agreement. |
| hmacd_mtf+ | mtf_macd.py | HMACD_PLUS_ENABLED=True | LONG | — | — | Z-score + histogram + cascade. |
| hmacd_bare- | hmacd.py | HMACD_MINUS_ENABLED=True | SHORT | — | — | SHORT direction. |
| hmacd_mtf- | mtf_macd.py | HMACD_MINUS_ENABLED=True | SHORT | — | — | SHORT direction. |
| macd_1m+ | macd_1m.py | MACD_1M_PLUS_ENABLED=True | LONG | — | — | 1m MACD. |
| macd_1m- | macd_1m.py | MACD_1M_MINUS_ENABLED=True | SHORT | — | — | 1m MACD SHORT. |
| engulfing+ | engulfing.py | ENGULFING_PLUS_ENABLED=True | LONG | — | — | Bullish engulfing. |
| engulfing- | engulfing.py | ENGULFING_MINUS_ENABLED=True | SHORT | — | — | Bearish engulfing. |
| momentum_leaderboard- | momentum_leaderboard.py | MOMENTUM_LEADERBOARD_MINUS_ENABLED=True | SHORT | — | — | SHORT direction only. |
| trend_purity- | trend_purity.py | TREND_PURITY_MINUS_ENABLED=True | SHORT | — | — | SHORT direction only. |
| wyckoff+ | wyckoff.py | WYCKOFF_PLUS_ENABLED=True | LONG | — | — | Accumulation spring. |
| wyckoff- | wyckoff.py | WYCKOFF_MINUS_ENABLED=True | SHORT | — | — | Distribution upthrust. |

## Dead Signals (NEVER_REENABLE)

All in `NEVER_REENABLE_FLAGS` — signal_rotator skips these permanently.

| Signal | Killed | Reason |
|--------|--------|--------|
| ct-hot+ / ct-hot- | 2026-08-17 | 42.4% WR -$0.42/7d. NEUTRAL regime noise. |
| hzscore+ / hzscore- | 2026-08-17 | 38% / 54.3% WR. Inverted R:R. Combos bleeding. |
| wave_catcher+ / - | 2026-08-17 | Both variants dead. |
| accel-300 (all variants) | 2026-08-17 | 0% WR over 48h. Permanent. |
| range_breakout+ / short | 2026-08-16/17 | 25% WR, 0% WR. Dead. |
| range_finder (all) | 2026-08-16 | R:R 0.12:1. Never captures gains. |
| continuation+ / - | 2026-08-16 | 40% WR -$0.17. Re-entry not working. |
| trend_momentum_near_sma+ | 2026-08-12 | 16.7% WR -$0.37. |
| vel_hermes (all) | 2026-08-04 | 0% WR (12 trades). No edge. |
| tl_break+ | 2026-08-07 | 33.3% WR -$1.33. Hemorrhaging. |
| zscore_rising (all) | 2026-08-07 | 38.6% WR -$1.37. No edge. |
| gap_300 (all) | — | 14.3% WR -$1.52. Worst active loser. |
| squeeze_cross (all) | 2026-07-28 | 0% LONG, 40% SHORT. No edge. |
| vortex_break+ / - | 2026-08-09/10 | 22.2% / sub-threshold. |
| pct_hermes (all) | 2026-05-06 | Signals now fire via signals_runner. |

## Key Filter System

All signals pass through these filters before execution:

| Filter | Flag | Purpose |
|--------|------|---------|
| Context Gate | CONTEXT_GATE_ENABLED | LLM + rule-based context check |
| Signal Filter | SIGNAL_FILTER_ENABLED | Master filter switch |
| Spike Filter | SPIKE_FILTER_ENABLED | Reject spike entries |
| Z-Score Accel | ZSCORE_ACCEL_ENABLED | Z-score + acceleration alignment |
| Directional Outcome | DIRECTIONAL_OUTCOME_ENABLED | Trade outcome velocity/integral |
| Weather Vané Shield | WEATHER_VANE_SHIELD_ENABLED | Regime-aware position shield |
| Tide | TIDE_ENABLED | BTC momentum tide detection |
| Volatility Floor | VOL_FLOOR_ENABLED | Reject low-vol entries (0.15%) |
| Token Sentiment | TOKEN_SENTIMENT_ENABLED | Blacklist chronic losers |
| Similar Setup Lookup | SIMILAR_SETUP_LOOKUP_ENABLED | Avoid repeated setups |

## Key Exit System

| Exit | Flag | Params |
|------|------|--------|
| PM_TRAIL | PM_TRAIL_ENABLED | act 0.40%, dist 0.20% — DOMINANT exit |
| ATR_SL | (always on) | ATR-based stop loss |
| Cut Loser | CUT_LOSER_ENABLED | Emergency loss cut |
| Stale Rotation | STALE_ROTATION_ENABLED | PAUSED — closing too aggressively |
| Time Exit | TIME_EXIT_ENABLED | DISABLED — 0% WR |
| Peak Exit | PEAK_EXIT_ENABLED | DISABLED — 0% WR |

## Confluence Combos

Active combos in hotset (bb_bounce+ pairs with other signals):

| Combo | Status | WR |
|-------|--------|-----|
| bb_bounce+,hl_copy_trader | Active | 50.0% |
| bb_bounce+ (standalone) | Active | 58.3% |
| r2-trend-long2 (standalone) | Active | 64.7% |
| return_exhaustion+ (standalone) | Active | 71.4% |

## STANDALONE_BYPASS

Signals that bypass confluence check:
- `hl_copy_trader` — copy-trading, different logic

## Signal Pipeline Flow

```
signals_runner.py → signals/*.py → add_signal() → signal_compactor.py → hotset.json → position_manager.py
                                        ↓
                                  signal_analyst.py (breakout engine)
                                        ↓
                              filters (context_gate, vol_floor, zscore_accel, etc.)
```

## Source Files

- Signal registry: `scripts/signals/__init__.py`
- Constants: `scripts/hermes_constants.py` (line 895+ for NEVER_REENABLE_FLAGS)
- Compactor: `scripts/signal_compactor.py` (suppression weights)
- Schema: `scripts/signal_schema.py`
