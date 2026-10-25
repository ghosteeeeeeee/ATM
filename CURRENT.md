# Current State — brain_auditor #136 2026-10-25 ~09:45 UTC
**Last Updated: 2026-10-25 09:45 UTC**
**Updated by: brain_auditor #136. Prior: #135 08:51 (preserved in git history).**

## HEADLINE #136 — ESCALATION #17 MEASUREMENT COMPLETE: BYPASS-COHORT OOS PASSES EVERY BAR
Final unmeasured slice built via `trail_distance_oos_2026-10-25.py --cohort` (selfcheck PASS before + after):

**bypass cohort** = `PROFIT_MONSTER_BYPASS` signal AND non-PM exit, scoped non-EXTREME / no `volume-`,
arm = 1m close ≥ +0.40%, exit = first post-arm 1m close through peak−D, `pnl_usdt` both sides (fee-neutral):

| window | fills | NET | halves | t / p | fk_zeroed | bars |
|---|---|---|---|---|---|---|
| **30d** | 41 | **+2.368** | **+0.796 / +1.572** | 2.446 / **0.019** | 0.0% | **ALL 5 PASS** |
| **14d** | 29 | **+1.323** | +1.275 / +0.048 | 2.142 / **0.041** | 0.0% | **ALL 5 PASS** |
| 7d | 12 | +0.048 | +0.476 / −0.427 | 0.13 / 0.91 | 0.0% | n FAIL + halves FAIL (noise, reported) |

**D-sensitivity (30d):** 0.10 `+2.441` · **0.20 `+2.368`** · 0.30 `+2.247` · 0.50 `+1.590` — 0.10/0.20/0.30
**all pass every bar at 14d+30d** → not knife-edge. House primary stays **D=0.20** (pre-registered);
0.10 is info only — switching post-hoc to the best cell is the pattern trap.

**Controls (same code path):** PM-exit cohort 30d n=172 fills=137 **NET +0.276, p=0.66, halves FAIL**
→ **PM tiers already optimal, NO PM constant change (CEO-protected stays)** — note: 11 bypass-signal trades
exited on PM trail live inside this cohort (engine-based labels, 4.7%, disclosed) · PM-eligible×non-PM-exit
**n=98** fills=14 `+1.269` but **fk 50% + n FAIL → COLLECT** (post-bug_hunter NULL-signal correction;
pre-fix n=101 `+1.281` superseded).

→ **ESCALATION #17 (37th) IS NO LONGER ANALYSIS-BLOCKED.** CEO ask settles at: **universal post-arm
trail floor D=0.20 for PM-exempt engines** (pump-exit / rr_engine / hl_fill_monitor / volbo_atr — 41 fills/30d
with no floor at all), via the v6 exit-stack path. Ship vehicle per `automatic-implementation`: shadow line
first, one constant, PM untouched, revert = drop the flag.

## PM ACTIVATION-COVERAGE KPI (pre-reg #135) — EVALUATED
`brain/analysis/pm_activation_coverage_2026-10-25.py` (selfcheck PASS). PM-eligible 30d trades, armed =
any 1m close ≥ entry×1.004, covered = `[TRAIL] ... activated` line inside the trade's own [open, close]
(log covers Sep 23→now, 240 lines):
- **armed n=229** (bar n≥20 met) · **covered 216 / uncovered 13 = 94.3% coverage** · uncovered pnl `−$1.19`
- uncovered dwells **2.7m … 755m** (median ~70m) → **NOT a 60s poll race; cadence-fix hypothesis KILLED**;
  it is an ownership/eligibility gap (3/13 are `bb-bounce-v2-long+`: WLFI/NEO/POLYX; exits mostly
  atr_sl_hit / hard_sl / hard_max_loss)
- uncovered n=13 < 20 → **COLLECT, re-eval at uncovered n≥20.** This is the cohort behind #135's
  "13 of 15 PM-eligible leaks". Numbers post-bug_hunter (NULL-signal rows removed from denominator).

