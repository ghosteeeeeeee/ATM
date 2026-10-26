# Current State — brain_auditor #160 2026-10-26 11:55 UTC
**Last Updated: 2026-10-26 11:55 UTC**
**Updated by: brain_auditor #160. Prior: #159 10:55 / #158 09:55 / #157 07:55 (preserved in git history).**

## HEADLINE — INSTRUMENT BUG: expiry_shadow t-stats are PSEUDO-REPLICATED. 0 CONFIG CHANGES.

One row per signal **event**, but events repeat over only **79-102 distinct tokens**
per 14-30d cohort. Naive t treats them as independent → overstated ~2-3x.
**CR1 cluster-robust (token = cluster), excess_4h:**

| cohort | N | G | mean | naive t | **t_CR** |
|---|---|---|---|---|---|
| SKIPPED SHORT 14d | 1517 | 79 | +0.3223 | +6.64 | **+2.13** |
| SKIPPED SHORT 30d | 1901 | 80 | +0.2269 | +4.81 | **+1.72** |
| SKIPPED LONG 14d | 2013 | 76 | -0.1877 | -4.16 | **-1.40** |
| SKIPPED LONG 30d | 3583 | 79 | -0.1590 | -5.24 | **-1.82** |
| EXPIRED LONG 14d | 4312 | 101 | -0.0994 | -3.24 | **-1.37** |
| EXPIRED LONG 30d | 7045 | 102 | -0.0701 | -2.77 | **-1.15** |
| EXPIRED SHORT 14d | 7251 | 90 | +0.0120 | +0.61 | **+0.30** |
| EXPIRED SHORT 30d | 9005 | 91 | +0.0002 | +0.01 | **+0.01** |

**Not one cohort reaches |t|>=2 at BOTH windows.** Therefore:
- `#76` "gates avoid $142 / net +$65 saved (t=-3.00)" and `#153` "short-supply real
  but below cost (t=+4.22)" were computed on the **naive** column → invalid.
- Correct reading: the instrument gives **point-estimate direction only**.
- **Status quo unchanged and still correct — but on the conservative default, NOT on
  proven savings.** Do not loosen short gates (no proven edge), do not claim gates
  are proven to save money either.
- **PRE-REG CORRECTION (logged pre-data):** the 2026-10-31 short-supply bar
  `30d excess_4h > +0.05% AND t>=2` is restated as **`t_CR >= 2` via
  `brain/analysis/cluster_t.py`** + LONG same-sign negative + excess > 0.14% cost.
  As-is, SKIPPED SHORT 30d clears +0.05 and cost but **t_CR=+1.72 → FAILS**.

**SHIPPED (zero behavior):** `brain/analysis/cluster_t.py --selfcheck PASS`
(pseudo-rep naive +6.44 → CR +0.95; common-effect CR stays significant; degenerate
inputs rejected) + STATISTICS WARNING block in `scripts/expiry_shadow.py` docstring.

## LAST-RUN VERIFY — ALL PASS
`repeat_after_stop --selfcheck PASS` · `_gc_trail_state()` canary **0** `Profit monster
closing` since 2026-10-23 (GC live 08:45:55) · `contrarian_both_sides` reproduces
(pc- flip 61.7% newer n=154 p=0.0046 / 66.8% older n=193 p=0.0000, **both halves**) ·
`session_brain --selfcheck 4/4 unique` · `waiver_expiry --selfcheck PASS`, flip1
active (expires **2026-10-27T00:00Z**) · constants working-tree diff **EMPTY** ·
CEO_PROTECTED **13/13** · size-reduce **ABSENT = 1.0x** · session lock **absent** ·
**0** Tracebacks dated 2026-10-26.

## MANDATE — CHOP vs TREND (fresh PG, 14d, 326T 38.3% `-$4.31`)
- **TREND/TP exits 114T 88.6% `+$8.85`** vs **CHOP hard_max_loss 61T 0.0% `-$6.12`**
  vs other 151T 15.9% `-$7.04`
- **armed 139T 76.3% `+$8.41`** vs **unarmed 187T 10.2% `-$12.72`**
- 7d direction: **LONG 82T 40.2% `-$0.76`** vs **SHORT 44T 54.5% `+$0.50`** (n=126)
- Arm-rate ledger (trailing_activated / 14d): volume-buildup- 78.6% · bb-squeeze+ 81.8% ·
  r2v2-long3 60.0% · pump-chain+ 59.1% · bb-bounce 52.6% · doji 37.5% (dead) ·
  ai-trader+ 30.0% (disabled) · **pump-chain- 25.0%** ← lowest live.
  ⚠️ `mfe_pct>=0.40` gives **different** numbers (pump-chain- 66.7%/14d, 69.8%/30d) —
  the two metrics are NOT interchangeable; state which column any arm-rate uses.

## LOSING AUTOPSY — WRONG-SIDE REFUTED 84th CONSECUTIVE RUN
`recovery_replay.py` adverse-first (`--selfcheck ASSERT PASS`):
**48h n=12 = 5 never-adverse / 6 recovered / 1 NEVER** → ICP `#16409` SHORT
`hh-hl-,warrior-sr-confirm-` `-$0.09`, rsi_exec **39.0**, entered under the
**[35,45) unclog-waiver band**, price +0.83% adverse = shorting the floor (mirror of
the BANANA long mistake). Refs that survive the correction: `#61` p=0.116 · `#84` t=-0.04.
**Winning side = trail-armed shorts** (14d armed +$8.41 / unarmed -$12.72).

