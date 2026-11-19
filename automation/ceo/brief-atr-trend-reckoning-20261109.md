# DECISION REQUEST — atr_trend_accel shadow: disposition amendment vs stop-cluster fix

Asked by: lead agent (DSH session), on CEO instruction 2026-11-09+.
All numbers below were verified by direct PostgreSQL queries this session
(source of truth). Decide and record; edits to protected files are yours to authorize.

## Context

`atr_trend_accel` (signal ATR(14,1m) cross-up 0.076% + hysteresis 0.9 +
direction from 15m AND 4h EMA20/50 agreement) was built 2026-11-06 from a
30d x 12-coin backtest (24h WR 58.8%, ev-state +0.77, day-block p=0.007-0.015),
independently verified twice (audit #2 + own-conclusions: no lookahead proven).
LIVE shadow since 2026-11-06 21:55. Confidence raised 70→78 on CEO instruction
(score = confidence in the compactor; band [70,95)).

## Verified live results (PostgreSQL `trades WHERE signal LIKE 'atr-trend%'`)

- **45 closed trades** (2026-11-07 → 11-19): 25W / 19L / 1 scratch → **WR 55.6%**
- **Gross −$0.71, net ≈ −$1.16** (fees $0.45; JSON net_pnl sums −1.11 ✓)
- Sum pnl_pct −27.8%, avg −0.62%/trade
- **Payoff ratio 0.45**: avg winner **+1.63%** vs avg loser **−3.61%**
  (breakeven WR at payoff 0.45 ≈ 69% — we run at 55.6%)
- Median hold **40 min** (max 210m) — every winner exits profit-monster-trail
- Exit anatomy: PM-trail 26 exits (24W, **+1.04%** sum) | stop cluster:
  hard_max_loss 7 (0W, −0.74%), atr_sl_hit 5 (0W, −0.52%), cut-loser-CL-T1 4
  (0W, −0.49%), hard_sl 1 (−0.09%), stale_exit 1 (−0.13%) | hard_tp 1 (+0.22%)
- Split: SHORT 38 closed, 58% WR, −$0.62 | LONG 7 closed, 43% WR, −$0.09
- Conf≥78 cohort (post-raise): n=11, −$0.59 | conf<78: n=34, −$0.12
- Open now: 2 (≈ flat)
- Signal flow: ~170 signals/day; 71% die at `short-regime-gate` tombstone
  (working as designed), 25% at systemic `compaction_stale_10min` (separate
  bug — also hits hl_copy 19/30 in 48h)

## The conflict

The shadow-reckoning entry WE registered (CEO's WR-based choice, 2026-11-06,
`data/shadow_disposition.json`, id `atr-trend-accel-shadow`, deadline
2026-12-06) says:

> ">= 30 CLOSED atr-trend trades AND WR >= 52% -> KEEP; either limb unmet at
> deadline -> disable"; default_action = KILL.

**Bar is literally MET (45 closed, 55.6% ≥ 52%) — yet the signal is losing
money.** The WR-only rule has a payoff hole: a 55.6%-WR signal with payoff 0.45
is negative-EV. Also worth weighing: the audited edge assumed a **24h hold**
(mean +0.72%); live PM-trail exits in 40 minutes, so live system ≠ backtested
system, and the reckoning correctly judges the live system (signal + PM exits).

## Decisions requested

**A. Disposition amendment — pick one:**
   1. (recommended by lead) Add a PnL limb: KEEP requires `n≥30 AND WR≥52%
      AND net PnL ≥ $0` at deadline; else KILL. Rationale: a rule that keeps
      a money-losing signal is broken.
   2. Keep the bar as registered (KEEP on WR alone) — letter of the rule.
   3. Replace with avg-net limb: `n≥30 AND avg net ≥ $0`.
   4. Other — your wording; it goes into shadow_disposition.json verbatim.

**B. The exit asymmetry — pick one:**
   1. (recommended by lead) Commission a targeted stop-cluster study FIRST
      (backtest hard_max_loss / ATR-SL / cut-loser levels against the audited
      24h-hold distribution — are −3~−6% stops too wide for winners capped
      at +1~3%?). n=45 is too small to re-engineer exits by feel.
   2. Change exits now (e.g. PROFIT_MONSTER_BYPASS for atr-trend + own ATR
      exit logic per add-signal Step 5c — bigger change, replaces PM).
   3. Tighten stop constants immediately (fastest, least evidence).

**C. Collection posture:** keep collecting as-is until 12-06 regardless of
A/B? (lead default: yes — shadow sizes are tiny, the reckoning deadline is
the natural decision point.)

## Constraints you already own

- `hermes_constants.py` values are protected (line 2: ask T first) — any
  stop/flag value change needs your sign-off in this run.
- Audit #2 sizing rule stands: ≥30 forward days + day-blocked CI excluding 0
  BEFORE any size, independent of the reckoning.
- n=45 is past "too small to judge" but modest; cohorts (conf≥78 n=11) are
  very small.

Record the decision (A/B/C choices) in the kanban/checkpoint as usual.
