# scan_zscore_rising_signals() Per-Bar Iteration Pitfall

## The Bug

Original code computed z-score **once** for the entire price array:

```python
z_cur = compute_zscore(closes, LB)     # uses closes[-LB:] — last LB bars of array
z_prev = compute_zscore(closes[:-1], LB) # uses closes[:-1][-LB:] — last LB bars excluding last element
```

For oldest-first data (oldest at index 0, newest at index N-1):
- `closes[-LB:]` = bars N-LB through N-1 (the **end** of the series)
- `closes[:-1][-LB:]` = bars N-LB through N-2 (end minus one)

**Problem 1 — Pump in the middle is invisible:** If a pump happens at bar 462 in a 600-bar window, both `z_cur` and `z_prev` are computed over bars 580-599 (the last 20 bars). The pump at bar 462 is never examined.

**Problem 2 — z_prev window is wrong for oldest-first data:** `closes[:-1]` removes the **last** element (newest price). For oldest-first data, the newest price is at the END of the array. `closes[:-1][-LB:]` gives bars N-LB-1 through N-2 — one bar older than `z_cur`'s window, but NOT the window immediately preceding it. The correct `z_prev` for bar i should use `closes[:i][-LB:]` (window ending at i-1).

**Problem 3 — Cross detection only happens once:** Even if `z_prev < TH <= z_cur` happens to be true for the end-of-series snapshot, the signal fires at most once. Real pumps cross the threshold at specific bars — you need to check EACH bar.

## The Fix

Per-bar iteration: for each bar `i` from `LB` to `len(closes)-1`:

```python
for i in range(LB, len(closes)):
    # z_curr: window ending at i (closes[0..i])
    z_curr = compute_zscore(closes[:i+1], LB)
    # z_prev: window ending at i-1 (closes[0..i-1])
    z_prev = compute_zscore(closes[:i], LB) if i >= LB else None
    # z_past: window ending at i-VEL_BARS (closes[0..i+1-VEL_BARS])
    z_past_win = closes[:i+1-VEL_BARS]
    z_past = compute_zscore(z_past_win, LB) if len(z_past_win) >= LB else None
    z_vel = (z_curr - z_past) if z_past is not None else 0.0

    # Now check crossing at THIS bar
    if z_prev < TH <= z_curr and z_vel > 0:
        # FIRE LONG at bar i
```

## Why DB Data Is Descending

`price_history` query with `ORDER BY timestamp DESC` returns newest-first. Most z-score algorithms expect oldest-first (chronological). The scan function must `reversed()` the data:

```python
# DB returns newest-first (DESC) — scan expects oldest-first (ASC)
for token, prices in token_prices.items():
    prices_dict[token] = list(reversed(prices[:200]))
```

## Verified Results

| Token | Old logic | New logic |
|-------|-----------|-----------|
| XLM (200 bars) | 0 fires | 3 LONG fires |
| SNX (600 bars) | 0 fires | 14 fires (7 LONG, 7 SHORT) |
| Kill-switch test (PLUS=False) | 0 fires | 0 fires ✓ |

## Detection Pattern

To find other signals with this same bug, look for:

```bash
# Single compute_zscore call over full array — wrong for sliding window signals
grep -n "compute_zscore(closes[,)]" /root/.hermes/scripts/signals/*.py

# Correct pattern: compute_zscore should only appear INSIDE the bar-iteration loop,
# operating on a slice that ends at the current bar.
```

## Related

- `zscore_rising.py` — standalone signal that required this fix
- `compute_zscore(values, LB)` — uses `values[-LB:]` internally, so passing `closes[:i+1]` gives window ending at bar i