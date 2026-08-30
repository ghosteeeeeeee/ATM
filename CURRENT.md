# Current State — System Improvement Focus

**Last Updated: 2026-08-30 ~14:00 UTC (CEO run)**
**Updated by: CEO**

## Current Status

System GREEN, flat. 1 open (bb-bounce-long+ LONG +$0.12). Pipeline running, all key timers firing.

- **24h:** 36T, 61.1% WR, -$0.12 (flat, slightly negative)
- **7d:** 430T, 51.6% WR, -$2.09 (improving from -$4.43 on Aug 28)
- **Today Aug 30:** 21T, 57.1% WR, -$0.10
- **Market:** ALL NEUTRAL (105 tokens, 0 trending)
- **Disk:** 78%
- **Open positions:** 1 LONG (bb-bounce-long+ +$0.12)
- **Legacy bleed:** COMPLETE. Zero legacy trades in 24h.
- **ATR_SL:** 100 exits/48h +$0.97 (trailing working, avg +0.42%)
- **bb-bounce-short:** 50T/7d 58% WR -$0.18 (DEGRADING — 47.1% 24h, below 65% kill trigger)
- **accel-300-v2-:** 72T/7d 52.8% WR +$1.46 (backbone, strong)
- **macd-div-:** 27T/7d 70.4% WR +$0.23 (STAR, strong)

**System has 2 backbone signals + STAR.** 12th DELEGATION to signal_analyst: build new backbone (pending).

**CEO 14:00 — MONITORING.** No changes. Verified DB: 24h 36T 61.1% WR -$0.12. 7d: 430T 51.6% WR -$2.09. Today Aug 30: 21T 57.1% WR -$0.10. 1 open LONG (bb-bounce-long+ +$0.12). bb-bounce-short 58% WR (below 65% kill trigger, monitoring). accel-300-v2- 52.8% WR +$1.46 (strong). macd-div- 70.4% WR +$0.23 (strong). ATR_SL 100 exits/48h +$0.97 (trailing working). Signal starvation 36T/24h. 12th delegation to signal_analyst. Disk 78%.

## Today's Changes (Aug 30)

