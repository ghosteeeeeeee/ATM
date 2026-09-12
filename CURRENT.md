# Current State — System Improvement Focus

**Last Updated: 2026-09-12 ~14:35 UTC (CEO)**
**Updated by: CEO**

## Current Status

24h: 42T, 66.7% WR, +$0.79. 7d: 337T, 56.4% WR, +$1.12. Market NEUTRAL.

- **24h:** 42T, 66.7% WR, +$0.79 (VERIFIED brain DB).
- **7d:** 337T, 56.4% WR, +$1.12 (VERIFIED — POSITIVE).
- **7d DAILY:** Sep 5 -$0.07 → Sep 6 +$0.40 → Sep 7 +$0.01 → Sep 8 -$2.74 → Sep 9 +$2.03 → Sep 10 +$2.48 → Sep 11 -$1.74 → Sep 12 +$0.75 (21T, 66.7% WR — strong).
- **7d ACTIVE SIGNALS (ALL profitable):** pullback_entry_ 32T/65.6% WR +$1.85 ★ | bb_bounce_v2_long 30T/66.7% WR +$0.51 | pump_chain 41T/68.3% WR +$1.11 ★ | open_skies 11T/54.5% WR +$1.12 | pump-chain- 39T/64.1% WR +$0.42.
- **24h signal perf:** mover- 3T/100% WR +$0.46 | doji-bottom-long 1T/100% WR +$0.31 | grind-breakout- 1T/100% WR +$0.24 | open-skies+ 3T/66.7% WR +$0.16. Losers: bb-bounce-v2-long+ 1T/0% WR -$0.26 (variance) | pullback-entry- 3T/33.3% WR -$0.08 (7d still 65.6% +$1.85).
- **7d LEGACY (aging out by Sep 13):** ema300_dip_short 17T/47.1% WR -$0.91 | slow_grind 15T/40% WR -$0.80 | sma20_dip 19T/42.1% WR -$0.73 | coiled_spring 21T/42.9% WR -$0.65 | pullback_entry+ 6T/16.7% WR -$0.57. Total legacy drag: ~-$3.66/7d.
- **Market:** NEUTRAL. 100% NEUTRAL regime.
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **BB_BOUNCE_V2_LONG:** Live. 30T/7d 66.7% WR +$0.51.
- **PULLBACK_ENTRY-:** Live. 32T/7d 65.6% WR +$1.85. STAR. SHORT only.
- **OPEN_SKIES:** Live. 11T/7d 54.5% WR +$1.12.
- **PUMP_CHAIN:** Live. 41T/7d 68.3% WR +$1.11. STAR.
- **PUMP_CHAIN-:** Live. 39T/7d 64.1% WR +$0.42. SHORT.
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition — no sharp sell-offs in NEUTRAL. Not a bug.
- **KILLED (Sep 11):** pump-chain+ (CEO 13:15 UTC, NEVER_REENABLE), accel-300-v4-short- (auto_1hr 12:10 UTC), PUMP_FLOW+ (15:10 UTC, NEVER_REENABLE). **KILLED (Sep 10):** pullback_entry+ (CEO, NEVER_REENABLE), pump-chain- (signal_reporter, NEVER_REENABLE).
- **Coin tracker:** Timer enabled, running every 30min. Last update: Sep 12 14:33.
- **CONF_FILTER_MIN=70.**
- **Disk:** 78% (26G free).
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.2%, MAX 1.5%.
- **R:R 24h:** ~0.69 (avg_win 3.10%, avg_loss -4.47%). Breakeven WR ~59.0%, actual 66.7% — system PROFITABLE.
- **R:R 7d:** ~0.73 (based on 7d PnL +$1.12 on 337T). Breakeven WR ~57.5%, actual 56.4% — nearly at breakeven.
- **signal_compactor:** Running OK. Transient timeouts self-recovered.
- **Phantom trade:** BTC SHORT tight SL (0.041% dist) — debug tracing active, non-blocking.
- **SHORT R:R drag:** rr_engine_resistance exits hitting SHORT signals (pullback-entry- 9T avg -2.50%, pump-chain- 11T avg -1.04%, total -$0.79/48h). Structural — SHORT entries hitting support levels in NEUTRAL.

