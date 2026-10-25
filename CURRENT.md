# Current State — brain_auditor #148 2026-10-25 22:50 UTC
**Last Updated: 2026-10-25 22:50 UTC**
**Updated by: brain_auditor #148. Prior: brain_auditor #147 20:55 / #146 19:52 (preserved below + git history).**

## HEADLINE — 0 trading-constant changes, 0 ships, 3 creative items (1 rejected-with-data, 2 zero-code), CONF_FLOOR fk REPRODUCES #146 EXACTLY

**1. CONF_FLOOR fk FRESH (reproduces #146 byte-identical, 4h zero drift).**
blocked = pump-chain bare conf<30: **14d/30d 36T 7W `-$1.48`** | fkA-literal **5.6%** PASS |
fkB **19.4%** PASS (bar 20, margin 0.6pts) | fkA-family/scope **35.0%** FAIL.
Drift vs ship-time table (Oct 23): 32T 4W save `+$1.81` -> 36T 7W `+$1.48`; last 4 blocked
trades net `+$0.33` (3 winners). **DECAY TRIGGER PRE-REGISTERED: drop the ship if
blocked-cohort 7d net >= 0 at ship time.** Ruling + enforcement-site lock (AFTER
`decider_run.py:4856`; natural site = structural no-op per #146) + ship-time blocked-count
self-check = CEO time-critical.

**2. DIRECTION-MIX LEVER REJECTED-WITH-DATA (creative #1).**
7d SHORT 37T 51.4% `+$0.50` vs LONG 90T 42.2% `-$0.92`, 14d same sign — but **30d REVERSES
(SHORT `-$1.78` vs LONG `-$0.28`)** = fails OOS same-sign. Logged so nobody re-derives
"trade more shorts" from a 7d snapshot.

**3. TODAY'S 8 mfe_pct-NULLs = NOT A REGRESSION (root-caused).**
brain.py `trade close` (profit_monster/cut_loser path) never writes mfe; `cell_stats.backfill_mfe_mae()`
repairs nightly, timer last fired **00:20 UTC** — all 8 NULLs closed 00:58-22:26 and self-heal
Oct 26 00:20 (prior-day 0 NULLs = already repaired). Explains the "armed=None 8T all-winners"
KPI artifact: mfe-based arm KPIs blind up to 24h on ~8 brain-CLI closes/day. Zero action.

## MANDATE — CHOP vs TREND (fresh, PG this run)
- trail family 14d: **115T 102W 88.7% `+$9.29`** vs chop exits (HML+atr_sl) **145T 1W `-$12.07`**
- armed 7d **62T 71.0% `+$3.23`** vs unarmed **57T 8.8% `-$4.04`**
- never-armed share of gross loss: **7d 83.7% | 14d 85.5%** (band 70-92, no breach)
- 24h 17T 10W 58.8% `+$0.29` GREEN | 7d 127T 44.9% `-$0.42` | 14d 328T 37.8% `-$4.08`

## LOSING AUTOPSY — WRONG-SIDE REFUTED 72nd CONSECUTIVE RUN
`recovery_replay.py` adverse-first: **24h n=6 = 4 never-adverse / 2 recovered / 0 NEVER**;
**48h n=8 = 4/3/1** (1 = BTC ai-trader-pending CEO immaterial); **14d n=191 = 37/125/29**
(15.2% structural = re-enter-on-recovery Oct 27). All 6 24h losers = mid-band LONGs into a
SHORT_BIAS tape (ICP chased RSI 72.73) = chop, not wrong side. Refs: #61 p=0.116, #84 t=-0.04.

## LAST-RUN VERIFY — ALL PASS
#147 session_brain dedup **confirmed in live use** (3 Step-2 queries 6/6 unique each) |
#146 conf_field_semantics selfcheck PASS + fk section + :3800 hazard comment | [TRAIL] trade_id
live | **UGB-PT 2 fires today** (HYPE +1.11->+0.80, PENDLE +0.44->-0.01) | **TAT-C 3 fires**
(HBAR/SAGA/DOGE cut at 56m) | constants EMPTY diff | size-reduce absent=1.0x | 0 Tracebacks
2026-10-25 | session lock absent.

## READINESS
**2 open:** BTC #16395 LONG @80637, 6.5h never-armed — **arm-or-exit 23:47 UTC if btc_15m
still SHORT_BIAS** (retracts on arm/flip), SL 80151.7 backstop. ACE #16401 SHORT closed
`+0.43%` PM-trail 22:26 (volume-buildup- 14d 25T 72% `+$0.68` = best live family).
NO NEW LONGs while both TFs SHORT_BIAS + 1m below EMA300; reclaim WITH volume only;
mid-band = no trade; size 1.0x.

## QUEUE
- **CEO (time-critical):** CONF_FLOOR fk ruling (fkB 19.4% vs 20) + decay trigger + site-lock after :4856.
- **Oct 27:** unclog waiver expiry + contrarian pump-chain- PROMOTE (flip 64.2% n=344) + waiver scoreboard + #139 band+BELOW re-measure.
- **Nov 1:** coin_regime ALIGNED/COUNTER 14d OOS. **Nov 15:** floor_admit 30d same-sign.
- **Monitor:** bb-bounce 7d 20T 45% (kill WR bar <30% not met, TAT-C owns) | hl_copy 12T n<20.

---

# Current State — brain_auditor #147 2026-10-25 20:55 UTC
**Last Updated: 2026-10-25 20:55 UTC**
**Updated by: brain_auditor #147. Prior: brain_auditor #146 19:52 / #145 18:58 / #144 17:50 (preserved below + git history).**

## HEADLINE — SESSION BRAIN REPAIRED (8-run drift, root-caused), 0 trading-constant changes, 6 candidates REJECTED/COLLECT-WITH-DATA

**1. SESSION-BRAIN DUPLICATE-RECORD DRIFT — FIXED AT ROOT.**
294,753 of 404,091 chunk rows (**73%**) are duplicate `text` stored under a *different*
`session_id` (38,167 shared texts across 269 sessions = DSH session forks/copies). Near-identical
vectors land adjacent, so `query()` returned the same record under 6 titles for 8 runs straight
(#82, #85 and 5 in between) — mandate Step 2 has been returning garbage since then.
- **Before:** probe `loss money bleeding losing` -> **2 unique texts of 6** (5 identical copies)
- **After:** 5 probes x top_k=6 -> **6/6 unique each**; `python3 scripts/session_brain.py --selfcheck` **PASS**; py_compile PASS
- **bug_hunter:** round 1 FIX-REQUIRED (HIGH — dedup key was the full `text` while the returned dict
  stores `text[:500]`, so 2,690 prefix groups could still return duplicate strings; 3/15 diverse probes
  reproduced) -> fixed (`key = row[1][:500]`) + MED comment correction + 2 more probes + duplicate
  `db_size_mb` key deleted from `stats()` -> **round 2 SHIP, 0 HIGH / 0 MED**.
- **Where:** `scripts/session_brain.py query()` — text-dedup + search window `top_k*2 -> top_k*4`.
  Deliberately **not** at ingest: ingest already does per-session DELETE+INSERT, so skipping a
  shared text there would drop it whenever the *other* holder of that text is re-ingested.

**2. SIX CANDIDATES REJECTED/COLLECT-WITH-DATA (0 config changes).**
| candidate | verdict | why |
|---|---|---|
| **MEAN_REVERSION x btc_regime block** (mirror of BTC-CHOP-GATE) | **REJECTED** | real at 7d (p=0.035) and 14d (p=0.0085): MR in RANGING 25T 64% WR `+$0.74` vs BULL_TREND+BEAR_TREND 100T 27% WR `-$2.22`. But **30d OOS p=0.2416**, save collapses to `+$0.50`, **fkA-literal 22.0%/29.8% and fkB 27-41% all FAIL** the <20% bar. Logged so nobody re-derives it from a 14d snapshot. |
| coin_regime COUNTER block | **COLLECT** | 7d ALIGNED 56T 53.6% `+$0.95` vs COUNTER 35T 40.0% `-$0.47` (worst cell LONG-COUNTER 26T `-$0.71`) — but stamps only exist since **2026-10-20 08:11** (identical n at 7/14/30d = no OOS window) and fkB 10/26 = 38.5% FAIL. 14d OOS recheck **2026-11-01**. |
| **pump-chain+ non-HIGH regime** (watchdog-assigned) | **ANSWERED — no lever** | 14d EXTREME 34T 9W `+$0.08` **positive**, NORMAL 2T `-$0.03`, HIGH 9T `-$0.50` with **all 9 opens before the 2026-10-21 03:38 block ship** (last HIGH open 00:18) = **0 post-block leaks**; 7d EXTREME `-$0.42` is window noise. Real split is confidence: conf<30 26T 6W `-$1.29` vs 60+ 14T 6W `+$1.10` = CONF_FLOOR cohort. |
| r2v2-long3 entry filter | **MONITOR** | 14d 15T 46.7% `-$0.12`; losers RSI 60.3/65.9/68.7/72.7 vs winners 59-73 — no separation. |
| ai-trader-pending dead-flag leak | **NOT A BUG** | CEO-armed conditional directives (`trade_watchdog.py:1405` -> `brain.py trade add --force`); signal_schema gates components `ai-trader`/`ai-trader+`/`ai-trader-` only, by design ("Manual trades unaffected"). 16T 25% `-$0.14` = CEO domain, n<20. |
| session-brain ingest-side dedup | **REJECTED** | would punch holes (see above). |

**3. SHIPPED: `scripts/session_brain.py` retrieval dedup + `--selfcheck`.** Zero trading behavior.

## MANDATE — CHOP vs TREND (fresh, verified this run)
- armed(mfe>=0.40) vs unarmed: **7d 62T 71.0% `+$3.23` vs 65T 18.5% `-$3.73`** | **14d 154T 68.8% `+$8.46` vs 173T 9.8% `-$12.56`** | **30d 391T 72.4% `+$25.40` vs 305T 7.2% `-$27.48`**
- 14d exit cohorts: **profit-monster-trail 79T 72W `+$4.44` + atr_trail_hit 25T 20W `+$3.56`** vs **hard_max_loss 67T 0W `-$6.52` + atr_sl_hit 78T 1W `-$5.55`**
- never-armed share of gross loss: **7d 83.9% | 14d 85.5% | 30d 80.7%** (baseline band 70-92, no threshold breach)
- arm-rate ledger: volume-buildup- 66.7% / pump-chain- 65.7% / r2v2-long3 46.7% / **bb-bounce 41.7% (avg MFE 0.399 = ON the 0.40 line)** / pump-chain+ 37.8% / doji 31.3% / **ai-trader-pending 18.8%**
- 24h 16T 9W 56.2% `+$0.27` GREEN | 7d 127T 44.1% `-$0.50` | 14d 327T 37.6% `-$4.10` | 30d 696T 43.8% `-$2.08`

## LOSING AUTOPSY — WRONG-SIDE REFUTED 71st CONSECUTIVE RUN
`recovery_replay.py` adverse-first: **24h n=6 = 4 never-adverse / 2 recovered / 0 NEVER**;
**48h n=8 = 4 / 3 / 1** (the 1 = BTC #16377 ai-trader-pending manual_sl `-$0.08`, CEO, immaterial).
Valid refs: #61 opposite-side p=0.116, #84 forward-return t=-0.04. 0 new patterns.
All 6 24h losers were LONG into a SHORT_BIAS tape — 100% never-adverse or recovered = chop, not wrong side.

## READINESS
**1 open: BTC LONG #16395 continuum-trend+ @80637, SL 80151.7 / TP 81846.6, 4.5h, MFE 0 (never-armed profile), meta_rsi 58.15.**
- **Arm-or-exit at 8h open = 23:47 UTC today IF btc_15m still SHORT_BIAS** (watchdog condition; retracts if trail arms or 15m flips).
- **NO NEW LONG exposure** while btc_15m + btc_4h both SHORT_BIAS and BTC 1m holds below EMA300 ~80609 —
  expires on a 15-30m hold above or a 15m flip; re-test every cycle. Advisory for new entries only.
- LONGs only on a sustained reclaim WITH volume; SHORTs aligned; mid-band = no trade; size 1.0x.

## QUEUE
- **CEO (time-critical): CONF_FLOOR fk-definition ruling** — fkB 19.4% vs 20% bar; enforcement MUST sit
  AFTER `decider_run.py:4856` with a ship-time blocked-count self-check (gate site = 0 of 56 = structural no-op).
- **2026-10-27:** unclog waiver expiry + contrarian pump-chain- PROMOTE (flip 64.2% n=344) + waiver scoreboard.
- **2026-11-01:** coin_regime ALIGNED/COUNTER 14d OOS recheck. **2026-11-15:** floor_admit 30d same-sign bar.
- **INFO:** point docs at `brain/gate_shadow.db` (the `data/` copy is a 0-byte stale artifact);
  `data/contrarian_shadow_summary.json` says 54.7% where the outcome-join says 64.2% — the join is authoritative.

---

# Current State — brain_auditor #146 2026-10-25 19:52 UTC
**Last Updated: 2026-10-25 19:52 UTC**
**Updated by: brain_auditor #146. Prior: brain_auditor #145 18:58 / #144 17:50 / daily_orchestrator 17:05 (preserved below + git history).**

## HEADLINE — 0 trading-constant changes, 3 zero-behavior ships, 5 candidates REJECTED-WITH-DATA

**1. CONFIDENCE-FIELD SEMANTICS TRAP — caught before it became a live no-op.**
`trades.confidence` (post-penalty, the column every fk table in `brain/fk_definitions.md` measures) and the
value `MIN_EXEC_CONFIDENCE` compares at `decider_run.py:3796` (gate-time) are **different numbers**. Three
reductions run **after** the gate and their result is what `brain.py` stores:
- `:4308` WRONG_SIDE_PENALTY (−10) · `:4811` CTX-GATE WARN (−20 typical, **760 log lines**) · `:4856` LOSERS_CONF_PENALTY (−50)
- **14d n=294: LEAK 58/58** = every trade stored below 40 was **≥40 at the gate**; avg divergence **+18.18**
- **30d n=649: gate-time `conf<30` = 0 · stored `conf<30` = 56** → implementing CONF_FLOOR=30 at the natural
  site would block **0 of the 56** trades all its fk numbers were computed on = **STRUCTURAL NO-OP**
  (same class as the #129 size-dampen no-op)
- Contradicts the comment at `decider_run.py:4298` ("MIN_EXEC_CONFIDENCE handles the final cutoff").
- `_signal_metadata.final_confidence` **is** the gate-time value — use it for gate questions.

**2. CONFIDENCE SCALE CHANGED TWICE IN 10 DAYS.** Gate-time confidence **p50 95.0 (Oct 1-14) → 51.8 (Oct 15+)**
and share under 50 **12.5% → 49.4%**, driven by cell_stats `_cell_mult` wiring (2026-10-14) + CONF-CALIB clamp
(2026-10-15 03:41, commit `82c90ccd`). Any confidence split straddling Oct 14/15 is time-confounded — this run
rejected exactly such a candidate (below). Constants calibrated pre-2026-10-14 are on the old scale.

**3. SHIPPED (3, all zero-behavior):**
1. `brain/analysis/conf_field_semantics_2026-10-25.py` — `--selfcheck` PASS (LEAK / no-op / scale drift reproduce)
2. `brain/fk_definitions.md` — **CONFIDENCE FIELD SEMANTICS** section: field table, three post-gate reductions,
   blocked-count self-check requirement for CONF_FLOOR, scale-drift note
3. `scripts/decider_run.py:3796` — hazard comment at the gate site (`py_compile` PASS)

## CONF_FLOOR REFRESH — standing CEO item is now TIME-CRITICAL
bare pump-chain `conf<30` blocked set = **14d/30d 36T 7W `-$1.48`**
- **fkB 12.1% (Oct 23) → 19.4%** — one blocked winner from the 20% bar (margin collapsed 7.9pts → 0.6pts)
- fkA-family **35.0%** (14d) FAIL · fkA-literal 5.6% (14d) / 2.3% (30d) PASS
- Still **HELD** on the fk-definition ruling. The ruling must now also specify: **enforcement site after
  `decider_run.py:4856`** + **ship-time blocked-count self-check** (assert the count, don't trust the constant).

## FIVE CANDIDATES REJECTED-WITH-DATA THIS RUN
1. **pump-chain+ conf<70 floor** — naive 30d Fisher **p=0.0073** (blocked 36T 8W `-$1.60` vs kept 35T 19W `+$3.44`)
   **BUT CONFOUNDED**: conf≥70 trades exist only Oct 3-13 (old scale, values to 499); post-2026-10-14 conf≥70
   **n=3**; book p50 halved in the same week. fkA 22.2% also fails. → fails confounder check, do not re-propose
   without a within-era test.
2. **stored conf<40 hard block** — fkA 30.6% (30d) / 31.0% (14d) / 30.4% (7d) all FAIL; 14d p=0.296, 7d p=0.169 OOS FAIL.
3. **CTX-GATE WARN cohort block** (meta−stored ∈ [19,26]) — fkA 30.0% (14d) / 39.8% (30d) FAIL; 14d & 30d p=0.244
   FAIL; **30d cohort PnL `+$0.58` = blocking loses**.
4. **EXTREME volatility gate** — 14d 149T 28.2% `-$2.50` worst, but **30d EXTREME 290T `+$0.57` = BEST regime**
   with the highest arm rate (59.3%) → sign flip, window disagreement.
5. **watchdog-queued bleed families** — pc+ 30d `+$1.84` NO-KILL stands; bb-bounce conf split p=0.74 and regime
   split n=9/n=27 under-powered (TAT-C already live); ai-trader-pending n=16 <20 AND CEO/autopilot domain.

## MANDATE — CHOP vs TREND (fresh)
- armed(mfe≥0.40) vs unarmed: **7d 62T 71.0% `+$3.23` vs 58T 8.6% `-$4.10`** | **14d 155T 69.0% `+$8.48` vs
  164T 6.1% `-$12.93`** | **30d 391T 72.4% `+$25.40` vs 289T 4.8% `-$27.93`**
- TRAIL/TP vs CHOP/STOP: **7d 60T 52W `+$4.26` vs 67T 4W `-$4.76`** | **14d 124T 110W `+$10.65` vs 204T 14W `-$14.73`**
- never-armed share of gross loss: **7d 79.6% | 14d 83.4%** (baseline band 70-92, no threshold breach)
- 24h 18T 11W 61.1% `+$0.51` GREEN | 48h 27T 18W `+$1.33` | 7d 127T 44.1% `-$0.50` (LONG 90T `-$0.92` / SHORT 37T `+$0.42`)
- 14d 328T 37.8% `-$4.08` | 30d 696T 43.8% `-$2.08`

## LOSING AUTOPSY 48h — WRONG-SIDE REFUTED 70th CONSECUTIVE RUN
`recovery_replay.py` adverse-first: n=8 = 4 never-adverse / 3 recovered / **1 NEVER** (BTC #16377
ai-trader-pending manual_sl `-$0.08`, CEO, immaterial). Valid refs: #61 p=0.116, #84 t=-0.04. 0 new patterns.

## SHADOW (2/5 usable)
contrarian join **RE-RAN 814/542**: **pump-chain- flip 64.2% n=344 = Oct 27 PROMOTE stands** (63.9→64.2 monotone);
btc-pump-rider+ 24.9% n=197 do-not-flip; TOTAL 49.8% = flip is family-specific. shadow_trader **21,826** signals —
CONFLUENCE-EXPIRY blocked 10,669 @48% would-win avg `-$0.12` (gates justified), EXEC-BLOCK 16 @12% best gate;
exit A/B pm_trail `+$3,043` vs hard_max `-$4,611`. oscillator frozen (JSONL, `json.load` crashes) · wyckoff no
outcome col · floor_admit join COLLECT to 2026-11-15 · rr_shadow orphaned 21d.

## SIGNAL DEEP-DIVE — 0 new sub-50% n≥15 targets
pc+ / bb-bounce-v2-long+ / ai-trader-pending / r2v2-long3 / hl_copy_trader all owned, killed or under-powered.
Arm-rate KPI (n≥15 ∧ arm<40% ∧ PnL<0) yields only **pump-chain+ 37.8%** among live signals = already CONF_FLOOR-owned.

## WATCHDOG TRIAGE (19:14 cycle)
- steers `[]` in watchdog.json; recommendations carried 2 warnings + 1 info
- ETH #16400 knife-edge SL: **AGREE — leave it**; trade has since closed. Tight stop is right for a chop pin.
- Pin-scoped mid-band LONG entry block: **ENDORSE as advisory, no config change** (unlike the blanket block
  refuted in #139, this one is condition-keyed and expires on a decisive EMA300 close)
- Bleed families flagged for brain_auditor: triaged above (rejected / owned / under-powered)
- STX SHORT pick: watchlist-only, `AI_TRADER_ENABLED=False` verified ✓ will not execute

## CHANGES FROM LAST RUN — ALL VERIFIED
#145 cell-stats guard **HOLD honored** (not re-proposed, no code landed) · #144 price-feed **HOLDING**
(latest_prices 267 rows newest 0.5min, timer fired 19:50:38Z; 24h soak still due) · #143 escalation #17
**not re-listed** (0 "awaiting CEO GO" in CURRENT.md) · #141 source stamp **6/6** post-15:15Z
(continuum-trend+, bb-bounce-v2-long+ ×3, bb-squeeze+, hl_copy_trader) · #135 spider fix **0 negative
trail_floor lines after Oct 23 10:30** · TAT-C still 3 fires (tripwire n=10 not reached).

## STANDING VERIFIES — ALL PASS
kill flags correct (vb+/doji/oversold/hmacd_mtf±/ai-trader/vb-long+ False, TAT-C True, LIVE_TRADING True) ·
CEO_PROTECTED_FLAGS **13/13** (SIGNALS_REGISTRY = signals/__init__.py registry, bb_bounce present, 165 rows) ·
hermes_constants.py **git diff EMPTY** · size-reduce file absent = 1.0x · session lock absent ·
**0 new Tracebacks 2026-10-25** (5 in log all pre-existing; Oct 25 03:00 = known Sunday self-healing) ·
`py_compile scripts/decider_run.py` OK · `conf_field_semantics --selfcheck` PASS.

## READINESS — 1 open, flat
**BTC #16395 LONG continuum-trend+ @80637**, SL 80151.7, TP 81846.6 — HOLD; exit condition = 15+ min of 1m
closes below EMA300; SL backstop untouched until arm. ETH #16400 and KAS #16399 closed during this run.
Regime: btc_15m **SHORT_BIAS** / btc_4h **LONG_BIAS** / continuum AT EMA300 / vol **LOW** / zscore STRONG_NEG /
velocity SLOW / acceleration POSITIVE / volume **LOW** / market_phase RECOVERY / trend_quality **STRONG_DOWN** /
auto=CHOP.
**No added size while auto=CHOP AND volume LOW (both true); trail-family first; LONGs only on sustained reclaim
WITH volume; SHORTs only with 4h aligned; size 1.0x; mid-band = no added exposure.** A LONG on a 15m SHORT_BIAS
tape → defense is the SL/arm, not direction panic.

## QUEUE
**This run added:** confidence-scale drift KPI (pre-registered) · CONF_FLOOR enforcement-site + blocked-count
self-check requirement (now part of the CEO ruling)
**Oct 27:** waiver expiry + mid-band [35,45) re-measure + pump-chain- contrarian PROMOTE (64.2% n=344 re-verified)
**Oct 28:** solo-bypass conversion recheck
**CEO:** **CONF_FLOOR fk-definition ruling — TIME-CRITICAL (fkB 19.4% vs 20% bar) + enforcement site (after
`:4856`) + blocked-count self-check** · cell-stats guard = HOLD with significance FAIL (not untested)
**Standing:** TAT-C fk tripwire at n≥10 fires (currently 3) · hl_copy_trader watch at 14d n≥15 (currently 12)
**MED:** session_brain duplicate-record rebuild (7th run flagged, still not done)
