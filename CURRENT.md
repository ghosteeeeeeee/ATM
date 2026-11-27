# Current State — brain_auditor #306 2026-11-27 00:55 UTC
**Last Updated: 2026-11-27 00:55 UTC**
**Updated by: brain_auditor #306. Prior: #305 2026-11-26 17:10 UTC (preserved in git history).**

## HEADLINE — Due-11-27 other-gate split run by me when the owner stayed silent: RR-ENGINE SHORT (+$9.92, p=0.032) and CONFLUENCE-GATE-BLOCK SHORT (+$9.56, p=0.021) pass all four written bars at 14d and beat the population base-rate 3.6-3.9x — BOTH FAIL the 7d OOS window, so no relax ships and every KEEP ruling now rests on measurement. 0 trading-constant changes. Wrong-side refuted 157th.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d (NET-of-fee) | 22T 68.2% gross -0.15 net **-0.40** / 130T 55.4% net -2.10 / 239T 52.7% net -3.20 / 643T 52.7% gross -4.67 fees 7.84 **net -12.51** (fees = 168% of gross, cov 87%) |
| open trades | **0** — flat, 0 steers, portfolio good |
| armed vs never 14d | **134T 83.6% +8.09** vs **105T 13.3% -7.90** — arm-gap owns the bleed |
| chop-bleed (canonical mfe<0.40) | **7d 76.6% dollar / 77.8% count — below 92 gate** |
| 7d payoff | avg win +0.0694 vs avg loss -0.0981 = 1.41x → breakeven WR **58.6%** vs actual 55.4% |
| kill screen | **0** — only 14d sub-50 n>=15 = ai-trader-pending 38T 36.8% net **+0.39** (payoff-positive, CEO) |
| size-reduce | **0.25x r2_tier** (file truth, 11-23) |

### 2. OTHER-GATE PER-GATE SPLIT (deadline fired; owner signal_analyst silent)
Tool `brain/analysis/gate_relax_bar_2026-11-27.py` (--selfcheck PASS 6): PRIMARY fwd_4h (direction-adjusted — verified same-token/same-minute LONG = -x, SHORT = +x), token-day dedup, t-test, 7d-half sign, top-5 concentration, **new population base-rate limb** (14d pop mean +0.069% / 7d -0.076%).

| gate | 14d n | net | p | halves | base | 14d | 7d OOS | verdict |
|---|---|---|---|---|---|---|---|---|
| RR-ENGINE | 294 | +$9.92 | 0.0322 | +21.5/+53.5 SAME | 3.61x | PASS | p=0.066, **sign-flip** | **FAIL OOS** |
| CONFLUENCE-GATE-BLOCK | 263 | +$9.56 | 0.0213 | SAME | 3.88x | PASS | p=0.187 | **FAIL OOS** (+CEO-protected) |
| OVERSOLD-SHORT | 379 | -$2.72 | 0.606 | FLIP | 0.77x | FAIL | FAIL | KEEP (protective) |
| PUMP-CHAIN-SHORT-HIGH | 246 | +$2.74 | 0.486 | SAME | 1.19x | FAIL | FAIL | KEEP |
| rep (PENDING-APPROVE) | 1 | — | — | — | — | n<30 | n<30 | INSUFFICIENT |
| floor / regime / vol | 405/188/204 | +2.5/+1.9/+6.8 | 0.64/0.53/0.11 | mixed | ~1x | FAIL | FAIL | all KEEP stand |

Realized follow-on join (blocked → PG fill ≤60m) thin: RR-ENGINE n=81 WR 55.6% net +0.45, CONFLUENCE n=1 = the #284 dual-basis landmine. **DEFAULT FIRES: NO CHANGE.** New disposition `rr-engine-short-relax-remeasure` due **12-05** (two reads ≥3d apart + base-rate limb + realized n≥30 net>0 + conc <70%).

### 3. CONFIG — **0 trading-constant changes**
Session lock absent; `hermes_constants.py` EMPTY git diff; CEO_PROTECTED untouched; size-reduce = 0.25x. **0 ships (1 zero-behavior analysis tool), 0 trade actions.** Registry: 1 adjudicated + 1 registered (162 entries).

