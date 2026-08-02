# Spec: Auto-Enrichment + Backfill — Recording Entry Conditions for All Trades

**Date:** 2026-07-28
**Status:** SPEC — awaiting review
**Depends on:** `2026-07-28_hebbian-recall-spec.md` (Phase 1)

---

## Problem

2573 closed trades in PostgreSQL. ZERO have indicator data:

| Column | Populated | Source |
|--------|-----------|--------|
| signal_z_score | 0/2573 | should be z-score at signal time |
| signal_z_score_tier | 0/2573 | bucketed z-score |
| signal_rsi_14 | 0/2573 | RSI(14) at signal time |
| signal_macd_hist | 0/2573 | MACD histogram |
| signal_macd_value | 0/2573 | MACD line |
| signal_macd_signal | 0/2573 | MACD signal line |
| signal_momentum_state | 0/2573 | rising/falling/flat |
| entry_rsi_14 | 0/2573 | RSI at entry time |
| entry_macd_hist | 0/2573 | MACD hist at entry |
| entry_trend | 0/2573 | trend direction |
| regime | 0/2573 | market regime |
| entry_atr_14 | 0/2573 | ATR(14) at entry |
| entry_bb_position | 0/2573 | Bollinger Band position |
| _signal_metadata | 2573/2573 | all `{}` (empty JSON) |

**Root cause:** Active signal modules (accel_300, inverse_accel_300, tl_break, pattern_scanner) don't pass z_score/rsi/macd to `add_signal()`. The columns exist in the schema, the INSERT includes them, but callers pass `None` for all optional kwargs.

**Data available for backfill:**
- `price_history` table: ~2.7M rows, 1m close prices, covers all 2573 trade timestamps
- `candles.db`: OHLCV data (5m, 15m, 1h, 4h) for ATR computation
- Each trade has `token`, `open_time`, `signal`, `direction`

---

## Solution: Three Parts

### Part A: Auto-Enrichment in `add_signal()`

Add a `_enrich_indicators(token, price)` helper in `signal_schema.py` that computes indicators from `price_history` when the caller doesn't provide them. Called once per `add_signal()` invocation.

#### Indicators to Compute

| Indicator | Formula | Data Source | Bars Needed |
|-----------|---------|-------------|:-----------:|
| z_score | (last_price - mean) / std | price_history closes | 20 |
| z_score_tier | bucket z_score | derived | — |
| rsi_14 | 100 - 100/(1+RS), RS = avg_gain/avg_loss | price_history closes | 14+ |
| macd_value | EMA(12) - EMA(26) | price_history closes | 26+ |
| macd_signal | EMA(9) of macd_value | derived from MACD | 35+ |
| macd_hist | macd_value - macd_signal | derived | — |
| momentum_state | rising/falling/flat from 5-bar velocity | price_history closes | 5+ |
| bb_position | (price - lower) / (upper - lower), bands = mean ± 2*std | price_history closes | 20 |

#### z_score_tier Buckets

| z_score range | tier |
|---------------|------|
| z > 2.0 | `extreme_high` |
| 1.0 < z <= 2.0 | `high` |
| -1.0 <= z <= 1.0 | `neutral` |
| -2.0 <= z < -1.0 | `low` |
| z < -2.0 | `extreme_low` |

#### momentum_state

| 5-bar velocity | state |
|----------------|-------|
| > 0.1% | `rising` |
| < -0.1% | `falling` |
| else | `flat` |

#### Helper Function

