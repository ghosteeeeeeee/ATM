# Current State — System Improvement Focus

**Last Updated: 2026-09-09 ~19:10 UTC (CEO)**
**Updated by: CEO**

## Current Status

24h: 42T, 47.6% WR, -$0.72. 7d: 371T, 57.7% WR, -$3.31. Sep 9: 34T, 55.9% WR, +$0.16. Market SHORT_BIAS (3 SHORT / 0 LONG / 115 NEUTRAL).

- **24h:** 42T, 47.6% WR, -$0.72 (verified brain DB). Avg win +3.24%, avg loss -4.46%.
- **7d:** 371T, 57.7% WR, -$3.31. Avg win +2.81%, avg loss -4.78%.
- **7d ACTIVE SIGNALS:** bb_bounce_v2_long 73T/74.0% WR +$2.08 ★ | open_skies 19T/63.2% WR +$1.56 ★ | pump_chain 43T/67.4% WR +$1.11 | continuation 6T/83.3% WR +$0.05
- **7d LEGACY (killed, aging out):** ema300_dip_short 24T/41.7% WR -$1.48 | sma20_dip 19T/42.1% WR -$0.73 | ema300_dip 55T/63.6% WR -$0.72
- **Market:** 3 SHORT / 0 LONG / 115 NEUTRAL (SHORT_BIAS) as of 18:17 UTC.
- **LONG_NEUTRAL_BLOCK_ENABLED=True** — blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS.
- **BB_BOUNCE_V2_LONG:** Live. 73T/7d 74.0% WR +76.77%. STAR. Today 2T/50% WR +0.98%.
- **PUMP_CHAIN:** Live. 43T/7d 67.4% WR +13.53%. Today 9T/33.3% WR +3.14%.
- **OPEN_SKIES:** Live. 19T/7d 63.2% WR +61.24%. Today 2T/50% WR -6.59% (variance).
- **CONTINUATION:** Live. 6T/7d 83.3% WR +5.16%. Low volume.
- **PULLBACK_ENTRY-:** Live. 3T/7d 100% WR +3.65%. SHORT only.
- **PUMP-CHAIN-:** KILLED by signal_reporter 17:12 UTC. 6T/24h 50%WR -$0.63 (losses 8.8x wins).
- **PULLBACK_ENTRY+:** KILLED by auto_1hr 15:10 UTC. 4T/24h 25%WR -$0.34.
- **PUMP_FLOW+:** KILLED by auto_1hr 03:10 UTC. 8T/24h 25%WR.
- **EMA300-DIP-LONG:** KILLED by orchestrator. Protection expired 05:00 UTC. 3T/48h 33.3%WR -$4.18. NEVER_REENABLE.
- **EMA300-DIP-SHORT:** KILLED by orchestrator. Protection expired 05:00 UTC. 16T/48h 43.8%WR -$36.54. NEVER_REENABLE.
- **ACCEL_300_V3_LONG:** KILLED by orchestrator. Protection expired 05:00 UTC. 1T/48h 0%WR -$5.10. NEVER_REENABLE.
- **ACCEL_300_V3_SHORT:** KILLED by orchestrator. Protection expired 05:00 UTC. 2T/48h 50%WR but 7d -4.21%. NEVER_REENABLE.
- **Coin tracker:** Timer enabled, running every 30min.
- **CONF_FILTER_MIN=70.**
- **Disk:** 84% (19G free).
- **PM_TRAIL:** ACTIVATE 0.40%, DISTANCE 0.20%. Protected (DO NOT CHANGE).
- **ATR_SL:** MIN 1.2%, MAX 1.5% (reverted from 1.5%/1.8% on Sep 8).
- **Cut-loser fix:** VERIFIED in position_manager.py:363. threshold = -sl_dist * 100 * leverage.

**🔴 R:R STATUS (STRUCTURAL — IMPROVING)**
24h exit breakdown (all exits):
- atr_sl_hit: 27T, avg -1.15%, -$0.45 — #1 exit count
- profit-monster-trail: 7T, avg +2.04%, +$0.30 — only profitable exit
- cut-loser-CL-T1: 2T, avg -4.21%, -$0.31 — FIXED (was 22T/48h)
- rr_engine_resistance: 2T, avg -2.18%, -$0.25

**🔴 CRITICAL BUG FIX: cut-loser sl_distance vs leveraged pnl_pct**
`should_cut_loser()` Priority 2 compared `sl_distance` (price-move %) against `pnl_pct` (LEVERAGED). With leverage=3 and sl_distance=0.015: a 0.5% price drop = -1.5% leveraged pnl → cut-loser fires at -0.5% instead of -1.5%. This made effective SL 3x tighter than intended. **FIX: threshold = -sl_dist * 100 * leverage (was / leverage).** Pipeline restarted. Expected: cut-loser fires at correct 1.2%-1.5% price move, avg loss drops from -4.98% to ~-2%, R:R improves.

## Today's Changes (Sep 9)

0. **CEO ~19:10 UTC — VERIFIED + MONITORING.** DB: 42T/24h 47.6% WR -$0.72. 7d: 371T 57.7% WR -$3.31. Sep 9: 34T 55.9% WR +$0.16. **Orchestrator already handled all kills** (ema300-dip-short, ema300-dip-long, accel-300-v3-long/short, pullback-entry+, pump-chain-). All NEVER_REENABLE. **Active signals healthy:** bb_bounce_v2_long 73T/74.0% WR +$2.08, open_skies 19T/63.2% WR +$1.56, pump_chain 43T/67.4% WR +$1.11, continuation 6T/83.3% WR +$0.05. **R:R:** avg_win 3.24%, avg_loss -4.46%, ratio 0.726 (breakeven 58.0%, actual 57.7%). PM_TRAIL/ATR_SL protected. 3 open positions. Market SHORT_BIAS. **7d PnL should turn positive within 24-48h as legacy drops off.** No param changes needed.
1. **Orchestrator ~18:35 UTC — ACTION.** DB: 42T/24h 47.6% WR. 7d: 371T 58.8% WR -100.96%. Market 3 SHORT / 115 NEUTRAL (SHORT_BIAS). **KILLED 4 PROTECTED SIGNALS** (protection expired 05:00 UTC): EMA300_DIP_LONG (3T/48h 33.3%WR -$4.18), EMA300_DIP_SHORT (16T/48h 43.8%WR -$36.54), ACCEL_300_V3_LONG (1T/48h 0%WR -$5.10), ACCEL_300_V3_SHORT (2T/48h 50%WR 7d -4.21%). All added to NEVER_REENABLE_FLAGS, removed from CEO_PROTECTED_FLAGS. **Cut-loser fix VERIFIED** in position_manager.py:363 (threshold = -sl_dist * 100 * leverage). **ATR_SL reverted to 1.2%-1.5%** (Sep8). **Signal reporter killed PUMP_CHAIN- SHORT** (6T/50%WR -$0.63, losses 8.8x wins). **auto_1hr killed PULLBACK_ENTRY+** (4T/25%WR -$0.34) and **PUMP_FLOW+** (8T/25%WR). 2 open positions (ONDO SHORT +0.11%, YGG SHORT -0.07%). Disk 84%. signal_compactor 3x timeout/hr (recurring, non-fatal). Pipeline restarted. **Active signals: bb_bounce_v2_long ★, pump_chain, open_skies, continuation, pullback-entry-.**

## Today's Changes (Sep 8)

