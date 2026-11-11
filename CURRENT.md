# Current State — brain_auditor #248 2026-11-11 08:55 UTC
**Last Updated: 2026-11-11 08:55 UTC**
**Updated by: brain_auditor #248. Prior: #247 2026-11-11 04:51 UTC (preserved in git history).**

## HEADLINE — BLEED IS 100% PRE-ARM (stall 96T vs armgap 7T); CHOP-BLEED 2ND 92% BREACH; WINNER-CELL REVERT STILL OVERDUE

1. **EXIT-BLEED ROUTING SHIPPED** — new `brain/analysis/stall_decomposition.py` (--selfcheck PASS) splits the two biggest bleed exits by cohort: **14d atr_sl_hit+hard_max_loss 103T -11.95 = STALL(mfe<0.40 never armed) 96T -11.26 / ARMGAP 7T -0.69 / ARMED 0T**; 30d 216T -22.78 vs 37T -2.29. Mandate intact: every dollar of the #1/#2 bleed exits came from trades that never armed = ENTRY problem. **#247's amplify-ugb-bypass-armgap targets only 6.8% of that bleed** — its registry evidence now carries the pool-size ceiling (serviced this run) for the 11-18 adjudication.
2. **Chop-bleed share 7d = 92.1% → 2nd breach of the 92% push threshold** (14d 90.8% / 30d 88.1%). Response stack already registered and not yet due: mfe-cut + prearm-breakeven + stop-tighten x3 + tat-neverarmed (all 11-14), jup entry evals (11-17), structure-flip (11-21). 0.75x size stays VETOED (#196). No new gate invented without significance testing.
3. **AMPLIFY weekly: 0 new proposals, why-not documented** (not skipped) — all 5 n>=10 winner cells and every n>=5 early cell already have OPEN entries; stall pool covered by the 11-14 stack + 7 open jup evals; weekly offense already emitted by #247 4h ago. Flip-KPI: 0 conversions this week — ready-looking shadows carry explicit "not runnable before ~11-13" OOS guards.
4. **CEO ACTION STILL REQUIRED: `WINNER_CELL_SIZE_MULT` 1.25→1.0 revert ~32h OVERDUE** (deadline was 00:00Z 11-10). Constant still 1.25 at `hermes_constants.py:1174`. One-line CEO act or explicit extension.
5. **0 trading-constant changes** — session lock ABSENT, hermes_constants EMPTY git diff, CEO_PROTECTED intact, size-reduce absent = 1.0x, 0 Tracebacks today.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| bleed routing | stall 96T -11.26 vs armgap 7T -0.69 vs armed 0T (14d) → entry problem, full stop |
| armgap amplify pool | 6.8% of 14d bleed — evidence ceiling added to registry entry |
| chop-bleed 7d | **92.1% ≥92% = 2nd breach** — stack already registered, not yet due |
| deep-dive kill targets | 0 new; dead-signal check CLEAN (doji 0 opens since 10-16 kill, ai-trader+ 0 since 10-19) |
| AMPLIFY | 0 new — every ranked cell covered by an OPEN entry; why-not in kanban |
| winner-cell revert | STILL overdue ~32h → resurfaced to CEO |

### 2. NUMBERS (fresh PG 08:30Z)
- 24h **14T small-red** (ai-trader-pending SHORT -0.31 biggest) | 7d **90T 50.0% -1.76** | 14d **373T 53.9% -3.53** | 30d **745T 46.6% -9.18**
- armed 14d **177T 86.4% +8.39** vs unarmed 196T 24.5% **-11.92** | armed 7d **38T 89.5% +1.60** vs unarmed 52T 21.2% **-3.36**
- 14d exits: profit-monster-trail **133T 97.7% +7.43** | mfe_exit 39T 84.6% +1.84 | **atr_sl_hit 59T 0% -6.54 (#1)** | hard_max_loss 44T 0% -5.41 | cut-loser-CL-T1 11T 0% -1.63
- chop-bleed share: **7d 92.1%** (breach) | 14d 90.8% | 30d 88.1%
- stall feeders 14d: **jup_yolo_mirrored 43T -5.91 (52%)** · pc- 12T -0.73 · bb-squeeze+ 6T -0.70 · vb- 4T -0.45

### 3. SHADOW (3/5 usable)
- **contrarian join RE-RAN 08:30Z (mandate):** overall flip **44.6%** n=1653 · **pc- 64.6% (226W/124L n=350) STABLE** · rider 39.5% do-NOT (chi2 p=7e-30) · pc- token chi2 p=0.375 uniform
- floor join 11-10 20:36Z fresh → 11-15 same-sign read on track
- shadow_trader 08:31Z 87,038 signals: gates justified (CONFLUENCE-EXPIRY 16,411 @47% -0.13); exit A/B **pm_trail +13,122 vs hard_max -15,515** = trail-or-nothing
- oscillator FROZEN (archived) · wyckoff RETIRED · rr ORPHANED · gate_shadow usable only with token-day dedup

### 4. AUTOPSY + AMPLIFY
- **48h recovery_replay (adverse-first, selfcheck PASS): n=18 = 4 never-adverse / 10 recovered / 4 NEVER (FOGO -0.13, AR -0.11, DYDX -0.10, GMX -0.10 immaterial) → WRONG-SIDE REFUTED 76th consecutive.**
- **AMPLIFY: 0 NEW — why-not documented** (all cells covered; weekly already emitted #247). Service done: armgap entry evidence extended with pool sizes.
- Creative x1: stall-vs-armgap decomposition KPI (shipped, see audit_recommendations).

### 5. READINESS (2026-11-11 08:55 UTC)
**0 open — CORRECT.** Watchdog: no steers, portfolio_health good, btc_15m LONG_BIAS vs btc_4h SHORT_BIAS disagree, continuum ABOVE, trend_quality STRONG_UP, volatility LOW, velocity SLOW, market_phase RECOVERY — mixed tape = chop. Flat until a side sustains 15-30m with volume. Trail-family first; size 1.0x; no size added.

**Queue:** **CEO: winner-cell revert (OVERDUE ~32h)** + fade fee/size input → 11-12 storm x3 → 11-13 vb- clone-hunt + linreg fill + pc+ kill-review + chop-exempt → **11-14 EXIT-STACK DAY** (mfe-cut, prearm-breakeven, stop-tighten x3, jup-short-walk, tat-neverarmed) → 11-15 floor same-sign → 11-16 atr-trend cell → 11-17 jup batch + atrsl + 7 shadow bars → **11-18 contrarian fade read + atr-trend clone-hunt + UGB-bypass-armgap candle-walk (adjudicate against 6.8% pool ceiling)** → 11-19 jup HIGH OOS + ema300-underdeploy → 11-21 structure-flip + conf-tilt → 12-15 ugb-bypass-hole.
**CEO owed:** winner-cell revert · fade fee/size review · mult-150 sign-off (folds into revert) · unclog-waiver [35,45) re-measure · fade-ctx fee-net · jup Option-D monitor.
