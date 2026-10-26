# Current State — brain_auditor #166 2026-10-26 18:55 UTC
**Last Updated: 2026-10-26 18:55 UTC**
**Updated by: brain_auditor #166. Prior: #165 18:00 / #164 15:45 (preserved in git history).**

## HEADLINE — loss-cooldown ladder was half-dead. Fixed + SHIP verdict.
`brain._record_loss_cooldown` wrote `reason='brain'` but
`signal_schema._is_loss_cooldown_active` only honors `('loss','guardian')` —
every brain-closed loss recorded a cooldown the decider could never see
(dead since 2026-04-28). Fixed: `reason -> 'loss'` (`scripts/brain.py:55`,
canonical like position_manager/guardian/pipeline). 4-check selftest PASS
(write→check→dedup→cleanup). bug_hunter **SHIP** (10 findings).

**3 pre-existing MEDs TICKETED (CEO queue, not shipped — one variable at a time):**
- **F1** `position_manager.close_paper_position` calls `set_loss_cooldown` TWICE
  per loss close (:1253 + :1594; log-proven streak 1→2 within 3s) — remove one.
- **F2** guardian locks `FileLock('loss_cooldown')` vs `'loss_cooldowns'` elsewhere
  = writes not mutually exclusive.
- **F3** `signal_schema.set_cooldown` clobbers active `reason='loss'` entries with
  `'signal'` (invisible downgrade).

`hermes_constants.py` working-tree diff **EMPTY** · CEO_PROTECTED untouched ·
session lock **absent** · size-reduce **ABSENT = 1.0x**.

## WATCHDOG QUEUE — all 4 items dispositioned
1. **'Floor leak 6/14 shorts RSI 36-40' = RESOLVED-NO-BUG.** Those values are
   `rsi_detect`; floor checks BOTH detect+exec (2026-10-13 detect-floor fix live).
   Clears via unclog waiver bear-exemption (T directive 10-24, expires tonight
   00:00Z). Working as designed.
2. **#139 mid-band [35,45) RE-MEASURE (early): exec-band 7d n=16 9W/7L +$0.09
   NEUTRAL (p=0.40).** Blocking kills +$0.86 trail winners vs -$0.77 chop losers;
   8/9 winners volume-buildup- PM-trail. **RECOMMEND: let waiver LAPSE at
   00:00Z as pre-registered**; if T/CEO extends, scope to volume-buildup- only.
3. **pump-chain+ CONFIRMED worst** 7d 18T -1.08 33.3%: armed 8T +$0.04 75%WR /
   unarmed 10T -$1.12 **0%WR**. Winner/loser detect-RSI indistinguishable
   (56.0/57.5) = entry-scan banned → 10-30 time-stop blind + hard-stop reentry.
4. **bb-bounce-v2-long+ CONFIRMED** same shape (armed +$0.34 / unarmed -$0.71,
   all NORMAL). CEO-flagged 13:28, TAT-C-owned, no new lever.

## CREATIVE → PROPOSED_TO_CEO — HARD_STOP re-entry cooldown 4-8h
After hard_max_loss/hard_sl exits (ladder caps at 90min today).
30d PG census: re-entry within 8h after same-coin hard stop =
**n=37 10W 27.0%WR vs 45.0% base, z=-2.14 p=0.032 SIG**; 14d OOS n=18 16.7%WR
holds; net **+$1.18** if blocked (saves $2.23 losers / kills $1.05 winners =
3.1% of winners). Chop-begets-chop (BLUR 5T -$0.61; LDO/ALGO/JUP clusters).
Path: shadow→enforce via review queue AFTER #166 restore proves live.

## LOSING AUTOPSY — WRONG-SIDE REFUTED **90th** CONSECUTIVE RUN
`recovery_replay.py` adverse-first (selfcheck PASS): 48h n=17 = 5 never-adverse /
10 recovered / **2 NEVER** (16409 ICP waiver-band, 16423 CC pump-chain-) ·
14d 194 losers = 37/128/**29 NEVER = 15.0%** structural.
Surviving refs: `#61` p=0.116, `#84` t=-0.04.

## SHADOW
- **contrarian** join re-ran: pc- flip **64.7% n=348 STABLE**, rider control 28.6%
  = 10-27T17:12Z PROMOTE STANDS, do NOT ship early
- `--report`: CONFLUENCE-EXPIRY 11,659 @48% avg -0.12 = gates earning keep;
  exit A/B pm_trail +3,594 vs hard_max -5,371
- oscillator FROZEN · floor_admit+wyckoff PENDING Nov 15 · rr ORPHANED

## LAST-RUN VERIFY (#165) — PASS
guardian **STILL LIVE** (hl-sync-guardian PID 3491810, started 17:56:35 = the
post-phantom-MFE-fix restart; timer last fired 17:56). Fix intact.

## PG fresh (18:55)
24h 30T 46.7% **-0.92** · 7d 139T 44.6% **-0.95**
(worst: pump-chain+ 18T -1.08 33.3% / bb-bounce-v2 18T -0.37 33.3%)
· armed 7d both worst families: 75%WR vs unarmed 0%WR

## READINESS
1 open RENDER #16425 LONG rider+r2 @1.7388 bracketed (SL 1.7243/TP 1.7825) 1.4h
flat. BLUR #16428 closed hard_max_loss -0.31 (watchdog steer correct but late —
full stop donated; family = chop-bleed pattern). Regime CHOP: 15m LONG_BIAS /
4h SHORT_BIAS disagree = flip-rate p50. No new LONGs while BTC below EMA300
80259 with aggregate SHORT_BIAS. Trail-family first. **size 1.0x (file absent).**

## NEXT
1. **2026-10-27T00:00Z** waiver LAPSE verify (mid-band done: neutral, lapse stands)
2. **2026-10-27T17:12Z** pc- PROMOTE formal re-verify — classifier-vs-live-exit
   caveat MANDATORY; do NOT ship early
3. **2026-10-27** mfe phantom backfill dry-run · CHASE_RATIO_SHADOW
4. **next run** verify first brain-closed loss writes reason=loss AND blocks
   (end-to-end live proof of #166)
5. 10-30 momentum time-stop blind · 10-31 short-supply t_CR>=2 · Nov 15 joins
6. **CEO:** hard-stop reentry proposal (evidence complete) + MEDs F1/F2/F3 ·
   CONF_FLOOR fkB · ARM-BE-STOP GO · escalation #17 · 02:19:30 constants
   writer · LOSERS EMPTY · ai-trader-pending dead cohort
7. **STOP:** entry-feature scans (6th null), oscillator join, exit-ladder 6
   families, direction-mix levers, cluster limiters
