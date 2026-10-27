# Current State — brain_auditor #189 2026-10-27 20:44 UTC
**Last Updated: 2026-10-27 20:44 UTC**
**Updated by: brain_auditor #189. Prior: #188 19:47 (preserved in git history).**

## HEADLINE — 0 config changes (nothing passed bars; session lock absent; constants untouched;
**CEO_PROTECTED 13/13). NEW MEASURE: arm-timeout forward test — stall cuts are NOT premature
at the pre-reg bar (14d 34.5% / 30d 42.9% would-arm-60m, needs >=40% both windows) = MONITOR.**

1. **Arm-timeout forward test SHIPPED as analysis** (`brain/analysis/arm_timeout_forward_2026-10-27.py`,
   `--selfcheck` PASS, adverse-forward anchor from `close_time`, no lookahead). Answers the defensive
   side of the 92.5% chop-bleed steer: are the 45/55/60m stall cuts landing before momentum?
   - 7d 19 cuts **36.8%** | 14d 29 cuts **31.0%** | 30d 42 cuts **40.5%** would reach +0.40% arm within 60m of the cut
   (candle-close-strict horizon: `ts+60<=horizon` — bug_hunter found an off-by-one admitting closes up to +61m;
   fixed mid-run, pre-fix 34.5%/42.9%; verdict unchanged)
   - **Family split (the finding):** bb-bounce TAT-C cuts **VALIDATED** (1/7 = 14% forward-arm < 25% bar —
     variant-C is cutting right); **pump-chain+ 45m timeout is the hot one** (30d 10/21 arm60, 10/21 arm30, 14d 5/13) — but the cut cohort
     is **NOT bleeding** (30d exits +0.30), so no urgency.
   - Pre-registered re-eval: pump-chain+ 14d cuts n>=20 AND arm60>=45% → then full trail-sim counterfactual
     before ANY 45→60m proposal. Verdict **MONITOR**, zero behavior change.
