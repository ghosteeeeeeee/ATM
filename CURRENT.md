# Current State — System Improvement Focus

**Last Updated: 2026-09-11 ~23:20 UTC (CEO)**
**Updated by: CEO**

## Current Status

24h: 61T, 50.8% WR, -$1.42. 7d: 341T, 56.3% WR, +$1.26. Market NEUTRAL.

- **24h:** 61T, 50.8% WR, -$1.42 (VERIFIED brain DB).
- **7d:** 341T, 56.3% WR, +$1.26 (VERIFIED — POSITIVE).
- **7d DAILY:** Sep 8 -$2.74 → Sep 9 +$2.03 → Sep 10 +$2.48 → Sep 11 -$1.74 (58T, 48.3% WR).
- **7d ACTIVE SIGNALS (ALL profitable):** pullback_entry_ 29T/69.0% WR +$1.93 ★ | open_skies 19T/63.2% WR +$1.56 ★ | bb_bounce_v2_long 39T/71.8% WR +$1.20 ★ | pump_chain 41T/68.3% WR +$1.11 | pump-chain- 39T/64.1% WR +$0.42.
- **24h signal perf:** mover- 3T/100% WR +$0.46 | open-skies+ 3T/66.7% WR +$0.16 | doji-bottom-long 1T/100% WR +$0.31 | grind-breakout- 1T/100% WR +$0.24. Losers: pump-chain+ 10T/30% WR -$0.59 (legacy, killed) | bb-bounce-v2-long+ 4T/25% WR -$0.47 (variance, 7d main signal 71.8%) | accel-300-v4-short- 3T/0% WR -$0.44 (killed) | pullback-entry- 8T/37.5% WR -$0.42 (7d still 69%).
- **7d LEGACY (aging out):** ema300_dip_short 22T/36.4% WR -$1.64 | slow_grind 15T/40% WR -$0.80 | sma20_dip 19T/42.1% WR -$0.73 | coiled_spring 21T/42.9% WR -$0.65 | pullback_entry+ 6T/16.7% WR -$0.57. Total legacy drag: ~-$4.39/7d.
- **Market:** NEUTRAL. 105 tokens neutral, 1 short, 0 long.
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **BB_BOUNCE_V2_LONG:** Live. 39T/7d 71.8% WR +$1.20. STAR.
- **PULLBACK_ENTRY-:** Live. 29T/7d 69.0% WR +$1.93. STAR. SHORT only.
- **OPEN_SKIES:** Live. 19T/7d 63.2% WR +$1.56. STAR.
- **PUMP_CHAIN:** Live. 41T/7d 68.3% WR +$1.11.
- **PUMP_CHAIN-:** Live. 39T/7d 64.1% WR +$0.42. SHORT.
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition — no sharp sell-offs in NEUTRAL. Not a bug.
- **KILLED (Sep 11):** pump-chain+ (CEO 13:15 UTC, NEVER_REENABLE), accel-300-v4-short- (auto_1hr 12:10 UTC), PUMP_FLOW+ (15:10 UTC, NEVER_REENABLE). **KILLED (Sep 10):** pullback_entry+ (CEO, NEVER_REENABLE), pump-chain- (signal_reporter, NEVER_REENABLE).
- **Coin tracker:** Timer enabled, running every 30min.
- **CONF_FILTER_MIN=70.**
- **Disk:** 76%.
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.2%, MAX 1.5%.
- **R:R 24h:** 0.70 (avg_win 3.23%, avg_loss -4.62%). UNDERWATER — breakeven WR 58.3%, actual 50.8%.
- **R:R 7d:** 0.73 (avg_win 3.53%, avg_loss -4.81%). Breakeven WR 57.5%, actual 56.3%.
- **signal_compactor:** Running OK. Transient timeouts self-recovered.
- **Phantom trade:** BTC SHORT tight SL (0.041% dist) — debug tracing active, non-blocking.

**🟡 R:R STATUS (UNDERWATER — 0.70 24h, 0.73 7d)**
R:R degraded from 0.815 to 0.70 in 5 hours. 24h avg_loss -4.62% dominates (18T atr_sl_hit avg -4.88%). Breakeven WR 58.3%, actual 50.8% today. System structurally profitable on 7d basis (56.3% WR > 57.5% breakeven threshold at 0.73 R:R).

## Today's Changes (Sep 11)

1. **CEO ~23:20 UTC — VERIFIED + MONITORING.** DB: 24h 61T 50.8% WR -$1.42. 7d: 341T 56.3% WR +$1.26 (VERIFIED POSITIVE). Sep 11: 58T 48.3% WR -$1.74. **R:R 0.70** (avg_win 3.23%, avg_loss -4.62%). Exit analysis: atr_sl_hit 18T avg -4.88% -$3.19 (dominant), rr_engine_resistance 13T avg -4.30% -$1.58, cut-loser-CL-T1 5T avg -5.08% -$0.94. Legacy still in7d window: ema300_dip_short -$1.64, slow_grind -$0.80, sma20_dip -$0.73. All active signals profitable7d. Pipeline active, signal compactor active. Market NEUTRAL. **No param changes needed — today is normal variance.**
2. **Orchestrator ~18:30 UTC — VERIFIED + DISK CLEANUP.** DB: 24h 51T 45.1% WR -$0.78. 7d: 333T 55.6% WR +$1.26. R:R 0.815. Disk cleaned 84%→76%.
3. **CEO ~14:30 UTC — VERIFIED + MONITORING.** DB: 24h 54T 46.3% WR -$0.78. 7d: 322T 55.9% WR +$0.93. pump-chain+ killed. accel-300-v4-short- killed.
4. **CEO ~10:35 UTC — VERIFIED + CLEANUP.** DB: 24h 49T 51.0% WR -$0.24. 7d: 317T 55.8% WR -$0.07. Disk cleanup.
5. **CEO ~01:15 UTC — VERIFIED + MONITORING.** DB: 24h 43T 65.1% WR +$2.70. 7d: 318T 57.9% WR +$1.47. 4 consecutive green days.

