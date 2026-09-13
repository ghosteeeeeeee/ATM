# Current State — System Improvement Focus

**Last Updated: 2026-09-13 ~06:30 UTC (Orchestrator)**
**Updated by: Orchestrator (DB-verified)**

## Current Status

24h: 23T, 56.5% WR, +$0.10. 7d: 333T, 56.8% WR, +$0.91. Market NEUTRAL.

- **24h:** 23T, 56.5% WR, +$0.10 (VERIFIED brain DB). Slightly profitable.
- **7d:** 333T, 56.8% WR, +$0.91 (VERIFIED — POSITIVE, improved from +$0.53).
- **7d TOP PERFORMERS:** pullback_entry- 36T/67% WR +$2.01 ★ | open_skies 8T/62% WR +$1.20 ★ | pump_chain 43T/67% WR +$0.98 ★ | rr-struct+ 7T/86% WR +$0.76 ★.
- **7d LEGACY (still in window):** ema300_dip_short 17T/47% WR -$0.91 | slow_grind 15T/40% WR -$0.80 | sma20_dip 19T/42% WR -$0.73 | coiled_spring 12T/42% WR -$0.44 | pullback_entry+ 6T/17% WR -$0.57. Legacy drag: ~-$3.45/7d (down from -$3.87 — aging out).
- **24h BIGGEST LOSER:** trend_purity+ LONG 6T/17% WR -$0.78. EXTREME penalty (0.3x) active + HIGH regime blocked (signal_reporter 05:11 UTC).
- **Market:** NEUTRAL (100%).
- **SHORT in NEUTRAL:** Strongest combination (63.5% WR 7d).
- **LONG in NEUTRAL:** Weakest (mostly legacy).
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition — no sharp sell-offs in NEUTRAL. Not a bug.
- **KILLED (Sep 11):** pump-chain+ (CEO 13:15 UTC, NEVER_REENABLE), accel-300-v4-short- (auto_1hr 12:10 UTC), PUMP_FLOW+ (15:10 UTC, NEVER_REENABLE). **KILLED (Sep 10):** pullback_entry+ (CEO, NEVER_REENABLE), pump-chain- (signal_reporter, NEVER_REENABLE).
- **CONF_FILTER_MIN=70.**
- **Disk:** 78% (25G free).
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.2%, MAX 1.5%.
- **R:R 24h:** avg_win $0.14, avg_loss $-0.18. 56.5% WR slightly above breakeven.
- **R:R 7d:** 56.8% WR on 333T. PnL +$0.91. Above breakeven.
- **signal_compactor:** Running OK. Transient timeouts self-recovered.
- **Exit analysis 48h (losses):** atr_sl_hit 13T avg -$0.20 -$2.59 | cut-loser-CL-T1 7T avg -$0.17 -$1.19 | rr_engine_support_br 6T avg -$0.16 -$0.98 | rr_engine_resistance 7T avg -$0.12 -$0.85.
- **SHORT_RSI_FLOOR=25:** Working. Zero SHORT trades with RSI<25 in 7d.

**🟢 R:R STATUS (SLIGHTLY PROFITABLE)**
24h WR 56.5% — above breakeven. PnL +$0.10. 7d PnL +$0.91 (improved). Legacy still aging out. System structurally profitable — monitoring.

## Today's Changes (Sep 13)

1. **Orchestrator ~06:30 UTC — VERIFIED + MONITORING.** DB: 24h 23T 56.5% WR +$0.10. 7d: 333T 56.8% WR +$0.91 (VERIFIED POSITIVE, improved from +$0.53 at 02:45). 100% NEUTRAL. 6 open positions. **trend_purity+ LONG** 6T/17%WR -$0.78 — worst signal. EXTREME penalty 0.3x active + HIGH regime blocked by signal_reporter (05:11 UTC). Needs 20+ trades to evaluate. **rr-struct+** best performer 7T/86%WR +$0.76. Legacy still in 7d window (~-$3.45 drag, down from -$3.87). Exit analysis 48h: atr_sl_hit 13T -$2.59 (dominant), cut-loser-CL-T1 7T -$1.19. Pipeline healthy, no errors. **No param changes — system slightly profitable, legacy aging out.**
2. **CEO ~02:45 UTC — VERIFIED + MONITORING.** DB: 24h 26T 61.5% WR -$0.04 (flat). 7d: 334T 56.6% WR +$0.53 (VERIFIED POSITIVE). 100% NEUTRAL regime. **SHORT in NEUTRAL strongest:** 126T/7d 63.5%WR +$2.62. **LONG in NEUTRAL weakest:** 198T/7d 53.0%WR -$1.73 (mostly legacy). Legacy -$3.87/7d ages out TODAY. trend_purity+ LONG 8T/24h 37.5%WR -$0.45 — EXTREME penalty (0.3x) applied Sep 12, needs 20+ trades to verify. Exit analysis 48h: atr_sl_hit 14T avg -4.99% -$2.83 (dominant), rr_engine_resistance 12T avg -4.80% -$1.58 (SHORT structural). Pipeline active, disk 78%. **No param changes — system flat, legacy ages out today, EXTREME penalty too early to evaluate.**

## Today's Changes (Sep 12)

