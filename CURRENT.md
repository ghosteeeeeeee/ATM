# Current State — brain_auditor #150 2026-10-26 00:55 UTC
**Last Updated: 2026-10-26 00:55 UTC**
**Updated by: brain_auditor #150. Prior: #149 23:58 / #148 (preserved in git history).**

## HEADLINE — volume-precondition hypothesis REFUTED-WITH-DATA (it inverted); 0 constants changes; 2 zero-behavior ships

**1. CREATIVE: pump-chain+ volume gate — naive form is a DISASTER, inverse is the real edge.**
Tested the obvious idea: volume-buildup- (only healthy SHORT, 75% WR, arm-rate 78.6%,
volume-native) vs pump-chain+ (zero volume checks). Pre-registered 1.5x 20-bar 5m entry-vol
precondition, 30d, 63/71 joined. **Result inverted the hypothesis:**
- PASS vol>=1.5x: 17T 41.2% armed **23.5% WR -$0.63** (high volume = chasing = bleed)
- BLOCK vol<1.5x: 46T 45.7% armed **39.1% WR +$1.52** (stealth entries win)
- Naive ship would kill **18/22 = 81.8% of winners** → hard reject.
- **INVERSE (block chase entries vol>=1.5x)**: winner-impact 4/22 = **18.2% (<20% bar PASS)**,
  saves +$0.63/30d, but **n=17 < 20 ship bar → COLLECT, re-measure at n>=20.**
Script `brain/analysis/vol_precondition_pumpchain_2026-10-26.py` (--selfcheck PASS).

**2. SHIP: watchdog SQL cheat-sheet (zero-behavior).** `trade_watchdog_prompt.md` gains the
correct open-trade columns — **`stop_loss`, `target`; there is NO `take_profit`** (1,691
UndefinedColumn hits in logs/trade-watchdog.log). Closes #149's MED sideways find.

**3. CONF_FLOOR margins IMPROVED, still HELD for CEO.** Blocked set slid to 55T 16W `-$1.71`
(~90% pump-chain family; volume-buildup- has 0 rows below conf 45). **fkB 19.4% → 12.6%**
(comfortable vs bar 20) | fkA-literal 16.6% PASS | 7d blocked cohort still `-$0.59` = decay
trigger holds. Ship still blocked on: CEO fk ruling + site-lock AFTER decider_run:4856 +
**ship-time blocked-count RECOMPUTE** (fk_definitions pins 33@14d/56@30d are STALE — live is 55@14d).

## MANDATE — CHOP vs TREND (fresh, PG this run)
- TRAIL family 14d **87T 80W 92.0% +$5.25** vs HML **67T 0W -$6.52** (only **1/67** ever
  reached +0.40) + atr_sl_hit 79T 1W `-$5.63`
