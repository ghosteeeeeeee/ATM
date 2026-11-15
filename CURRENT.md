# Current State — brain_auditor #266 2026-11-15 16:55 UTC
**Last Updated: 2026-11-15 16:55 UTC**
**Updated by: brain_auditor #266. Prior: #265 2026-11-15 08:55 UTC (preserved in git history).**

## HEADLINE — CONTRARIAN OUTCOME-JOIN RETENTION-WINDOW BUG FOUND + FIXED (2 joins); ARM-TRIPWIRE RUN 2 FIRED → CEO FLAG

1. **THE JOIN WAS MEASURING CANDLES UP TO 71h AFTER THE SIGNAL.** `contrarian_outcome_join.classify()`
   had no lower bound on its 5m window: any shadow row older than candles.db **30d retention (floor =
   now-30d, slides hourly)** silently read retention-floor candles as the "post-signal" window, so
   outcomes rewrote themselves every run. **246/352 pc- decided rows contaminated today (70%)**;
   three reads of the same jsonl today: 56.8% (#265 08:30Z) → 45.7% (16:30Z) → 45.2% (pre-fix 16:44Z).
   Contamination: **0% on Oct-27..Nov-11 (the clean 64.6% n=350 era)** → 14% by 11-13 → 74% by 11-15.
2. **FIXED (root cause, both live joins, zero trading behavior):** `WINDOW_SLACK_S=1800` → NO_DATA when
   the first available candle starts >30min after the signal + selfcheck fixture.
   `analysis/contrarian_outcome_join.py` + `analysis/floor_admit_outcome_join.py`, `--selfcheck PASS exit=0` both.
   Corrected: **pc- flip-WR 65.1% (69/106), halves 67.3/63.2 same-sign**, tape pc-|BELOW **80.6% n=62** /
   AT 37.5% n=40; rider 41.0% n=1524 do-NOT; overall 42.6%. Floor verdict UNCHANGED (p=0.1384 NO-SHIP).
   **⇒ the 11-13 CONTRARIAN_LIVE demote (#257) fired on a corrupted metric — CEO flagged, NO action taken**
   (re-promote = CEO/T sign-off + live fee gate NET -0.245; registered as `amplify-pcfade-windowfix-repromote-review`).
3. **ARM-RATE TRIPWIRE RUN 2: BOTH LEGS MET → CEO FLAG WITH LEADERBOARD, NO AUTO-CONFIG**
   (checkpoint `arm-tripwire-run2-1115` disposed done): 7d LONG arm **45.2% (19/42)** <50 AND SHORT
   **55.9% (38/68)** >55. LONG unarmed bleed **-2.13/23T at 4.3% WR** (ai-trader -0.31, atr-trend+ -0.29,
   jup -0.26, bb-squeeze+ -0.20); **SHORT leg is healthy** (armed SHORT 84.2% WR +2.76) — defect is
   exclusively LONGs never reaching +0.40% trail → same class as tape-AT census (re-measure 11-29).

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d | 20T 45.0% **+0.63** GREEN / 110T 46.4% -0.74 / 262T 51.9% -2.53 / 653T 50.2% -5.64 |
| armed vs NEVER 7d | ARMED 57T 82.7%→**82.5% +4.13** vs NEVER 53T 7.5% **-4.87** |
| chop-bleed (prompt SQL) | 7d **84.8%** (47/55, -5.01/-5.91) / 14d 90.2% / 30d 90.8% — below 92% gate, no escalation |
| arm tripwire | **RUN 2 FIRED both legs** → CEO flag issued, no config |
| 7d regime | NORMAL 49T +0.72 · HIGH 33T -1.26 · EXTREME 26T -0.04 · FLAT 2T -0.16 |
| loser clusters 7d | ai-trader-pending SHORT 13T -1.52 (8 never) · jup SHORT 9T -1.13 (9/9 never) · atr-trend- SHORT 7T -0.82 (7/7 never) |
| sub-50% n>=15 (14d) | 0 new actionable (ai-trader-pending 31T 35.5% net +0.32 = CEO; jup = 11-17 batch) |

### 2. AUTOPSY + SHADOW
- **48h recovery_replay (adverse-first, selfcheck exit=0): n=15 = 1 / 12 / 2 NEVER**
  (HYPE #16914 jup SHORT -0.12, ZRO #16927 hl_copy LONG -0.01) → **wrong-side REFUTED 93rd**
  (#61 p=0.116, #84 t=-0.04). Dominant mode = giveback (12/15) = exit/arming side.
- **Chop anatomy:** 20/20 of the 7d atr_sl_hit losers never armed (+0.40%) = chop entries; trail never fires.
- **Contrarian join (FIXED, 16:44Z):** pc- 65.1% n=106 · rider 41.0% n=1524 · overall 42.6% n=1628.
- **shadow_trader 16:31Z:** 105,137 signals; pm_trail **+15,915** vs hard_max **-19,552** vs rr_engine
  -7,490 = trail-or-nothing; peak-buyer worst grind-breakout+ (giveback +3.08).
- floor join fixed + verdict unchanged (p=0.1384 NO-SHIP) · oscillator FROZEN / wyckoff RETIRED / rr ORPHANED = 2/5.

### 3. AMPLIFY (weekly offense)
EMITTED `amplify-pcfade-windowfix-repromote-review` (due 11-18, NO-SHIP default, 4 bars incl. fee NET>=0
and CEO+T sign-off; caveat: per-token heterogeneity untestable at n=106 → tape split is the scope test).
Why-not: all other n>=10 net>0 30d cells in-flight (ai-trader NORMAL SHORT 11-22, bb-squeeze+ x4,
vb- HIGH 11-20, atr-trend-/jup 11-18/11-19) or below materiality (pump-chain- NORMAL LONG +0.15).
Flip-KPI 0 this week (stated). **atr-trend- NORMAL SHORT watch: 13T +0.06 << +0.25 → CLOSE NO-CELL at 11-16 deadline.**

### 4. LAST-RUN VERIFY (#265) — ALL PASS
CONTINUUM-BLOCK log text present (:3222) · tape-at-long-remeasure-1129 registered · arm-tripwire checkpoint
registered+disposed · session_brain keys live · constants EMPTY · CEO_PROTECTED 13/13 · kill flags 8/8 ·
lock absent · size-reduce absent=1.0x · 0 Tracebacks (last 500) · recovery selfcheck exit=0 ·
shadow_disposition --selfcheck PASS.

### 5. SIDE-FINDs / DRIFT
- **FIXED:** retention-window class (2 joins) — see headline.
- **LOW:** `analysis/contrarian_both_sides_2026-10-26.py` same unbounded pattern (dated one-off, never
  scheduled — do not rerun without the guard).
- **HIGH (not mine):** slippage-column BUILD #1 overdue 11-14, **10th resurface**, owner main-session.
- **MED (known):** session_brain dup 18th.

### 6. READINESS (16:45Z)
**3 open, all atr-trend- SHORT, all bracketed, size 1.0x:** HYPER #16930 (SL 0.040736/TP 0.039765 lev3,
12min) · MNT #16931 (SL 0.37847/TP 0.36726, 9min) · ENS #16932 (SL 3.88547/TP 3.76849, 6min) — flat at
entry. 0 steers, portfolio good. Regime 16:38: 15m/4h LONG_BIAS vs continuum BELOW + velocity SLOW +
accel NEGATIVE + LOW volume = **disagree (chop undertone) → hold the 3 shorts (tape-BELOW aligned),
NO fresh entries until 15m/4h and continuum agree; trail-family first; size 1.0x.**

**Queue:** NEXT RUN after 11-16 00:00Z → **close `amplify-atr-trend-short-cell-watch` NO-CELL unless 30d
net >= +0.25** (16:45Z read = +0.06) → 11-17 **exitstack formal** (28 post-ship closes vs n>=30; trailing-30
avg loser -0.1163 vs bar -0.070 = failing) + jup eval batch + flip1 → 11-18 **pc-fade corrected re-promote
review** + watch-contrarian-live fee gate + 5 amplifies → 11-22 win-side GO + ai-trader replication →
11-29 tape-AT re-measure.
**CEO owed:** ARM-TRIPWIRE RUN-2 FLAG (this run) · demote-metric invalidation (no action before 11-18) ·
slippage BUILD #1 (OVERDUE) · win-side shadow-build GO.
