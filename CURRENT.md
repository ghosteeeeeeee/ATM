# Current State — brain_auditor #311 2026-11-28 00:55 UTC
**Last Updated: 2026-11-28 00:55 UTC**
**Updated by: brain_auditor #311. Prior: #310 2026-11-27 20:55 UTC (preserved in git history).**

## HEADLINE — THE HIGH×LONG BLOCK'S OWN SIGNIFICANCE BAR DOES NOT REPRODUCE
`high-long-displacement-read` (formal read 11-29) records Fisher **p=0.0003 / <0.0001 / <0.0001** (7/14/30d) for HIGH-LONG vs non-HIGH-LONG. Re-run on the same cohorts: **p=0.177 / 0.079 / 0.108** — and no variant I can construct gets below 0.056 (vs-all-other 30d p=0.056; two-prop z 30d p=0.061). The entry's own SHIP BAR says *all six must hold on re-measure* → **default at the 11-29 joint read = NO-SHIP unless #304 discloses a method that reproduces.**
Other five bars still hold: n PASS (29/49/124) · net-neg same-sign PASS (-1.20/-1.58/-3.54) · weekly 5/5 PASS · fk14 21/127 = 16.5% PASS · 30d save +$3.54 PASS. Arm-side mechanism unchanged: 30d HIGH-LONG **armed 53T +2.85 (90.6%) vs never 71T −6.39 (11.3%)** = chop/arm-gap cell, not a direction cell.

## SECOND — HIGH-MULT PRE-REGISTERED READ FIRED EARLY → KEEP 0.50 (measured, not assumed)
Rule: *n>=15 post-ship closes OR deadline, whichever first*. Post-ship (open_time ≥ 2026-11-25 12:43Z) **n=20** → read executed: **net −0.39, WR 65.0%, armed 11/20**. Verdict limb: *RE-RAISE only if WR≥50 AND net>0; KEEP if WR<45 OR net<0* → **net<0 = KEEP 0.50**. One-variable rule honored (EXTREME untouched 0.85); `regime-conf-high-first-read` **CLOSED**. Note the WR/net split (65% WR, negative net) = loss-size again, same as the whole book.

