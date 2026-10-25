# Current State — brain_auditor #134 2026-10-25 ~06:55 UTC
**Last Updated: 2026-10-25 06:55 UTC**
**Updated by: brain_auditor #134. Prior: #133 05:10 + daily_orchestrator 05:10 (both preserved in git history).**

## HEADLINE #134 — ESCALATION #17 LEG 1 MEASURED (was escalated 78×, script existed but UNRUN)
**BE-at-arm candle OOS (`brain/analysis/be_at_arm_replay_2026-10-25.py`, selfcheck PASS) passes ALL FOUR
Oct-17 pre-registered bars on the pre-registered scope (non-EXTREME, exclude volume-, 1m close-through variant):**

| window | n | armed-rate (bar ≥30%) | armed_W | touched | saves | harmed W | NET | **fk_armed (bar <20%)** |
|---|---|---|---|---|---|---|---|---|
| 30d | 366 | **59.0%** ✓ | 171 | 53 | 34L +2.97 | 16 −0.83 | **+2.14** ✓ | **9.4%** ✓ |
| 14d | 153 | 57.5% ✓ | 64 | 33 | 20L +1.56 | 10 −0.56 | **+1.00** ✓ | **15.6%** ✓ |
| 7d | 75 | 60.0% ✓ | 34 | 16 | 10L +0.54 | 6 −0.46 | +0.08 ✓ | **17.6%** ✓ |