```python
def _enrich_indicators(token, price=None):
    """Compute standard indicators from price_history. Returns dict or {}."""
    try:
        rows = get_price_history(token, lookback_minutes=60)  # ~60 1m bars
        prices = [r[1] for r in rows]  # (timestamp, price) tuples
        if len(prices) < 26:
            return {}
        
        last = prices[-1]
        result = {}
        
        # Z-score (20-bar)
        window = prices[-20:]
        mean = sum(window) / len(window)
        var = sum((p - mean) ** 2 for p in window) / len(window)
        std = var ** 0.5
        if std > 0:
            z = (last - mean) / std
            result['z_score'] = round(z, 4)
            result['z_score_tier'] = (
                'extreme_high' if z > 2 else 'high' if z > 1 else
                'extreme_low' if z < -2 else 'low' if z < -1 else 'neutral'
            )
        
        # RSI(14)
        if len(prices) >= 15:
            changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            gains = [c for c in changes[-14:] if c > 0]
            losses = [-c for c in changes[-14:] if c < 0]
            avg_gain = sum(gains) / 14 if gains else 0
            avg_loss = sum(losses) / 14 if losses else 0
            if avg_loss == 0:
                result['rsi_14'] = 100.0
            else:
                rs = avg_gain / avg_loss
                result['rsi_14'] = round(100 - 100 / (1 + rs), 2)
        
        # MACD (12, 26, 9)
        if len(prices) >= 35:
            def ema(values, period):
                k = 2 / (period + 1)
                e = sum(values[:period]) / period
                for v in values[period:]:
                    e = v * k + e * (1 - k)
                return e
            
            ema12 = ema(prices[-35:], 12)
            ema26 = ema(prices[-35:], 26)
            macd_line = ema12 - ema26
            # Signal: EMA(9) of MACD — approximate with last 9 MACD values
            macd_vals = []
            for i in range(35, len(prices) + 1):
                chunk = prices[max(0, i-35):i]
                if len(chunk) >= 26:
                    e12 = ema(chunk, 12)
                    e26 = ema(chunk, 26)
                    macd_vals.append(e12 - e26)
            if len(macd_vals) >= 9:
                signal_line = ema(macd_vals, 9)
                result['macd_value'] = round(macd_line, 8)
                result['macd_signal'] = round(signal_line, 8)
                result['macd_hist'] = round(macd_line - signal_line, 8)
        
        # Momentum state (5-bar velocity)
        if len(prices) >= 6:
            velocity = (prices[-1] - prices[-6]) / prices[-6] * 100 if prices[-6] else 0
            result['momentum_state'] = (
                'rising' if velocity > 0.1 else
                'falling' if velocity < -0.1 else 'flat'
            )
        
        # Bollinger Band position (20-bar)
        if std > 0:
            upper = mean + 2 * std
            lower = mean - 2 * std
            result['bb_position'] = round((last - lower) / (upper - lower), 4) if upper != lower else 0.5
        
        return result
    except Exception:
        return {}
```

#### Integration in `add_signal()`

After the existing confidence/blacklist checks, before the INSERT:

```python
# ── Auto-enrichment: fill missing indicators from price_history ──
if z_score is None or rsi_14 is None or macd_hist is None:
    enriched = _enrich_indicators(token)
    if z_score is None:
        z_score = enriched.get('z_score')
    if z_score_tier is None:
        z_score_tier = enriched.get('z_score_tier')
    if rsi_14 is None:
        rsi_14 = enriched.get('rsi_14')
    if macd_value is None:
        macd_value = enriched.get('macd_value')
    if macd_signal is None:
        macd_signal = enriched.get('macd_signal')
    if macd_hist is None:
        macd_hist = enriched.get('macd_hist')
    if momentum_state is None:
        momentum_state = enriched.get('momentum_state')
```

#### `signal_metadata` Population

Also populate `signal_metadata` JSONB with the full enriched dict for future-proofing:

```python
metadata = signal_metadata or {}
metadata.update({
    'z_score': z_score, 'z_score_tier': z_score_tier,
    'rsi_14': rsi_14, 'macd_hist': macd_hist,
    'macd_value': macd_value, 'macd_signal': macd_signal,
    'momentum_state': momentum_state, 'bb_position': enriched.get('bb_position'),
    'price_at_signal': price,
})
```

This gets passed to brain.py via `--signal-metadata-json` and stored in `_signal_metadata` column.

#### Performance

- `get_price_history(token, 60)` = one SQLite query, ~1ms
- Computations are pure Python arithmetic on 60 floats, <0.1ms
- Called once per `add_signal()` — ~50-200 calls per pipeline cycle (every 1 min)
- Total overhead: ~0.2s per pipeline run — negligible

#### Fallback

All enrichment is wrapped in try/except. If price_history is unavailable or computation fails, `add_signal()` proceeds with `None` values as before — no regression.

---

### Part B: Backfill 2573 Existing Trades

Script: `scripts/backfill_trade_indicators.py`

#### Approach

For each of the 2573 closed trades:
1. Read `token`, `open_time`, `signal`, `direction` from PostgreSQL
2. Fetch `price_history` for that token up to `open_time` timestamp
3. Compute z_score, RSI, MACD, momentum_state, BB position at that timestamp
4. Fetch ATR(14) from `candles.db` (5m candles) at that timestamp
5. Compute `entry_trend` from 1h price slope
6. UPDATE the PostgreSQL trades row with all computed values

#### Indicators to Backfill

