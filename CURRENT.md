# Current State — brain_auditor #282 2026-11-20 12:55 UTC
**Last Updated: 2026-11-20 12:55 UTC**
**Updated by: brain_auditor #282. Prior: #281 2026-11-20 04:45 UTC (preserved in git history).**

## HEADLINE — owed stop-tighten candle-walk RAN 1 day early: limb (i) FAIL → pre-registered scope-widen REVERT executed (tuple 8→2), guardian restarted, jup/vb clamp untouched

1. **Walk shipped+run** (`brain/analysis/stop_tighten_scope_walk_2026-11-20.py`, --selfcheck PASS): 30d NEW6 stop-family losers n=45 — **net +$0.29/30d vs +$1.00 bar = FAIL limb (i)**; PASS fk 1.1% (1/87), PASS n>=30, PASS 5/5wk same-sign. Per-source binds all >=0 (pc+ +0.17 / r2v2 +0.07 / bbsq +0.03 / bbbv2 +0.02; pc-, vb-long zero).
2. **BLIND SPOT FOUND+CORRECTED**: walk reads stored stop_loss — post-widen every clamped trade stores exactly 0.750 → classed "tighter_sl_no_bind" (delta 0), hiding the feature's realized value. ENFORCE-log join (19 distinct NEW6 clamped ids across rotated archives; grep needs `-a` + signal→id join since ENFORCE lines carry no signal name) + no-clamp exit-stack replay (arm 0.40 / trail 0.20 / orig-SL / 8h UNIVERSAL_MAX_HOLD) of the 9 clamp-bound losers: **6 of 9 were on recovery paths** (4 recovered to entry, 3 r2v2 trail-armed would-be wins) → clamp value per 12d live window **-$0.55..+$0.56** → corrected limb (i) **-$0.26..+$0.85/30d — no variant robustly >= $1.00**.
3. **REVERT EXECUTED 12:40Z** per pre-registered clause (registry amplify-stoptighten-scope-widen, CEO consult 20261108T180116Z): `STOP_TIGHTEN_SOURCES = ('jup_yolo_mirrored','volume-buildup-')`, restore path = re-append 6 entries (comment carries it); **guardian restarted 12:41Z** (import-time binding); cap 0.75 + ENFORCE True + substring matching UNCHANGED. py_compile PASS, stale_comment_linter --strict clean, payoff probes B/C4 PASS (A7/A8/C6 fail-by-design post-revert — docstring marked HISTORICAL SHIP GATE), 0 open trades at revert. **CEO: veto = re-append.**
4. **AMPLIFY**: light screen #282 already logged (6 positive 30d cells all claimed/in-flight → 0 NEW, formal weekly Mon 11-23); this run CLOSED-REVERTED the scope-widen amplify entry (its owed walk). Flip-KPI 0 this week (fade FAIL-fk, scope-widen reverted — both near-term candidates gone).

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 48h / 7d / 14d / 30d | 15T 60.0% **+0.15** / 31T 51.6% -0.30 / 111T 49.5% **+0.54** / 205T 48.3% -1.59 / 642T 52.5% -4.16 |
| LONG vs SHORT 7d | LONG 55T 41.8% -0.11 / SHORT 56T 57.1% **+0.65** (shorts = tape side) |
| armed vs unarmed 7d | 56T 85.7% **+4.46** vs 55T 12.7% **-3.92** |
| chop-bleed (never-armed % gross loss) | 7d **84.6%** (-4.13 of -4.88) |
| regimes 7d | NORMAL only positive 25T 68.0% **+1.71** / HIGH -0.73 / EXTREME -0.44 |
| exit families 7d | TRAIL 39T 94.9% +2.80, TP +1.52 vs HML+ATR_SL+manual_sl 38T 0% **-4.11** |
| 14d mandate | trail 71T 67W 94.4% **+4.18** vs hard_max_loss 26T 0W **-2.75** |
| kill screen | 14d sub50 n>=15 net>0 = ai-trader-pending SHORT only (CEO) → **0 new** |

### 2. AUTOPSY (48h, recovery_replay adverse-first, selfcheck PASS)
n=14 = 0 never-adverse / 10 recovered / **3 NEVER** (IMX atr-trend- · GOAT r2v2-long7 MFE 0 MAE 1.03 · ALT atr-trend- MAE 0.92) → **WRONG-SIDE REFUTED 133rd** (#61 p=0.116, #84 t=-0.04).

### 3. SHADOW (mandate re-runs done)
| Source | Status |
|---|---|
| contrarian join | **RE-RAN 12:30Z** — overall flip 47.5% n=2109; rider chi2 p=4.3e-39 per-signal only; **pc-\|BTC-BELOW 64.6% n=48 HOLDS** (tape-split 11-25); pc-\|AT 28.6% = never blanket |
| floor join | **RE-RAN 12:42Z** — 49.1% vs 45.1% p=**0.132** (decaying 0.0877→0.132) → NO-SHIP stands, note appended |
| shadow_trader | 12:41Z — exit A/B pm_trail **+18,941** vs hard_max **-24,571** = trail-or-nothing; all gates negative-EV (earning keep) |
| rider-fade guard | **COLLECTING (58 lines / 37 distinct tokens vs 15 bar = MET early)** — logs to `/var/www/hermes/logs/signals.log`, NOT `/root/.hermes/logs/` (wrong-file false alarm recorded) |
| oscillator / wyckoff / rr | archived / retired / orphaned = 3/6 + walk |

### 4. REJECTED-WITH-DATA (never re-propose)
- Keep scope-widen on corrected/upper-bound math — corrected straddles and none robustly clears the bar (this run).
- Floor-admit over always-admit (p trajectory now 0.132, route closed).
- Book-wide drift gate (#280), arm-rate throttle (#195), time blocks (standing ban).

### 5. LAST-RUN VERIFY (#281) — ALL PASS
rider-fade walk script present→executed ✓ · fade guard collecting (58/37 tokens) ✓ · jup-long-blocked clonehunt open 11-23 ✓ · contrarian mandate ✓ · session lock absent ✓ · size-reduce absent=1.0x ✓ · kill-line checkpoint 12-03 only ✓ · 0 Tracebacks ✓ (constants diff now = this run's intended revert).

### 6. READINESS (2026-11-20 12:55 UTC)
**0 open = FLAT** — regime 15m **SHORT_BIAS** vs 4h **SHORT_BIAS** (agree = with-tape), trend STRONG_DOWN, continuum BELOW, vol NORMAL, zscore STRONG_NEG, velocity FALLING → short-with-tape under EMA300 preferred; LONGs only on sustained EMA300 reclaim WITH volume; trail-family first; size 1.0x; 0 watchdog steers, health good.

**Queue:** **11-21 batch of 11 + amplify-cell-conf-tilt-floorproof + prearm soak read** → **11-21/22 rider-fade formal read (bar 37/15 already met)** → 11-22 win-side + ai-trader cell → 11-23 jup-long clonehunt + formal weekly AMPLIFY → 11-25 watch-contrarian tape-split + pcfade → 11-26 storm-waiver → 11-29 tape-at-long → 11-30 hl-copy + long-rsi-floor30.
CEO: **scope-widen REVERT ratify/veto (NEW)** · LONG arm tripwire · mult-150 label · exitstack dual-read · slippage BUILD #1 · ai-trader-pending MFE-giveback observation. Flip-KPI: 0 conversions this week.
