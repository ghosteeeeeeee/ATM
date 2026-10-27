# Current State — brain_auditor #190 2026-10-27 22:50 UTC
**Last Updated: 2026-10-27 22:50 UTC**
**Updated by: brain_auditor #190. Prior: #189 20:44 (preserved in git history).**

## HEADLINE — 0 config changes (nothing passed bars; session lock absent; constants EMPTY;
**CEO_PROTECTED 13/13 byte-identical vs HEAD). CHASE-MOVE COVERAGE MEASURED: the #188 soak
catches only 7% of the chop-bleed — pre-register Nov 10 to judge it on its own counterfactual,
NOT on KPI movement. BUG-068 state corrected (see drift).**

1. **CHASE-MOVE coverage-vs-edge (new measurement, no code change).** 14d n=301, entry_price vs
   last closed 5m close (candles_5m fresh):
   - fires on **10/141 unarmed losers (7.1%)** saving $1.00, and **5/130 winners** costing $0.32
     → net **+$0.68/14d**. Threshold sweep 0.20/0.30/0.40/0.50 monotonic.
   - **unarmed move p75 = +0.098%** — the bleed is NO-MOVE chop, not chase. 7% coverage cannot
     move a 92% dollar-share KPI. Flip review **2026-11-10** = judge on own edge (z=-3.49),
     pre-registered this run.
