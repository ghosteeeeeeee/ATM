# accel-300 Debug Procedure

Systematic verification when `accel-300` signal issues are reported.

## Step 1 — Verify EMA Calculation

The signal depends on EMA(300) being correct. Always verify first.

```python
import pandas as pd
sys.path.insert(0, '/root/.hermes/scripts')
from signals.accel_300 import _ema_series, _get_1m_prices

prices = _get_1m_prices(token, lookback=720)
closes = [p['price'] for p in prices]

ema_code = _ema_series(closes, 300)
s = pd.Series(closes)
ema_pd = s.ewm(span=300, adjust=False).mean()

# Compare last 3 values
for i in [-3, -2, -1]:
    print(f"i={i}: code={ema_code[i]:.4f} pandas={ema_pd.iloc[i]:.4f} diff={abs(ema_code[i]-ema_pd.iloc[i]):.4f}")
```

**Known difference:** Code uses `SMA(first 300)` as seed; pandas uses `price[0]`. This causes ~0.4 BTC absolute drift but only ~0.0005% gap difference — negligible for direction detection.

If EMA is wrong: check `_ema_series()` function, verify period=300, k=2/(period+1).

## Step 2 — Verify Signal Detection

Run detection directly on the token:

```python
from signals.accel_300 import detect_accel_300, _ema_series

prices = _get_1m_prices(token, 700)
sig = detect_accel_300(token, prices)
if sig:
    print(f"DIRECTION={sig['direction']} gap={sig['gap_pct']:.4f}% growth={sig['gap_growth']:.4f}% bars={sig['bars_since_cross']}")
else:
    # Trace why it was rejected
    closes = [p['price'] for p in prices]
    ema = _ema_series(closes, 300)
    gap_pcts = [(closes[i]-ema[i])/ema[i]*100 for i in range(len(closes))]
    print(f"Last gap: {gap_pcts[-1]:.4f}% (MIN_GAP_PCT=0.20)")
    print(f"Last close vs EMA: {closes[-1]:.6f} vs {ema[-1]:.4f}")
```

## Step 3 — Check DB Signals

```python
import sqlite3, datetime
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()
c.execute("""
    SELECT id, token, direction, signal_type, source, confidence, created_at
    FROM signals WHERE source IN ('accel-300+', 'accel-300-')
    ORDER BY created_at DESC LIMIT 10
""")
for r in c.fetchall():
    print(f"id={r[0]} {r[1]} {r[2]} conf={r[5]} at={r[6]}")
conn.close()
```

## Step 4 — Check Hotset

```bash
cat /var/www/hermes/data/hotset.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
for e in d['hotset']:
    if 'accel' in e.get('source',''):
        print(f\"token={e['token']} dir={e['direction']} conf={e['confidence']:.1f} score={e['final_score']:.1f}\")
"
```

## Step 5 — Check hermes_constants Kill Switches

```python
from hermes_constants import ACCEL_300_ENABLED, ACCEL_300_PLUS_ENABLED, ACCEL_300_MINUS_ENABLED, ACCEL_300_TOKEN_ALLOWLIST
print(f"ACCEL_300_ENABLED={ACCEL_300_ENABLED}")
print(f"PLUS={ACCEL_300_PLUS_ENABLED} MINUS={ACCEL_300_MINUS_ENABLED}")
print(f"ALLOWLIST={ACCEL_300_TOKEN_ALLOWLIST} (empty=allow all)")
```

## Common Failure Modes

| Failure | Symptom | Check |
|---------|---------|-------|
| abs() missing on gap check | SHORT never fires, gap_pct negative always rejected | Line 224: `abs(gap_now) < MIN_GAP_PCT` |
| Sign inverted for SHORT | Fires on bounces, not accelerations | Line 255: `gap_then - gap_now` for SHORT |
| Patch accident deleted gap_then | NameError crash on all tokens | Verify `gap_then = gap_pcts[gap_then_idx]` present |
| EMA seed mismatch | Gap values slightly off but rarely direction-changing | Compare with pandas ewm |
| Cooldown active | Token shows no signal despite valid conditions | Check cooldown in DB |
| Token in open position | Scanner skips tokens with open pos | `position_manager.get_open_positions` |
| Price stale (>5min) | No signal, prices skipped | `_get_1m_prices` freshness guard |

## Confidence Calculation

```python
# From scan_accel_300_signals (lines ~393-398)
gap_bonus = max(0, sig['gap_growth'] - 0.05) * 200  # need >0.05% growth for bonus
confidence = int(min(70, 65 + max(0, (sig['gap_pct'] - MIN_GAP_PCT) * 80) + gap_bonus))
confidence = max(60, confidence)
# MIN_GAP_PCT=0.20, so base=65, cap=70
```

If confidence seems wrong, compute manually from gap_pct and gap_growth values.

## Debugging bars_since_cross

If signal fires but bars_since_cross is unexpectedly high/low:

```python
# The cross_bar search scans i-LOOKBACK to i looking for:
# LONG: closes[j] > ema300[j] AND closes[j-1] <= ema300[j-1]
# SHORT: closes[j] < ema300[j] AND closes[j-1] >= ema300[j-1]
# bars_since_cross = i - cross_bar
# bars_since_cross < 1: rejected (must have at least 1 bar after cross)
# bars_since_cross > 10: rejected (stale)
```