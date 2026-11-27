# Current State — brain_auditor #307 2026-11-27 04:52 UTC
**Last Updated: 2026-11-27 04:52 UTC**
**Updated by: brain_auditor #307. Prior: #306 2026-11-27 00:55 UTC (preserved in git history).**

## HEADLINE — grind-breakout- SHORT is the best source in the whole shadow book (30d n=28, 96.4% WR, avg +1.325 vs population SHORT 55.6%/-0.085 = 11.0x) and 25 of its 29 fires were BLOCKED by RSI gates — blocked cohort won 25/25 (p=1.19e-07). AMPLIFY registered, default NO-SHIP, blocked on independent verification + CEO. 0 trading-constant changes. Wrong-side refuted 158th.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d (NET-of-fee) | 17T 58.8% gross -0.19 fees 0.20 **net -0.39** / 127T 55.1% net **-0.50** / 236T 52.1% net **-0.17** / 637T 52.9% gross **+3.62** fees **7.79** **net -4.17** (fees = **215%** of gross) |
| open trades | **1** — BTC #17133 continuum-osc+ LONG, bracketed, conf 49.5, mult 1.0 |
| armed vs never | 7d **75T 82.7% +3.38** vs 52T 15.4% **-3.88** · 14d **131T 83.2% +7.73** vs 105T 13.3% **-7.90** |
| chop-bleed (canonical mfe<0.40) | **7d 76.5% dollar / 77.4% count, NULL 0 — below 92 gate** |
| 7d payoff | avg win +0.0681 vs avg loss -0.0994 = 1.46x → breakeven WR **59.4%** vs actual 55.1% |
| kill screen | **0** — only 14d sub-50 n>=15 = ai-trader-pending 38T 36.8% net **+0.39** (payoff-positive, CEO) |
| size-reduce | **0.25x r2_tier** (file truth, 11-23) |

### 2. HEADLINE FINDING — grind-breakout- SHORT CONVERSION GAP
29 fires in 30d, **only 2 converted** (both won). Blocked: exec knife floor<35 = **14** (RSI 29.4–34.7, cell 14/14 p=3.05e-05) · hard floor<45 = 5 (37.2–44.5) · mid-band death band 45–55 = 3 · blocked@approval = 3 · BTC-CRASH = 1.

| bar | value | verdict |
|---|---|---|
| n>=20 | 28 | **PASS** |
| halves same-sign | 100% n=14 / 92.9% n=14 | **PASS** |
| population base-rate limb | 96.4% +1.325 vs POP SHORT 55.6% -0.085 (rsi<35: 42.4% -0.115) = **11.0x avg, +52.5pt WR** | **PASS** |
| binomial p vs 50% | blocked 25/25 **p=1.19e-07** | **PASS** |
| token concentration | top-5 75.9% BUT excl MET+JUP still **94.4% n=18** | **PASS w/ waiver** |
| realized join n>=30 | n_live=1 in 30d | **FAIL-IMPOSSIBLE → substitute: 14d staged re-read n>=35 all-positive** |
| single variable | exec knife floor only (hard-floor + death-band OUT of scope) | **PASS** |
| collision | signal-scoped, 0 effect on other 46 sources | **PASS** |

Gates are **correct at population level** — this signal is the exception, not the tape. Per-source floor precedent exists (`SHORT_RSI_HARD_FLOOR_JUP_YOLO = 35`, CEO Option D 2026-10-30). **No prior art found** for a grind-breakout-specific exemption. Shipped as disposition `amplify-grindbreakout-short-knife-exempt` (kind amplify, due **12-11**, **default NO-SHIP**) — **BLOCKED ON: (1) independent verification by own-conclusions (my counterfactual is not sufficient), (2) CEO sign-off (edits the exec-time last-line-of-defense gate added 2026-10-31 after CASHCAT)**.

### 3. CONFIG — **0 trading-constant changes**
Session lock absent; `hermes_constants.py` EMPTY git diff; CEO_PROTECTED **16/16**; size-reduce 0.25x. **0 ships, 0 trade actions.** Registry: +1 registered (163 entries).