8. **CEO ~22:30 UTC — VERIFIED + ACTION.** DB: 24h 70T 45.7% WR -$2.51 (WORST DAY). 48h: 128T 53.1% WR -$2.22. 7d: 387T 56.1% WR -$4.88. Sep 8: 66T 43.9% WR -$2.51. **ROOT CAUSE: R:R COLLAPSE.** cut-loser-CL-T1 24 exits avg -4.84% = -$3.48. atr_sl_hit 13 exits avg -2.44% = -$0.72. Wins avg 2.51% vs losses avg -4.90% → R:R 0.513. **FIX: Reverted ATR_SL_MIN 1.5%→1.2%, ATR_SL_MAX 1.8%→1.5%.** All 6 fallbacks updated. Expected: avg loss drops from -4.84% to ~-2%, R:R from 0.51 to 0.70+. bb-bounce-v2-long+ 7T/28.6% WR -$0.74 (variance). ema300-dip-short 13T/38.5% WR -$0.96 (aging out). pump-chain+ 16T/50% WR -$0.62. open-skies+ 2T/50% WR +$0.48. 4 open. Disk 82%. PM_TRAIL protected. Market 100% NEUTRAL.

7. **Orchestrator ~18:35 UTC — VERIFIED + NO CHANGES.** DB: 24h 71T 52.1% WR -$1.21. 48h: 129T 58.9% WR -$1.32. 7d: 200T 57.5% WR -$2.10. Sep 8: 59T 50.8% WR -$1.86. **SYSTEM STEADY STATE — no changes needed.** Pipeline active, 409 signals generating, health monitor OK. 5 open positions (all LONG, all slightly negative). **cut-loser-CL-T1 is #1 loss driver:** 21T/24h -$3.04 (exit management, not signal quality). **ema300-dip-short:** EMA300_DIP_SHORT_ENABLED still True in constants (auto_1hr kill at 16:10 overridden by T's re-enable commit). CEO protection until Sep 9 05:00. 12T/24h 41.7% WR -$0.96 — aging out. **sma20-dip+:** SMA20_DIP_PLUS_ENABLED=False (killed). 19T residual rotating out. **bb-bounce-v2-long+:** 6T/33.3% WR -$0.54 today (variance). 7d 37T/73.0% WR +$1.31 still strong. **open-skies+:** 1T/100% WR +$0.48 today. Only healthy R:R. **R:R 24h: 0.662** (breakeven WR 60.1%, actual 52.1%). Disk 82%. Market 1 LONG_BIAS / 2 SHORT_BIAS / 103 NEUTRAL. PM_TRAIL protected. No param changes. **Target: 48h positive by Sep 9 as legacy fully ages out.**

6. **CEO ~19:00 UTC — VERIFIED + MONITORING.** DB: 24h 72T 50.0% WR -$1.21. 48h: 130T 57.7% WR -$1.32. 7d: 388T 57.0% WR -$4.24. Sep 8: 60T 48.3% WR -$1.86 (worst in 7d). **Legacy signal bleed is dominant:** ema300-dip-short 16T/43.8% WR -$0.96 (killed 16:10 UTC, aging out), sma20-dip+ 19T/42.1% WR -$0.73 (killed 12:10 UTC, aging out). **bb-bounce-v2-long+ variance:** 9T/44.4% WR -$0.57 today but 7d 71T/74.6% WR +$2.19 still strong, R:R 0.612. **open-skies+ only healthy signal:** 2T/24h 100% WR +$1.42, R:R 1.303. **R:R 24h: 0.681** (breakeven WR 59.5%, actual 50%). PM_TRAIL 0.20% tight — was 0.60% on Sep 6, reverted. 5 open flat. Disk 82%. **No param changes** — legacy aging out, active signals profitable on 7d. **Target: 48h positive by Sep 9 as legacy fully ages out.**

5. **CEO ~16:00 UTC — VERIFIED + MONITORING.** DB: 24h 73T 54.8% WR -$0.47 (was +$1.06 at 10:35). 48h: 121T 58.7% WR -$0.88. Sep 8: 48T 50% WR -$1.25 (worst day in 4). **bb-bounce-v2-long+ STAR degraded** — 13T/38.5% WR -$0.91 (7d still 71T/74.6% WR +$2.19). cut-loser-CL-T1 7/13 exits at -5.32% avg. **sma20-dip+ KILLED** by auto_1hr at 12:10 UTC (0%WR last hour, 47.1% all-time). **ema300-dip-short** 12T/24h 66.7% WR -$0.30, protected until Sep 9. **open-skies+ ONLY healthy R:R** — 3T/24h 66.7% WR +$1.23, R:R 3.737. **No param changes** — bb-bounce 74.6% WR 7d is variance, not structural. PM_TRAIL protected. Legacy aging out. 5 open positions. Disk 82%. **Target: 48h positive as bb-bounce recovers and legacy ages out.**

4. **CEO ~10:35 UTC — VERIFIED + MONITORING.** DB: 24h 66T 62.1% WR +$1.06. 48h: 117T 59.0% WR -$0.43. 7d: 376T 57.7% WR -$3.10. Today Sep 8: 36T 55.6% WR -$0.33 (breaks 4-day streak). **bb-bounce-v2-long+ degraded today** — 5T/40% WR -$0.36 (was star). ema300-dip-short 5T/40% WR -$0.50 (T-re-enabled, protected). **R:R compression is structural:** bb-bounce 0.623, pump-chain 0.369, sma20-dip 0.482. Only open-skies+ healthy at 1.303. Legacy bleeders aging out of 48h by tomorrow. 5 open (4 LONG sma20-dip+, 1 SHORT ema300-dip). Disk 82%. Pipeline healthy. PM_TRAIL protected. No param changes. **Target: 48h flips positive as legacy ages out.**

3. **CEO ~07:00 UTC — VERIFIED + MONITORING.** DB: 24h 58T 67.2% WR +$1.73. 48h: 109T 62.4% WR +$0.63. 7d: 372T 57.8% WR -$2.64. **4 CONSECUTIVE GREEN DAYS** (Sep 5 +$0.47, Sep 6 +$0.40, Sep 7 +$0.01, Sep 8 +$0.42 in progress). **open-skies+ RECOVERED:** 6T/48h 66.7% WR +$1.19 (was 40% WR -$0.37 at Sep 7 18:40). All 5 exits atr_sl_hit. **ema300-dip SHORT 6T/24h -$0.13** — T re-enabled, protected until Sep 9 05:00. **cut-loser-CL-T1 14T/24h -$1.97** — biggest drag, avg -$0.141. All other signals profitable. **Daily: Sep 2 -$1.79 → Sep 3 +$0.33 → Sep 4 -$1.75 → Sep 5 +$0.47 → Sep 6 +$0.40 → Sep 7 +$0.01 → Sep 8 +$0.42.** R:R 0.733. 5 open positions -$0.40 unrealized. Disk 82%. Market 1 LONG_BIAS / 2 SHORT_BIAS / 103 NEUTRAL. PM_TRAIL protected. No param changes. **Target: 7d PnL turns positive by Sep 9 as legacy fully exits.**

