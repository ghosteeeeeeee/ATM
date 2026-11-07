# Current State — brain_auditor #232 2026-11-07 08:55 UTC
**Last Updated: 2026-11-07 08:55 UTC**
**Updated by: brain_auditor #232. Prior: #231 2026-11-07 04:52 UTC (preserved in git history).**

## HEADLINE — shadow_trader's UNKNOWN bucket was hiding 9,055 blocked rows. The `blocked@approval:` parse gap was logged as a LOW follow-up on 2026-10-29 and sat unshipped 9 days, blindfolding BOTH `shadow_trader --report` and `shadow_mode_analysis.py` (they share `gate_name`). Shipped shared `gate_name_from_reason()` + one-time relabel of 8,716 rows. Every gate is still avg-negative-EV — the "gates earn their keep" conclusion holds, but attribution is now complete for the first time (approval-CONFLUENCE 873 @57%, SHORT-RSI-HARD-FLOOR 391 @56% were invisible). 0 trading-constant changes; 1 AMPLIFY proposal registered with a fresh measured threshold curve.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| **Gate-label fix (HEADLINE, ops)** | `gate_name_from_reason()` shared by ingest + backfill (single source of truth — two parsers = drift). Parses `blocked@approval:` (head-segment before `:` / `|`), `combo_key stale`→COMBO-STALE, `expired: APPROVED combo`→HOTSET-EXIT, `trade failed at execution:`→EXEC-FAIL, `post-claim block:`→first token. Backfill: 9,046 of 9,055 UNKNOWN relabeled (8,716 + 330 cooldown skips -> COOLDOWN-SKIP), residual 9 = blacklist expiries (documented honest bucket); bug_hunter SAFE TO DEPART 6/6. py_compile PASS, 10-case truth table PASS, `--report` re-run. **Corrected top-10: CONFLUENCE-EXPIRY 15,604 @47% '-0.13' · COMBO-STALE 3,296 @44% '-0.15' · CTX-GATE 2,419 @53% '-0.08' · EXEC-BLOCK 1,321 @48% · HOTSET-EXIT 920 @49% · CONFLUENCE(approval) 873 @57% '-0.08' · BTC-CRASH 578 @44% · EXEC-FAIL 486 @46% · PUMP-CHAIN-SHORT-HIGH 452 @40% · SHORT-RSI-HARD-FLOOR 391 @56% '-0.04'.** All avg_pnl < 0 → no gate verdict flips. |
| **PRE-ARM LOCK thr curve (AMPLIFY, new)** | Unarmed closed trades by peak (mfe_pct), ceiling = cohort losers→~0 in pnl_usdt: **thr 0.10 +19.73/30d · 0.15 +16.92 · 0.20 +13.75 · 0.25 +10.14 · 0.30 +8.17 · 0.40 +3.85** (14d: 9.24/7.71/5.85/3.62/2.59/0.79). Independently reproduces #231's 0.25 band. Cohort-winner pnl flat ~+6.8-7.0 across thr 0.10-0.25 → ceiling is loser-driven; **fk (winner pass-through) is the only unknown** → candle-walk bar. Registered `amplify-prearm-breakeven-lock` due 11-14, arms flat-BE vs peak-proportional, ONE variable, net>=$2.00 units-guarded ∧ fk<20% ∧ 14d same-sign ∧ armed untouched, default NO SHIP. 14d never-armed MFE<0.30 = 114T sits BELOW all thresholds → not coverable here (TAT/stop-tighten own it). |
| **Kill screen** | **ZERO candidates** — 14d n>=15 sub-50% WR AND net<0 = no rows. R:R trio (WR-positive, net-negative, exit-side): jup LONG 101T 61.4% '-1.04' (avgwin +0.063/avgloss -0.137), vb- SHORT 48T 60.4% '-0.91', pc+ LONG 30T 50.0% '-0.22'. Entry filters closed by #228 pre-registered negative result. |
| **#231 verify** | DailyFillCap identity **PASS** (pipeline.log 04:58:23 `[blocked ETH LONG jup_yolo_mirrored]`); leaky-limiter confirmed — cap self-released (now 12 opens <15, fee-net still '-0.67', 0 SKIPs since 04:58). LOW: a second same-second SKIP call carried empty context (token/source None on that path) → fold into 11-08 05:03Z re-read. Combo pin HELD (1.3/1.6 + PINNED_COMBO_WEIGHTS). |
| **Winner-cell AMPLIFY screen** | 30d n>=10 net>0: bb+ NORMAL 44T +0.76 · pc+ EXTREME 72T +0.50 · vb- HIGH 19T +0.42 · jup HIGH 15T +0.40 · pc-,v6- EXTREME 10T +0.30 · pc- NORMAL LONG 29T +0.24. 4/6 in-flight; **pc- cells REJECTED-WITH-DATA by #230** (daily sign-flip / fat-tail) — not re-proposed (why-not stands). |

