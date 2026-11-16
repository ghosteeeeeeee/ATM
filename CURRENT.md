# Current State — brain_auditor #268 2026-11-16 00:55 UTC
**Last Updated: 2026-11-16 00:55 UTC**
**Updated by: brain_auditor #268. Prior: #267 2026-11-15 20:47 UTC (preserved in git history).**

## HEADLINE — [COPY-STALE] TELEMETRY SHIPPED; CELL-WATCH CLOSED NO-CELL; 0 CONFIG CHANGES

1. **[COPY-STALE] SHIPPED** (hl_fill_monitor.py, log-only): after a successful trader_exit close,
   compute age from PG `open_time`; if <5s print `[COPY-STALE] ... phantom mirror`.
   Rationale: 3/5 hl_copy 7d closes were 1.1s phantoms (WLD x2, ZRO) dragging the signal-health KPI.
   Selfcheck: 311s → no flag, 1.1s → flag, NULL open_time safe, py_compile PASS.
   **Gate decision deferred** until 7d phantom rate measured (telemetry-first, pre-registered #267).
2. **amplify-atr-trend-short-cell-watch -> done NO-CELL** (deadline was 11-16 00:00Z):
   30d NORMAL SHORT cell 15T +0.11 << +0.25 materiality bar; HIGH 14T -0.22;
   armed/never split 19W/100% vs 0W/11L = exit-side lever only (11-17 exitstack + 11-18 clone-hunt own it).

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d | 27T 33.3% **-0.01** / 112T 43.8% -1.11 / 262T 50.8% -2.72 / 654T 50.5% -4.96 |
| armed vs never 14d | ARMED 136T 89.0% **+8.59** vs NEVER 126T 9.5% **-11.31** |
| chop-bleed $ share | 7d **85.2%** (50/57) / 14d 90.2% / under 92 gate |
| LONG arm rate 7d | **42.5% (17/40)** <50 tripwire — CEO flag owed from #266, not duplicated |
| trail vs chop-stop 14d | TRAIL 120T 95.8% **+7.42** vs CHOP_STOP 97T 1.0% **-11.12** |
| 7d by regime | NORMAL 48T +0.69 · EXTREME 26T -0.15 · HIGH 38T -1.65 |
| sub-50% n>=15 (14d) | 0 kill candidates (ai-trader-pending SHORT net +0.63 = CEO) |

### 2. REJECTED WITH DATA
- **atr-trend- HIGH-regime block re-test:** prior art #267 — fk 29% of 7d winners >> 20% bar;
  30d split-half unstable. Not re-proposed.

### 3. AUTOPSY + SHADOW
- **48h recovery_replay (adverse-first, selfcheck PASS): n=18 = 3 / 12 / 3 NEVER**
  (HYPE jup SHORT -0.12, ALGO atr-trend- -0.11, ZRO hl_copy -0.01) = 16.7% structural ->
  **wrong-side REFUTED 95th** (#61 p=0.116, #84 t=-0.04). Dominant mode = giveback 12/18 (exit side).
- **Contrarian join RE-RAN 00:30Z (mandate):** overall flip 42.5% n=1657 |
  **pc- 65.1% (69/106) STABLE** post-window-fix | rider 40.9% do-NOT.
- **Floor join RE-RAN 00:37Z:** floor_only 49.9% n=1754 vs always 46.2% n=355;
  bars n>=200 PASS, same_sign FAIL -> **CONFIRMS #264 NO-SHIP, route CLOSED**.
- **shadow_trader 00:32Z:** exit A/B pm_trail **+16,152** vs hard_max **-20,149** = trail-or-nothing.
- oscillator FROZEN / wyckoff RETIRED / rr ORPHANED => **2/5 shadow sources answerable.**

### 4. AMPLIFY (weekly offense)
0 NEW proposals — all 6 n>=10 net>0 30d cells in-flight or below materiality
(ai-trader NORMAL SHORT 27T +1.36 · bb-squeeze+ NORMAL LONG 40T +0.82 · vb- HIGH 19T +0.42 ·
pc- NORMAL LONG +0.15 < bar · atr-trend- NORMAL +0.11 < bar (closed NO-CELL) · jup HIGH +0.04).
Flip-KPI 0 this week (stated). **stop-tighten-slippage-column OVERDUE 11-14 (owner main-session, 12th resurface).**

### 5. LAST-RUN VERIFY (#267) — ALL PASS
session_brain keys fix HOLDING (10 queries native keys) · join retention guard HOLDING (pc- identical 65.1%) ·
CONTINUUM-BLOCK tag 1487 lines · constants EMPTY · CEO_PROTECTED 13/13 · kill flags correct ·
lock absent · size-reduce absent=1.0x · 0 Tracebacks · recovery selfcheck PASS ·
gate_shadow_health selfcheck PASS 37 gates · checkpoint_registry 0 pending.

### 6. DRIFT / SIDE-FINDs
- **MED:** exitstack-day-kpi-1114 early read FAILS avg-loss bar (-0.111 vs -0.070) BUT post-11-14
  armed split healthy (22W +2.42 vs 17L -1.59) — dual-metric creative proposed; formal eval 11-17.
- **HIGH (not mine):** slippage-column BUILD #1 overdue 11-14, 12th resurface, owner main-session.
- **LOW:** hl_copy.db closed_at ages disagree with PG open-close (different clocks); COPY-STALE uses PG.

### 7. READINESS (00:55Z)
**0 open / 0 steers / health good.** Regime: **15m SHORT_BIAS vs 4h LONG_BIAS + continuum BELOW
+ accel NEGATIVE + vol LOW + zscore STRONG_NEG + trend STRONG_DOWN = chop pin.**
→ no fresh counter-trend entries; trail-family first; size 1.0x;
LONGs only on sustained reclaim WITH volume; SHORTs only under EMA300 with 4h aligned.

**Queue:** **11-17** exitstack formal (dual-metric) + 13 dispositions + jup batch →
**11-18** pc-fade re-promote + 7 amplifys + watch-contrarian-live deadline →
**11-19/20/21** remaining amplify batches → **11-22** ai-trader cell →
**11-27** pc-weight/linregfade → CEO: slippage BUILD #1 (12th) + LONG arm 42.5% + NET-KPI.