Split-sample (pre-reg bar: fk ≤20% in BOTH halves): **OLD d16-30 NET +1.04 fk 4.0% ✓ | NEW d1-15 NET +1.10 fk 16.7% ✓.**
→ **CEO GO ASK.** Ship path per Oct-17 verdict = shadow (LIVE since 10-18, #127 DB-state fix) → v6 exit-stack → CEO GO.

**⚠️ MID-RUN bug_hunter (2 HIGH) — all numbers above are POST-FIX and re-derived:**
- `be_at_arm` candle bound was `close_ts+60`, which admits the 1m candle lying **entirely after the real exit**
  → invented touches/saves. Fixed to `close_ts`.
- `mfe_cut` MFE window was `t_cut+60`, which fed MFE from the candle **after the T=55m cut** → inflated MFE,
  under-counted fires. Fixed to `t_cut`.
- **fk denominator**: the house bar is fk as % of **policy-cohort winners** (armed winners / open-at-T winners),
  not all window winners. The all-winners figure is dilute and always reads lower — it produced one false PASS
  (see MFE-CUT). Both scripts now print `fk_armed`/`fk_cohort` (house bar) and `fk_all` (diluted) separately.
- Selfchecks extended so each bug would now fail them: post-close candle, post-cut candle, SHORT direction.

**CREATIVE (measured, REJECTED-WITH-DATA):** BE activation gate above arm — 30d NET `+2.14` (0.40/arm) →
`+1.18` (0.60) → `+0.56` (0.80) → `+0.63` (1.00); fk_armed 9.4%→2.9%. Arm-level already passes every bar
(incl. 7d), so the gate buys no bar and costs ~45% of the edge. **Keep BE at arm-level.**

**MFE-CUT family-scoped bb-bounce candle OOS (`mfe_cut_bb_bounce_oos_2026-10-25.py`, selfcheck PASS) — BAR FAIL:**
30d cohort 33 (open at T with candles) / cohort_W 17, fired 9, saved 4 `+0.31`, killed 4 `−0.18`, NET **`+0.14`**,
**fk_cohort 23.5% > 20% bar → REJECTED-WITH-DATA.** (Pre-fix run divided by ALL window winners and read
14.3% = false PASS; edge is also only $0.005/trade.) 14d/7d pass on fk but are n=2/n=1 fires. **Do not re-propose.**

**HABITAT dampen Oct-25 re-measure (pre-reg #671, due today):** non-RANGING fc<50 108T 29.6% `−2.40` vs
fc≥50 123T 39.0% `−1.07` → Fisher **p=0.0025 PASSES** (was 0.0945), **fk 32/122=26.2% FAIL**, 0.80x save
**`+$0.48`/14d FAIL**; 30d passes fk (11.3%) but 7d fk 30.8% = window-unstable. Plus the size-lever structural
no-op rule (#8145) still stands. **STAYS REJECTED.** BOOST still needs CEO GO + measurement vehicle.

## ARM-RATE KPI (14d n≥15) — extends #131
volume-buildup- 72.7% arm / 68.2% WR (trend) · r2v2-long3 60.0% · pump-chain+ 58.7% · bb-bounce-v2-long+ 48.5% ·
doji 37.5% (killed) · ai-trader+ 30.4% (killed) · **pump-chain- 25.7% arm 22.9% WR `-0.30`** · ai-trader-pending 12.5%.
Standing rule (n≥15 ∧ arm<40% ∧ PnL<0) flags **exactly ONE live family: pump-chain- SHORT** = an *independent*
second axis on the Oct-27 contrarian PROMOTE (flip-WR 63.9%). No config change — Oct-27 ruling owns it.

## WATCHDOG TRIAGE
- **P1 direction-misalignment** (7d LONG 85T 41% `-1.07` vs SHORT 38T 45% `+0.33`, 91/122 tokens SHORT_BIAS):
  **ACKNOWLEDGED, NO ACTION.** Short-gate CLOSED #129 (SLOPE-FILTER +0.98 fails bar), counter-regime penalty
  REJECTED #608, time blocks BANNED. The correct lever exists and is pre-registered → contrarian flip Oct-27.
- **P3 pump-chain+ / bb-bounce**: no new lever passed bars (see above).
- **ICP #16389 CLOSED hard_max_loss `-4.58%` 05:46** — executor steer self-resolved. Book is FLAT, 0 open.
- **SIDEWAYS — hotset.json 0 tokens every minute since 05:56** (was 1); health monitor WARN "0 tokens 25x/30min".
  hermes-trades-api falls back to DB query and 12 trades/24h still execute → **MONITOR, not a fault**; escalate
  to a compaction-gate look only if still 0 for >24h.

## ORCHESTRATOR RUN 05:10 (4/4 first-attempt, 0 constants changes, 0 trade actions)
1. Zero-fire shadow diag CLOSED (upgrade_audit #2): 0 broken keys.
2. "closed today"→"closed 24h" label fix (run_pipeline.py:289, trading-checklist.py:204).
3. health-monitor timeout fix → **VERIFIED this run: 05:42 run COMPLETED 05:54:41 SUCCESS.**
4. price-fetcher.timer disabled (dead legacy unit).
**SIDEWAYS (disk):** real hogs coin_tracker.db 3.3G, session_brain.db 1.5G, price_history 15.3M rows / NO PRUNE.
Disk **82%**, below >85% trigger. First lever at 85% = price_history 30d retention, NOT candle pruning.

## LIVE (PG 06:50Z)
**0 open — flat book.** Last close: ICP #16389 r2v2-long3 hard_max_loss 05:46.

## NUMBERS (PG this run)
24h **12T 9W 75.0% '+0.70' GREEN** | 7d 123T 42.3% '-0.74' | 14d 324T 37.7% '-3.55' | 30d 686T 43.7% '-2.13'
14d arm split (mfe≥0.40 basis): **ARMED 157T 70.1% '+9.17' vs UNARMED 162T 6.2% '-12.84'**
7d exits: **PM-trail 41T 36W '+2.51'** vs chop/stop **HML 15T 0W '-1.89' + atr_sl 27T 0W '-1.48' + stale 3T 0W '-0.64'
+ hard_sl 4T 0W '-0.36' = 49T 0W '-4.37'** → the trend/chop law, unchanged.
Autopsy 48h n=14 (adverse-first, selfcheck PASS) = **4 never-adverse / 5 recovered / 5 NEVER → wrong-side
REFUTED 58th consecutive run** (valid refs: #61 p=0.116, #84 t=-0.04).
Shadow 3/5 usable: contrarian re-run **pc- flip 63.9% n=338, OOS post-Oct18 64.0%** · floor_admit join **638ep,
48.2% vs 38.2% p=0.126 COLLECT Nov-15** · oscillator frozen-by-design · wyckoff join still missing · rr_shadow orphaned.
LAST-RUN VERIFY (#132/#133) all PASS: constants EMPTY git diff · protected OK · size-reduce absent=1.0x ·
0 Tracebacks 2026-10-25 · floor_admit selfcheck PASS · watchdog dead-signal check present · ARM-BE/UGB-PT correct.

**⚠️ ARM-BE "0 fires correct-by-traffic" is UNPROVEN, not proven:** 0 fires since the #127 fix (22:50 Oct-24) —
but sibling UGB-BE also 0 in the same window and the book was flat for most of it. It is *no eligible traffic*,
not *verified*. First real test needs an armed trade that round-trips. Do not cite #128 as a pass.

## CEO STACK
1. **NEW: BE-at-arm GO** (all 4 Oct-17 bars met post-fix — table above) → v6 exit-stack integration
2. pump-chain+ NO-KILL (30d '+1.85') → CONF_FLOOR fk ruling (fkA 41.7% FAIL) → pump-chain TAT BASE-vs-VARIANT-C
3. UGB-BE pending (PT subsumes it) · Oct-27 contrarian PROMOTE + coin_regime n≥50 + mid-band dampen re-measure
4. Nov-15 floor_admit 30d same-sign

## ESCALATION #17 — LEG 1 DONE, LEG 2 OPEN (was "78th, uncommissioned")
- **Leg 1 (BE-at-arm): MEASURED this run, all 4 bars MET post-bug-fix → CEO GO ask.**
- **Leg 2 (armed-trail-distance candle OOS): PRE-REGISTERED this run.** PM trail sits at peak-1.20% while
  UGB-PT already runs peak-0.30% for the *unarmed* half — the armed half has the wider leash, and the round-trip
  giveback ceiling (+$8.28/14d) far exceeds what BE-at-arm can capture (+$2.14/30d) because most giveback never
  reaches entry. Single variable, pnl_usdt both sides, shadow first + CEO GO.

## NEXT ACTIONS
1. CEO ruling on BE-at-arm (armed-rate/fk/net bars all met — send the table)
2. Build leg 2: armed-trail-distance sweep (pre-registered this run)
3. Oct 27: contrarian pump-chain- PROMOTE (63.9% n=338 + arm-rate 25.7% corroboration) + coin_regime + mid-band
4. Disk >85% → price_history 30d retention (see orchestrator sideways find)
5. Hotset 0-token watch: re-check at ~07:00 Oct 26
