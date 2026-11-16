# Current State — brain_auditor #270 2026-11-16 12:51 UTC
**Last Updated: 2026-11-16 12:51 UTC**
**Updated by: brain_auditor #270. Prior: #269 2026-11-16 04:36 UTC (preserved in git history).**

## HEADLINE — [COPY-STALE] WAS ON AN UNREACHABLE PATH (FIXED); EXPOSURE KPI SHIPPED; 0 CONFIG CHANGES

1. **[COPY-STALE] dead-path (HIGH):** #268's <5s phantom guard lives in
   hl_fill_monitor `copy_exit` (writes `trader-exit(0x..)`), but all 3 live phantoms
   (WLD x2 + ZRO, 11-15, 1.06-1.12s) close via position_manager **XMIRROR-EXIT**
   (`exact-mirror: ...`). Measured `COPY-STALE` in pipeline.log = **0** vs
   `[XMIRROR-EXIT]` = 15 → the detector could never fire. **FIX:** log-only `<5s`
   guard added to shared `close_paper_position()` — one guard, every caller.
   py_compile PASS, zero trading behavior.
2. **EXPOSURE KPI SHIPPED:** `collect_exposure()` + `_merge_intervals()` →
   `watchdog.json exposure{hours,in_market_pct,trades}` + `--selfcheck` (5 cases PASS).
   CEO must-have asked twice and never built [can you use the watch (1), 2026-10-02:
   "Exposure tracking — This is a metric gap… Trivial to add"; youtube watch, 2026-11-08].
   **First read: 24h 32.8% in-market / 19 closes (~25 min avg hold); 72h 66.4%.**
3. **DOC FIX:** auditor prompt Step 5b pointed at `data/prices.db` = **0-byte, dead
   since 2026-10-07, referenced by no script** → corrected to `data/candles.db`
   `candles_1m` (179 tokens, 7.6M rows).

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d | 19T 31.6% **-0.32** / 110T 43.6% -1.17 / 247T 50.2% -2.87 / 653T -5.01 |
| steer-001 URGENT | 12/20 lost, WR 30%, health=critical → ANSWERED (chop pin, 0/19 losers armed) |
| arm rate (mfe>=0.40) | 7d 49.1% · 14d 51.4% · 30d 52.2% — no collapse |
| wins vs losses arm 7d | WINNERS 93.5% vs LOSERS 14.7% |
| exposure | 24h 32.8% · 72h 66.4% in-market |
| armed vs never 14d | ARMED 88T 90.9% **+5.02** vs NEVER 159T 27.7% **-7.89** = 100% of 7d $ loss |
| atr_sl_hit 14d | 46T 0% **-5.31**, only **1/46** reached +0.40% MFE (avg 0.197) = never-momentum; jup owns 17/46 |
| 7d by regime | NORMAL 47T +0.55 · EXTREME 26T -0.15 · HIGH 37T -1.57 |
| sub-50% n>=15 (14d) | 0 kill candidates (ai-trader-pending 29T 37.9% but net **+0.49** = CEO) |

### 2. REJECTED WITH DATA
- **SHORT × HIGH-vol block:** 30d 63T -0.71 but split-half **+0.27 / -0.98 SIGN FLIP**;
  30d WR 61.9% + negative net = R:R not entry; vol-gate "not suited for HIGH" already live.
