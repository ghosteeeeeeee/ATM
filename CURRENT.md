# Current State — brain_auditor #313 2026-11-28 12:45 UTC
**Last Updated: 2026-11-28 12:45 UTC**
**Updated by: brain_auditor #313. Prior: #312 2026-11-28 09:05 UTC (audit_recommendations only — no kanban/CURRENT write, folded into #313). Prior CURRENT: #311 2026-11-28 00:55 UTC.**

## HEADLINE — THE TWO FEE-CLEARING CELLS READ OPPOSITE WAYS 2 DAYS BEFORE THEIR 11-30 READ
`amplify-atp-short-normal-cell`: weekly **+1.36 (22T) → -0.16 (4T) → -0.20 (1T)**, 7d leg **3T -0.22** → bar (ii) same-sign **FAILING today**; 30d 27T +1.00 (net-fee +0.66) is almost entirely the w11-09 cohort → **default HOLD/NO-SHIP at the 11-30 read unless 7d recovers** (evidence_note_313 appended). CEO RSI<35 dampen must be decided BEFORE that read (one variable, same signal).
`amplify-rider-extreme-long-cell`: 7d **11T 100% +0.62** / 14d 19T +0.79 / 30d 20T +0.66 net-fee +0.41, **15 tokens**, sibling EXTREME SHORT n=0, armed 15/20 → **all bars PASSING** (only risk: 7d window has 2 days to flip) (evidence_note_313 appended). Cell-add inert while mult=1.0; mult re-raise CEO-gated.

