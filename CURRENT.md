# Current State — brain_auditor #240 2026-11-08 16:50 UTC
**Last Updated: 2026-11-08 16:50 UTC**
**Updated by: brain_auditor #240. Prior: #239 2026-11-08 12:50 UTC (preserved in git history).**

## HEADLINE — STOP-TIGHTEN 11-14 EVAL ROTATION DRIFT RESOLVED + FREQUENCY COLLAPSE DECOMPOSED (NOT A BUG)

1. **Stop-tighten id bar MET pre-deadline:** the >=20 bar counts **[STOP-TIGHTEN-SHADOW] distinct trade-id joins** (not ENFORCE clamps). Archive (`pipeline.log.20261107001010.gz`, retained 30d by pipeline-log-rotate.service) + current log = **86 real ids 16632-16818 over 10-31..11-08** (ENFORCE-only = 5 ids = wrong tag). Evidence + reproduce command appended to `data/shadow_disposition.json`. #239 MED closed, zero behavior.
2. **43T/day → 5-7T/day is NOT a bug:** detections -54% (LOW-vol regime) + DailyFillCap brake ON through 11-07 16:20Z + gate block share stable 51-74% (no Nov-4/5 spike). Correct chop-response. Creative: opportunity-cost KPI pre-registered.
3. **0 config changes** — session lock absent, constants EMPTY diff, nothing passed vacation review-queue bars.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| **stop-tighten rotation (headline)** | RESOLVED — 86 SHADOW ids ≥ 20 bar; 11-14 read must source archive+current, SHADOW tag only |
| **trade-frequency collapse** | DECOMPOSED — detections -54% + fillcap brake (released 11-07 16:20) + stable 60% block share; not a gate regression |
| **chop-bleed** | 7d **94.6%** / 14d **94.7%** (BOTH ≥92%) / 30d 88.8% — chronic, remedy VETOED as inert, owned by 11-14 stack; no blind re-escalation |
| **SL-placement landmine (side-find)** | `trades.stop_loss` mutated by PM trail for winners (min 0.003%) — losers-only or open-time snapshot required; contaminated census NOT cited |
| **losers-only census (corroboration)** | 14d losers SL>0.75% 114T -13.64 vs ≤0.75% 48T -2.82 — confounded (signal-mix/exit-family), appended to scope-widen disposition; candle-walk (11-21) stays decision evidence |
| **#239 verify** | shadow_dup_check selfcheck PASS · dedup disposition open 11-10 · drop-pcplus open (pc+ EXTREME 65T $0.00) · clamps live · joins re-run · constants EMPTY · 0 Tracebacks today · registry 0 pending — **ALL PASS** |

### 2. NUMBERS (fresh PG 16:40Z)
- 24h **9T 55.6% $0.00 FLAT** | 7d **152T 55.9% -1.79** (armed 81T 93.8% +4.57 vs unarmed 71T 12.7% -6.36) | 14d 393T 54.5% -3.36 (armed 208T 90.4% +11.51 vs unarmed 185T -14.87) | 30d 768T 46.9% -6.45
- **RR asymmetry:** 7d breakeven WR **63.3%** vs actual 55.9% (avg win +0.062 vs avg loss -0.107) — loss SIZE is the lever
- 14d exit families: profit-monster-trail 139T **+7.82** 97.8% vs atr_sl_hit 58T **-6.36** 0% + hard_max_loss 44T **-5.73** 0%
- 14d sub-50% n≥15: pc+ 29T 48.3% -0.27 (NO-KILL/11-13) · pc- 32T 37.5% **+0.07** (contrarian-owned) — **0 new targets**

### 3. SHADOW (3/6 usable)
- **contrarian join 16:30Z (re-ran):** overall flip 43.1% n=1442 · **pc- 64.6% (226W/124L) LIVE uniform p=0.375 = Oct-27 PROMOTE stands** · rider 36.2% do-NOT (chi2 p=8.9e-25)
- floor join 08:30Z same-day: 49.2% vs 43.7% **p=0.1411 COLLECT (11-15)**
- shadow_trader 76,185: exit A/B **pm_trail +11,411 vs hard_max -13,378** = trail-or-nothing · shadow_dup_check selfcheck PASS
- oscillator FROZEN · wyckoff RETIRED · rr ORPHANED

### 4. AUTOPSY + AMPLIFY
- **48h recovery_replay (adverse-first, selfcheck PASS): n=5 = 2 never-adverse / 3 recovered / 0 NEVER → WRONG-SIDE REFUTED 67th consecutive** (#61 p=0.116, #84 t=-0.04).
- **AMPLIFY: 0 new proposals (rule-3 why-not recorded).** Top cells all in-flight (size-125 11-10 · vb- clone-hunt 11-13 · jup walk 11-14/high-cell 11-19) or below materiality (pc- EXTREME +0.30, pc- NORMAL +0.19); early cells n=6-7 <10. **Flip-KPI MET this week** (#239), 0 new conversions.
- Creative x2: opportunity-cost decomposition KPI · losers-only SL census (corroboration, landmine documented).
- constants EMPTY · session lock ABSENT · size-reduce absent = 1.0x · 0 pending checkpoints · watchdog steers = 2 cluster warnings (non-auto).

### 5. READINESS (2026-11-08 16:50 UTC)
**3 open LONGs, all bracketed — HOLD.** SOL jup_yolo_mirrored #16818 4.2h -0.12% SL 0.60% · IMX continuation+ #16821 0.4h +0.67% SL 0.48% · ARB atr-trend+ #16822 0.4h +0.14% SL 1.01% (out-of-stop-tighten-scope BY DESIGN = live scope-widen evidence for 11-21). Steers: IMX+ARB cluster + 3-long portfolio (warnings). Regime: **15m LONG_BIAS vs 4h SHORT_BIAS = disagree = chop**, continuum AT, vol LOW, velocity SLOW, trend_quality STRONG_DOWN → **NO fresh counter-trend entries; trail-family first; LONGs only on sustained EMA300 reclaim WITH volume; size 1.0x.**

**Queue:** **11-09 zombie-purge DECIDE (default NO CHANGE, pre-adjudicated)** → **11-10 gate-shadow-dedup fold + size-125 + fade-ctx + rsi-ceiling-75 + conf-filter-parity + jup-atrsl-parity + mfe-cut-arm-be + ichimoku-dampen** → 11-11 contrarian watch → 11-12 storm-waiver → 11-13 pc+ kill-review + vb- clone-hunt + linreg-fade → **11-14 stop-tighten eval (id bar MET=86, SHADOW tag, source archive+current) + drop-pcplus + probe-080 + bbsqueeze reband/neutral-exempt + mult-150 + atrtrail-clip + prearm-breakeven + TAT-age-sweep** → 11-15 floor → 11-19 jup HIGH OOS → 11-21 conf-tilt + scope-widen walk.
**CEO:** mult-150 sign-off (evidence decayed — judge ex-pc+ or drop first) · jup HIGH cell HOLD · unclog-waiver EXPIRY re-measure [35,45) before renewal (expired 11-03).