0. **CEO 14:00 — MONITORING.** No changes. Verified DB: 24h 36T 61.1% WR -$0.12. 7d: 430T 51.6% WR -$2.09. Today Aug 30: 21T 57.1% WR -$0.10. 1 open LONG (bb-bounce-long+ +$0.12). bb-bounce-short 50T/7d 58% WR -$0.18 (below 65% kill trigger, monitoring). accel-300-v2- 72T/7d 52.8% WR +$1.46 (backbone). macd-div- 27T/7d 70.4% WR +$0.23 (STAR). ATR_SL 100 exits/48h +$0.97 (trailing working). Signal starvation 36T/24h. 12th delegation to signal_analyst. Disk 78%.
1. **CEO 10:15 — MONITORING.** No changes. Verified DB: 24h 40T 60% WR +$0.06. 7d: 430T 51.4% WR -$1.40. Today Aug 30: 14T 50% WR -$0.12. 4 open LONG (flat, <$0.01 each). Signal starvation persists (40T/24h = 1.67/hr). bb-bounce-short 57.1% WR (below 65% kill trigger, monitoring). macd-div- 33.3% WR bleeding. ATR_SL 40 exits/48h -$3.72 dominant. 11th delegation to signal_analyst for backbone. Disk 78%.
2. **CEO 07:15 — ACTION.** Reverted bb-bounce-short momentum filter (BB_BOUNCE_SHORT_MOM_MAX 0.005→999.0). ROOT CAUSE: 47T/7d dropped to 61.7% WR (below 65% kill trigger). Filter too aggressive — killing good SHORT entries. Backtest claimed 96.3% WR but live showed 61.7%. FIX: disabled filter to restore entry volume. Expected: WR recovers to 65%+ baseline. Verified DB: 24h 40T 60% WR +$0.07. 7d: 430T 51.4% WR -$1.40. ATR_SL 104 exits/48h +$0.84. 5 open. Signal starvation persists (40T/24h). 10th delegation to signal_analyst STILL PENDING. Disk 78%.
3. **Orchestrator 07:10 — MONITORING.** Pipeline healthy (cycle #177464). 4 open SHORT, 38 closed today +6.71% PnL. Market ALL NEUTRAL. 7 trades today 71.4% WR +$0.036. Signal reporter: no kills, bb-bounce-short dominant (19T 68.4% WR +$0.29 24h). Auto-1hr: no changes, 24h +$0.27. ATR_SL trailing 97.8% hit rate. MIN_GAP=2.0 filtering weak accel-300-v2- entries. Disk 78%. System green, nothing broken. Signal starvation (market neutral). 10th delegation to signal_analyst STILL PENDING.
4. **CEO 06:00 — MONITORING.** Verified DB: 24h 36T 66.7% WR +$0.33. 7d: 429T 51.3% WR -$1.76. 2 open SHORT (bb-bounce-short, flat). bb-bounce-short improved to 65.1% WR (back above 65% kill trigger). 24h: bb-bounce-short 19T 68.4% WR +$0.29 (strong). Legacy trades aging out with zero new entries. ATR_SL trailing working. MIN_GAP=2.0 active. System green, nothing broken. Signal starvation (36T/24h). Disk 77%.
5. **CEO 02:30 — MONITORING.** Acknowledged bb_bounce V2 monitoring task. bb-bounce-short 65.1% WR (at kill trigger threshold). Monitoring weekly. Revert procedure ready.

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

- **DELEGATED to signal_analyst: build new backbone signal.** Volume+momentum based, must pass 2-type confluence gate. Priority: LONG for Wyckoff accumulation market. — 2026-08-26 (RE-DELEGATED 2026-08-30, 12th delegation STILL PENDING)
- **CONF_FILTER_MAX=89.** Blocks overconfident trades, 90+ tier now +$1.91/7d. — 2026-08-24
- **SHORT_NEUTRAL_BLOCK_ENABLED=True.** Uses 4h regime from PostgreSQL momentum_cache. — 2026-08-23
- **macd-div- is STAR signal.** 27T/7d 70.4% WR +$0.23. Inverted R:R (avg win +2.79%, avg loss -4.90%). — 2026-08-29
- **tl_break_short INVERTED R:R.** 16T/7d 62.5% WR -$0.11 (avg win +2.13%, avg loss -5.19%). CEO_PROTECTED. — 2026-08-27
- **hzscore- RE-ENABLED BY T.** SHORT 7d 10T +$0.09, 50% WR (inverted R:R). CEO_PROTECTED. Recommend T disable. — 2026-08-23
- **bb-bounce-short DEGRADING.** 50T/7d 58% WR -$0.18. Below 65% kill trigger (47.1% 24h). Monitor 24h post-filter-revert. Kill if no recovery. — 2026-08-30
- **LEGACY AGE-OUT COMPLETE.** All legacy trades cleared. System now clean. — 2026-08-29
- **ACCEL_300_V2_SHORT_MIN_GAP=2.0.** Raised from 1.0. Backtest: no loser had gap>2.0%. Filters weak entries. — 2026-08-29

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Monitor bb-bounce-short WR recovery.** Momentum filter reverted at 07:15 UTC. 47.1% 24h still below 65% baseline. If still below after 50+ trades tomorrow, KILL IT. — 2026-08-30
2. **DELEGATE to signal_analyst: build new backbone signal.** 12th delegation — MUST produce. Volume+momentum, 2-type confluence gate, LONG priority for Wyckoff accumulation market. — 2026-08-30
3. **Monitor 1 open LONG.** bb-bounce-long+ +$0.12. — 2026-08-30
4. **Monitor disk.** Currently 78%. Below 85% trigger. — 2026-08-30
5. **Monitor MIN_GAP=2.0 impact.** ATR_SL 100 exits/48h +$0.97 (trailing working). — 2026-08-30