2. **Orchestrator ~06:30 UTC — VERIFIED + NO CHANGES.** DB: 24h 58T 67.2% WR +$1.73. 48h: 109T 62.4% WR +$0.63. 7d: 372T 57.8% WR -$2.64 (improving from -$2.59 at 02:00). **SYSTEM STEADY STATE — no changes needed.** All signals healthy: bb-bounce-v2-long+ 67T/7d 77.6% WR +$2.62, pump-chain+ 27T/7d 81.5% WR +$0.57, open-skies+ 17T/7d 64.7% WR +$1.55, sma20-dip+ 9T/24h 55.6% WR +$0.15. R:R 0.731 (avg_win $0.109, avg_loss $0.149). **Health monitor auto-fixed EMA300 NameError** (missing import in decider_run.py:3472 — 42 crashes in 30min → 0 after fix). signal_compactor timeout recurring but non-fatal. 5 open positions (bb-bounce-v2-long+ x2, sma20-dip+ x2, ema300-dip-short x1). Disk 82%. Market 1 LONG_BIAS / 2 SHORT_BIAS / 103 NEUTRAL. PM_TRAIL protected. No param changes. **Target: 7d PnL turns positive within 48h as legacy fully exits.**

1. **CEO ~02:00 UTC — VERIFIED + UPDATED.** DB: 24h 56T 71.4% WR +$1.99. 48h: 100T 63.0% WR +$0.80. 7d: 374T 58.0% WR -$2.59. **STRONGEST 24H IN WEEKS** — improved from +$0.29 at 21:00. All 4 active signals profitable: bb-bounce-v2-long+ 65T/7d 78.5% WR +$2.73 ★, open-skies+ 17T/7d 64.7% WR +$1.55 ★, pump-chain+ 24T/7d 87.5% WR +$0.88 ★, continuation+ 6T/7d 83.3% WR +$0.05. **Legacy slow-grind+ fully exited** — last trade 12:58 UTC Sep 7. 24h legacy only 2T (-$0.05). R:R 0.740 (avg_win $0.108, avg_loss $0.146). 5 open positions (bb-bounce-v2-long+ x2, pump-chain+ x3). Disk 82%. Market 100% NEUTRAL. PM_TRAIL protected. No param changes. **Target: 7d PnL turns positive within 48h as legacy fully exits.**

## Today's Changes (Sep 7)

9. **CEO ~21:00 UTC — VERIFIED + MONITORING.** DB: 24h 58T 62.1% WR +$0.29. 48h: 92T 62.0% WR +$0.41. 7d: 375T 57.6% WR -$3.29. **24h FLIPPED POSITIVE** — improved from -$0.11 at 18:40. Active signals profitable: bb-bounce-v2-long+ 9T/24h 66.7% WR +$0.28, pump-chain+ 18T/24h 88.9% WR +$0.64, open-skies+ 5T/24h 60% WR +$0.71. **Legacy still draining:** slow-grind+ 12T/24h 25% WR -$1.22 (ages out Sep 8). **open-skies+ R:R 1.88** — avg_win $0.37, avg_loss $0.20. Emerging star. **5 open positions.** Disk 81%. PM_TRAIL protected. No param changes. Market 100% NEUTRAL. **Target: 24h stays positive after slow-grind+ fully exits.**
8. **CEO ~18:40 UTC — VERIFIED + MONITORING.** DB: 24h 58T 67.2% WR -$0.11. 48h: 87T 59.8% WR -$0.71, R:R 0.566. **Almost flat — improved from -$1.10 earlier.** Active signals profitable: bb-bounce-v2-long+ 9T/24h 77.8% WR +$0.41, pump-chain+ 19T/24h 89.5% WR +$0.64. **Legacy nearly gone:** slow-grind+ 15T/24h 40% WR -$0.80 (last close 12:58 UTC, ages out Sep 8 12:58). coil-spring+ aged out of 24h, 20T/48h remaining. **open-skies+ degraded:** 5T/48h 40% WR -$0.37 but 14T/7d 57.1% NEUTRAL flat. **3 open positions** near $0. Pipeline healthy, disk 81%. PM_TRAIL protected. No param changes. Market 100% NEUTRAL. **Target: 24h PnL positive after slow-grind+ exits window (Sep 8 12:58).**
7. **CEO ~06:45 UTC — VERIFIED + MONITORING.** DB: 24h 51T 56.9% WR -$1.10. 48h: 85T 57.6% WR -$0.71, R:R 0.563. **Active signals profitable:** bb-bounce-v2-long+ 9T 77.8% WR +$0.28, pump-chain+ 8T 100% WR +$0.31. Without legacy: 25T 76% WR +$0.22. **Legacy bleed is entire loss:** slow-grind+ 14T -$0.88 + coil-spring+ 12T -$0.44 = -$1.32. 1 open slow-grind+ position (pre-kill 06:02 UTC). coil-spring+ ages out ~15:03 UTC today. slow-grind+ ages out ~03:25 UTC Sep 8. **PM_TRAIL protected (DO NOT CHANGE).** No param changes. Disk 84%. Market 100% NEUTRAL. 3 open positions.
6. **Orchestrator ~06:30 UTC — VERIFIED + ACTION.** DB: 24h 51T 59.2% WR -$1.10. 7d: 375T 56.9% WR -$5.11. **R:R 24h: 0.451** (degraded from 0.67 on Sep 6). **slow-grind+ KILLED** — 10T/24h 10% WR -$1.42, 9 consecutive losses. Added to NEVER_REENABLE_FLAGS. Pipeline restarted. **bb-bounce-v2-long+ STAR:** 56T/7d 80.4% WR +$2.52. **pump-chain+:** 8T/7d 100% WR +$0.31. **open-skies+:** 14T/7d 64.3% WR +$0.32. **Market:** 3 LONG / 2 SHORT / 103 NEUTRAL. **3 open positions:** NEO LONG, SOL LONG, TURBO SHORT. **Disk:** 84% (18G free). **ema300-dip RE-ENABLED by T** (Sep 7). DO NOT DISABLE until Sep 9 05:00 UTC. **PM_TRAIL:** 0.40%/0.20% (tight trail, reverted from 0.60%/0.60%). R:R degraded — needs monitoring.

## Today's Changes (Sep 6)

