# Current State — brain_auditor #231 2026-11-07 04:52 UTC
**Last Updated: 2026-11-07 04:52 UTC**
**Updated by: brain_auditor #231. Prior: #230 2026-11-06 20:55 UTC (preserved in git history).**

## HEADLINE — DailyFillCap is a LEAKY LIMITER, not a stop, and its opportunity cost was unmeasurable until this run. Cap engaged 00:12:50Z (15 opens/24h, fee-net '-0.76'); first braked candidate = ENS LONG grind-accum+ conf 49.5 @03:03:42Z. The AND also releases on n<15, so it self-frees at 05:02:47Z while fee-net is STILL red, then admits ~1 open per aging slot until green. Ship: SKIP line now carries `[blocked TOKEN DIR source]` (log-only, zero behavior). 5 hypotheses REJECTED-WITH-DATA; 1 new creative (PRE-ARM BREAKEVEN LOCK, ceiling +$2.69..$3.91/14d) pre-registered NO CODE.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| **DailyFillCap opportunity cost (HEADLINE)** | SKIP line carried no candidate identity -> brake cost unmeasurable. **SHIPPED log context** (decider_run.py `_daily_fill_cap_block(token, direction, source)`, both fill paths, return byte-identical, py_compile PASS, 2 callers, no exact-match parser). **Leaky-limiter mechanic measured:** release fires on `n<15` too — 15th-oldest open 2026-11-06 05:02:47Z ages out **2026-11-07 05:02:47Z with fee-net still '-0.76'**; afterwards admits ~1/open per aging slot (05:02/06:54/07:48…). Matches CEO metric, wording + disposition criterion imprecise (LOW). |
| **EXTREME regime gate — REJECTED** | 30d 277T 37.9% '-2.50' Fisher p=0.0007 BUT split-half FAILS OOS: d1-15 172T 28.5% **arm 14.0%** vs d16-30 105T 53.3% **arm 59.0%** — exit stack (HML_VOL_ATR_MULT, stop-tighten 0.75, ATR_SL) inverted it. |
| **Wider SL — REJECTED** | `shadow_trader --report-wider` own bar: wider WR 37.9% vs required 55.0%, total PnL '-410.5pp'. |
| **pump-chain- SHORT kill — STALE** | 30d 55T 23.6% '-0.22' arm 23.6%, but **52/55 in d1-15**; d16-30 = 3T '+0.22'. Already quiet, monitor. |
| **TREND-ALIGN "backwards" — CONFOUNDER CAUGHT** | LONG x entry_regime_4h=SHORT_BIAS 110T 58.2% arm 60.0% vs other 164T 49.4% arm 45.7%. **Within jup LONG (the 54/110 driver): 61.1% vs 61.7% — effect vanishes.** Aggregate gap = signal mix. Arm-rate Fisher p=0.026 survives, WR does not. NO SHIP, logged so it is never re-proposed. |
| **LONG-RSI-BLOCK magnitude guard — REFUTED** | Hypothesis: RSI 0.0 on flat feeds (ENS 03:04 blocked on 4.63→4.61 = '-0.43%' drift, bounced 5 min later; TURBO 6 cycles) = misfire. **7d census, 131,264 RSI<20 events / 179 tokens: net<=-1.0% fwd60 '+0.060%' 51.7% pos | -1.0..-0.3% '+0.023%' | net>-0.3% (the flat-drift class) fwd60 '-0.042%' 43.2% pos = WORST.** The intuitive fix unblocks the worst cohort. Root cause real, NO SHIP. |
| **Giveback ledger (units-correct, ceiling)** | 14d 399T peaked **+27.85** finished **-2.62** = **$30.47 unharvested**; 30d peaked +64.24 / finished -7.21 = $71.45. By exit 30d: atr_sl_hit giveback 19.90 (146T) + hard_max_loss 17.75 (130T) = 37.65 of it; profit-monster-trail only 9.37/233T (avg 0.040) = efficient. Winners gave back 18.15 of 46.52 peak (39%). |
| **#230/#229 verify** | dedup warnings present, git diff EMPTY (= committed); live repro **173 [SHADOW] TAT lines for ONE trade 16808**, consumers dedup by trade_id so published counts honest, structural fix NOT shipped (log-honesty only) · combo pin HELD (bb+ 1.3 / warrior 1.6) · #230 AMPLIFY entry present (11-14, NO-SHIP) · gate_shadow_health **selfcheck PASS 34 gates** · recovery_replay **ASSERT PASS**. |

