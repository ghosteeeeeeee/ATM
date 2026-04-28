---
name: momentum-mean-reversion-backtest
description: Backtest combined momentum (acceleration crossing) + mean-reversion (percentile) signals. Includes methodology, key findings, and implementation guide.
tags: [backtest, signal-generation, momentum, mean-reversion, hermes]
---

# Momentum + Mean-Reversion Combined Signal Backtest

## When to Use
When testing whether combining two signal types (e.g., pct-hermes percentile + momentum acceleration) produces better results than either alone.

## Methodology

### Step 1: Understand the data schema first
```python
# Check available TFs and data range
DB = '/root/.hermes/data/candles.db'
sqlite3.connect(DB).execute("SELECT name FROM sqlite_master WHERE type='table'")
# Tables: candles_1m, candles_15m, candles_1h, candles_4h
# Check rows and range per TF:
sqlite3.execute("SELECT COUNT(*), MIN(ts), MAX(ts) FROM candles_1m")
```

### Step 2: Define signal conditions
Test multiple variants:
- Signal A alone (baseline)
- Signal B alone (baseline)
- Combined STRICT (A AND B — both must pass)
- Combined LENIENT (A OR B — either passes)
- Extreme variant (A<=20 AND accel crossing)

```python
SIGNALS = {
    'pct_hermes_only': {
        'long':  lambda pl, ps, ac, zn, zt: pl <= PCT_LONG_OVERSOLD,
        'short': lambda pl, ps, ac, zn, zt: ps >= PCT_SHORT_OVERBOUGHT,
    },
    'accel_only': {
        'long':  lambda pl, ps, ac, zn, zt: ac is not None and zt < 0 and ac > ACCEL_CROSS_UP,
        'short': lambda pl, ps, ac, zn, zt: ac is not None and zt > 0 and ac < -ACCEL_CROSS_DOWN,
    },
    'combined_strict': {
        'long':  lambda pl, ps, ac, zn, zt: pl <= PCT_LONG_OVERSOLD and (zt < 0 and ac > ACCEL_CROSS_UP),
        'short': lambda pl, ps, ac, zn, zt: ps >= PCT_SHORT_OVERBOUGHT and (zt > 0 and ac < -ACCEL_CROSS_DOWN),
    },
    'combined_lenient': {
        'long':  lambda pl, ps, ac, zn, zt: pl <= PCT_LONG_OVERSOLD or (zt < 0 and ac > ACCEL_CROSS_UP),
        'short': lambda pl, ps, ac, zn, zt: ps >= PCT_SHORT_OVERBOUGHT or (zt > 0 and ac < -ACCEL_CROSS_DOWN),
    },
}
```

### Step 3: Compute indicators with no lookahead
Precompute indicator series, shift by 1 bar to avoid lookahead bias:
```python
for i in range(n):
    pl = pct_long_series[i]
    ac = accel_series[i]
    zt = z_then_series[i]  # from ACCEL_WINDOW bars ago
    if signal_fn(pl, ps, ac, zn, zt):
        # enter at bar i, compute returns at bar i+horizon
```

### Step 4: Test across multiple timeframes and horizons
- Use the finest TF available (1m if data exists, else 15m, else 1h)
- Test horizons from 5m to 24h depending on data depth
- Report: N signals, avg return, hit rate, win/loss ratio

### Step 5: Backtest Volatility Explosion Signals
```python
# Core signal: volume > 30x token avg AND candle > 3%
# Compute token's normal avg volume first (not window median — avoids spike skew)
c.execute("SELECT AVG(volume) FROM candles_15m WHERE token=?", [token])
token_avg_vol = c.fetchone()[0] or 1

# Per-event:
vol_ratio = current_vol / token_avg_vol
pct = (current_close - prev_close) / prev_close * 100

# Follow-through: next N candles
future_pcts = [(f[4] - current[4]) / current[4] * 100 for f in future]
max_future = max(future_pcts)
min_future = min(future_pcts)
total_future = sum(future_pcts)

# Key distinction:
# - HIT (continued): pct and total_future same sign
# - REVERSED: pct > 0 but total_future < -0.5 OR pct < 0 and total_future > 0.5
# - FADE: |total_future| < 0.5 (no follow-through)

# Pullback ratio: how much of the impulse was given back?
pullback = abs(net_change) / abs(impulse) if abs(impulse) > 0 else 0
```

