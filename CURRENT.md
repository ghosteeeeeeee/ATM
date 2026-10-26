# Current State — brain_auditor #153 2026-10-26 03:45 UTC
**Last Updated: 2026-10-26 03:45 UTC**
**Updated by: brain_auditor #153. Prior: #152 02:40 / #151 01:40 (preserved in git history).**

## HEADLINE x2 — INSTRUMENT BUG FIXED + AUDIT-TRAIL GUARD (0 trading-constant changes)
1. **`analysis/tat_variant_c_candle_oos_2026-10-24.py` accepted `--dir SHORT` but computed
   LONG-signed `live_pnl`** — a SHORT probe cut shorts that were IN PROFIT (inverted test).
   `exit_ladder_tat_grid_2026-10-17.py:58-60` already flips correctly. Fixed (negate when
   `SCOPE_DIR=='SHORT'`) + selfcheck source-guard. **bug_hunter SHIP: LONG output
   BYTE-IDENTICAL old vs new** (bb-bounce `+$0.44` fk 11.1% / ai-trader+ `+$0.30` reproduce),
   SHORT sign verified empirically against PG `pnl_usdt` (direction-signed) + candles.
   **My first SHORT numbers this run (`-$6.51..-$7.06`) are RETRACTED.**
2. **47/2000 commit subjects carry $-expansion corruption** (`3T -/usr/bin/bash.11` =
   `-$0.11`; `/usr/bin/bash.` 93x + `/bin/bash.` 3x; latest **4386032f 2026-10-26 03:28**).
   Shipped **`.git/hooks/commit-msg`** (untracked, `core.hooksPath` unset = live): repairs both
   renderings to `$0.NN`, always exits 0. 3-case self-test PASS. **History NOT rewritten.**
   bug_hunter SHIP (fail-open on mktemp/sed, clean messages byte-identical incl. literal `$500`).

## REJECTED-WITH-DATA THIS RUN (do not re-derive)
- **SHORT trail-arm-timeout** (the `direction=='LONG'` coverage gap at position_manager.py:3735):
  corrected 30d candle OOS variant-C T=30 `-$0.62` / T=45 `-$0.21` / T=60 `+$0.10` (17 fires,
  fk 10.8%). T=60 clears bars at **$0.10/30d = 0.6bp/fire**; base condition already NO-PASS
  (exit_ladder Oct 17). **The LONG-only design is data-correct.**
- **Block LONG `entry_rsi_14>=65`** (watchdog steer mechanism): 7d `-$0.31` / 14d `+$0.30` /
  30d `+$0.20`; would catch **1 of 7** 24h LONG losers; mid-band already owned by
  `LONG_MIDBAND_NON_EXTREME_BLOCK` (residual 60-70 non-exempt 7d n=11 `-$0.04` flat).
- **Short-gate loosening (Oct-25 review)**: NONE meet (SHORT, n>=50, net >+$1.00, 30d same-sign,
  blocked WR<30%) at 14d or 30d. Nearest SLOPE-FILTER `+0.98`/227 @30d = fails by $0.02 and is
  sub-fee. **Re-confirms #142 CLOSED.** Next review 2026-11-08.
- **Expiry short-supply**: 14d SHORT excess_4h `+0.0795%` t=+4.22 LOOKS shippable but measured
  round-trip cost on the same rows = **`0.1400%`** (fee 0.04 + slip 0.10; gross-net = 0.1400
  exactly, n=10815) and blocked-cohort `net_pnl_pct` `-0.0798%` t=-7.77 → **edge real, BELOW
  COST.** 30d `+0.0260` t=+1.47 ns. Re-measure **Oct 31** (bar: 30d >+0.05% AND t>=2 AND LONG
  negative AND net of 0.1400%).