| Column | Computation | Data Source |
|--------|-------------|-------------|
| signal_z_score | 20-bar z-score at open_time | price_history |
| signal_z_score_tier | bucketed z-score | derived |
| signal_rsi_14 | RSI(14) at open_time | price_history |
| signal_macd_value | MACD line | price_history |
| signal_macd_signal | MACD signal line | price_history |
| signal_macd_hist | MACD histogram | derived |
| signal_momentum_state | 5-bar velocity | price_history |
| entry_rsi_14 | same as signal_rsi_14 | price_history |
| entry_macd_hist | same as signal_macd_hist | price_history |
| entry_trend | 1h slope direction | price_history (60 bars) |
| entry_atr_14 | ATR(14) from 5m candles | candles.db candles_5m |
| entry_bb_position | Bollinger position | price_history |
| _signal_metadata | JSON dict of all above | derived |

Not backfilled (no historical data):
- `regime` — needs 15m regime scanner output (not stored historically)
- `entry_slope_4h` — needs 4h candle history (may exist in candles.db but complex)
- `entry_regime_4h` — same
- `entry_fear_greed` — external API, no historical endpoint
- `signal_decision` — was not captured at signal time

#### Script Design

```python
#!/usr/bin/env python3
"""
Backfill trade indicator data for all closed trades.

Reads token + open_time from PostgreSQL, computes indicators from
price_history at that timestamp, updates the trades row.

Usage:
    python3 scripts/backfill_trade_indicators.py           # full backfill
    python3 scripts/backfill_trade_indicators.py --dry     # dry run, no writes
    python3 scripts/backfill_trade_indicators.py --limit 100  # test on first 100
    python3 scripts/backfill_trade_indicators.py --token BTC  # single token
"""
```

