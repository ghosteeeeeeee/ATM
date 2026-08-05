# Pipeline Timing — Architecture Decision (2026-05-06)

**Problem:** `signals_runner` took 62s for 21 signals. Pipeline blocked for 62s on every cycle.

**Root cause:** Three slow signals each call `get_momentum_stats(token)` for all 191 tokens:
- `pct_hermes`: ~20s
- `vel_hermes`: ~14s
- `phase_accel`: ~21s

Each call fetches ~60,480 rows of 1-min candles from SQLite and runs O(n) computation. Running sequentially = 56s just for these three.

## Architecture Options Evaluated

### ThreadPoolExecutor — FAILS
Threads share the LRU cache. But Python GIL serializes CPU-bound work across threads. Result: slower than sequential, not faster.

### ProcessPoolExecutor (5 workers) — Marginal improvement
Real CPU parallelism, but each subprocess starts with cold cache. 3 slowest overlap to ~21s, but 18 fast still run ~62s total.

### Background run (IMPLEMENTED) — Correct solution
Run `signals_runner` in background via `run_bg()` in `run_pipeline.py`. Non-signal steps start immediately. Pipeline exit: ~seconds.

## LRU Cache Behavior

- `get_price_history()` in signal_gen.py has `@lru_cache(maxsize=128)` — cache is per-process
- ProcessPoolExecutor subprocesses each start with empty cache
- ThreadPoolExecutor shares cache but GIL prevents parallel CPU work
- **Key finding:** warm cache second pass is only 1.7x faster (16.7s vs 28.8s) — bottleneck is SQLite I/O + numpy computation, not DB connection overhead

## Implementation

```python
# run_pipeline.py — signals_runner runs in background
run_bg('signals_runner', ['--fast'])
```

Non-signal pipeline steps: ~1s total. signals_runner (62s) runs in background.

## ProcessPoolExecutor Worker Count

- 4 CPU cores on this machine
- 5 workers: minimal overhead, real parallelism
- 21 workers: process spawn overhead dominates, times out
- 5 workers is the practical maximum

## Signals Runner Architecture (2026-05-06)

signals_runner runs via `run_bg()` — starts as background process, writes hotset.json for next cycle.

Non-signal steps (decider, position_manager, hermes-trades-api) read the hotset from the PREVIOUS cycle — this was always the design, even before the architecture migration.

The background approach means the 62s signals_runner doesn't block anything downstream.

---

# Signal Quality Deep-Dive (2026-05-06)

## The Three Slow Signals — Why They're Losing Money

### pct_hermes (21s, fires LONG mean-reversion at bottom of 42d range)
**Logic:** price is at pct_rank >= 72 percentile of 42-day lookback → LONG. pct_rank <= 28 → SHORT.

**Problem:** In a sustained downtrend, price is "at the bottom of 42 days" for WEEKS. This catches falling knives. In a bull market, pct_rank >= 72 fires at the TOP — meaning LONG fires at price peaks (mean-reversion against the trend).

**Evidence from recent trades:**
- PURR LONG (accel-300+, pct-hermes+): -1.10%
- ASTER LONG (accel-300+, pct-hermes+): -0.41%
- TRB SHORT (vel-hermes-): +1.20% — counter-trend SHORT worked

**Verdict:** `pct-hermes-` blocked (correct). `pct-hermes+` enabled but is a falling knife in bull market.

### vel_hermes (14s, fires SHORT on rising z-score momentum)
**Logic:** velocity > 0 (z-score rising = price above mean) → SHORT. velocity < 0 → LONG.

**Problem:** In a bull market, z-score velocity is positive most of the time. This constantly fades the move — fighting the trend.

**Evidence:**
- vel-hermes- SHORT on APEX: +0.80% (short worked because APEX was actually reversing)
- vel-hermes- SHORT on TRB/0G: small losses

**Verdict:** Mean-reversion signal fighting trending markets. Currently has some positive results but edge is thin.

### phase_accel (21s, fires on momentum phase transitions)
**Logic:** Detects when momentum "phase" transitions to "accelerating" using percentile + velocity over 42 days.

**Problem:** Phase detection is very slow to respond over 42-day lookback. By the time it detects acceleration, the move is already well underway. Fires in both directions with no clear edge.

**Evidence:** Recent trades show phase_accel combos winning and losing with no directional consistency.

## Key Insight: All Three Are Mean-Reversion in a Trending Market

The signals were likely built and tuned during a ranging or mean-reverting market. In the current bull market (2024-2026), they consistently fade the trend.

## Fix Options

1. **Raise thresholds** — pct_rank >= 85 (only most extreme) instead of >= 72. Fewer signals, higher conviction.

2. **Add regime filter** — Only fire pct-hermes+ LONG when market is not in broad downtrend. `compute_regime()` in signal_gen.py can provide this.

3. **Restrict to majors** — Mean-reversion works better on BTC/ETH/SOL where liquidity is stable. Small caps are noise.

4. **Disable pct-hermes+** — Given T's explicit "falling knife" concern, safest option is to disable until regime-aware.

## Recommendation

- `pct-hermes+` (LONG): Most dangerous — disabled or raise threshold to 85th percentile
- `pct-hermes-` (SHORT): Already disabled — keep it
- `vel-hermes-` (SHORT): Thin edge, keep enabled with monitoring
- `vel-hermes+` (LONG): Keep disabled
- `phase_accel`: No clear edge — monitor closely

## Shared Computation: get_momentum_stats Bottleneck

All three signals call `get_momentum_stats(token)` independently — 191 tokens × 3 signals = 573 calls per cycle. Each call:
1. `get_price_history(token, lookback_minutes=60480)` — ~60k rows from SQLite
2. `compute_zscore_percentile(prices, window=ZSCORE_HISTORY)` — O(n)
3. `compute_zscore_velocity(prices)` — O(n)
4. `get_tf_zscores(token)` — multi-timeframe z-score fetch
5. `rsi(prices)` + `macd(prices)` — O(n) each
6. `_persist_momentum_state()` — DB write

**The fix is architectural:** compute momentum_stats ONCE per token per cycle, pass dict to all 3 signals. This requires:
1. Adding `get_momentum_stats_batch(tokens)` in signal_gen.py
2. Modifying pct_hermes.py, vel_hermes.py, phase_accel.py to accept pre-computed stats
3. Updating `run_all_signals()` to pre-compute then pass to each signal

This would reduce 573 calls to 191 calls — 3x reduction in SQLite reads + CPU computation.