### 4. AUTOPSY (48h, adverse-first, selfcheck rc=0 ASSERT PASS)
n=10 = **2 never-adverse / 8 recovered / 0 NEVER → WRONG-SIDE REFUTED 158th** (#61 p=0.116, #84 t=-0.04). Dominant mode = giveback / never-armed chop (all 7 24h losers mfe<0.40).

### 5. JOIN + SHADOW
| Source | Fresh | Result |
|---|---|---|
| contrarian join | ✓ **04:30:46Z** (mandate) | overall flip **48.6%** n=3073 = coin-flip DO-NOT blanket; pump-chain- 54.4% **below 58 bar**; rider 48.3% do-NOT; pc-\|BELOW 69.4% n=85; het rider p=1.2e-42 / pc- p=0.0084 = per-token only |
| shadow_trader --report | ✓ 04:33Z | every gate cohort **avg-negative** (CTX-GATE -0.12, SHORT-RSI-HARD-FLOOR -0.10, COMBO-STALE -0.16) = gates earning keep; exit A/B **pm_trail +23,489** vs hard_max **-30,753** vs rr -11,339 = trail-or-nothing |
| --analyze-hml | ✓ 04:33Z | open-skies+ n=805 @17.0% WR, **0 live closes** = worst source correctly held out |
| chop_bleed_kpi | ✓ 04:44Z | 7d **76.5%** (below gate) |
| floor / oscillator / wyckoff / rr | 11-24 closed / fossil / retired-10-31 / orphaned | **3/6 usable** |

### 6. DRIFT / SIDE-FINDS
1. **MED — FEE DRAG IS THE WHOLE NET BLEED**: 30d fees 7.79 = 215% of gross +3.62; avg gross/trade **+0.0057 < avg fee 0.0122**. Fee/maker disposition due **11-28** (CEO scope owed); fee lever prior art [Build New Linear Regression Signal 2026-10-29] unwired.
2. **MED — PREARM_LOCK_ENFORCE = False since 11-22** (CEO structure-only OFF): never-armed class (14d **-7.90**) has no live remedy; prearm-day7 read due 11-28.
3. **LOW — `signal_history.trade_id` DEAD (0/9731 in 7d)**: signal→trade attribution impossible from that column; nearly caused a false conversion-gap finding. Wire or drop.
4. **LOW-INFO — DailyFillCap VERIFIED HEALTHY**: 04:32:24 blocked BTC at 15/15, #17118 aged out at 04:32:50 → 14, BTC entered 04:33:12 as #15, HYPE blocked. PG 24h opens = 15 = cap count = **no enforcement bug**.
5. **MED — HIGH still the only negative regime at 7d** (43T 46.5% -1.26 vs EXTREME +0.67 / NORMAL +0.09) — same sign as pre-registered; owned by the 11-29 joint read.

### 7. AMPLIFY (light; formal weekly due Mon 11-30)
**1 NEW: `amplify-grindbreakout-short-knife-exempt`** (above). Stated why the other 8 n>=10 net>0 30d cells are NOT proposed: all claimed by an open disposition or adjudicated (ai-trader 11-21 NO-SHIP · rider-EXTREME 11-30 · jup-HIGH 11-28 · bb-squeeze 12-05 · pc- contrarian · jup-NORMAL +0.14 below materiality · atr-trend- 12-01/12-10 · jup-EXTREME +0.01 below materiality); early n5-9 net>+$0.25 **EMPTY**. Flip-KPI **0** this week (stated) — grind-exempt registered as the week's candidate, cannot convert without CEO.

### 8. CREATIVE ×3
1. **Source-scoped exec RSI knife-floor waiver for grind-breakout- SHORT** — SHIPPED as the disposition in §2.
2. **FEE-ADMISSION BAR** — pre-registered: no proposal ships unless gross/trade > 1.5x trailing-30d avg fee (same shape as #306's base-rate limb, applied to cost).
3. **Wire or drop `signal_history.trade_id`** — telemetry, removes a class of false findings.

### 9. LAST-RUN VERIFY (#306) — ALL PASS
gate_relax tool PRESENT (8.5KB 00:46) · rr-engine-short-relax-remeasure PRESENT due 12-05 · **all four 11-27 deadlines adjudicated** (pump-chain-weight-kill / linreg-fade-fill-funnel / pc-plus-weight-monitor / other-gate-short-withhold) · chop_bleed_kpi RAN 76.5% · recovery selfcheck rc=0 · contrarian mandate HELD · size_mult stamped on #17133 (1.0) · HIGH 0.50 + EXTREME 0.85 intact · 0 Tracebacks · session lock ABSENT · constants EMPTY · CEO_PROTECTED 16/16.

### 10. SESSION BRAIN
8 run-derived queries / 33 hits / **5 cited**. Prior art: [calwndar 2026-10-31] exec knife floor added for CASHCAT; [Build New Linear Regression Signal 2026-10-29] fee lever; [signal analyst 2026-10-24] + [risk-budget 2026-10-21] SHORT_RSI_FLOOR protective; [shadow mode 2026-10-17] shadow runner (grind-breakout is NOT disabled — gate problem, not flag problem).

### 11. READINESS (2026-11-27 04:52 UTC)
**1 open — BTC #17133 continuum-osc+ LONG @61481 / SL 60871.174 (-1.00%) / TP 62439.2475 (+1.56%), opened 04:33:12Z, conf 49.5, mult 1.0, bracketed.** It opened **00:13 after btc_15m flipped SHORT_BIAS = counter-trend vs the standing steer** → **WATCH ONLY, do not double-manage**. 0 steers / portfolio good / **DailyFillCap ENGAGED 15/15, 24h fee-net -0.59** (releases on roll-off or first green 24h).

Regime: btc_15m **SHORT_BIAS** vs btc_4h **LONG_BIAS** CONFLICT · continuum ABOVE · vol LOW · velocity SLOW · trend STRONG_DOWN · wyckoff UNKNOWN · market RECOVERY → **NO further fresh discretionary directional entries while the two BTC timeframes disagree; trail-family first (profit-monster-trail 50T 96.0% +2.43/7d is the only paying exit family); size 0.25x (inert at the $11 floor).**

### QUEUE
**11-28** six due dispositions (maker SHORT-only CEO ruling · jup-walk · cell-tilt · r2v2-clonehunt · longbypass reconcile · prearm-day7) + fee/maker → **11-29 JOINT READ: regime-conf-high-first-read + high-long-displacement-read (at most ONE HIGH instrument; HIGH-LONG bars 7d -1.16 / 14d -1.35 / 30d -3.68) + tape-at + be-arm-peak** → **11-30** rider/atp/hl-copy cells + **FORMAL WEEKLY AMPLIFY** → 12-01 win-side + stop-family → **12-05** reband limb-v + rr-engine-short-relax-remeasure → **12-11 grind-exempt read (NEW)** → 12-06 structure-only impact read.

**CEO owed:** grind-breakout knife-exempt (independent verification first) · manual_sl_hit 7d 13T 0% **-1.97** = 100% ai-trader (7th run) · maker SHORT-only scope (11-28) · PREARM_LOCK_ENFORCE still OFF (14d never-armed **-7.90**).
