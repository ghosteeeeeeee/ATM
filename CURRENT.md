# Current State — System Improvement Focus

**Last Updated: 2026-08-30 ~07:10 UTC (Orchestrator run)**
**Updated by: Orchestrator**

## Current Status

System GREEN, positive. 4 open SHORT positions. Pipeline running, all key timers firing.

- **24h:** 37T, 62% WR, +$0.27 (positive)
- **7d:** ~430T, 51% WR, -$1.76 (flat, improving post-legacy)
- **Daily trend:** Aug 25 -$1.79 → Aug 28 +$1.55 → Aug 29 -$0.01 → Aug 30 +$0.27
- **Market:** ALL NEUTRAL (105 tokens, 0 trending)
- **Disk:** 78%
- **Open positions:** 4 SHORT (KAS -24%, MET +5%, SAND +5%, GMT +9%)
- **Legacy bleed:** COMPLETE. All legacy trades cleared. System clean.
- **STAR signal:** macd-div- SHORT 3T/24h 33% WR -$0.13 (weak sample, monitoring)
- **Backbone:** bb-bounce-short SHORT 20T/24h 65% WR +$0.21 (dominant), accel-300-v2- SHORT (MIN_GAP=2.0 filtering)
- **ATR_SL:** Trailing working — 97.8% hit rate, avg +$0.008/trade. MIN_GAP=2.0 active.

**System has 2 backbone signals + STAR.** 10th DELEGATION to signal_analyst: build new backbone (pending).

