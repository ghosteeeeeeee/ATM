---
name: per-token-signal-implementation
description: How to add a new per-token signal type to Hermes — backtest → store tuned params → standalone function → wire into pipeline. Use when implementing any new signal that benefits from per-token parameter tuning (e.g., MACD SHORT on 1m candles).
tags: [hermes, signal-generation, backtesting, implementation]
related_skills:
  - zscore-momentum-signal  # concrete implementation example
triggers:
  - add new signal to hermes
  - per-token param tuning
  - new signal type implementation
  - standalone signal function
---

# Per-Token Signal Implementation in Hermes

## When to Use This

Adding a new signal type that uses per-token tuned parameters. Example: MACD SHORT on 1m candles — different tokens work best with different MACD params.

## Architecture

```
backtest script (one-shot or cron)
    ↓ writes best params
tuner DB table (token_best_config_1m)
    ↓ read at startup
signal_gen.py standalone function (_run_xxx_signals)
    ↓ fires signals via add_signal()
signals DB
    ↓
signal_compactor.py (routes to hot-set scoring)
    ↓
ai-decider / guardian (execution)
```

## Step-by-Step Implementation

### Step 1 — Design the Signal

- **Direction**: LONG only, SHORT only, or both?
- **Timeframe**: 1m, 5m, 15m, 1h, 4h?
- **Data source**: local candles.db or Binance API?
- **API calls**: Zero HL/Binance API calls is preferred (read from local candles.db)
- **Backtest metric**: Win Rate, avg PnL%, profit factor, or composite score?

### Step 2 — Run Per-Token Backtests

```python
# Param grid — keep small to avoid combinatorial explosion
# For 1m candles: Fast=3-8, Slow=10-30, Signal=4-6, Hold=40-60
param_grid = [
    (f, sl, sg, h)
    for f in [3, 5, 6, 8]
    for sl in [10, 15, 20, 30]
    for sg in [4, 5, 6]
    for h in [40, 60]
    if sl > f
]
```

Pre-load ALL token closes into memory before sweeping (orders of magnitude faster than per-token DB queries):

```python
conn_c = sqlite3.connect(DB_CANDLES)
cc = conn_c.cursor()
cc.execute("SELECT token, close FROM candles_1m ...")
token_closes = {}
for token, close in cc.fetchall():
    if token not in token_closes:
        token_closes[token] = []
    token_closes[token].append(close)
conn_c.close()
```

Score each param per token:
```python
# Score = WR + (25 if avg_pnl > 0 else 0)
# Prefer params with WR >= 50% AND positive avg PnL
```

### Step 3 — Store Best Params in DB

Create a dedicated table (separate from existing `token_best_config` which is for 1h/4h):

```sql
CREATE TABLE IF NOT EXISTS token_best_config_1m (
    token TEXT PRIMARY KEY,
    fast INTEGER NOT NULL,
    slow INTEGER NOT NULL,
    signal INTEGER NOT NULL,
    hold_bars INTEGER NOT NULL,
    win_rate REAL NOT NULL,
    avg_pnl_pct REAL NOT NULL,
    signal_count INTEGER NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

Store with `INSERT OR REPLACE INTO` for easy updates.

### Step 4 — Write Standalone Signal Function

Create a `_run_{signal_name}_signals(prices_dict)` function in `signal_gen.py`. Place it BEFORE the pattern scanner section (around line 2100).

Structure:
```python
def _run_xxx_signals(prices_dict: dict) -> int:
    """
    Standalone [description] signal.
    Completely isolated: [data source], uses per-token tuned params from [DB table].
    
    Returns: number of signals written to DB.
    """
    # Module-level cache (reset in run() each cycle)
    params = _load_token_xxx_params()
    added = 0
    
    from signal_schema import add_signal, price_age_minutes
    from position_manager import get_open_positions as _get_open_pos
    
    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}
    
    for token, data in prices_dict.items():
        # Standard guards — always include ALL of these:
        if token.startswith('@'): continue
        if not data.get('price') or data['price'] <= 0: continue
        if token.upper() in open_pos: continue
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES): continue
        if is_delisted(token.upper()): continue
        if token.upper() in SHORT_BLACKLIST: continue
        if price_age_minutes(token) > 10: continue
        
        # Get per-token params (cache WR stats alongside params)
        p = params.get(token.upper(), params['DEFAULT'])
        
        # Fetch data (prefer local candles.db, not HL API)
        candles = _get_xxx_candles_from_db(token, lookback_bars=...)
        
        # Compute signal
        # ...
        
        # If signal fires:
        if crossover_detected:
            sid = add_signal(
                token=token,
                direction='SHORT',  # or 'LONG'
                signal_type='xxx_signal',
                source=f'xxx-{fast},{slow},{sig}@{hold}',
                confidence=min(75, max(50, round(wr))),
                value=float(confidence),
                price=price,
                exchange='hyperliquid',
                timeframe='1m',
                z_score=None,
                z_score_tier=None,
            )
            if sid:
                added += 1
                set_cooldown(token, 'SHORT', hours=1)
    
    return added
```

Load params ONCE at module level with lazy init and per-run reset:
```python
_TOKEN_XXX_CACHE = None

def _load_token_xxx_params():
    global _TOKEN_XXX_CACHE
    if _TOKEN_XXX_CACHE is not None:
        return _TOKEN_XXX_CACHE
    
    # Load from DB, include WR/n for confidence calculation
    cache = {}
    # ... DB query ...
    cache['DEFAULT'] = {'fast': 8, 'slow': 15, 'signal': 6, 'hold_bars': 60, 'wr': 56.0, 'n': 0}
    _TOKEN_XXX_CACHE = cache
    return cache
