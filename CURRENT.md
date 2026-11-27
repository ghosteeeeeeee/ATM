# Current State — brain_auditor #308 2026-11-27 13:00 UTC
**Last Updated: 2026-11-27 13:00 UTC**
**Updated by: brain_auditor #308. Prior: #307 2026-11-27 04:52 UTC (preserved in git history).**

## HEADLINE — LONG z∈[1,2.0) is the only completely ungated entry band left, and it loses in every window: 30d 80T 42.5% net -$2.52 (fisher p=0.033) vs non-band LONG 56.1%, 14d -$0.95 (p=0.051), 7d -$0.74 (p=0.087) all same sign, reach+0.40% only 46.3%, 31/46 loser exits = atr_sl_hit+hard_max_loss (chop signature), 6 signals, survives excluding EXTREME, kills only 15.8% of LONG winners. CHASE gates z>2.5, SIGNAL_FILTER_Z_MIN gates z<-1.5 → [1,2) open. No prior art. Shipped as disposition `eval-long-z-midband-1-2` (due 12-04, default NO-SHIP, needs independent verification + CEO). 0 trading-constant changes. Wrong-side refuted 159th.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d (NET-of-fee) | 14T 71.4% gross +0.08 fees 0.17 **net -0.09** / 125T 56.0% gross -0.42 fees 1.71 **net -2.13** / 236T 53.0% gross +0.12 fees 3.28 **net -3.16** / 631T 53.4% gross **-3.73** fees **7.78** **net -11.51** (fees = **209% of gross**, 407% at 7d; avg gross/trade -0.0059 < avg fee/trade 0.0123) |
| open trades | **3 ALL LONG** — BTC #17133 continuum-osc+ LONG 7.6h (opened 04:33Z, COUNTER to btc_15m SHORT_BIAS) · GRASS #17136 warrior-sr-confirm+ +1.14% · RUNE #17137 atr-trend+ -0.39% |
| armed vs never | 7d **67T 89.6% +3.33** vs 58T 17.2% **-3.75** · 14d **106T 91.5% +6.13** vs 130T 21.5% **-6.01** |
| chop-bleed (canonical mfe<0.40) | **7d 76.4% dollar / 76.9% count, NULL 0 — BETWEEN the 92% escalate and 70% exit gates → no action** |
| 7d exit family | profit-monster-trail 51T 96.1% **+2.50** ‖ manual_sl_hit 13T 0% -1.97 ‖ atr_sl_hit 14T 0% -1.71 ‖ hard_max_loss 10T 0% -1.07 |
| kill screen | **0** — only 14d sub-50 n>=15 = ai-trader-pending 34T 35.3% net **+0.25** (payoff-positive, CEO) |
| size-reduce | **0.25x r2_tier** (file truth, 11-23) |

### 2. HEADLINE FINDING — LONG z-midband [1,2.0)
| bar | value | verdict |
|---|---|---|
| n>=20 | 80 (30d) | PASS |
| p<0.05 | 30d **0.03303** · 14d 0.05128 · 7d 0.08674 | PASS at 30d, marginal below — all three same sign |
| reach+0.40% | 46.3% (band) — lowest of all LONG z bands | chop signature |
| loser exits | atr_sl_hit 16 (-2.11) + hard_max_loss 15 (-1.68) = 31/46 | no-momentum class |
| signal spread | r2v2-long3 -0.88 · jup_yolo -0.87 · pump-chain+ -0.71 · warrior -0.27 · bb-squeeze -0.23 · rider +0.10 | not one signal |
| confounder (regime) | EXCL EXTREME: band 39T -1.19 46.2% vs baseline 234T -1.03 55.1% — still worse | survives |
| winners killed | 34/215 = **15.8%** (bar <20%) | PASS |
| not already shipped | only CHASE_ZSCORE_MAX=2.5 (>2.5) and SIGNAL_FILTER_Z_MIN=-1.5 exist | PASS |
| prior art | 4 session-brain queries → **none** (hits were RSI-midband / SHORT_CONTINUUM / chase-gap) | PASS |
| independent verification | PENDING (own-conclusions) | BLOCKING |
| CEO sign-off | REQUIRED (live entry block) | BLOCKING |

### 3. CONFIG — **0 trading-constant changes**
Session lock absent; `hermes_constants.py` not in git-status modified list = EMPTY diff; CEO_PROTECTED **16/16**; PREARM_LOCK_ENFORCE=False intact; size-reduce 0.25x. **0 ships, 0 trade actions.** Registry: +1 registered (164 entries).

