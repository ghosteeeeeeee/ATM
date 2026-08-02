# Plan: Add Volume to Signal Corroboration

## Goal
Add volume as a signal corroboration layer — confirming momentum signals with actual trading volume before execution. Minimum API calls.

## Current State

**What we have:**
- `candles.db` — stores OHLCV from Binance (1m, 15m, 1h, 4h). Has volume column in all tables.
- `price_collector.py` (cron: every minute) — fetches Binance candles and stores to `candles.db`. Seeds universe 50 tokens/run.
- `allMids` (HL, every minute) — price only, NO volume.

**Problem: candles.db is stale**
- `candles_1m` table: last row = April 6, 2026 (stale)
- `candles_15m/1h/4h`: mostly fresh (rows from today)
- Only 6 tokens in the `tokens` tracking table
- The 1m feed that `macd_rules.py` reads from is not being updated

**What `macd_rules.py` does today:**
```
macd_rules.py line 882: reads from local candles.db first (zero API calls)
 Falls back to Binance API if local DB has no data
```

So the infrastructure is already there — the problem is the 1m candle feed died.

---

## Option A: Fix Binance 1m Candle Feed (RECOMMENDED)

**API cost:** 1 Binance API call per signal corroboration check
**Effort:** Low
**Latency:** Live (real-time from Binance)

Binance is unlimited free for klines. We already have the code in `candle_db.py`. We just need to:

1. **Fix the 1m candle seed** — currently `price_collector` seeds 50 tokens/run across all TFs but 1m is skipped somehow
2. **Add a lightweight volume check** to `macd_rules.py` or a new `volume_check()` function that:
   - Fetches the latest 1m candle from Binance (or reads from candles.db if fresh)
   - Compares current volume vs the 20-period moving average volume
   - Returns `volume_surge = current_volume > avg_volume * threshold`

**Binance endpoint (free, no rate limit):**
```
GET https://api.binance.com/api/v3/klines?symbol={TOKEN}USDT&interval=1m&limit=1
```
Returns the most recent 1m candle. 1 call per token.

**Code change:** A new helper in `macd_rules.py` or a standalone `volume_filter.py`:

```python
def check_volume_surge(token: str, threshold: float = 2.0, lookback: int = 20) -> dict:
    """
    Returns {'surge': bool, 'ratio': float, 'current_vol': float, 'avg_vol': float}
    Binance 1m klines — free, no rate limit.
    """
    url = f"https://api.binance.com/api/v3/klines?symbol={token}USDT&interval=1m&limit={lookback+1}"
    resp = requests.get(url, timeout=5)
    vols = [float(k[5]) for k in resp.json()]
    current_vol = vols[0]
    avg_vol = sum(vols[1:]) / len(vols[1:])
    return {
        'surge': current_vol > avg_vol * threshold,
        'ratio': current_vol / avg_vol if avg_vol > 0 else 0,
        'current_vol': current_vol,
        'avg_vol': avg_vol
    }
```

**Corroboration logic (in signal_schema.py or macd_rules.py):**
```
IF volume_surge AND momentum_signal:
    confidence += 10  # volume confirms momentum
ELIF NOT volume_surge AND momentum_signal:
    confidence -= 5   # momentum unsupported by volume — flag
```

---

## Option B: Use Hyperliquid candleSnapshot

**API cost:** 1 HL API call per token per timeframe. HL rate limits apply (~120 req/min).
**Effort:** Medium
**Advantage:** Volume directly from the exchange where we trade

**Problem:** HL rate limits are tight. Polling candleSnapshot for all hotset tokens every minute would burn through the rate limit fast.

**Better use:** Only call `candleSnapshot` when a signal fires — not on every cycle. One HL API call per signal to get the 1m volume confirmation.

```
POST https://api.hyperliquid.xyz/info
{"type": "candleSnapshot", "req": {"coin": "BTC", "interval": "1m", "num": 20}}
Returns: [[time, open, high, low, close, volume], ...]
```

---

## Option C: Hybrid (RECOMMENDED IMPLEMENTATION)

**Do Binance for routine checks, HL for final confirmation on high-conviction signals.**

1. **Routine (every pipeline minute):** Binance 1m candle for volume spike check — free, unlimited
2. **On signal fire (high confidence):** HL `candleSnapshot` for on-exchange volume confirmation — 1 call per signal

---

## Recommended Approach: Option A + C

### Step 1: Fix the 1m candle feed in price_collector.py
The 1m candles stopped being seeded. Find why and fix it. Likely the `_seed_universe_candles` loop only hits tokens that have stale 4h data, and most tokens already have fresh 4h from prior runs.

