# Current State — brain_auditor #164 2026-10-26 15:45 UTC
**Last Updated: 2026-10-26 15:45 UTC**
**Updated by: brain_auditor #164. Prior: #163 14:55 / #162 13:50 / #161 12:55 (preserved in git history).**

## HEADLINE — 0 config changes, 2 instruments. Contrarian PROMOTE now has every leg PASS, 26h before its date. Exit-ladder OOS delivered the next slice: 5 families REJECT-WITH-DATA.

Nothing shipped. Every candidate failed a bar that was written down before the number was read.

| candidate | bar | result |
|---|---|---|
| short-gate loosening | n≥50 AND net > +$1.00 AND 30d OOS same sign AND blocked WR <30% | **0 of 22 PASS** (nearest SLOPE-FILTER +$0.98 — misses by $0.02) |
| pump-chain- direction flip | paired p<0.05, flip>orig both tables, OOS same sign both halves | **ALL PASS** — but auto-fire is **2026-10-27T17:12Z**, DO NOT ship early |
| bb-bounce-v2-long+ kill | must not block >20% of 30d winners | **FAIL** (would take 28/56 = 50%) |
| new arm-timeout (6 families) | ALIVE n≥20, fired≥5, fk≤20% of alive winners, net>0, OOS same sign | **0 PASS / 6 FAIL-or-skip** |
| bb-squeeze TAT 60→55m | same as above | **FAIL** (alive fk 46.2% at T=55, 66.7% at live T=60) |

`hermes_constants.py` working-tree diff **EMPTY** · CEO_PROTECTED untouched · session lock **absent** · size-reduce **ABSENT = 1.0x**.

## CONTRARIAN PROMOTE — control arm landed today, and it was the missing leg
`analysis/contrarian_both_sides_2026-10-26.py` scores **both** directions on the same events/rule
(same ±0.40% / 30×5m classifier), paired exact binomial, median-time OOS split:

| signal | n | orig WR | flip WR | paired p | OOS older | OOS newer |
|---|---|---|---|---|---|---|
| **pump-chain-** | 348 | **36.5%** | **64.7%** | <1e-4 | 36.2→65.7 p<1e-4 | 37.0→63.0 p=0.0033 |
| btc-pump-rider+ (control) | 252 | 73.4% | 25.3% | <1e-4 | do-not-flip | do-not-flip |
| whole pool | 601 | — | 48.5% | — | — | — |

The counter-control is what makes it evidence: btc-pump-rider+ is **right** 73% of the time, so this is
not a global upward-drift artifact of the entry windows, and the pool-wide 48.5% proves the edge is
**family-specific**, not a generic "flip everything".

**Fee-adjusted EV under the symmetric classifier** = 0.647×(0.40−0.05) − 0.353×(0.40+0.05) = **+0.068%/event**.

**⚠️ MISSING LEG for the Oct-27 package:** 64.7% is scored under a fixed touch classifier, **not** under
live trail/ATR-SL exits. State the caveat in the ruling, or ship a live-gate-aware shadow line first
(`automatic-implementation` shadow→enforce). Do not present "64.7%" as live expectancy.

## EXIT-LADDER CANDLE OOS — escalation #17, next slice (instrument ships, nothing does)
`brain/analysis/exit_ladder_oos_2026-10-26.py` — `--selfcheck PASS` (**5** assertions: sign
convention, units, fk%, verdict bars, **alive-denominator guard**). Bars locked in the docstring
**before** any result: **ALIVE** n≥20 (= held to age T), fired≥5, fk≤20% of **alive** winners, net>0,
OOS same-sign across the cohort's own median `open_time`. Units: `cf$ = amount_usdt × live_pnl/100`,
`benefit = cf − actual` (no `pnl_pct` landmine).

**⚠️ SELF-AUDIT CAUGHT A FALSE PASS IN MY OWN FIRST CUT.** The first version inherited the Oct-17
grid's *whole-cohort* denominators. A trade that closed **before age T can never be fired on**, so
counting it as a possible FK victim dilutes fk% and inflates n — both anti-conservative. Under those
denominators bb-squeeze T=55 read **PASS** (fk 12.0%, net +$1.10); on alive-only it is **fk 46.2% =
FAIL**. This was the **only** PASS in the run. Script fixed, both columns now printed
(`fk%` = alive, `fk%coh` = cohort), selfcheck gained an assertion that a big cohort with few alive
trades cannot satisfy b1. **Tightened post-data toward the stricter side, so no loosening risk.**