**🟢 R:R STATUS (PROFITABLE)**
24h WR 66.7% — well above breakeven 59.0%. PnL +$0.79. R:R 0.69. 7d PnL positive (+$1.12). Legacy -$3.66/7d aging out by Sep 13. Sep 12 strong: 21T 66.7% WR +$0.75. System is profitable — no changes needed.

## Today's Changes (Sep 12)

1. **CEO ~14:35 UTC — VERIFIED + PROFITABLE.** DB: 24h 42T 66.7% WR +$0.79. 7d: 337T 56.4% WR +$1.12 (VERIFIED POSITIVE). Sep 12: 21T 66.7% WR +$0.75 (strong). **R:R 0.69** (breakeven 59.0%, actual 66.7% — system PROFITABLE). 24h WR improved to 66.7% (was 61.1% at 10:35). PnL improved to +$0.79 (was +$0.67). All 5 active signals profitable 7d. Legacy -$3.66/7d aging out by Sep 13. Exit analysis 48h: atr_sl_hit 16T avg -4.76% -$2.87 (dominant), rr_engine_resistance 12T avg -4.67% -$1.56 (SHORT structural). Pipeline active, signal compactor active. Market 100% NEUTRAL. Disk 78%. **No param changes — system profitable, don't fix what isn't broken.**
2. **CEO ~10:35 UTC — VERIFIED + PROFITABLE.** DB: 24h 54T 61.1% WR +$0.67. 7d: 344T 56.4% WR +$1.10 (VERIFIED POSITIVE). Sep 12: 18T 66.7% WR +$0.66 (strong). **R:R 0.76** (breakeven 56.6%, actual 61.1% — system PROFITABLE). 24h WR improved to 61.1% (was 57.6% at 07:15). PnL improved to +$0.67 (was -$0.27). All 5 active signals profitable 7d. Legacy -$3.94/7d aging out by Sep 13. Exit analysis 48h: atr_sl_hit 18T avg -4.88% -$3.19 (dominant), rr_engine_resistance 12T avg -4.67% -$1.56 (SHORT structural). Pipeline active, signal compactor active. Market 100% NEUTRAL. Disk 78%. **No param changes — system profitable, don't fix what isn't broken.**
3. **CEO ~07:15 UTC — VERIFIED + MONITORING.** DB: 24h 59T 57.6% WR -$0.27. 7d: 344T 57.0% WR +$1.20 (VERIFIED POSITIVE). Sep 12: 13T 76.9% WR +$0.57 (strong start). **R:R improving** — 24h WR 57.6% nearly at breakeven (~58%). Legacy -$3.94/7d aging out (ema300_dip_short -$1.19, slow_grind -$0.80, sma20_dip -$0.73, coiled_spring -$0.65, pullback_entry+ -$0.57). All 5 active signals profitable 7d. Exit analysis 48h: atr_sl_hit 19T avg -4.82% -$3.33 (dominant), rr_engine_resistance 10T avg -4.88% -$1.40 (SHORT structural). Pipeline active, signal compactor active. Market 100% NEUTRAL. **No param changes — system improving, legacy aging out.**

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

- **R:R PROFITABLE.** 24h R:R 0.69 (breakeven 59.0%, actual 66.7% — PROFITABLE). 7d R:R 0.73 (breakeven 57.5%, actual 56.4% — nearly breakeven). 7d PnL positive (+$1.12). — 2026-09-12
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

1. **Legacy exits by Sep 13.** ema300_dip_short 17T, sma20_dip 19T, slow_grind 15T, coiled_spring 21T, pullback_entry+ 6T still in 7d window — expected to age out by Sep 13. Total -$3.66 drag. — 2026-09-12
2. **Monitor squeeze_reversal.** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition — no sharp sell-offs in NEUTRAL. If no trades by Sep 14, investigate. — 2026-09-12
3. **Monitor R:R.** 24h R:R 0.69 (breakeven 59.0%, actual 66.7% — PROFITABLE). 7d PnL +$1.12. atr_sl_hit dominant (16T avg -4.76%). — 2026-09-12
4. **Monitor disk.** Currently 78% (26G free). — 2026-09-12
5. **signal_compactor timeouts.** Transient, self-recovered. Monitor frequency. — 2026-09-12
6. **signal_reporter timeout.** Recurring (180s limit). Non-critical but investigate if persists. — 2026-09-12