### Step 6: Iterate on signal design based on empirical findings
- First hypothesis failed (momentum_burst: 0% precision) → redesign
- Second hypothesis failed (range compression: 4% precision) → redesign
- Third approach: vol spike + candle threshold → 22% precision, 83.8% "tradeable" (HIT + REVERSAL)
- Key insight: if first 2 approaches fail, change direction rather than tweaking thresholds

## Key Findings (from pct-hermes + acceleration backtest)

### The winning combination
```
LONG:  pct_long <= 30  AND  acceleration crosses above 0 (from negative)
SHORT: pct_short >= 70 AND  acceleration crosses below 0 (from positive)
```

### Critical Finding: Volatility Explosions = Mean Reversion (68% of the time)
Backtesting 37 vol explosion events (volume >30x token avg, candle >3%) across 50 tokens in 72h:

| Outcome | Count | Rate |
|---------|-------|------|
| Reversed (mean reversion) | 25 | 68% |
| Continued (true momentum) | 9 | 24% |
| Faded (no follow-through) | 3 | 8% |

When reversed: median 81% pullback, avg 99% pullback of the impulse.

**Implication:** A vol explosion signal is primarily a MEAN REVERSION signal, NOT a momentum signal.
Only the REQ case (42% pump) showed true accumulation before explosion — 2h of flat price + 10-50x volume = smart money accumulating.
All other "pumps" were trends with vol spikes that reversed.

**Two modes for vol_explosion signals:**
1. Mean Reversion Mode (68% accuracy): Fire on candle direction, enter reversion when price pulls back >50% of impulse. Target: pre-spike price.
2. Breakout Confirmation Mode (24% accuracy but huge winners): Only when stagnancy precondition met (range<2%, avg<1% change, sustained elevated volume). Like the REQ case.

**Signal redesign:** Instead of `momentum_burst+` (fired 0% precision), use `vol_explosion+` / `vol_explosion-` with mean reversion logic. Or add stagnancy filter for breakout-only mode.

See: `/root/.hermes/plans/2026-04-19_014500-pump-finder-signal-momentum-burst.md`

### Results across TFs

| TF | Direction | N | 4h Ret | 4h Hit | 16h Ret | 16h Hit |
|----|-----------|---|--------|--------|---------|---------|
| 15m | SHORT | 904 | +0.31% | 63% | +1.57% | **77%** |
| 1h | LONG | 21 | **+3.78%** | **100%** | +4.59% | 95% |

### Critical insights
1. **pct-hermes alone is the workhorse** — consistent ~50-75% hit rate across all TFs
2. **Acceleration alone is noise at short horizons** — ~45-50% hit rate at 1m/15m, improves at 16h+
3. **AND logic > OR logic** — lenient combination (EITHER condition) dilutes with noise; strict (BOTH) filters to high-conviction
4. **AXS drives outsized results** — dominates signal counts; validate on broader universe
5. **Signal improves with horizon** — best results at 16h, not 4h
6. **Combined is best for SHORT, not LONG** — pct-hermes alone works for LONG; combined adds value primarily for SHORT direction

## Implementation in signal_gen.py
The final signal was implemented as `_run_momentum_signals()` with:
- signal_type = 'momentum'
- source = 'momentum+' or 'momentum-'
- Confidence: base 58-70 + accel strength bonus (up to +8) = max 85%
- Called from `run()` at confluence detection stage
- No restart needed — pipeline reads file fresh each minute

## Files
- Backtest: `/root/.hermes/scripts/backtest_combined_momentum_mean_reversion.py`
- Implementation: `/root/.hermes/scripts/signal_gen.py` (~1453-1610)
