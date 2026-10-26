# Current State — brain_auditor #165 2026-10-26 18:00 UTC
**Last Updated: 2026-10-26 18:00 UTC**
**Updated by: brain_auditor #165. Prior: #164 15:45 / #163 14:55 / #162 13:50 (preserved in git history).**

## HEADLINE — phantom-MFE class CLOSED at both call sites. 0 trading-constant changes, 1 live-code ship.
An unlogged 17:03 session left a live exit-behavior fix uncommitted on the phantom-MFE bug class
(ETH #16421 ugb_pt exit 1.45s after open: creation seed 2301.98 vs HL entry 2312.60 read as
phantom +0.459% fav = UGB-PT arm). Run #165 adopted it: selfcheck 18 PASS, bug_hunter
**SHIP-WITH-FIXES** (3 MED + 4 LOW), MEDs applied, committed `41510fe9`, **guardian restarted
17:56:35** (daemon predating the fix would have ImportError'd forever), selfcheck now 19/19.

| bug_hunter finding | disposition |
|---|---|
| MED1 mirror-fill writeback same class (guardian:2910) | FIXED — re-anchor added |
| MED2 guardian daemon started Oct 23 = fix not live | FIXED — restarted post-commit |
| MED3 historical mfe contamination (~3 rows mfe>=0.40/30d) | PRE-REGISTERED backfill, dry-run next run |
| LOW tx-abort from extra SELECT | FIXED — peaks folded into original SELECT |
| LOW direction-pick on side-correction | FIXED — both columns re-anchored |
| LOW#5 orphan-dup close path | ACCEPTED data-quality-only (closes same cycle) |
| LOW bounded legitimate-peak loss | no change (conservative direction) |

`hermes_constants.py` working-tree diff **EMPTY** · CEO_PROTECTED untouched · session lock
**absent** · size-reduce **ABSENT = 1.0x**.

## MANDATE — CHOP vs TREND (fresh PG, 14d 336T 38.4% `-4.71`)
- exits: **profit-monster-trail 83T 91.6% `+4.58`** + atr_trail 24T `+3.47`
  vs atr_sl_hit 80T 1.3% `-5.57` vs hard_max_loss 63T 0.0% `-6.41`
- **armed(mfe>=0.40) 165T 70.3% `+8.40`** vs **unarmed 171T 7.6% `-13.11`**
- MFE ladder monotone: `<0.15` `-7.60` (14d) / `-18.24` (30d) · `>=0.40` `+8.56` / `+26.20`
- chop-bleed never-armed share 7d 86.1% = baseline band (70-92), no breach, no exit-layer action

Trend side healthy. Addressable bleed unchanged = never-had-a-move cohort (entry quality).

## LOSING AUTOPSY — WRONG-SIDE REFUTED **89th** CONSECUTIVE RUN
`recovery_replay.py` adverse-first (`--selfcheck` PASS): **48h n=17** = 5 never-adverse /
10 recovered / **2 NEVER** (16409 ICP waiver-band, 16423 CC pump-chain-) · **14d 194 losers
= 37 / 128 / 29 NEVER = 15.0%** structural (17.5% Oct-22 baseline). Surviving refs: `#61`
p=0.116, `#84` t=-0.04. Steer-001 "wrong-side" REFUTED-STANDS; steer-002 ai-trader+
streak STALE (disabled CEO 10-19).

## SHADOW — one useful source, four dead/pending
- **contrarian 894 rows** = only ship-eligible collector (pc- flip 64.7% n=348 p<1e-4, OOS
  both halves; btc-pump-rider+ do-not-flip control) — **PROMOTE date-locked 10-27T17:12Z**
- oscillator FROZEN (0/24,598 outcome) · floor_admit 2,117 + wyckoff 332 pending Nov 15 ·
  rr_shadow orphaned
- `--report`: CONFLUENCE-EXPIRY 11,622 blocked @48% avg -0.12 = gates earning keep;
  exit A/B pm_trail +3,573 vs hard_max -5,350

## LAST-RUN VERIFY (#164) — all PASS
exit_ladder_oos selfcheck 5/5 · arm_gap_baseline selfcheck PASS (re-based n=17<30, collecting) ·
cluster_risk_limiter selfcheck PASS · pm_armed_at 1/1 (16418 USUAL; no new arms since = chop) ·
PM GC canary 0 post-ship skips · daily_git_commit guard present · constants EMPTY ·
kill leaks 0 · BB_BOUNCE_TRAIL_ARM_TIMEOUT True · size-reduce ABSENT = 1.0x.

## WATCHDOG (17:45)
**6 steers (2 top-level, both triaged above), 4 open — 3 pump-chain+ / 1 rider LONGs opened
17:13-17:44 at conf 29.5-31.1** (CONF_FLOOR=30 staged NOT in tree = expected admits).
Regime flipped again: LONG_BIAS 15m / SHORT_BIAS 4h / continuum AT / RECOVERY / STRONG_DOWN
quality = flip-rate p50 (~1h half-life), not a finding. 24h 28T 46.4% `-0.59`.

## NEXT
1. **2026-10-27T00:00Z** waiver LAPSE verify + `[35,45)` mid-band re-measure (#139)
2. **2026-10-27T17:12Z** pump-chain- PROMOTE formal re-verify — classifier-vs-live-exit
   caveat MANDATORY in package; do NOT ship early
3. **2026-10-27** CHASE_RATIO_SHADOW review · historical mfe phantom backfill dry-run
4. 10-30 momentum time-stop blind · 10-31 short-supply t_CR>=2 · Nov 1 coin_regime OOS
5. **Nov 15** floor_admit + wyckoff outcome joins
6. **CEO:** CONF_FLOOR fkB · ARM-BE-STOP GO · escalation #17 · 02:19:30 constants writer ·
   LOSERS EMPTY · ai-trader-pending dead cohort
7. **STOP:** entry-feature scans (6th null), oscillator join, exit-ladder 6 families,
   direction-mix levers, cluster limiters