2. **#188 CHASE-MOVE soak verified live** — code present (decider_run.py:5330-5377), py_compile PASS,
   **AST-checked name resolution** (`sqlite3`/`time`/`log`/`CANDLES_DB` all resolvable in `run()` scope —
   a NameError would have been swallowed by the gate's own try/except and gone undetected otherwise),
   pre_entry_momentum selfcheck PASS. 0 `[CHASE-MOVE-SHADOW]` lines = correct-by-traffic (0 trades opened
   since the 19:47Z ship). CHASE_RATIO_SHADOW=False (revert held). Flip review **2026-11-10**.

### Answering the watchdog's own steers (20:15Z cycle)
- **Chop-bleed KPI 92.5% 3rd consecutive cycle ≥92% → entry-quality (brain auditor)** — shipped response is
  CHASE-MOVE shadow (#188, soaking); this run adds the exit-side defensive check above (measured, not tweaked).
  Route-reopen tripwire needs <70% ×2 → NOT tripped (92.5%).
- **pump-chain+ advisory 19T '-0.41' 7d bleeder** — re-measured: 7d 19T 47.4% '-0.41' / 14d 40T 40.0% '-0.09' /
  **30d 88T 39.8% '+1.77'** → **NO-KILL stands**, CONF_FLOOR remains the CEO-owned lever.
- **CHIP LONG pick** — AI_TRADER_ENABLED=False → watchlist only, no action.
- **ARM-RATE tripwire NOT TRIPPED**: 7d LONG arm **56.4%** (53/94), SHORT **59.6%** (28/47) — repaired vs run-#186 trip.

### Mandate numbers, fresh (PG self-query, 2026-10-27 20:35Z)
| Metric | Value |
|---|---|
| 24h | **21T 66.7% '+0.39' GREEN** |
| today | **17T 76.5% '+0.62' GREEN** |
| 7d | 141T 51.1% '-0.41' |
| 14d / 30d | 303T 42.9% '-2.88' / 737T 44.5% '-3.40' |
| armed 7d | **81T 84.0% '+4.26'** vs unarmed 60T 6.7% '-4.67' |
| armed 14d | **161T 73.9% '+8.27'** vs unarmed 142T 7.7% '-11.15' |
| trail family 14d | **126T 88.1% '+8.95'** (incl ugb_pt) vs chop exits 149T 3.4% '-11.63' |
| chop-bleed | 7d **92.5%** (52/64) / 14d 86.7% / 30d 81.4% |
| armed losers 14d | 37T '-1.77' avg mfe 1.21, atr_sl_hit 21T '-1.25' = **giveback class, OWNED by pending D=0.20 CEO GO** |

### Losing autopsy (mandated, corrected method)
`recovery_replay.py --selfcheck` **PASS** (asserts the 96% open-anchored vacuity).
**48h n=20 = 3 never-adverse / 14 recovered-after-adverse / 3 NEVER** (AERO '-0.12' cut-loser, ICP '-0.09',
CC '-0.07' — all waiver-era shorts, class closed 00:00Z) → **WRONG-SIDE REFUTED 114th consecutive run**
(#61 p=0.116, #84 t=-0.04).

### Signal deep-dive — 0 new actionable n≥15 sub-50% targets (14d)
| Signal | n | WR | PnL | Status |
|---|---|---|---|---|
| bb-bounce-v2-long+ LONG | 37 | 35.1% | '-1.11' | OWNED: TAT-C live (validated this run), MFE-CUT fk-FAIL, kill = CEO |
| ai-trader+ LONG | 17 | 35.3% | '-0.68' | OWNED: AI_TRADER_ENABLED=False, 0 opens |
| pump-chain- SHORT | 21 | 14.3% | '-0.10' | OWNED: contrarian flip **LIVE 15:27Z** (CONTRARIAN-LIVE logs firing, 0 closed flip trades yet) |
| pump-chain+ LONG | 40 | 40.0% | '-0.09' | OWNED: NO-KILL (30d '+1.77'), CONF_FLOOR CEO |

### Shadow sources 3/6 answerable (SHADOW-RECKONING table honored)
- **contrarian** join fresh **18:31Z**: 651 decided, flip 46.7%; **pump-chain- 64.6% (226/350) STABLE** — flip
  already live, do NOT re-propose; btc-pump-rider+ 26% do-not-flip.
- **shadow_trader** 29,527 signals: CONFLUENCE-EXPIRY 12,629 @48%, CTX-GATE 1,138 @49%; exit A/B
  **pm_trail '+4,207'** vs hard_max '-6,130' vs rr_engine '-1,419' (trail-or-nothing reconfirmed).
- **floor_admit** join 10-25 (floor 47.9% vs always_admit 38.4%, p=0.138) — raw still writing (2,263).
- oscillator = FROZEN fossil / wyckoff 345 PENDING Nov 15 / rr ORPHANED (mtime 10-04).

### LAST-RUN VERIFY #188: ALL PASS
CHASE_RATIO_SHADOW=False ✓ · CHASE-MOVE code+selfcheck+name-resolution ✓ (0 fires = correct-by-traffic) ·
constants EMPTY git diff ✓ · CEO_PROTECTED 13/13 ✓ · session lock absent ✓ · size-reduce absent = 1.0x ✓ ·
gate_leak_census selfcheck PASS ✓ · recovery_replay selfcheck PASS ✓ · mfe backfill 1 NULL/141 ✓ ·
kill flags correct ✓ · 0 new Tracebacks (5 total, all Oct-11) ✓ · waiver 0 SHORT opens today ✓.

### READINESS: 0 open flat = CORRECT
Regime sources disagree: 15m NEUTRAL vs 4h SHORT_BIAS, continuum ABOVE EMA300 (STRONG_UP, linreg 0.75),
vol LOW, wyckoff DISTRIBUTION, market CALM. Drifting range = never-armed-chop breeding ground.
**No fresh mid-band entries; structure-qualified only (EMA300-hold or S/R reaction); trail-family first;
size 1.0x.**

### Queue
- **2026-11-10**: CHASE-MOVE flip review (≥14d soak ∧ 0 trail-winner blocks ∧ net counterfactual positive; revert on any trail winner)
- **MONITOR**: arm_timeout_forward pc+ re-eval (n>=20@14d ∧ arm60>=45%)
- **WATCH**: first closed contrarian pc- flip trades
- **Nov 1**: self-healing SKIP verify + coin_regime · **Nov 3**: coupled-SL trial disposition ·
  **Nov 15**: floor/wyckoff joins · wyckoff outcome join still unbuilt
- **CEO**: CONF_FLOOR fk definition pin + raw-confidence column pin · 1m vs 5m RSI tf-authority ·
  D=0.20 post-arm floor GO · bb-bounce keep-vs-disable · TAT flip

Artifacts: brain/audit_recommendations.json, brain/creative_improvements.json,
brain/analysis/arm_timeout_forward_2026-10-27.py, CURRENT.md. — brain_auditor
