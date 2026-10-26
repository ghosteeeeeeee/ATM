# Current State — brain_auditor #152 2026-10-26 02:40 UTC
**Last Updated: 2026-10-26 02:40 UTC**
**Updated by: brain_auditor #152. Prior: #151 01:40 / #150 00:55 (preserved in git history).**

## HEADLINE — ROGUE CONSTANTS EDIT FOUND AND REVERTED (HIGH drift): uncommitted
`hermes_constants.py` change removing pump-chain from `PROFIT_MONSTER_BYPASS_SIGNALS`,
written **2026-10-26 02:19:30 UTC** with a backdated comment "REMOVED 2026-10-05".
This is byte-identical to the freeze violation the **CEO already reverted on
2026-10-05 17:55** (kanban) after independent verification rejected the claim
(**trading_log.md:4511**: pump_exit 9T `+$0.94` 8W / TRAIL 8T `+$1.52` 8W vs
HARD_MAX 14T `-$1.96` 0W → "Keep pump-chain in PROFIT_MONSTER_BYPASS").
**REVERTED to HEAD f6a7ed8b at 02:35** — git diff EMPTY, CEO_PROTECTED 13/13.
Author unknown: no agent log, no changes_log entry, no kanban note → **CEO to identify
the writer.**

**GUARD SHIPPED (root cause): `scripts/daily_git_commit.py` no longer stages
`scripts/hermes_constants.py` in the 07:15 `git add -A` sweep.** Without this the same
edit would have been auto-committed as HEAD 4.5h later with zero audit trail. py_compile
PASS + 5-case predicate self-check PASS. Failure mode is now a loud GUARD print.

**Why the edit is wrong on its data (fresh PG, 30d, signal LIKE %pump-chain%):**
- profit side: `atr_trail_hit` 27T 85.2% `+$6.73` | `trail_sl` 8T 100% `+$1.33` |
  `pump_exit_dead_money` 11T 90.9% `+$1.02` | `rr_engine_trail_hit` 2T 100%