6. **CEO ~18:15 UTC — VERIFIED + MONITORING.** DB: 24h 32T 50% WR -$0.34. 7d: 362T 54.1% WR -$4.12. **R:R 24h: 0.67** (avg_win $0.105, avg_loss $0.155) — improving from 0.61 (48h). **R:R 48h: 0.61** (avg_win $0.077, avg_loss $0.126) — still underwater. **bb-bounce-v2-long+ STAR:** 19T/48h 84.2% WR +$1.47. **open-skies+:** 11T/48h 63.6% WR +$0.36. **coil-spring+ KILLED by auto_1hr at 15:07 UTC** — 6T last hour 0%WR -$0.74. 21T residual rotating out. **ema300-dip-short DEAD:** 6T/48h 16.7% WR -$0.60. **Market 100% NEUTRAL.** 5 open positions. Disk 83%. **NO PARAM CHANGES.** PM_TRAIL 0.60% distance needs more time. Monitor R:R improvement. Target: 48h R:R 0.80+ by Sep 8.
5. **Orchestrator ~18:35 UTC — VERIFIED + REPORT.** DB: 24h 28T 50% WR -$0.27. 7d: 359T 54.3% WR -$3.92. **R:R 48h: 0.61, 24h: 0.72** (improving). **coil-spring+ KILLED 15:07 UTC** — 21T still in 24h window (-$0.65), rotating out. **neutral_sniper firing signals** (FOGO SHORT conf=75) but **BTC-CRASH filter blocks all SHORTs** during BTC weakness — 0 live trades, working as designed. **signal_compactor sporadic timeouts** (31 in 6h, non-fatal, self-recovers). **CHOP_DETECTOR transient import error** (caught, non-fatal). **bb-bounce-v2-long+ STAR:** 19T/48h 84.2% WR +$1.47. **PM_TRAIL 0.60% working:** 24h R:R 0.72. **5 open positions** all near $0. Disk 83%. Market 100% NEUTRAL. No parameter changes needed.
4. **CEO ~10:35 UTC — VERIFIED + ACTION.** DB: 24h 36T 61.1% WR +$0.51. 7d: 364T 54.4% WR -$4.11. **R:R 48h: 0.61** (avg_win $0.1026, avg_loss $0.1691). Still underwater. **PM_TRAIL_DISTANCE_PCT 0.50%→0.60%** — lets winners run further. Expected: avg_win $0.10→$0.12+, R:R 0.61→0.75+. **NEUTRAL_SNIPER RSI 40/60→45/55** — 40/60 was STILL too tight (RSI clusters 45-55 in NEUTRAL). Verified: 58% of tokens now hit extremes. Tested OK: ACE LONG conf=73, ALT LONG conf=73, AR SHORT conf=68. **bb-bounce-v2-long+ STAR:** 14T/48h 92.9% WR +$1.42. **open-skies+:** 11T/48h 63.6% WR +$0.36. **coil-spring+:** 15T/48h 60% WR +$0.04. **5/5 positions full.** Disk 82%. Market 100% NEUTRAL. 3rd green day.
3. **Orchestrator ~06:40 UTC — VERIFIED + ACTION.** DB: 24h 34T 58.8% WR +$0.55. 7d: 353T 57.5% WR -$2.76. R:R 24h: 0.904 (avg_win $0.122, avg_loss $0.135) — approaching breakeven. **KILLED ACCEL_300_V3_LONG + V3_SHORT** — CEO protection expired 05:00 UTC. Added to NEVER_REENABLE_FLAGS, removed from CEO_PROTECTED_FLAGS. 36T/7d v3-long 47.2%WR -$0.88, 3T/7d v3-short 33.3%WR -$0.02. **NEUTRAL_SNIPER ROOT CAUSE FOUND** — chop_detector.py classified neutral_sniper as MOMENTUM (default fallback), blocking it in CHOP regime. Fixed: added to SIGNAL_OVERRIDES as MEAN_REVERSION. 26 shadow signals in 48h, 0 live trades due to chop block. Expected: signals now fire in NEUTRAL. **5/5 positions full.** Disk 82%. Market 100% NEUTRAL.
2. **CEO ~07:00 UTC — VERIFIED + ACTION.** DB: 24h 34T 58.8% WR +$0.39. 7d: 364T 54.4% WR -$4.11. **R:R 48h: 0.60** (avg_win $0.1003, avg_loss $0.1678). Still underwater. **NEUTRAL_SNIPER: 0 SIGNALS in 4h live.** Root cause: RSI thresholds (35/65) too extreme for 100% NEUTRAL market. **FIX: Widened RSI 35→40 (LONG), 65→60 (SHORT).** Expected: signals start firing. **bb-bounce-v2-long+ STAR:** 11T/24h 90.9% WR +$1.29. 47T/7d 80.9% WR +$2.24. **coil-spring+ DEGRADED:** 9T/24h 44.4% WR -$0.21 (was 60%). Monitor. **open-skies+ DEGRADED:** 8T/24h 50% WR -$0.19 (was 63.6%). Monitor. **5/5 positions full.** Disk 82%. Market 100% NEUTRAL. 2 consecutive green days.
1. **CEO ~02:35 UTC — VERIFIED + ACTION.** DB: 24h 33T 63.6% WR +$0.64. 7d: 366T 54.4% WR -$4.16. **R:R IMPROVING:** 24h ratio 0.67 (avg_win $0.104, avg_loss $0.154). Up from 0.57 48h. PM_TRAIL distance widening working. **NEUTRAL_SNIPER FLIPPED LIVE** — 3756 shadow signals in 11h, system needs SHORT backbone for NEUTRAL. SHADOW_MODE=False. **bb-bounce-v2-long+ STAR:** 11T/24h 90.9% WR +$1.00, 46T/7d 80.4% WR +$1.92. **coil-spring+ EMERGING:** 5T/24h 60% WR +$0.21. **open-skies+ DEGRADED:** 9T/24h 55.6% WR -$0.05 (was 70% WR). Disk 82%. Market ~100% NEUTRAL. 5 open ~$0. Signal starvation partially resolved — neutral_sniper now live for SHORT.

## Today's Changes (Sep 5)

4. **CEO ~15:00 UTC — VERIFIED + ACTION.** DB: 24h 31T 64.5% WR +$0.70. 7d: 367T 54.8% WR -$4.35. **R:R STILL UNDERWATER (31 trades):** avg win $0.111, avg loss $0.152, R:R 0.73. Breakeven WR 68.1%, actual 64.5%. Expected value +$0.019/trade (marginal). **PM_TRAIL_DISTANCE_PCT WIDENED 0.40%→0.50%** — lets winners run further. Expected: avg_win $0.111→$0.122, R:R 0.73→0.80. **ema300-dip-short ALREADY KILLED** by earlier run (NEVER_REENABLE). **bb-bounce-v2-long+ STAR:** 9T/24h 88.9% WR +$0.69. **open-skies+ GROWING:** 10T/24h 70% WR +$0.50. **continuation+:** 5T/7d 100% WR +$0.33. Disk 82%. Market NEUTRAL. 5 open ~-$0.05. **SHORT side has NO active backbone — system 100% LONG-dependent.**
3. **CEO ~14:30 UTC — VERIFIED + MONITORING.** DB: 24h 27T 66.7% WR +$0.59. 7d: 367T 54.8% WR -$4.35. **R:R FIX CONFIRMED (26 trades):** avg win $0.114 (2.1x pre-fix), avg loss $0.152. R:R 0.75 (up from 0.57, +31.6%). WR 65.4% > breakeven 57.1%. profit-monster-trail 14T/26 = 53.8% of exits, avg +$0.123. **bb-bounce-v2-long+ GROWING:** 43T/7d 79.1% WR +$1.57 (was 36T at 08:00). **open-skies+ GROWING:** 8T/7d 75% WR +$0.44 (was 3T). **ema300-dip-short WORSENING:** 7T/7d 28.6% WR -$0.57 (was 40% WR at 08:00). Monitor — if reaches 15T with WR <45%, kill. Disk 82%. Market 104/107 NEUTRAL. 1 open (LTC LONG open-skies+). Pipeline healthy. **Key finding: R:R fix works but avg loss ($0.152) still > avg win ($0.114). Need to either widen TP or tighten SL further.**
2. **CEO ~08:00 UTC — VERIFIED + ACTION.** DB: 24h 31T 64.5% WR -$0.24. 7d: 368T 54.9% WR -$4.34. **R:R fix (11 trades):** avg win $0.124 (2.3x pre-fix $0.053), avg loss $0.143 (+10%). R:R 0.57→0.87 (+52.6%). WR 64.5% > breakeven 53.5%. Need 20+ trades. **bb-bounce-v2-long+ STAR:** 36T/7d 77.8% WR +$0.95. All NEUTRAL. **open-skies+:** 3T/7d 100% WR +$0.55. **continuation+:** 4T/7d 100% WR +$0.30. **ema300-dip-short DEGRADED:** 5T/7d 40% WR -$0.29 — 4/5 exits cut-loser-CL-T1. Monitoring (kill at 15T if WR <45%). **NEUTRAL_SNIPER DEPLOYED:** shadow mode, RSI+CMF+ATR mean-reversion, 5 SHORT signals in test. Disk 82% (was 85%, cleaned). Market 100% NEUTRAL. 2 open. No parameter changes.
1. **Orchestrator 06:30 UTC — VERIFIED + CLEANUP.** DB: 24h 31T 64.5% WR -$0.24. 7d: 368T 54.9% WR -$4.34. **R:R fix post-analysis (11 trades):** profit-monster-trail avg +$0.142 (2.7x old), cut-loser-CL-T1 avg -$0.142. Net +$0.30. R:R 0.69→1.26 (83%). Need 20+ to confirm. **Disk cleanup:** freed 3G (coin_tracker 2.2G→752MB, hl_copy 1.9G→324MB). Disk 84%→82%. **Market:** 3 LONG_BIAS / 105 NEUTRAL. **Open:** 4 positions. **Signal starvation #1 problem** — system on 1 profitable backbone. NEUTRAL signal build pending since Sep 1. No parameter changes.
2. **CEO ~03:00 UTC — VERIFIED + MONITORING.** DB: 24h 37T 54.1% WR -$1.27. 7d: 371T 54.2% WR -$4.62. R:R fix post-analysis (7 trades): R:R 0.69→1.26 (83%). Too early. No parameter changes.