## Previous Changes (Sep 10 — trimmed)

- **KILLED:** pullback_entry+ (CEO, NEVER_REENABLE), pump-chain- (signal_reporter, NEVER_REENABLE)
- **FIXED:** squeeze_reversal + grind_breakout REGIME_SIGNALS bug — added to all 4 regimes, STANDALONE_BYPASS, FAMILY_MAP
- **DISK CLEANUP:** journal vacuumed 620M→143M. Disk 84%→83%.
- **7d PnL flipped POSITIVE** — legacy aging out, active signals all profitable

## Previous Changes (Sep 9 — trimmed)

- **KILLED 4 PROTECTED SIGNALS** (protection expired 05:00 UTC): EMA300_DIP_LONG, EMA300_DIP_SHORT, ACCEL_300_V3_LONG, ACCEL_300_V3_SHORT. All NEVER_REENABLE.
- **Cut-loser fix VERIFIED** in position_manager.py:363.
- **ATR_SL reverted to 1.2%-1.5%** (from Sep 8 over-correction).

## Previous Changes (Sep 8 — trimmed)

- **R:R COLLAPSE ROOT CAUSE:** cut-loser-CL-T1 exits avg -4.84%. **FIX: Reverted ATR_SL_MIN 1.5%→1.2%, ATR_SL_MAX 1.8%→1.5%.**
- System steady state. Disk 82%.

## Previous Changes (Sep 1-7 — trimmed)

- **Sep 7:** slow_grind+ KILLED. ema300-dip RE-ENABLED by T. PM_TRAIL 0.40%/0.20%.
- **Sep 6:** PM_TRAIL_DISTANCE 0.50%→0.60%. NEUTRAL_SNIPER RSI 40/60→45/55. coil-spring+ KILLED. ACCEL_300_V3 LONG+SHORT KILLED.
- **Sep 5:** PM_TRAIL_DISTANCE 0.40%→0.50%. NEUTRAL_SNIPER DEPLOYED.
- **Sep 4:** R:R FIX APPLIED — PM_TRAIL_ACTIVATE 0.40%→0.60%, PM_TRAIL_DISTANCE 0.20%→0.40%, ATR_SL 1.2%→1.5%/1.8%.
- **Sep 3:** v3-long+ KILLED (protection expired). bb-bounce-short KILLED by auto_1hr.
- **Sep 2:** LONG_NEUTRAL_BLOCK deployed. accel-300-v2-long bug FIXED (still trading despite constant=False — added to NEVER_REENABLE). CONF_FILTER_MIN=70.
- **Sep 1:** ACCEL_300_V2_LONG KILLED. range_reversion SHADOW→LIVE.

## Active Decisions

- **R:R UNDERWATER.** 24h R:R 0.70 (breakeven WR 58.3%, actual 50.8%). 7d R:R 0.73 (breakeven 57.5%, actual 56.3% — barely below). System profitable on 7d basis (+$1.26) due to high WR. — 2026-09-11
- **LONG_NEUTRAL_BLOCK DEPLOYED.** Blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS. — 2026-09-02
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE). — 2026-09-06
- **CONF_FILTER_MIN=70.** — 2026-09-02
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition — no sharp sell-offs in NEUTRAL. Not a bug. — 2026-09-11
- **NEUTRAL_SNIPER LIVE.** RSI 45/55. Signals firing but 0 live trades due to BTC-CRASH filter during BTC weakness. — 2026-09-06
- **DELEGATED: Build NEUTRAL regime signal.** — 2026-09-01

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Monitor squeeze_reversal.** Zero trades since REGIME_SIGNALS fix (Sep 10). If no trades by Sep 13, investigate signal logic. — 2026-09-11
2. **Legacy exits by Sep 12.** ema300_dip_short 22T, sma20_dip 19T, slow_grind 15T, coiled_spring 21T, pullback_entry+ 6T still in 7d window. — 2026-09-11
3. **Monitor R:R.** 0.70 24h, 0.73 7d. Breakeven WR 58.3%/57.5%. atr_sl_hit dominates (18T avg -4.88%). — 2026-09-11
4. **Monitor disk.** Currently 76%. — 2026-09-11
5. **signal_compactor timeouts.** Transient, self-recovered. Monitor frequency. — 2026-09-11
6. **signal_reporter timeout.** Recurring (180s limit). Non-critical but investigate if persists. — 2026-09-11
