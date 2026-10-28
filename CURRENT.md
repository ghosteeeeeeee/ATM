# Current State — brain_auditor #192 2026-10-28 05:00 UTC
**Last Updated: 2026-10-28 05:00 UTC**
**Updated by: brain_auditor #192. Prior: #191 00:50 (preserved in git history).**

## HEADLINE — #191's named next lever EXECUTED EARLY and REJECTED; entry-quality route now closed on 3 axes
0 trading-constant changes (`constants_change_review_queue` active per T 2026-10-23 — propose → CEO
auto-approve, auditor-direct is not the channel; hermes_constants.py EMPTY git diff; CEO_PROTECTED
13/13; session lock absent; size-reduce file absent = 1.0x). 1 zero-behavior ship, 0 trade actions.

### 1. TAPE-STATE ARM CENSUS — REJECTED-WITH-DATA (0/10)
`brain/analysis/tape_state_arm_census_2026-10-28.py` (--selfcheck **ASSERT PASS**).
Backfilled BTC 1m tape state from `data/continuum.db` (**78 consecutive days, 0 complete days <1000
rows**) at every historical `open_time` using the **exact live stamp rule** (decider_run.py:5456-5474,
age<600s) → **n=728 at 30d** instead of waiting ~2 weeks for n>=100 stamped.
10 **pre-declared** tests, Bonferroni 0.05/10 = 0.005, bar = 30d same-sign ∧ p<0.05 ∧ Bonferroni ∧
fk<20% ∧ n>=20/cell: **0/10 pass.**
- T6 SHORT pos==BELOW p=0.0246 → fails Bonferroni 5x **and** 7d sign flips (+/-/-)
- T7 trend bear-vs-bull p=0.0398, same-sign 7/14/30d → **fk 62.6%** (blocking the low-arm cell kills
  62.6% of all winners) — real, ungatable
- **bug_hunter round: 1 MED + 6 LOW, ALL FIXED** (docstring coverage claim, TICK_INTERVAL imported
  from continuum_constants, staleness `>=600` to match live `<600`, dead `cell(pred)` param, T9/T10
  complements require `dist not null`, selfcheck unit guard bound to the imported constant) →
  **verdict STANDS, re-run reproduces 0/10 exactly.**

**With #96 (admission features), #190 (14 detect-time metadata fields) and #192 (BTC tape state) the
detect-time ENTRY-QUALITY route is closed on three independent axes. The 91.5% chop-bleed is not
predictable from anything observable at entry.**

### 2. COUPLED-SL TRIAL HIERARCHY INVERTED (time-critical for 2026-11-03)
The Oct-27 trial moved HML to **-1.200% price @5x** (design target MAE p75 = 1.17%) but
`CL_TIER1_MAX_PCT = -1.00` cuts at **-1.00% price** every 2-4 min → **T1 now binds first.**
- HML-SHADOW live: `actual=-0.800%` pre-trial (**10,999** lines) → `actual=-1.200%` post (**1,877**)
- **7/7 cut-loser-CL-T1 exits in 21d** closed at **-0.950 … -1.110%** price, avg **-1.012%**
- PRE-trial hard_max_loss **37 exits avg -0.907%** (HML bound first) · POST-trial 13h = **0 HML /
  1 T1 / 3 atr_sl_hit avg -1.283%**
→ On Nov 3 the CUT_LOSER half reads ~no-effect (structurally unreachable) and either renews on PnL or
reverts to -4.00 — **reverting restores the old hierarchy and undoes the fix; either way the verdict
is not attributable.**
**Lodged in the review queue:** **Proposal A (preferred)** add `CL_TIER1_MAX_PCT -1.00 → -1.25` to the
coupled set at Nov-3 so HML -1.20 becomes reachable, revert all three together · **Proposal B** leave
T1 and stop describing CUT_LOSER as widened · **do NOT do both.**
n=7 T1 exits **FAILS the queue's n>=15 bar for an EDGE change** — filed as a **trial-validity /
measurement fix**, mechanism confidence HIGH, frequency MEDIUM.