```

Reset cache at start of `run()`:
```python
# In def run():
_ZSCORE_CACHE.clear()
_VOL_CACHE.clear()
global _TOKEN_XXX_CACHE
_TOKEN_XXX_CACHE = None  # re-load from DB each run
```

### Step 5 — Wire Into run() Pipeline

In `run()`, after pattern signals and before confluence detection:

```python
confluences_added = 0
try:
    pattern_added = _run_pattern_signals(prices_dict)
    # ... existing signals ...
    xxx_added = _run_xxx_signals(prices_dict)
    if pattern_added or xxx_added:
        print(f'  Signals: {pattern_added} pattern + {xxx_added} xxx')
    confluences_added = run_confluence_detection(regime, long_mult, short_mult)
except Exception as e:
    print(f'  Signal error: {e}')
```

### Step 6 — Add to signal_compactor Routing

In `signal_compactor.py`, add to `SIGNAL_SOURCE_WEIGHTS`:

```python
('xxx_signal', 'xxx-'): 1.25,  # description
```

Weight guidance:
- 1.5 = very strong (e.g., hmacd-)
- 1.35 = strong (e.g., macd-accel-)
- 1.25 = standard
- 0.8 = suppress (weak signals)

### Step 7 — Create Tuner Script

Separate script at `/root/.hermes/scripts/{signal_name}_tuner.py` with:
- `run_sweep()` function
- Param grid matching what was used in backtesting
- Writes to the DB table
- Can run as systemd oneshot service

## Key Files

- `/root/.hermes/scripts/signal_gen.py` — main signal generation, add function here
- `/root/.hermes/scripts/signal_compactor.py` — hot-set scoring routing
- `/root/.hermes/scripts/signal_schema.py` — `add_signal()`, `set_cooldown()`
- `/root/.hermes/data/mtf_macd_tuner.db` — tuner results storage
- `/root/.hermes/data/candles.db` — local candle data (1m table: `candles_1m`)

## Critical Lessons Learned (from zscore_momentum implementation)

### Minimum signal count for tuning: n ≥ 15
- n=5 was far too lenient — tokens with 5 signals showing 100% WR are pure noise
- After bump to n=15: avg WR dropped from 69.6% to 58.0% — honest numbers
- For production, n=20+ is safer; n=15 is a reasonable floor
- Always fall back to defaults for tokens that don't meet the minimum

### Patch bug: data-fetch lines get eaten
- When patching nested code blocks (if/else inside a loop), the `closes = get_price_history(...)` line was accidentally deleted
- **Always verify** after patching: data-fetch lines before the main logic are the most fragile
- Fix: read the patched function end-to-end before declaring success

### DB schema migrations: use try/except for ALTER TABLE
- Adding columns to an existing table requires `ALTER TABLE ... ADD COLUMN`
- Wrap in try/except pass so it works on both fresh installs and existing DBs that already have the column
- Or: drop the table and rebuild if the schema changes (acceptable for tuner DBs with no user data)

### STANDALONE_SIGNALS bypass — never use for normal signals
- `STANDALONE_SIGNALS` in signal_compactor.py skips the entire confluence gate in guardian
- Only use it for truly external signals that cannot go through the normal pipeline at all
- Normal signals (reading from local candles.db) must follow the standard flow: signal_gen → signals_hermes_runtime.db → signal_compactor → hotset.json → guardian → HL
- Volume anomaly signals read from local candles.db, so they are NOT candidates for STANDALONE_SIGNALS
- Adding to STANDALONE_SIGNALS when you shouldn't = signal bypasses confluence gating = broken behavior

### Z-score can mean different things depending on signal philosophy
- **Mean reversion**: |z| high → price far from average → expect reversion back toward mean
- **Momentum confirmation**: z > +threshold → price above average → momentum has inertia, ride it
- Be explicit about which interpretation drives your signal design
- The backtest hold period (how long you stay in) must match the philosophy

## Important Constraints

1. **Zero HL API calls** in signal functions — use local candles.db only
2. **Cache DB reads** at module level, reset each `run()` cycle
3. **Include WR in confidence** — confidence = WR (55-70% range maps to 55-75)
4. **SHORT blacklist** enforced at signal level
5. **Recent trade guard** — `recent_trade_exists()` prevents over-trading
6. **Separate DB table** from existing 1h/4h tuner tables — don't mix timeframes
7. **Standalone function** — don't mix with existing signal logic to avoid corruption
8. **Minimum 15 signals before trusting tuned params** — n=5 is noise, n=15 is minimum
9. **Never use STANDALONE_SIGNALS bypass** for normal signals — it skips confluence gating

## Verification Checklist

- [ ] signal_gen.py loads without error
- [ ] New function is callable
- [ ] Params load from DB correctly (check with `python3 -c "import signal_gen; ..."`)
- [ ] signal_compactor has the new routing entry
- [ ] Cache reset works in `run()`
- [ ] Zero new HL API calls (check with `grep -rn "_http_post\|requests\." signal_gen.py`)
- [ ] DB query is fast (<1ms per token with index)
- [ ] Patch verified — read the patched function end-to-end after editing
- [ ] Backtest run on all tokens — distribution of WR/PnL looks sane
