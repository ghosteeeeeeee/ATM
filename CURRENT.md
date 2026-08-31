# Current State — System Improvement Focus

**Last Updated: 2026-08-31 ~07:00 UTC (CEO run)**
**Updated by: CEO**

## Current Status

System FLAT, 3 open positions. Pipeline healthy. volume_breakout DEPLOYED (0 signals — market flat). range_reversion SHADOW MODE EXTENDED (24h+ with 0 signals — market too flat for mean-reversion triggers, shadow extended 24h).

- **24h:** 36T, 52.8% WR, -$0.12 (near breakeven)
- **48h:** 75T, 58.7% WR, +$0.06 (POSITIVE)
- **7d:** 407T, 51.1% WR, -$2.45
- **Today Aug 31:** 8T, 37.5% WR, -$0.07
- **Market:** ALL NEUTRAL. Dead.
- **Disk:** 79%
- **Open positions:** 3 (cascade-reverse-v2 LONG +0.11%, macd-div- SHORT -0.35%, ichimoku- SHORT flat)
- **Legacy bleed:** hl_copy LONG -$1.03, slow-grind- -$0.64, ct-hot+ -$0.60 (all aging out, zero new 24h)
- **ATR_SL:** 26T/48h losers avg -4.12% — entry quality issue persists
- **accel-300-v2-:** 72T/7d 52.8% WR +$1.46 (backbone, strong). Barely active.
- **macd-div-:** 31T/7d 61.3% WR -$0.14 (STAR, CEO_PROTECTED). **48h: 7T 14.3% WR -$0.50 (DEGRADED — small sample, monitoring).**
- **bb-bounce-short:** 27T/48h 55.6% WR -$0.16 (below 65% target).
- **volume_breakout:** DEPLOYED. 0 signals total (flat market).
- **range_reversion:** SHADOW MODE EXTENDED 24h. 24h+ with 0 signals. Market too flat.

**System has 2 backbone signals + STAR + new volume_breakout + range_reversion (shadow).** Signal starvation persists (~37T/24h = 1.5/hr). Market dead. System near breakeven.

**CEO 02:45 — MONITORING.** Verified DB: 24h 37T 54.1% WR -$0.29. 7d: 416T 52.6% WR -$1.99. Today Aug 31: 2T 50% WR -$0.07. Open: 0. 48h: atr_sl_hit 74T +$0.71 (TRAILING PROFITABLE). macd-div- 5T/48h 20% WR -$0.40 (degraded, small sample). volume_breakout: 0 signals. Coin tracker active. Disk 79%. No changes needed.

## Today's Changes (Aug 31)

0. **CEO 07:00 — MONITORING.** Verified DB: 24h 36T 52.8% WR -$0.12. 48h: 75T 58.7% WR +$0.06. 7d: 407T 51.1% WR -$2.45. Today Aug 31: 8T 37.5% WR -$0.07. Open: 3 (cascade-reverse-v2 LONG +0.11%, macd-div- SHORT -0.35%, ichimoku- SHORT flat). Legacy bleed aging out (hl_copy LONG -$1.03, slow-grind- -$0.64, ct-hot+ -$0.60 — zero new 24h). macd-div- 7T/48h 14.3% WR -$0.50 (DEGRADED — small sample, monitoring). bb-bounce-short 27T/48h 55.6% WR -$0.16. atr_sl_hit 26T/48h -$2.65 (dominant). volume_breakout 0 signals. range_reversion 24h+ shadow 0 signals — EXTENDED SHADOW 24h. Market ALL NEUTRAL. Disk 79%. No parameter changes.
1. **CEO 02:45 — MONITORING.** Verified DB: 24h 37T 54.1% WR -$0.29. 7d: 416T 52.6% WR -$1.99. Today Aug 31: 2T 50% WR -$0.07. Open: 0. 48h: atr_sl_hit 74T +$0.71 (TRAILING PROFITABLE). macd-div- 5T/48h 20% WR -$0.40 (degraded, small sample). volume_breakout: 0 signals. Coin tracker active. Disk 79%. No changes.

## Today's Changes (Aug 30)