| family | verdict | why |
|---|---|---|
| bb-bounce-v2-LONG (n=65, alive 28–50) | **FAIL all 7 T** | alive fk 52.9%–87.0% — a no-arm cut would butcher its PM-trail winners |
| volume-buildup-SHORT (n=33, alive 3–15) | SKIP all 7 T | alive n<20 at every T **and** net negative at every T; it is our 66.7% WR signal — do not touch |
| r2v2-long3-LONG (n=20, alive 4–9) | SKIP all T | alive n<20; cohort fk 25% at best |
| hl-copy LONG (n=12) / SHORT (n=3) | SKIP | n<20 |
| bb-squeeze-LONG (n=83, alive 14–49) | **FAIL all T** | alive fk 46.2%–66.7% where alive≥20 (cohort-denominator read would say 12.0% at T=55 — see self-audit) |

**Net: 0 exit levers, 0 PASS anywhere.** The new-arm-timeout, widen-bb-bounce-TAT and tighten-bb-squeeze-TAT
alternatives are now closed with data for these 6 families — stop re-proposing them. Max candle staleness
observed: 58s (negligible).

## DRIFT — the Oct-25 arm-rate KPI counted the wrong column
`trailing_activated` is an **exit-reason flag**, not an arm indicator:

- 14d: `trailing_activated`=142 vs `mfe_pct>=0.40`=165
- **pump-chain-: 9 (24.3%) vs 24 (64.9%)** ← the KPI published 25.7%
- `ugb_pt` exits with `mfe_pct=0.459` read **FALSE** (trade 16421 ETH); `trail_arm_timeout` reads **TRUE** with no arm (25/25)

**Impact:** the KPI called pump-chain- a **CHOP** signal and routed it toward a momentum gate. It is a
**WRONG-SIDE** signal — it reaches the trail threshold 65% of the time and still loses 78% of them.
A momentum gate cannot fix that; the direction flip can. Corrected entry appended to
`brain/creative_improvements.json`.

### Corrected two-axis matrix (arm = `mfe_pct >= 0.40`, 14d n≥15, 30d alongside)

| signal | 14d n | arm% | WR% | pnl | 30d | route |
|---|---|---|---|---|---|---|
| bb-bounce-v2-long+ | 38 | 42.1 | 36.8 | −1.12 | 61 / 57.4 / 47.5 / −0.61 | WRONG-SIDE → direction/exit |
| ai-trader+ | 20 | 45.0 | 30.0 | −0.85 | 29 / 48.3 / 41.4 / −0.80 | WRONG-SIDE (already disabled Oct 19) |
| **pump-chain-** | 37 | **64.9** | **21.6** | −0.42 | 87 / 69.0 / 34.5 / −0.04 | **WRONG-SIDE → contrarian flip** |
| pump-chain+ | 46 | 41.3 | 32.6 | −0.15 | 75 / 49.3 / 40.0 / **+1.81** | WRONG-SIDE 14d only; 30d green — no lever |
| ai-trader-pending | 16 | **18.8** | 25.0 | −0.14 | 16 / 18.8 / 25.0 / −0.14 | **CHOP** (never arms) — n<20, no fire since Oct 24 |
| doji-bottom-long | 16 | 31.3 | 31.3 | −0.97 | 30 / 56.7 / 50.0 / −0.36 | killed Oct 16, last open matches |
| r2v2-long3 | 17 | 47.1 | 58.8 | −0.03 | 20 / 55.0 / 60.0 / +0.47 | healthy |
| volume-buildup- | 33 | 69.7 | 66.7 | **+0.51** | 33 / 69.7 / 66.7 / +0.51 | healthy |

**This matrix is also why entry-feature mining stays STOPPED (6th null):** cohorts separate by signal
identity, not by admission-time continuous features. A momentum gate aimed at the CHOP column would
miss pump-chain- entirely.

## MANDATE — CHOP vs TREND (fresh PG, 14d 336T 38.6% `−$4.71`)
- exits: **`profit-monster-trail` 83T 91.6% `+$4.58`** + `atr_trail_hit` 24T `+$3.47`
  vs `atr_sl_hit` 80T 1.3% `−$5.57` vs `hard_max_loss` 63T 0.0% `−$6.41`
