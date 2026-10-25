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