**Orchestrator 07:10 — MONITORING.** Pipeline healthy (cycle #177464). 4 open SHORT, 38 closed today +6.71% PnL. Market ALL NEUTRAL. 7 trades today 71.4% WR +$0.036. Signal reporter: no kills, bb-bounce-short dominant (19T 68.4% WR +$0.29 24h). Auto-1hr: no changes, 24h +$0.27. ATR_SL trailing 97.8% hit rate. MIN_GAP=2.0 filtering weak accel-300-v2- entries. Disk 78%. System green, nothing broken. Signal starvation (market neutral).

## Today's Changes (Aug 30)

0. **Orchestrator 07:10 — MONITORING.** Pipeline healthy (cycle #177464). 4 open SHORT, 38 closed today +6.71% PnL. Market ALL NEUTRAL. 7 trades today 71.4% WR +$0.036. Signal reporter: no kills, bb-bounce-short dominant (19T 68.4% WR +$0.29 24h). Auto-1hr: no changes, 24h +$0.27. ATR_SL trailing 97.8% hit rate. MIN_GAP=2.0 filtering weak accel-300-v2- entries. Disk 78%. System green, nothing broken. Signal starvation (market neutral). 10th delegation to signal_analyst STILL PENDING.
1. **CEO 06:00 — MONITORING.** Verified DB: 24h 36T 66.7% WR +$0.33. 7d: 429T 51.3% WR -$1.76. 2 open SHORT (bb-bounce-short, flat). bb-bounce-short improved to 65.1% WR (back above 65% kill trigger). 24h: bb-bounce-short 19T 68.4% WR +$0.29 (strong). Legacy trades aging out with zero new entries. ATR_SL trailing working. MIN_GAP=2.0 active. System green, nothing broken. Signal starvation (36T/24h). Disk 77%.
2. **CEO 02:30 — MONITORING.** Acknowledged bb_bounce V2 monitoring task. bb-bounce-short 65.1% WR (at kill trigger threshold). Monitoring weekly. Revert procedure ready.

## Today's Changes (Aug 29)

0. **CEO 19:00 — ACTION.** Raised ACCEL_300_V2_SHORT_MIN_GAP 1.0→2.0. ROOT CAUSE: ATR_SL 49 exits/48h -$4.50 — entries at poor locations. Backtest: no loser had gap>2.0%. FIX: raised MIN_GAP to 2.0 to filter weak entries. Disk 78%.
1. **CEO 16:00 — ACTION.** Killed ACCEL_300_V2_MINUS_ENABLED=False (4T/7d 25% WR -$0.14, all losses). Added to NEVER_REENABLE_FLAGS.
2. **CEO 14:30 — ACTION.** Killed ACCEL_300_V2_LONG_ENABLED=False (0 trades in 24h+, dead signal). Added to NEVER_REENABLE_FLAGS.
3. **CEO 13:15 — ACTION.** Killed 2 dead signals: INVERSE_ACCEL_300_V2_ENABLED=False, ACCEL_300_V2_LONG_5M_ENABLED=False. Both added to NEVER_REENABLE_FLAGS.
4. **CEO 09:30 — MONITORING.** Fixed .pyc cache for ACCEL_300_V2_LONG_5M_ENABLED NameError.

## Today's Changes (Aug 28)

1. **CEO 23:10 — MONITORING.** 24h 89T 56.2%WR +$1.55 (best day in weeks). 7d: 448T 49.6%WR -$3.96. Legacy bleed: ct-hot+ -$3.91/7d (CEO_PROTECTED), hl_copy SHORT -$0.65/7d, slow-grind- -$0.64/7d. WITHOUT LEGACY: system fully profitable. Disk 83%.
2. **CEO 06:50 — MONITORING.** 24h 73T 53.4% WR +$0.63. 4 consecutive positive hours. System improving.
3. **Orchestrator 06:35 — DISK CLEANUP.** Journal vacuumed to 500MB (-2G), pump_hunter.log truncated (-24MB). Disk 84% → 83%.
4. **CEO 02:35 — KILLED ATR_SPIKE_ENABLED.** 7T/7d 28.6% WR -$0.15, ALL atr_sl_hit exits. Disabled + added to NEVER_REENABLE.

## Active Decisions

- **DELEGATED to signal_analyst: build new backbone signal.** Volume+momentum based, must pass 2-type confluence gate. Priority: LONG for Wyckoff accumulation market. — 2026-08-26 (RE-DELEGATED 2026-08-27, 10th delegation STILL PENDING)
- **CONF_FILTER_MAX=89.** Blocks overconfident trades, 90+ tier now +$1.91/7d. — 2026-08-24
- **SHORT_NEUTRAL_BLOCK_ENABLED=True.** Uses 4h regime from PostgreSQL momentum_cache. — 2026-08-23
- **macd-div- is STAR signal.** 27T/7d 70.4% WR +$0.23. Inverted R:R (avg win +2.79%, avg loss -4.90%). — 2026-08-29
- **tl_break_short INVERTED R:R.** 16T/7d 62.5% WR -$0.11 (avg win +2.13%, avg loss -5.19%). CEO_PROTECTED. — 2026-08-27
- **hzscore- RE-ENABLED BY T.** SHORT 7d 10T +$0.09, 50% WR (inverted R:R). CEO_PROTECTED. Recommend T disable. — 2026-08-23
- **bb-bounce-short EMERGING.** 43T/7d 65.1% WR +$0.29. Improved from 62.5% baseline — back above 65% kill trigger. Monitor weekly. — 2026-08-30
- **LEGACY AGE-OUT COMPLETE.** All legacy trades cleared (ct-hot+, slow-grind-, hl_copy SHORT, pump-catcher+, atr-spike+, continuation-). System now clean. — 2026-08-29
- **ACCEL_300_V2_SHORT_MIN_GAP=2.0.** Raised from 1.0. Backtest: no loser had gap>2.0%. Filters weak entries. — 2026-08-29

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **DELEGATE to signal_analyst: build new backbone signal.** 10th delegation — MUST produce. Volume+momentum, 2-type confluence gate, LONG priority for Wyckoff accumulation market. — 2026-08-30
2. **Monitor 4 open SHORT positions.** KAS -24%, MET +5%, SAND +5%, GMT +9%. ATR_SL trailing will manage. — 2026-08-30
3. **Monitor disk.** Currently 78%. Below 85% trigger. — 2026-08-30
4. **Monitor system performance post-legacy.** 7d at -$1.76 — track if improving now clean. — 2026-08-30
5. **Monitor MIN_GAP=2.0 impact.** Effect should show in next 24h — fewer accel-300-v2- trades, higher WR. — 2026-08-30
