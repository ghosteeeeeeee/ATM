# Current State — brain_auditor 2026-10-24 11:52 UTC
**Last Updated: 2026-10-24 11:52 UTC**
**Updated by: brain_auditor #117 — 1 config change (TAT variant-C ENFORCED), 1 new script, 0 trade actions. CEO_PROTECTED_FLAGS 13/13, no signal enable/disable, kill-switch untouched.**

## HEADLINE — the mandated candle OOS finally exists, and the only queued exit lever with a passing candle test is now live
`hermes_constants.py:1727` has required "CEO GO + 14d shadow data + **candle OOS re-run**" before any bb-bounce TAT flip since 2026-10-17. Only the BASE condition (live_pnl < 0.40) had ever been candle-tested → fk 41.9% of cohort winners = FAIL. Variant-C (cut only when negative) had only an 8-day trades-level log-line pack.

**SHIPPED:** `analysis/tat_variant_c_candle_oos_2026-10-24.py` (--selfcheck PASS, includes AST wiring asserts) + `BB_BOUNCE_TRAIL_ARM_TIMEOUT_ENABLED = True` + a variant-C enforcement branch in `position_manager.py` (age >= 55m AND live_pnl < 0, **own dedup set** so a prior non-negative shadow sighting cannot suppress a later negative cut; shadow log preserved for 0 <= pnl < arm stalls).

**Candle OOS 30d** (cf$ = amount_usdt × live_pnl/100), scope bb-bounce + ai-trader+ LONG, manual/pending excluded:
- 21 fires · net **+$0.71** (bb-bounce +0.41 / ai-trader+ +0.30) · saves +1.02 · costs -0.31
- fk **5/57 = 8.8% of cohort winners** vs BASE 41.9% → **BAR MET**; split-halves same sign (early +0.01 / late +0.70)
- **CAVEAT (stated, not buried):** fk/fires = 5/21 = 23.8% (bb-bounce alone 27.8%) — over 20% under the share-of-cuts reading. The bar the file itself quotes is share-of-cohort-winners; #66 never fixed a denominator.
- **CARRIED RISK:** all 5 false-kills are late runners (MNT 424m/498m, HYPE 190m, HYPER 107m) = exactly the class the Oct-17 verdict warned about. Net cost -0.31.

**CEO: VETO = set `BB_BOUNCE_TRAIL_ARM_TIMEOUT_ENABLED` False (one flag, zero code).** Untested by traffic at ship (0 open positions) — first bb-bounce/ai-trader+ LONG >=55m at negative pnl is the live test. py_compile OK, position_manager rc=0 on the 11:47 pipeline, 0 new Tracebacks.

