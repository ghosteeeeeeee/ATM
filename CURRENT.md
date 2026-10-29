# Current State — brain_auditor #196 2026-10-29 01:10 UTC
**Last Updated: 2026-10-29 01:10 UTC**
**Updated by: brain_auditor #196. Prior: #195 2026-10-28 20:45 (preserved in git history).**

## HEADLINE — the arm-rate tripwire was falsely "OPEN"; root cause was the MFE write gap, fixed at source

0 trading-constant changes (review queue honored, session lock absent,
`hermes_constants.py` EMPTY git diff = 0 lines, CEO_PROTECTED 13/13, size-reduce file
absent = 1.0x), **1 zero-behavior ship, 1 ops fix, 0 trade actions, 3 creative ideas
(1 REJECTED-WITH-DATA, 1 pre-registered, 1 shipped telemetry).**

### 1. Root cause: brain.py never stamped mfe_pct/mae_pct at close
Watchdog at 00:11Z printed 7d LONG arm **46.9% (38/81, 6 NULL) = tripwire <50 OPEN**.
The nightly `cell_stats.backfill_mfe_mae` ran at 00:20Z and the identical KPI read
**53.7% (44/82) = NOT tripped** — all 6 NULLs were armed trail winners that the
brain-CLI close path (profit-monster / cut_loser / guardian / hl_fill) never writes.
Chop-bleed moved **91.6% (45/52, 1 NULL) → 94.3% (46/52, 0 NULL)** on the same event:
**an escalation-gating KPI depended on whether the nightly job had run.**

**SHIPPED** (`scripts/brain.py`, commit e830e207): the single
`UPDATE trades ... WHERE id=%s AND status='open'` now writes `mfe_pct`/`mae_pct` from
`highest_price`/`lowest_price` — **byte-identical to `cell_stats.backfill_mfe_mae`**
(guard `entry/extremes>0 AND direction IN ('LONG','SHORT')`, `COALESCE` so any value
another writer already stamped stands), inside the same statement that closes the row.

- Self-check `brain/analysis/mfe_write_at_close_2026-10-29.py --selfcheck` → **ALL PASS**
  (formula identity · temp-table round-trip with hand-computed LONG/SHORT + zero-peak NULL
  + COALESCE-preserve + status guard · single-statement assert)
- Live-schema probe: exact statement on open trade 16512 → rowcount 1, then ROLLBACK →
  row unchanged
- **bug_hunter subagent verdict = SHIP**: 0 HIGH · MED (hl_copy_trader caches old module)
  → **acted: service restarted 00:59:25Z, PID 1062534, active** · LOW (ELSE treated NULL
  direction as SHORT) → **acted: `direction IN ('LONG','SHORT')` added, now matches the
  backfill skip rule exactly** · LOW (selfcheck excluded guard clauses) → guard now asserted
- Zero trading behavior independently confirmed: no live gate reads `trades.mfe_pct`
  (decider_run / signal_compactor have 0 occurrences; trade_watchdog reads mfe only on
  `close_time IS NULL` rows, which no writer touches)

### 2. Chop-bleed KPI — BREACHED, run #1 of 2
- **7d 94.3%** dollar (4.48 of 4.75; 46 of 52 losers; 0 NULL) ≥ 92% gate → **breach #1**
  of the #194 two-consecutive rule · 14d 89.2% · 30d 82.3%
- arm-rate tripwire **NOT tripped** (LONG 53.7%) · route-reopen (<70% ×2) NOT tripped
- **If next run ≥92% again → present the #194 0.75x size proposal TOGETHER with #195's
  measurement that 74% of never-armed dollars sit at the HL floor where size cuts are
  NO-OP.** Do not escalate blind. Checkpoint `chop-bleed-92-adjudicate` due 04:30Z, grace 90m.

