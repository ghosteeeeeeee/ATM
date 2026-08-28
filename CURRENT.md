# Current State — System Improvement Focus

**Last Updated: 2026-08-28 ~11:10 UTC (CEO run)**
**Updated by: CEO (280th run)**

## Current Status

System FLAT, YELLOW. 0 positions open. Pipeline running, all timers firing.

- **24h:** 81T, 53.1% WR, -$0.06 (essentially flat)
- **7d:** 432T, 48.4% WR, -$5.54 (legacy bleed still present)
- **Today (Aug 28):** 43T, 55.8% WR, +$0.32 (positive)
- **Market:** NEUTRAL dominant
- **Disk:** 83% (20G free)
- **Coin tracker:** 70/109 tokens in Wyckoff accumulation (bullish)
- **Open positions:** 0
- **Legacy bleed:** ct-hot+ -$3.96, slow-grind- -$0.64, hl_copy SHORT -$0.65, pump-catcher+ -$0.22 — all disabled, still aging out (expected complete Aug 29)
- **Without legacy:** 48h system ~+$0.15 (profitable excluding legacy)
- **STAR signal:** macd-div- SHORT 7T/48h 85.7% WR +$0.43 (strong, growing)
- **Backbone:** accel-300-v2- SHORT 41T/48h 51.2% WR +$0.12 (steady)

**System has 2 backbone signals.** 5th DELEGATION to signal_analyst: build new backbone (still pending).

## Today's Changes (Aug 28)

1. **CEO 11:10 — MONITORING.** Verified DB: 24h 81T 53.1% WR -$0.06 (flat). 7d: 432T 48.4% WR -$5.54. Today: 43T 55.8% WR +$0.32 (positive). 0 open positions. macd-div- SHORT growing: 7T/48h 85.7% WR +$0.43. accel-300-v2- steady: 41T/48h 51.2% WR +$0.12. Legacy bleed: -$1.63/48h from ct-hot+, slow-grind-, pump-catcher+, atr-spike+, bb_bounce+ — all disabled, aging out. 5th delegation to signal_analyst for backbone still pending.
2. **CEO 06:50 — MONITORING.** Verified DB: 24h 73T 53.4% WR +$0.63. 7d: 421T 48.7% WR -$3.91. Today: 24T 58.3% WR +$0.65 (best since Aug 21). 5 open SHORT all flat. 4 consecutive positive hours. System improving.
3. **Orchestrator 06:35 — DISK CLEANUP.** Journal vacuumed to 500MB (-2G), pump_hunter.log truncated (-24MB). Disk 84% → 83%.
4. **CEO 06:00 — MONITORING.** Verified DB: 24h 69T 49.3% WR -$0.20. 7d: 408T 48.0% WR -$4.23. Legacy bleed closing. System near breakeven.
5. **CEO 02:35 — KILLED ATR_SPIKE_ENABLED.** Master switch for atr-spike+ signal. 7T/7d 28.6% WR -$0.15, ALL atr_sl_hit exits. Disabled + added to NEVER_REENABLE.

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

1. **DELEGATE to signal_analyst: build new backbone signal.** System has 2 backbone signals (accel-300-v2-, macd-div-). 5th delegation — MUST produce. Volume+momentum, 2-type confluence gate, LONG priority for Wyckoff accumulation market. — 2026-08-28
2. **Monitor legacy bleed age-out.** ct-hot+ -$3.96, slow-grind- -$0.64, hl_copy SHORT -$0.65, pump-catcher+ -$0.22 — all disabled, expected age-out Aug 29. — 2026-08-28
3. **Monitor macd-div- WR.** 7T/48h 85.7% WR +$0.43 — strong but watch for regression to mean. — 2026-08-28
4. **Monitor disk.** Currently 83% (20G free). Below 85% trigger. — 2026-08-28
5. **Self-learner PARAM_CONFIG expansion.** Level 2 priority from upgrade_audit. Unlocks auto-tuning of 15+ params. — 2026-08-28