## THIRD — 4 AMPLIFY ENTRIES AT THE 11-28 DEADLINE: 3 CLOSED, 1 EXTENDED (reason stated)
- **conf-tilt CLOSED NO-CHANGE** — its own precondition (all 4 cells clear bar (ii)) fails on 3: `bb-squeeze+|NORMAL|LONG` decayed to 30d gross −0.04 / net −0.34; `r2v2-long3|NORMAL|LONG` **30d n=0**; `pump-chain+|EXTREME|LONG` net −0.25. Reopen trigger documented (cells recover).
- **r2v2-clonehunt CLOSED** — coverage gap moot: the validated member no longer fires (30d n=0), nothing to mine against.
- **maker-entry full-book CLOSED NO-SHIP** — 3/7 bars fail on the directional proxy (fill 79.2%<80, fk 25.8%>20, halves sign-flip). Do not re-open full-book; the SHORT-only child is spun out (below).
- **amplify-jup-short-walk EXTENDED 12-05** — guard (OOS days) has been satisfied 15 days, but the walk producer is **orphaned**: no script in the repo writes `brain/analysis/jup_long_blocked_walk_result.json`. **3rd producer-less artifact class** (with `rr_shadow_audit_7d.json` and contrarian join's missing systemd timer). Rebuilding the exit-engine walk inline = unverifiable numbers, so it waits for its tool.

## AMPLIFY (weekly mandate) — 1 EMITTED: `amplify-maker-entry-short-only-pilot`
Shadow-first ALO/Limit on **SHORT entries only** (LONG-only cohort measured loser: fill 59.4%, fk 46%, mixed halves). SHORT scope 30d: **n=220, fill 93.6%, fee_save +1.705, missed_net +1.000, NET_cf +0.705/30d, fk 8.1%/13.5%, halves +0.019/+0.686 same-sign**.
Why this axis: 30d gross −3.68 + fees 7.81 = **net −11.49 (fees = 212% of gross)**; every type-(b) winner-cell mult caps at **+$0.085/30d** (#309 measured) → fee axis is 10–40x the headroom. Default **NO SHIP** until CEO signs the money path; retry-semantics bar (vi) must be *shown*, not assumed (10-min signal expiry at decider_run.py:6770 may already cover it).
Citations: [Build New Linear Regression Signal, 2026-10-29] "taker 0.09% RT … maker 0.03% RT would add +0.06% to every trade" (30d old, still unwired) · [calwndar, 2026-10-31] "headline net negative is gross of fees".
**Flip-KPI:** 1 conversion this week = #299 REGIME_CONF_HIGH_MULT 0.70→0.50 pre-registered limb firing (a revert — labeled as such); 0 new shadow→enforce this week.

## FOURTH — THE LONG-BYPASS TWO-BASE RECONCILE (owed since 11-21) IS BUILT AND RUN
`brain/analysis/longbypass_reconcile_2026-11-28.py --selfcheck PASS` (bug_hunter **SHIP**, 3 findings fixed) — SAME cohort, both bases, token-day dedup:
- **BASE A (fwd_4h PRIMARY)** 30d tok_n=52, avg **+1.1373%**, pos 71/96 = **74.0%** (7d: tok_n=26, +1.2547%, 66.7%)
- **BASE B (realized, first live LONG within 24h of the block → PG)** 30d n=15, **net +0.79, WR 66.7%** (7d n=7, +0.09) — corrected after bug_hunter round 1: overlapping token-day windows double-counted ZRO #16920 (+0.25); seen-set fix applied, **bug_hunter round 2 = SHIP**
→ **SAME-SIGN POSITIVE at both windows: the two bases do NOT reconcile to "gate saves money."** The 11-17 opposite read (n=53, WR 17.0%, net −10.09) does not reproduce on the first-trade/24h/strict-dedup convention.
Residual: realized n=15 and those are other-path fills, not the blocked setup itself → **step (2) candle-walk with the live exit engine still owed → EXTENDED 12-05, default NO CHANGE** (this is a CEO SHIP-LIVE "do not fight the trend" gate).

### 1. FINDINGS THIS RUN (net-of-fee, fee = 0.01247/trade measured)
| Window | n | WR | gross | net |
|---|---|---|---|---|
| 24h | 13 | 69.2% | +0.17 | **+0.01** |
| 7d | 128 | 57.0% | −0.41 | **−2.01** |
| 14d | 236 | 53.8% | +0.27 | **−2.67** |
| 30d | 626 | 53.0% | −3.68 | **−11.49** |

| Item | Result |
|---|---|
| open trades | **1 — LDO atr-trend− SHORT #17146** (00:50Z, HIGH, bracketed, −0.01). Watchdog steer SOL+YGG cluster **MOOT** (both closed: YGG −0.09 atr_sl / SOL +0.06 trail) |
| arm split 7d | armed 69T **89.6%→89.9% +3.35** vs unarmed 58T **17.2% −4.03** |
| 7d exit family | profit-monster-trail 53T 96.2% **+2.52** ‖ atr_sl 16T 0% −1.97 ‖ manual_sl 10T 0% −1.67 ‖ hard_max 10T 0% −1.07 ‖ prearm 9T 0% −0.13 |
| chop-bleed KPI | **7d 77.3% dollar / 78.8% count, NULL 0 — BETWEEN 70% and 92% gates → no action** (6th run in band) |
| kill screen | **0** — only 14d sub-50 n≥15 = ai-trader-pending 32T 37.5% net **+0.41** (payoff-positive, CEO-owned) |
| 7d RR | avg win +0.0675 / avg loss −0.0971 (1.44×) → breakeven **59.0%** vs actual 57.0% = loss-size + fees, entry avenue closed (#309) |
| regime 7d | EXTREME 54T +0.51 · NORMAL 31T +0.04 · **HIGH 42T −1.23 = only negative** (30d HIGH 206T −4.27) |
| 14d arm-rate floor | ai-trader-pending **21.9%**, pump-chain+ **23.1%** (n=13) — both net-negative |
| 30d cell screen | only **1 of 11** gross-positive cells (n≥5) is net-of-fee positive = ai-trader-pending\|NORMAL\|SHORT (owned/HOLD) |

### 2. AUTOPSY (adverse-first anchor, selfcheck PASS)
- **48h n=12 = 3 never-adverse / 8 recovered / 1 NEVER (17139 MERL atr-trend− stale_exit −0.13) → WRONG-SIDE REFUTED 162nd consecutive run** (#61 p=0.116, #84 t=−0.04)
- **168h n=52 = 13 / 30 / 9 NEVER = 17.3%** = at the 17.5% #85 baseline (**not elevated**)
- Dominant mode = **never-armed chop**, not direction. All 4 24h losers unarmed, mfe 0.000–0.182.

### 3. CONFIG — **0 trading-constant changes**
Session lock absent; `hermes_constants.py` EMPTY git diff; CEO_PROTECTED 16/16; PREARM_LOCK_ENFORCE **False** (line 2294); REGIME_CONF_HIGH_MULT **0.50** (KEEP); WINNER_CELL_SIZE_MULT 1.0; size-reduce 0.25x r2_tier. **0 ships, 0 trade actions.** 4 dispositions closed + 2 extended + 1 read-closed, **1 AMPLIFY emitted**. 0 overdue; registry 1 pending (kill-line 12-03); 0 intraday checkpoints needed.

### 4. JOIN + SHADOW (3/6 usable)
| Source | Fresh | Result |
|---|---|---|
| contrarian join | ✓ **00:31:17Z** (mandate, no systemd producer) | overall flip **47.8%** n=3176 = coin-flip DO-NOT blanket · pump-chain- 88W/60L **59.5%** (BELOW 70.8% n=89) · rider chi2 **p=6.4e-41** / pc- p=0.0084 = **PER-TOKEN ONLY** |
| shadow_trader --report | ✓ 00:31Z (155,911) | **pm_trail +23,948** vs **hard_max −31,584** vs rr −11,682 vs cut_loser −2,429 = **TRAIL-OR-NOTHING**; every gate cohort avg-negative = gates earning keep; WRONG-SIDE table **EMPTY** |
| shadow_trader --analyze-hml | ✓ 00:33Z | worst n≥10: ema300-breakthrough+ 25T 16.0% · tl-bounce+2 39T 10.3% · r2-trend-long6 27T 14.8% |
| chop_bleed_kpi | ✓ | 7d **77.3%**, between gates |
| oscillator / wyckoff / rr | fossil / pending / orphaned | **3/6 usable** |

**STORM:** none fired in window (auto_1hr window-min −0.44% at 20:55Z); waiver CLOSED KEEP-SHADOW 11-26.

## READINESS (00:55Z)
**1 open — HOLD LDO atr-trend− SHORT #17146** (opened 00:50Z, HIGH regime, bracketed, −0.01). 0 actionable steers (cluster steer moot), portfolio good, db healthy.
Regime: btc_15m **LONG_BIAS** vs btc_4h **NEUTRAL** · continuum **ABOVE** · vol **LOW** · zscore **STRONG_POS** · velocity SLOW · acceleration NEGATIVE · market_phase **DECLINING** · trend_quality **STRONG_UP** (bias pair vs trend disagree = chop undertone) → **HOLD the short (aligned SHORT in a HIGH-vol tape); no fresh counter-trend LONGs while 15m/4h disagree; trail-family first; size 0.25x is inert at the $11 floor (no DailyFillCap engaged = no real brake on today's tape).**

**Queue: 11-29** high-long-displacement FORMAL joint read (bar (c) fails — default NO-SHIP) + tape-at-long + be-arm-peak day-7 → **12-01** win-capture n40 / hotset trial-flip / stale-block / struct-flip / 4 shadows → **12-02** contrarian watch + pcfade → **12-03** kill-line enforce review → **12-05** longbypass step-2 walk + jup-short walk + rr-engine relax → **12-12** maker SHORT pilot read.
**CEO owed: SHORT-only ALO pilot sign-off (the one offense axis worth 10–40x any cell mult) · atp RSI<35 half-size dampen · hotset trial-flip · cell reads (atp/rider) 11-30.**
Artifacts: brain/audit_recommendations.json, brain/creative_improvements.json (+2), brain/changes_log.json (+3), data/shadow_disposition.json (40 open + 1 new), brain/analysis/longbypass_reconcile_2026-11-28.py, data/contrarian_outcome_join.json.
