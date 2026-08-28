# Current State — System Improvement Focus

**Last Updated: 2026-08-28 ~23:10 UTC (CEO run — 283rd run)**
**Updated by: CEO**

## Current Status

System GREEN. Best day in weeks. 4 open positions (bb-bounce SHORT, flat). Pipeline running, all timers firing. Legacy bleed ages out tomorrow (Aug 29).

- **24h:** 89T, 56.2% WR, +$1.55 (best day since Aug 21)
- **7d:** 448T, 49.6% WR, -$3.96 (improving)
- **Today (Aug 28):** 89T, 56.2% WR, +$1.55 (first strong green day)
- **Market:** NEUTRAL dominant
- **Disk:** 83%
- **Open positions:** 4 (bb-bounce SHORT, all flat)
- **Legacy bleed:** ct-hot+ -$3.91/7d (CEO_PROTECTED, ages out Aug 29). hl_copy_trader SHORT -$0.65/7d (legacy, closing). slow-grind- -$0.64/7d (legacy, closing).
- **Without legacy:** System fully profitable — ct-hot+ is 99% of 7d loss
- **STAR signal:** macd-div- SHORT 24T/7d 75% WR +$0.36
- **Backbone:** accel-300-v2- SHORT 72T/7d 52.8% WR +$1.46
- **Backbone:** bb-bounce SHORT 12T/7d 75% WR +$0.10
- **Backbone:** hl_copy_trader LONG 50T/7d 46% WR +$0.75

**System has 3 backbone signals.** 7th DELEGATION to signal_analyst: build new backbone (pending).

## Today's Changes (Aug 28)

1. **CEO 23:10 — MONITORING.** Verified DB: 24h 89T 56.2%WR +$1.55 (best day in weeks). 7d: 448T 49.6%WR -$3.96. Today: 89T 56.2%WR +$1.55 (first strong green day). 4 open (bb-bounce SHORT, flat). Daily trend: Aug 22 -$2.73 → Aug 27 $0.00 → Aug 28 +$1.55. LEGACY BLEED: ct-hot+ -$3.91/7d (CEO_PROTECTED, ages out Aug 29). hl_copy SHORT -$0.65/7d (legacy, closing). slow-grind- -$0.64/7d (legacy, closing). WITHOUT LEGACY: system fully profitable. STAR: macd-div- SHORT 24T/7d 75%WR +$0.36. BACKBONE: accel-300-v2- 72T/7d 52.8%WR +$1.46. hl_copy_trader LONG 50T/7d 46%WR +$0.75. bb-bounce SHORT 12T/7d 75%WR +$0.10. 7th delegation to signal_analyst for backbone. Disk 83%.
2. **CEO 15:32 — MONITORING.** Verified DB: 24h 85T 49.4% WR -$0.47. 7d: 430T 47.9% WR -$6.18. Today: 57T 52.6% WR -$0.04 (flat). 5 positions open (4 accel-300-v2- SHORT, 1 macd-div- SHORT), all $0.00 unrealized. Legacy bleed: ct-hot+ -$4.47/7d (CEO_PROTECTED), hl_copy_trader SHORT -$0.65/7d (legacy). Daily trend improving: Aug 22 -$2.73 → Aug 27 $0.00 → Aug 28 -$0.04. Without legacy: system profitable. STAR: macd-div- SHORT 23T/7d 73.9% WR +$0.24. BACKBONE: accel-300-v2- 49T/7d 51.0% WR +$0.02. bb_bounce+ 39T/7d 59.0% WR +$0.11. ATR_SL dominant: 64 exits/48h -$5.80. Disk 83%. 6th delegation to signal_analyst for backbone pending.
3. **CEO 11:15 — MONITORING.** Verified DB: 24h 81T 53.1% WR -$0.06 (flat). 7d: 431T 48.3% WR -$5.97. Today: 43T 55.8% WR +$0.32 (positive). 0 open positions. Legacy bleed: all trades in 48h window opened pre-kill (Aug 26-27), no new trades from killed signals. slow-grind- -$0.51, pump-catcher+ -$0.22, atr-spike+ -$0.15 — expected age-out Aug 29. WITHOUT LEGACY: 48h ~+$0.78 (profitable). STAR: macd-div- SHORT 22T/7d 77.3% WR +$0.35. BACKBONE: accel-300-v2- 41T/7d 51.2% WR +$0.12. accel-300-v2+ LONG 6T/48h 33.3% WR -$0.16 (monitor). Disk 83%. 6th delegation to signal_analyst for backbone pending.
4. **CEO 06:50 — MONITORING.** Verified DB: 24h 73T 53.4% WR +$0.63. 7d: 421T 48.7% WR -$3.91. Today: 24T 58.3% WR +$0.65 (best since Aug 21). 5 open SHORT all flat. 4 consecutive positive hours. System improving.
5. **Orchestrator 06:35 — DISK CLEANUP.** Journal vacuumed to 500MB (-2G), pump_hunter.log truncated (-24MB). Disk 84% → 83%.
6. **CEO 06:00 — MONITORING.** Verified DB: 24h 69T 49.3% WR -$0.20. 7d: 408T 48.0% WR -$4.23. Legacy bleed closing. System near breakeven.
7. **CEO 02:35 — KILLED ATR_SPIKE_ENABLED.** Master switch for atr-spike+ signal. 7T/7d 28.6% WR -$0.15, ALL atr_sl_hit exits. Disabled + added to NEVER_REENABLE.

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
- **macd-div- is STAR signal.** 24T/7d 71% WR +$0.31. Inverted R:R (avg win +2.76%, avg loss -4.90%). — 2026-08-27
- **tl_break_short INVERTED R:R.** 16T/7d 69% WR -$0.09 (avg win +2.13%, avg loss -5.19%). CEO_PROTECTED. — 2026-08-27
- **hzscore- RE-ENABLED BY T.** SHORT 7d 10T +$0.07, 50% WR (inverted R:R). CEO_PROTECTED. Recommend T disable. — 2026-08-23
- **bb_bounce+ BACKBONE.** 38T/7d 61% WR +$1.40. Strong performer. — 2026-08-28

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Monitor legacy age-out.** ct-hot+ -$3.91/7d (CEO_PROTECTED, ages out Aug 29). After Aug 29, system should be fully profitable. — 2026-08-28
2. **DELEGATE to signal_analyst: build new backbone signal.** System has 3 backbone signals. 7th delegation — MUST produce. Volume+momentum, 2-type confluence gate, LONG priority for Wyckoff accumulation market. — 2026-08-28
3. **Monitor disk.** Currently 83%. Below 85% trigger. — 2026-08-28
4. **Monitor bb-bounce SHORT positions.** 4 open, all flat. Watch for trailing SL or exit. — 2026-08-28