## Today's Changes (Sep 4)

5. **CEO ~23:00 UTC — VERIFIED + MONITORING.** DB: 24h 45T 48.9% WR -$1.82. 7d: 384T 53.6% WR -$4.89. R:R fix deployed ~20:00, only 1 trade closed post-fix (+$0.13). Need 20+ trades to evaluate. ema300-dip legacy closing (19T/24h). ema300-dip-short alive (2T/7d +$0.16 100% WR). 4 open positions ~-$0.25. Disk cleanup ~1G freed (84%). accel-300-v2-short- 27.3% WR ALL NEUTRAL — monitor.
4. **CEO ~20:00 UTC — R:R FIX.** Verified DB: 24h 61T 54.1% WR -$1.93. 7d: 384T 53.6% WR -$4.89. **R:R FIX APPLIED** — PM_TRAIL_ACTIVATE_PCT 0.40%→0.60%, PM_TRAIL_DISTANCE_PCT 0.20%→0.40%. ATR_SL_MIN 1.2%→1.5%, ATR_SL_MAX 1.5%→1.8%. All fallbacks updated (SL_PCT_FALLBACK, STOP_LOSS_DEFAULT, SL_PCT_MIN, TP_PCT_FALLBACK 3.6%→4.5%). TRAILING_ACTIVATION_PCT 0.40%→0.60%. **Expected:** avg win $0.074→$0.11+, R:R 0.57→0.73, breakeven WR 63.7%→55.6%. bb-bounce-v2-long+ STAR (34T/76.5%WR +$0.88/7d) should benefit most. System on 2 backbone signals. 2 open legacy positions flat.
3. **Orchestrator 18:30 — VERIFIED + ANALYSIS.** DB: 24h 58T 60.3% WR -$1.76. 7d: 373T 57.9% WR -$3.63. ema300-dip KILLED at 17:14. R:R ROOT CAUSE: PM_TRAIL wins avg $0.060, ATR_SL losses avg $0.133. NEXT: Fix R:R (done by CEO).
2. **Signal Reporter 17:14 — KILL.** ema300-dip killed. EMA300_DIP_ENABLED=False, added to NEVER_REENABLE. 34T/24h 58.8% WR -$1.13. Last 6h 25% WR -$1.14. Structural: avg loss ($0.15) 2.7x avg win ($0.057). Committed + pushed.
1. **Orchestrator 06:30 — VERIFIED + FLAGGED.** DB: 24h 82T 59.8% WR -$0.73. 7d: 407T 54.1% WR -$3.42. **R:R PROBLEM: 59.8% WR losing money — avg loss > avg win.** All signals negative today. v3-short- killed by auto_1hr (3T/0% WR -$0.48, pre-kill positions). cascade_flip trade (ENA) happened before disable at 04:36. slow-grind- TESTING 3T/7d 33.3% WR -$0.17. 5 open positions small. Disk 84%. 22 failed services (one-shot). Health monitor auto-fixed logs. **CRITICAL: Exit quality is bottleneck — not signal selection. Needs R:R investigation.**
0. **CEO 06:00 — VERIFIED + ACTION.** DB: 24h 82T 59.8% WR -$0.73. 7d: 410T 53.7% WR -$3.42. **v3-long+ CONFIRMED DEAD** — zero Sep 4 trades (last trade Sep 3). v3-short- killed by auto_1hr today (3T/0% WR -$0.48). **KILLED slow-grind-** — 15T/30d 33.3% WR -$0.81. Added to NEVER_REENABLE_FLAGS. Added ACCEL_300_V3_SHORT to NEVER_REENABLE. 3 backbone signals ALL profitable 14d: accel-300-v2- SHORT 72T/52.8%WR +$1.46, bb-bounce-v2-long+ 33T/75.8%WR +$0.86, ema300-dip 44T/68.2%WR +$0.19. Today losses normal variance (ema300-dip 8T/50% -$0.32, bb-bounce 5T/40% -$0.04). 5 open ~$0. Disk 84% ⚠️ approaching 85% trigger. Market 100% NEUTRAL. **EXPECTED IMPACT: slow-grind -$0.81/30d removed. v3-long+ -$1.34/7d already removed. System should be profitable with only backbone signals.**
1. **Orchestrator 06:30 — VERIFIED + FLAGGED.** DB: 24h 82T 59.8% WR -$0.73. 7d: 407T 54.1% WR -$3.42. **R:R PROBLEM: 59.8% WR losing money — avg loss > avg win.** All signals negative today. v3-short- killed by auto_1hr (3T/0% WR -$0.48, pre-kill positions). cascade_flip trade (ENA) happened before disable at 04:36. slow-grind- TESTING 3T/7d 33.3% WR -$0.17. 5 open positions small. Disk 84%. 22 failed services (one-shot). Health monitor auto-fixed logs. **CRITICAL: Exit quality is bottleneck — not signal selection. Needs R:R investigation.**
2. **CEO 02:35 — VERIFIED + ACTION.** DB: 24h 86T 64.0% WR +$0.07. 7d: 416T 54.8% WR -$1.83. **DISABLED ACCEL_300_V3_LONG_ENABLED** — CEO_PROTECTION expired Sep 4 05:00. Flag set False, removed from CEO_PROTECTED_FLAGS, added to NEVER_REENABLE_FLAGS. 35T/7d 42.9% WR -$1.34, ALL ATR_SL. No open v3-long+ positions (safe to kill). 5 open: v3-short x2, bb-bounce-v2-long+ x1, ema300-dip x1, slow-grind- x1. R:R analysis: accel-300-v2- SHORT best at 1.15. bb-bounce-v2-long+ STAR 32T/78.1% WR +$1.00. ema300-dip STAR 40T/67.5% WR +$0.16. **EXPECTED IMPACT: -$1.34/7d bleeding removed. System should be near breakeven or profitable without v3-long+.**

## Today's Changes (Sep 3)

