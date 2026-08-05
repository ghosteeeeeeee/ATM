# RS Signal Collapse — Root Cause Analysis (2026-05-28)

## Symptoms
signals/rs.py producing ~0 signals for 92 non-blacklisted fresh tokens. Previously ~15K/day.

## Root Causes

### 1. price_collector stopped writing price_history (primary)
- Lock file `/root/.hermes/data/price_collector.lock` exists and appears held (process running at 99.6% CPU)
- But price_history stopped updating at `04:17:28` (ts=1779941848) — over an hour before diagnosis
- 92 tokens have fresh (<2min) price_history, 138 tokens are stale
- signals/rs.py has 120s freshness guard at `_get_candles_1m()` line 614 — stale tokens get skipped entirely
- All 138 stale tokens print: `[rs] {TOKEN}: stale price_history (last ts 1779941848, skipping)`

### 2. RS_PROXIMITY_K tightened from 1.20 → 0.70 ATRs
- Old `rs_signals.py`: `RS_PROXIMITY_K = 1.20` (40% wider band)
- New `signals/rs.py`: `RS_PROXIMITY_K = 0.70` — price must be within 0.70 ATRs of level
- For low-ATR tokens (e.g., W at 0.034% ATR), the band is tiny: 0.024% vs 0.041% before

### 3. Bounce confirmation always False on close-only candles
- `price_history` is close-only: open=high=low=close for every row
- `_bounce_confirmation()` checks `c['close'] > c['open']` for condition (a) — always False since they're equal
- Falls back to condition (b) requiring >0.025% follow-through candle after touch
- Result: `bounce=False` on every signal — confidence penalized but not blocked entirely

### 4. Regime filtering (secondary)
- `_get_regime_5m()` reads from `regime_5m.json`
- Tokens not in regime file get `('NEUTRAL', 0)` — no penalty since conf=0
- Counter-regime signals get 20% haircut only if regime_conf > 50 — mostly not triggered

## Key Files
- `signals/rs.py` — new canonical RS signal (replaced `rs_signals.py` 2026-05-06)
- `rs_signals.py` — old RS signal (had wider proximity, no bounce check, no regime)
- `price_collector.py` — writes price_history and latest_prices
- `signals/__init__.py` — `run_all_signals()` dispatches via `_run_signal(sig_name, fn_name)` 
- `_PRICE_DB = /root/.hermes/data/signals_hermes.db`

## Diagnostic Commands
```bash
# Check price_history freshness
python3 -c "
import sqlite3, time
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
now = int(time.time())
c.execute('SELECT token, MAX(timestamp), MAX(timestamp) FROM price_history GROUP BY token')
all_rows = c.fetchall()
fresh = [(t, ts) for t, ts, _ in all_rows if (now - ts) < 120]
stale = [(t, ts) for t, ts, _ in all_rows if (now - ts) >= 120]
print(f'Fresh: {len(fresh)}, Stale: {len(stale)}')
for t, ts in stale[:5]:
    print(f'  STALE: {t} age={now-ts}s')
"

# Test rs signal directly on fresh tokens
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from signals.rs import _get_candles_1m, detect_rs_signal
from signal_schema import get_all_latest_prices
import sqlite3, time
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor(); now = int(time.time())
c.execute('SELECT token, MAX(timestamp) FROM price_history GROUP BY token')
fresh_tokens = {tok for tok, ts in c.fetchall() if (now - ts) < 120}
conn.close()
prices = get_all_latest_prices()
fresh_prices = {tok: d for tok, d in prices.items() if tok in fresh_tokens}
results = []
for tok in sorted(fresh_tokens):
    candles = _get_candles_1m(tok)
    if not candles: continue
    price = fresh_prices.get(tok, {}).get('price')
    if not price: continue
    result = detect_rs_signal(tok, candles, price)
    if result:
        results.append((tok, result['direction'], result['confidence']))
for tok, d, c in results:
    print(f'{tok}: {d} conf={c:.0f}%')
print(f'Total: {len(results)} signals from {len(fresh_tokens)} fresh tokens')
"
```

## Fix Priority
1. **Restart price_collector** — primary cause; 138 tokens completely missing
2. **Restore RS_PROXIMITY_K to 1.20** — widened the valid signal band significantly
3. **Fix bounce confirmation** — use fixed 0.15% threshold instead of ATR-based for close-only candles