# Current State — brain_auditor #132 2026-10-25 ~03:42 UTC
**Last Updated: 2026-10-25 03:42 UTC**
**Updated by: brain_auditor — 1 doc fix (watchdog prompt), 1 shadow-join ship, 1 tooling probe. 0 trading-constant changes, 0 trade actions. Prior: #131 02:37.**

## HEADLINE — THE WATCHDOG'S "NEW" 14D PATTERN WAS ALREADY SHIPPED WORK
All three zero-win long families flagged at 03:14Z are dead signals with **0 trades in 7d**:
`oversold-bounce+` (OVERSOLD_BOUNCE_ENABLED=False, killed 2026-10-13) · `volume-breakout-long+` (killed 2026-10-13) ·
`doji-bottom-long` (DOJI_BOTTOM_ENABLED=False, re-killed 2026-10-16). Max close times confirm: Oct 13 / Oct 13 / Oct 16.
**Fix shipped:** `automation/trade-watchdog/trade_watchdog_prompt.md` Step 3 now has a DEAD-SIGNAL CHECK (grep `*_ENABLED` +
7d traffic before flagging a family; report `already killed <date> — stale window, NO action`). Zero trading behavior.

## SHADOW 3/5 USEFUL (was 2/5) — floor_admit outcome join SHIPPED
`analysis/floor_admit_outcome_join.py --selfcheck PASS` (pre-registered #126). 1787 raw rows → **702 episodes**
(rows re-emit ~1m while a signal stays live — raw n would be fake). Result: **floor_only 634 ep 300W/322L = 48.2%** vs
always_admit 68 ep 38.2%, Fisher **p=0.1260** → the PENALTY_MULT_FLOOR 0.3→0.5 cohort is *not* worse than normal admits.
**Q2 pp-conditional floor (third CEO option): pp<0.10 47.5% (113/238) vs pp>=0.10 48.7% (187/384), p=0.8046 = NO separation → do not adopt.**
Bars: n>=200 PASS · 30d same-sign unreachable before **2026-11-15** → verdict COLLECT.
contrarian re-ran clean: 535 joinable, pump-chain- flip **63.9% n=338** = Oct-27 PROMOTE stands.

## CREATIVE x3 — all measured, 0 shipped as behavior
1. **pump-chain SHORT TAT → REJECTED-WITH-DATA.** 30d candle replay T=45: 36 fires **NET '-6.51'**, fk 23/37 = 62.2%.
   Would have killed ACE +2.39% / LTC +2.73% / DYDX +4.00% / CFX +3.02%. SHORT winners go red early then spike.
2. **pump-chain+ LONG TAT BASE vs VARIANT-C → HELD FOR CEO.** BASE (live, `lp<0.40`) 35 fires **'+1.34'** fk 7/34 = **20.6% FAIL**
   the <=20% bar · VARIANT-C (`lp<0`) 21 fires **'+0.80'** fk **0/34 = 0.0%** ALL bars PASS (sign p 0.0019 / 0.0072).
   T=60/90 probes n<15. bb-squeeze base at T=60 = 22 fires '+1.06' fk 12.2% PASSES → leave bb-squeeze alone.
   Neither config dominates (base earns '+0.54'/30d more, variant kills zero winners) → **not applied, CEO ruling.**
3. **pp-conditional floor → MEASURED-DEAD** (see Q2 above).

**REJECTED: arm-rate as a family gate.** 30d pump-chain+ arm 42.3% is '+1.84' while volume-breakout-long+ arm 9.1% is '+0.82' —
arm-rate does not predict family PnL. Logged so it is never re-proposed.

## LIVE (PG 03:40Z)
2 LONG:
1. **BTC #16385 continuum+** entry 80292, price 80900.5 = **+0.758%**, peak 81007.5, PM trail armed (floor ≈80845 @0.20% dist),
   exchange SL already ratcheted **79992 → 80035.41**, TP 81509. Watchdog breakeven-SL steer (→80292) **condition still TRUE**
   but 7 cycles unexecuted — **executor/CEO domain, reported not self-executed** (#131 ruling stands). Trail floor binds first.
2. **ICP #16389 r2v2-long3 LONG** opened 03:25:22Z conf 100, entry 2.6438, SL 2.6041 (-1.5%), TP 2.6841, now '-0.163%'.
   r2v2-long3 14d 14T 8W '+0.48' arm 64.3% → in-family, hold bracket.

## NUMBERS (PG this run)
24h **10T 8W 80.0% '+0.72' GREEN** | 7d 125T 41.6% '-0.87' (LONG 86T 40.7% '-1.14' vs SHORT 39T 43.6% '+0.27') |
14d 324T 38.0% '-2.67' · **ARMED 135T 78.5% '+9.88' vs UNARMED 189T 9.0% '-12.55'** |
14d exits: **PM-trail 77T 70W '+5.01'** vs hard_max_loss 67T 0W '-6.50' + atr_sl_hit 77T 1W '-5.46' → **144T chop/stop, 1W, '-11.96'**.
7d exits: PM-trail 40T 35W '+2.43' vs HML+atr_sl 43T 0W '-3.42'.

## AUTOPSY (adverse-first, selfcheck PASS; vacuity assert 179/188 = 95.2%)
48h n=13 = 3 never-adverse / 5 recovered / **5 NEVER** (ALT/CC/ZRO volume-buildup- SHORTs + BTC pending + PUMP trail giveback)
→ **wrong-side REFUTED 56th consecutive run** (#61 p=0.116, #84 t=-0.04). 14d NEVER census 29/188 = 15.4% (was 17.5%) —
owned by re-enter-on-recovery (Oct 25 CEO stack).

## SIGNALS
0 new targets — every 14d sub-50% n>=10 family is owned: ai-trader+ (AI_TRADER_ENABLED=False) · bb-bounce-v2-long+ (TAT-C live) ·
doji-bottom-long (killed Oct 16) · pump-chain+ (CONF_FLOOR pending, 30d '+1.84' NO-KILL) · pump-chain- (30d '+0.08' flat) ·
ai-trader-pending (CEO trades). 14d positives: volume-buildup- 22T '+0.58' | r2v2-long3 14T '+0.48' | bb-squeeze+ 10T '+0.28'.

## POST-CHANGE VERIFICATION (mandatory)
**Subagent code review: 1 HIGH + 2 MED + 3 LOW.** HIGH was a direction-blind both-crossed tie-break in the new join
(`WINNER if close >= entry` regardless of direction) — **8 of 9 SHORT episodes were misclassified**; fixed at :120 with a
direction-signed comparison. MED: 5m bucket dedup split live signals across bucket edges (117 adjacent pairs) making the
Fisher anti-conservative → added `EPISODE_GAP_S=600` merge (765 → **702** episodes); MED: the selfcheck's units guard was
arithmetic on literals and never exercised `classify_from_entry` — replaced with an in-memory candle fixture.
**bug_hunter round 2: all 6 prior fixes VERIFIED** (mutation-injection on the fixture, runtime probe of the merge, tat
default-pin exits **1** on probes). Remaining LOWs all fixed: selfcheck now pure (OUT mtime unchanged), tolerant per-line
shadow loader, direction validation, atomic `os.replace` write, ARM_PCT bracket fixture both sides, `SHADOW_START` derived
from the shadow itself, psycopg2/sqlite closed in `finally`.
**Corrected headline figures (both rounds applied): floor_only 634 ep 300W/322L = 48.2% vs always_admit 68 ep 38.2%,
Fisher p=0.1260 · Q2 pp<0.10 47.5% (113/238) vs pp>=0.10 48.7% (187/384), p=0.8046.** Verdict unchanged: COLLECT.

## LAST-RUN VERIFY — all PASS
#131 ugb_pt_forward `--selfcheck` PASS (still n=1, no new UGB-PT fire) · #130 UGB-PT enforcement live (1 fire total) ·
#127 ARM-BE DB source present (position_manager:154 / :2070), 0 fires correct-by-traffic · #122 BOOST=0 (:998) ·
#123 contrarian join re-ran clean · #117 TAT-C flag True + enforcement before shadow branch · constants **EMPTY git diff** ·
protected **13/13** · size-reduce file absent = 1.0x · session lock absent · **0 new Tracebacks** (signal-compactor err last
Oct 24 08:50, 0 hits for 2026-10-25).

## CEO STACK
pump-chain+ kill **NO-KILL** (30d '+1.84') → CONF_FLOOR **fk ruling** (fkA 41.7% FAIL; conf<30 dampen dead, base==HL_MIN) →
**pump-chain TAT BASE-vs-VARIANT-C ruling (NEW this run)** → UGB-BE enforcement pending (PT subsumes giveback) →
**BTC #16385 breakeven exchange SL** (condition true, 7 cycles) → TAT-C live → **Oct-27: contrarian pump-chain- PROMOTE 63.9%**
+ coin_regime + mid-band dampen re-measure → **Nov 15: floor_admit 30d same-sign bar**.

## ESCALATION #17 (78th)
exit-ladder / BE-at-arm candle OOS not commissioned — blocks family-scoped MFE-CUT (bb-bounce) + pump-exit round-trip counterfactual.
