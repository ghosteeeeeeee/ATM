# Current State — brain_auditor #261 2026-11-14 12:55 UTC
**Last Updated: 2026-11-14 12:55 UTC**
**Updated by: brain_auditor #261. Prior: #260 2026-11-14 08:46 UTC (preserved in git history).**

## HEADLINE — JUP ANTI-CHASE EVAL MEASURED + INDEPENDENTLY REPLICATED: 4/4 PRE-REG BARS PASS, SHIP BLOCKED BY SIGNIFICANCE + fk

1. Pre-registered eval due 11-17 was executed early: rsi_14>=55 at detect blocks 50-54 jup trades / 15d-of-data
   saving **+$1.35..1.47** (bar +$0.50), kept WR **64.15% ≥ baseline 61.54%** (bar: not down), both time-halves
   blocked-negative, direction split BOTH negative (LONG -1.10 / SHORT -0.25).
2. **Independent own-conclusions replication PASS** — `brain/verdicts/jup_antichase_replication_2026-11-14.md`
   (separate SQL, Fisher/Welch hand-computed + scipy cross-check).
3. **NO SHIP**: Fisher p=0.379 / Welch p=0.122 > 0.05 (house Step-5c rule), fk=29% >> 20%, blocked WR still
   56% (not a bad-setup cohort), effect $0.09/day. jup-SCOPING mandatory — same rule would annihilate
   atr-trend- (21/21 rsi>=55, net +0.05). Re-open at blocked-n>=100 or p<0.05.
4. **0 trading-constant changes**, 4 ops dispositions, 1 AMPLIFY emit (EARLY).

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h | 14T 57.1% +0.03 GREEN |
| 7d/14d/30d | 98T 48.0% -1.86 / 293T 51.2% -3.71 / 682T 49.9% -7.23 |
| armed vs never 14d | 141T 91.5% +8.08 vs 152T 13.8% -11.79 |
| chop-bleed dollar | 7d 93.7 / 14d 94.6 / 30d 92.0 = BREACH all 3 (2nd run) |
| trailing-30 avg loser | -0.1063 vs KPI -0.070 (26/30 never-armed) = 2nd leg failing |
| entry-feature anatomy | rsi_exec / gap / momentum / tape: NO armed-vs-never separation (arm rates flat 53-57%) — no entry gate derivable; exitstack 11-15 + prearm 11-21 own the remedy |
| arm-rate tripwire | NOT met (7d LONG 42.1%<50 but SHORT 55.0% not >55; 14d SHORT 54.9%) |
| sub-50 n>=15 | 0 new (ai-trader CEO; pc- LONG net +0.15 noise; warrior n=11) |

### 2. AUTOPSY + SHADOW
- **48h recovery_replay (adverse-first, selfcheck PASS): n=12 = 0/11/1 NEVER (CFX #16883) → wrong-side
  refuted 88th** (#61 p=0.116, #84 t=-0.04). 24h: 3 LONG hard_max against short tape = pattern #2 (owned
  by long-bypass-regime-shadow 11-17); #16896 MFE 0.778→manual_sl = armed giveback (prearm owns).
- **Contrarian join re-ran 12:30Z (mandate): pc- flip 49.0% n=351 — DECAY from 64.6% (Oct-28), demote
  vindicated, >=58% re-promote now further away.** rider 42.1% do-not-flip. overall 43.5% n=1847.
- shadow_trader 12:33Z: pm_trail +15,060 vs hard_max -18,202 = trail-or-nothing. PREARM live 132 lines.
- oscillator FROZEN / wyckoff RETIRED / rr ORPHANED = 3/6 + prearm. floor join fresh 04:36Z due 11-15.

### 3. SHORT-RELAX WEEKLY RE-CHECK (queued by #260) — CRITERION FAILS
Token-day dedup fwd_4h ISO-week sign runs: **SLOPE-FILTER 0 consecutive POS weeks** (W41-W45 all NEG,
W46 first POS = partial); **SHORT-BB-DEAD-ZONE 1** (W44 NEG breaks). Named gates fail
3rd-consecutive-same-sign-week → short-relax STAYS CLOSED. (SHORT-RSI-CEILING / EXEC-RSI-HARD-FLOOR /
SHORT-REGIME-GATE each show W43-W45 POS but were never the named gates; weekly n=3-24 = noisy.)

### 4. AMPLIFY + CREATIVE
- **Emitted: `amplify-pcv6-extreme-short-cell`** (EARLY n=8, due 11-21, NO-SHIP default) — only uncovered
  positive n>=5 30d cell. Two prior emits today (#259 slope-jup, #260 r2v2). Flip-KPI: 0 this run (stated).
- atr-trend-short-cell-watch early re-measure: 5T 100% +0.32 → 13T 69.2% **+0.06** = decayed to noise;
  close as no-cell at 11-16 unless >= +0.25.
- Creative x3: AT-pin census REJECTED-WITH-DATA (t=-0.96, fk 35.5%, prior art AT-acceptance fix 10-21) ·
  UGB-PT race tripwire FIRED n=5 then SUPPRESSED (0 closes/8d) → investigation closed · weekly same-sign tracker.

### 5. LAST-RUN VERIFY (#260/#259) — ALL PASS
MFE_CUT False + 0 closes · pc+ absent from validated set (3 members) · PREARM True + 132 live lines ·
pc- demote holding (CONTRARIAN_LIVE=False) · recovery selfcheck exit 0 · session lock absent ·
hermes_constants EMPTY git diff · size-reduce absent = 1.0x · slippage BUILD #1 still owed (default fired) ·
#260's queued gate_shadow fwd_4h leaderboard re-run DONE (above).

### 6. READINESS (2026-11-14 12:55 UTC)
**1 open: BTC #16905 ai-trader-pending SHORT @67402 (mark ~67170 = +0.34%, SL 67812, TP 66283, 5.4h).**
Watchdog BE@67402 steer **NOT executed**: at read BTC 1m closes BELOW EMA300 67236 since 12:33 — the steer's
'WHILE closes hold ABOVE' condition is inverted; if below-streak ≥10 min the steer self-retracts (its own text).
Regime 12:20: aggregate SHORT_BIAS 24S/9L · btc_15m LONG_BIAS vs 4h SHORT_BIAS disagree · continuum AT
(resolving below) · vol LOW · zscore STRONG_NEG · auto CHOP/MANAGE_ONLY → **HOLD bracketed; no fresh LONGs;
no entries until 1m sustains one side 15-30m with volume; trail-family first; size 1.0x.**

**Queue:** 11-15 floor same-sign + exitstack DUAL-KPI read + confirm 2 kills + win-side-capture · 11-16
atr-trend (close-no-cell note) · 11-17 jup batch (anti-chase verdict: bars PASS / significance FAIL) +
atrs parity + 5 short-exempt shadows · 11-18 grind/re-promote(49% far)/jup-flat/xmirror · 11-19 jup HIGH
+ storm · 11-20 grind-underdeploy/compaction/vb-/warrior · 11-21 prearm first read + slope-jup walk +
r2v2 clone-hunt + short-relax weekly re-check (method shipped) + pc-v6 cell bar.
**CEO owed:** prearm enforce GO · pc- demote veto · slippage-column BUILD #1 (OVERDUE) · steer-001.
**Housekeeping:** session_brain rebuild owed 16 runs.