- **EXTREME-vol LONG block** re-rejected: 14d 86T `-$1.96` vs **30d 173T `+$2.48`** (#146 flip).
- **direction-mix** re-rejected: 30d SHORT `-$1.78` vs LONG `-$0.44` (#148 flip again).
- **bb-squeeze TAT 60→55**: grid best cell `+1.07` vs live `+1.02` = +$0.05 across 5 cells.

## MANDATE — CHOP vs TREND (fresh PG)
- TRAIL family 14d: **116T 88.8% `+$9.27`** vs chop exits (HML+atr_sl) **144T 0.7% `-$12.01`**
- armed (mfe>=0.40) 14d **164T 70.1% `+$8.23`** vs unarmed **165T 6.1% `-$12.89`**
  (30d 404T 73.0% `+$25.85` vs 302T 5.3% `-$28.07`)
- MFE buckets 14d monotone: `<0.20 -$8.65` | `0.20-0.40 -$4.24` | `0.40-0.80 +$1.13` |
  `>=0.80 +$7.10`
- chop-bleed share (HML+atr_sl+stale+TAT / gross loss): 7d 82.4% / 14d 88.0% / 30d 70.8%
  = inside 70-92 band, entry-quality owned, no exit lever qualifies
- 7d direction: LONG 90T 40.0% `-$1.16` vs SHORT 44T 54.5% `+$0.50`; **30d reverses**
  (SHORT 188T `-$1.78` vs LONG 518T `-$0.44`)

## WATCHDOG TRIAGE (0 steers; deep-analysis 3 recs)
1. Counter-trend LONG RSI-65 gate → **rejected with data**; the direction half is the
   pre-registered **coin_regime LONG-COUNTER (#147)**: 7d LONG+SHORT_BIAS tape **28T 35.7%
   `-$0.87`** vs LONG+LONG_BIAS **37T 51.4% `+$0.63`**; stamps only since 2026-10-20 (identical
   n at 7d/14d = no OOS window), **fkB 35.7% FAIL <20%** → COLLECT to **Nov 1**.
   `meta_rsi` claim verified against `entry_rsi_14` (54.17/58.15/47.67/53.37/57.14/72.73, 1 NULL).
2. pump-chain+ → NO-ACTION (7th run): 30d `+$1.84` NO-KILL, bleed = stops + conf<30 = CONF_FLOOR.
3. volume-buildup- → confirmed edge, keep fed: 19T 73.7% `+$0.43` 7d, arm-rate 78.6%.

## LOSING AUTOPSY — WRONG-SIDE REFUTED 77th CONSECUTIVE RUN
`recovery_replay.py` adverse-first (`--selfcheck` PASS): **48h n=11 = 5 never-adverse /
5 recovered / 1 NEVER.** The NEVER = ICP #16409 SHORT hard_max_loss `-$0.09` (RSI 40.0, 8.8m).
Refs that survive: #61 p=0.116, #84 t=-0.04. All 11 = chop; 7 LONG losers mid-band 47.67-58.15;
4 were TAT-cut for `-$0.17` total = defense working.

## LAST-RUN VERIFY — ALL PASS
#152 rogue-constants REVERT holding (git diff EMPTY, no new uncommitted edit,
PROFIT_MONSTER_BYPASS pump-chain intact) | #152 daily_git_commit GUARD present — **first live
test 07:15 UTC today** | #152 IO #16407 fk point CLOSED (atr_sl_hit `-$0.05`, open 01:59 /
close 03:05 = blocked-cohort LOSS; first was CFX `+$1.31`) | #151 postarm_giveback_census
present | #150 vol_precondition present, inverse chase-block n=17 of 20 | #147 session_brain
dedup live (6 probes, all distinct) | #146 conf_field_semantics present | kill flags correct,
0 post-kill opens | constants EMPTY | CEO_PROTECTED **13/13** | size-reduce **absent = 1.0x** |
session lock absent | session_brain dedup still healthy.

## DEEP-DIVE — 0 new sub-50% n>=15 targets (30d)
volume-breakout-long+ 22T 31.8% `+$0.82` (killed Oct 13, pre-kill) | ai-trader+ 29T 41.4%
(disabled Oct 19) | bb-bounce-v2-long+ 60T 48.3% `-$0.60` (TAT-C live, kill bar WR<30 NOT met) |
pump-chain+ 71T 38.0% `+$1.84` NO-KILL | pump-chain- 86T 34.9% `+$0.03` CONF_FLOOR+PROMOTE.
Arm-rate 30d: vb- 78.6% / pc- 69.8% / bb-squeeze 66.7% / bb-bounce-v3 63.2% / r2v2-long3 61.1% /
bb-bounce-v2 58.3% / pump-chain+ 47.9% — **no live signal >50% of trades in HML.**

## PRE-REG RECHECKS
- **CONF_FLOOR fkB 29.1% FAIL → ship HELD**, CEO ruling must waive/reject explicitly (pins 55@14d).
- pump-chain+ **NO-KILL stands** (30d `+$1.84`).
- pump-chain- **Oct-27 PROMOTE stands** — contrarian flip **64.6% n=347** (re-run this run).
- inverse chase-block n=17 of 20 COLLECT | hl_copy 12T COLLECT | bb-bounce weekly re-measure.
- **Oct 31**: expiry short-supply (cost-reconciled bar above).
- **Nov 1**: coin_regime ALIGNED/COUNTER 14d OOS | **Nov 8**: gate scoreboard review #2 |
  **Nov 15**: floor_admit 30d same-sign.

## SHADOW (3/5 answerable)
contrarian join — pump-chain- flip **64.6% n=347 STANDS**, btc-pump-rider+ 24.9% do-NOT-flip |
shadow_trader 23,053 signals: CONFLUENCE-EXPIRY 11,006 blocked @48% avg `-$0.12`, EXEC-BLOCK 16
@12%, exit A/B pm_trail `+$3,224` vs hard_max `-$4,885` = trail-or-nothing reproduces |
expiry_shadow 21,814 events (direction-signed table above) | **`data/gate_shadow.db` is a 0-byte
stale artifact — live writer is `brain/gate_shadow.db` 7.6MB (reconfirmed)** | oscillator FROZEN
/ wyckoff+floor PENDING / rr ORPHANED.

## READINESS
**0 open = CORRECT.** btc_15m + btc_4h BOTH SHORT_BIAS, continuum BELOW EMA300 (862+ min), vol
LOW, velocity SLOW, acceleration NEGATIVE, market_phase CALM/DECLINING, 0 steers, flips 21/24h =
p50 band (not an anomaly, churn = standing state). SHORT is the aligned side. **LONGs only on a
sustained 1m EMA300 reclaim WITH volume** (re-test next cycle); mid-band = no trade;
trail-family first; size 1.0x.

## DEAD COLUMNS (do not mine)
`predicted_return` 689/703 = all 0.0000 (uniq=1); `actual_return`, `entry_fear_greed`,
`entry_timing` = 0/703. `momentum_state` live (397/703) but failed the 7-check battery 2026-10-08.

## CEO QUEUE
Identify the 02:19:30 `hermes_constants.py` writer (URGENT) | CONF_FLOOR fkB FAIL 29.1% ruling |
D=0.20 post-arm floor GO (with #149 scope caveat).
