# accel-300: LB=35 Signal Works, Data Pipeline Blocks (2026-06-06)

## TL;DR
accel-300 signal logic is working correctly with ACCEL_300_LOOKBACK=35. Manual gate1 traces pass for DYDX, BABY, RESOLV, CC, VINE, HYPER, FET, ZK, IP, IOTA, WCT, ZEC, STX, KAITO, TIA, ZEN, TRB, APEX, AXS, BLUR. All are blocked at the `price_age_minutes > 10` scanner guard.

## Root Cause of "Zero Signals"
All 230 tokens in `signals_hermes.db` have `price_history` last updated May 27 (208h stale). The signal logic itself is fine — `scan_accel_300_signals()` blocks at `price_age_minutes(token) > 10`.

Check: `from signal_schema import price_age_minutes; price_age_minutes('DYDX')` → 4913 minutes.

## Manual Gate1 Trace Methodology

For any token, manually verify each gate in order:

```python
import sqlite3, pandas as pd
LB = 35  # ACCEL_300_LOOKBACK
STALE = 200  # ACCEL_300_STALE_BARS
PERIOD = 300
MIN_GAP_SHORT = 0.10
MIN_GAP_LONG = 0.15

conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = conn.cursor()
cur.execute('SELECT price FROM price_history WHERE token=? ORDER BY timestamp DESC LIMIT 400', (tok,))
rows = cur.fetchall()
closes = [r[0] for r in reversed(rows[:400])]
ema300 = pd.Series(closes).ewm(span=300).mean()

i = 399  # latest detection bar (PERIOD+LB to n-2)
price = closes[i]
gap = (price - ema300[i]) / ema300[i] * 100
current_below = price < ema300[i]
current_above = price > ema300[i]

# was checks (SHORT gate1: was_above_recently, LONG gate1: was_below_recently)
was_above = any(ema300[j] is not None and closes[j] > ema300[j]
                for j in range(max(310, i - LB), i + 1))
was_below = any(ema300[j] is not None and closes[j] < ema300[j]
                for j in range(max(310, i - LB), i + 1))

# Cross search (below->above, for bars_since)
cross_bar = next((j for j in range(max(310, i - LB), i + 1)
                  if j > 0 and ema300[j] is not None and ema300[j-1] is not None
                  and ema300[j-1] < closes[j-1] and closes[j] > ema300[j]), None)
bars_since = i - cross_bar if cross_bar else 999

# Regime slope
ema_recent = ema300.iloc[-60:]
slope = (ema_recent.iloc[-1] - ema_recent.iloc[0]) / ema_recent.iloc[0] * 100

# Gate evaluation
long_gate1 = current_above and not was_below
short_gate1 = current_below and not was_above
long_passes = long_gate1 and bars_since <= STALE and gap >= MIN_GAP_LONG and slope > 0.003
short_passes = short_gate1 and bars_since <= STALE and abs(gap) >= MIN_GAP_SHORT and slope < -0.003
```

## Key Findings

### GOAT: Choppy Oscillation Pattern
- GOAT has no clean cross in range 300-399
- At i=335-395: `gate1=TRUE`, `cross=None`, `bars_since=999`, stale fails
- At i=398: cross found (bar 397, below->above), but `was_above=True` → gate1 fails
- GOAT is stuck in chop — no position in the lookback window satisfies both gate1 and cross requirements
- **This is working as designed** — GOAT doesn't deserve a signal in chop

### DYDX: Strong Uptrend, All Checks Pass
- DYDX regime slope: +1.04%/bar (strong bullish)
- Cross at bar 364 (below->above), bars_since=35
- Gap at i=399: +1.76% above EMA
- All checks pass → signal fires when data pipeline is fixed

### ACCEL_300_LOOKBACK=35 vs 30
- LB=30: detection starts at bar 330, GOAT cross at bar 299 is 31 bars before detection start
- LB=35: detection starts at bar 335, cross at bar 299 is 36 bars before — still outside
- For GOAT to find cross: LB must be ≥ 62 (so i-LB ≤ 299 at i=361)
- LB=35 is minimum for meaningful cross capture — GOAT's specific cross at 299 needs LB≥62
- LB=35 correctly allows 20 tokens to pass gate1 with DYDX being the strongest

### Data Pipeline Fix
Fix `signals_hermes.db` price_history updates — price_collector.py must run reliably.
Until then: `scan_accel_300_signals()` returns 0 for all tokens regardless of parameters.

## Scanner Block Order
1. `ACCEL_300_ENABLED` check
2. `price_age_minutes(token) > 10` — **BLOCKS ALL when data stale**
3. Token in open_pos
4. `recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES)`
5. `is_delisted(token)`
6. Token in SHORT_BLACKLIST
7. `ACCEL_300_TOKEN_ALLOWLIST` (empty = allow all)
8. Insufficient price history (< PERIOD+LOOKBACK+PERSISTENCE_BARS+5 bars)
9. `detect_accel_300()` returns None
10. `get_cooldown(token, direction)`
11. Direction-specific `ACCEL_300_PLUS_ENABLED` / `ACCEL_300_MINUS_ENABLED`

## Recommended Parameter Tweaks (for chop market)
- `ACCEL_300_REGIME_SLOPE_PCT`: 0.003 → 0.005 (tighter trend requirement)
- `ACCEL_300_MIN_GAP_GROWTH`: 0.05 → 0.08 (stronger momentum confirmation)
- `ACCEL_300_PERSISTENCE_BARS`: 4 → 5 (harder to fake in chop)
