# Detection-vs-Execution Reconciliation — 2026-11-20

Descriptive only (§E-SPEC): how stale/drifted was the signal when the trade
opened, and does gap class associate with PnL? No filter recommendations.

- **Window**: last 30d closed trades anchored `MAX(close_time)` → 2026-10-21 17:03:26 .. 2026-11-20 16:08:09, **n=630** (psql `brain.trades`, status=closed).
- **Reproduce**: `python3 brain/analysis/detection_execution_reconciliation_2026-11-20.py`
- **Units**: money = `pnl_usdt` only; `trades.stop_loss` (trail-mutated) never read;
  no `pnl_pct`-vs-price comparisons (landmine #193).
- **Thresholds**: all v2 filter thresholds imported from `hermes_constants`.

## Joins & coverage

| Join / coverage | n | % of window |
|---|---:|---:|
| detection record joined (`signals`, coin+dir+closest created_at ≤ open) | 207 | 32.9% |
| …of trades opened inside signals-table retention (≥ 2026-11-06 04:00:39) | 207/211 | 98.1% of era |
| `_signal_metadata` non-empty | 625 | 99.2% |
| `staleness_minutes` present (exec-time age stamp) | 579 | 91.9% |
| RSI leg evaluable (meta rsi_14 + 1m candles at open) | 602 | 95.6% |
| momentum state evaluable | 558 | 88.6% |
| v2 momentum qty evaluable (30x1m / 10x5m linreg) | 559 | 88.7% |
| v2 velocity qty evaluable | 559 | 88.7% |
| gap leg evaluable (meta gap_at_entry + 5m candles at open) | 568 | 90.2% |

> **Join-quality caveat (data fact, not a recommendation):** executed detection
> rows are purged ~1h after execution (`signal_compactor._purge_executed_signals`),
> so for older trades the spec join lands on an *earlier surrogate* signal, not the
> true parent. Cross-check vs `_signal_metadata.staleness_minutes` (stamped live at
> exec): |join_age − staleness| P50=121.5m P90=672.6m; only 5/167 (3.0%) within ±3min.

## G1 — signal age (open_time − detection created_at)

**Spec-literal (detection join), n=207:** P50=75.6m  P90=635.9m  P99=1302.4m

| age bucket | n | WR | avg pnl_usdt | total pnl_usdt |
|---|---:|---:|---:|---:|
| <5m | 16 | 43.8% | -0.02 | -0.29 |
| 5-10m | 5 | 20.0% | -0.05 | -0.27 |
| 10-30m | 41 | 43.9% | -0.01 | -0.21 |
| >30m | 145 | 50.3% | -0.01 | -1.17 |

**Cross-check — `_signal_metadata.staleness_minutes` (exec-time stamp), n=579:** P50=1.9m  P90=7.4m  P99=10.1m

| age bucket | n | WR | avg pnl_usdt | total pnl_usdt |
|---|---:|---:|---:|---:|
| <5m | 437 | 55.6% | -0.01 | -2.66 |
| 5-10m | 133 | 51.9% | -0.01 | -1.08 |
| 10-30m | 9 | 33.3% | -0.03 | -0.27 |
| >30m | 0 | — | — | — |

> The staleness stamp is the trustworthy age (purge-immune); the join-age table
> is reported because §E-SPEC defines G1 from the detection join. Both are shown;
> neither is used to propose anything.

## G2 — condition drift (detection → open)

Detect side: `meta.rsi_14` / `meta.gap_at_entry` / `meta.momentum_state` where
present; raw v2 momentum/velocity quantities (not stored in metadata) are evaluated
at the metadata-implied detection time (`open − staleness_minutes`, else joined
created_at). Open side recomputed from local candles at `open_time` (same formulas
as the source filters). Verdict flips use thresholds **imported from
`hermes_constants`**: LONG RSI band [`BB_BOUNCE_V2_RSI_MIN`, `BB_BOUNCE_V2_RSI_MAX`],
SHORT `≥ BB_BOUNCE_V2_SHORT_RSI_OVERBOUGHT`; momentum `BB_BOUNCE_V2_MOM_MIN` /
`BB_BOUNCE_V2_SHORT_MOM_MAX`; velocity `BB_BOUNCE_V2_VEL_MIN` /
`BB_BOUNCE_V2_SHORT_VEL_5M_MAX`. Gap has no v2 threshold → sign flip = zero-cross
(price crossing the EMA).

### RSI drift (detect `meta.rsi_14` → Cutler RSI(14) at open), evaluable n=602

| abs(drift) bucket | n | WR | avg pnl_usdt | total pnl_usdt |
|---|---:|---:|---:|---:|
| <5 | 184 | 50.5% | -0.01 | -1.50 |
| 5-10 | 147 | 53.1% | -0.01 | -1.29 |
| 10-20 | 158 | 51.3% | -0.01 | -1.09 |
| >=20 | 113 | 60.2% | +0.00 | +0.46 |

| threshold verdict | n | WR | avg pnl_usdt | total pnl_usdt |
|---|---:|---:|---:|---:|
| SIGN FLIP across threshold | 201 | 54.7% | -0.00 | -0.59 |
| no flip | 401 | 52.4% | -0.01 | -2.83 |

### Momentum state flip (`meta.momentum_state` → recomputed at open)

| state verdict | n | WR | avg pnl_usdt | total pnl_usdt |
|---|---:|---:|---:|---:|
| rising↔falling flip | 83 | 57.8% | +0.01 | +0.63 |
| no direction flip | 475 | 54.3% | -0.01 | -4.14 |

(evaluable n=558; flat transitions counted as no direction flip)

### v2 momentum quantity drift (LONG: 30×1m linreg; SHORT: 10×5m linreg), evaluable n=559

| abs(drift) bucket | n | WR | avg pnl_usdt | total pnl_usdt |
|---|---:|---:|---:|---:|
| <0.02 | 516 | 54.7% | -0.01 | -3.68 |
| 0.02-0.05 | 37 | 54.1% | -0.01 | -0.20 |
| 0.05-0.1 | 5 | 60.0% | +0.06 | +0.29 |
| >=0.1 | 1 | 100.0% | +0.04 | +0.04 |

| threshold verdict | n | WR | avg pnl_usdt | total pnl_usdt |
|---|---:|---:|---:|---:|
| SIGN FLIP across threshold | 44 | 56.8% | -0.02 | -0.94 |
| no flip | 515 | 54.6% | -0.01 | -2.61 |

### v2 velocity quantity drift (LONG: 15m 1m-bars; SHORT: 4×5m bars), evaluable n=559

| abs(drift) bucket | n | WR | avg pnl_usdt | total pnl_usdt |
|---|---:|---:|---:|---:|
| <0.1 | 290 | 56.2% | -0.01 | -2.58 |
| 0.1-0.5 | 222 | 53.6% | -0.01 | -1.46 |
| 0.5-1 | 42 | 50.0% | +0.01 | +0.27 |
| >=1 | 5 | 60.0% | +0.04 | +0.22 |

| threshold verdict | n | WR | avg pnl_usdt | total pnl_usdt |
|---|---:|---:|---:|---:|
| SIGN FLIP across threshold | 88 | 58.0% | +0.00 | +0.43 |
| no flip | 471 | 54.1% | -0.01 | -3.98 |

### gap drift (`meta.gap_at_entry` → EMA300/100/50 gap at open, pp), evaluable n=568

| abs(drift) bucket | n | WR | avg pnl_usdt | total pnl_usdt |
|---|---:|---:|---:|---:|
| <0.25 | 115 | 44.3% | -0.03 | -2.95 |
| 0.25-0.5 | 99 | 58.6% | -0.00 | -0.30 |
| 0.5-1 | 130 | 61.5% | +0.01 | +1.80 |
| 1-2 | 149 | 53.0% | -0.02 | -2.39 |
| >=2 | 75 | 53.3% | -0.00 | -0.16 |

| threshold verdict | n | WR | avg pnl_usdt | total pnl_usdt |
|---|---:|---:|---:|---:|
| SIGN FLIP across threshold | 164 | 53.0% | -0.01 | -1.47 |
| no flip | 404 | 54.7% | -0.01 | -2.53 |

## G3 — metadata missing (coverage)

- **G3 n=423 (67.1% of window)** — coverage = 32.9% classifiable.
  - no detection join: 423 (signals table retains ~14d: min `2026-11-06 04:00:39` + 1h executed-row purge)
  - empty `_signal_metadata`: 0
  - joined+meta but zero evaluable drift fields (age<10m only): 0
- G3 outcome: n=423 WR=54.6% avg=-0.01 total=-2.23 pnl_usdt

## Key findings — gap class × n / WR / pnl (pnl_usdt basis)

Partition precedence: **G3** (unjoinable) > **G1** (age ≥10m) > **G2** (sign-flip drift, age <10m) > **G0** (clean). Drift tables above are computed over ALL evaluable trades, so drift×PnL is visible regardless of class.

| class | definition | n | WR | avg pnl_usdt | total pnl_usdt |
|---|---|---:|---:|---:|---:|
| **G0** | joined, age<10m, no sign-flip drift | 19 | 36.8% | -0.03 | -0.59 |
| **G1** | joined, signal age ≥10m | 186 | 48.9% | -0.01 | -1.38 |
| **G2** | joined, age<10m, ≥1 sign-flip across v2 thresholds | 2 | 50.0% | +0.01 | +0.03 |
| **G3** | absent/unjoinable detection record or metadata | 423 | 54.6% | -0.01 | -2.23 |
| total | | 630 | | | |

> ⚠️ **G1 footnote (join quality):** the spec-literal join ages are 97% discordant with the
> trusted `staleness_minutes` stamp (only 5/167 within ±3min; |Δ| P50=121.5m; join-age P50=75.6m
> vs stamp P50=1.9m) — read G1=186 as *"spec-literal detection-join age"*, **not** as 186 truly
> stale signals. On purge-immune staleness stamps almost nothing is ≥10m stale (sensitivity
> G1=1 below), and most of the window's trades predate the signals-table era entirely (G3=423).

**Sensitivity** — same rules but age from `staleness_minutes` (purge-immune; only trades carrying the stamp):

| class | n | WR | avg pnl_usdt | total pnl_usdt |
|---|---:|---:|---:|---:|
| G0 | 59 | 44.1% | -0.03 | -1.85 |
| G1 | 1 | 100.0% | +0.01 | +0.01 |
| G2 | 100 | 55.0% | +0.00 | +0.07 |
| G3 | 470 | 52.8% | -0.01 | -2.40 |

## Method notes

- Detection join: `SELECT token, direction, created_at FROM signals` (mode=ro),
  coin+direction, closest `created_at ≤ open_time` (bisect), deterministic by `id`.
- `meta.gap_at_entry` is stamped at decision time from the signal price vs a
  decision-time EMA (`decider_run.py:6233`); its detect→open drift therefore
  measures decision→fill gap movement — noted, not corrected (§E-SPEC fields).
- RSI method = Cutler equal-weight (matches how `meta.rsi_14` was produced,
  `signal_schema._enrich_indicators`); applying it against the v2 RSI thresholds
  follows the AGENTS.md CFX precedent (detect 44.6 vs `RSI_MIN=35`).
- All SQL SELECT-only; SQLite `mode=ro`; connections/cursors closed in `finally`.

