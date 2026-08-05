# Bug #16: Stale Price Data Causes Counter-Trend Signal Entries (2026-05-13)

## Symptom

15 losing LONG trades in 6 hours (08:30-14:30 UTC). All had confidence 77-98%, all labeled "bullish" by the system. All entries lost money.

Post-mortem: Every analyzed trade entered with price **BELOW EMA300** by -1.4% to -4.4%. The accel-300 signal was supposed to fire when price accelerates ABOVE EMA300 — instead it fired on the way down.

ATOM SHORT is the worst case: system fired SHORT in a 4h UP trend (4h EMA20 > EMA50), costing money immediately.

## Root Cause

Signal scripts (notably `accel_300.py`) read price data from `signals_hermes.db` → `price_history` table, which ends **March 2026** — stale by ~2 months.

Live prices are in `candles.db` → `candles_1m` (fresh, ~2 min old).

The EMA(300) calculation on stale data produces wrong values → signal fires at wrong time.

## All 9 Analyzed Trades: Counter-Trend Entries

| Token | Dir | Entry Price | EMA300 | Gap% | 4h Trend | Counter-Trend? |
|-------|-----|------------|--------|------|----------|---------------|
| NEAR | LONG | 1.5786 | 1.6013 | -1.4% | UP | ❌ YES |
| BRETT | LONG | 0.00974 | 0.01012 | -3.8% | UP | ❌ YES |
| BERA | LONG | 0.4036 | 0.4109 | -1.8% | UP | ❌ YES |
| ONDO | LONG | 0.3862 | 0.3955 | -2.3% | UP | ❌ YES |
| LINEA | LONG | 0.00391 | 0.00398 | -1.7% | UP | ❌ YES |
| S | LONG | 0.04963 | 0.05083 | -2.4% | UP | ❌ YES |
| GRIFFAIN | SHORT | 0.01176 | 0.01230 | -4.4% | DOWN | ✅ aligned |
| ATOM | SHORT | 2.0761 | 2.1107 | -1.6% | **UP** | ❌❌ YES |
| MERL | SHORT | 0.03546 | 0.03635 | -2.4% | DOWN | ✅ aligned |

8 of 9 trades were counter-trend. Only 2 (GRIFFAIN SHORT, MERL SHORT) were aligned with the 4h trend.

## The Two Bugs

### Bug A: Wrong Data Source

Signal scripts import from `hermes_db` or `paths` and call `get_price_history()` → reads stale `price_history` table.

```python
# WRONG — stale source:
from hermes_db import get_price_history
prices = get_price_history(token)  # ends March 2026!

# CORRECT — live source:
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/candles.db')
c.execute("SELECT close FROM candles_1m WHERE token=? ORDER BY ts DESC LIMIT 500", (token,))
closes = [r[0] for r in c.fetchall()]
```

### Bug B: No 4h Trend Filter

signal_compactor.py has NO check against 4h EMA20/EMA50 trend before approving a signal. A token with bullish 1m momentum but bearish 4h trend passes through all gates and gets executed.

**Fix:** Add a hard block in signal_compactor or decider_run:
- Block LONG if 4h EMA20 < EMA50 (4h downtrend)
- Block SHORT if 4h EMA20 > EMA50 (4h uptrend)

## Data Freshness Verification

```bash
# Check price_history (stale — do NOT use for live signals)
sqlite3 /root/.hermes/data/signals_hermes.db \
  "SELECT MAX(timestamp), COUNT(*) FROM price_history WHERE token='NEAR'"
# Result: max_ts=1773864000 (2026-03-18), entries=56,079

# Check candles_1m (live — USE THIS)
sqlite3 /root/.hermes/data/candles.db \
  "SELECT MAX(ts), COUNT(*) FROM candles_1m WHERE token='NEAR'"
# Result: max_ts ~ current time (within minutes)
```

## Fix Priority

1. **Immediate**: Add EMA300 proximity filter — entry price must be within +1.5% of EMA300 for LONG, -1.5% for SHORT (prevents counter-trend entries at extreme)
2. **High**: Add 4h trend filter in signal_compactor — block trades against 4h EMA20/EMA50 direction
3. **High**: Audit ALL signal scripts to use `candles.db` instead of `price_history` for live price/EMA data

## Detection Script

```python
import sqlite3

def check_ema_position(token):
    conn = sqlite3.connect('/root/.hermes/data/candles.db')
    c = conn.cursor()
    c.execute("SELECT close FROM candles_1m WHERE token=? ORDER BY ts DESC LIMIT 300",
              (token,))
    rows = c.fetchall()
    closes = [r[0] for r in reversed(rows)]
    if len(closes) < 300:
        return None
    ema = sum(closes[:300]) / 300
    k = 2 / (301)
    for c_ in closes[300:]:
        ema = c_ * k + ema * (1 - k)
    latest = closes[-1]
    gap = (latest / ema - 1) * 100
    return {'ema300': ema, 'latest': latest, 'gap_pct': gap}

def check_4h_trend(token):
    conn = sqlite3.connect('/root/.hermes/data/candles.db')
    c = conn.cursor()
    c.execute("SELECT close FROM candles_4h WHERE token=? ORDER BY ts DESC LIMIT 50",
              (token,))
    rows = c.fetchall()
    closes = [r[0] for r in reversed(rows)]
    if len(closes) < 50:
        return None
    ema20 = sum(closes[-20:]) / 20
    ema50 = sum(closes[-50:]) / 50
    trend = "UP" if ema20 > ema50 else "DOWN"
    return {'trend': trend, 'ema20': ema20, 'ema50': ema50}
```