# Current State — brain_auditor #267 2026-11-15 20:47 UTC
**Last Updated: 2026-11-15 20:47 UTC**
**Updated by: brain_auditor #267. Prior: #266 2026-11-15 16:55 UTC (preserved in git history).**

## HEADLINE — WATCHDOG'S 3 FLAGGED SIGNALS DISPOSITIONED WITH DATA; 0 CONFIG CHANGES (nothing passed bars)

1. **atr-trend- (2 of 3 open shorts) = PAYOFF INVERSION + PERFECT ARM SEPARATION, not an exit defect:**
   30d 29T 65.5% net -0.15 — 19 armed -> 19 wins (+0.046 avg), 10 unarmed -> 10 losses (-0.103 avg).
   Entry features IDENTICAL armed vs never (rsi_detect 70.6/71.4, momentum 14.9/13.9, speed 36.5/33.7,
   gap 0.106/0.125) => **no detect-time entry separator exists** (reproduces #191's census on a fresh family,
   n=29). Entry gate CANNOT see it; the lever is exit-side = 11-17 exitstack read + 11-18 clone-hunt. No change.
2. **jup_yolo_mirrored = 2.0x loss/win asymmetry** (14d 98T 62.2% -0.88; win +0.068 vs loss -0.136).
   OWNED by the 11-17 batch (trail-1xatr / atrsl-parity / cluster-gate / pro-selection) — not re-proposed.
3. **hl_copy_trader "WR 0%" watchdog flag = ARTIFACT + real bleed:** 3 closes today (WLD x2, ZRO) opened and
   closed **1.1s apart via trader_exit** = we copied a position the pro had ALREADY closed in our poll window
   (phantoms paying fees, dragging the signal-health KPI); separately 5 real HML chop-LONG losses -0.42/14d
   (n=11 total -> no gate). **Telemetry proposed ([COPY-STALE] <5s), no kill.**

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d | 26T 38.5% **+0.32** GREEN / 113T 45.1% -0.77 / 268T 51.1% -2.90 / 657T 50.4% -5.45 |
| armed vs never 14d | ARMED 139T 89.2% **+8.73** vs NEVER 129T 10.1% **-11.63** |
| chop-bleed $ share | 7d **85.3%** (50/58 never-armed) / 14d 90.5% / 30d 90.8% — under 92 gate, no escalation |
| LONG arm rate 7d | **42.5% (17/40)** <50 tripwire — CEO flag already owed from #266, NOT duplicated |
| trail vs HML 14d | TRAIL 85T 95.3% **+5.36** vs hard_max_loss 47T 0% **-5.65** |
| 7d by regime | NORMAL 49T +0.84 · EXTREME 26T -0.04 · HIGH 37T -1.56 · FLAT 1T -0.01 |
| sub-50% n>=15 (14d) | 0 new actionable (ai-trader-pending SHORT 27T 40.7% net +0.63 = CEO; rest owned/killed) |

