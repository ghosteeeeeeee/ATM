# HH_HL Bounce-Point Entries — Threshold Fix (2026-05-12)

## Problem: Signals Fire at Bounce Tops, Not Breakouts

**Symptom:** BERA SHORT, COMP LONG, NIL LONG all closed instantly at or near entry.
Price reversed immediately after position opened — classic bounce-point entry.

**Root cause:** `HH_HL_BREAKOUT_THRESHOLD = 0.0005` (0.05%) was too loose.

| Token | Price | 0.05% threshold | 0.15% threshold |
|-------|-------|-----------------|----------------|
| BERA | $0.40 | $0.0002 | $0.0006 |
| COMP | $24.50 | $0.0123 | $0.0368 |
| NIL | $0.059 | $0.00003 | $0.00009 |

A 0.05% move on BERA is micro-noise — it catches the upward micro-spike at the top of the bounce, not a structural breakdown.

## Fix Applied

**hermes_constants.py line 357:**
```python
HH_HL_BREAKOUT_THRESHOLD = 0.0015   # was 0.0005 (0.05%)
# 0.15% = $0.0006 for BERA, $0.0368 for COMP
```

**signals/hh_hl.py line 238, 243:** Uses `HH_HL_BREAKOUT_THRESHOLD` via import. No code change needed — constant updated in hermes_constants.

## Range-Position Filter — Still Permissive

**signals/hh_hl.py lines 254-261** — SHORT blocked if `price > recent_high - atr`:
```python
if direction == 'SHORT':
    recent_high = max(c['high'] for c in candles[-20:])
    if price > recent_high - atr:
        return None  # too close to top of range = bounce territory
```

**Current threshold is 1 ATR** — for BERA (ATR proxy ~$0.000065, range 0.22%), price at 37% up from range bottom was NOT blocked:
```
BERA: high20=0.406740, atr=0.000065, threshold=0.406675
Actual price: 0.406170 → NOT blocked (0.406170 < 0.406675)
```

For tight-range tokens, 1 ATR = nearly the entire range. Consider tightening to 0.5 ATR or adding a percentage-of-range check.

## Constants Must Live in hermes_constants.py

All `HH_HL_*` constants are in `hermes_constants.py` (lines 354-373). Import chain verified:

```python
# hh_hl.py lines 24-32:
from hermes_constants import (
    HH_HL_LOOKBACK, HH_HL_SWING_WINDOW, HH_HL_MIN_SEP,
    HH_HL_BREAKOUT_THRESHOLD, HH_HL_ATR_ENTRY_MIN,
    HH_HL_SL_ATR_MULT, HH_HL_TP_ATR_MULT,
    HH_HL_MAX_HOLD_BARS, HH_HL_MAX_BARS_SINCE, HH_HL_COOLDOWN_MIN,
    HH_HL_CONFIDENCE_FLOOR, HH_HL_CONFIDENCE_CAP,
    HH_HL_BASE_CONFIDENCE, HH_HL_STRUCT_BONUS_MAX,
    HH_HL_BREAKOUT_BONUS_MAX, HH_HL_RECENCY_BONUS_MAX,
    HH_HL_ENABLED,
)
```

Used at:
- Line 76: `window = HH_HL_SWING_WINDOW`
- Line 238, 243: `(breakout_strength / 100) >= HH_HL_BREAKOUT_THRESHOLD`
- Line 267: `bars_since > HH_HL_MAX_BARS_SINCE`
- Line 275-277: struct/break/recency bonus caps

## Diagnostic

```bash
# Check recent hh_hl signals and their breakout strength
cd /root/.hermes/scripts && python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('data/signals_hermes_runtime.db')
c = conn.cursor()
c.execute("""
    SELECT token, direction, source, confidence,
           CAST(SUBSTR(source, 10) AS INTEGER) as bars_since
    FROM signals
    WHERE signal_type LIKE 'hh_hl%'
    AND decision IN ('PENDING','APPROVED','HOTSET')
    AND created_at > datetime('now', '-2 hours')
    ORDER BY created_at DESC
    LIMIT 20
""")
for row in c.fetchall():
    print(row)
conn.close()
EOF

# Check BERA current range vs ATR
cd /root/.hermes/scripts && python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
c.execute("""
    SELECT price FROM price_history
    WHERE token = 'BERA'
    ORDER BY timestamp DESC LIMIT 25
""")
prices = [r[0] for r in c.fetchall()]
candles = list(reversed(prices))
current = candles[-1]
high20 = max(candles[-20:])
low20 = min(candles[-20:])
atr = (high20 - low20) / 14
range_pct = (current - low20) / (high20 - low20) * 100 if high20 != low20 else 50
print(f"BERA: price={current:.6f}, 20-bar range=[{low20:.6f}, {high20:.6f}]")
print(f"ATR={atr:.6f} ({atr/current*100:.3f}%), price at {range_pct:.1f}% of range")
print(f"SHORT blocked if price > {high20 - atr:.6f}? {current > high20 - atr}")
EOF
```