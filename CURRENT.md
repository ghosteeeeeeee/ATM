# Current State — brain_auditor #151 2026-10-26 01:40 UTC
**Last Updated: 2026-10-26 01:40 UTC**
**Updated by: brain_auditor #151. Prior: #150 00:55 / #149 23:58 (preserved in git history).**

## HEADLINE — CONF_FLOOR fkB CORRECTION: sanity bar actually FAILS at 29.1% (#150 said "12.6% comfortable" — that number was fkA-literal mislabeled); 0 constants changes; 1 doc correction ship; TAT eval CLOSED PASS

**1. CONF_FLOOR fk table CORRECTED (brain/fk_definitions.md).** Fresh PG: blocked set
55T 16W `-$1.71` reproduces. **fkB = 16/55 = 29.1%** (all-signal) / **20.5%**
(pump-chain-only) — BOTH ≥20% bar = **FAIL**. fkA-literal = 16/128 = **12.5%** PASS
(#150's "fkB 12.6%" was this number mislabeled; blocked winners grew 4→16 which pushed
real fkB 12.5%→29.1%). 30d: fkB 28.6% FAIL / fkA-literal 5.2% PASS. Net EV still
positive (+$1.71/14d) but the pre-registered sanity bar is a hard gate — **ship stays
HELD; CEO ruling must now explicitly waive/reject the fkB FAIL, not just pin a
denominator.** Ship-time blocked-count pins: **55@14d / 56@30d** (33@14d stale).

**2. TAT EVAL CLOSED — PASS, keep as-is (threshold 15 crossed at 23 fires, now 24).**
14d fires 24: **20/24 (83%) MFE<0.40** = correct stall cuts. TAT avg exit `-$0.032`
vs HML avg `-$0.098` (same never-armed class, 3x better exit). bb-bounce variant-C
4 fires `-$0.14` (working, post-#117 HBAR proof). Side-watch: **4/24 fires had final
MFE≥0.40** (BLUR 1.33, APT 0.83, ADA 0.39-ish edge) = peak decayed through the
PM-exempt pump-exit engine into TAT — monitor, same class the D=0.20 floor would catch.

**3. CREATIVE SHIPPED: post-arm giveback census baseline (zero code).**
`brain/analysis/postarm_giveback_census_2026-10-26.py` (--selfcheck PASS):
PM-exempt (pump-chain) reached-arm→stop-exit cohort **14d 25T `-$1.35` avg_mfe 0.771,
49% of armed exits hit a stop not a trail**; 7d 7T `-$0.44` 63.6%. Pre-registered
success bars for the D=0.20 CEO GO: 7d cohort net improves same-sign, cohort size
shrinks, no offsetting premature-exit rise. Ships the "measure before/after" so the
floor GO is validated, not hoped.

## MANDATE — CHOP vs TREND (fresh PG)
- TRAIL family: profit-monster-trail 83T 91.6% `+$4.56` + atr_trail 25T 80% `+$3.56`
- Chop exits: HML 65T 0% `-$6.35` + atr_sl 79T 1.3% `-$5.63`
- armed 14d **166T 71.1% +$8.96** vs unarmed **164T 6.1% -$12.92**
- MFE buckets 14d: `<0.20` `-$8.63` | `0.20-0.40` `-$4.29` | `0.40-0.80` `+$1.20` | `>=0.80` `+$7.76`
- chop-bleed share 84.2% (7d) / 85.5% (14d) — inside baseline band, entry problem
- 7d direction: LONG 90T 40% `-$1.16` vs SHORT 41T 56.1% `+$0.61` — LONG still the bleed

## LOSING AUTOPSY — WRONG-SIDE REFUTED 75th CONSECUTIVE RUN
`recovery_replay.py` adverse-first (--selfcheck PASS): **48h n=9 = 5 never-adverse /
4 recovered / 0 NEVER**. Refs that survive: #61 p=0.116, #84 t=-0.04.

## LAST-RUN VERIFY — ALL PASS
#150 vol_precondition selfcheck PASS + re-run (inverse n=17 still COLLECT) |
watchdog SQL cheat-sheet present (:76) | #144 price-feed soak due **Oct 26 17:42Z** |
#147 session_brain dedup live (3 unique probes) | kill flags correct, doji
dead-by-traffic (last Oct 16) | vb- 7d 19T 73.7% `+$0.43` = revert criterion NOT hit |
constants **EMPTY git diff** | CEO_PROTECTED **13/13** | size-reduce **absent = 1.0x** |
session lock absent | selfchecks PASS.

## PRE-REG RECHECKS
- **CONF_FLOOR**: fkB **29.1% FAIL** (corrected) / fkA-literal 12.5% PASS / net `-$1.71`
  holds → ship HELD, CEO ruling now includes explicit fkB waive/reject.
- pump-chain+ **NO-KILL stands** (14d 45T 26.7% `-$0.36` MET-by-letter; 30d 71T `+$1.84`).
- pump-chain- **Oct-27 PROMOTE stands** (contrarian flip **64.5% n=346**, re-verified).
- inverse chase-block n=17 COLLECT | hl_copy 12T COLLECT | bb-bounce weekly re-measure.
- TAT eval **CLOSED PASS** (see above) — no further eval scheduled unless fires double.

## SHADOW (2/5 answerable)
contrarian join **816/544** — pump-chain- flip **64.5% n=346 STANDS**, btc-pump-rider+
24.9% do-NOT-flip, total 50.0% family-specific | shadow_trader: hard_max simulated
`-$4834` vs pump_exit `+$82.79` = trail-or-nothing reproduces | oscillator FROZEN /
wyckoff+floor PENDING / rr ORPHANED.

## READINESS — 0 open = CORRECT
CHOP / STRONG_DOWN / LOW vol; sources disagree (15m LONG_BIAS vs 4h SHORT_BIAS).
SHORTs aligned (volume-buildup- 6T 100%WR `+$0.20` in 24h = keep fed). LONGs only on
sustained EMA300 reclaim WITH volume; mid-band = no trade; trail-family first; size 1.0x.

## QUEUE
- **CEO (time-critical, UPDATED):** CONF_FLOOR — **fkB FAILS 29.1%**; ruling must
  waive/reject fkB or pin fkA-literal headline; pins 55@14d/56@30d.
- **CEO:** D=0.20 post-arm floor GO — census baseline locked (25T `-$1.35`, 49% giveback).
- **Oct 26 17:42Z:** price-feed 24h soak.
- **Oct 27:** unclog waiver expiry + pump-chain- PROMOTE + waiver scoreboard + #139 re-measure.
- **COLLECT:** inverse chase-block n→20 | hl_copy n=12 | census re-measure post-D0.20.
- **Nov 1:** coin_regime OOS. **Nov 15:** floor_admit 30d same-sign.
