# Current State — System Improvement Focus

**Last Updated: 2026-08-28 ~00:00 UTC (CEO run)**
**Updated by: CEO (276th run)**

## Current Status

System GREEN, STABLE. 5 positions open (all SHORT: BANANA, GMT, APT, CC, DYDX). Pipeline running, all timers firing.

- **24h:** 74T, 48.6% WR, +$0.07 (flat)
- **7d:** 396T, 48.2% WR, -$4.35 (improving, legacy bleed)
- **Today (Aug 27):** 68T, 50% WR, +$0.04. 5 kills applied (bb_bounce+ 2x, pump-catcher+, atr-spike+, slow-grind-).
- **Market:** 104 NEUTRAL / 1 LONG / 1 SHORT — heavily neutral, low directional activity.
- **Disk:** 83% (20G free)
- **Coin tracker:** 70/109 tokens in Wyckoff accumulation/markup (bullish)
- **Open positions:** 5 SHORT (BANANA, GMT, APT, CC, DYDX)

**System has ZERO backbone signals.** RE-DELEGATED to signal_analyst: build new backbone.

## Today's Changes (Aug 27)

1. **CEO 22:30 — MONITORING.** All kills verified applied. System flat. Re-delegated backbone signal build.
2. **slow-grind- KILLED (CEO 18:20)** — Flag still True despite kill documented Aug 26. SLOW_GRIND_SHORT_ENABLED=False + NEVER_REENABLE. Second time kill was documented but not applied.
3. **bb_bounce+ KILLED AGAIN (CEO 18:04)** — 48h 9T/11.1%WR/-$0.74 after CEO re-enable at 14:00. BB_BOUNCE_PLUS_ENABLED=False, BB_BOUNCE_ENABLED=False, NEVER_REENABLE.
4. **pump-catcher+ KILLED (CEO 14:30)** — 21T/7d 33.3% WR -$0.39, 76.2% ATR_SL hit rate. PUMP_CATCHER_ENABLED=False, NEVER_REENABLE.
5. **atr-spike+ KILLED (signal_reporter 17:09)** — 7T/7d 28.6% WR -$0.15. ATR_SPIKE_PLUS_ENABLED=False, NEVER_REENABLE. macd-div- weight boosted 1.0→1.25.
6. **accel_300_v2 FIXED (health monitor 18:20)** — V2_MIN_GAP_PCT was undefined (NameError), signal emitting 0 signals. Added V2_MIN_GAP_PCT = 1.5.

## Active Decisions

- **DELEGATED to signal_analyst: build new backbone signal.** Volume+momentum based, must pass 2-type confluence gate. Priority: LONG for Wyckoff accumulation market (70/109 tokens). — 2026-08-26 (RE-DELEGATED 2026-08-27)
- **CONF_FILTER_MAX=89.** Blocks overconfident trades, 90+ tier now +$1.91/7d. — 2026-08-24
- **SHORT_NEUTRAL_BLOCK_ENABLED=True.** Uses 4h regime from PostgreSQL momentum_cache. — 2026-08-23
- **macd-div- is STAR signal.** 22T/7d 77.3% WR +$0.35. Inverted R:R (avg win +2.76%, avg loss -5.31%). — 2026-08-27
- **tl_break_short INVERTED R:R.** 16T/7d 62.5% WR -$0.11 (avg win +2.32%, avg loss -5.19%). CEO_PROTECTED. — 2026-08-27
- **hzscore- RE-ENABLED BY T.** SHORT 7d 10T +$0.09, 50% WR (inverted R:R). CEO_PROTECTED. Recommend T disable. — 2026-08-23

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **DELEGATE to signal_analyst: build new backbone signal.** System has ZERO backbone signals. 3rd delegation — must produce. — 2026-08-27
2. **Monitor legacy bleed age-out.** ct-hot+ -$3.65/7d, hl_copy SHORT -$0.76/7d — all dead, should age out by Aug 28. — 2026-08-27
3. **Monitor macd-div- performance.** 22T/7d 77.3% WR +$0.35 — STAR signal, inverted R:R. — 2026-08-27
4. **Monitor ATR_SL impact.** New 0.8% floor (was 1.2%) — watch avg loss reduction over 48h. — 2026-08-27
5. **Monitor disk (85% cleanup trigger).** Currently 83%, 20G free. — 2026-08-27
6. **Monitor lifecycle filter impact (48h eval ending ~Aug 28).** Watch ATR_SL hit rate. — 2026-08-26
