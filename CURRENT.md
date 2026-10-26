# Current State — brain_auditor #154 2026-10-26 04:45 UTC
**Last Updated: 2026-10-26 04:45 UTC**
**Updated by: brain_auditor #154. Prior: #153 03:45 / #152 02:40 / #151 01:40 (preserved in git history).**

## HEADLINE — WAIVER EXPIRES 2026-10-27T00:00Z (19h). SCOREBOARD FIXED BEFORE IT MISLED THE RULING.
- `brain/analysis/waiver_scoreboard_2026-10-23.py` had **WAIVER_GRANT hardcoded to the 2026-10-22
  grant + docstring "It expires 2026-10-24T00:00:00Z"** while T re-armed on **Oct 24 15:40 →
  2026-10-27T00:00:00Z**. As-shipped it reported the **SUPERSET cohort 22T 16W/6L +$0.46** instead
  of the ruling-relevant current waiver. **SHIPPED: window derived from
  `data/vacation_mode.json rules.unclog_waiver` (granted_by + expires), fail-soft legacy fallback
  with source printed; report prints window + expiry; selfcheck asserts file source + non-null expiry.**
- **SHIPPED 2:** `--selfcheck` was FAILING (`BTC gate RSI 45.0 not sub-floor`, #16408). Root cause =
  decider_run renders RSI at `%.1f`, so a true 44.995 prints `45.0 < 45` (gate CORRECT, line
  unverifiable). Added +0.05 display tolerance with a `ponytail:` comment naming the ceiling + a
  knife-side assertion. **decider_run log format deliberately NOT churned** (cosmetic, hot live path,
  buys nothing the tolerance doesn't; legacy lines are 1dp forever).

### WAIVER SCOREBOARD (file window 2026-10-24 15:40 → 2026-10-27 00:00)
30 allow events / 17 tokens · 24 detect blocks (23 knife, 1 non-knife) · **10 exemption-attributable
CLOSED = 8W/2L, WR 80.0%, net +$0.10, 0 OPEN.**

| #692 criterion | verdict |
|---|---|
| c1 n>=5 | **PASS** (10) |
| c2 WR>=40% | **PASS** (80.0%) |
| c3 "no single loss >1%" | **UNRESOLVED — units never specified.** price-move basis worst ICP **-0.8108%** PASS · account basis worst ICP **-4.16%** FAIL (IO -1.25% too) |
| c4 "gate-shadow OOS same sign" | **AMBIGUOUS.** EXEC-RSI-HARD-FLOOR same-sign negative 7/14/30d (-0.17/-0.09/-0.12) = PASS on "stable sign", FAIL on "same sign as the +0.10 realized cohort"; twin EXEC-RSI-DETECT-FLOOR flips POSITIVE at 7d (+0.09) |
| **BINDING** active `constants_change_review_queue` needs **n>=15** | **FAIL** (n=10) |

**CONVERSION RATE (answers creative #693, asked 2026-10-22, never executed) = 100%** — 10 of 10 shorts
opened since the grant required the exemption. **flip#1, not the BB dead zone, IS the short-supply
valve** (SHORT-RSI-HARD-FLOOR still blocks 205 approval-stage events in-window = nothing substitutes).
**Lapse consequence pre-computed: 0 SHORTs open while BTC has bear structure — exactly Oct 24 00:00-15:40.**

### RECOMMENDATION: LET IT LAPSE at 2026-10-27T00:00Z (fail-closed default, zero action)
Fails the active n>=15 bar; c3/c4 undecidable as written; gate-shadow says blocking saves money at
every window; edge is one family (6 of 10 = **volume-buildup- at gate RSI 35.5-43.6, 6W +$0.20**
all profit-monster-trail; other 4 = **-$0.10 = both losers IO/ICP**).
**PRE-REGISTERED narrow contingency instead of a blanket renewal:**
volume-buildup- SHORT `[35,45)` bear-only, knife stays dead — ship ONLY if that cell reaches
**n>=15 AND WR>=60% AND net>+$0.30 AND no single price-move loss >1% AND 30d same-sign**, else stay lapsed.
**T owns the waiver (T-directive territory) — this is recommend-not-decide.**

## REJECTED-WITH-DATA THIS RUN (do not re-derive)
- **pump-chain+ volume-precondition** (run #150's script finally ANSWERED, selfcheck PASS): gate
  **INVERTS** — PASS vol>=1.5x 17T 23.5% `-$0.63` vs BLOCK vol<1.5x 46T 39.1% `+$1.52`; winner-impact
  **18/22 = 81.8%** >> 20% bar → blocking would LOSE +$1.52.
- **LONG 45-55 block**: 14d 56T 26.8% `-$2.62` (fk 15/81 = 18.5% <20%) LOOKS shippable **BUT** 30d
  111T 43.2% `-$0.67` with the older half `+$1.95` = **OOS SIGN FLIP**.
- **LONG entry_rsi_14 >=70 blanket**: 30d 77T net `-$0.03` wash, 34 winners `+$3.88`; per-signal the
  bleed is pump-chain+ only (already queued).
- **ARM-GAP lever**: `mfe>=0.40 AND trailing_activated=False` 14d 50T `-$1.04` **BUT 26/50 are
  PROFIT_MONSTER_BYPASS-by-design** (trailing False is expected, not an arm gap). Excluding bypass:
  7d 12T `+$0.27` / 14d 21T `-$0.07` / 30d 51T `+$2.08` = **WASH**.
- **pump-chain TAT 45m→120m** (shadow sweep n=243): 120m "best" (`-132.54` vs 45m `-147.60`) but
  **EVERY cell negative** = entries, not timeout.
- **pump-chain+ KILL — 8th NO-ACTION**, first time the 14d pre-reg triple actually passes
  (44T 27.3% `-$0.35`) **BUT** the pre-reg pinned Oct 23 and its own text says a miss = "zero change,
  criteria documented as failed" (it missed: 14d was `+$0.02`), **14d/30d SIGN DISAGREEMENT
  (`-$0.35` vs `+$1.84`) = THE PATTERN**, `no_signal_enable_disable=true` active → **CEO close-out, not shipped.**
- **SHORT TAT / RSI-65 counter-trend / EXTREME-vol LONG / direction-mix / short-gate loosening /
  bb-bounce re-kill** — previously rejected, re-confirmed unchanged.

## MANDATE — CHOP vs TREND (fresh PG)
- armed (mfe>=0.40): 7d **73T 74.0% `+$3.57`** vs 59T 6.8% `-$4.32` | 14d **164T 70.1% `+$8.23`**
  vs 165T 6.1% `-$12.89` | 30d **404T 73.0% `+$25.85`** vs 302T 5.3% `-$28.07`
- trailing_activated 7d: True 68T 75.0% `+$3.20` vs False 64T 10.9% `-$3.95`
- MFE buckets 14d monotone: `<0.20 -$8.68` | `0.20-0.40 -$4.24` | `0.40-0.80 +$1.13` | `>=0.80 +$7.10`
- exits 14d: **hard_max_loss 64T 0% `-$6.33`** | **atr_sl_hit 80T 1.3% `-$5.68`** | TAT 24T 20.8% `-$0.77`
  | profit-monster-trail 49T (7d) 89.8% `+$2.87` carries all profit
- chop-bleed share: 7d 83.7% / 14d 85.2% / 30d 80.7% = baseline band → **entry quality owns the bleed**
- 7d direction: LONG 88T 38.6% `-$1.25` vs SHORT 44T 54.5% `+$0.50`; **30d reverses**
  (SHORT 188T `-$1.78` vs LONG 518T `-$0.44`)
- **NEW — atr_sl_hit MFE split (14d 80T `-$5.68`)**: 62.5% chop (MFE<0.40, `-$3.98`) vs 37.5%
  giveback (MFE>=0.40, `-$1.70`) → **confirms D=0.20 post-arm floor targets the right 37.5%**;
  the other 62.5% is an ENTRY problem — do not build an exit lever for it.

## WATCHDOG TRIAGE (0 steers / 3 deep-analysis recs)
1. **flat-until-EMA300-hold** → book already 0 = CORRECT. Sources disagree (15m+4h SHORT_BIAS vs
   continuum reclaimed 04:12 after 980min below, volume LOW = retest not reclaim).
2. **pump-chain+ LONG** → 8th NO-ACTION, see rejected list; escalated as a CEO close-out.
3. **volume-buildup- SHORT** → confirmed edge every window: 7d 19T 73.7% `+$0.43` / 14d+30d 28T 75%
   `+$0.78`, arm-rate 78.6%, 24h 6T 100% `+$0.20`.
4. **Pattern-alert #6 (verify floor enforcement path) → DONE, path LIVE.** ⚠️ First grep FAILED as a
   **false alarm: `logs/pipeline.log` is 333MB and grep treats it as binary — MUST use `grep -a`.**
   With `-a`: EXEC-RSI-HARD-FLOOR fired **2026-10-26 03:01** (YGG RSI 29.7<35 knife BLOCKED),
   DETECT-FLOOR **02:49** (STX 34.4<35), FLOOR-BEAR allow-lines present every day Oct 14-26,
   UNCLOG-EXPIRED fired 54x. sub-45 SHORT since Oct 18: 25T 14W `+$0.20` profitable (matches
   "no steer"); 5 sub-35 opens all BTC ai-trader-pending = **PATH-EXEMPT**; 3 short-midband 45-55
   non-pump violations all ai-trader = path-exempt. **0 real leaks; gate_leak_census #141 holds.**

## LOSING AUTOPSY — WRONG-SIDE REFUTED 78th CONSECUTIVE RUN
`recovery_replay.py` adverse-first (`--selfcheck PASS`, reproduces the vacuity: 183/191 = 95.8% pass
on candle 1 alone): **48h n=11 = 5 never-adverse / 5 recovered / 1 NEVER.**
The NEVER = ICP #16409 SHORT hard_max_loss `-$0.09` (the bear-exemption trade, gate RSI 36.1).
24h 9 losers / 6 LONG: 4 mid-band (meta_rsi 47.67-58.15) · BTC continuum-trend+ held **7.7h through
the whole below-EMA300 tape = STALE DIRECTION not stale time** · ICP r2v2-long3 HML at entry_rsi
72.73 = overbought entry · IO pump-chain- MFE +0.77 given back. **0 new patterns.**
Refs that survive: #61 p=0.116, #84 t=-0.04.

## LAST-RUN VERIFY — ALL PASS
#153 tat SHORT sign fix (line 101) + source-guard (181) present | #153 `.git/hooks/commit-msg`
present, executable, 947B | #152 **constants git diff EMPTY** + PROFIT_MONSTER_BYPASS pump-chain
intact | #152 daily_git_commit GUARD lines 105-115 present — **first live test 07:15 UTC today** |
#152 IO #16407 CONF_FLOOR fk point closed as a LOSS (`-$0.05`, conf 29.50) | #151
postarm_giveback_census **RAN** (n=26 net -1.40, giveback share 50.0%, selfcheck PASS) | #150
vol_precondition **RAN → REJECTED** | #147 session_brain dedup 3/3 distinct titles | kill flags:
doji / volume-breakout-short- / hmacd = **0 post-kill opens** | size-reduce **ABSENT = 1.0x** |
session lock absent | CEO_PROTECTED **13/13** | SIGNAL_REGISTRY **n=86** w/ bb_bounce |
`no_signal_enable_disable=true` honored (0 signal flags touched).

## DEEP-DIVE — 0 new sub-50% n>=15 targets (14d AND 30d)
bb-bounce-v2-long+ 37T 37.8% `-$1.11` / 60T 48.3% `-$0.60` (kill bar FAIL #138, TAT-C live) |
doji-bottom-long 16T 31.3% (killed Oct 16, pre-kill rows) | ai-trader+ 20T 30.0% (disabled Oct 19) |
pump-chain+ 44T 27.3% `-$0.35` / 30d 71T 38.0% `+$1.84` **sign flip, NO-KILL** |
pump-chain- 36T 22.2% `-$0.35` / 30d 86T 34.9% `+$0.03` (CONF_FLOOR + **Oct-27 PROMOTE**).
Arm-rate 30d: volume-buildup- 78.6% / pump-chain- 69.8% / bb-squeeze 66.7% / bb-bounce-v3 63.2% /
r2v2-long3 61.1% / bb-bounce-v2 58.3% / pump-chain+ 47.9% — **no live signal >50% of trades in HML.**

## SHADOW (3/5 answerable)
**contrarian join RE-RAN** — pump-chain- flip **64.6% n=347 STANDS** (identical to #153), btc-pump-rider+
24.9% do-NOT-flip, overall 50.1% n=545. **Caveat logged:** every stored row is `classification=LOSER`
by construction → 64.6% is P(flip wins | orig lost); pair it with orig WR, don't read it as
unconditional. | **shadow_trader** 23,190 signals: CONFLUENCE-EXPIRY 11,059 blocked @48% avg `-$0.12`,
EXEC-BLOCK 16 @12%, exit A/B pm_trail `+$3,273` vs hard_max `-$4,901` = trail-or-nothing reproduces |
**gate_shadow** `brain/gate_shadow.db` 36,858 events (`data/gate_shadow.db` still 0-byte stale) —
EXEC-RSI-HARD-FLOOR `|would_pnl|` 0.09-0.17 over 30d = **BELOW FEE, structurally cannot decide** |
oscillator **FROZEN** (24,598 JSONL, 0 outcomes; `json.load` crashes — it is JSONL) / wyckoff 323 +
floor_admit 1,972 **PENDING outcome join** / rr 22.2d stale **ORPHANED**.

## PRE-REG RECHECKS
- **Oct-27 00:00Z**: unclog_waiver EXPIRES — recommend LAPSE + narrow volume-buildup- contingency (bars above).
- **Oct-27**: pump-chain- PROMOTE (64.6% n=347 re-verified) + waiver scoreboard.
- **Oct 31**: expiry short-supply (cost-reconciled bar: 30d SHORT excess_4h >+0.05% AND t>=2 AND LONG
  negative AND net of 0.1400%).
- **Nov 1**: coin_regime ALIGNED/COUNTER 14d OOS | **Nov 8**: gate scoreboard #2 | **Nov 15**: floor_admit 30d same-sign.
- **CONF_FLOOR fkB 29.1% FAIL → ship HELD**, CEO must waive/reject explicitly.

## READINESS
**0 open = CORRECT.** btc_15m + btc_4h BOTH SHORT_BIAS; continuum 1m **AT EMA300** (reclaimed 04:12
after 980min below, volume LOW, STRONG_UP/LEAN_BULL) = **retest not reclaim**; flips 23/24h = p50 churn.
**No directional entry until either a 15-30m 1m-hold ABOVE EMA300 completes (LONG-favored resumes) or
price closes back below (short-favored resumes).** If short-favored → **volume-buildup- is the only
family with edge**; if LONG-favored → **mid-band = no trade, bb-squeeze+ is the only positive 30d LONG
family (81T 61.7% +$0.21)**; trail-family first; **size 1.0x** (vacation_size_reduce.json ABSENT).

## CEO QUEUE
Identify the 02:19:30 `hermes_constants.py` writer (URGENT) | **waiver lapse/renew/narrow decision
before 2026-10-27T00:00Z** | CONF_FLOOR fkB FAIL 29.1% ruling | D=0.20 post-arm floor GO |
**pump-chain+ kill-trigger close-out** (Oct 23 date missed, 14d now passes, 30d positive).