2. **Impulse floor REJECTED-WITH-DATA** (creative #4433 idea): block |signed 15m move|<0.15%.
   BLOCKED n=154 **WR 45.5%** vs KEPT n=147 WR 40.8% (blocked cohort BETTER), kills **70/130
   winners = 54% >> 20% bar**, bins non-monotonic ([-0.15,0) 54.5% best, [0.15,0.30) 34.0% worst
   = opposite of theory), shallow -$0.015/trade. **Never re-propose a blanket impulse floor.**
3. **Next lever pre-registered: metadata-only no-momentum census** — momentum_state,
   momentum_score, volume_spike, speed_percentile, rsi_drift already in `_signal_metadata`,
   detect-stamped (no lookahead, zero candle joins). Ship bar: 30d same-sign AND p<0.05 AND
   winner-kill <20% AND n>=20/cell AND not-already-in-constants. One variable at a time.

### ⚠️ DRIFT corrected this run
- **#189 recorded `CHASE_RATIO_SHADOW=False (revert held)` as PASS — WRONG STATE.** False = LIVE
  BLOCK (decider_run:5320). Main session restored **True** at 21:55 (f96a1e2c, BUG-068). Current
  = True = log-only, correct. FOGO counterfactual 21:45→22:40 = **-0.31% → accidental block cost
  $0** (lucky). '0 fills 19:50-21:55' attribution is FOGO-evidenced only — quiet market confounds.
  First post-fix fill BTC #16450 at 21:54:38.
- **Adopted main-session rule: any flag flip must quote the consumer line proving direction
  before setting.**
- **MED side-find:** uncommitted parallel work in tree — `shadow_disposition.py` +170 lines
  (threshold_eval) + `config/hermes-shadow-disposition.*` weekly→daily, docstring labeled
  'run #190', review notes present. NOT touched, NOT committed. Reconcile at #191.
- LOW: gate log lines (`CHASE-*`) go to `logs/pipeline.log` (hermes_log.FP), NOT `signals.log` —
  grepping signals.log gives false 0s (it's 373MB binary-flagged too, use grep -a).

### Mandate numbers, fresh (PG self-query, 2026-10-27 22:35Z)
| Metric | Value |
|---|---|
| 24h | **19T 68.4% '+0.39' GREEN** (6th+ green window) |
| today | **17T '+0.62' GREEN** |
| 7d | 139T 51.1% '-0.47' |
| 14d / 30d | 301T '-2.84' / 735T '-3.31' |
| armed 7d | **81T 84.0% '+4.26'** vs unarmed 58T 5.2% '-4.73' |
| 14d armed vs chop | **186T 67.2% '+7.50'** vs 114T 4.4% '-10.34' |
| chop-bleed (dollar) | 7d **92.5%** ($4.81/$5.20, 4th cycle age=7) / 14d 87.4% / 30d 81.6% |
| tripwires | arm-rate NOT tripped (LONG 57.6 / SHORT 59.6); route-reopen NOT tripped |

### Losing autopsy (mandated, corrected method)
`recovery_replay.py --selfcheck` **ASSERT PASS**. **48h n=20 = 3 never-adverse / 14 recovered /
3 NEVER** (AERO, ICP, CC — waiver-era shorts, class closed) → **WRONG-SIDE REFUTED 115th
consecutive run** (#61 p=0.116, #84 t=-0.04). 14d context: 35/101/25 = 15.5% structural.

### Signal deep-dive — 0 new actionable n>=10 sub-50% targets
All owned: pc+ NO-KILL (30d +1.77, CONF_FLOOR CEO) · bbbv2 (TAT-C+MFE-CUT, kill=CEO) ·
pc- (flip LIVE 15:27Z, 0 closed) · ai-trader* (disabled) · continuation+ 6T n<10 COLLECT.

### Shadow 3/6 answerable (all used)
- **contrarian** join 18:31Z: 651 decided, flip 46.7%; **pc- 64.6% n=350 STABLE** — flip already
  live, do NOT re-propose; rider 26% do-not-flip. No timer for the join file = agent-run design.
- **shadow_trader** 29,827 signals: CONFLUENCE-EXPIRY 12,684@48% justified; exit A/B
  **pm_trail '+4,249'** vs hard_max '-6,155' vs rr_engine '-1,451' (trail-or-nothing).
- **floor_admit** join 10-25: floor 47.9% vs always 38.4%, p=0.138 COLLECT.
- oscillator = FROZEN fossil / wyckoff 345 PENDING Nov 15 / rr ORPHANED.

### LAST-RUN VERIFY #189: PASS (one correction)
session lock absent ✓ · constants EMPTY ✓ · protected 13/13 byte-identical ✓ · size-reduce
absent=1.0x ✓ · 0 new Tracebacks (5 total, Oct-25 self-heal noise) ✓ · recovery selfcheck PASS ✓ ·
kill flags unchanged ✓ · **its `CHASE_RATIO_SHADOW=False PASS` line = wrong-state, corrected
above** · arm_timeout_forward script not re-run (analysis-only, no edits since #189).

### READINESS: 1 open — BTC #16450 LONG continuum-trend+ @80950, SL 80007, TP 82164, ~flat
Opened 21:54:38 = first fill post-BUG-068-fix. Watchdog: **HOLD** — thesis intact (1m above
EMA300 since 10:44); invalidation = sustained 15-30m close below EMA300 (condition-keyed), NOT
the 4h SHORT_BIAS label. Sources split: 15m LONG_BIAS vs 4h SHORT_BIAS, continuum ABOVE, vol LOW,
auto_trader CHOP. Structure-qualified entries only; trail-family first; size 1.0x; no mid-band adds.

### Queue
- **2026-11-10**: CHASE-MOVE flip review — judge on own counterfactual, NOT KPI (pre-reg this run)
- **#191**: reconcile uncommitted shadow_disposition threshold_eval work (MED side-find)
- **Run when ready**: metadata no-momentum census (pre-registered, bars locked above)
- **WATCH**: first closed contrarian pc- flip trades
- **Nov 1**: self-healing SKIP verify + coin_regime · **Nov 3**: coupled-SL trial disposition ·
  **Nov 15**: floor/wyckoff joins
- **CEO**: CONF_FLOOR fk pin + tf-authority · D=0.20 post-arm floor GO · bb-bounce keep-vs-disable ·
  TAT flip
- **Honest chop-bleed status**: no passing entry-quality lever exists today (coverage 7%, impulse
  rejected, CHASE-RATIO enforce = money-losing per #178/#188) — KPI likely stays >=92% until the
  metadata census produces a bar-passing candidate.

Artifacts: brain/audit_recommendations.json, brain/creative_improvements.json, CURRENT.md.
— brain_auditor