### Next-lever bar (CHANGED THIS RUN)
Any future entry-gate proposal must use a field **outside** {#96 admission features, #190's 14 metadata
fields, #192 BTC tape state} or it is duplicate of closed work. Remaining bar unchanged: 30d same-sign
AND p<0.05 AND Bonferroni AND winner-kill <20% AND n>=20/cell AND not-already-in-constants.

### Mandate numbers (fresh PG, 2026-10-28 04:59Z)
| Metric | Value |
|---|---|
| 24h | **16T 62.5% `-0.17`** (6 losers, ALL never armed) |
| 7d | **136T 52.9% `-0.47`** |
| 14d | **295T 43.4% `-3.43`** |
| armed 7d | **80T 85.0% `+4.28`** vs unarmed 56T 3.6% `-4.75` |
| armed 14d | **154T 76.0% `+7.92`** vs unarmed 141T 7.8% `-11.35` |
| chop-bleed | 7d **91.5%** dollar (49/60) **age=11 — still UNDER the 92% gate** · 14d 86.2% |
| arm-rate tripwire | LONG **57.1** (n=91) / SHORT **62.2** (n=45) — **NOT tripped** |
| 7d exits | pm_trail 55T 51W `+3.06` · ugb_pt 16T 13W `+0.63` vs hard_max_loss 14T 0W `-1.88` · atr_sl_hit 16T 0W `-1.32` |

### Losing autopsy (corrected method)
`recovery_replay.py --selfcheck` **ASSERT PASS**, vacuity assert 155/160.
**48h n=20 = 2 never-adverse / 15 recovered / 3 NEVER** (PURR `-0.19`, AERO `-0.12`, CC `-0.07`) ·
**14d n=160 = 35 / 100 / 25 (15.6% structural)** → **WRONG-SIDE REFUTED 117th consecutive run**
(#61 p=0.116, #84 t=-0.04). No new pattern.

### Signal deep-dive — 0 new actionable n>=15 sub-50% targets
bb-bounce 34T 35.3% (TAT-C + MFE-CUT + CEO) · ai-trader+ disabled · **pc- 17T 11.8% FLIPPED Oct 27** ·
ai-trader-pending CEO · pc+ 41T 41.5% NO-KILL/CONF_FLOOR.
Healthy: volume-buildup- 38T 65.8% `+0.34` arm 68.4% · bb-squeeze 17T 58.8% `+0.50` · r2v2-long3 16T 62.5%.

### Re-measures this run
- **arm-timeout pre-reg (#189):** overall 14d 31.0% (bar needs >=40% at BOTH 14d+30d) → **MONITOR holds**;
  pc+ 14d **n=13 <20** → pre-reg NOT met, **no 45→60m proposal**.
- **momentum time-stop (#156):** re-run **0/8 again** (best cell T=20m/THR=0.20 delta `+2.01` p=0.0044
  but winner-kill **56.7%** vs 20% bar). **Oct-30 SCOPED blind run NOT touched.**
- **midband × EMA300 (#139/#172):** SAME verdict OOS 7/14/30d — band+BELOW `+0.10/-0.08/+0.57`,
  band+AT/ABOVE `-0.99/-3.31/-2.30`, both variants FAIL → **WITHDRAWN stands.**

### Last-run verify #191 — ALL PASS
session lock absent · constants EMPTY · protected 13/13 · size-reduce absent=1.0x ·
**btc_ema300 stamp 5/5 post-ship opens (first = PURR #16452 02:06Z; #16450/#16451 correctly None)** ·
Tracebacks 5 total latest Oct-25 self-healing, 0 new · recovery_replay selfcheck PASS ·
kill flags as recorded · contrarian reproduces 64.5% n=350 ·
**session_brain 6/6 unique titles — dup-heavy drift NOT observed this run.**
**CHASE_MOVE_SHADOW first live fire 03:03:21 KAS (move 0.673%, 8s before open) → KAS closed -0.12 =
live counterfactual +$0.12, n=1** (flip review still 2026-11-10).

### Watchdog steers 6/6 dispositioned
chop-bleed 91.5% age=11 → **answered** (route closed, headline) · BTC #16450 exit condition →
**FLAGGED NOT EXECUTED** (CEO/autopilot; live 04:59 = price **AT** the line -0.0034%, STRONG_DOWN,
condition NOT met) · **8h-stale → CHECKPOINT REGISTERED `btc-16450-8h-stale` due 05:54Z grace 45m** ·
5× pending RSI<28 SHORTs → knife rule correct, no action · shadow auto-trader BTC SHORT → mode=shadow
phase 0, no action · paid-extremes rec → re-measured, advisory only (`eval-midband-long-4564` Nov 3).

### Shadow 3/6 answerable (all used)
- **shadow_trader** 30,670 signals: gates justified (CONFLUENCE-EXPIRY 12,861 @48% avg `-0.12`);
  exit A/B **pm_trail `+4,368`** vs cut_loser `-426` (0% WR) vs hard_max `-6,245` (0% WR) vs
  rr_engine `-1,525` → **trail-or-nothing** confirmed again.
- **contrarian** join 10-27T18:31Z: 651 decided, flip 46.7%; pc- **64.5% n=350 ALREADY LIVE**;
  rider 26.0% do-not-flip. **Conversion: 3 PRODUCTION events (GOAT×1, HBAR×2) vs 26 smoke, 0 in 13h
  = base-rate expected — but 2/3 are HBAR which sits in `LOSERS_LONG` (the flip's own target direction
  carries a losers-penalty) → metric definition flagged for the 11-03 disposition.**
- **floor_admit** 10-25: floor 47.9% vs always 38.4%, fisher p=0.138 **COLLECT** (Nov 15).
- oscillator FROZEN fossil / wyckoff 345 PENDING / rr ORPHANED — none cited.

### Drift / side-finds
- **LOW** — AGENTS says the contrarian join runs every 15 min; systemd shows
  `hermes-contrarian-monitor.timer` fires **HOURLY at :00** (file 10h stale). Cadence doc vs timer: T/CEO pick.
- **LOW** — `vacation_mode.json` still true (21st+ run); review queue honored this run (0 auditor-direct changes).
- **INFO** — `rsi_drift` log lines 0 this window (COLLECT field, monitor).
- **INFO** — auto_1hr boosted bb-squeeze+ compactor weight 0.8→0.9 at 04:30; **verified COMMITTED
  (e9565d9e), tree clean** — recorded so the auditor trail carries a scoring change made outside this run.

### READINESS: 1 open
- **BTC #16450 LONG** continuum-trend+ @80950, SL 80463.8 / TP 82164.25, lev 5, age 6.6h, ~0.00,
  meta_rsi 30.89, **NEVER ARMED**. continuum EMA300 live ≈ **80960**.
- Regime: BTC 1m **AT** EMA300 (`-0.0034%`, duration 380 ticks), trend_quality **STRONG_DOWN**,
  wyckoff UNKNOWN, linreg NEUTRAL · 15m/4h **LONG_BIAS** vs tape AT the line · vol LOW · volume LOW ·
  velocity SLOW · auto_trader **CHOP ×6** · flips 26/24h = **p95**.
- **No fresh entries while sources disagree.** Line = 80960: **15-30 consecutive 1m closes below →
  exit; a reclaim that HOLDS 15-30m with volume → retract.** Trail-family first, size 1.0x.

### Queue
1. **2026-10-28 05:54Z** — checkpoint `btc-16450-8h-stale` (exit if still flat AND line held below).
2. **2026-10-30** — SCOPED momentum time-stop **BLIND** run (pc+/bb-bounce only, B1' n>=60 + B2-B6
   pre-registered in #156). **Do not peek first.**
3. **2026-11-03** — coupled-SL trial disposition (**Proposal A / B above**) · shadow_disposition batch
   (escalation #17, rr-engine, relative-regime, wyckoff, shadow-trader-bypass, chase-ratio,
   eval-midband-long-4564) · contrarian conversion KPI definition.
4. **2026-11-04+** — coin_regime direction-split re-measure (#179).
5. **2026-11-10** — CHASE-MOVE flip review · gate_shadow · MFE-CUT · expiry-t5.
6. **2026-11-15** — floor_admit same-sign · wyckoff outcome join.
7. **CEO** — CONF_FLOOR fk-definition pin · tf-authority 1m vs 5m RSI · bb-bounce keep-vs-disable ·
   TAT variant-C flip · MFE-CUT enforcement.
8. **RE-ANCHOR the chop-bleed 92% escalation gate** — its target (entry-quality filters) is now
   measured-closed, so a breach has no valid destination.

Artifacts: `brain/audit_recommendations.json`, `brain/creative_improvements.json`,
`brain/changes_log.json`, `brain/analysis/tape_state_arm_census_2026-10-28.py` (--selfcheck PASS),
`data/checkpoint_registry.json`, CURRENT.md.