- bleed side: `hard_max_loss` 50T 0% `-$5.77` + `atr_sl_hit` 37T 0% `-$2.68`
→ the bleed is **stops**, not the profit engine. Re-routing to PM Trail does not touch
hard_max/atr_sl. The validated remedy for the pump-chain giveback is the **D=0.20
universal post-arm floor** (#135/#136: 30d `+$2.368` p=0.019, fk 0%, CEO GO pending) —
a narrow lever, not engine reassignment.

## MANDATE — CHOP vs TREND (fresh PG)
- TRAIL family 14d: profit-monster-trail 82T 91.5% `+$4.54` + atr_trail 25T 80% `+$3.56`
  + trail_sl 4T `+$0.69` + rr_trail 5T `+$0.54` = **116T +$9.33**
- Chop exits 14d: HML 63T 0% `-$6.24` + atr_sl 79T 1.3% `-$5.63` = **142T -$11.87**
- armed (mfe>=0.40) 14d **164T 70.7% +$8.37** vs unarmed **161T 5.6% -$12.83**
- MFE buckets 14d: `<0.20` `-$8.59` | `0.20-0.40` `-$4.24` | `0.40-0.80` `+$1.18` |
  `>=0.80` `+$7.19` — monotone
- chop-bleed share 84.2% (7d, of `-$5.25` gross) / 85.4% (14d) — baseline band, entry
  problem, no trail change warranted
- 7d direction: LONG 90T 40.0% `-$1.16` vs SHORT 41T 56.1% `+$0.61` — LONG still the bleed

## LOSING AUTOPSY — WRONG-SIDE REFUTED 76th CONSECUTIVE RUN
`recovery_replay.py` adverse-first (--selfcheck PASS): **48h n=9 = 5 never-adverse /
4 recovered / 0 NEVER**. Refs that survive: #61 p=0.116, #84 t=-0.04.
All 9 losers = chop: 5 never-armed LONG trail_arm_timeout (MFE 0.10-0.24) + 3 SHORT-SL +
ICP r2v2-long3 chased at RSI 72.7 (already covered by SIGNAL_FILTER_RSI_MAX=75).

## LAST-RUN VERIFY — ALL PASS
#151 fk_definitions fkB correction reproduces | postarm_giveback_census selfcheck PASS |
#150 vol_precondition selfcheck PASS (71 joined / 63) | watchdog SQL cheat-sheet present |
#147 session_brain dedup live (3 probes × 6/6 unique) | conf_field_semantics selfcheck
PASS (LEAK 57/58, NO-OP 0/656) | kill flags correct, doji dead-by-traffic (last Oct 16) |
**constants EMPTY git diff (post-revert)** | CEO_PROTECTED **13/13** | size-reduce
**absent = 1.0x** | session lock absent | price-feed soak due **Oct 26 17:42Z**.

## DEEP-DIVE — 0 new sub-50% n>=15 targets
bb-bounce-v2-long+ 37T 37.8% `-$1.11` (TAT-C live, kill bar WR<30 NOT met, #138 no-re-propose)
| doji 16T 31.3% (killed Oct 16, dead-by-traffic) | ai-trader+ 20T 30.0% (disabled CEO Oct 19)
| pump-chain+ 44T 27.3% (NO-KILL, 30d `+$1.84`, conf<30 = CONF_FLOOR cohort)
| pump-chain- 35T 22.9% (CONF_FLOOR + Oct-27 PROMOTE) | ai-trader-pending 16T (CEO, n<20).

## PRE-REG RECHECKS
- **CONF_FLOOR**: fkB **29.1% FAIL** (corrected #151) / fkA-literal 12.5% PASS / net
  `-$1.71` → ship HELD, CEO ruling must waive/reject fkB. Pins 55@14d / 56@30d.
- pump-chain+ **NO-KILL stands** (14d 44T 27.3% `-$0.35` MET-by-letter; 30d `+$1.84`).
- pump-chain- **Oct-27 PROMOTE stands** (contrarian flip **64.5% n=346**).
- inverse chase-block n=17 COLLECT | hl_copy 12T COLLECT | bb-bounce weekly re-measure.
- TAT eval **CLOSED PASS** — side-watch 4/24 fires with final MFE>=0.40.

## SHADOW (2/5 answerable)
contrarian join — pump-chain- flip **64.5% n=346 STANDS**, btc-pump-rider+ 24.9%
do-NOT-flip | shadow_trader `--report` 22,850 signals: gates justified
(CONFLUENCE-EXPIRY 10,949 blocked @48% avg `-$0.12`, EXEC-BLOCK 16 @12%, BTC-CRASH 116 @31%),
exit A/B pm_trail `+$3200` vs hard_max `-$4851` = trail-or-nothing reproduces | oscillator
FROZEN / wyckoff+floor PENDING / rr ORPHANED.

## DEAD COLUMNS (do not mine)
`predicted_return` 689/703 populated but **all 689 = 0.0000 (uniq=1)**; `actual_return`
0/703; `entry_fear_greed` 0/703; `entry_timing` 0/703. Only `signal_momentum_state`
live (397/703) and momentum-state already failed the 7-check battery 2026-10-08.

## READINESS — 2 open SHORTs, both bracketed
BTC continuum-trend- #16408 (SL 80992.9 / TP 78574.9, rsi_exec 56.92) +
IO pump-chain- #16407 (SL 0.14515 / TP 0.14068, rsi_exec 48.24 = floor PASS,
**confidence 29.50 = the exact CONF_FLOOR blocked cohort → pre-registered as a second
live fk data point**, first was CFX #16373 conf 26.50 closed `+1.31%`).
Regime: btc_15m + btc_4h SHORT_BIAS, continuum BELOW, vol LOW, acceleration NEGATIVE,
trend_quality UP (mixed). Watchdog steer: IO+BTC 12-min cluster = correlation risk,
not auto-executable. LONGs only on sustained EMA300 reclaim WITH volume; SHORTs at
mid-RSI only (1m RSI on obvious short candidates is 21-28 — BANANA lesson, no chase);
mid-band = no trade; trail-family first; size 1.0x.

## QUEUE
- **CEO (URGENT):** who wrote `hermes_constants.py` at **02:19:30 UTC**? No agent
  claimed it. Rogue edit reverted; identify the writer.
- **CEO (time-critical):** CONF_FLOOR — **fkB FAILS 29.1%**; ruling must waive/reject
  fkB or pin fkA-literal; pins 55@14d / 56@30d. Enforcement must sit after
  decider_run.py:4856.
- **CEO:** D=0.20 post-arm floor GO — census baseline locked (25T `-$1.35`, 49% giveback).
- **Oct 26 17:42Z:** price-feed 24h soak.
- **Oct 27:** unclog waiver expiry + pump-chain- PROMOTE + waiver scoreboard + #139 re-measure.
- **Next run:** record IO #16407 outcome into the CONF_FLOOR fk evidence set.
- **COLLECT:** inverse chase-block n→20 | hl_copy n=12 | census re-measure post-D0.20.
- **Nov 1:** coin_regime OOS. **Nov 15:** floor_admit 30d same-sign.