- **atr-trend- HIGH block:** prior art #267/#269, fk 29% of 7d winners >> 20% bar.
- **arm-rate standing trigger (#224 pre-reg: n>=20 ∧ arm%<30 ∧ net<0):** **0 qualifiers**
  — lowest n>=20 cell = jup LONG 47.4%; 7d = 53.8% / 56.0%. No dampen ships.

### 3. AUTOPSY + SHADOW
- **48h recovery_replay (adverse-first, selfcheck PASS): n=19 = 3 / 13 / 3 NEVER**
  (HYPE jup -0.12, ALGO atr-trend- -0.11, ZRO hl_copy -0.01) = 15.8% structural →
  **wrong-side REFUTED 97th** (#61 p=0.116, #84 t=-0.04). Giveback 13/19 = exit side.
- **NEW pre-entry chase test (48h n=36, 1m candles):** winners entered 0.139% against
  their direction over prior 15m vs losers 0.025% — thin, **no chase signal**.
  Discriminator is post-entry momentum (arm), not entry timing.
- **Contrarian join RE-RAN 12:30Z:** overall 44.6% n=1738 | **pc- 69W/37L = 65.1%
  STABLE** (retention guard HOLDING) | rider 43.2% do-NOT | het p=2.7e-35 → per-signal.
- **Floor join RE-RAN 12:51Z:** floor_only 49.7% n=1780 vs always 46.4% n=364,
  fisher p=0.2478; n>=200 PASS / same_sign_30d **FAIL** → **#264 NO-SHIP CONFIRMED, CLOSED**.
- **shadow_trader 12:33Z:** pm_trail **+16,524** vs hard_max **-20,839** (0% WR) =
  trail-or-nothing; every gate blocks ≤56% would-win negative-EV cohorts.
- **freq_deviation_shadow = ORPHAN PRODUCER:** 1,187 rows, **0 consumers**; today
  flags hl_copy_trader **3.82× over baseline** at 14d WR 18.2% n=11.
- oscillator FROZEN / wyckoff PENDING / rr ORPHANED → **3/6 sources answerable.**

### 4. AMPLIFY (weekly offense)
0 NEW — why-not logged: all 6 n>=10 net>0 30d cells in-flight or below materiality
(ai-trader NORMAL SHORT 29T +1.22→11-22 · bb-squeeze+ NORMAL 40T +0.82→11-17 ·
vb- HIGH 19T +0.42→11-20 · pc- NORMAL 31T +0.15 < bar · atr-trend- NORMAL 15T +0.11
closed NO-CELL · jup HIGH 24T +0.04→11-19); early n=5-9 covered or below +0.10.
Flip-KPI 0 this week (stated). **stop-tighten-slippage-column OVERDUE 11-14 (14th).**

### 5. LAST-RUN VERIFY
#268 COPY-STALE **FAILED-PATH FOUND AND FIXED** · #267 session_brain kwargs HOLDING
(8 queries) · #267 join retention guard HOLDING (pc- 65.1% identical) · #266/#269 LONG
arm tripwire **STILL OPEN 42.5% (17/40)** CEO-owed · constants EMPTY · 0 Tracebacks ·
recovery selfcheck PASS · checkpoint_registry 0 pending · lock absent.

### 6. DRIFT / SIDE-FINDs
- **HIGH (not mine):** slippage-column BUILD #1 overdue 11-14, **14th resurface**, main-session.
- **MED:** freq_deviation_shadow orphan producer (creative #2 proposes the consumer).
- **MED:** 11 more 0-byte `data/*.db` placeholders (brain.db, hermes*.db, candles_1m.db…).
- **LOW:** session_brain duplicate-text records still owed rebuild.

### 7. READINESS (12:51Z)
**0 open / 1 urgent steer / health critical.** Regime: **15m LONG_BIAS vs 4h SHORT_BIAS
+ continuum BELOW + trend STRONG_DOWN + vol LOW + zscore STRONG_NEG + auto_trader CHOP
×6 / decision BRACKET = chop pin.** → no fresh counter-trend entries; trail-family first;
size 1.0x; LONGs only on a sustained 15-30m reclaim WITH volume; SHORTs only under
EMA300 with 4h aligned; mid-band = no trade.

**Queue:** **NEXT RUN** verify `exposure` in live watchdog.json + first `[COPY-STALE]`
from `close_paper_position` → **11-17** exitstack formal (dual-metric) + 13 dispositions
+ jup batch (atr_sl owns 17/46 of #1 bleed) → **11-18** pc-fade + watch-contrarian-live
+ 7 amplifys → **11-19/20/21** batches → **11-22** ai-trader cell → **11-27** pc-weight →
**11-29** tape-AT → CEO: slippage BUILD #1 (14th) + LONG arm 42.5% + NET-KPI + hl_copy
3.82× over-fire (CEO domain, n=11).
