# Current State — System Improvement Focus

**Last Updated: 2026-08-27 ~18:35 UTC (Orchestrator)**
**Updated by: Orchestrator (daily run)**

## Current Status

System GREEN, IDLE. 5/5 positions open (all SHORT). Pipeline running, all timers firing.

- **24h:** 107T, 47.7% WR, -$0.43 (near breakeven)
- **7d:** 366T, 51.1% WR, +$0.10 (flat)
- **Today (Aug 27):** 62 closed. Kill actions: atr-spike+ (signal_reporter), slow-grind- (CEO), bb_bounce+ (CEO, twice), pump-catcher+ (CEO).
- **Market:** 104 NEUTRAL / 1 LONG / 1 SHORT — heavily neutral, low directional activity.
- **Disk:** 83% (20G free)
- **Open positions:** POL SHORT (accel-300-v2-), ALT SHORT (r2-trend), USUAL SHORT (macd-div-), GMT SHORT (rs-r34), DYDX SHORT (rs-r38)

**System has ZERO backbone signals.** DELEGATED to signal_analyst: build new backbone.

## Today's Changes (Aug 27)

1. **slow-grind- KILLED (CEO 18:20)** — Flag still True despite kill documented Aug 26. SLOW_GRIND_SHORT_ENABLED=False + NEVER_REENABLE. Second time kill was documented but not applied.
2. **bb_bounce+ KILLED AGAIN (CEO 18:04)** — 48h 9T/11.1%WR/-$0.74 after CEO re-enable at 14:00. BB_BOUNCE_PLUS_ENABLED=False, BB_BOUNCE_ENABLED=False, NEVER_REENABLE.
3. **pump-catcher+ KILLED (CEO 14:30)** — 21T/7d 33.3% WR -$0.39, 76.2% ATR_SL hit rate. PUMP_CATCHER_ENABLED=False, NEVER_REENABLE.
4. **atr-spike+ KILLED (signal_reporter 17:09)** — 7T/7d 28.6% WR -$0.15. ATR_SPIKE_PLUS_ENABLED=False, NEVER_REENABLE. macd-div- weight boosted 1.0→1.25.
5. **accel_300_v2 FIXED (health monitor 18:20)** — V2_MIN_GAP_PCT was undefined (NameError), signal emitting 0 signals. Added V2_MIN_GAP_PCT = 1.5.

## Active Decisions

- **DELEGATED to signal_analyst: build new backbone signal.** Volume+momentum based, must pass 2-type confluence gate. Priority: LONG for Wyckoff accumulation market (71/109 tokens). — 2026-08-26
- **CONF_FILTER_MAX=89.** Blocks overconfident trades, 90+ tier now +$1.91/7d. — 2026-08-24
- **SHORT_NEUTRAL_BLOCK_ENABLED=True.** Uses 4h regime from PostgreSQL momentum_cache. — 2026-08-23
- **tl_break_short INVERTED R:R.** 16T/7d 62.5% WR -$0.11 (avg win +2.32%, avg loss -5.19%). CEO_PROTECTED. — 2026-08-27
- **hzscore- RE-ENABLED BY T.** SHORT 7d 8T -$0.18, 50% WR (inverted R:R). CEO_PROTECTED. Recommend T disable. — 2026-08-23

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **DELEGATE to signal_analyst: build new backbone signal.** System has ZERO backbone signals. — 2026-08-27
2. **Monitor legacy bleed age-out.** ct-hot+ -$3.65/7d, slow-grind- -$0.64/7d, hl_copy SHORT -$0.76/7d — all dead, should age out by Aug 28. — 2026-08-27
3. **Monitor macd-div- performance.** 21T/7d 76.2% WR +$0.31 — STAR signal, now boosted. — 2026-08-27
4. **Monitor disk (85% cleanup trigger).** Currently 83%, 20G free. — 2026-08-27
5. **Monitor lifecycle filter impact (48h eval ending ~Aug 28).** Watch ATR_SL hit rate. — 2026-08-26
