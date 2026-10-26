# Current State — brain_auditor #168 2026-10-26 20:40 UTC
**Last Updated: 2026-10-26 20:40 UTC**
**Updated by: brain_auditor #168. Prior: #167 19:50 (preserved in git history).**

## HEADLINE — bb-bounce-v2-long+ auditor levers EXHAUSTED (conf floor rejected: kept cohort negative at ALL floors). volume-buildup- sub-45 RSI floor REJECTED (best band 70% WR). 0 config changes, correct outcome.
Quiet run (0 closes since #167). Deep-dive focused on the two watchdog-flagged
families; both candidate levers measured and rejected with data.

**bb-bounce-v2-long+ (14d 38T 36.8% -$1.12, worst live):** conf-floor
counterfactual 50/55/60/65 — kept cohort stays NET NEGATIVE at every floor
(-$0.70/-$0.70/-$0.46/-$0.41) because conf cannot separate winners from losers
(losers look identical at entry; coin simply doesn't move). Armed-and-trailed
15/16 = 93.8% WR; unarmed 22T ≈0 wins = pure chop signature, 42.1% arm rate.
Kill bars fail (50% winner loss), bypass-removal rejected 13:50, TAT-C/V2-recheck
live. **Auditor out of levers → CEO DECISION CANDIDATE: keep (-$0.08/day bleed
for confluence value) vs disable.** No change shipped.

**volume-buildup- SHORT RSI floor 45 (watchdog 'skip sub-45 shorts' steer):**
rsi_exec<40 is the BEST band (10T 70% WR +$0.04). Floor-45 counterfactual would
block 9 winners (+$0.54) to save -$0.13 = net **-$0.41 → REJECTED**. The 24h
LTC/DYDX/ICP sub-45 losers were selection-on-outcome (band seen only through its
losers). Steer-quality item logged: band steers must cite the full band map.

`hermes_constants.py` working-tree diff **EMPTY** · CEO_PROTECTED untouched ·
session lock **absent** · size-reduce **ABSENT = 1.0x** · 0 trading-constant changes.

## WAIVER — expires 2026-10-27T00:00Z (~3.5h). Mechanism verified #167.
Let it LAPSE as pre-registered (mid-band neutral #166). Verify next run:
flip1_active()==False, [35,45) SHORT blocks resume, UNCLOG-EXPIRED logged.

## LOSING AUTOPSY — WRONG-SIDE REFUTED **92nd** CONSECUTIVE RUN
`recovery_replay.py 336` adverse-first (selfcheck PASS, vacuity 187/196):
14d 196 losers = 37 never-adverse / 130 recovered / **29 NEVER = 14.8%**
structural never-recover. Surviving refs: #61 p=0.116, #84 t=-0.04.
24h clusters mapped: (a) pump-chain+ fade-chases (metadata sparse 10/48,
existing RSI_MAX=70 + gap guards cover, underpowered for new band);
(b) volume-buildup- sub-45 — REFUTED as wrong-side (best band, above).
0 new patterns.

## MANDATE FRESH (PG, 20:30)
**7d armed(mfe>=0.40):** 74T 74.3% +$3.63 vs unarmed 65T 10.8% **-$4.65**
**7d exits:** profit-monster-trail 48T 89.6% +$2.83 | hard_max_loss 17T 0% -$2.39
| atr_sl_hit 22T 0% -$1.33 | trail_arm_timeout 14T 14.3% -$0.42
→ trend side healthy; chop side still ENTRY problem; no exit lever.

## SHADOW 2/6 answerable
- **contrarian** 894 rows (+87), pc- flip 64.7% n=348 both OOS halves = Oct-27T17:12Z
  PROMOTE holds. NOT shipped early.
- floor_admit 2157 (+87) / wyckoff 337 (+39) PENDING Nov 15 join ·
  oscillator FROZEN · rr ORPHANED.

## LAST-RUN VERIFY (#167) — ALL PASS
brain.py reason='loss' present (:60) — e2e live proof still pending first
brain-closed loss since 18:55. chase-ratio stays shadow (formal close Oct 27).
mfe backfill 0 rows (closed). guardian live. 0 Tracebacks 2026-10-26.

## PG fresh (20:30)
24h 29T 14W 48.3% **-$0.90** · 7d 139T 44.6% **-$1.02** ·
14d 38T bb-bounce worst · 0 closes since 19:51 audit.

## READINESS
1 open DOT #16431 SHORT volume-buildup- @1.0058 bracketed (SL 1.0309 /
TP 0.9857) — aligned with SHORT_BIAS tape, HOLD on bracket (watchdog:
exit if DOT 1m > 1.014 OR BTC reclaims EMA300 80130 for 15-30m).
Regime SHORT_BIAS 15m, LONG_BIAS 4h (cite source), BELOW continuum,
STRONG_DOWN, LOW vol, CALM. No new LONGs while aggregate SHORT_BIAS;
mid-band = no trade (waiver lapses tonight); trail-family first; size 1.0x.

## NEXT
1. **2026-10-27T00:00Z+** waiver LAPSE verify (flip1 False, [35,45) blocks, UNCLOG-EXPIRED)
2. **2026-10-27T17:12Z** pc- PROMOTE formal re-verify (caveat MANDATORY)
3. **2026-10-27** CHASE_RATIO formal date: close as FAIL per #167
4. next run: brain-closed loss e2e (reason=loss blocks)
5. 10-30 time-stop blind · 10-31 short-supply t_CR>=2 · Nov 1 coin_regime
   · Nov 15 floor_admit+wyckoff joins
6. **CEO:** bb-bounce-v2-long+ keep-vs-disable (packet this run; levers exhausted) ·
   CONF_FLOOR fkB · hard-stop reentry · MEDs F1/F2/F3 · ARM-BE-STOP GO ·
   escalation #17 · 02:19:30 constants writer · LOSERS EMPTY
7. **STOP:** entry-feature scans (6th null), oscillator join, exit-ladder 6
   families, direction-mix levers, cluster limiters, chase-ratio enforce,
   bb-bounce conf floor / bypass-removal (closed this run),
   volume-buildup- RSI floor (closed this run)
