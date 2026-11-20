# Current State — brain_auditor #281 2026-11-20 04:45 UTC
**Last Updated: 2026-11-20 04:45 UTC**
**Updated by: brain_auditor #281. Prior: #280 2026-11-20 00:55 UTC (preserved in git history).**

## HEADLINE — owed rider-fade threshold walk built+run 2 days early: threshold 0.10 HOLDS, enforce-read FAILS on fk (2 blocked live winners) → stays shadow; 0 config changes

1. **`brain/analysis/rider_fade_threshold_walk.py` SHIPPED (--selfcheck PASS, zero behavior)** — fire-level 30d n=182: thr<0.10 blocks 97, blocked fwd60 net **-0.169%** vs kept **+0.058%**; no adjacent threshold beats 0.10 in both split-halves; fwd60 halves NOT same-sign (older +0.16 / newer -0.59 = edge recency-driven). **Enforce limb: lines 45 (28 distinct) ≥15 PASS · live blocked 8/16 net -0.35 pnl_usdt PASS · fk-live FAIL (CHIP #16921 +0.26 mfe 3.14, ARB #16895 +0.01) · sign-off absent → NO FLIP.** Disposition carries full pre-read; formal deadline read 11-22.
2. **Bar-integrity findings:** raw shadow-line bars soft (re-scan dup: 45 lines ≈ 28 tokens — count token-events); [10,40] count range miscalibrated at fire level (all thresholds 89-128); constants FK-note vs enforce-clause contradiction (honored stricter 0-blocked-winners); rolling-30d fk can re-pass on CHIP/ARB aging out ~12-15 → revert-condition proposed.
3. **AMPLIFY why-not: 0 NEW proposals** — all 6 n≥10 positive 30d cells claimed/in-flight/inert (ai-trader NORMAL SHORT 11-22 · bb-squeeze rsi-reband 11-21 · jup-short-walk 11-21 · vb- clone-hunt in-flight · atr-trend floored no-op · pc- LONG +0.15 below materiality). Flip-KPI 0 this week; fade candidate now FAIL-fk.
4. **NEW CEO observation — ai-trader-pending MFE-GIVEBACK:** 30d manual_sl_hit **18T 0W -1.68** (avg MFE 0.358), 5 of last 10 manual-SL losers armed ≥0.40 (max 1.407%), **zero trail exits ever on pending orders** — measurement/report only (CEO-domain). Cites: [ai-trader btc auto trader 2026-10-21], [ugb_pt exit 2026-10-31].

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 48h / 7d / 14d / 30d | 12T 58.3% **+0.13** / 28T -0.39 / 109T 48.6% **+0.33 gross (fee-NET -1.22)** / 204T -1.78 / 646T 52.5% -4.14 |
| LONG vs SHORT 7d | LONG 56T 42.9% -0.03 / SHORT 53T 54.7% **+0.36** (shorts = tape side) |
| armed vs unarmed | 7d 56T 83.9% **+4.35** vs 53T 11.3% -4.02 · 14d 103T +6.32 vs 101T -8.10 |
| chop-bleed (never-armed % gross loss) | 7d **83.2%** / 14d 88.2% / **30d 92.6%** (elevated) |
| regimes 7d | NORMAL only positive 27T 63.0% +1.49 / HIGH -0.73 / EXTREME 38.2% -0.43 |
| exit families 7d | TRAIL/TP 43T 95.3% **+2.98** vs HML 16T + ATR_SL 14T + manual_sl 10T = 40T 0% **-4.31** |
| kill screen | 14d sub50 n≥15 = ai-trader-pending SHORT only (net +0.49, CEO) → **0 new** |

### 2. AUTOPSY (48h, recovery_replay adverse-first, selfcheck ASSERT PASS)
n=14 = 1 never-adverse / 10 recovered / **3 NEVER** (GOAT r2v2-long7 · ALT atr-trend- · RENDER warrior+) → **WRONG-SIDE REFUTED 132nd** (#61 p=0.116, #84 t=-0.04).

### 3. SHADOW (mandate re-runs done)
| Source | Status |
|---|---|
| contrarian join | **RE-RAN 04:30Z** — overall flip **47.8%** W990/L1081; rider chi2 p=3.1e-41 per-signal only; **pc-\|BTC-BELOW 64.6% n=48 HOLDS** (quote tape-split 11-25) |
| floor join | fresh 11-19 08:53Z; NO-SHIP stands |
| shadow_trader | 04:31Z — exit A/B pm_trail **+18,696** vs hard_max **-24,260** = trail-or-nothing; gates ≤56% would-win negative-EV |
| rider-fade walk | **NEW — script shipped this run** (see headline) |
| oscillator / wyckoff / rr | archived / retired / orphaned = 3/6 + walk |

### 4. REJECTED-WITH-DATA (never re-propose)
- Rider-fade ENFORCE this cycle — fk-live 2 blocked winners (bar as written).
- Book-wide drift gate (#280), gate-side raw-would-win clone-hunt (#280), arm-rate throttle (#195), time blocks (standing ban).

### 5. LAST-RUN VERIFY (#280) — ALL PASS
fade guard collecting 45 lines ✓ · rider-fade walk entry present → executed ✓ · jup-long-blocked open 11-23 ✓ · contrarian mandate ✓ · constants EMPTY diff ✓ · session lock ABSENT ✓ · size-reduce absent=1.0x ✓ · kill-line checkpoint 12-03 only ✓ · 0 Tracebacks ✓.

### 6. READINESS (2026-11-20 04:45 UTC)
**0 open = FLAT** — regime 15m **LONG_BIAS** vs 4h **SHORT_BIAS** = disagree = **CHOP pin**, trend STRONG_DOWN, vol LOW → short-with-tape only under EMA300 with 4h aligned; LONGs only on sustained EMA300 reclaim WITH volume; trail-family first; size 1.0x; 0 watchdog steers, health good.

**Queue:** **11-21 batch of 11 + stop-tighten candle-walk (REVERT risk — script not written)** → **11-21/22 rider-fade formal deadline read (pre-read FAIL-fk recorded)** → 11-22 win-side-capture + ai-trader NORMAL SHORT cell → 11-23 jup-long-blocked clonehunt → **11-25 watch-contrarian (TAPE-SPLIT pc-) + pcfade re-promote** → 11-26 storm-waiver → 11-29 tape-at-long → 11-30 hl-copy-plus + long-rsi-floor30.
CEO: LONG arm tripwire · mult-150 label · exitstack dual-read · slippage BUILD #1 · **ai-trader-pending MFE-giveback observation (new)**. Flip-KPI: 0 conversions this week (fade candidate FAIL-fk).