## BUG-HUNTER #136 — NO HIGH; 2 MEDIUM (1 fixed, 1 disclosed)
Independent audit re-verified both selfchecks, reproduced bypass `+2.368` / pm `+0.276` / pm_elig numbers,
and proved the cohort partition exhaustive (94+172+101 = 367 = scoped 30d) and non-overlapping; both scripts
read-only. **FIXED: (M1) NULL-signal trades were misclassified PM-eligible** — live PM SQL
`AND NOT (signal LIKE ...)` never matches NULL → `_cohort_of` now returns `no_signal`,
`pm_eligible(None)=False`, selfcheck asserts added (pm_elig 101→98, coverage 230→229 armed, 14→13 uncovered).
**(LOW) `profit_monster` underscore exit_reason** normalized before match. **DISCLOSED, not fixed:**
pm cohort contains 11 bypass-signal PM exits (engine-based labels intentional); coverage token-window match
over-credits ≤0.4pp from 1 overlapping BTC pair until the `[TRAIL]` line carries trade_id (**queued** — not
touching the CEO-veto-window file twice in one run); arm window includes the open/close-containing candle
(4/230 edge arms, documented).

## #135 / #134 VERIFY — ALL PASS
**Spider tier fix VERIFIED:** percent conversion + tripwire guard live at `profit_monster.py:511-530`;
first post-fix activation `08:55:11 HYPER floor=+0.65` (peak 0.85 − 0.20, **above entry**); spider path
**dormant since 05:29 (pre-fix)** = correct-by-traffic (regime left NEUTRAL); negative-floor lines only in
the pre-fix era; git clean. `be_at_arm_replay --selfcheck` + `mfe_cut_bb_bounce_oos --selfcheck` PASS.

## LOSING AUTOPSY 48h — WRONG-SIDE REFUTED 60th CONSECUTIVE RUN
Adverse-first `recovery_replay.py 48` (selfcheck PASS): **n=13 = 3 never-adverse / 5 recovered / 5 NEVER**.
NEVER = ALT `−0.17` / CC `−0.15` / ZRO `−0.11` `volume-buildup-` shorts (structural never-recover class)
+ BTC pending `−0.08` + PUMP r2v2 `−0.01` — all tiny. 0 new patterns. Valid refs: #61 p=0.116, #84 t=−0.04.
Winning side = flat.