### 2. NUMBERS (fresh PG)
- 24h **15T 53.3% '-0.46' RED** | 7d **208T 52.9% '-1.97' RED** | 14d 399T 55.1% '-2.61' | 30d 780T 46.2% '-7.21'
- 7d by regime: EXTREME 20T 30.0% '-0.84' · HIGH 63T 54.0% '-0.86' · NORMAL 109T 54.1% '-0.45' · FLAT 16T 68.8% '+0.18'
- 7d exits: **profit-monster-trail 61T 100% '+4.10'** + mfe_exit 36T 83.3% '+1.67' || **hard_max_loss 37T 0% '-4.68' + atr_sl_hit 35T 0% '-3.70'** + trail_arm_timeout 24T 45.8% '-0.23'
- 14d exits: atr_sl_hit 57T 0% '-6.31' · hard_max_loss 43T 0% '-5.63' · cut-loser 13T 0% '-1.92' || trail-family (PM-trail+mfe+ugb+rr+trail_sl+atr_trail) **234T 83.3% '+10.72'** vs other **165T 15.2% '-13.33'**
- 14d never-armed 183T: **MFE<0.30 = 132T '-13.42' 3.8% WR (86% of bleed)** · MFE>=0.30 = 51T '-2.13' 37.3% WR · MFE>=0.25 cohort 64T
- 15d direction x entry_regime_4h (feature_recorder coverage 364/780 30d, all in last 15d): LONG/SHORT_BIAS 110T 58.2% arm 60.0% · LONG/NEUTRAL 114T 49.1% · LONG/LONG_BIAS 50T 50.0%
- 30d winner cells n>=10 unchanged: pc+ EXTREME L 73T +1.44 · bb+ NORMAL L 44T +0.76 · vb- HIGH S 19T +0.42 · jup HIGH S 15T +0.40 · pc-,pc-v6- EXTREME S 10T +0.30 · pc- NORMAL L 29T +0.24

### 3. SHADOW (2/6 raw answerable + shadow_trader + gate_shadow)
- contrarian join **RE-RAN 04:30Z (mandate)**: overall flip **43.1% (W620/L820/SHALLOW2)**; pc- uniform chi2 p=0.375; btc-pump-rider+ **HETEROGENEOUS p=8.9e-25 → per-signal only**; by tape pc- BELOW 67.8% n=211 / AT 58.6% n=111 / ABOVE 64.3% n=28
- floor join 11-06 20:53Z: floor_only 1391 **49.3%** vs always_admit 210 43.8% **Fisher p=0.159 → COLLECT, bar 11-15**
- shadow_trader --report: 71,736 signals; **every gate blocks a <=53% would-win negative-EV cohort** (CONFLUENCE-EXPIRY 15,572 @47% '-0.13', CTX-GATE 2,419 @53% '-0.08') = gates earning their keep; exit A/B pm_trail '+10,854' vs hard_max '-12,458', rr_engine '-4,803', cut_loser '-2,183'; --sweep-arm (jup LONG) = No data
- oscillator FROZEN/archived · wyckoff source retired · rr ORPHANED

### 4. SIGNAL QUALITY — 0 kill candidates
- 14d n>=15 sub-50% WR **AND net<0 = ZERO rows.** Closest R:R-class: jup LONG 101T 61.4% '-1.04' / vb- SHORT 68T 63.2% '-0.52' — WR-positive net-negative, #228 pre-registered negative result stands (no entry filter).
- 24h losers n=7 all pass standing filters; RUNE r2v2-long3 RSI 75.0 sits exactly on the 75 LONG ceiling (n=7<20, monitor).

### 5. READINESS (04:52Z)
**0 open / 0 steers / portfolio good — FLAT 5.5h (last open 11-06 23:02Z).** Regime: **btc_15m SHORT_BIAS + btc_4h SHORT_BIAS (aligned) / continuum AT / vol LOW / velocity SLOW / accel FLAT / wyckoff ACCUMULATION / market_phase CALM / trend_quality STRONG_DOWN.** Two brakes named and measured: **DailyFillCap** (self-releases 05:02:47Z, then ~1 open/aging-slot while fee-net red) and the **gate stack** (last ~3h: CONTINUUM-BLOCK 107 · CONFLUENCE-GATE-BLOCK 63 · SHORT-NEUTRAL-BYPASS 346 · VOL-GATE-BYPASS 20 · DailyFillCap SKIP 24). → no fresh counter-trend entries, trail-family first, size **1.0x** (size-reduce file absent). Session lock **ABSENT**; CEO_PROTECTED **13/13**; hermes_constants **EMPTY git diff**; checkpoint_registry **0 pending (9/9 done)**; **0 Tracebacks** in pipeline.log.

**Queue:** **11-08 05:03Z DailyFillCap post-context re-read (count braked candidates, did any arm?)** → 11-09 zombie-purge → 11-10 five bars + uninert next-100 read + fade-ctx fee-net re-measure → 11-11 HML post-ship re-read + watch-contrarian → 11-13 linreg-fade / chop-exempt / vb- clonehunt / pc+ kill-review → 11-14 neutral-exempt read + mult-150 CEO label chase + atrtrail + stop-tighten → 11-15 floor/wyckoff → 11-17 jup eval batch.
**CEO:** mult-150 label pending since 11-04 · 34 combo-weight divergences need precedence review · LOSERS/BLUR uncommitted diff (not mine) · NET-KPI.
