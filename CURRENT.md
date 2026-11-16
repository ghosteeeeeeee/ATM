# Current State — brain_auditor #269 2026-11-16 04:36 UTC
**Last Updated: 2026-11-16 04:36 UTC**
**Updated by: brain_auditor #269. Prior: #268 2026-11-16 00:55 UTC (preserved in git history).**

## HEADLINE — 4 FILTERS MEASURED, 4 REJECTED-WITH-DATA; 0 CONFIG CHANGES

1. **atr-trend- SHORT inverse-confidence block (conf>=75):** blocked 5W/4L net -0.35,
   fk 26.3% >20%, fisher p=0.687, n=30 → REJECT (global CONF_FILTER_MIN=70 prior art).
2. **require SHORT gap_at_entry<-0.2:** aggregate p=0.041 BUT split-half +0.44/-0.34
   SIGN FLIP, kills 62% of winners, PUMP_CHAIN_SHORT_DEAD_GAP already live → REJECT.
3. **NO-LONG-WHILE-BTC-BELOW-EMA300:** fk 24.2% >20%, p=1.0, AT band worse
   (-1.72/37T), heavy prior art (#139, tape-AT 11-29, ema300-underdeploy) → REJECT.
4. **CREATIVE: atr-trend- TAT extension** — winner arm delays le45=8 / 45-60=2 /
   60-90=4 / gt90=5 of 19W (avg 70.9m max 185m); TAT@45 kills 57.9% of winners,
   @60 47.4%, @90 26.3% all >>20% while all 10 never-armed losers already die <=90m
   via existing SL stack → REJECT.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d | 23T 34.8% **+0.03** / 111T 44.1% -1.03 / 254T 49.2% -3.16 / 651T 50.5% -4.87 |
| armed vs never 14d | ARMED 128T 88.3% **+8.15** vs NEVER 126T 9.5% **-11.31** |
| chop-bleed (cnt/$) | 7d 87.5/85.0 · 14d 89.4/90.2 · 30d 86.2/90.6 — all UNDER 92 gate |
| LONG arm rate 7d | **42.5% (17/40)** <50 tripwire — CEO flag owed #266, not duplicated |
| key exits 14d | PM trail 75T 96% **+4.58** · hard_max 46T 0% -5.40 · atr_sl 46T 0% -5.31 |
| 24h worst cluster | atr-trend- SHORT 8T 37.5% **-0.31** (11-15) — exit-side, owned 11-17/11-18 |
| sub-50% n>=15 (14d) | 0 kill candidates (ai-trader-pending 31T 35.5% net +0.32 = CEO) |

### 2. REJECTED WITH DATA
- inverse-confidence atr-trend- SHORT (fk 26.3%, p=0.687)
- require SHORT gap<-0.2 (split-half sign flip, 62% winner kill, prior art)
- NO-LONG-WHILE-BELOW (fk 24.2%, AT band worse, prior art)
- atr-trend- TAT extension (fk 57.9/47.4/26.3% at 45/60/90m)

### 3. AUTOPSY + SHADOW
- **48h recovery_replay (adverse-first, selfcheck PASS): n=18 = 3 / 12 / 3 NEVER**
  (HYPE jup -0.12, ALGO atr-trend- -0.11, ZRO hl_copy -0.01) = 16.7% structural ->
  **wrong-side REFUTED 96th** (#61 p=0.116, #84 t=-0.04). Giveback 12/18 = exit side.
- **Contrarian join RE-RAN 04:30Z (mandate):** overall 42.9% n=1672 |
  **pc- 69W/37L = 65.1% STABLE** | rider 41.4% do-NOT | heterogeneity p=2e-33.
- **Floor join 00:37Z:** same_sign FAIL -> **CONFIRMS #264 NO-SHIP, CLOSED**.
- **shadow_trader 04:31Z:** pm_trail **+16,351** vs hard_max **-20,384** = trail-or-nothing.
- oscillator FROZEN / wyckoff shadow-only 0 live / rr ORPHANED => **2/5 answerable.**

### 4. AMPLIFY (weekly offense)
0 NEW proposals — all 6 n>=10 net>0 30d cells in-flight or below +0.25 materiality
(ai-trader NORMAL SHORT +1.36→11-22 · bb-squeeze+ NORMAL +0.82→11-21 · vb- HIGH
+0.42→11-20 · pc- NORMAL LONG +0.15 < bar · atr-trend- NORMAL +0.11 closed NO-CELL ·
jup HIGH +0.04→11-19); early n>=5 cells covered (warrior/r2v2/pcv6/jup-flat) or below bar.
Flip-KPI 0 this week (stated). **stop-tighten-slippage-column OVERDUE 11-14 (13th resurface).**

### 5. LAST-RUN VERIFY (#268/#267) — ALL PASS
COPY-STALE code present hl_fill_monitor.py:661-671 + hermes-hl-copy daemon active +
0 hl_copy closes since = correct-by-traffic · cell-watch disposition done ·
session_brain native kwargs HOLDING (8 queries) · join retention guard HOLDING
(pc- identical 65.1%) · constants EMPTY · CEO_PROTECTED 13/13 · size-reduce absent=1.0x ·
0 Tracebacks · recovery selfcheck PASS · checkpoint_registry 0 pending · lock absent.

### 6. DRIFT / SIDE-FINDs
- **LOW:** hl_fill_monitor.py has no --selfcheck flag (invoking it runs the live
  monitor); #268 selfcheck was manual — add 3-line flag or fix record wording.
- **HIGH (not mine):** slippage-column BUILD #1 overdue 11-14, 13th resurface, main-session.
- **MED:** session_brain duplicate-text records still owed rebuild.

### 7. READINESS (04:36Z)
**0 open / 0 steers / health good.** Regime: **15m SHORT_BIAS vs 4h LONG_BIAS + continuum
BELOW + accel NEGATIVE + vol LOW + zscore STRONG_NEG + trend STRONG_DOWN = chop pin.**
→ no fresh counter-trend entries; trail-family first; size 1.0x;
LONGs only on sustained 15-30m reclaim WITH volume; SHORTs only under EMA300 with 4h
aligned; mid-band = no trade.

**Queue:** **11-17** exitstack formal (dual-metric) + jup batch + 13 dispositions →
**11-18** pc-fade re-promote + 7 amplifys + watch-contrarian-live (pc- 65.1%) →
**11-19/20/21** remaining amplify batches → **11-22** ai-trader cell →
**11-27** pc-weight/linregfade → **11-29** tape-AT re-measure →
CEO: slippage BUILD #1 (13th) + LONG arm 42.5% + NET-KPI.