- armed 14d **141T 78.0% +$8.70** vs unarmed **191T 8.9% -$12.76** | 7d 69T +$3.37 vs 61T -$3.82
- MFE buckets 14d (reproduces #149): `<0.20` **-$8.72** | `0.20-0.40` -$4.29 | `0.40-0.80`
  +$1.19 | `>=0.80` **+$7.76**
- 7d direction: LONG 77T 31W `-$1.12` vs SHORT 34T 16W `+$0.40` — LONG side still the bleed

## LOSING AUTOPSY — WRONG-SIDE REFUTED 74th CONSECUTIVE RUN
`recovery_replay.py` adverse-first (--selfcheck PASS): **24h n=6 = 4 never-adverse / 2
recovered / 0 NEVER**; 48h n=8 = 5/3/**0**. All 6 24h losers mid-band LONGs into SHORT_BIAS
(ICP r2v2-long3 HML, ETH hl_copy, KAS/SAGA TAT, PENDLE ugb, BTC continuum-trend+ atr_sl) = chop.
Refs that survive: #61 p=0.116, #84 t=-0.04.

## LAST-RUN VERIFY — ALL PASS
#149 arm-sweep reject **stands** (PM_TRAIL_ACTIVATE_PCT untouched) + MFE ledger reproduces |
#148 mfe backfill **CLEARED** (armed=None 14d = 0) | #144 price-feed **HOLDING** (267 rows,
newest **0.44 min**, PENDLE 1.96095; soak due **Oct 26 17:42Z**) | #147 session_brain dedup
in live use (3 probes unique) | #146 fk_definitions present (pins stale, see above) |
kill flags correct, 0 post-kill opens | constants **EMPTY git diff** | CEO_PROTECTED **13/13** |
size-reduce file **absent = 1.0x** (auto-clear realized) | session lock absent | **0 new
Tracebacks 2026-10-26**.

## PRE-REG RECHECKS
- **CONF_FLOOR**: fkB 12.6% PASS / fkA 16.6% PASS / decay `-$0.59` holds → **ship stands, CEO time-critical**.
- pump-chain+ **NO-KILL stands** (30d `+$1.84`, conf>=30 30d `+$3.13`; 14d kill-by-letter MET
  but OOS reverses).
- pump-chain- **Oct-27 PROMOTE stands** (contrarian flip **64.3% n=345**, re-verified this run).
- **NEW pre-reg**: inverse chase-block (block pump-chain+ LONG when entry 5m vol >= 1.5x
  prior-20 mean) — re-measure when blocked n>=20 (now 17); bars locked: fk<20%, 30d same-sign,
  winner-impact <20% (currently 18.2%).
- hl_copy 13T n<20 COLLECT | TAT 23 fires/14d (eval threshold 15 crossed — adjudicate next run).

## SHADOW (2/5 answerable)
contrarian join **814/543** — pump-chain- flip **64.3% n=345 STANDS**, btc-pump-rider+ 24.9%
do-NOT-flip, total 49.9% family-specific | shadow_trader HML threshold sim: no change |
oscillator FROZEN / wyckoff+floor PENDING / rr ORPHANED.

## READINESS — 1 open, LONG into SHORT_BIAS = watch closely
ADA #16405 bb-bounce-v2-long+ LONG @0.20455 (SL 0.20230 / TP 0.20769, conf 51, meta_rsi 54.17)
opened 00:12 into **btc_15m + btc_4h both SHORT_BIAS**, continuum BELOW, LOW vol. Bracketed;
TAT-C owns bb-bounce. This is the exact chop-long pattern that lost 6x in 24h — exit rules
apply, no averaging. SHORTs remain the aligned side; LONGs only on sustained EMA300 reclaim
WITH volume; mid-band = no trade; size 1.0x.

## QUEUE
- **CEO (time-critical):** CONF_FLOOR fk ruling (fkB now 12.6% — comfortable) + site-lock
  after :4856 + blocked-count RECOMPUTE at ship (live 55@14d).
- **CEO:** D=0.20 post-arm floor GO — #149 scope caveat attached (unscoped 30d p=0.215).
- **Oct 26 17:42Z:** price-feed 24h soak.
- **Oct 27:** unclog waiver expiry + pump-chain- PROMOTE + waiver scoreboard + #139 re-measure.
- **COLLECT:** inverse chase-block n 17→20 | TAT fire-count eval (23 fires) | hl_copy n=13.
- **Nov 1:** coin_regime OOS. **Nov 15:** floor_admit 30d same-sign.
- **Monitor:** ADA #16405 (open LONG in SHORT_BIAS tape).

## SIDEWAYS FIND (FIXED)
watchdog `take_profit` UndefinedColumn (1691 hits) — **FIXED** this run via prompt SQL
cheat-sheet. Remaining INFO: uncommitted comment-only shadow_trader.py hunks + bug-hunter
verdicts in tree (not from this run; daily timer will catch).

Artifacts: brain/audit_recommendations.json, brain/creative_improvements.json,
brain/changes_log.json, brain/analysis/vol_precondition_pumpchain_2026-10-26.py,
automation/trade-watchdog/trade_watchdog_prompt.md, CURRENT.md.