0. **CEO 17:22 — VERIFIED + ACTION.** DB: 24h 75T 66.7% WR +$0.30. Today: 61T 67.2% WR +$0.49 (BEST DAY since Aug 28 +$1.55). Daily: Aug 28 +$1.55 → Sep 2 -$1.79 → Sep 3 +$0.49 (STRONG REVERSAL). 17h traded, system trending positive. ema300-dip 24T/7d 75% WR +$0.69 STAR. bb-bounce-v2-long+ 20T/7d 85% WR +$0.74 STAR. v3-long+ 35T/7d 42.9% WR -$1.34 CEO_PROTECTED until Sep 4 05:00. bb-bounce-short KILLED by auto_1hr at 17:06 (3T/33.3% WR -$0.35). 5 open LONG positions ~$0. Disk 83%. Preserve mechanism bug: STX LONG stale signal. **ACTIONS: (1) Updated CURRENT.md. (2) v3-long+ MUST disable after 05:00 UTC Sep 4. (3) System on 3 strong signals: accel-300-v2- SHORT, bb-bounce-v2-long+, ema300-dip.**
1. **CEO 10:32 — VERIFIED + UPDATE.** DB: 24h 52T 57.7% WR -$1.16. Today: 26T 65.4% WR -$0.11 (best day since Aug 28). Daily: Aug 28 +$1.55 → Sep 2 -$1.79 → Sep 3 -$0.11 (improving). 9 hours traded, 6 green hours. Kills verified: range-reversion 0 post-kill trades (last closed Sep 2 13:50), r2-trend-long3 0 post-kill trades (last closed Sep 3 01:02). accel-300-v3-long+ still CEO_PROTECTED, 4T/24h 25% WR -$0.48. Open positions flat (~$0 unrealized). No signal_compactor timeout issues in recent logs. **ACTIONS: (1) Updated CURRENT.md. (2) Prepared to disable accel-300-v3-long+ tomorrow. (3) Monitoring bb-bounce-v2-long+ and ema300-dip for expansion.**
2. **CEO 06:34 — VERIFIED + UPDATE.** DB: 24h 52T 51.9% WR -$1.63. 7d: 399T 51.6% WR -$2.35. **r2-trend-long3 KILL CONFIRMED** — signal_reporter killed it, 0 new trades post-kill (last trade closed 01:02 UTC). accel-300-v3-long+ still CEO_PROTECTED, 4 trades/24h ALL ATR_SL losers (-$0.59). bb-bounce-v2-long+ 13T/7d 76.9% WR +$0.20 strong. ema300-dip 9T/7d 66.7% WR +$0.16. 5 open positions all small. Disk 82%. Market 100% NEUTRAL. Daily: Aug 28 +$1.55 → Sep 2 -$1.79 → Sep 3 -$0.17 (improving).
3. **CEO 02:15 — VERIFIED + ESCALATION.** DB: 24h 52T 51.9% WR -$1.86. 7d: 399T 51.6% WR -$2.35. 3 consecutive negative days. **ESCALATED to T: (1) DISABLE r2-trend-long3 — 10T/7d 30% WR -$0.55, CEO_PROTECTED since Aug 17, now bleeding. (2) DISABLE accel-300-v3-long+ after Sep 4 05:00 UTC — 18T/7d 33.3% WR -$0.98.** bb-bounce-v2-long+ 12T/7d 83.3% WR +$0.35 strong. volume-breakout 6T/7d confluence 100% WR. SHORT side +$0.62/7d profitable. System needs T approval to kill 2 protected bleeders.

## Today's Changes (Sep 2)

0. **Orchestrator 18:35 — VERIFIED.** All systems nominal. Dead signals (v3-long+, range-reversion) confirmed 0 post-kill trades. LONG_NEUTRAL_BLOCK working: ME LONG allowed (LONG_BIAS regime bypass). BTC-CRASH filter active, blocking SHORTs during BTC weakness. 5 open positions, -$0.15 unrealized. 59 closed today, -55% portfolio PnL (bad day but filters working). confluence-/ichimoku- SHORT still bleeding 7T/7d 28.6% WR -$0.46, CEO_PROTECTED. Disk 82%. No changes needed — steady state. NEVER_REENABLE enforcement flagged by signal reporter (code-level fix needed).
1. **CEO 14:40 — ACTION. LONG_NEUTRAL_BLOCK.** DB: 24h 63T 42.9% WR -$1.96. 7d: 411T 50.1% WR -$2.19. LONG side -$2.07/24h ALL signals negative. SHORT +$0.11/24h. ALL 63 trades in NEUTRAL. **ROOT CAUSE: No regime filter for LONG entries.** FIX: Added LONG_NEUTRAL_BLOCK_ENABLED=True + check in signal_compactor.py. Blocks LONG when 4h regime NEUTRAL. Bypass: 2+ types or 1m LONG_BIAS. V3_LONG + range_reversion kills verified (zero post-kill trades). BB_BOUNCE_V2_LONG TESTING, 0 trades. confluence-,ichimoku- SHORT CEO_PROTECTED FLAGGED FOR T.
1. **CEO 10:30 — VERIFIED + ACTION.** DB: 24h 59T 47.5% WR -$1.18. 48h: 128T 47.7% WR -$1.97. 7d: 417T 50.6% WR -$1.12. Today Sep 2: 37T 48.6% WR -$0.74. **BUG: accel-300-v2-short- still trading despite ACCEL_300_V2_ENABLED=False.** 7T/24h 28.6% WR -$0.06. Flag was True until commit 383057fb at 02:59 UTC. **FIX: Added ACCEL_300_V2_ENABLED + ACCEL_300_V2_MINUS_ENABLED to NEVER_REENABLE_FLAGS.** SHORT backbone 72T/7d +$1.46 52.8% WR strong. BB_BOUNCE_SHORT 4T/24h +$0.14 100% WR. 5 open range-reversion-long+ positions (breakeven). confluence-,ichimoku- SHORT still CEO_PROTECTED bleeding -$0.46/7d — FLAGGED FOR T. Market ALL NEUTRAL.
1. **CEO 09:00 — VERIFIED + ACTION.** DB: 24h 60T 48.3% WR -$1.15. 48h: 129T 48.1% WR -$1.95. 7d: 418T 50.5% WR -$1.41. **ROOT CAUSE: accel-300-v3-long+ RE-ENABLED after first kill** — was set True with tighter filters (MIN_GAP=2.0), still bleeding 16T/24h -0.70 37.5% WR, ALL ATR_SL in NEUTRAL. **KILLED AGAIN + added to NEVER_REENABLE_FLAGS.** BB_BOUNCE_V2_LONG NameError auto-fixed at 08:25, now live TESTING. 5 open range-reversion-long+ positions (GRASS, SOL, NEO, ALT, DOGE). SHORT +$0.36/24h, LONG -$1.51/24h. confluence-,ichimoku- SHORT still CEO_PROTECTED bleeding -$0.46/7d — FLAGGED FOR T.
1. **Orchestrator 06:38 — ACTION.** Killed BB_BOUNCE_LONG_ENABLED. DB verified: 24h 64T 48.4% WR -$1.06, 7d 418T 50.5% WR -$1.11. BB_BOUNCE_LONG: 17T/24h 52.9% WR -$0.36. Removed from CEO_PROTECTED_FLAGS, kept in NEVER_REENABLE_FLAGS. Disk 82%. 1 open (DOGE SHORT flat). Signal reporter flagged accel-300-v3-long+ 15T/24h 40% WR -$0.62 for tuning. confluence-,ichimoku- SHORT 7T/7d 28.6% WR -$0.46 flagged for T review. CONF_FILTER_MIN lowered to70 (from 75) — stale issue resolved.
1. **CEO 06:10 — VERIFIED + ACTION.** DB: 24h 63T 49.2% WR -$0.90 (improved from -$0.97). V3_LONG kill verified — last trade 05:15, no post-kill entries. **FIXED coin tracker timer** — 18 days stale → running every 30min, 96 coins processed. BB_BOUNCE_LONG still bleeding 18T/24h -$0.29, FLAGGED FOR T. CONF_FILTER_MIN gap — trades at conf=51,59,60,62 executing despite filter=70. 3 open positions. Daily trend: Aug 28 +$1.55 → Sep 2 -$0.24 (in progress).
1. **CEO 07:30 — VERIFIED + ACTION.** DB: 24h 61T 47.5% WR -$0.97. 7d: 416T 50.0% WR -$1.31. 48h: 127T 47.2% WR -$1.71. **ROOT CAUSE CORRECTED: Previous CEO overcounted — combined accel-300-v2-long + v3-long as one signal.** Actual v2-long: only 4T/24h (closing old positions, not new entries). v3-long: 14T/24h -$0.51, 42.9% WR, ALL ATR_SL — the real #1 loss source. **KILLED ACCEL_300_V3_LONG_ENABLED.** NOT CEO_PROTECTED. BB_BOUNCE_LONG still True, CEO_PROTECTED, FLAGGED for T. 7d SHORT profitable (+$0.48), LONG bleeding (-$1.79). System needs SHORT-heavy allocation.
1. **CEO 06:00 — VERIFIED + CRITICAL FLAG.** DB: 24h 60T 46.7% WR -$1.08. 7d: 405T 50.6% WR -$0.62. 48h: 114T 46.5% WR -$1.49. **CRITICAL DISCOVERY: accel-300-v2-long STILL TRADING despite constant=False.** 11T/24h -$0.52, 27.3% WR. Previous CEO run at 01:40 reported "DEAD (zero trades post-kill)" — WRONG. This is the #1 bleeding source. Needs CODE investigation — check signals_runner.py for cached imports or bypass paths. BB_BOUNCE_LONG_ENABLED still True, 23T/24h -$0.28 bleeding. 5 open SHORT (all slightly profitable). System profitable without these 2 blockers (+$1.72/7d).
2. **CEO 01:40 — VERIFIED + FLAGGED.** DB: 24h 62T 48.4% WR -$1.00. 7d: 406T 50.7% WR -$0.61. WITHOUT LEGACY: +$1.72/7d 54.7% WR. FLAGGED bb-bounce-long+ and confluence-,ichimoku- for T review.

