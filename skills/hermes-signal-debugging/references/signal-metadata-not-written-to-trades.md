# Signal Metadata Not Written to PostgreSQL Trades — 2026-06-02

## Finding

All trade metadata fields are NULL in PostgreSQL `trades` table across all 193 trades in the 48h window:

```
signal_z_score: NULL
signal_z_score_tier: NULL  
signal_momentum_state: NULL
signal_rsi_14: NULL
signal_macd_hist: NULL
entry_regime_4h: NULL
entry_timing: NULL
entry_bb_position: NULL
entry_fear_greed: NULL
entry_slope_4h: NULL
sl_distance: 0.0 (not NULL but wrong)
```

Meanwhile, `signal` column IS populated (e.g., `accel-300-,rs-s-broken`), `confidence` IS populated (e.g., 91-98), `leverage` IS populated.

## Why This Matters

The `accel-300-,rs-s-broken` SHORT signal has 114 trades in 48h with 57.9% winrate overall. But 48 losing SHORT trades (0% winrate, avg -0.814% PnL) vs 66 winners (avg +0.47% PnL) — same signal, same direction — and there's NO WAY to distinguish what made the losers different from winners because all the per-trade metadata is NULL.

The signal system COMPUTES z_score, momentum_state, RSI, MACD — but never writes them to the trade record. Without these fields, building filters for losing-trade patterns is impossible.

## What We Tried to Filter On (all that was available)

| Field | Losers | Winners | Finding |
|-------|--------|---------|---------|
| Leverage 3x SHORT | avg +0.015% | — | Flat |
| Leverage 5x SHORT | avg +0.201% | — | Better but not filterable |
| Confidence 95+ | 59.5% WR | — | Slightly better |
| Confidence 90-95 | 48.8% WR | — | Worst bucket |
| Confidence <85 | 61.7% WR | — | Best bucket |

Small differences, not actionable without more context.

## What We'd Need to Filter Properly

- `signal_momentum_state` — to exclude "exhaustion" entries in chop
- `signal_z_score` — to exclude mean-reversion entries at extreme z
- `entry_regime_4h` — to exclude counter-trend entries in strong regime
- `entry_timing` — to exclude entries at bad market hours
- `entry_bb_position` — to exclude entries at wrong BB extreme

## Root Cause Path

1. `signal_gen.py` (or signal sources like `zscore_pump.py`) compute these values during signal generation
2. `signal_compactor.py` builds hotset entries and writes to `hotset.json`
3. `decider_run.py` reads hotset and calls `brain.py add_trade()`
4. `brain.py add_trade()` INSERT to PostgreSQL — the signal metadata fields are NOT in the INSERT column list OR not extracted from the hotset entry to pass to the INSERT

## Next Steps (not implemented — requires T approval)

1. Trace the hotset.json entry structure — what fields does a hotset_final entry contain?
2. Find where `brain.py add_trade()` extracts hotset data — which columns are mapped to trade fields
3. Add `signal_z_score`, `signal_momentum_state`, `signal_rsi_14`, `signal_macd_hist` to trade INSERT
4. Verify: re-query PostgreSQL after fix and confirm fields are populated

## Key Files to Investigate

- `/root/.hermes/scripts/brain.py` — `add_trade()` function, INSERT column list
- `/root/.hermes/scripts/signal_compactor.py` — hotset entry structure, `_enrich_and_write_signals()`
- `/root/.hermes/scripts/signal_schema.py` — `record_signal_outcome()` trade INSERT
- hotset.json — actual entry structure for a trade signal