### 4. AUTOPSY (48h, adverse-first, selfcheck rc=0)
n=11 = **2 never-adverse / 8 recovered / 1 NEVER (#17094 HYPE SHORT jup atr_sl -0.10) → WRONG-SIDE REFUTED 157th** (#61 p=0.116, #84 t=-0.04). Dominant mode = giveback / never-armed chop class.

### 5. JOIN + SHADOW
| Source | Fresh | Result |
|---|---|---|
| contrarian join | ✓ **00:31Z** (mandate) | overall flip **49.3%** n=2998 = coin-flip DO-NOT blanket; pump-chain- 55.2% (below 58 bar); rider 47.4% do-NOT; het p=9.5e-42/0.0084 = per-token only; pc-\|BELOW 69.4% n=85 |
| shadow_trader --report | ✓ 00:33Z | **pm_trail +23,421** vs hard_max **-30,615** = trail-or-nothing; every gate cohort avg-negative = gates earning keep |
| --analyze-hml | ✓ 00:43Z | open-skies+ n=801 @17.1% WR, **0 live closes** = worst source correctly held out |
| chop_bleed_kpi | ✓ | 7d **76.6%** (below gate) |
| floor / oscillator / wyckoff / rr | 11-24 / fossil / pending / orphaned | **3/6 usable** |

### 6. DRIFT (2 MED)
1. **bb-squeeze+|NORMAL|LONG decayed** to 30d **+0.13** / 14d 0.00 / 7d -0.04 while **FIVE open amplify entries cite it** (was +0.45 on 11-14) → decay-kill pre-registered for the 12-05 read.
2. **PREARM_LOCK_ENFORCE = False since 11-22** (CEO structure-only OFF) — flip-KPI receipt "prearm live 11-20" is historical only; never-armed class (14d -7.90) has **no live remedy**. (MED, also: fee coverage 87% unchanged since #305.)

### 7. AMPLIFY (light; formal weekly due Mon 11-30)
**0 NEW — stated:** all 8 n≥10 net>0 30d cells claimed by an OPEN entry or adjudicated (ai-trader 11-21 NO-SHIP · rider-EXTREME 11-30 · jup-HIGH 11-28 · pc- contrarian · jup-NORMAL +0.14 · atr-trend- 12-01/12-10 · bb-squeeze 12-05 · jup-EXTREME +0.01); early n5-9 EMPTY; Flip-KPI **0** this week (stated).

### 8. CREATIVE ×3
1. **Base-rate limb on every gate-relax bar** — SHIPPED inside the tool (advisory, no gate reads it).
2. **Structure-only change-impact read pre-registered 12-06** — POST 5d never-armed 29T 20.7% -2.70 (-0.54/day, -0.093/trade) vs PRE 9d -0.58/day, -0.068/trade; share flat 41%/45%; arm% series-best 58.6% yet book flipped +1.34 → -1.30. n=29 = measurement, not a claim.
3. **bb-squeeze decay-kill** at the 12-05 reband read (close the notional/conf-tilt family if 14d ≤ 0).

### 9. LAST-RUN VERIFY (#305) — ALL PASS
reentry-study still done/REJECTED · maker disposition open 11-28 (CEO scope owed) · fee-drag HOLDS (168%) · chop_bleed_kpi RAN 76.6% · HIGH 0.50 post-ship 13 closes 69.2% -0.22 (n<15, read 11-29) · size_mult stamped on all 6 opens since 11-26 (1.0/1.8/2.0) · contrarian mandate HELD · 0 Tracebacks · session lock ABSENT · constants EMPTY · CEO_PROTECTED intact.

### 10. SESSION BRAIN
5 run-derived queries / 21 hits / **5 cited**. Prior art: [risk-budget decision 2026-10-21] confluence-block history + RR-engine EXIT prior art (not a SHORT relax); [calwndar 2026-10-31] fwd-basis switch = PRIMARY; [Build New Linear Regression Signal 2026-10-29] gate inventory + the fee lever (28d old, unwired).

### 11. READINESS (2026-11-27 00:55 UTC)
**0 open / 0 steers / portfolio good.** Regime: btc_15m **SHORT_BIAS** vs btc_4h **LONG_BIAS** CONFLICT · continuum AT · vol LOW · velocity SLOW · accel NEGATIVE · trend STRONG_UP · wyckoff ACCUMULATION · market CALM → **NO fresh discretionary directional entries while the two BTC timeframes disagree; trail-family first (profit-monster-trail 52T 96.2% +2.66/7d is the only paying exit family); no entries while the armed-rate does all the work; size 0.25x (inert at the $11 floor — real brakes are the entry gates and, when engaged, DailyFillCap).**

### QUEUE
**11-28** six due entries (maker SHORT-only CEO ruling · jup-walk · cell-tilt · r2v2-clonehunt · longbypass reconcile · prearm-day7) → **11-29 JOINT READ: regime-conf-high-first-read + high-long-displacement-read (at most ONE HIGH instrument; HIGH-LONG bars still holding 7d -1.16 / 14d -1.35 / 30d -3.68)** → **11-30** rider/atp/hl-copy cells + **FORMAL WEEKLY AMPLIFY** → 12-01 win-side + stop-family → **12-05** reband limb-v + **rr-engine-short-relax-remeasure (NEW)** → 12-06 structure-only impact read + be-arm day-14.

**CEO owed:** maker SHORT-only scope (11-28) · manual_sl_hit 14d 23T -3.05 = 100% ai-trader (6th run) · structure-only impact-read ACK.
