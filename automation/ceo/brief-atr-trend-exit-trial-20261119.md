# DECISION REQUEST — atr_trend_accel exits: adopt longer-hold engine, or status quo to 12-06?

Asked by: lead agent (DSH session), on CEO instruction. All numbers verified by
direct queries this session; full artifact: `brain/analysis/atr_trend_exit_engine_compare_20261119.py`
(committed, re-runs clean). Prior ruling context: your deep run 20261119T210516Z
ruled **B = option 1 (study first, no exit/constant changes without T sign-off)** —
this IS that study, delivered.

## What was measured

`brain/shadow_trades.db` holds a replay of **every** atr_trend_accel signal fire
through each exit engine independently (1,932 closed rows; 1,807 complete-case,
same signals through every engine, 2026-11-06 → 11-19; gross pct, fee 0.04 +
slip 0.10 excluded; entries at signal fire on 1m candles):

| Engine | mean | median | WR | hold | paired vs live pm_trail |
|---|---|---|---|---|---|
| ride_it (24h max) | **+0.363** | 0.327 | 61.2% | 242m | **+0.179pp, t=5.8, p=5.6e-9**, halves +0.344/+0.388 |
| universal_hold (8h) | **+0.303** | 0.294 | 58.7% | 282m | **+0.120pp, p=7.7e-5**, halves +0.260/+0.362 |
| speed_stale | +0.285 | 0.280 | 56.9% | 261m | — |
| hard_max | +0.195 | 0.000 | 49.5% | 217m | — |
| atr_sl_tp | +0.192 | −0.058 | 48.6% | 135m | +0.009, **p=0.74 (no difference)** |
| pm_trail (LIVE exit) | +0.183 | 0.384 | 81.6% | 114m | — |
| cut_loser | +0.164 | 0.000 | 48.9% | 212m | — |
| pump_exit | +0.086 | 0.000 | 49.7% | 120m | ❌ dead_money fires 99% at ~120m |
| rr_engine | +0.035 | −0.114 | 41.2% | 59m | ❌ worst |
| mfe_exit (sim, arm 0.40%/giveback 30%) | +0.056 | 0.295 | 55.2% | — | **−0.127pp, halves +0.055/+0.058 — consistently worse** |
| trail_arm_timeout n=1; wider_sl, extended_time n=0 | not populated for this signal | | | | |

- **mfe_exit:** atr-trend is NOT in `MFE_EXIT_SIGNALS` (only `jup_yolo`) — it
  never applied live; simulation says do not adopt.
- **Basis sanity:** pm_trail gross +0.183 − 0.14 fee/slip ≈ +0.04 net ≈ the
  live 47-trade net (−0.026/trade) — shadow magnitudes are believable.
- **Tradeoff (explicit):** pm_trail wins the typical signal (median 0.384 vs
  0.327; WR 81.6% vs 61.2%; beats ride_it on 53.5% of individual pairs).
  ride_it's mean edge is **tail capture** — it lets the +5~6% runners develop
  that PM caps at +1~3%, at the cost of more mid-size losers riding longer.
- **Triangulation:** matches your stop-cluster study (result-2: whole bleed is
  exit-side; stops median −3.51% margin vs winners +1.37%) AND the audited
  backtest (24h hold, mean +0.72%). Three independent reads say: exits are
  cutting the thesis short.

## The decision

**A. Pre-register a live exit trial for atr-trend ONLY** (automatic-implementation
pattern: ship OFF, collect live counterfactual, flip only with your approval;
scope via signal source so no other signal is touched). Choose engine:
   1. **ride_it-style 24h hold** (strongest mean, p=5.6e-9, tail-capture thesis)
   2. **universal_hold 8h** (middle ground, p=7.7e-5, less tail, less giveback)
   3. **neither engine — stop-cluster delay/tighter** (from result-2; but that
      study showed no robust stop width either)
   4. other wording from you
   Mechanically this needs either PROFIT_MONSTER_BYPASS_SIGNALS entry for
   atr-trend + ride_it/universal exit logic scoped to it, or a scoped hold
   extension — either way **hermes_constants values are protected (line 2):
   your sign-off in this run is the authorization.**

**B. Status quo** — no exit change; the 12-06 reckoning (3-limb bar) adjudicates
signal+exit-as-is, with this table as evidence on whether to KILL vs amend.

**C. Other.**

## Constraints

- n=1,807 shadow paper replays (13-day window, correlated signal population);
  mean-vs-median split is real (typical-signal winner vs runner-capture winner).
- Audit #2 sizing rule unchanged (≥30 forward days day-blocked CI before size).
- Live 47 trades remain the reckoning basis; this table informs the exit half,
  not the entry half.

Record A/B/C in the checkpoint/kanban as usual.