### 4. AUTOPSY (168h, adverse-first, selfcheck rc=0)
n=52 = **12 never-adverse / 32 recovered / 8 NEVER traded back = 15.4% structural never-recover cohort** (14d calibration 17.5%) → **WRONG-SIDE REFUTED 159th** (#61 p=0.116, #84 t=-0.04). Dominant mode = giveback / never-armed chop.

### 5. JOIN + SHADOW
| Source | Fresh | Result |
|---|---|---|
| contrarian join | ✓ **12:31:15Z** (mandate) | overall flip **47.8%** n=3152 = coin-flip DO-NOT blanket; pc-\|BELOW 69.4% n=85; het rider p=1.45e-40 / pc- p=0.0084 = per-token only |
| shadow_trader --report | ✓ 12:35Z | pm_trail **+23,662** vs hard_max **-31,038** vs rr -11,477 = trail-or-nothing; every gate cohort avg-negative = gates earning keep |
| --analyze-hml | ✓ 12:57Z | CUT_LOSER_PNL sweep: every looser threshold costs MORE = current cut optimal on the proxy; worst n>=10: ema300-breakthrough+ 25T 16.0%, tl-bounce+2 39T 10.3% |
| chop_bleed_kpi | ✓ | 7d **76.4%**, between gates |
| floor / oscillator / wyckoff / rr | CLOSED / fossil / pending / orphaned | **3/6 usable** |

### 6. REJECTED-WITH-DATA / DRIFT / SIDE-FINDS
1. **REJECTED — source-level FEE-FLOOR admission**: ALL 8 sources with n>=20 have avg gross/trade < avg fee/trade (jup_yolo -0.0002 vs 0.0145 … btc-pump-rider +0.0122 vs 0.0145). The 8 = 471T gross -1.15 fee 6.08; blocking them kills **265 winners worth +$18.21**. No source-level fee floor exists — logged so it is never re-proposed.
2. **REJECTED — LONG RSI 70-75**: 30d 36T -0.71 41.7% **but 14d 11T +0.17** = sign-reverses at 14d.
3. **MONITOR — ai-trader-pending SHORT by entry RSI**: <20 6T +0.18 / **20-30 18T -1.70 22.2%** / 30-40 11T +0.44 / >=40 5T +1.32 — non-monotone, n=18 < 20.
4. **MED — FEE DRAG IS THE WHOLE NET BLEED** (209% of 30d gross) → maker disposition due **11-28**, CEO SHORT-only scope owed.
5. **MED — PREARM_LOCK_ENFORCE = False since 11-22** — never-armed 14d **-6.01** has no live remedy; day-7 read due 11-28.
6. **LOW — `data/gate_shadow.db` is a 0-byte ORPHAN** created 11-20; every real consumer resolves `brain/gate_shadow.db` (28MB, 0.8h fresh). Source inventories globbing `data/` report an empty source.
7. **LOW-INFO — SHORT RSI floor is NOT leaking**: non-ai SHORT entry_rsi<45 30d = 64T, all inside the documented [35,45) bear-structure exemption (35-40 27T -0.57 / 40-45 37T +0.93), rows below 35 = **0**.
8. **INFO — HIGH still the only negative 7d regime** (41T -1.05 51.2%) — same sign as pre-registered; owned by the 11-29 joint read.

### 7. AMPLIFY (light; formal weekly due Mon 11-30)
**0 NEW, saying why with the #307 FEE-ADMISSION BAR ($0.0185/trade = 1.5x 30d avg fee).** All 8 n>=10 net>0 30d cells screened: only 2 clear — ai-trader-pending|NORMAL|SHORT (+0.037, ALREADY ADJUDICATED no-ship AND 100% single-token BTC) and btc-pump-rider+|EXTREME|LONG (+0.033, ALREADY CLAIMED 11-30); other six +0.001..+0.008 below bar; early n5-9 cell already in WINNER_CELLS_VALIDATED. Flip-KPI **0** this week (stated) — grind-exempt is the week's candidate.

### 8. CREATIVE ×4
1. **LONG z-midband kill [1,2.0)** — SHIPPED as disposition `eval-long-z-midband-1-2` (§2).
2. **Source fee-floor** — REJECTED-with-data (above).
3. **ai-trader oversold-short band scoped to 20-30** — MONITOR (n=18).
4. **Orphan `data/gate_shadow.db` cleanup** — telemetry hygiene.

### 9. LAST-RUN VERIFY (#307) — ALL PASS
grind-exempt disposition present/open/12-11 with blocking-requirements intact · chop_bleed_kpi RAN 76.4% · contrarian mandate HELD 12:31:15Z · recovery selfcheck rc=0 · session lock ABSENT · constants EMPTY · CEO_PROTECTED 16/16 · size_mult stamped · HIGH 0.50 + EXTREME 0.85 intact · 0 Tracebacks.

### 10. SESSION BRAIN
11 run-derived queries / 37 hits / **9 cited**. Prior art: [calwndar 2026-10-31] fee + SHORT_RSI_FLOOR working, [Build New Linear Regression Signal 2026-10-29] maker lever unimplemented, [yolo dash 2026-11-02] no-arm fee churn. **NO prior art for the z-midband.**

### 11. READINESS (2026-11-27 12:10Z watchdog)
**3 open ALL LONG — BTC #17133 (7.6h, counter to btc_15m at open → WATCH ONLY, do not double-manage) · GRASS #17136 · RUNE #17137.** 2 steers, both auto_executable=false: **steer-001** GRASS+RUNE cluster within 0min · **steer-002** 3/3 long = one BTC dump hits all three. Regime: btc_15m **SHORT_BIAS** vs btc_4h **LONG_BIAS** CONFLICT · continuum AT · vol NORMAL · velocity SLOW · accel NEGATIVE · wyckoff ACCUMULATION · market CALM · trend UP → **NO fresh discretionary directional entries while the two BTC timeframes disagree; trail-family first (51T 96.1% +2.50/7d is the only paying exit family); size 0.25x (inert at the $11 floor).**

### QUEUE
**11-28** six due dispositions (maker SHORT-only CEO ruling · jup-walk · cell-tilt · r2v2-clonehunt · longbypass reconcile · prearm-day7) → **11-29 JOINT READ: regime-conf-high-first-read + high-long-displacement-read + tape-at + be-arm-peak (at most ONE HIGH instrument)** → **11-30** rider/atp/hl-copy cells + **FORMAL WEEKLY AMPLIFY** → 12-01 win-side + stop-family → **12-04 z-midband first read (NEW)** → 12-05 reband limb-v + rr-engine-short-relax-remeasure → 12-06 structure-only impact read → 12-11 grind-exempt.

**CEO owed:** z-midband kill (12-04; independent verification first) · maker SHORT-only scope (11-28) · manual_sl_hit 7d 13T 0% **-1.97** = 100% ai-trader (8th run) · PREARM_LOCK_ENFORCE still OFF (14d never-armed **-6.01**).
