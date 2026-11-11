# Current State — brain_auditor #246 2026-11-11 00:50 UTC
**Last Updated: 2026-11-11 00:50 UTC**
**Updated by: brain_auditor #246. Prior: #245 2026-11-10 21:00 UTC (preserved in git history).**

## HEADLINE — CONTRARIAN WATCH EXTENDED (fee, not edge); ATR-TREND CLONE-HUNT REGISTERED; WINNER-CELL REVERT STILL OVERDUE

1. **Contrarian fade watch DUE 11-11 → EXTEND to 11-18 (adjudicated this run).** n=36 since 10-27, gross +0.130 / fees 0.375 / **NET -0.245** (bare pc-: -0.127). Promote gate (NET>=0) UNMET — but the problem is FEES at $11.69 notional (gross/trade 0.004-0.006 vs fee/trade 0.0104), not direction: shadow flip **64.6% n=350 STANDS** (join re-ran 00:30Z), real WR 40% vs baseline 27-38%, kill gate (0 fills) unmet. Disable would destroy a working instrument over a sizing problem. v6-combo fade (6T, gross -0.060) flagged: exclude from promote math or kill v6 fade at 11-18. **CEO input wanted: fade-size bump OR min-expected-move>2x-fee filter (creative idea logged).**
2. **AMPLIFY NEW: `amplify-atr-trend-short-clonehunt`** (type c, due 11-18, NO-SHIP default). gate_shadow atr-trend- SHORT blocked 42/42 would-win → **token-day dedup = n=5** (ETC/BABY/HYPER/BCH/WLFI) << n>=15 bar. Collection-only. Controls: hh-hl+ 0/21 WW, continuum-trend+ sum -10.51 = gates correct, do not exempt.
3. **CEO ACTION STILL REQUIRED: `WINNER_CELL_SIZE_MULT` 1.25→1.0 revert is 25h overdue** (deadline was 00:00Z 11-10). Constant still 1.25 at `hermes_constants.py:1174`; auto-flip denylist blocks self-fire. Bar FAILs: A -0.014 / B -1.13 / C +0.04. One-line CEO act or explicit extension.
4. **Side-find: ai-trader-pending/manual trades carry NULL momentum_state/z_score_tier** — 23T/14d `-0.68` (63% of NULL cohort), 30d 63T 36.5% WR. Instrumentation gap, NOT a tradeable feature (blocking on missing metadata is fragile). Flag to main-session: stamp metadata on ai-trader path.
5. **0 trading-constant changes** — hermes_constants.py EMPTY git diff, session lock ABSENT, CEO_PROTECTED intact, size-reduce absent = 1.0x, 0 Tracebacks today.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| contrarian watch deadline | EXTEND 11-18 (kill gate unmet, promote fee-negative, shadow intact) |
| atr-trend- clone-hunt | 42/42 WW raw → 5 deduped = below bar → registered collection |
| entry-filter fisher scan | REJECTED — arm-rate predictors ≠ net (#139 lesson: rising 14d net -2.26 @56% WR) |
| deep-dive kill targets | 0 new (all owned) |
| winner-cell revert | STILL overdue → resurfaced |

### 2. NUMBERS (fresh PG 00:45Z)
- 24h **14T 57.1% -0.40** | 7d **97T 51.5% -1.48** (armed 14d 176T 86.4% **+8.34** vs unarmed 200T 24.5% **-12.35**)
- 14d exit family: trail **193T 91.2% +11.50** vs chop_exits **132T 0.8% -15.50**
- chop-bleed: **98.0% / 95.4% / 94.2%** (7/14/30d) — all ≥92% push threshold = entry-quality zone
- arm rate ~45% across windows | RR asymmetry 7d: breakeven WR 61.6% vs actual 51.5%

### 3. SHADOW (3/5 usable)
- **contrarian join 00:30Z (mandate):** overall flip **43.8%** n=1609 · **pc- 64.6% (226W/124L) LIVE, chi2 p=0.3747 uniform** · rider 38.0% do-NOT
- floor join 11-10 20:36Z fresh, jsonl 4674 rows → 11-15 read on track
- shadow_trader 00:33Z: exit A/B **pm_trail +12,942 vs hard_max -15,260** = trail-or-nothing; gates justified (COMBO-STALE 48% avg -0.15)
- oscillator FROZEN · wyckoff RETIRED (file moved to archive — not an anomaly) · rr ORPHANED

### 4. AUTOPSY + AMPLIFY
- **48h recovery_replay (adverse-first, selfcheck PASS): n=17 = 6 never-adverse / 9 recovered / 2 NEVER (FOGO -0.13, GMX -0.10 immaterial) → WRONG-SIDE REFUTED 74th consecutive.** 16/17 never-armed.
- **AMPLIFY: 1 NEW** — amplify-atr-trend-short-clonehunt (type c, due 11-18). Flip-KPI: 0 new conversions this run (week day 2); prior week's cited.
- Creative x2: fade fee-hurdle · clone-hunt registration (see audit_recommendations).

### 5. READINESS (2026-11-11 00:50 UTC)
**1 open — HOLD: WCT #16857 atr-trend- SHORT** entry 0.029636 / SL 0.03008 / TP 0.02904 / 3x / `-0.63%` price against, 0.9h. btc_15m LONG_BIAS vs btc_4h SHORT_BIAS disagree; trend_quality STRONG_DOWN agrees with short; continuum AT; vol LOW. Bracketed → hold per watchdog; no steers; no size added while volume LOW; trail-family first; size 1.0x.

**Queue:** **CEO: winner-cell revert (OVERDUE 25h)** + fade fee/size input → 11-12 storm x3 → 11-13 pc+ kill-review + vb- clone-hunt + linreg fill + chop-exempt → **11-14 EXIT-STACK DAY** (13 entries) → 11-15 floor same-sign → 11-16 atr-trend cell → 11-17 jup batch + atrsl + 7 shadow bars → **11-18 contrarian fade read + atr-trend clone-hunt n** → 11-19 jup HIGH OOS (net>0 bar; n=18, 7d -0.09 sign-flip caution) → 11-21 structure-flip + conf-tilt → 12-15 ugb-bypass-hole.
**CEO owed:** winner-cell revert · fade fee/size review · mult-150 sign-off (folds into revert) · unclog-waiver [35,45) re-measure · fade-ctx fee-net · jup Option-D monitor.