- **armed 165T 70.3% `+$8.40`** vs **unarmed 166T 5.4% `−$13.27`** — 7d `+3.65` vs `−4.43`
- MFE ladder monotone in all 3 windows: `<0.15` **−$7.60** (14d) / **−$18.24** (30d) · `≥0.40` **+$8.56** / **+$26.20**
- hold by bucket (14d): `<0.15%` 42m avg · `0.15–0.40` 89m · `≥0.40` 93m

Trend side healthy. The addressable bleed is unchanged and every exit lever tested this run failed.

## LOSING AUTOPSY — WRONG-SIDE REFUTED **88th** CONSECUTIVE RUN
`recovery_replay.py` adverse-first (`--selfcheck` ASSERT PASS, vacuity 182/191 reproduced):
**48h n=17** = 5 never-adverse / 10 recovered-after-adverse / **2 NEVER** (16409 ICP waiver-band,
16423 CC pump-chain-) · **14d 194 losers = 37 / 128 / 29 NEVER = 15.0%** structural never-recover
(17.5% Oct-22 baseline, 14.7% #163). Refs that survive: `#61` p=0.116, `#84` t=−0.04.

## SHADOW — one useful source, four dead/pending
- **contrarian 892 rows / 601 joinable** = the only collector producing a ship-eligible answer
- **oscillator 24,598 — `actual_outcome` 0/24,598** (frozen by design): unusable, decided dead
- **floor_admit 2,106 / wyckoff 331 — no outcome column**: pending joins (Nov 15)
- **rr_shadow_audit_7d**: orphaned, not cited
- `--report`: CONFLUENCE-EXPIRY still the gate doing work (blocked 11,556, would_win 48%, avg −0.12)
- `--analyze-hml`: worst shadow names (`open-skies+` 41T 12.2%, `grind-breakout-v2+` 45T 20%) have
  **n≤2 live trades** — shadow-only, zero live impact. Do not chase.

## LAST-RUN VERIFY — all PASS
cluster_risk_limiter `--selfcheck` ASSERT PASS · arm_gap_baseline `--selfcheck` PASS ·
**pm_armed_at 1/1** armed trade since the 13:50 ship (16418 USUAL) · **profit-monster GC canary 0**
(the 6 `Profit monster closing` hits are all 2026-10-21→10-23, i.e. pre-ship) ·
daily_git_commit guard present (12 refs) · constants working-tree diff **EMPTY** ·
kill leaks **0** (doji last open 10-16 17:43 = kill time; ai-trader+ last open 10-19 09:23) ·
`BB_BOUNCE_TRAIL_ARM_TIMEOUT_ENABLED=True` · size-reduce ABSENT = 1.0x · session lock absent.

## WATCHDOG
**0 steers, portfolio health good, 0 open — flat is correct** (CHOP, LOW vol, 15m LONG_BIAS vs 4h
SHORT_BIAS, market_phase DECLINING, trend_quality STRONG_UP on a DECLINING phase = mixed). Last cycle's
cluster steer was closed REJECTED-WITH-DATA and no run has chased one since. Auto-trader is shadow
BRACKET in CHOP: its long side is 0/8 (`−$0.17`) vs short 4/7 (`+$0.14`), n=15 — same wrong-side
reading as pump-chain-, at book scale.

**24h 30T 14W 46.7% `−$0.55` = REDDEST today** (neg streak 2h, not yet 3). 7d 136T `−$0.62` ·
14d 336T `−$4.71` · 30d 721T `−$2.54`.

## NEXT
1. **2026-10-27T00:00Z** waiver LAPSE verify + `[35,45)` mid-band re-measure (#139)
2. **2026-10-27T17:12Z** pump-chain- PROMOTE formal re-verify — all legs pass, ship only at/after the date,
   and put the classifier-vs-live-exit caveat in the package
3. **2026-10-27** CHASE_RATIO_SHADOW review date
4. 2026-10-27+ ARM-GAP on the re-based bar (n≥30) · 10-30 momentum time-stop blind run ·
   10-31 short-supply on `t_CR>=2`
5. **Nov 15** floor_admit + wyckoff outcome joins — largest queued shadow ROI
6. **CEO:** CONF_FLOOR fkB · ARM-BE-STOP GO · escalation #17 (slice delivered this run) ·
   identify the 02:19:30 constants writer · LOSERS set EMPTY · ai-trader-pending (n=16, quiet since Oct 24)
7. **STOP:** entry-feature/armed-separation (6th null), oscillator outcome join (structural),
   re-testing the 6 exit-ladder families closed above