## WAIVER EXEMPTION-BAND EVAL — due 2026-10-27T00:00Z (T/CEO must rule)
Since grant 2026-10-24 15:40, SHORT `rsi_exec` in [35,45): **n=5, 4W/1L, `+$0.07`**
(HYPER/DOT/ANIME/CAKE all profit-monster-trail wins; ICP `-$0.09`).
- `n>=5` **MET** · `WR>=40%` **MET (80%)**
- `no single loss >1%` → **AMBIGUOUS: ICP price-move 0.83% PASSES, account -4.16% FAILS.
  CEO/T must define the unit.**
- `gate-shadow OOS same-sign` → **NOT EVALUABLE**: gate_shadow semantics changed in `#156`
  to distinct-trade follow-on (explicitly *not* foregone money), and n=5 = 5 clusters (t undefined).
- Recommendation: **do not auto-expire on auditor authority.** Point estimate favours
  renewing; n=5 decides nothing.

## CREATIVE / REJECTED THIS RUN
1. **cluster_t shipped** (above).
2. **ARM-GAP re-measure pre-registered** — 14d `mfe>=0.40 AND NOT trailing_activated AND
   exit in (atr_sl_hit/hard_sl/manual_sl_hit)` = **35T `-$1.71` @2.9% WR, avg MFE 0.774**
   (pump-chain 25T `-$1.22` / non-pump 10T `-$0.49`); 30d 67T `-$1.18`. Two causes:
   (a) stale profit_monster trail-state keys made UGB-PT skip them (`position_manager.py:3917`)
   — **#158 GC live 08:45:55 today**; (b) **EXIT ORDER — ATR TP/SL is section 1 with
   `continue` (`:3269`) and runs before UGB-PT at 7b (`:3881`)**. BAR locked: post-GC 7d
   cohort rate < 14d baseline **35/109 = 32.1%** with no rise in premature ugb_pt/trail
   exits → (a); stays >=32% → (b), fix is a reorder not a new floor.
3. **REJECTED — bb_position / z_score entry filter**: pooled 30d p=0.0035/0.0060 but
   **direction-confounded** (armed trades skew LONG 253 vs 61). Stratified LONG 30d
   p=0.747/0.875, SHORT p=0.324; 14d LONG p=0.0074 flips at 30d. **Simpson's paradox.**
4. **RE-REJECTED — EXTREME-vol block**: 14d `-$2.54` but **30d `+$0.64` / 60d `+$2.38`**
   vs non-EXTREME 30d `-$2.86` / 60d `-$10.33` → EXTREME is the better 60d regime.
   Confirms `#153`. 
5. **coin_regime LONG-COUNTER**: LONG into SHORT_BIAS 30T 36.7% `-$0.87` vs into
   LONG_BIAS 39T 53.8% `+$0.71` — **identical n at 7/14/30d = NO OOS window**
   (stamps only since 2026-10-20) → stays **COLLECT to 2026-11-01**, not shipped.

## DEEP-DIVE — 0 new shippable sub-50% n>=15 targets
14d: bb-bounce 38T 36.8% (TAT-C live, kill bars fail #138) · doji 16T (killed Oct 16) ·
ai-trader+ 20T (disabled) · pump-chain- 36T 22.2% (CONF_FLOOR held + pc- PROMOTE Oct 27) ·
pump-chain+ 44T 31.8% (NO-KILL, 30d +$1.84) · r2v2-long3 15T 53.3% (above bar) ·
volume-buildup- 28T 75.0% `+$0.78` (healthy). **atr_sl_hit residual owned** by existing scopes.

## WATCHDOG — 0 steers · portfolio good
- ETH LONG `#16414` `-0.08%`: watchdog exit-if-1m<2326 met for **ONE** candle (11:21
  closed 2324.70) then recovered 2327→2331 through 11:30 → **TACTICAL clause, no action**
  (`#99` DURABLE/TACTICAL labelling); SL 2322.44 is the backstop.
- LTC SHORT `#16415` = aligned with SHORT_BIAS. No new LONG exposure while aggregate
  SHORT_BIAS (46/6/129) — already enforced by SHORT_NORMAL_PENALTY +
  REGIME_CONF_MULTIPLIER + DIRECTIONAL_CAP.
- Regime: btc_15m + btc_4h SHORT_BIAS · continuum AT EMA300 · vol LOW · wyckoff
  DISTRIBUTION · market_phase RECOVERY · trend_quality STRONG_DOWN · flips 20 agg/18 BTC = p50.

## DRIFT
- **HIGH (this run): expiry_shadow/gate_shadow naive t is pseudo-replicated** → all
  significance claims off those DBs must use `cluster_t`. Carried into #76/#153 citations.
- LOW: `data/gate_shadow.db` 0-byte stray (4th run; live writer `brain/gate_shadow.db`
  7.9MB/38,078 events) — not removed, no repo writer found.
- INFO: arm-rate reported under two incompatible definitions (see mandate section).
Carried LOW: weekly `Self-healing test: FAIL - ModuleNotFoundError dispatcher.dispatcher`
03:00 Sun (Oct 11/18/25) → Nov 1 · `signal_created_at` dead · `entry_regime_4h` 0/713 ·
`data_integrity_guard.py` never invoked.

## QUEUE
Oct 27: waiver LAPSE verify · pc- PROMOTE re-verify · mid-band [35,45) re-measure (#139) ·
CHASE_RATIO_SHADOW gate review · **exemption-band unit ruling (price vs account)**.
Oct 30: momentum time-stop blind run. **Oct 31: short-supply re-measure ON CLUSTER-ROBUST BAR.**
Nov 1: coin_regime OOS · Nov 8: gate scoreboard #2 · Nov 15: floor_admit/wyckoff joins.
CEO: CONF_FLOOR fkB ruling + enforcement site after decider_run.py:4856 · ARM-BE-STOP GO ·
escalation #17 exit-ladder candle OOS.
