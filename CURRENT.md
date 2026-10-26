# Current State — brain_auditor #170 2026-10-26 22:45 UTC
**Last Updated: 2026-10-26 22:45 UTC**
**Updated by: brain_auditor #170. Prior: #169 21:45 (preserved in git history).**

## HEADLINE — Habitat ledger (new standing KPI, zero code): 2 signals are
PSEUDO-KILLED by regime overrides while flags stay True — bb-bounce-v2-long+ 87%
of 30d habitat blocked (signal_reporter NORMAL-block 21:43 verified live) and
pump-chain- 85% (EXTREME blocked, NORMAL-only live). 0 config changes (correct:
nothing passed bars; no_signal_enable_disable honored). Waiver lapses ~00:00Z.

**bb-bounce-v2-long+ (CEO packet COMPLETE):** 3rd live demo failed — CAKE #16430
trail_arm_timeout MFE 0.359 (never armed), ADA + CAKE#16413 earlier today, all
NORMAL regime. signal_reporter shipped NORMAL block (commit 5395c3a8) at 21:43 —
verified in volatility_gate_v2.py:412, correct-by-traffic (0 opens since). NORMAL
block forfeits 11T +0.63 to save 19T -1.35 = net +0.72/14d. With EXTREME already
blocked, live habitat is HIGH/FLAT-only = 0 trades in 14d. Every auditor lever
rejected-with-data; keep-vs-disable GO still CEO (flag stays True per rules).

**Waiver-class SHORT deaths root-caused (no action — lapse handles it):**
LTC #16422 detect RSI 37.33 → exec 51.18 (drift 13.85) and DYDX #16420 37.94 →
44.92 both entered via the [35,45) exemption band; SHORT-MIDBAND reads
detect-first (decider_run.py:2265) so exec drift into the death zone passed.
Tonight's 00:00Z lapse (HARD_FLOOR=45 at detect) closes the class automatically.

`hermes_constants.py` working-tree diff **EMPTY** · CEO_PROTECTED 13/13 · session
lock **absent** · size-reduce **ABSENT = 1.0x** · 0 trading-constant changes ·
vacation no_signal_enable_disable=true · unclog waiver expires **2026-10-27T00:00Z**.

## LOSING AUTOPSY — WRONG-SIDE REFUTED **94th** CONSECUTIVE RUN
`recovery_replay.py` adverse-first (selfcheck PASS): 48h n=21 losers =
6 never-adverse / 13 recovered-after-adverse / **2 NEVER**:
- ICP #16409 SHORT rsi 39.0 = waiver-band class — **blocked post-lapse tonight**
- CC #16423 pump-chain- SHORT rsi 46.95 = midband carve-out legal (n=1, documented)
24h 15 losers: 7 LONG chase entries (RSI 55-69 buying strength that faded) +
SHORTs in the 45-55 death/whipsaw band — the mirror-image pattern unchanged.

## MANDATE FRESH (PG 22:35)
**7d armed(mfe>=0.40):** 74T 74.3% +$3.63 vs unarmed 62T 4.8% **-$4.84**
**14d armed:** 166T 69.9% +$8.36 vs unarmed 165T 5.5% **-$13.35**
**14d exits:** profit-monster-trail 84T 91.7% +$4.61 | hard_max_loss 61T 0% -$6.37
| atr_sl_hit 80T 1.3% -$5.57 | trail_arm_timeout 25T 16% -$0.87
**7d direction:** LONG 91T 40.7% -$1.25 / SHORT 50T 52.0% +$0.23 — chop tape,
continuum BELOW, sources flipped overnight to LONG_BIAS (advisory: no fresh LONGs
until reclaim holds with volume).

## SHADOW 2/6 ANSWERABLE
- contrarian 894/622: **pc- 64.7% n=348 holds**, rider 28.6% flipped-worse —
  signal-selective. NEW: pc- 85% habitat regime-blocked → Oct 27 PROMOTE verify
  must add NORMAL-scoped flip-WR (pre-registered this run)
- shadow_trader 26146: CONFLUENCE-EXPIRY 11837 @48% (gates justified); pm_trail
  exit engine dominant (+3687.76 shadow vs hard_max -5535.92)
- floor_admit 2158 / wyckoff 337 PENDING Nov 15 · oscillator FROZEN · rr ORPHANED

## LAST-RUN VERIFY — ALL PASS
- #169 pm_armed_at stamp LIVE (profit_monster.py:453, 1 adoption)
- #169 contrarian scope caveat re-verified fresh
- #167 brain.py loss-cooldown: code present, e2e correct-by-traffic
- #152 daily-commit constants guard LIVE (4-case selfcheck), no rogue commits
- #151 CONF_FLOOR held: fkB re-confirmed FAIL (all-signal 16/55=29.1%, bare 9/32=28.1%)
- kill flags correct (VB+/VB-/HMACD_MTF±/OVERSOLD False) · protected 13/13 ·
  constants EMPTY · 0 new Tracebacks (last Oct 11) · session lock absent

## PG fresh (22:35)
24h 30T 14W 46.7% **-$0.92** · 7d 141T 44.7% **-$1.02** · 14d 337T 38.6% -$4.80

## READINESS
0 open — flat correct. Regime: chop, continuum BELOW (BTC ~79964 vs EMA300 80109),
aggregate flipped SHORT→LONG_BIAS 21:45, trend_quality STRONG_DOWN, LOW vol.
No fresh LONGs until 1m reclaims EMA300 with volume; SHORTs on bounce into
RSI 55-65 only (skip 45-55); mid-band = no trade; trail-family first; size 1.0x.
bb-bounce effectively dormant (HIGH/FLAT-only) — do not treat flag True as live.

## WAIVER — expires 2026-10-27T00:00Z (~1.5h)
Let LAPSE as pre-registered. flip1_active()==True verified this run. Post-lapse
verify: flip1_active()==False, [UNCLOG-EXPIRED] logged, 0 new [35,45) band opens.

## NEXT
1. **2026-10-27T00:00Z+** waiver LAPSE verify (flip1 False + 0 band opens)
2. **2026-10-27T17:12Z** contrarian PROMOTE re-verify — pc--scoped + NORMAL-scoped
   flip-WR report (pre-registered #170)
3. **CEO:** bb-bounce keep-vs-disable (packet complete — effective habitat gone)
   + CONF_FLOOR fk-definition/fkB FAIL ruling
4. Habitat ledger: carry 2 more audit runs, then decide auto_1hr automation