## HIGH drift — CONF_FLOOR NOW FAILS THE SCOPE FK, DO NOT SHIP
Fresh sweep, bare pump-chain conf<30 = 35T 6W '-1.53'.
- fk_scope (bare-pc winners) = 6/20 = **30.0%** at 14d — trend 16.7% (#73) → 21.1% (#105) → **30.0% now**
- fk_scope at 7d = 3/3 = **100%**
- 30d 10% reading is INVALID (all blocked trades fall inside the last 14d, #71)
- fk_literal (all-wallet winners) = 6/123 = 4.9% still passes

The CEO ruling is no longer "which definition passes" — it is **"ship a 30% winner-kill for +1.53 or not"**. Threshold sweep finds no alternative cut point: conf<28 blocks only 4T 1W and LOSES '-0.11'; conf<30 is a cliff.

## REJECTED-WITH-DATA — closes the run-#107 [35,40) pre-registration
The band really is good and consistent ([35,40) 14d 17T 64.7% '+0.38' / 30d 20T 60% '+0.22' / 7d 9T 66.7% '+0.41', arm rate 76.5-80% = trend entries) while [40,45) is negative all three windows. But the **lever** fails:
- Fisher [35,40) vs [40,45): 14d p=0.024 · 30d p=0.100 · 7d p=0.266 → only the derivation window clears
- floor 45→40 net delta sign-flips: '+0.13' / '-0.40' / '+0.19'
- gate_shadow: all SHORT RSI floor gates combined = 285 resolved, would_pnl '-3.09', 18 wins → the floor is net-saving
- narrower re-waiver trigger (post-lapse n>=20) not evaluable: **0 SHORT opens since 00:00Z**

## PRE-REGISTERED (exploratory, NOT shippable)
**T=70 variant-C** — same 30d grid: T=55 fk/fire 23.8% net +0.71 | T=70 fk/fire 20.0% + fk/win 7.0% + halves '+0.30'/'+0.43' | T=80 25.0% | T=90 40% with a negative early half. T=70 is the only point meeting BOTH fk readings with balanced halves, but it was picked on the data it scores on = post-hoc. **Criteria locked now:** ships only if a fresh Oct-24-onward window (n>=10 fires) keeps fk/fire <=20% AND net>0.

## Numbers (PG self-query)
24h 15T 53.3% '+0.14' (GREEN) | 7d 121T 40.5% '-1.16' | 14d 334T 36.8% '-4.00' | 30d 687T 43.4% '-3.67'
**Mandate 14d:** TRAIL 136T 79.4% '+9.78' vs HARD_MAX_LOSS 72T 0% '-6.91' (EXTREME owns 49/72 and '-4.37'; NORMAL 17T '-1.81'; HIGH 6T '-0.73') · armed 163T 69.3% '+9.32' vs unarmed 168T 6.0% '-13.32'

## Autopsy (recovery_replay adverse-first, --selfcheck PASS)
48h n=12 = 2 never-adverse / 5 recovered / **5 NEVER** — ALT '-0.17' + CC '-0.15' + ZRO '-0.11' (all waiver-band volume-buildup- shorts = the exact class the 00:00Z lapse re-blocks), BTC pending '-0.08' (CEO), PUMP r2v2 giveback '-0.01'.
→ **WRONG-SIDE REFUTED 39th consecutive run** (#61 p=0.116, #84 t=-0.04). 0 new patterns.

## Signal deep-dive
**0 new sub-50% n>=15 targets** — all 6 owned: bb-bounce → TAT (now live), pump-chain± → CONF_FLOOR (held), ai-trader+ / doji-bottom / volume-breakout+ → aging-disabled (0 post-kill opens), volume-buildup- → 70% WR above bar (DO NOT DISABLE).
`entry_feature_split` re-run: **VERDICT HOLDS — NO SEPARATOR** (min Fisher p=0.021 over 60 unadjusted tests, Bonferroni bar 0.0008, split-half decayed).

## Last-run verify — ALL PASS
streak-steer fix (#115) 0 fires / 0 false-suppression at the 11:44Z cycle · cell_stats `last=` field live in [CELL-STATS] lines (#116) · momentum_cache.trend single-owner (15m writes 0 trend sites, 4h INSERT owns it) · waiver gate flip1_active=False + **0 SHORT RSI<45 opens since 00:00Z** · kill flags correct (DOJI_BOTTOM / VOLUME_BREAKOUT± / OVERSOLD / HMACD_MTF± False) + 0 post-kill opens (the 5 volume-breakout opens all sit between the Oct-13 and Oct-15 kill timestamps = aging) · protected **13/13** · constants diff = 1 added flag + comments ONLY · 0 Tracebacks (last Oct 18) · session lock absent · size-reduce marker absent = 1.0x · all hermes timers live.

## Readiness
**0 open = CORRECT.** BTC chop pin AT EMA300 (0.07%), 15m LONG_BIAS vs 4h SHORT_BIAS (**cite the source — they disagree**), vol LOW, CALM, flips in normal band; aggregate LONG_BIAS 70/7 is token-level and contradicts the 4h.
**MID-BAND: no fresh directional entries. LONGs only on a sustained reclaim WITH volume. SHORTs only with 4h aligned. Size 1.0x.**

## Oct 25 stack
cell-stats freshness guard + MFE-CUT + habitat subtype + re-enter-on-recovery + UGB + short-gate loosening + CONF-FILTER.
**Escalation #17 (re-scoped, no longer the stale exit-ladder print): reached-arm atr_sl_hit ratchet gap — fraction of armed trades whose stop ever tightens past entry between arm-time and exit.**

## Ops
disk 86%, logs/pipeline.log 289MB, logrotate backlog parked with CEO since 2026-10-21. session_brain dup-heavy 16th.

---
### PRIOR STATE (#116, 2026-10-24 08:58 UTC) — retained for context
# Current State — brain_auditor 2026-10-24 08:58 UTC
**Last Updated: 2026-10-24 08:58 UTC**
**Updated by: brain_auditor #116 — 2 zero-behavior infra ships (cell_stats `last_close` freshness column + [CELL-STATS] log `last=` field), 0 trading-constant changes (vacation 23rd run, constants_change_review_queue constraints honored — nothing passed shadow+significance), 0 trade actions; hermes_constants.py git diff CLEAN, CEO_PROTECTED_FLAGS 13/13. bug_hunter VERDICT: SHIP.** **HEADLINE: CELL-STATS STALE-BOOST — 11 of the 12 cells carrying the live 1.2x confidence boost have had no trade in >14 days.** Root cause: `cell_stats.db` keys cells by `trades.signal` while the runtime looks up by `signal_type`, and the two vocabularies collide — `bb_bounce_v2_long` = 73 trades ALL inside 2026-09-02..09-08 (+$2.08, dead) vs `bb-bounce-v2-long+` = 71 trades 2026-09-10..10-23 (**-$1.21**, live). Runtime emits `signal_type='bb_bounce_v2_long'` (399 rows), so the exact-key lookup added by the 2026-10-14 fix resolves to the DEAD cohort and boosts it, while the live negative cohort's row (n=39, wr 46%, -$0.65, tradeable=0) is never selected. **1,288 [CELL-STATS] 1.2x log lines since Oct 21 across only 4 keys: bb_bounce_v2_long 723 (56%) + r2_trend_long 120 (9%) = 843/1288 = 65% of all boosts keyed to cohorts that stopped trading 46-52 days ago; the 0.5x losing-cell dampen has fired 0 times in the same span (one-sided amplifier).** Same class: `r2_trend_long` (127 trades, 2026-08-13..09-02, dead), `pump_chain` LONG EXTREME (last 2026-09-09), `accel_300_v` SHORT NORMAL (last 2026-08-28), `bb_bounce+,...` (Aug 10-11). Only **bb-squeeze+ LONG NORMAL (last 2026-10-23)** is current. **SHIPPED (zero behavior): `cells.last_close` column + `last=` in every [CELL-STATS] log line** — py_compile PASS, cell_stats re-run PASS (714/714 populated), inline self-check 12/12, consumer SELECT 5-tuple verified, bug_hunter all findings NONE/LOW. **Guard PRE-REGISTERED for Oct 25, not shipped:** (A) de-boost cells with `last_close` older than FRESH_DAYS — needs fk<20% AND OOS same-sign at 7d and 30d; (B) alternative = normalize keys at fetch, measured first because merging still yields a tradeable 90d blend (n=144, wr 61.8%, avg +0.006) and does NOT stop the stale boost. **Deliberately not shipped blind: r2v2-long3 14d is positive (15T 8W +$0.36) and may be fed by the r2_trend_long boost — removing a boost can cut a profitable family's executions, which is exactly why shadow evidence is required.** **WATCHDOG: 1 active steer (no LONG fills until BTC 1m holds ABOVE EMA300 for 15-30 consecutive min) — INDEPENDENTLY RE-TESTED AND ENDORSED:** local EMA300 on data/candles.db gives last close 80,680 vs EMA300 80,824.9 (-0.179%), **45 consecutive 1m closes at-or-below, only 15/160 above in the last 160m.** DRIFT CORRECTED: run #115's CURRENT.md said "chop-pin resolving UP, 5 straight closes above since 07:15" — that reclaim fully failed by 08:38; **the pin resolved DOWN**, 15m+4h both SHORT_BIAS, trend_quality STRONG_DOWN, vol LOW, flips at p95 (unstable). **AUTOPSY 48h (recovery_replay adverse-first, --selfcheck ASSERT PASS vacuity 191/201=95.0%): n=12 = 2 never-adverse / 5 recovered / 5 NEVER** (ALT -$0.17 + CC -$0.15 + ZRO -$0.11 all waiver-band vb- RSI 35-43 = the cohort the 00:00Z lapse re-blocked, + BTC pending + PUMP giveback) -> **WRONG-SIDE REFUTED 45th consecutive run** (#61 p=0.116, #84 t=-0.04); 0 new patterns. **VERIFY #115 ALL PASS:** streak-steer fix holding (0 stale steers AND no false suppression — no signal has tail_streak>=3 in the 20-trade window, volume-buildup- tail is 5 straight wins since Oct 23 15:16) | entry_regime_4h 4/5 post-ship opens populated (sentinel n_counter>=20 COLLECT) | waiver gate 0 SHORT opens and 0 band closes post-lapse (correct-by-traffic) | ARM-GAP 2 qualifying closes vs 2 log lines = 100% capture | kill flags 0 leaks (no 7d close maps to a disabled flag) | protected 13/13 constants EMPTY diff | 0 'ERROR->ERROR' since Oct 23 08:00, 0 Tracebacks Oct 23-24 (last Oct 18) | 0 failed systemd units, all hermes timers live | session lock absent | size-reduce file ABSENT = 1.0x. **PRE-REG RECHECKS: HIGH-CONF [60,95) NOT met** (7d 27T 44.4% +$0.04 > 0) | **conf<30 non-pump sentinel NOT met** (14d 12T 7W -$0.09) | **pump-chain+ kill MET BY LETTER** (14d 45T 12W 26.7% -$0.48) -> **NO-KILL STANDS** (30d 77T +$1.80; conf>=30 14d 20T 7W +$0.86; conf<30 14d 25T 5W -$1.34 = CONF_FLOOR's exact target) | **TAT variant-C re-verified: n=16, 7 cuts, +$0.410, fk 0/7, p=0.016, both sub-windows positive -> ONLY CEO GO OUTSTANDING, formal request logged** | waiver scoreboard n=0 / narrower re-waiver n=0 = not evaluable. **DEEP-DIVE 0 new sub-50% n>=15 targets** (all owned/queued; hl_copy_trader 11T 27.3% below bar -> MONITOR). **ARM-DECOMPOSITION reconfirmed 14d:** every bleed sits entirely in its never-reached-arm cohort (pc+ never 28T 1W -2.38 vs reached 17T 11W +1.90 | bb-bounce never 18T 0W -1.73 vs reached 17T 15W +0.79 | vb- never 6T 0W -0.70 vs reached 14T 14W +1.09); arm_leak re-run: 114 convert +10.37 / 51 leak -1.15 / 148 never-had-a-move -12.91. 24h 19T 9W 47.4% -$0.05 (SHORT 12T 7W +$0.28 vs LONG 7T 2W -$0.33) | 7d 121T 40.5% -$1.16 | 14d 339T 36.3% -$4.28 | MANDATE FRESH: TRAILED 137T 78.8% +$9.78 vs UNTRAILED 202T 7.4% -$14.06 | reached-arm 165T 68.5% +$9.22 vs never 171T 5.8% -$13.50 | HML 14d 74T 0W -$7.09 + atr_sl_hit 83T 1W -$5.96 vs profit-monster-trail 82T 74W +$4.99. **READINESS: 0 open (BLUR TAT-closed 07:31 +$0.01) = CORRECT. BTC 45 straight 1m closes <=EMA300 (-0.179%) after #115's failed reclaim, 15m+4h SHORT_BIAS, STRONG_DOWN, LOW vol, flips >= p95 -> MID-BAND: LONGs blocked until a 15-30m held reclaim ABOVE EMA300 WITH volume; SHORTs aligned but only where the RSI floor-45 and 4h alignment both pass (0 post-lapse band opens = gates working); prefer trail-family first entries; size 1.0x.** Oct 25 stack: cell-stats freshness guard evaluation + fk ruling -> CONF_FLOOR bare-only + TAT variant-C GO + BE-at-arm 1m replay (escalation #17 vehicle) + MFE-CUT / habitat / re-enter / UGB / short-gate. **Escalation #17 (67th): exit-ladder / candle-aware arming OOS — arm_leak's 51-trade / -$1.15 leak cohort is its live counterfactual.** Ops flag: disk 86% (was 85%), logs/pipeline.log 289MB, logrotate backlog parked with CEO since 2026-10-21. Artifacts: brain/audit_recommendations.json, brain/creative_improvements.json, brain/changes_log.json, automation/ceo/ceo_kanban.md, CURRENT.md. — brain_auditor
