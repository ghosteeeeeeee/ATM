# Current State — brain_auditor #180 2026-10-27 09:45 UTC
**Last Updated: 2026-10-27 09:45 UTC**
**Updated by: brain_auditor #180. Prior: #179 08:45 / #178 07:55 (preserved in git history).**

## HEADLINE — All Oct-27 scheduled evals now DISPOSITIONED. 0 config changes, 0 ships, 0 trade actions.

Four items were due today; #179 disposed of waiver/mid-band/coin_regime/pc-PROMOTE. This run
closed the remaining scheduled item and refuted the watchdog's "best cells":

1. **LONG rsi_14 55-65 death cell re-measure (the last Oct-27 item):** 7d 22T 31.8% `-$0.79` |
   14d 55T 38.2% `-$1.65` | **30d 156T 49.4% `+$1.01` SIGN-FLIP positive** → window-instability =
   stays **advisory-only, NO enforceable block** (was already measured-refuted; re-measure confirms).
2. **Watchdog deep-analysis "best cells" DO NOT REPRODUCE:** LONG meta_rsi<35 "83.3% n=6" →
   14d 14T **42.9%** `-$0.25` / 30d 38T 55.3% `-$0.08`; SHORT 65-75 "100% n=5" → 14d 9T 77.8%
   `+$0.46` / 30d 49T 51.0% `+$0.34` = **small-n noise, do not trade those cells as edge.**
3. **Watchdog route #3 (vb- oversold-short band) re-confirmed CLOSED** (already #177): blocked
   14d==30d 22T 63.6% `-$0.15`, fk 63.6% >> 20% bar, save `$0.86` < `$1.00` bar → REJECTED stands.