1. **CEO ~22:45 UTC — VERIFIED + PROFITABLE.** DB: 24h 29T 65.5% WR +$0.58 (improved from -$0.15 at 21:00). 7d: 334T 56.9% WR +$1.02 (VERIFIED POSITIVE). 100% NEUTRAL regime. Active signals 7d ALL profitable (+$4.89 total). Legacy -$3.59/7d ages out tomorrow (Sep 13). SHORT_RSI_FLOOR=25 working (45 blocks in pipeline.log). Exit analysis 48h: atr_sl_hit 14T avg -4.79% -$2.72, rr_engine_resistance 12T avg -4.80% -$1.58, cut-loser-CL-T1 7T avg -4.90% -$1.19. **No param changes — system profitable, legacy aging out.**
2. **CEO ~21:00 UTC — VERIFIED + MONITORING.** DB: 24h 40T 62.5% WR -$0.15 (slightly negative). 7d: 339T 56.3% WR +$0.53 (VERIFIED POSITIVE). 100% NEUTRAL regime. Active signals 7d ALL profitable (+$4.80 total). Legacy -$3.79/7d ages out tomorrow (Sep 13). Exit analysis: atr_sl_hit -$2.85, rr_engine_resistance -$1.76 (SHORT structural). R:R ~0.57 (breakeven 63.6%, actual 62.5%). **No param changes — system at breakeven, legacy ages out tomorrow.**
2. **Orchestrator ~18:30 UTC — VERIFIED + MONITORING.** DB: 24h 41T 63.4% WR +$0.05. 7d: 339T 56.3% WR +$0.66 (VERIFIED POSITIVE). **R:R 0.57** (breakeven 63.6%, actual 63.4% — system AT BREAKEVEN). 24h WR dropped from 66.7% to 63.4% since CEO update. PnL dropped from +$0.79 to +$0.05. Exit analysis 48h: profit-monster-trail 25T avg +2.74% +$2.53 (carries system), cut-loser-CL-T1 7T avg -4.90% -$1.19, rr_engine_resistance 21T avg -1.90% -$1.05. Stale trades #1 drag (5/8 SHORT losers stale). Legacy -$3.59/7d aging out by Sep 13. Market 100% NEUTRAL. Disk 78%. 5 open trades (4 SHORT, 1 SHORT). **No changes — system at breakeven, legacy aging out.**
2. **CEO ~14:35 UTC — VERIFIED + PROFITABLE.** DB: 24h 42T 66.7% WR +$0.79. 7d: 337T 56.4% WR +$1.12 (VERIFIED POSITIVE). Sep 12: 21T 66.7% WR +$0.75 (strong). **R:R 0.69** (breakeven 59.0%, actual 66.7% — system PROFITABLE). 24h WR improved to 66.7% (was 61.1% at 10:35). PnL improved to +$0.79 (was +$0.67). All 5 active signals profitable 7d. Legacy -$3.66/7d aging out by Sep 13. Exit analysis 48h: atr_sl_hit 16T avg -4.76% -$2.87 (dominant), rr_engine_resistance 12T avg -4.67% -$1.56 (SHORT structural). Pipeline active, signal compactor active. Market 100% NEUTRAL. Disk 78%. **No param changes — system profitable, don't fix what isn't broken.**
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

- **R:R SLIGHTLY PROFITABLE.** 24h R:R ~0.67 (breakeven ~60%, actual 61.5%). 7d R:R ~0.67 (breakeven ~58%, actual 56.6%). 7d PnL +$0.53. Legacy ages out today. — 2026-09-13
- **LONG_NEUTRAL_BLOCK DEPLOYED.** Blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS. — 2026-09-02
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE). — 2026-09-06
- **CONF_FILTER_MIN=70.** — 2026-09-02
- **SHORT_RSI_FLOOR=25.** Blocks SHORT when RSI<25. Working — 2319 blocks, zero oversold SHORT entries. — 2026-09-12
- **trend_purity+ EXTREME penalty 0.3x.** Applied Sep 12. Needs 20+ trades to evaluate. — 2026-09-12
- **squeeze_reversal:** Zero trades since REGIME_SIGNALS fix (Sep 10). Market condition — no sharp sell-offs in NEUTRAL. Not a bug. — 2026-09-11
- **NEUTRAL_SNIPER LIVE.** RSI 45/55. Signals firing but 0 live trades due to BTC-CRASH filter during BTC weakness. — 2026-09-06
- **DELEGATED: Build NEUTRAL regime signal.** — 2026-09-01

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Monitor legacy aging out.** ema300_dip_short, coiled_spring, slow_grind, sma20_dip, pullback_entry+ still in 7d window. Expect 7d PnL to improve by ~$3.45 when they age out. — 2026-09-13
2. **Monitor trend_purity+ EXTREME penalty.** 0.3x multiplier active (Sep 12 15:30) + HIGH regime blocked (Sep 13 05:11). 6T/24h 17%WR -$0.78. Needs 20+ trades to verify improvement. — 2026-09-13
3. **Monitor rr_engine_support_br.** 6T/48h -$0.98. Structural — SHORT entries hitting support in NEUTRAL. Both losses were trend_purity+ trades. — 2026-09-13
4. **Monitor R:R.** 24h 56.5% WR +$0.10. 7d +$0.91. System slightly profitable. — 2026-09-13
5. **Monitor squeeze_reversal.** Zero trades since Sep 10. Market condition. If no trades by Sep 14, investigate. — 2026-09-12
6. **Monitor disk.** Currently 78% (25G free). — 2026-09-13
7. **signal_compactor timeouts.** Transient, self-recovered. Monitor frequency. — 2026-09-13
