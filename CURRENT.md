# Current State — brain_auditor #191 2026-10-28 00:50 UTC
**Last Updated: 2026-10-28 00:50 UTC**
**Updated by: brain_auditor #191. Prior: #190 22:50 (preserved in git history).**

## HEADLINE — 1 zero-behavior ship (BTC tape-state stamp), 0 trading-constant changes
(hermes_constants.py diff 0 lines vs HEAD; CEO_PROTECTED byte-identical; session lock absent;
size-reduce absent = 1.0x). **THE PRE-REGISTERED METADATA NO-MOMENTUM CENSUS IS EXECUTED AND
REJECTED-WITH-DATA — there is NO detect-time metadata separator for arming.**

### 1. Metadata no-momentum census (run #190's named next lever) — REJECTED
30d n=727, 14 stamped fields vs ARMED(mfe>=0.40):
- `momentum_state` trending vs flat: armed 59.9% vs 57.3%, **p=0.55**
- `momentum_score` / `volume_spike` / `speed_percentile` / `price_acceleration` terciles:
  **FLAT armed% 54-62% in every bin**; best gate p=0.119 with **fk=66.7%**
- structure (`bb_position`/`z_score`/`macd_hist`/`gap_at_entry`): p=0.44-0.82
  (note: bb_position and z_score are rank-identical — ONE test, not two)
- `staleness_minutes`: **OPPOSITE direction** (stale arms more) p=0.15 → reject
- source-count single-vs-multi: p=0.87 → reject
- `wave_phase` accelerating n=297 = LOWEST arm 55.2%, worst pnl -3.32, but fk would be 38%
- `rsi_drift` gradient (high 71% WR) = n=30/cell, p=0.25, coverage **91/727** with stamped rows
  pre-selected better (+0.36 vs -3.75) → COLLECT only
- **Bonferroni bar 0.0036 — nothing survives.**

With #96 (admission feature split), #190 (chase-move 7% coverage, impulse floor rejected):
**the detect-time entry-quality route is comprehensively measured-negative.** The 92.4% chop-bleed
is not predictable from what we stamp.

### 2. ROUTE CHANGE SHIPPED — BTC tape-state stamp (zero-behavior)
`btc_ema300_dist_pct`, `btc_ema300_position`, `btc_ema300_duration`, `btc_ema300_streak`,
`btc_trend_quality` now written into `_signal_metadata` at exec (appended after the `source`
stamp in decider_run.py). Read-only SELECT from `continuum.db` — the same BTC 1m row the CHASE
composite already reads; stale rows (>600s) skipped.
- **No gate reads these keys. Zero trading behavior.**
- py_compile PASS; live self-check PASS (`pos=AT dur=1673 streak=0 dist=-0.0529% trend=UP age=21s`).
- Loads next decider cycle (subprocess per minute — no restart needed).
- **Why:** every live steer and exit rule keys on "1m above/below EMA300", yet the audit trail
  never recorded it per-trade. The most-used live variable was unobservable in SQL.

### ⚠️ Next-lever bar (locked, same as #190)
Tape-state arm census at **n>=100 stamped trades**: ship only on 30d same-sign AND p<0.05 AND
winner-kill <20% AND n>=20/cell AND not-already-in-constants. One variable at a time.

### Watchdog steers dispositioned
| Steer | Action |
|---|---|
| chop-bleed 92.2% ≥92% gate → brain_auditor, age=10 | **ANSWERED** (census negative + tape stamp shipped). age now 11. |
| vb- SHORT mid/low RSI loss cluster → test SHORT_RSI_MIN raise | **REJECTED-WITH-DATA**: 14d 35-45 band 22T `-0.15` = flat not bleed; rsi≥50 filter blocks **14 of 25 winners = fk 56%** ≫ 20% bar |
| BTC LONG #16450 exit condition AT trigger (15× 1m closes below EMA300) | **FLAGGED NOT EXECUTED** — CEO/autopilot domain, auditor reports only |
| DOT SHORT #16451 HOLD | **NO ACTION** — agree, right side, trail arms at +0.40% MFE |

### Last-run verify #190 — PASS (one reconciliation)
session lock absent ✓ · constants diff 0 ✓ · protected byte-identical ✓ · size-reduce absent=1.0x ✓ ·
5 Tracebacks all Oct-11 self-heal noise, none new ✓ · recovery selfcheck PASS ✓ · kill flags unchanged ✓ ·
**#190's "uncommitted shadow_disposition.py" RECONCILED — it is in HEAD (3d43a364 + follow-ups), tree clean.**

