# Current State — brain_auditor #284b 2026-11-21 04:50 UTC
**Last Updated: 2026-11-21 04:50 UTC**
**Updated by: brain_auditor #284b (completing run). Prior: #283 2026-11-20 20:45 UTC (preserved in git history).**

## HEADLINE — run #284 (00:30) died with 2 unlogged ships: v6 kill + bb-squeeze dead-print fix, both recovered from its journal, verified live, logged. atr_trail_hit death root-caused = PM-trail OWNERSHIP (walk closed by forward-value bound). PREARM enforce live, first read delivered.

1. **Dead-run recovery**: #284 edited 2 files at 00:42, launched bug_hunter at 00:46, then died with zero logging. Ships: (a) `PUMP_CHAIN_V6_ENABLED True->False` per CEO pre-registration (cell = 0 rows/30d EXTREME SHORT, v6 30d 9T all LONG '-0.29'; import False; 0 opens since; one-line revert; **CEO ratify/veto open**); (b) `[bb-squeeze] BLOCKED print -> hermes_log` (38 timestamped lines now in pipeline.log, 0 bare — the registry's "NEVER SHIPPED" was a stdout artifact). Both logged to `brain/changes_log.json`.
2. **atrtrail-clip-12 CLOSED NO CHANGE** — ownership transfer, not a gate bug: profit-monster-trail wins the profit-side exit race since 10-26 (weekly atr_trail 22->3->0->0->1->0 vs pm_trail 33->50->87->50->31->24; 14d pm_trail 65T 95.4% '+3.82' vs atr_trail_hit 1T; loss-side atr_sl_hit 31T/14d = ATR check alive). Forward-value bound: 1 exit/21d x old $11.71/30d foregone ≈ $0.30/30d << +$2/30d bar → locked-cohort replay cannot change the verdict; PM widen already REJECTED + CEO_PROTECTED.
3. **PREARM LOCK ENFORCING LIVE** (CEO GO 20261120T002223Z, `PREARM_LOCK_ENFORCE=True` since 11-20 01:26): first read = 4/4 exits at breakeven, class-correct (mfe 0.251-0.297), net $0.000, n=4 UNDER-POWERED, fk unread → enforce KEEPS, re-measure 11-28 with post-exit-upside fk metric.
4. **0 trading-constant changes of my own** — session lock absent; STOP_TIGHTEN_SOURCES 2-tuple revert (#282) holding; CEO_PROTECTED untouched; size-reduce file absent = 1.0x.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d | 16T 43.8% **+0.03 gross** (auto_1hr net '-0.24' fee-drag) / 112T 49.1% '+0.63' gross |
| 14d / 30d | 205T 47.8% '-1.29' / 631T 52.8% '-3.52' |
| arm gap 7d | armed 57T 84.2% **+4.39** vs never 55T 12.7% **-3.76** |
| chop-bleed | 7d **83.6%** dollar (under 92 gate) · 30d **92.2% AT line** — route CLOSED (#96/#190/#192) → MONITOR |
| 14d families | TRAIL 65T **95.4% +3.82** vs CHOP/STOP 81T **0% -8.59** (other 59T 61% +3.48) |
| regime 7d | NORMAL 25T 68% '+1.71' · EXTREME 35T 42.9% 0.00 · HIGH 52T 44.2% '-1.08' |
| kill screen | 14d sub-50 n>=15 net<0 = **0 rows** |

### 2. AUTOPSY (48h, recovery_replay adverse-first, selfcheck PASS)
n=11 = 0 never-adverse / 9 recovered / **2 NEVER** (IMX atr-trend- hard_max_loss '-0.12' · GOAT r2v2-long7 CL-T1 '-0.12') → **WRONG-SIDE REFUTED 135th** (#61 p=0.116, #84 t=-0.04). Both NEVER = never-armed chop class.

### 3. SHADOW (mandate re-runs done)
| Source | Status |
|---|---|
| contrarian join | **RE-RAN 04:30Z** — overall flip 47.3% n=2143; pc-\|BELOW 64.6% n=48 HOLDS; pc-\|AT 28.6% never blanket; rider chi2 p=4.9e-40 = per-signal only |
| floor join | **RE-RAN 04:31Z** — p=0.1688 (floor 49.5% n=1908 vs always 45.8% n=439); route CLOSED 11-15, reproduces |
| shadow_trader | 127,102 — exit A/B pm_trail **+19,419** vs hard_max -25,121 (0% WR) vs rr_engine -9,414 = trail-or-nothing; all 11 gates negative-EV |
| prearm enforce | 4 exits since GO, net $0.000, class-correct; 166 log lines |
| struct-flip | **0 lines ever** — probe never wired (owed 11-25) |
| rider-fade | **SIDE-FIND: 0 lines in pipeline.log AND archive** — #283's "62/39 MET" unverifiable; re-source before the 11-22 read |
| oscillator / wyckoff / rr | archived / retired / orphaned = 3/6 answerable |

### 4. DUE 11-21 BATCH — 11/11 dispositioned
pcv6 **DONE-KILL** · atrtrail **DONE-CLOSED** · prearm **DONE-first-read** · bbsqueeze-reband OPEN 11-25 (step i shipped, 2/>=10 ceiling events) · conf-tilt OPEN 11-28 (**cell precondition FAILS: pc+\|EXTREME 14d '-0.16', r2v2 n=0**) · ceiling-85 **DONE-NO-SHIP REINFORCED** (realized 75-85 SHORT now 18T/30d net '-0.10' → criterion 3 fails on substance) · slope-jup **DONE-CLOSED** (live jup SHORT 30d 61T 63.9% '+0.24' without any exempt) · r2v2 OPEN 11-28 (tok_n <<50) · jup-short-walk EXTENDED 11-28 · structure-flip OPEN 11-25 · reentry-study OPEN 11-28 (**prior art in-repo: `brain/analysis/reenter_recovery_cf_2026-10-25.py`, `repeat_after_stop_2026-10-26.py` — extend, don't redesign**).

### 5. AMPLIFY (1 new) + WHY-NOT
**`amplify-longbypass-dual-basis-reconcile`** — LONG-BYPASS-SHORT-BIAS-BLOCK PRIMARY fwd_4h 30d 63 tok-days **+0.87% pos 68%** / 7d 41 tok-days **+1.02% same-sign** vs adjudicated 11-17 read "gate saves ~$10/14d" = the #237 adverse-selection gap. Measurement-first, **NO trade change**, default NO CHANGE. Why-not: every other 30d n>=10 net>0 winner cell is already in-flight. **Flip-KPI: 0 conversions this week** (rider-fade only candidate, source owed).

### 6. LAST-RUN VERIFY (#283/#282) — ALL PASS
atrtrail side-find confirmed+diagnosed ✓ · STOP_TIGHTEN_SOURCES 2-tuple revert holding (constants:761) ✓ · contrarian+floor mandates ✓ · session lock ABSENT ✓ · size-reduce absent=1.0x ✓ · CEO_PROTECTED untouched ✓ · py_compile 6 files PASS ✓ · checkpoint_registry only kill-line 12-03 pending ✓.

### 7. READINESS (2026-11-21 04:47 UTC)
**1 open — BTC SHORT #17014 ai-trader-pending @56637, age 0.9h, +1.63%, stop R1-moved to 56693.6 (locks ~breakeven), meta_rsi 33.25.** Regime 15m **SHORT_BIAS** + 4h **SHORT_BIAS** AGREE, continuum BELOW, zscore STRONG_NEG, velocity FALLING, wyckoff MARKDOWN, trend STRONG_DOWN, vol NORMAL = **with the tape → HOLD**; exits drawdown-driven only (CEO stay-in doctrine 2026-11-21, skill rule 14 — no profit-lock closes). SHORTs only on bounce to RSI 45-55 (never ≤35 post-dump); LONGs only on a sustained EMA300 reclaim WITH volume; trail-family first; size 1.0x; 0 watchdog steers.

**Queue:** **11-21/22 rider-fade formal read ONLY after re-sourcing its lines** → 11-23 jup-long clonehunt + formal weekly AMPLIFY → 11-25 STRUCT-FLIP probe ship + bb-squeeze ≥10 ceiling events → 11-28 PREARM fk re-measure + conf-tilt cell re-validation + r2v2/jup-walk/reentry reads.
CEO: **v6 kill RATIFY/VETO (one-line revert)** · PREARM first-read ACKNOWLEDGE · dual-basis reconcile queued · LONG arm tripwire 42.9% (data only) · mult-150 label. Flip-KPI: 0 this week.
