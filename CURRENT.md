# Current State — brain_auditor #149 2026-10-25 23:58 UTC
**Last Updated: 2026-10-25 23:58 UTC**
**Updated by: brain_auditor #149. Prior: #148 22:50 / #147 20:55 (preserved in git history).**

## HEADLINE — 0 trading-constant changes, 0 ships, 3 creative items (1 measured-and-REJECTED, 1 zero-code KPI, 1 CEO scope caveat)

**1. ARM-LINE SWEEP = REJECTED-WITH-DATA (the mandated creative item).**
Hypothesis: the near-arm cohort (max-MFE in [0.30,0.40)) never arms and rides to the stop —
7d 8T `-$0.36` | 14d 25T `-$1.95` | 30d 49T `-$3.33`, same-sign every window. Swept ARM
0.20 / 0.30 / 0.40 / 0.50 % with D locked at the pre-registered 0.20%, BOTH scopes (all trades +
the #135 scope the pending D=0.20 GO ask was measured on), plus a paired per-trade
delta(ARM)-delta(0.40) test with an old/new half split. **Every arm fails the locked ship bar:**
- ARM 0.30 paired: all-scope 14d `+1.226` p=0.0198 (old half `+0.808` p=0.049) but
  **30d `+0.862` p=0.295 with OLD HALF `-0.180`**; scoped 14d p=0.273 / 30d p=0.322.
- ARM 0.20 paired: **30d old half `-1.156` (all) / `-0.387` (scoped)** — negative OOS.
- ARM 0.50 fails same-sign.
- The whole lower-ARM edge lives in the NEW half and reverses out-of-sample. The absolute
  bars that "pass" are inherited from the baseline, which passes the same cells.
Collisions named: `PM_TRAIL_ACTIVATE_PCT` is CEO_PROTECTED ("MUST BE 0.40% DO NOT CHANGE"),
and the in-flight TAT-C tripwire predicate is `live_pnl < PM_TRAIL_ACTIVATE_PCT` — changing
the arm line mid-flight would confound that eval. **Verdict: do not re-propose lower ARM.**
Script `brain/analysis/arm_sweep_oos_2026-10-25.py` (--selfcheck 5 asserts PASS, --verdict
exit 2 = rejected).

**2. SCOPE CAVEAT for the pending D=0.20 post-arm floor CEO GO (NEW side-find).**
The published absolute bars reproduce on the pre-registered #135 scope (14d PASS / 30d PASS)
**but not on the whole book**: unscoped ARM=0.40 30d net `+3.659` with **p=0.2149** and older
half only `+0.398` of `+3.659` = **89% of the edge sits in the newest 15d**. Scope was
pre-registered so this is a caveat, not a refutation — the CEO should see it next to the GO.

**3. MFE-BUCKET LEDGER (zero-code KPI, adopted this run).** 14d net by max-MFE bucket is
monotone: `<0.20` = `-$8.72` | `0.20-0.40` = `-$4.29` | `0.40-0.80` = `+$0.98` | `>=0.80` =
`+$7.48`. Read it beside the never-armed share as the arm-quality KPI.

## MANDATE — CHOP vs TREND (fresh, PG this run)
- TRAIL/TP 14d **124T 111W +$10.58** vs CHOP/STOP **190T 6W -$14.99** | 7d **60T 53W +$4.16** vs **62T 2W -$4.92**
- trail family 14d by exit: PM-trail 82T 75W `+$4.53` + atr_trail 25T 20W `+$3.56` + rr_trail `+$0.54` + trail_sl `+$0.69` = **116T +$9.32**
- chop exits 14d: hard_max_loss 67T 0W `-$6.52` + atr_sl_hit 79T 1W `-$5.63` = **146T -$12.15**
- armed 7d **62T 71.0% +$3.23** vs unarmed **57T 7.0% -$4.17** | 14d 154T `+$8.46` vs 165T `-$13.01` | 30d 391T `+$25.40` vs 290T `-$28.01`
- never-armed share of gross loss: **7d 80.7% | 14d 83.5% | 30d 79.5%** (band 70-92, no breach)

## LOSING AUTOPSY — WRONG-SIDE REFUTED 73rd CONSECUTIVE RUN
`recovery_replay.py` adverse-first (--selfcheck PASS): **24h n=6 = 4 never-adverse / 2 recovered / 0 NEVER**;
**48h n=9 = 5/3/1** (the 1 = BTC #16377 ai-trader-pending manual_sl `-$0.08`, CEO, immaterial);
**14d n=192 = 38/125/29** (15.1% structural never-recover = re-enter-on-recovery Oct 27).
All 6 24h losers were mid-band LONGs into a SHORT_BIAS tape (ICP chased RSI 72.73) = chop.
Refs that survive: #61 p=0.116, #84 t=-0.04.

## LAST-RUN VERIFY — ALL PASS
#147 session_brain dedup **confirmed in live use** (3 Step-2 probes, 6/6 unique titles each) |
#146 conf_field_semantics + fk_definitions section present (fk table re-run this run, byte-identical) |
#144 price-feed **HOLDING** (latest_prices 267 rows, newest **0.14 min**, PENDLE 1.95575 = correct,
timer 23:52:25Z; 24h soak due **Oct 26 17:42**) | #145 TAT-C tripwire 3 attributed fires, n=10 not reached |
#148 mfe backfill due **Oct 26 00:20 UTC** (armed=None 12T 14d still present, self-heals as predicted) |
kill flags correct, **0 post-kill opens** | constants EMPTY git diff | CEO_PROTECTED **13/13** |
size-reduce file absent = 1.0x | session lock absent | **0 new Tracebacks 2026-10-25**
(pipeline.log 5 total, latest 03:00:00 = known weekly self-healing, triaged #137).

## PRE-REG RECHECKS
- **CONF_FLOOR fk repro EXACT**: blocked 36T 7W `-$1.48` | fkA-literal 5.6% PASS | **fkB 19.4% PASS**
  (bar 20, margin 0.6pts) | fkA-family+scope 35.0% FAIL | **decay trigger: 7d blocked cohort 12T 3W `-$0.39`
  = still negative -> ship stands.** Ruling + site-lock after decider_run.py:4856 + ship-time
  blocked-count self-check remain CEO time-critical.
- pump-chain+ NO-KILL stands (30d `+$1.84`); pump-chain- Oct-27 PROMOTE stands (flip 64.2% n=344, re-verified).
- 0 new sub-50% n>=15 targets; 0 post-kill leaks; 0 pump-chain HIGH leaks after the 2026-10-21 03:38 block.

## SHADOW (2/5 answerable)
contrarian join RE-RAN 814/542 — **pump-chain- flip 64.2% n=344 STANDS**, btc-pump-rider+ 24.9%
do-NOT-flip, total 49.8% family-specific | shadow_trader **22,406 signals** — gates justified
(CONFLUENCE-EXPIRY 10,857 @48% avg `-$0.12`, EXEC-BLOCK 16 @12% best, BTC-CRASH 116 @31%),
exit A/B pm_trail `+$3,139` vs hard_max `-$4,790` | oscillator FROZEN / wyckoff+floor PENDING / rr ORPHANED.

## READINESS — 0 open, flat = CORRECT
CAKE #16404 SHORT volume-buildup- `+$0.03` (23:35) and ANIME #16403 SHORT volume-buildup- `+$0.02`
(23:34) both trailed winners; book is now 0 open. Regime: **btc_15m + btc_4h both SHORT_BIAS (now
aligned)**, continuum BELOW, volatility LOW, zscore **STRONG_NEG**, acceleration NEGATIVE, volume LOW,
trend_quality STRONG_DOWN. SHORT side is the aligned side; LONGs only on a sustained EMA300 reclaim
WITH volume; mid-band = no trade; size 1.0x.

## SIDEWAYS FIND (LOW)
trade_watchdog agent queries a non-existent `take_profit` column (correct = `target`) — 2 fresh
tracebacks in logs/trade-watchdog.log today, wasted cycles. Add to the prompt SQL cheat-sheet.

## QUEUE
- **CEO (time-critical):** CONF_FLOOR fk-definition ruling (fkB 19.4% vs 20) + decay trigger +
  site-lock after :4856 + blocked-count self-check.
- **CEO:** D=0.20 post-arm floor GO — with this run's scope caveat (passes pre-registered scope,
  unscoped 30d p=0.215, 89% of edge in newest 15d).
- **Oct 26 00:20Z:** mfe backfill clears armed=None. **Oct 26 17:42Z:** price-feed 24h soak.
- **Oct 27:** unclog waiver expiry + contrarian pump-chain- PROMOTE + waiver scoreboard + #139 re-measure.
- **Nov 1:** coin_regime ALIGNED/COUNTER 14d OOS. **Nov 15:** floor_admit 30d same-sign.
- **Monitor:** bb-bounce 7d 20T 45% (kill WR bar <30% not met, TAT-C owns) | hl_copy 12T n<20.
- **MED:** add `target` (not `take_profit`) to the watchdog prompt SQL cheat-sheet.

Artifacts: brain/audit_recommendations.json, brain/creative_improvements.json, brain/changes_log.json,
brain/analysis/arm_sweep_oos_2026-10-25.py (+ .out and _scoped.out), CURRENT.md.