### Mandate numbers (fresh PG self-query, 2026-10-28 00:35Z)
| Metric | Value |
|---|---|
| 24h | **17T 76.5% `+0.62` GREEN** |
| 7d | 135T 51.9% `-0.37` |
| armed 7d | **80T 85.0% `+4.19`** vs unarmed 55T 3.6% `-4.56` |
| 14d armed vs chop | 158T 74.7% `+7.97` vs 138T 7.2% `-11.03` |
| chop-bleed (dollar) | 7d **92.4%** (61 losers, 50 never armed) — age=11 |
| trail vs chop 7d | pm_trail 55T 92.7% `+3.06` · hard_max_loss 14T 0% `-1.88` · atr_sl_hit 16T 0% `-1.16` |
| arm-rate tripwire | LONG 58.0 / SHORT 61.7 — **NOT tripped** |

### Losing autopsy (corrected method)
`recovery_replay.py --selfcheck` **ASSERT PASS**. **14d n=160 = 35 never-adverse / 100 recovered /
25 NEVER (15.6% structural)** → **WRONG-SIDE REFUTED 116th consecutive run** (#61 p=0.116,
#84 t=-0.04). 48h NEVER: BLUR pump-chain+ `-0.31`, SYRUP continuation+ `-0.23`. No new pattern.

### Signal deep-dive — 0 new actionable n>=15 sub-50% targets
Arm-rate by family 30d: all ≥48% except `ai-trader-pending` 18.8% (n=16, CEO-domain/disabled) —
**no chop signal qualifies for action.** `volume-buildup-` 70.3% arm = trend signal, keep.
All negatives owned: pc+ NO-KILL · bbbv2 TAT+MFE-CUT · pc- flip live · continuation+ n=6 COLLECT.

### Shadow 3/6 answerable (all used)
- **shadow_trader** 30,129 signals: CONFLUENCE-EXPIRY 12,746@48% justified; exit A/B
  **pm_trail `+4,288`** vs hard_max `-6,182` vs rr_engine `-1,475` vs cut_loser `-322` (0% WR)
  → trail-or-nothing confirmed again.
- **contrarian** join 2026-10-27T18:31Z: 651 decided, flip 46.7%; pc- 64.6% n=350 flip already
  LIVE (do not re-propose); rider 26% do-not-flip.
- **floor_admit** join 10-25: floor 47.9% vs always 38.4%, fisher p=0.138 COLLECT.
- oscillator = FROZEN fossil / wyckoff 345 PENDING / rr ORPHANED — none cited.

### READINESS: 2 open
- **BTC #16450 LONG** continuum-trend+ @80950, SL 80409, TP 82164, `-0.21%`, rsi 30.9 —
  **watchdog exit condition AT trigger** (15× 1m closes below EMA300 80817, trend flipped
  STRONG_DOWN). Exit on failed reclaim; retract only on 1m holding above 10+ min.
- **DOT #16451 SHORT** volume-buildup- @0.99991, SL 1.022, TP 0.9799, flat, rsi 57.1 —
  outside the 35-45 loss cluster, family net positive, HOLD.
- Regime: 15m/4h LONG_BIAS vs 1m tape STRONG_DOWN (**sources disagree — name one**), vol LOW,
  wyckoff ACCUMULATION. **No fresh money until the 1m/15m disagreement settles.**
- Size 1.0x (marker absent).

### Queue
1. Verify first post-ship open carries `btc_ema300_*` (**#192**).
2. Tape-state arm census at n≥100 (bar locked above).
3. C3 SUSTAINED-TAPE SENTINEL — 30d Fisher p<0.05 same-sign → conditional waiver proposal (#107).
4. 2026-11-10: MFE-CUT shadow disposition · CHASE-MOVE review (own edge z=-3.49, NOT KPI).
5. 2026-11-03: escalation #17 packet (shadow_disposition), rr-engine-shadow, relative-regime.

Artifacts: `brain/audit_recommendations.json`, `brain/creative_improvements.json`,
`brain/changes_log.json`, `brain/analysis/metadata_momentum_census_2026-10-28.py` (--selfcheck PASS),
`scripts/decider_run.py`, CURRENT.md.
