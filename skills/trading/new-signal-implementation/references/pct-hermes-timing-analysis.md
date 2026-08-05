# pct-hermes Timing Analysis — Signal Entry Quality Debug

## The Problem

`pct-hermes+` (LONG when pct_short >= 72%) fires at the **top** of a session move, not the bottom. The signal interprets elevated percentile rank as "suppressed price → bounce incoming," but elevated percentile actually means "price near session highs → likely to mean-revert DOWN."

## Diagnostic Technique — Session Timing Analysis

When a trade loses, determine WHERE in the session range the entry occurred:

```python
import sqlite3, datetime

STATIC_DB = '/root/.hermes/data/signals_hermes.db'  # price_history
TRADES_FILE = '/var/www/hermes/data/trades.json'

conn = sqlite3.connect(STATIC_DB)
cur = conn.cursor()

# For each losing trade, compute entry's position in session range
for trade in losing_trades:
    coin = trade['coin']
    entry_price = trade['entry']
    entry_ts = int(datetime.datetime.strptime(
        trade['opened'], '%Y-%m-%d %H:%M:%S.%f').timestamp())

    # Get last 20 candles before entry (session range proxy)
    cur.execute('''
        SELECT price FROM price_history
        WHERE token=? AND timestamp < ?
        ORDER BY timestamp DESC LIMIT 20
    ''', (coin, entry_ts))
    recent = [r[0] for r in cur.fetchall()]
    recent.reverse()

    if len(recent) < 5:
        continue

    session_low = min(recent)
    session_high = max(recent)
    range_pct = (entry_price - session_low) / (session_high - session_low + 1e-10) * 100

    # 0% = bottom of session, 100% = top of session
    # pct-hermes+ should only fire < 40%, not > 60%
    print(f"{coin}: entry at {range_pct:.0f}% of session range "
          f"(low={session_low:.5f}, high={session_high:.5f})")
```

## Key Finding (May 4 2026)

| Coin | Entry Position | Expected | Result |
|------|---------------|----------|--------|
| ONDO | ~90% of session range | < 40% | Lost |
| LINEA | ~85% | < 40% | Lost |
| ICP | ~80% | < 40% | Lost |
| ZK | ~90% | < 40% | Lost |

## Root Cause in pct-hermes Logic

```python
# signal_gen.py ~line 1685
elif pct_short >= PCT_RANK_THRESH:  # 72%
    pct_signal_dir = 'LONG'  # WRONG: pct_short HIGH = price elevated = top of range
```

`pct_short` = % of bars ABOVE current price. When pct_short >= 72%:
- 72%+ of history was ABOVE current price
- Current price is at the BOTTOM of the historical range
- This IS actually suppressed = good LONG entry

Wait — re-read the ONDO data:

```
ONDO: pct_short=67.1% at entry (below 72%)
BUT signal was pct-hermes+,rs-s11,rs-s9
```

The signal had ALREADY fired earlier when pct_short WAS >= 72%. The entry happened later (filled via hot-set). By the time the guardian executed the trade, pct_short had already dropped below 72%.

**This means the signal AGED BADLY.** The pct-hermes+ signal persisted in the hot-set for minutes after pct_short fell below threshold, and was filled at a much worse price.

## Two Failure Modes

### Failure Mode 1: Entry at local peak (signal correct, filled late)
Signal fires when pct_short >= 72% → price bounces → guardian fills at higher price → price mean-reverts immediately after fill.

### Failure Mode 2: Stale signal (pct drops below threshold but signal still in hot-set)
Signal fires at pct_short=78% → pct_short falls to 67% → signal persists in hot-set → filled at bad entry.

## The Fix Direction

1. **Block `pct-hermes+` if price within 0.5% of session high** (last 20 candles)
2. **Reduce signal TTL** from 30 min to 5 min — stale signals are the bigger problem
3. **Re-check pct_short at fill time** (in guardian) — don't fill if pct_short < 72%
4. **Flip direction**: pct_short >= 72% = price suppressed = genuinely good LONG entry (current logic is correct per this interpretation — the issue is timing/ageing)

## Computing pct_short Correctly

```python
def compute_pct_short(prices, window=200):
    """% of bars in window with price >= current price."""
    lookback = prices[-window:] if len(prices) >= window else prices
    current = lookback[-1]
    n_above = sum(1 for p in lookback if p >= current)
    return round((n_above / len(lookback)) * 100, 1)

# In signal_gen.py compute_zscore_percentile():
# pct_short = round((price_above / len(lookback)) * 100, 1)
# where price_above = sum(1 for p in lookback if p >= current_price)
```

Key: `pct_short >= 72` means price is at the BOTTOM (suppressed), not top. The logic is directionally correct — the problem is signal ageing and entry timing.