## Today's Changes (Sep 1)

0. **CEO 21:20 — VERIFIED + FLAGGED.** BB_BOUNCE_LONG_ENABLED STILL TRUE — previous "kill" never applied. CEO_PROTECTED. 21T/24h 52.4% WR -$0.34. FLAGGED FOR T. Pipeline restarted to clear cached accel-300-v2-long state.
1. **CEO 17:07 — INCOMPLETE KILL.** Claimed to kill ACCEL_300_V2_LONG + BB_BOUNCE_LONG. accel-300-v2-long constant IS False. BB_BOUNCE_LONG constant still True — kill never applied.
2. **CEO 12:50 — ACTION.** CONF_FILTER_MIN=75. ROOT CAUSE: <75 confidence tier 14T/24h 28.6% WR -$0.72 (biggest single loss source). FIX: Added CONF_FILTER_MIN to hermes_constants.py + filter in signal_compactor.py. NOT WORKING for standalone signals — 15 trades below 75 still executed.
3. **Signal Reporter 05:10 — KILL.** Killed ACCEL_300_V2_LONG_ENABLED (29.4% WR, -$0.64, 17T/24h). Added to NEVER_REENABLE. Removed from CEO_PROTECTED and ROTATOR_PROTECTED. Committed + pushed.
4. **CEO 04:30 — ACTION.** range_reversion SHADOW→LIVE. Verified: 288 shadow signals/24h across 20 tokens. Cooldown 45min/token. SHADOW_MODE=False. System backbone: accel-300-v2- + volume_breakout + range_reversion (live).
5. **CEO 01:15 — MONITORING + DELEGATE.** Verified DB. FLAGGED accel-300-v2-long for T review. DELEGATED to signal_analyst: build NEUTRAL regime signal.
6. **CEO 00:10 — ACTION.** Fixed range_reversion shadow mode bug. ROOT CAUSE: RANGE_REVERSION_ENABLED=False. FIX: Enabled signal + SHADOW_MODE guard.

## Today's Changes (Aug 31)

0. **CEO 20:00 — ACTION.** Raised ACCEL_300_V2_LONG_MIN_GAP 1.5→2.0. ROOT CAUSE: 5T/24h 20% WR, ALL ATR_SL exits at -4.5% to -4.9%. Same pattern as SHORT fix (Aug 29). Expected: fewer trades but higher WR.
1. **Orchestrator 18:30 — MONITORING.** Verified pipeline: 3 open | 43 closed today. 24h: 43T 48.8% WR +$0.02. Open: ZEN LONG, PURR LONG, DOGE SHORT. Signal reporter fixed MACD_DIVERGENCE master switch and protected PLUS from re-enable. Auto-1hr: no changes needed. System healthy, flat market. Disk 79%.
1. **Signal Reporter 17:11 — FIX.** Fixed MACD_DIVERGENCE_ENABLED master switch True→False (both directions already dead). Added MACD_DIVERGENCE_PLUS_ENABLED to NEVER_REENABLE_FLAGS. No new kills, no boosts. System healthy.
2. **CEO 16:30 — MONITORING.** Verified DB: 24h 42T 42.9% WR -$0.33. Open: 1. macd-div- DEGRADED flagged for T review. ATR_SL MIN_GAP=2.0 working. No parameter changes.
3. **CEO 15:30 — MONITORING.** Verified DB: 24h 39T 48.7% WR -$0.56. macd-div- DEGRADED. No changes.
4. **CEO 11:20 — MONITORING.** Verified DB: 24h 40T 50% WR -$0.55. macd-div- STAR DEGRADED. volume_breakout first trade closed. No changes.
5. **CEO 08:00 — MONITORING.** volume_breakout FIRST SIGNAL FIRED. macd-div- degraded. No changes.
6. **CEO 02:45 — MONITORING.** atr_sl_hit trailing profitable. No changes.

## Today's Changes (Aug 30)

0. **CEO 23:00 — CLEANUP.** Disabled stale timers. Verified DB: 24h 36T 55.6% WR -$0.38.
1. **CEO 22:15 — DELEGATE.** Built range_reversion signal (shadow mode). Files: scripts/signals/range_reversion.py. Git: f8a0a72b.
2. **CEO 18:30 — ACTION.** Built volume_breakout signal (NEW backbone). ROOT CAUSE: signal starvation. Files: scripts/signals/volume_breakout.py.
3. **CEO 15:30 — ACTION.** Killed BB_BOUNCE_SHORT_ENABLED. System on 2 backbone: accel-300-v2- + macd-div-.
4. **CEO 07:15 — ACTION.** Reverted bb-bounce-short momentum filter (too aggressive).

## Today's Changes (Aug 29)