4. **pc- PROMOTE formal at 17:12Z** — NO-GO rec already on file (#178/#179); no action until then.

## LAST-RUN VERIFY #179 — ALL PASS
`coin_regime_direction_2026-10-27.py --selfcheck PASS` + re-run reproduces COLLECT (p=0.1262) ·
constants working-tree diff **EMPTY** · CEO_PROTECTED **13/13** · session lock **absent** ·
waiver `flip1_state=(False,'expired')` + **0 band opens** since 00:00Z · kill flags correct
(doji-bottom False, vb+ False, vb- False, oversold False, hmacd False, AI_TRADER False) ·
size-reduce **absent = 1.0x** · Tracebacks **5 total, all Oct 11** (0 new) · `pm_armed_at`
**5 stamps** · `gate_leak_census --selfcheck PASS`.

## MANDATE (fresh PG 09:31)
- 24h **27T 12W 44.4% `-$0.74`** | 7d **143T 46.9% `-$0.51`** | 14d 328T 39.3% `-$4.73`
- **armed 7d 80T 76.3% `+$4.03` vs unarmed 59T 5.1% `-$4.58`** (4T null-mfe `+$0.04`)
- **armed 14d 164T 70.7% `+$7.95` vs unarmed 159T 6.3% `-$12.72`**
- pm_trail 7d 52T 90.4% `+$2.95` vs HML 15T 0% `-$2.00` + atr_sl 20T 0% `-$1.25`
- **chop-bleed share 85.6%/86.1%/81.2%** — stable, entry-quality stays at gates
- LONG 7d 92T 44.6% `-$0.50` / SHORT 7d 51T 51.0% `-$0.01`

## NEW KPI — LONG ARM-RATE GAP (creative #2, zero-code)
14d **LONG armed 45.2%** (95/210) vs **SHORT 59.0%** (69/117); unarmed bleed LONG `-$8.90` vs
SHORT `-$3.67` — LONGs enter chop more often. Pre-registered tripwire: flag to CEO when 7d LONG
arm-rate <50% while SHORT >55% for 2 consecutive runs (advisory only, no gate).

## CREATIVE #1 — btc_regime × direction census, REJECTED-WITH-DATA
Counter-intuitive cell found: **LONG BULL_TREND is the WORST LONG cell** (30d 181T 44.2%
`-$2.57`) while LONG RANGING is best (`+$0.88`/89T) — "trend is your friend" fails on this axis.
Block **REJECTED**: fk 44.2% >> 20% bar, effect shallow (`-$0.014`/trade), partially signal-mix
(pc+ 32T 31.3% `-$0.57`, bb-bounce 18T 27.8% `-$1.06`) yet rest-of-book also `-$0.94`/131T.
Logged so no future run re-proposes naively. SHORT BEAR_TREND mixed (pc- 51T 27.5% but `+$0.49`).

## LOSING AUTOPSY — WRONG-SIDE REFUTED **104th** CONSECUTIVE RUN
`recovery_replay.py` adverse-first, selfcheck PASS: **48h n=21 = 5 never-adverse / 13 recovered /
3 NEVER** (AERO cut-loser `-0.12`, ICP waiver-class `-0.09`, CC pc- `-0.07`) — identical cohort to
#179 (no new closes since 08:42). Refs that survive: `#61` p=0.116, `#84` t=-0.04. Winning side = flat.

## DEEP-DIVE — 0 new sub-50% n>=10 targets
pump-chain+ LONG 18T 44.4% `-$0.44` (NO-KILL standing, 30d positive) · bb-bounce-v2-long+ 18T
33.3% `-$0.36` (CEO keep-vs-disable pending) — every other bleed owned/killed/disabled/CEO.

## SHADOW — 2/6 answerable
contrarian join fresh 623: **pc- flip 64.8% n=349 STABLE** (p=4.6e-08, OOS 66.1/62.6) = NO-GO
rec stands for 17:12Z (live-exit contradiction #178) · btc-pump-rider+ 28.6% do-not-flip ·
shadow_trader 27,743 signals: CONFLUENCE-EXPIRY 12,218@48% gates justified, exit A/B pm_trail
`+3971` vs hard_max `-5862` · oscillator FROZEN · floor/wyckoff PENDING Nov 15 · rr ORPHANED.

## WATCHDOG TRIAGE (09:15 cycle)
- 0 steers, portfolio healthy, 0 open — flat book correct on chop pin
- Regime: STRONG_DOWN trend_quality + RECOVERY phase + LEAN_BULL linreg + AT EMA300 = classic
  no-edge conflicting labels → no fresh entries until 1m sustains one side 15-30m with volume
- Routes #3 (vb- band) and #4 (death cell) both dispositioned above; "best cells" refuted
- Chop-bleed KPI 84.7% quoted at baseline — matches my 85.6% fresh (stable, not deteriorating)

## DRIFT
- **D180-1:** `meta_rsi` is NOT a PG column — it is `_signal_metadata.rsi_14` (watchdog maps it at
  trade_watchdog.py:247). Analysts querying `meta_rsi` get 0 rows (hit this run, corrected).
- Carried: session_brain dup-heavy (rebuild owed, ideation only) · weekly Sun 03:00 dispatcher
  Traceback (verify Nov 1) · `data_integrity_guard.py` never invoked.
- #179's `pm_armed_at` "5 stamps" re-confirmed (5/5 closed trades since ship carry it).

## QUEUE
- **2026-10-27T17:12Z** pc- PROMOTE formal — NO-GO already on file, do NOT ship early
- **2026-10-30** scoped momentum time-stop BLIND run (bars locked + MFE<0.15 attribution)
- **2026-10-31** short-supply re-measure `t_CR>=2`
- **2026-11-01** coin_regime LONG-COUNTER OOS + self-healing SKIP verify
- **2026-11-04+** coin_regime LONG->SHORT_BIAS re-measure (p<0.05 + fk<20%)
- **2026-11-08** gate scoreboard #2
- **2026-11-15** floor_admit + wyckoff outcome joins
- rsi drift monitor n>=100 (81) · CHASE_RATIO joined n>=20 (18)
- **NEVER:** re-run entry-feature / armed-separation scans (5 nulls) · vacuous open-anchored recovery
- **CEO:** CONF_FLOOR fkB FAIL · pc- PROMOTE NO-GO (17:12Z) · bb-bounce keep-vs-disable · TAT flip ·
  hard-stop reentry · escalation #17 (exit-ladder candle OOS)

## BOOK / READINESS (24h 27T 44.4% `-$0.74` · 7d 143T 46.9% `-$0.51` · 14d 328T `-$4.73`)
**0 open — flat correct.** Chop pin at EMA300 unresolved, conflicting regime labels, vol LOW.
No fresh entries until 1m sustains one side 15-30m WITH volume · mid-band = no trade ·
trail-family first · size 1.0x (file absent) · SHORTs only as bounce-fades with full precheck
(the watchdog's 65-75 "100%" cell is refuted — do not use it as a target).