### Step 2: Add volume corroboration to signal generation
In `signal_schema.py` `add_signal()` or `macd_rules.py`, add a volume filter:

**File: `volume_filter.py`** (new file in `/root/.hermes/scripts/`)

**Corroboration threshold ideas:**
- Volume ratio > 2.0x 20-bar average = surge (high confirmation)
- Volume ratio > 1.5x = moderate confirmation
- Volume ratio < 0.5x = divergence (reduce confidence or skip)

### Step 3: Wire into signal scoring
Add volume score component to `signal_scoring.py` or `macd_rules.py`. Integrate with existing confidence scoring.

---

## Step-by-Step Plan

### Step 1: Diagnose why candles_1m stopped updating
- [ ] Check `price_collector.py` logic — is `_seed_universe_candles` actually writing to `candles_1m`?
- [ ] Check `CANDLE_TOKENS_FILE` (`/root/.hermes/data/candle_universe_tokens.json`) — is cursor advancing?
- [ ] Check logs: `grep -a "candle" /root/.hermes/logs/pipeline.log | tail -20`
- [ ] Fix: ensure 1m candles are written when `intervals = {'1h': 500, '4h': 200, '15m': 500}` is fetched

### Step 2: Create volume_filter.py
- [ ] `check_volume_surge(token, threshold=2.0, lookback=20)` using Binance 1m klines
- [ ] `get_relative_volume(token, lookback=20)` — returns current/avg ratio
- [ ] `volume_confirms_signal(token, direction)` — returns +conf, 0, or -conf

### Step 3: Wire into macd_rules.py
- [ ] In `macd_rules.py`, call volume check before returning a signal
- [ ] If volume contradicts (price up but volume below avg), reduce confidence or skip
- [ ] Document: volume corroboration can veto a signal

### Step 4: Test on recent signals
- [ ] Backtest: run `macd_rules.py` with volume filter on last 100 signals
- [ ] Compare: signals with volume confirmation vs without — which performed better?
- [ ] Tune threshold (start at 2.0x, test 1.5x and 3.0x)

### Step 5: Add to production pipeline
- [ ] Once validated, add volume check to the pipeline cron
- [ ] Log volume ratio in signal record (add `volume_ratio` column to signals DB if useful)

---

## Files Likely to Change

| File | Change |
|------|--------|
| `/root/.hermes/scripts/price_collector.py` | Fix 1m candle seed logic |
| `/root/.hermes/scripts/macd_rules.py` | Add volume filter to signal generation |
| `/root/.hermes/scripts/signal_schema.py` | Optional: add volume to signal record |
| `/root/.hermes/scripts/hermes_constants.py` | Add `VOLUME_SURGE_THRESHOLD`, `VOLUME_LOOKBACK` |
| **NEW**: `/root/.hermes/scripts/volume_filter.py` | Volume corroboration functions |

---

## API Call Cost

| Approach | Per Pipeline Cycle | Per Signal Fire |
|----------|-------------------|-----------------|
| Binance 1m (Option A) | 0 (read from candles.db if fresh) | 0-1 (local DB read or 1 Binance call) |
| HL candleSnapshot (Option B) | 0 | 1 HL API call |
| Hybrid (Option C) | 0 | 1 Binance call routine / 1 HL call on fire |

**Bottom line:** Binance 1m is free and unlimited. The main cost is fixing the stale feed and adding the corroboration logic.

---

## Risks & Tradeoffs

1. **Binance volume ≠ HL volume** — Binance is more liquid than HL perp. Volume surges on Binance may not translate 1:1. Use as a soft confirmation, not a hard filter.
2. **1m candles are noisy** — Volume spikes can be whipsaws. Consider using 15m or 1h volume for better signal-to-noise.
3. **Stale feed** — Need to confirm `candles_1m` actually gets written to. If the root cause is a logic bug, fix it first before relying on it.
4. **Corroboration vs veto** — Decide: does low volume kill the signal or just reduce confidence? Recommend: reduce confidence (-10), don't veto entirely.

---

## Open Questions

1. Should volume check use Binance (off-chain, higher volume) or HL candleSnapshot (on-exchange, less volume but directly relevant)?
2. Should we use 1m, 15m, or 1h candles for the volume average? (1m = noisy, 1h = slow)
3. Does this run on every pipeline cycle or only when a signal fires?
4. Should we backtest this before production? Recommend: yes, 100-signal backtest comparing volume-confirmed vs non-volume-confirmed outcomes.
