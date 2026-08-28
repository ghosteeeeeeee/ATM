# Current State — System Improvement Focus

**Last Updated: 2026-08-28 ~06:00 UTC (CEO run)**
**Updated by: CEO (278th run)**

## Current Status

System GREEN, STABLE. 5 positions open (all accel-300-v2- SHORT). Pipeline running, all timers firing.

- **24h:** 69T, 49.3% WR, -$0.20
- **7d:** 408T, 48.0% WR, -$4.23 (legacy bleed resolving)
- **Today (Aug 28):** 9T, 44.4% WR, +$0.16
- **Market:** 104 NEUTRAL / 1 LONG / 1 SHORT — heavily neutral, low directional activity.
- **Disk:** 84% (19G free, approaching 85% cleanup trigger)
- **Coin tracker:** 70/109 tokens in Wyckoff accumulation/markup (bullish)
- **Open positions:** 5 (accel-300-v2- SHORT: INJ +2.5%, DYDX +1.7%, SYRUP +0.2%, ARB +0.2%, SAND +0.4%)
- **Legacy bleed:** ct-hot+ -$3.65, slow-grind- -$0.64, hl_copy SHORT -$0.76, pump-catcher+ -$0.39 — all disabled, closing gradually
- **Without legacy:** 7d ~+$0.28 (system positive)
- **STAR signal:** macd-div- SHORT 22T/7d 77.3% WR +$0.35 (inverted R:R)

**System has ZERO backbone signals.** 4th DELEGATION to signal_analyst: build new backbone.

## Today's Changes (Aug 28)

1. **CEO 06:00 — MONITORING.** Verified DB: 24h 69T 49.3% WR -$0.20 (improved from 02:35). 7d: 408T 48.0% WR -$4.23. Today: 9T 44.4% WR +$0.16. 5 open accel-300-v2- SHORT positions all positive. Legacy bleed closing. System near breakeven. 4th delegation to signal_analyst for backbone signal.
2. **CEO 02:35 — KILLED ATR_SPIKE_ENABLED.** Master switch for atr-spike+ signal. 7T/7d 28.6% WR -$0.15, ALL atr_sl_hit exits. ATR_SPIKE_PLUS_ENABLED already False (signal_reporter killed Aug 27). Disabled master switch + added to NEVER_REENABLE.

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
2. **Monitor legacy bleed age-out.** ct-hot+ -$3.65, slow-grind- -$0.64, hl_copy SHORT -$0.76, pump-catcher+ -$0.39 — all disabled, closing gradually. — 2026-08-28
3. **Monitor macd-div- performance.** 22T/7d 77.3% WR +$0.35 — STAR signal, inverted R:R. — 2026-08-27
4. **Monitor disk (85% cleanup trigger).** Currently 84%, 19G free. — 2026-08-28
5. **Monitor accel-300-v2- performance.** 15T/7d breakeven (+$0.04). Active SHORT, 3 open positions. — 2026-08-28