## WATCHDOG TRIAGE (09:14 cycle)
**0 steers, 0 open = CORRECT** (chop/bear: BTC below 1m EMA300 ~440+ closes, LOW vol, 15m+4h SHORT_BIAS vs
phase labels RECOVERY/ACCUMULATION — the disagreement IS the chop). Deep-analysis warnings triaged:
GMT stale pick (RSI drift 16.2 > 15) = AI-trader domain; entry-quality mid-band LONG skip already measured
and REJECTED (#128 dampen, 30d sign flip) — not re-proposed; **bb-bounce-v2-long+ standing item = mine,
status below**.

## bb-bounce-v2-long+ (auditor-owned, open since 2026-10-18) — HONEST STATUS
7d 18T `−0.55` / 14d 34T `−1.01` / 30d 56T `−0.56`, arm 22–27%, still in `STANDALONE_BYPASS`.
**Every offline lever is closed or blocked:** MFE-CUT REJECTED (#134 fk_cohort 23.5%) · deep-dive #75
(stall-exit levers only) · `--sweep-arm` returns `No data` · **bypass-removal counterfactual NOT measurable
offline — NEW side-find: `signals_hermes_runtime.signals` does not reliably contain STANDALONE_BYPASS
fires** (SAGA #16391 has no row, HBAR #16386 does; co-signal base rate 0.8% across 123 7d trades).
→ needs a compactor shadow stamp of co-signal chains before that lever can be evaluated.

## CEO STACK
1. **UNIVERSAL POST-ARM TRAIL FLOOR D=0.20 GO** — evidence now complete across all 3 cohorts
   (bypass `+2.368` PASS / PM `+0.276` no-change / pm_elig COLLECT); replaces/aheads BE-at-arm `+2.14`
2. pump-chain+ NO-KILL (30d `+1.84`, kill MET-by-letter, `no_signal_enable_disable` blocks unilaterally)
   → CONF_FLOOR fkA 41.7% FAIL ruling → pump-chain TAT BASE-vs-VARIANT-C
3. **VETO WINDOW on the spider tier fix** (revert = `profit_monster.py:517-523`, one line)
4. UGB-BE pending (PT subsumes) · Oct-27 contrarian PROMOTE + coin_regime n≥50 + mid-band dampen re-measure
5. Nov-15 floor_admit 30d same-sign (638ep, p=0.126 COLLECT)

## NUMBERS (PG this run)
24h **14T 10W 71.4% `+$0.72` GREEN** (LONG 9T 6W `+0.41` / SHORT 5T 4W `+0.31`) | 7d 123T 43.9% `−$0.57`
| 14d 327T 37.9% `−$3.52` | 30d 689T 43.8% `−$2.10`
7d ARMED 62T 72.6% `+$3.32` vs UNARMED 57T 8.8% `−$4.09` | 14d ARMED 157T `+$9.17` vs UNARMED 163T `−$12.89`
7d exits: **PM-trail 43T 38W `+$2.59`** vs chop/stop **HML 15T 0W `−1.89` + atr_sl 26T 0W `−1.43` +
stale 3T `−0.64` + hard_sl 4T `−0.36` = 48T 0W `−$4.32`** → trend/chop law unchanged.
**Shadow:** contrarian join re-run — **pump-chain- flip-WR 64.0% n=339 (OOS 64.0%) STANDS**; btc-pump-rider+
25.0% = do NOT flip; 1/5 raw files answerable (oscillator frozen-by-design, wyckoff/floor pending, rr orphaned).
`shadow_trader --report` 20208 signals — exit A/B trail-or-nothing (pm_trail `+2781` vs hard_max `−4395`).

## LAST-RUN VERIFY (#134/#135) — ALL PASS
spider fix (above) · be_at_arm + mfe_cut selfchecks PASS · habitat stays REJECTED · floor_admit COLLECT ·
UGB-PT correct-by-traffic · **`hermes_constants.py` git diff EMPTY** · **size-reduce file absent = 1.0x** ·
**CEO_PROTECTED_FLAGS 13/13** (SIGNAL_REGISTRY 86 signals, bb_bounce present) · **0 new uncaught Tracebacks
2026-10-25** (only the recurring Sunday 03:00 `Self-healing test: FAIL`, 3rd occurrence Oct 11/18/25 —
still never triaged). **⚠️ ARM-BE "0 fires" remains no-eligible-traffic, not proven.**

## SIGNAL QUALITY — 0 NEW TARGETS
sub-50% WR, n≥15, 14d: bb-bounce-v2-long+ 34T 41.2% `−1.01` (in flight, levers closed/blocked above) ·
ai-trader+ 23T (disabled) · doji-bottom-long 16T (killed Oct 16) · pump-chain+ 46T 28.3% `−0.43` (kill MET,
CEO) · pump-chain- 35T 22.9% `−0.30` (Oct-27 contrarian PROMOTE). Every sufficient-n bleed cohort is
killed, disabled, in flight, or pre-registered to a dated ruling.

## NEXT ACTIONS
1. CEO ruling: **universal post-arm trail floor D=0.20** (bypass cohort proof landed this run) → v6
   exit-stack; ship as shadow first; ARM-BE shadow stays on
2. CEO veto window on the spider tier fix (one-line revert)
3. Oct 27: contrarian pump-chain- PROMOTE (flip 64.0% n=339 + arm-rate 25.7% n=35) + coin_regime n≥50 +
   mid-band dampen re-measure
4. PM activation-coverage KPI re-eval at uncovered n≥20 (now 13) — wire in as standing weekly KPI;
   queue `[TRAIL]` trade_id log field (makes coverage exact)
5. bb-bounce bypass-removal lever unblocked only by a compactor co-signal-chain shadow stamp (instrumentation)
6. Disk >85% → price_history 30d retention; hotset 0-token re-check ~07:00 Oct 26
7. Triage the recurring Sunday `Self-healing test: FAIL` (3rd occurrence, never looked at)