## SECOND — TWO CANDIDATE KILLS REJECTED-WITH-DATA
- **jup HIGH LONG dampen** (30d 52T gross -0.66 / net-fee -1.31, 14d/7d same-sign negative): REJECTED — split-half **sign flip** (older -0.75 vs newer +0.09), HYPE+SOL = 50/52 tokens, REGIME_CONF_HIGH_MULT **0.50 already live** since 11-25 (one-variable rule).
- **atr-trend+ LONG block** (30d 26T -0.29 same-sign, n=26): REJECTED — saves **+$0.29/30d << +$1.00 bar**, WR 54% = block kills ~12 winners for pennies. [mtf macd 2026-10-02: don't blanket disable].
- No new HIGH-side instrument before the **11-29 joint read** (one-instrument-max rule stands; high-long-displacement bar (c) fails → default NO-SHIP per #311).

## #312 VERIFY (LAST-RUN) — ALL 4 CHANGES WORKING + KANBAN GAP CLOSED
signal_compactor zscore **row[7] LIVE** (signals.json values -0.92/-0.50/-0.18 sane, macd separate) · decider_run:4230 INERT notice present, py_compile PASS · WINNER_CELLS_VALIDATED 2-cell drop present (**list now 1 member**: volume-buildup-|HIGH|SHORT) · 3 dispositions registered (zscore-long-gate-deadcode 12-05, eval-long-z restated, amplify-prearm-deadline-20m-shadow 12-12). **#312 never wrote kanban/CURRENT — folded here.**

## FINDINGS THIS RUN (net-of-fee, fee = 0.01247/trade)
| Window | n | WR | gross | net |
|---|---|---|---|---|
| 24h | 15 | 60.0% | -0.13 | **-0.32** |
| 7d | 124 | 55.6% | -1.18 | **-2.73** |
| 14d | 237 | 53.2% | -0.04 | **-3.00** |
| 30d | 628 | 53.0% | -3.69 | **-11.52** (fees 212% of gross) |

| Item | Result |
|---|---|
| open trades | **1 — HYPE SHORT jup_yolo_mirrored #17152** (11:48Z, HIGH, bracketed SL 63.05/TP 61.24, -0.53% lev). 0 steers. |
| arm split 7d | armed 56T **96.4% +3.05** vs never 68T **22.1% -4.23** |
| 7d exit family | profit-monster-trail 52T 96.2% **+2.39** ‖ atr_sl 17T 0% -2.13 ‖ manual_sl 10T 0% -1.67 ‖ hard_max 11T 0% -1.17 |
| chop-bleed KPI | **canonical RAN 12:40Z: 7d 79.5% $ / 81.5% cnt, NULL 0 — BETWEEN 70% and 92% gates → no action** |
| kill screen | **0** — only 14d sub-50 n≥15 = ai-trader-pending 31T 37.5% net **+0.31** (CEO-owned) |
| 7d payoff | avg win +0.0641 / avg loss -0.1037 → breakeven **61.8%** vs actual 55.6% = loss-size + fees |
| regime 7d | HIGH 44T **-1.28** only negative · EXTREME 48T +0.15 · NORMAL 32T -0.05 |
| 30d cells net-of-fee | only **2 of 8** gross-positive cells clear the fee bar: atp NORMAL SHORT +0.66 · rider EXTREME LONG +0.41 |

### AUTOPSY (adverse-first, selfcheck PASS)
- **48h n=10 = 3 never-adverse / 5 recovered / 2 NEVER (MERL stale_exit -0.13, RESOLV atr_sl -0.13) = 20.0% → WRONG-SIDE REFUTED 163rd consecutive run** (#61 p=0.116, #84 t=-0.04)
- **168h n=54 = 14/30/10 NEVER = 18.5%** = at the 17.5% baseline (not elevated)
- Dominant mode = **never-armed chop**: all 6 24h losers mfe 0.006–0.182, pm_armed_at empty.

### 3. CONFIG — **0 trading-constant changes**
Session lock absent; hermes_constants.py EMPTY git diff; WINNER_CELL_SIZE_MULT 1.0; PREARM_LOCK_ENFORCE False; REGIME_CONF_HIGH_MULT 0.50 (KEEP); size-reduce 0.25x r2_tier. **0 ships, 0 trade actions.** 2 evidence pre-reads appended (selfcheck PASS). **AMPLIFY: 0 NEW (weekly floor already met today ×2 — stated why in kanban).** 0 overdue; registry 1 pending (kill-line 12-03); 0 intraday checkpoints needed.

### 4. JOIN + SHADOW (4/6 usable)
| Source | Fresh | Result |
|---|---|---|
| contrarian join | ✓ **12:30:51Z** (mandate, no systemd producer) | overall flip **47.8%** n=3177 = coin-flip DO-NOT blanket · pc- 88W/61L 59.1% · rider 47.2% do-NOT · chi2 rider p=6.4e-41 / pc- p=0.0084 = **PER-TOKEN ONLY** |
| shadow_trader --report | ✓ 12:31Z (157,381) | **pm_trail +24,194** vs **hard_max −31,887** vs rr −11,813 = **TRAIL-OR-NOTHING**; every gate cohort avg-negative = gates earning keep; WRONG-SIDE table **EMPTY** |
| shadow_trader --analyze-hml | ✓ 12:34Z | worst n≥10: ema300-breakthrough+ 27T 14.8% · tl-bounce+2 40T 12.5% · rs-s48 23T 17.4% |
| floor join | ✓ 12:33Z | 30d same-sign **FAIL** → NO-SHIP stays CLOSED |
| chop_bleed_kpi | ✓ 12:40Z | 7d **79.5%**, between gates |
| oscillator / wyckoff / rr | fossil / pending / orphaned | **4/6 usable** |

## READINESS (12:45Z)
**1 open — HOLD HYPE SHORT #17152** (bracketed, HIGH regime; aligned with continuum BELOW + 4h SHORT_BIAS). 0 actionable steers, portfolio good, db healthy.
Regime: btc_15m **LONG_BIAS** vs btc_4h **SHORT_BIAS** DISAGREE · continuum **BELOW** · vol **LOW** · velocity SLOW · accel NEGATIVE · volume LOW · market DECLINING · trend STRONG_UP (bias pair vs trend disagree = chop undertone) → **HOLD the short; no fresh counter-trend LONGs while 15m/4h disagree; trail-family first; size 0.25x inert at the $11 floor.**

**Queue: 11-29** high-long-displacement FORMAL joint read (bar (c) fails → default NO-SHIP) + tape-at-long + be-arm-peak day-7 — **ONE HIGH-side instrument max** → **11-30** rider/atp/hl-copy cells + FORMAL WEEKLY AMPLIFY → **12-01** win-capture / hotset / stale-block / struct-flip / 4 shadows / tat read → **12-02** contrarian + pcfade → **12-03** kill-line enforce → **12-05** longbypass walk + jup-short walk + rr-engine + zscore-deadcode → **12-12** maker ALO pilot + prearm-20m read.
**CEO owed: SHORT-only ALO pilot sign-off · atp RSI<35 half-size dampen (BEFORE the 11-30 atp read) · hotset trial-flip · cell reads 11-30 · manual_sl_hit 7d 10T -1.67 = 100% ai-trader.**
Artifacts: brain/audit_recommendations.json, brain/creative_improvements.json (+2), brain/changes_log.json (+2), data/shadow_disposition.json (2 evidence appends), data/contrarian_outcome_join.json, data/floor_admit_outcome_join.json.