0. **CEO 23:00 — CLEANUP.** Disabled stale timers hermes-hl-copy and hermes-hl-sync-guardian (legacy hl_copy related, no longer relevant). Verified DB: 24h 36T 55.6% WR -$0.38. 7d: 421T 52.5% WR -$1.86. ATR_SL 76T/48h -$0.66 (MIN_GAP=2.0 working). macd-div- 5T/48h 20% WR (degraded, small sample). volume_breakout 0 signals (flat market). Disk 78%.
1. **CEO 22:15 — DELEGATE.** 14th delegation to signal_analyst: built range_reversion — mean-reversion signal for flat/ranging markets. BB squeeze + RSI extremes + bounce confirmation. Registered, shadow mode (ENABLED=False). Range family — pairs with ANY for 2-type confluence. Files: scripts/signals/range_reversion.py, hermes_constants.py (12 new constants), signals/__init__.py, market_phase_gate.py. Will test 48h shadow before enabling. Git: f8a0a72b.
2. **CEO 18:30 — ACTION.** Built and deployed volume_breakout signal (NEW backbone). Verified DB: 24h 35T 60% WR -$0.19. 7d: 425T 52% WR -$1.84. Today Aug 30: 28T 53.6% WR -$0.37. ROOT CAUSE: signal starvation (35T/24h = 1.46/hr) from only 2 backbone signals in flat market. FIX: built volume_breakout — Volume family signal (2x volume spike + price momentum + RSI confirmation). Pairs with ANY other family for 2-type confluence gate. Currently 0 signals (market flat, no volume spikes). Expected: fires when market wakes up, adds Volume family to confluence combos. Files: scripts/signals/volume_breakout.py, hermes_constants.py (VOLUME_BREAKOUT_ENABLED=True), market_phase_gate.py (FAMILY_MAP updated), signals/__init__.py (registry). 2 open. Disk 78%.
3. **CEO 15:30 — ACTION.** Killed BB_BOUNCE_SHORT_ENABLED. Verified DB: 24h 35T 60% WR -$0.16. 7d: 430T 51.6% WR -$2.09. Today Aug 30: 21T 57.1% WR -$0.10. ROOT CAUSE: bb-bounce-short 24h 17T 47.1% WR -$0.37 (below 65% kill trigger). Filter revert at 07:15 didn't recover. 48h 39T 53.8% WR -$0.23. FIX: disabled BB_BOUNCE_SHORT. System now on 2 backbone: accel-300-v2- (52.8% WR +$1.46) + macd-div- (70.4% WR +$0.23 STAR). 3 open. Signal starvation 35T/24h. 13th delegation to signal_analyst. Disk 78%.
4. **CEO 14:00 — MONITORING.** No changes. Verified DB: 24h 36T 61.1% WR -$0.12. 7d: 430T 51.6% WR -$2.09. Today Aug 30: 21T 57.1% WR -$0.10. 1 open LONG (bb-bounce-long+ +$0.12). bb-bounce-short 50T/7d 58% WR -$0.18 (below 65% kill trigger, monitoring). accel-300-v2- 72T/7d 52.8% WR +$1.46 (backbone). macd-div- 27T/7d 70.4% WR +$0.23 (STAR). ATR_SL 100 exits/48h +$0.97 (trailing working). Signal starvation 36T/24h. 12th delegation to signal_analyst. Disk 78%.
5. **CEO 10:15 — MONITORING.** No changes. Verified DB: 24h 40T 60% WR +$0.06. 7d: 430T 51.4% WR -$1.40. Today Aug 30: 14T 50% WR -$0.12. 4 open LONG (flat, <$0.01 each). Signal starvation persists (40T/24h = 1.67/hr). bb-bounce-short 57.1% WR (below 65% kill trigger, monitoring). macd-div- 33.3% WR bleeding. ATR_SL 40 exits/48h -$3.72 dominant. 11th delegation to signal_analyst for backbone. Disk 78%.
6. **CEO 07:15 — ACTION.** Reverted bb-bounce-short momentum filter (BB_BOUNCE_SHORT_MOM_MAX 0.005→999.0). ROOT CAUSE: 47T/7d dropped to 61.7% WR (below 65% kill trigger). Filter too aggressive — killing good SHORT entries. Backtest claimed 96.3% WR but live showed 61.7%. FIX: disabled filter to restore entry volume. Expected: WR recovers to 65%+ baseline. Verified DB: 24h 40T 60% WR +$0.07. 7d: 430T 51.4% WR -$1.40. ATR_SL 104 exits/48h +$0.84. 5 open. Signal starvation persists (40T/24h). 10th delegation to signal_analyst STILL PENDING. Disk 78%.
7. **Orchestrator 07:10 — MONITORING.** Pipeline healthy (cycle #177464). 4 open SHORT, 38 closed today +6.71% PnL. Market ALL NEUTRAL. 7 trades today 71.4% WR +$0.036. Signal reporter: no kills, bb-bounce-short dominant (19T 68.4% WR +$0.29 24h). Auto-1hr: no changes, 24h +$0.27. ATR_SL trailing 97.8% hit rate. MIN_GAP=2.0 filtering weak accel-300-v2- entries. Disk 78%. System green, nothing broken. Signal starvation (market neutral). 10th delegation to signal_analyst STILL PENDING.
8. **CEO 06:00 — MONITORING.** Verified DB: 24h 36T 66.7% WR +$0.33. 7d: 429T 51.3% WR -$1.76. 2 open SHORT (bb-bounce-short, flat). bb-bounce-short improved to 65.1% WR (back above 65% kill trigger). 24h: bb-bounce-short 19T 68.4% WR +$0.29 (strong). Legacy trades aging out with zero new entries. ATR_SL trailing working. MIN_GAP=2.0 active. System green, nothing broken. Signal starvation (36T/24h). Disk 77%.
9. **CEO 02:30 — MONITORING.** Acknowledged bb_bounce V2 monitoring task. bb-bounce-short 65.1% WR (at kill trigger threshold). Monitoring weekly. Revert procedure ready.

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

- **volume_breakout DEPLOYED.** Volume family signal — pairs with ANY other family for 2-type confluence. 2x volume spike + price momentum + RSI confirmation. Currently 0 signals (flat market). Monitor 48h for first signals. — 2026-08-30
- **range_reversion SHADOW MODE EXTENDED.** Mean-reversion signal for flat/ranging markets. BB squeeze + RSI extremes + bounce confirmation. Range family. Shadow 24h+ with 0 signals — market too flat. Shadow extended 24h, re-evaluate tomorrow. — 2026-08-31
- **CONF_FILTER_MAX=89.** Blocks overconfident trades, 90+ tier now +$1.91/7d. — 2026-08-24
- **SHORT_NEUTRAL_BLOCK_ENABLED=True.** Uses 4h regime from PostgreSQL momentum_cache. — 2026-08-23
- **macd-div- is STAR signal.** 28T/7d 67.9% WR +$0.07. Inverted R:R (avg win +2.66%, avg loss -4.77%). CEO_PROTECTED. — 2026-08-29
- **tl_break_short INVERTED R:R.** 16T/7d 62.5% WR -$0.11 (avg win +2.13%, avg loss -5.19%). CEO_PROTECTED. — 2026-08-27
- **hzscore- RE-ENABLED BY T.** SHORT 3T/7d +$0.30 66.7% WR. CEO_PROTECTED. Recommend T disable. — 2026-08-23
- **bb-bounce-short KILLED.** Was 51T/7d 58.8% WR -$0.16. Killed 2026-08-30 — 47.1% WR 24h. — 2026-08-30
- **LEGACY AGE-OUT COMPLETE.** All legacy trades cleared. System now clean. — 2026-08-29
- **ACCEL_300_V2_SHORT_MIN_GAP=2.0.** Raised from 1.0. Backtest: no loser had gap>2.0%. Filters weak entries. — 2026-08-29

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **CEO: Re-evaluate range_reversion shadow.** Extended 24h. If still 0 signals tomorrow, either tune thresholds lower or disable. — 2026-08-32
2. **Monitor macd-div- WR recovery.** 7T/48h 14.3% WR -$0.50 (degraded). 7d baseline 61.3%. If stays <40% over next 10+ trades, flag for review. — 2026-08-31
3. **Monitor volume_breakout.** 0 signals (flat market). Will fire when market wakes up. — 2026-08-30
4. **Monitor disk.** Currently 79%. Below 85% trigger. — 2026-08-31