Key design decisions:
- Batch PostgreSQL UPDATEs (100 at a time) to avoid locking
- `--dry` flag to preview without writing
- Progress bar / counter every 100 trades
- Skip trades where price_history has < 26 bars at that timestamp (can't compute MACD)
- Set `_signal_metadata` to JSON dict of all computed indicators
- Idempotent: can re-run safely (overwrites with same values)
- `--token` flag to backfill a single token for testing

#### ATR Computation

ATR(14) needs OHLC. Use `candles_5m` from candles.db:

```sql
SELECT open, high, low, close FROM candles_5m
WHERE token = ? AND ts <= ? AND is_closed = 1
ORDER BY ts DESC LIMIT 14
```

ATR = average of True Range over 14 bars, where:
TR = max(high - low, abs(high - prev_close), abs(low - prev_close))

If no 5m candles at that timestamp, skip ATR (set to NULL).

#### entry_trend Computation

From last 60 price_history bars (~1h):
- Linear regression slope of closes
- If slope > 0.05% per bar: `up`
- If slope < -0.05% per bar: `down`
- Else: `flat`

#### Expected Runtime

- 2573 trades × (1 SQLite query + 1 candle query + computation) ~ 2573 × 5ms = ~13s
- PostgreSQL batch UPDATEs: ~5s
- Total: ~20-30 seconds

---

### Part C: Ensure Future Trades Capture All Details

The auto-enrichment in Part A handles the signal side. But `decider_run.py` also needs to capture these values from the hotset and pass them to `brain.py`.

#### Current Flow (with auto-enrichment)

1. Signal module calls `add_signal()` → auto-enrichment fills z_score, RSI, MACD, etc.
2. `signal_compactor.py` queries signals: `MAX(z_score)`, `MAX(z_score_tier)` from signals table → populated in hotset JSON
3. `decider_run.py` reads `sig.get('z_score')` from hotset → passes `--signal-z-score` to `brain.py`
4. `brain.py` stores in PostgreSQL trades table

#### Gaps to Fix

**Gap 1:** `signal_compactor.py` SQL query (line 416-417) uses `MAX(z_score)` and `MAX(z_score_tier)`. With auto-enrichment, these will be populated. But the query doesn't select RSI, MACD, or momentum_state. Add them:

```sql
MAX(rsi_14) AS rsi_14,
MAX(macd_hist) AS macd_hist,
MAX(macd_value) AS macd_value,
MAX(macd_signal) AS macd_signal,
MAX(momentum_state) AS momentum_state,
```

**Gap 2:** Hotset entry dict (line 849-877) doesn't include rsi_14, macd_hist, momentum_state. Add them:

```python
'rsi_14': row[12] if len(row) > 12 else None,
'macd_hist': row[13] if len(row) > 13 else None,
'momentum_state': row[14] if len(row) > 14 else None,
```

**Gap 3:** `decider_run.py` already reads `sig.get('rsi_14')`, `sig.get('macd_hist')`, `sig.get('momentum_state')` (lines 2273-2275) and passes them to `execute_trade()` → `brain.py`. This already works — just needs the upstream data.

**Gap 4:** `entry_rsi_14`, `entry_macd_hist`, `entry_trend` are NOT passed by decider_run to brain.py. These are "entry-time" indicators (computed at actual trade open, not signal time). The auto-enrichment computes them at signal time. For brain.py to store entry-time values, either:
- Option A: Pass `signal_rsi_14` as `entry_rsi_14` too (they're the same for 1m signals)
- Option B: Let brain.py compute entry indicators itself

Option A is simpler and correct for 1m signals (signal time ≈ entry time within 1-2 minutes).

**Gap 5:** `regime` field in hotset is set by signal_compactor from `s.get('regime', 'NEUTRAL')`. This should be passed to brain.py. Currently it's in the hotset but decider_run doesn't pass `--regime` to brain.py. Check if brain.py accepts it.

---

### Part D: Also Enrich from token_speeds

At signal time, `token_speeds` has speed_percentile, wave_phase, price_acceleration, momentum_score. These should also be captured in signal_metadata.

Add to `_enrich_indicators()`:

```python
# From token_speeds (current market state)
try:
    with sqlite3.connect(RUNTIME_DB) as sconn:
        srow = sconn.execute(
            'SELECT speed_percentile, wave_phase, price_acceleration, '
            'momentum_score, is_stale FROM token_speeds WHERE token = ?',
            (token,)
        ).fetchone()
    if srow:
        result['speed_percentile'] = srow[0]
        result['wave_phase'] = srow[1]
        result['price_acceleration'] = srow[2]
        result['momentum_score'] = srow[3]
        result['is_stale'] = bool(srow[4])
except Exception:
    pass
```

This way `signal_metadata` in PostgreSQL contains the full market state at signal time: z-score, RSI, MACD, BB position, speed, phase, acceleration, momentum — everything needed for Phase 2 similar-setup lookup.

---

## Files to Modify

| File | Part | Change |
|------|:----:|--------|
| `signal_schema.py` | A | Add `_enrich_indicators()` helper, call in `add_signal()` |
| `scripts/backfill_trade_indicators.py` | B | New script — backfill 2573 trades |
| `signal_compactor.py` | C | Add rsi_14, macd_hist, momentum_state to SQL query + hotset dict |
| `decider_run.py` | C | Pass entry_rsi_14 = signal_rsi_14 (same value) to brain.py |
| `brain.py` | C | Verify `--entry-rsi-14`, `--entry-macd-hist` args exist; add if missing |

## Implementation Order

| Step | When | What | Verification |
|------|------|------|-------------|
| 1 | Now | Add `_enrich_indicators()` to `signal_schema.py` | Run `add_signal()` in test, verify z_score populated |
| 2 | Now | Update `signal_compactor.py` to include RSI/MACD/momentum in query + hotset | Check hotset.json has rsi_14 field |
| 3 | Now | Run backfill script on 100 trades (`--limit 100 --dry`) | Verify computed values are sensible |
| 4 | Now | Run backfill script on all 2573 trades | Verify PostgreSQL has populated columns |
| 5 | +1h | Verify next pipeline run populates new signals with indicator data | `SELECT signal_z_score FROM signals ORDER BY id DESC LIMIT 5` |
| 6 | +24h | Verify next trade in PostgreSQL has all indicator columns populated | `SELECT * FROM trades ORDER BY open_time DESC LIMIT 1` |
| 7 | +2 weeks | Verify 200+ trades have indicator data | `SELECT COUNT(*) FROM trades WHERE signal_z_score IS NOT NULL AND close_time IS NOT NULL` |

## Risk

- **Part A (auto-enrichment):** LOW — wrapped in try/except, fail-open returns None
- **Part B (backfill):** LOW — read-only computation, batch UPDATEs, --dry flag
- **Part C (compactor/decider):** MEDIUM — changing hotset schema could break consumers. Verify hermes-trades-api.py and any dashboard readers handle new fields gracefully (they use .get() so should be fine)

## Expected Impact

After implementation:
- All 2573 existing trades have indicator data for analysis/backtesting
- All new trades have full indicator data from signal generation through to close
- Phase 2 of hebbian recall (similar setup lookup) can be enabled immediately using backfilled data — don't need to wait 2 weeks for accumulation
- The `similar_setup_lookup()` can query by z_score_tier, rsi_14 band, momentum_state instead of just signal+direction