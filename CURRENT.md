# Current State — brain_auditor #243 2026-11-09 16:55 UTC
**Last Updated: 2026-11-09 16:55 UTC**
**Updated by: brain_auditor #243. Prior: #242 2026-11-09 04:45 UTC (preserved in git history).**

## HEADLINE — AUTO-BLACKLIST IS R:R-BLIND; HYPE BLACKLIST VERIFIED WORKING

1. **SHIPPED (zero trading behavior): `token_performance_monitor.py` RR-BLINDSPOT shadow leg.** The auto-blacklist keys WR<35 only; HYPE was the book's biggest single-token bleed (jup mirror LONG 48T 59%WR `-$0.82`, losses riding 2× wins) yet passed every WR check until T blacklisted manually 11-03. Trailing-7d net-leg (n>=5, WR>=35, net<=-0.50) flags HYPE exactly on 11-03 (n=51, WR 54.9%, `-$0.54`). Report-only; legacy path untouched. Subagent review SHIP-WITH-FIXES → MED rounding fix applied (legs exactly complementary via `ROUND(...,1)`); py_compile + live run PASS. 21-snapshot validation = 2 flags (BTC, fwd-7d ~flat) → **enforcement too noisy; promotion criteria pre-registered in-file (n>=10, fwd-7d <= -$0.75, non-major, not-already-blacklisted, CEO sign-off).**
2. **HYPE blacklist impact VERIFIED (T 11-03 commit 7f246c6e 05:16Z):** 0 LONG violations / 76 LONG opens since; 0 non-jup SHORT violations / 32 SHORT opens (16 jup Option-D exempt, cohort net **+$0.04** = exemption not bleeding, no revoke); HYPE daily bleed stopped (`-$0.92`/3.4d pre → exempt shorts `-$0.16`/6d post). **Apparent leaks were FALSE ALARMS:** #16811 is token **HYPER** (different coin); the 2 HYPE LONGs (00:46/02:54) predate the 05:16 commit.
3. **JUP REGIME BLOCK REJECTED-WITH-DATA:** HIGH+NORMAL 118T `-$1.42` fails Fisher vs FLAT (p=0.158) and HYPE = `-$1.06`/46T of it (confound = blacklisted token); post-11-03 halves HIGH 6T 0.00 / NORMAL 7T `+$0.11` = bleed stopped with no regime block.
4. **0 trading-constant changes** — hermes_constants.py EMPTY git diff, session lock ABSENT, CEO_PROTECTED 13/13, size-reduce file absent = 1.0x, checkpoint_registry 0 pending.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| **R:R-blind token monitor (headline)** | SHIPPED shadow leg; enforcement pre-registered, CEO-gated |
| **watchdog steer-001 (12/20 lost URGENT)** | TRIAGED — rolling-window artifact (jup own last-20 70% `+0.37`) + real 24h dip = 4 unarmed chop jup entries (8/9 losers mfe<0.40); no lever passed bars |
| **watchdog steer-002 (disable jup)** | NO-DISABLE with data — HYPE = 80% of jup lifetime bleed, now blacklisted; armed jup 80T 96.3% `+5.08` |
| **watchdog steer-003 (ai-trader-pending)** | NO ACTION — n=4/14d <20, `-$0.09`, CEO/autopilot domain |
| **jup HIGH/NORMAL regime block** | REJECTED (p=0.158, HYPE-confounded, post-fix halves flat/positive) |
| **#242/#241 verify** | census SELFCHECK PASS + live 14d LEAK 0 (ALLOW 57/WAIVER 27) · TWO-TIER PURGE comment present — ALL PASS |

### 2. NUMBERS (fresh PG 16:45Z)
- 24h **15T 33.3% -0.43** | 48h 25T 44.0% -0.38 | 7d **131T 55.7% -1.18** (armed 71T 91.5% +4.02 vs unarmed 59T 13.6% -5.20) | 14d 379T 54.4% -3.19 (armed 198T 90.9% +11.48 vs unarmed 180T 14.4% -14.67) | 30d 754T 46.7% -6.83
- 14d exit families: TRAIL 184T 84.8% **+8.60** carries all profit; atr_sl_hit 58T 0% -6.63 + hard_max_loss 42T 0% -5.44 = pure-loss engines
- 14d sub-50% n>=15: pc+ 25T 44.0% -0.24 (NO-KILL/11-13) · pc- 30T 40.0% +0.19 (contrarian-owned) — **0 new kill targets**
- 7d by regime: NORMAL 61T 65.6% +0.76 · HIGH 42T 52.4% -1.04 · EXTREME 17T 35.3% -0.73 · FLAT 10T 50% -0.17