### 2. REJECTED WITH DATA (3 — each would have been a ship)
- **HIGH-regime block:** 30d -3.32 BUT fk = 79 winners... 7d blocks 15 of 51 winners = **29% >> 20% bar** -> REJECT.
- **Book-wide CHASE gate (LONG rsi>=70 / SHORT rsi<=40):** 7d -0.91 / 14d -1.52 / **30d -1.66 vs rest -3.05
  (chase cohort BETTER at 30d = sign flip)**, p=0.29/0.054/**0.92**, 7d fk 23.4% -> never ship (jup-scoped
  anti-chase 11-17 stays the only chase work).
- **Against-tape SHORT gate (btc_trend_bias):** 30d AGAINST 75T 50.7% -0.95 vs WITH 251T 55.8% +0.01,
  same sign 7/14/30d but **p~0.4, -0.013/trade**; SHORT_CONTINUUM + #180 census already cover the axis -> monitor.

### 3. AUTOPSY + SHADOW
- **48h recovery_replay (adverse-first, selfcheck PASS): n=16 = 2 / 11 / 3 NEVER**
  (HYPE jup SHORT -0.12, ALGO atr-trend- SHORT -0.11, ZRO hl_copy LONG -0.01) = 18.7% structural ->
  **wrong-side REFUTED 94th** (#61 p=0.116, #84 t=-0.04). Dominant mode = giveback 11/16 (exit side).
- **Contrarian join RE-RAN 20:30Z (mandate):** overall 42.7% n=1647 | **pc- 65.1% (69/106) STABLE** — the
  #266 retention-window fix holds, no drift | rider 41.2% n=1541 do-NOT | pc-|BELOW 80.6% n=62.
- **Floor join RE-RAN 20:39Z:** floor_only 49.9% n=1755 vs always_admit 45.8% n=349, **p=0.177** — CONFIRMS
  #264's NO-SHIP today; significance decays as n grows (0.138 -> 0.088 -> 0.177). Route CLOSED.
- **shadow_trader 20:39Z:** exit A/B pm_trail **+16,058** vs hard_max **-19,990** vs rr_engine -7,530 =
  trail-or-nothing unchanged. --sweep-arm atr-trend- = No data (source-key mismatch, LOW drift).
- oscillator FROZEN / wyckoff RETIRED / rr ORPHANED => **2/5 shadow sources answerable.**

### 4. AMPLIFY (weekly offense)
0 NEW proposals — all 6 n>=10 net>0 30d cells in-flight or below materiality: ai-trader NORMAL SHORT 27T +1.36
(11-22) · bb-squeeze+ NORMAL LONG 40T +0.82 (11-17) · vb- HIGH 19T +0.42 (11-20) · pc- NORMAL LONG +0.15
below bar · **atr-trend- NORMAL SHORT 15T +0.11 << +0.25 = NO-CELL (cell-watch, closes at 11-16 00:00Z,
pre-deadline read appended)** · jup HIGH 24T +0.04 ~zero (11-19). Flip-KPI 0 this run (stated).
**stop-tighten-slippage-column OVERDUE 11-14 (owner main-session, 11th resurface).**

### 5. LAST-RUN VERIFY (#266) — ALL PASS
session_brain documented-keys fix (11 queries returned title/date/topic/excerpt) · CONTINUUM-BLOCK tag live
(1435 lines) · join retention guard holds (pc- identical 65.1%) · constants EMPTY · CEO_PROTECTED 13/13 ·
kill flags correct (AI_TRADER/DOJI/BB_BOUNCE_LONG/HMACD+/PUMP_CHAIN_V5/OVERSOLD False; MFE_EXIT True;
WINNER_CELL_SIZE_MULT 1.0) · lock absent · size-reduce absent=1.0x · 0 Tracebacks · recovery selfcheck PASS.

### 6. DRIFT / SIDE-FINDs
- **MED:** watchdog flags hl_copy on sub-2s phantoms (KPI artifact) -> [COPY-STALE] telemetry proposed.
- **HIGH (not mine):** slippage-column BUILD #1 overdue 11-14, 11th resurface, owner main-session.
- **MED:** coin_regime x direction cells SIGN-FLIPPED vs #179 (14d LONG+coinLONG_BIAS -2.56 now) = window
  instability; #179 COLLECT stands, no ship on coin_regime cells.
- **LOW:** shadow_trader --sweep-arm source-key mismatch (returns No data for PG signal names).
- **MED (known):** session_brain duplicate excerpts.

### 7. READINESS (20:45Z)
**3 open, all bracketed, size 1.0x:** MET SHORT #16940 (atr-trend-, 0.8h, flat, entered meta_rsi 85.2) ·
ARB LONG #16939 (btc-pump-rider+, -0.29%, 0.8h) · BTC SHORT #16936 (continuum-trend-, -0.38%, 2.0h).
Unrealized -0.08. Regime: **15m + 4h LONG_BIAS vs continuum AT EMA300 64837 + flips 24/25 (churn)** =
disagree -> watchdog steers STAND: no third short while aggregate >=50 long AND 1m >= EMA300; BTC exit on
10x 1m closes >=64850; MET exit on 2x 5m closes >0.2685; ARB exit on 5m <0.1340. **No fresh entries until
15m/4h and continuum agree; trail-family first; size 1.0x.**

**Queue:** first run after **11-16 00:00Z** -> flip `amplify-atr-trend-short-cell-watch` to done (NO-CELL)
-> **11-17** exitstack formal (trailing-30 avg loser <= -0.070, last -0.1117 FAILING) + 13 dispositions due
(jup trio, 5 short-exempt shadows, btc-standalone, setup-recall) -> **11-18** pc-fade corrected re-promote
(fee NET + CEO/T) + watch-contrarian-live + 4 amplifies -> 11-19/21/22 jup-high/ema300/grind/win-side ->
**11-29** tape-AT census.
**CEO owed:** ARM-TRIPWIRE RUN-2 flag (#266) · demote-metric invalidation (no action before 11-18) ·
slippage BUILD #1 (OVERDUE) · win-side shadow-build GO.