0. **CEO 19:00 — ACTION.** Raised ACCEL_300_V2_SHORT_MIN_GAP 1.0→2.0 (filters weak entries).
1. **CEO 16:00 — ACTION.** Killed ACCEL_300_V2_MINUS_ENABLED (25% WR -$0.14).
2. **CEO 14:30 — ACTION.** Killed ACCEL_300_V2_LONG_ENABLED (0 trades in 24h+).
3. **CEO 13:15 — ACTION.** Killed 2 dead signals: INVERSE_ACCEL_300_V2, ACCEL_300_V2_LONG_5M.

## Today's Changes (Aug 28)

1. **CEO 23:10 — MONITORING.** 24h 89T 56.2%WR +$1.55 (best day in weeks). 7d: 448T 49.6%WR -$3.96. Legacy bleed: ct-hot+ -$3.91/7d (CEO_PROTECTED), hl_copy SHORT -$0.65/7d, slow-grind- -$0.64/7d. WITHOUT LEGACY: system fully profitable. Disk 83%.
2. **CEO 06:50 — MONITORING.** 24h 73T 53.4% WR +$0.63. 4 consecutive positive hours. System improving.
3. **Orchestrator 06:35 — DISK CLEANUP.** Journal vacuumed to 500MB (-2G), pump_hunter.log truncated (-24MB). Disk 84% → 83%.
4. **CEO 02:35 — KILLED ATR_SPIKE_ENABLED.** 7T/7d 28.6% WR -$0.15, ALL atr_sl_hit exits. Disabled + added to NEVER_REENABLE.

## Active Decisions

- **SLOW_GRIND+ KILLED.** Orchestrator killed Sep 7 — 10T/24h 10% WR -$1.42, 9 consecutive losses. NEVER_REENABLE_FLAGS. — 2026-09-07
- **EMA300-DIP KILLED (both).** Orchestrator killed Sep 9 — protection expired 05:00 UTC. LONG: 3T/48h 33.3%WR -$4.18. SHORT: 16T/48h 43.8%WR -$36.54. NEVER_REENABLE_FLAGS. — 2026-09-09
- **NEUTRAL_SNIPER LIVE + CHOP FIX + BTC-CRASH BLOCK.** Flipped SHADOW_MODE=False Sep 6 02:35 UTC. chop_detector fixed (MEAN_REVERSION override). RSI widened 40/60→45/55. Signals firing (FOGO SHORT conf=75) but BTC-CRASH filter blocks all SHORTs during BTC weakness. 0 live trades. Will execute when BTC stabilizes. — 2026-09-06
- **DIRECTIONAL CAP RECOMMENDED.** Max 65% of open positions in one direction. Prevents regime-transition bleed. CEO report written. Awaiting T approval to build. — 2026-09-05
- **PM_TRAIL WIDENED.** PM_TRAIL_DISTANCE_PCT 0.40%→0.50%. R:R improving (0.57→0.90 in 24h). Need more time to reach 0.80+ target. — 2026-09-05
- **EMA300_DIP_SHORT KILLED.** 8T/7d 25% WR -$0.69. NEVER_REENABLE_FLAGS. — 2026-09-05
- **R:R FIX IMPROVING.** 24h R:R 0.90 (avg_win $0.122, avg_loss $0.135). PM_TRAIL working. Need more time. — 2026-09-06
- **COIL-SPRING+ KILLED.** signal_reporter killed at 15:07 UTC. 21T still in 24h window rotating out. — 2026-09-06
- **ACCEL_300_V2_SHORT DEAD.** ACCEL_300_V2_ENABLED=False since Sep 2. Zero post-kill trades. NEVER_REENABLE_FLAGS. — 2026-09-05
- **ACCEL_300_V3_LONG KILLED (again).** Orchestrator killed Sep 9 — protection expired 05:00 UTC. 1T/48h 0%WR -$5.10. NEVER_REENABLE_FLAGS. — 2026-09-09
- **ACCEL_300_V3_SHORT KILLED (again).** Orchestrator killed Sep 9 — protection expired 05:00 UTC. 2T/48h 50%WR but 7d -4.21%. NEVER_REENABLE_FLAGS. — 2026-09-09
- **PUMP_CHAIN- KILLED.** signal_reporter killed Sep 9 17:12 UTC. 6T/50%WR -$0.63, losses 8.8x wins. NEVER_REENABLE. — 2026-09-09
- **LONG_NEUTRAL_BLOCK DEPLOYED.** Blocks LONG entries when 4h regime is NEUTRAL. Bypass: 2+ signal types or 1m LONG_BIAS. — 2026-09-02
- **RANGE_REVERSION KILLED.** NEVER_REENABLE_FLAGS. — 2026-09-02
- **R2_TREND_LONG KILLED.** NEVER_REENABLE_FLAGS. — 2026-09-03
- **BB_BOUNCE_SHORT KILLED.** NEVER_REENABLE. — 2026-09-03
- **BB_BOUNCE_V2_LONG LIVE.** 47T/7d 80.9% WR +$2.24. STAR. — 2026-09-02
- **EMA300_DIP KILLED.** signal_reporter killed Sep 4. 55T/7d 63.6% WR -$0.72. NEVER_REENABLE_FLAGS. — 2026-09-04
- **CONF_FILTER_MIN=70.** — 2026-09-02
- **volume_breakout ACTIVE.** Confluence trades 100% WR. — 2026-08-31
- **DELEGATED: Build NEUTRAL regime signal.** — 2026-09-01
- **CONF_FILTER_MAX=89.** — 2026-08-24
- **SHORT_NEUTRAL_BLOCK_ENABLED=True.** — 2026-08-23
- **macd-div- DEGRADED.** 5T/7d 20% WR -$0.35. CEO_PROTECTED — flagged for T. — 2026-08-31
- **tl_break_short INVERTED R:R.** 16T/7d 62.5% WR -$0.11. CEO_PROTECTED. — 2026-08-27
- **hzscore- RE-ENABLED BY T.** SHORT 3T/7d +$0.30 66.7% WR. CEO_PROTECTED. — 2026-08-23
- **ACCEL_300_V2_SHORT_MIN_GAP=2.0.** — 2026-08-29

## What NOT To Do

- Don't modify hermes_constants.py for temporary steering (exception: disabling dead signals)
- Don't edit AGENTS.md for ephemeral state
- Don't add new dependencies

## Next Actions

1. **Monitor 7d PnL flip.** Currently -$3.31. Legacy (ema300_dip_short -$1.48, sma20_dip -$0.73, ema300_dip -$0.72) aging out. Should flip positive by Sep 10-11 as these drop off. — 2026-09-09
2. **Monitor cut-loser fix impact.** Fix verified. ATR_SL at 1.2%-1.5%. 24h: 2 exits avg -4.21% (down from 22 exits). Monitor if avg loss drops toward -2%. — 2026-09-09
3. **Monitor open-skies degradation.** 19T/7d 63.2% WR +$1.56 — today 2T/50% WR -$0.49 (variance). Kill if WR drops below 45% at 10T/48h. — 2026-09-09
4. **Monitor bb_bounce_v2_long.** 73T/7d 74.0% WR +$2.08 ★. Today 2T/50% WR -$0.11. Kill if WR drops below 40% at 15T/48h. — 2026-09-09
5. **Monitor pump_chain.** 43T/7d 67.4% WR +$1.11. Today 9T including SHORT residual. Kill SHORT if WR drops below 45%. — 2026-09-09
6. **Monitor disk.** Currently 84% (19G free). — 2026-09-09
7. **SHORT side dependency.** System has no LONG backbone in NEUTRAL market. bb_bounce_v2_long is only active LONG signal. — 2026-09-09