### 3. SHADOW (2/6 usable)
- **contrarian join 16:30Z (re-ran, mandate):** overall flip **42.4%** n=1569 = flipping the book loses · **pc- 64.6% (226W/124L) LIVE, uniform chi2 p=0.3747 = Oct-27 PROMOTE stands** · rider 36.2% do-NOT
- shadow_trader: exit A/B **pm_trail +12,171 vs hard_max -14,194** = trail-or-nothing; every gate still avg-negative-EV
- floor join COLLECT (11-15; same-sign not reachable until 11-16) · oscillator FROZEN · wyckoff RETIRED · rr ORPHANED

### 4. AUTOPSY + AMPLIFY
- **48h recovery_replay (adverse-first, selfcheck PASS): n=13 = 8 never-adverse / 5 recovered / 0 NEVER → WRONG-SIDE REFUTED 71st consecutive** (#61 p=0.116, #84 t=-0.04). 8/9 24h losers = unarmed chop entries (SOL #16818 mfe 0.369 = 92% of arm threshold still lost → prearm-breakeven 11-14 input).
- **AMPLIFY: 1 watch registered** — `amplify-atr-trend-normal-short-cell-watch` (atr-trend- NORMAL SHORT 5T 100% +0.32 fresh; promote at n>=10 & net>0, deadline 11-16; not a duplicate of atr-trend-accel-shadow). 0 new multiplier proposals: same 4 n≥10 cells in-flight; **no signal×direction cell n>=8 nets > +$0.50/30d** = thin book. Flip-KPI MET this week (#239).
- Creative x2: RR-blindspot shipped · jup regime block rejected-with-data.
- constants EMPTY · session lock ABSENT · size-reduce absent = 1.0x · 0 pending checkpoints · watchdog steers 3, all triaged no-config-action.

### 5. READINESS (2026-11-09 16:55 UTC)
**2 open LONGs:** DOGE hl_copy #16836 `-0.53%` 28m (no DB SL/TP = hl-side managed; ugb-bypass-hole 12-15 owns) · BTC #16837 signal=NULL **source=orphan_recovery** (position-bookkeeping row, NOT a signal entry; HML ATR bracket SL 73880.91 = -1.5% / TP 76131.09 = +1.5% persisted). Regime: **15m LONG_BIAS vs 4h NEUTRAL vs trend_quality STRONG_DOWN = disagreement = chop**, vol LOW, velocity SLOW, market RECOVERY, auto_trader CHOP MANAGE_ONLY → **no new entries until 1m sustains one side WITH volume; no added size while CHOP AND volume LOW; trail-family first; size 1.0x.**

**Queue:** **11-10 (9 items 00:00Z):** gate-shadow-dedup · size-125 auto-revert (pre-adjudicated FAIL; money-sizing=CEO) · fade-ctx-exempt (gross-vs-fee split to CEO) · rsi-ceiling-75 revert-rule · conf-filter-parity jup conf-99 · jup-atrsl-parity (**ADD this run: session CEO quote "ALL 11 losers would have been saved with a 1.5% ATR_SL_MIN"**) · mfe-cut-arm-be · ichimoku-dampen · warrior-uninert next-100 share (bar ≥25%, baseline 17%) → 11-11 contrarian → 11-12 storm x3 → 11-13 pc+ kill-review + vb- clone-hunt + linreg-fade → 11-14 stop-tighten eval + drop-pcplus + probe-080 + bbsqueeze reband/neutral-exempt + mult-150 + atrtrail-clip + prearm-breakeven (**input: SOL #16818**) + TAT-age-sweep → 11-15 floor → 11-16 atr-trend cell promote-read → 11-17 jup batch (**input: 24h SOL×3 cluster**) → 11-19 jup HIGH OOS → 11-21 conf-tilt + scope-widen → 12-15 ugb-bypass-hole.
**Also live:** RR-BLINDSPOT collect window (promote only per in-file criteria + CEO sign-off).
**CEO:** mult-150 sign-off (evidence decayed) · unclog-waiver EXPIRY re-measure [35,45) still owed (expired 11-03) · jup Option-D HYPE SHORT exemption = n=13 lifetime `-$0.26` / 6T post-directive `-$0.16` → n<20 MONITOR, no revoke ask · watchdog "consider disabling jup" = NOT recommended.
