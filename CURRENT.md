# Current State — brain_auditor #314 2026-11-28 16:50 UTC
**Last Updated: 2026-11-28 16:50 UTC**
**Updated by: brain_auditor #314. Prior: #313 2026-11-28 12:45 UTC. Prior CURRENT: #311 2026-11-28 00:55 UTC.**

## HEADLINE — 11-29 DEADLINE QUEUE CLEARED BY EARLY JOINT DISPOSAL
Three dispositions shared the 11-29 deadline. Partner `regime-conf-high-first-read` already fired DONE #311 (KEEP 0.50, post-ship n=20 net -0.39). Adjudicated the dependents same-run:
- **`high-long-displacement-read` → NO-SHIP.** Bar (c) Fisher FAILS independent re-measure: 7d p=0.1682 / 14d p=0.0817 / 30d p=0.1957 (reproduces #311 0.177/0.079/0.108). Bars a/b/d/f PASS but threshold requires ALL six. Block does not ship; mult stays 0.50 (one-HIGH-instrument rule).
- **`tape-at-long-remeasure-1129` → CLOSED NOISE.** n bar fails: stamped LONG-AT 14d n=24 / 30d n=128, both <150. net<0 holds (-0.68/-3.55) but else-branch = close as noise.
- **`be-arm-peak-structural-read` → day-7 MONITOR, deadline → 2026-12-06 (day-14).** Post-ship gap cohort n=8 < 20 bar. No revert of CEO 11-22 BE_ARM_PEAK_PCT 0.025 on n=8.

**Zero dispositions due 11-29.** Next formal reads: 11-30 (atp + rider cells + weekly AMPLIFY).

## SECOND — AMPLIFY WEEKLY: 0 NEW (floor already met this week)
#311 registered `amplify-maker-entry-short-only-pilot` 00:55Z today. Only 2 of 8 gross-positive 30d cells clear net-of-fee, both already in-flight:
- `amplify-atp-short-normal-cell` (11-30): 7d 3T net **-0.26 FAIL** same-sign / 14d +0.29 / 30d +0.66. Weekly +1.09 → -0.21 → -0.21. **Default HOLD/NO-SHIP at 11-30 unless 7d recovers.** CEO RSI<35 dampen unratified (one-variable sequencing). evidence_note_314 appended.
- `amplify-rider-extreme-long-cell` (11-30): 7d 7T 100% +0.22 / 14d 19T 78.9% +0.55 / 30d 20T 75% +0.41 net — **all bars PASSING**; cell-add inert while `WINNER_CELL_SIZE_MULT=1.0`; mult re-raise CEO-gated. evidence_note_314 appended.

Why-not for new cells: no fresh unowned cell cleared n>=10 net>0. Flip-KPI already met this week.

## #312/#313 VERIFY — ALL PASS
signal_compactor zscore row[7] present in signals.json · decider_run:4230 INERT notice present · WINNER_CELLS_VALIDATED = `{volume-buildup-|HIGH|SHORT}` mult 1.0 · evidence_note_313 present on both cells · hermes_constants.py EMPTY git diff · CEO_PROTECTED untouched · size-reduce 0.25x · 0 Tracebacks today · recovery_replay selfcheck PASS · shadow_disposition selfcheck PASS.

## FINDINGS THIS RUN (net-of-fee, fee = 0.01247/trade)
| Window | n | WR | gross | net | breakeven WR |
|---|---|---|---|---|---|
| 24h | 15 | 60.0% | -0.10 | **-0.29** | 63.6% |
| 7d | 112 | 55.4% | -1.43 | **-2.83** | 63.0% |
| 14d | 235 | 53.2% | -0.58 | **-3.51** | 54.7% |
| 30d | 620 | 52.7% | -3.66 | **-11.39** | 56.4% |

| Item | Result |
|---|---|
| open trades | **0 — FLAT = CORRECT.** 0 steers, portfolio good, db healthy. |
| arm split 7d | ARMED 63T **87.3% +1.98** vs NEVER 49T **14.3% -4.81** |
| 7d exit family | profit-monster-trail +0.24 dominant · atr_sl_hit -0.53 · stale -0.14 · hard_max -0.11 |
| chop-bleed KPI | **canonical 16:35Z: 7d 82.0% $ / 85.7% cnt, NULL 0 — BETWEEN 70% and 92% gates → no action** |
| kill screen 14d | **1** sub-50 n>=15: ai-trader-pending SHORT 16T 31.3% net -0.43 = OWNED (CEO/atp cell), not re-proposed. ai-trader-auto 14d 4T 0% -0.95 all manual_sl_hit = n<20 CEO domain. |
| 7d payoff | aw +0.0619 / al -0.1054 → breakeven **63.0%** vs actual 55.4% = loss-size + fees |
| 7d losers never-armed | atr-trend+ **87.5%** · atr-trend- **85.7%** · jup/pending/r2v2/pc+ **100%** — chop entries, stall stack owns |
| 30d cells net>0 n>=10 | only **2**: atp NORMAL SHORT +0.66 (HOLD) · rider EXTREME LONG +0.41 (PASSING) |

### AUTOPSY (adverse-first, selfcheck PASS)
- **48h n=10 = 3 never-adverse / 5 recovered / 2 NEVER (MERL stale_exit, RESOLV atr_sl) = 20.0% → WRONG-SIDE REFUTED** (#61 p=0.116, #84 t=-0.04)
- **168h n=49 = 13/27/9 NEVER = 18.4%** = at 17.5% baseline (not elevated)
- Dominant mode = **never-armed chop** — 24h losers mfe 0.006–0.182, trail never armed

### 3. CONFIG — **0 trading-constant changes**
Session lock absent; hermes_constants.py EMPTY git diff; WINNER_CELL_SIZE_MULT 1.0; REGIME_CONF_HIGH_MULT 0.50 KEEP (fresh post-ship HIGH 24T WR 66.7% **net -0.70** — net<0 rule holds); size-reduce 0.25x. **0 ships, 0 trade actions.** 3 dispositions + 2 evidence notes (data only). **AMPLIFY: 0 NEW (weekly floor already met #311 — stated in kanban).** 0 overdue after today's clears; registry 1 pending (kill-line 12-03); 0 intraday checkpoints needed.

### 4. JOIN + SHADOW (4/6 usable)
| Source | Fresh | Result |
|---|---|---|
| contrarian join | ✓ **16:30:31Z** (mandate) | overall flip **47.8%** n=3180 = coin-flip DO-NOT blanket · pc- 91W/61L 59.8% per-token only · rider 47.2% do-NOT · chi2 heterogeneous both |
| floor join | ✓ **16:33:43Z** | fisher_p **0.7505** (floor 49.5% vs always 48.8%) = no edge; prior disposition already NO-SHIP CLOSED #291 — route stays CLOSED |
| shadow_trader --report | ✓ 16:31Z (157,847) | **pm_trail +24,274** vs **hard_max −31,979** vs rr −11,853 = **TRAIL-OR-NOTHING**; every gate cohort avg-negative = gates earning keep; WRONG-SIDE table **EMPTY** |
| shadow_trader --analyze-hml | ✓ 16:31Z | worst n>=10 all shadow-only (ema300-breakthrough+ 14.8% WR etc) — not live kill targets |
| chop_bleed_kpi | ✓ 16:35Z | 7d **82.0%**, between gates |
| oscillator / wyckoff / rr | fossil / pending / orphaned | **4/6 usable** |

## READINESS (16:50Z)
**0 open — FLAT = CORRECT.** 0 actionable steers, portfolio good, db healthy.
Regime: btc_15m **SHORT_BIAS** agrees btc_4h **SHORT_BIAS** · continuum **ABOVE** · vol **LOW** · velocity SLOW · accel FLAT · volume LOW · market DECLINING · trend **STRONG_UP** (bias pair vs trend disagree = chop undertone) → **no fresh counter-trend LONGs; trail-family first; size 0.25x inert at the $11 floor. Auto-trader CHOP/BRACKET.**

**Queue: 11-30** atp+rider FORMAL cell reads (atp default HOLD/NO-SHIP; rider bars passing but inert) + hl-copy-plus-shadow + long-rsi-floor30-shadow + **FORMAL WEEKLY AMPLIFY** → **12-01** win-capture / hotset / stale-block / struct-flip / 4 shadows / tat read → **12-02** contrarian + pcfade → **12-03** kill-line enforce → **12-05** longbypass / jup-short walk / rr-engine / zscore-deadcode → **12-06** be-arm-peak day-14 → **12-12** maker ALO pilot + prearm-20m read.
**CEO owed: atp RSI<35 half-size dampen (BEFORE the 11-30 atp read) · SHORT-only ALO pilot sign-off · hotset trial-flip · WINNER_CELL mult re-raise gated · manual_sl_hit cluster = 100% ai-trader.**
Artifacts: brain/audit_recommendations.json, brain/creative_improvements.json (+2), brain/changes_log.json (+4), data/shadow_disposition.json (3 dispositions + 2 evidence notes), data/contrarian_outcome_join.json, data/floor_admit_outcome_join.json.
