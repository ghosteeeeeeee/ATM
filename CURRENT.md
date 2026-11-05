# Current State — brain_auditor #225 2026-11-05 16:55 UTC
**Last Updated: 2026-11-05 16:55 UTC**
**Updated by: brain_auditor #225. Prior: #224 2026-11-05 08:45 UTC (preserved in git history).**

## HEADLINE — Two live-bug fixes shipped: (1) jup_liq first fire stored corrupt price 7.658e16 (feed amount always 0 → fixed-point never scaled; exec guard ratio ~1e12 skipped it) — now get_hl_price-first; (2) 4h regime scanner token universe was blind to signal tokens (dead paths + list-only parse of dict) leaving regime_4h coverage 81.5% < 90% bar — fixed, re-measure at ~19:18Z. Chop-bleed still owns 94.8% of 7d dollar losses. Harvest ship 3/4 bars FAIL early (due 11-07).

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| **jup_liq price bug (FIXED)** | yolo feed amount=0 on 27/27 liquidates → notional/amount never ran → raw 1e12 fixed-point stored. First fire 16:27 SKIPPED by exec SUSPICIOUS PRICE ratio 997650469245x. Fix: get_hl_price first, else raw/1e12. Selfcheck PASS. |
| **4h regime_4h coverage (FIXED root cause)** | 81.5% (53/65 recent-7d) < 90% bar. Dead paths + list-only parse. Fixed: WWW_DATA + dict + recent-traded pull. Bad tokens (CASHCAT/CC/FARTCOIN/ZORA) now in universe. |
| **Chop-bleed 7d** | **94.8% dollar** (-10.60 of -11.18 never-armed). 14d trail 268T 81.3% +13.02 vs chop/stop 121T 0% -14.97. |
| **Harvest early FAIL** | rolling-50 jup 44-45% (bar <35) + HML 7d 37 (bar <15) + daily net unsustained = 3/4 FAIL, due 11-07. CEO pre-position revert. |
| **FADE-CRASH pre-read** | 17/23 coherent=NO → KEEP pre-flip (bar needs direction-coherent). Deadline 11-06. |
| **gate_shadow capture** | 15-30% all major gates (BTC-CRASH 0% in db). 11-06 re-audit must use log-reparse frame. |
| **AMPLIFY** | New: amplify-jup-short-high-cell WATCH (12T 66.7% +0.28 early, conflicts jup-share). Flip-KPI 0 this week. |

### 2. NUMBERS (fresh PG)
- 24h **6T 66.7% '+0.28'** | 7d **267T 53.9% '-1.36' RED** | 14d 409T 55.0% '-1.91' | 30d 781T 45.7% '-5.15'
- 7d armed 138T 90.6% '+8.69' vs never 129T 14.0% '-10.05'
- Contrarian join 16:30Z: overall 43.8% n=1362 | pc- ~64% LIVE | rider do-NOT
- Floor join 16:30Z: COLLECT p=0.1315

### 3. AUTOPSY + SHADOW
- **48h adverse-first n=20 = 7 never-adverse / 13 recovered / 0 NEVER → WRONG-SIDE REFUTED 79th**; selfcheck PASS
- shadow_trader: 65655 signals; gates healthy; pm_trail dominant; dead shadows = zombie list

### 4. LAST-RUN VERIFY (#224, ALL PASS)
Kill-premise correction HOLDING (cell eval 11-13) | arm-rate trigger 0 qualifiers | WINNER-CELL-SIZE firing (FOGO 07:57 x1.25) | contrarian join fresh | constants untouched by #225 | session lock absent | 0 new Tracebacks | size-reduce absent=1.0x.

### 5. READINESS (16:55)
**0 open trades.** Regime: 15m SHORT_BIAS / 4h SHORT_BIAS / continuum BELOW / vol LOW / MARKDOWN / DECLINING → SHORT side favored, no fresh counter-trend LONGs; trail-family first; size 1.0x.

**Queue:** 11-06 fade-btc-crash + momentum re-measure + gate-shadow log-reparse + candle audit → 11-07 harvest revert + jup regime review → 11-09 zombie-purge → 11-10 four bars → 11-12 storm ENFORCE bar (streak 2/3) → 11-13 pc+ kill-review CELL-SCOPED.
**CEO:** harvest early-fail pre-position · winner-cell-mult-150 · stop-tighten label · NET-KPI.
