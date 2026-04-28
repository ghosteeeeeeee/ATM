---
name: zscore-momentum-signal
description: Price z-score momentum signal for Hermes — fires LONG when price is significantly above its recent average (established upward momentum) and SHORT when below. Backtest-driven per-token tuning. Separate standalone module. Related to per-token-signal-implementation (general pattern).
tags: [hermes, signal-generation, z-score, momentum, per-token-tuning]
triggers:
  - add z-score momentum signal to hermes
  - price z-score momentum
  - momentum confirmation signal
---

# Z-Score Momentum Signal — Implementation Notes

## Signal Philosophy

Unlike mean-reversion (where |z| high = price too far from average = revert),
here we treat high |z| as **momentum confirmation**:

- **LONG**: z_score > +threshold — price significantly above average = established upward momentum
- **SHORT**: z_score < -threshold — price significantly below average = established downward momentum

The move has inertia. High z-score means the market has committed to a direction.

## Key Design Decisions

### Why standalone module?
- Self-contained: all z-score logic in one file
- Own tuner DB (`zscore_momentum_tuner.db`)
- Does NOT import from signal_gen — signal_gen imports it
- Avoids circular dependency hell

### Per-token tuning
- Param grid: lookback 10-60 bars (step 2), threshold 1.5-4.0 (step 0.25)
- Backtest exits: opposite signal OR `lookback * 2` bars (hold = 2x entry window)
- **Minimum 15 signals required** before trusting tuned params (NOT 5 — 5 was too lenient)
- Tokens with <15 historical signals fall back to defaults (LB=24, TH=2.0, confidence=58)

### Confidence scoring
- Tuned tokens: `confidence = min(75, max(50, win_rate))`
- Default-param tokens: fixed `confidence = 58.0`

### Quality filters (anti-chop / anti-dud)

**Filter (A) — Volatility floor** (`_get_1m_atr()`):
- Blocks signals when 14-bar 1m ATR < `MIN_ATR_PCT_SIGNAL` (0.04%)
- Prevents z-score from firing as noise in ultra-low-vol conditions (σ_24% < 0.15%)
- ATR table: `candles_1m` (token, ts, open, high, low, close, volume)
- **Calibration note**: 0.15% was too high for 1m data — would block ~86% of tokens incl. BTC (0.054%), ETH (0.055%), SOL (0.041%). Use 0.02–0.05% for 1m candles.

**Filter (B) — Sustained momentum**:
- Requires `|z| > threshold` on current bar AND at least one of prior `MIN_SUSTAINED_BARS-1` bars
- Filters one-bar spikes that fire then immediately mean-revert
- Slice math: `closes[-lookback - offset:-offset]` (not `closes[-(offset+1)-lookback:-(offset+1)]` — that skips the bar immediately before current)
- Minimum data: `len(closes) >= lookback + offset` before checking prior bar

### Source tag convention
- LONG: `zscore+` (e.g., `zscore+24,2.00`)
- SHORT: `zscore-`
- Signal type: `zscore_momentum`

## Files

- `/root/.hermes/scripts/zscore_momentum.py` — standalone module
- `/root/.hermes/data/zscore_momentum_tuner.db` — tuner results (per-token best configs)
- `/root/.hermes/scripts/signal_gen.py` — imports and calls `zscore_momentum._run_zscore_momentum_signals()`
- `/root/.hermes/scripts/signal_compactor.py` — routing weights for `zscore+`/`zscore-`

## Tuner DB Schema

```sql
CREATE TABLE token_best_zscore_config (
    token        TEXT PRIMARY KEY,
    lookback     INTEGER NOT NULL,
    threshold    REAL    NOT NULL,
    win_rate     REAL    NOT NULL,
    avg_pnl_pct  REAL    NOT NULL,
    signal_count INTEGER NOT NULL,
    total_long   INTEGER NOT NULL DEFAULT 0,
    total_short  INTEGER NOT NULL DEFAULT 0,
    updated_at   INTEGER NOT NULL
)
```

## Key Backtest Findings (156 tokens, n≥15)

- **Avg WR: 58%**, Median WR: ~60%
- **87% of tokens have positive avg_PnL** even with conservative n≥15
- Optimal threshold cluster: **2.0–2.5** (49/156 tokens prefer 2.25)
- Lookback is evenly distributed — per-token tuning genuinely matters
- LONG dominates SHORT: ~65% LONG signals vs ~35% SHORT
- **ETH SHORT is a notable outlier**: SHORT WR 83% vs LONG WR 50%
- Tokens where SHORT outperforms LONG by wide margin: ALGO, KAITO, STG, CATI, FET, ZEC, ZRO

## Running the Tuner

```bash
# Full sweep
python3 /root/.hermes/scripts/zscore_momentum.py --sweep

# Single token
python3 /root/.hermes/scripts/zscore_momentum.py --sweep --token BTC

# Run signal generation only
python3 /root/.hermes/scripts/zscore_momentum.py --run-signals
```

## Important Gotchas

1. **Patch bug**: When editing `_run_zscore_momentum_signals()`, the `closes = get_price_history(...)` line was accidentally deleted during a patch. Always verify the patched function has all lines present — particularly data-fetch lines that precede the main logic.

2. **DB schema migration**: The first version of the tuner DB didn't have `total_long`/`total_short` columns. When adding columns to an existing table, either drop-and-recreate or use `ALTER TABLE ... ADD COLUMN` with try/except pass (safe for both new installs and existing dbs with the column already present).

3. **Sweep minimum threshold**: Setting n≥5 let through tokens with only 5 signals — their 100% WR was noise. Required bump to n≥15. Even n≥15 is still somewhat aggressive for production; monitor actual signal WR vs backtest WR.

4. **Z-score direction matters**: z > 0 means price above average (upward momentum confirmed). The original CMC script only triggered on z > threshold (one direction only). Hermes version fires on both directions.

5. **Hold period**: `_backtest_params` uses `hold = min(lookback * 2, n - i - 1)` — exits after 2x the entry lookback. This is a fixed hold, not a true exit signal. Real-world performance may differ.

6. **Volatility floor calibration for 1m data**: When adding ATR-based filters to 1m signals, be aware that 1m ATR% is 5–30x smaller than on higher timeframes. A threshold of 0.15% blocks virtually all liquid tokens (BTC=0.054%, ETH=0.055%, SOL=0.041%). For 1m candles, 0.02–0.05% is the right range. Always validate against actual token ATR% before setting the constant.

7. **Sustained filter off-by-one**: The prior-bar slice must use `closes[-lookback - offset:-offset]`, NOT `closes[-(offset+1)-lookback:-(offset+1)]`. The latter skips `closes[-2]` (bar immediately before current) and checks `closes[-3]` instead.
