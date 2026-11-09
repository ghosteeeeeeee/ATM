# Current State — brain_auditor #241 2026-11-09 00:50 UTC
**Last Updated: 2026-11-09 00:50 UTC**
**Updated by: brain_auditor #241. Prior: #240 2026-11-08 16:50 UTC (preserved in git history).**

## HEADLINE — SIGNAL-ZOMBIE-PURGE DECIDE (DUE 11-09) RESOLVED: THE PURGE IS ALREADY TWO-TIER

1. **NO CHANGE (default action confirmed) — but both proposed options are ALREADY IMPLEMENTED.** Tier 1 = compactor purgers: `_purge_executed_signals` (1h, decision IN EXECUTED/FAILED) + `_purge_stale_unexecuted` (2h, EXPIRED/SKIPPED **and executed=0**). Tier 2 = `scripts/archive-signals.py` on `hermes-archive-signals.timer` (daily 04:00Z): archives decision IN (SKIPPED,EXPIRED,EXECUTED,COMPACTED,WAIT,FAILED) older than **CUTOFF_HOURS_OTHERS=336h = 14d** → `archive/signals/signals_YYYY-MM.jsonl.gz` **with decision_reason fully preserved** → DELETE+VACUUM. So option (a) retention≥14d and option (b) archive-preserve both exist already; the "sweep-expired zombies" (decision=EXPIRED AND executed=1) are the in-retention-window forensic cohort, by design.
2. **Evidence:** runtime DB `min(created_at)=2026-10-25` (16,161 rows, nothing older than ~15d despite ~1,000 zombies/day) + archive files 2026-08/09/10/11 all present. Forensic history not at risk. **SHIP: +8-line TWO-TIER PURGE ownership comment at the signal_compactor.py call site** (py_compile PASS, zero behavior) so this DECIDE is not re-derived a third time.
3. **0 config changes** — session lock absent, constants EMPTY diff, nothing passed vacation review-queue bars.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| **zombie-purge DECIDE (headline)** | RESOLVED → done. Two-tier purge already covers options (a)+(b); comment shipped |
| **chop-bleed** | 7d **94.5%** / 14d **94.8%** (both ≥92%) / 30d 89.0% — chronic, remedy VETOED as inert, owned by 11-14 stack |
| **RR asymmetry** | 7d avg win +0.0648 vs avg loss -0.1068 (1.65x) → breakeven WR **62.2%** vs actual 56.0% = loss SIZE is the lever |
| **exit families 14d** | profit-monster-trail 138T 97.8% **+7.76** carries all profit; atr_sl_hit 58T 0% -6.50 + hard_max_loss 45T 0% -5.82 = 103/162 losers (63.6%) through the two pure-loss engines |
| **jup concentration (side-find)** | jup_yolo_mirrored = 37% of last-100 fills, 139T/30d (18%) yet 30d net **-0.98** at 61.9% WR; only HIGH-SHORT cell positive — 4 registered items already cover it, reported NOT re-proposed |
| **#240 verify** | shadow_dup_check selfcheck PASS (77,491 rows) · clamps live · joins re-ran · constants EMPTY · 0 Tracebacks · registry 0 pending — **ALL PASS** |

### 2. NUMBERS (fresh PG 00:30Z)
- 24h **16T 56.3% -0.04 FLAT** | 7d **150T 56.0% -1.61** (armed 81T 92.6% +4.68 vs unarmed 69T 13.0% -6.29) | 14d 392T 54.6% -3.38 | 30d 768T 47.0% -6.60
- 7d exit families: trail 50T 98.0% +3.00 vs chop exits 56T 0% -6.69
- 14d sub-50% n≥15: pc+ 29T 48.3% -0.27 (NO-KILL/11-13) · pc- 32T 37.5% +0.07 (contrarian-owned) — **0 new targets**

### 3. SHADOW (3/6 usable)
- **contrarian join 00:30Z (re-ran, mandate):** overall flip 43.4% n=1448 · **pc- 64.6% (226W/124L) LIVE uniform chi2 p=0.3747 = Oct-27 PROMOTE stands** · rider 36.2% do-NOT
- floor join 11-08 08:30Z: 49.2% vs 43.7% **p=0.1411 COLLECT (11-15)**
- shadow_trader: exit A/B **pm_trail +11,582 vs hard_max -13,641** = trail-or-nothing
- oscillator FROZEN · wyckoff RETIRED · rr ORPHANED

### 4. AUTOPSY + AMPLIFY
- **48h recovery_replay (adverse-first, selfcheck PASS): n=8 = 5 never-adverse / 3 recovered / 0 NEVER → WRONG-SIDE REFUTED 68th consecutive** (#61 p=0.116, #84 t=-0.04).
- **AMPLIFY: 0 new proposals (rule-3 why-not recorded).** Top cells all in-flight (bb-squeeze combo-boost 11-10 · vb- clone-hunt 11-13 · jup walk 11-14 / HIGH OOS 11-19 · pc- contrarian 11-11) or below the +1.00 materiality bar. **Flip-KPI MET this week** (#239). In-flight reading: bb-squeeze+ 17 + warrior-sr-confirm+ 6 = **23% of last-100 vs ≥25% bar** (baseline 17%), deadline 11-10.
- Creative x2: two-tier purge ownership comment (SHIPPED) · jup concentration watch.
- constants EMPTY · session lock ABSENT · size-reduce absent = 1.0x · 0 pending checkpoints · watchdog steers = 0.

### 5. READINESS (2026-11-09 00:30 UTC)
**1 open — HOLD:** MON volume-buildup- SHORT #16828 +0.18% (0.1h), bracketed SL 0.016161 / TP 0.015516. 0 steers, portfolio good. Regime: **15m NEUTRAL vs 4h SHORT_BIAS**, continuum BELOW, vol NORMAL, wyckoff ACCUMULATION, market CALM, trend_quality UP → **HOLD; trail-family first; no fresh counter-trend entries; size 1.0x.**

**Queue:** ~~11-09 zombie-purge DECIDE~~ **DONE this run** → **11-10 eight items: gate-shadow-dedup fold + size-125 auto-revert (1.25→1.0, pre-adjudicated FAIL) + fade-ctx + rsi-ceiling-75 revert-rule + conf-filter-parity (jup conf-99) + jup-atrsl-parity + mfe-cut-arm-be + ichimoku-dampen** → 11-11 contrarian watch → 11-12 storm-waiver → 11-13 pc+ kill-review + vb- clone-hunt + linreg-fade → 11-14 stop-tighten eval (id bar MET=86, SHADOW tag, source archive+current) + drop-pcplus + probe-080 + bbsqueeze reband/neutral-exempt + mult-150 + atrtrail-clip + prearm-breakeven + TAT-age-sweep → 11-15 floor → 11-19 jup HIGH OOS → 11-21 conf-tilt + scope-widen walk.
**CEO:** mult-150 sign-off (evidence decayed — judge ex-pc+ or drop first) · jup HIGH cell HOLD · unclog-waiver EXPIRY re-measure [35,45) before renewal (expired 11-03, still owed).