### 2. NUMBERS (fresh PG)
- 24h **13T 46.2% '-0.52' RED** | 7d **190T 53.2% '-1.20' RED** | 7-14d 195T 57.4% '-0.90' | 14-30d 382T 36.9% '-4.59' | **30d 780T 46.2% '-7.21'**
- 7d: **armed 87T 83.9% '+4.23' vs unarmed 115T 29.6% '-5.87'** | **trail-family 100T 93.0% '+6.67' vs chop-family 71T 0% '-8.14'**
- 14d exits: profit-monster-trail 141T 97.9% +8.15 · mfe_exit 36T 83.3% +1.67 · ugb_pt 31T 67.7% +1.62 ‖ atr_sl_hit 57T 0% '-6.31' · hard_max_loss 43T 0% '-5.63' · cut-loser 13T 0% '-1.92'
- 14d never-armed MFE<0.30: **114T '-12.64' 1.8% WR** — the bleed class, below every pre-arm threshold
- 24h losers n=7 all stopped (5 atr_sl + 1 hard_max + 1); winners n=6 (trail/mfe/rr exits)

### 3. SHADOW (3/6 usable + gate table fixed)
- **contrarian join RE-RAN 08:31Z (mandate)**: overall flip **43.1% n=1442** (620W/820L/2 shallow); **pc- 64.6% n=350** (226/124) = Oct-27 PROMOTE stands, uniform p=0.375, by tape BELOW 67.8% n=211 / AT 58.6% n=111 / ABOVE 64.3% n=28; **btc-pump-rider+ 36.2% do-NOT-flip** token-het chi2 p=8.9e-25 → per-signal only
- floor join 11-06 20:53Z: floor_only 1391 **49.3%** vs always_admit 210 43.8% Fisher **p=0.159 → COLLECT** (bar 11-15); raw file fresh 11-07 03:03Z
- shadow_trader 72,188 signals; exit A/B **pm_trail '+10,923'** vs hard_max '-12,540' / rr_engine '-4,831' / cut_loser '-2,184' = trail-or-nothing again
- oscillator FROZEN/archived · wyckoff RETIRED (file gone) · rr ORPHANED (mtime 10-04)

### 4. AUTOPSY + DRIFT
- **48h recovery_replay (adverse-first, selfcheck PASS): n=8 = 3 never-adverse / 5 recovered / 0 NEVER → WRONG-SIDE REFUTED 59th consecutive** (#61 p=0.116, #84 t=-0.04). The loss driver is no-momentum entries exiting via stops, not direction.
- **Flip-KPI MET this week**: STOP_TIGHTEN_ENFORCE=True live since 11-04 (constants:764) + TAT-C enforcement live + bb/warrior combo uninert 11-06 (pin held). mult-150 still awaiting CEO label (since 11-04).
- Drift: NONE new. constants EMPTY diff · protected 13/13 · session lock ABSENT · size-reduce absent = 1.0x · 0 Tracebacks (log spans today) · checkpoint_registry 0 pending (9/9 done) · watchdog steers [].

### 5. READINESS (08:55Z)
**0 open / 0 steers / portfolio good — FLAT 9.7h (last open 11-06 23:02Z) = CORRECT posture.** Regime: **btc_15m LONG_BIAS vs btc_4h SHORT_BIAS (disagreement = the chop) / continuum AT / vol LOW / velocity SLOW / accel FLAT / wyckoff ACCUMULATION / market_phase DECLINING / trend_quality STRONG_UP.** Brakes: DailyFillCap RELEASED (12<15, fee-net '-0.67' still red — leaky limiter as modeled); gate stack binding: CONFLUENCE 54 + CONTINUUM 39 kills in last 4h, all on <=53%-would-win negative-EV cohorts (verified in corrected shadow table). → no counter-trend entries, trail-family first, size **1.0x**.

**Queue:** **11-08 05:03Z DailyFillCap post-context re-read (count braked candidates; check the empty-context second call)** → 11-09 zombie-purge → 11-10 five bars + uninert next-100 + fade-ctx → 11-11 HML post-ship + watch-contrarian → 11-13 linreg-fade / chop-exempt / vb- clonehunt / pc+ kill-review → **11-14 pre-arm-lock candle walk (NEW)** + neutral-exempt + mult-150 CEO chase + atrtrail + stop-tighten-eval → 11-15 floor/wyckoff → 11-17 jup eval batch.
**CEO:** mult-150 label pending since 11-04 · 34 combo-weight divergences precedence review · NET-KPI.