### 3. Watchdog routes answered
- **chop-bleed "entry gates age=4"**: detect-time route closed on 3 axes (#96/#190/#192);
  size lever 74% inert (#195); throttle premise **refuted this run** (creative #1 below) →
  remaining levers are the queued dated ones + CEO's TAT/CONF_FLOOR.
- **volume-buildup- R:R / loss-size**: 14d decomposition — armed 24T 91.7% `+1.24` vs
  unarmed 15T 6.7% `-1.77`; losses avg `-0.117` vs wins avg `+0.053` → break-even needs
  **66.9% WR** (actual 58.8%); loss exits HML 5 / CL-T1 4 / stale 2 / atr_sl 2 / ugb 2.
  **Same class as the whole system (the unarmed half), not a payout-structure defect.**
  Every candidate filter already fails (regime cells n<20 #195, direction p=0.75 #179,
  rsi<45 p=0.74) → **NO CHANGE**, owned by the queued stack.

### 4. CREATIVE x3
1. **REJECTED-WITH-DATA — same-day arm-rate throttle / confluence dampener** (the #195
   logged idea) and #194's "forecastable ~1 day ahead" claim: intra-day first-5-close arm%
   vs rest-of-day **per-trade** PnL r=-0.135 t=-0.69 n=28d (cold `-0.006` vs hot `-0.002`
   per trade) · day-over-day arm%D vs PnL(D+1) r=+0.174 t=0.88 p≈0.39 n=27 pairs.
   First cut showed r=-0.353 but that was trades-per-day confounded (SUM, not per-trade) →
   corrected to null. **Arm-rate is a LAGGING measure — do not build a gate on it.**
2. **PRE-REGISTERED EARLY-ARM ladder** (0.40 → 0.35/0.30) with the new 30d MFE census:
   `<0.10 144T 2.1% -16.56 · 0.10-0.20 67T 4.5% -5.76 · 0.20-0.30 52T 5.8% -4.82 ·
   0.30-0.40 58T 17.2% -3.49 · 0.40-0.60 131T 63.4% -0.16 · ≥0.60 288T 80.2% +26.11` —
   everything under +0.40% MFE owns `-30.63` gross, and the 0.30-0.40 band came within a
   dime of arming and still lost 83%. Bar: 1m candle replay, net ≥ +$2.00/14d, **fk <20%
   of the ≥0.60 winners** (they own +26.11 — earlier arm must not shake them out), 30d
   same sign. **`PM_TRAIL_ACTIVATE_PCT` is CEO_PROTECTED ("MUST BE 0.40% … DO NOT CHANGE")
   → measurement only, CEO ruling required.**
3. **Real-time MFE telemetry** from the ship — same-day arm/chop-bleed no longer lag the
   00:20Z backfill.

### 5. LAST-RUN VERIFY #195
| Item | Result |
|---|---|
| contrarian join mandate | **EXECUTED** — fresh 01:00Z, 744 joinable, flip 47.6% · pc- **64.6% n=350 LIVE** · rider **32.5% do-NOT-flip** |
| bb-squeeze+ weight 1.0 | **POSITIVE: 10-28 10T 90.0% `+0.17`** · 7d 21T 76.2% `+0.66` |
| #194 0.75x size proposal | **ARMED at breach run #1** (see §2) |
| #195 confluence dampener creative | **REFUTED this run** (creative #1) |
| btc-16450 checkpoint | already `done`, registry 0 pending before this run's new entry |
| constants / lock / size-reduce | EMPTY diff / absent / absent = 1.0x |
| Tracebacks | 0 new (pipeline 5, last Oct-11; profit_monster/cut_loser last Oct-17) |
| recovery_replay selfcheck | PASS |
| bug_hunter | SHIP (this run) |

## DRIFT / SIDE-FINDS
- **MED** — #194/#195 text calls same-day arm rate a *leading* indicator; measured null this
  run → strike "forecastable ~1 day ahead" from the escalation text (prompt edit next run).
- **LOW** — watchdog pattern_alerts mixed a pre-backfill arm-rate with a post-backfill
  chop-bleed in one block (two data states, opposite conclusions) — root-fixed by §1.
- **INFO** — LTC #16511 closed 00:32:43Z with NULL mfe, 3 min before the fix landed;
  tonight's backfill repairs it (proof the nightly net still works).
- **INFO** — `vacation_mode.json` still true (review queue honored) · err logs unrotated.

## PG FRESH (01:05 UTC)
24h **29T 51.7% `-0.83`** · 7d 129T 55.8% `-0.21` · 14d 289T 45.0% `-3.60` · 30d 748T 44.7% `-4.60`
· armed 14d **148T 78.4% `+7.70`** vs unarmed **140T 10.0% `-11.30`** · 14d exits:
profit-monster-trail 86T 93.0% `+4.55` vs atr_sl_hit 60T 1.7% `-4.59` / hard_max_loss 30T 0% `-3.83`
· 7d signal n≥5: bb-squeeze+ 21T 76.2% `+0.66` · volume-buildup- 34T 58.8% `-0.47` ·
pump-chain+ 17T 58.8% `-0.16` · bb-bounce-v2-long+ 10T 10% `-0.39`.

## AUTOPSY / DEEP-DIVE
- **Autopsy (adverse-first, selfcheck PASS): 48h n=16 = 3 never-adverse / 12 recovered /
  1 NEVER (PURR #16452 hh-hl+ `-0.19`) → WRONG-SIDE REFUTED 121st consecutive run**
  (#61 p=0.116, #84 t=-0.04).
- **Deep-dive: 0 NEW sub-50% n≥15 targets** — 7d none qualify; 14d all owned
  (bbbv2 32T 34.4% `-1.08` TAT+CEO · ai-trader+ 15T 40% disabled · pc+ 38T 36.8% NO-KILL).

## READINESS — 1 open, HOLD
**VIRTUAL #16512 LONG warrior-sr-confirm+** @0.62877, SL 0.6213038 / TP 0.6413454, lev 5,
age 1.7h, `-0.91%`, rsi 47.2. Family small-n (4T/7d) → watch only. LTC #16511 closed
00:32:43Z profit-monster-trail `+0.01`.
Regime: **btc_15m SHORT_BIAS vs btc_4h LONG_BIAS** (cite which source) · continuum AT ·
vol LOW · trend STRONG_UP → bias conflict → **NO fresh directional entries**; LONGs only on
a pullback-to-structure that reclaims EMA300 and HOLDS 15-30m WITH volume; SHORTs only under
EMA300 with 4h aligned; trail-family first; **size 1.0x**.

## QUEUE
**Next run** chop-bleed breach run #2 adjudication (checkpoint 04:30Z) + confirm **0 new NULL
mfe rows** (proof the source fix works end to end) + tape-state stamp on the first new open ·
**2026-10-30** scoped momentum time-stop BLIND (do not peek) · **2026-11-03** coupled-SL
disposition Proposal A/B (this run's HML sim: CUT_LOSER -6% cuts 12/2667 vs 956 at -4% →
supports A) + shadow batch + contrarian conversion KPI definition · **2026-11-04+** coin_regime ·
**2026-11-10** CHASE-MOVE flip + MFE-CUT disposition (default KILL, units guard first) ·
**2026-11-15** floor_admit + wyckoff joins ·
**CEO** C2 early-arm ladder ruling (protected flag) · CONF_FLOOR fk pin · TAT variant-C flip ·
tf-authority 1m-vs-5m · bb-bounce.

Artifacts: brain/audit_recommendations.json, brain/creative_improvements.json,
brain/changes_log.json, brain/analysis/mfe_write_at_close_2026-10-29.py, scripts/brain.py,
data/checkpoint_registry.json.
