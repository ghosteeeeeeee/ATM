# Confluence Gate + SHORT Signal Drought — Session Findings (2026-05-12)

## Problem

**Q:** "more live trades being opened from hot-set? was regime filtering too tight?"

**Root cause found:** Signal compactor confluence gate (`CONFLUENCE_REQUIRED=2`) is blocking nearly all SHORT signals from reaching hot-set. This is NOT a regime filtering issue — it's a signal diversity/combination issue.

## Confluence Gate Mechanics

Signal compactor groups signals by `combo_key` (token:direction:source1,source2,...). A combo passes the confluence gate only if it has **2+ unique signal source types**:

| Combo | Unique Types | Outcome |
|---|---|---|
| `RS:SHORT:rs-r180,rs-r196` | 1 (rs-r) | **BLOCKED** |
| `RS:SHORT:rs-r295,rs-r488` | 1 (rs-r) | **BLOCKED** |
| `SUPER:SHORT:rs-r120,vel-hermes-` | 2 (rs-r, vel-hermes-) | **PASSES** |
| `ASTER:SHORT:vel-hermes-` | 1 (vel-hermes-) | **BLOCKED** |

**34 SHORT combo_keys in 5-min window. All single-source → blocked. Zero entering hot-set.**

## Why RS SHORT and vel_hermes SHORT don't combine

- `rs.py` generates SHORT via resistance/rejection detection. Output: `rs-r###` (single type).
- `vel_hermes` generates SHORT via z-score rising. Output: `vel-hermes-` (single type).
- Even when both fire for the same token within the 5-min window, the combo is `rs-r###,vel-hermes-` → 2 unique types → passes. But this coincidence is rare.

## Why 11 of 13 Signals Return None

From `run_all_signals()` in a 2-hour run:
- `accel_300` → fires LONG (44 signals) ✅
- `rs` → fires both LONG/SHORT (600 signals) ✅
- `ma_cross`, `hh_hl`, `macd_accel`, `trend_purity`, `ema9_sma20`, `r2_trend`, `volume_hl`, `ma300_candle_confirm`, `atr_compression`, `exhaustion` → all return None
- `vel_hermes` → fires SHORT only (4 signals) — PLUS direction disabled 2026-05-06 for 31% WR

These 11 signals detect conditions not met in current market ( SHORT_BIAS on BTC/ETH/SOL/SUI).

## Market Regime State (2026-05-12 ~00:00 UTC)

| Asset | Regime | Slope | r² |
|---|---|---|---|
| BTC | SHORT_BIAS | -1.17 | 0.33 |
| ETH | SHORT_BIAS | -0.027 | 0.18 |
| SOL | SHORT_BIAS | -0.0037 | 0.57 |
| SUI | SHORT_BIAS | -0.00009 | 0.60 |

Market is consistently SHORT_BIAS but `_get_regime_1m()` in decider_run.py is **commented out** — not wired into the pipeline.

## Key Code Locations

- Confluence gate: `signal_compactor.py` lines 580-585 — `CONFLUENCE_REQUIRED = 2`
- Group by combo_key: lines 420-446
- WR gate (broken): `_get_token_wr()` lines 25-58 — queries PostgreSQL which has 0 closed trades → never fires
- Regime lookup: `signal_compactor.py` uses `get_regime_5m` (not 1m)
- `_get_regime_1m()`: `decider_run.py` lines 76-109 — defined but **not called** anywhere in hot-set path

## Fix Options

1. **Relax confluence gate** — lower to `CONFLUENCE_REQUIRED=1` for SHORT direction only, or allow single-source RS SHORT if confidence ≥75
2. **Wire regime filter into pipeline** — uncomment/use `_get_regime_1m()` to block counter-regime signals at the compactor
3. **Fix WR gate** — point `_get_token_wr()` at archive SQLite (`trades_analysis.db`) instead of empty PostgreSQL
4. **Investigate silent signals** — 11 signals returning None in current market conditions