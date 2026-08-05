# Signal Extraction Pattern

How to extract an inline signal from `signal_gen.py` into a standalone `signals/{name}.py` file.

## When to Extract

Signal logic is in `signal_gen.py` as `_run_xxx_signals()` AND the signal should be runnable via `signals_runner.py` independently. Extraction makes it testable, backtestable, and self-contained.

## Step-by-Step

### 1. Identify the inline function in signal_gen.py

```python
def _run_mtf_macd_signals():   # lines ~1373-1643
    # ... logic ...
    sid = add_signal(token, direction, 'mtf_macd', f'hmacd-{hmacd_char}', ...)
```

### 2. Create signals/{name}.py

Pattern from mtf_macd.py extraction:

```python
#!/usr/bin/env python3
"""
{name}.py — {Short description}.

Fires when: {entry conditions}
signal_type: {type_name}
"""

import sys, os, json, time
from typing import Optional

sys.path.insert(0, '/root/.hermes/scripts')

from signal_schema import (
    init_db, get_all_latest_prices, get_price_history,
    price_age_minutes, add_signal,
)
from hermes_constants import (
    {NAME}_ENABLED,
    {NAME}_PLUS_ENABLED,
    {NAME}_MINUS_ENABLED,
    SHORT_BLACKLIST, LONG_BLACKLIST,
)
from macd_rules import get_macd_params   # if needed

# ── Constants ────────────────────────────────────────────────────────────────
MIN_TRADE_INTERVAL = 10
LOG_FILE = '/root/.hermes/logs/signals.log'

# ── Helpers ─────────────────────────────────────────────────────────────────
def _log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] [{module_name}] {msg}'
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass

def _recent_trade_exists(token, minutes=MIN_TRADE_INTERVAL):
    TRADE_LOG = '/var/www/hermes/data/recent_trades.json'
    try:
        if not os.path.exists(TRADE_LOG): return False
        with open(TRADE_LOG) as f: data = json.load(f)
        cutoff = time.time() - minutes * 60
        for entry in data.get(token.upper(), []):
            ts = entry.get('timestamp', 0) if isinstance(entry, dict) else entry
            if ts > cutoff: return True
    except Exception: pass
    return False

def is_reasonable_price(price):
    return price is not None and price > 0 and price < 1e6

def is_delisted(token):
    from hyperliquid_exchange import is_delisted as _dl
    return _dl(token)

# ── Core detector (ported from signal_gen.py) ────────────────────────────────

def _your_detector_function(token, ...):
    """Port from signal_gen.py inline function."""
    ...

# ── Main run ────────────────────────────────────────────────────────────────

def run():
    """Scan all tokens. Returns number of signals added."""
    if not {NAME}_ENABLED:
        return 0

    init_db()
    prices_dict = get_all_latest_prices()
    added = 0

    for token, data in prices_dict.items():
        if token.startswith('@'): continue
        if price_age_minutes(token) > 10: continue
        price = data.get('price')
        if not is_reasonable_price(price): continue
        if _recent_trade_exists(token, MIN_TRADE_INTERVAL): continue
        if token.upper() in SHORT_BLACKLIST or token.upper() in LONG_BLACKLIST: continue
        if is_delisted(token.upper()): continue

        # Directional gate (before any processing)
        direction = your_direction_logic(...)
        if direction == 'LONG' and not {NAME}_PLUS_ENABLED: continue
        if direction == 'SHORT' and not {NAME}_MINUS_ENABLED: continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST: continue

        # Confidence scoring + boosts
        conf = ...
        # Cascade boost / block (if applicable)
        cascade_blocked = False
        try:
            cascade = cascade_entry_signal(token)
            if cascade.get('cascade_active') and cascade.get('cascade_direction'):
                if cascade['cascade_direction'] == direction:
                    conf += 10          # boost if agrees
                elif cascade['cascade_direction'] is not None:
                    cascade_blocked = True   # block if opposes
        except Exception: pass
        if cascade_blocked: continue

        # Write signal
        char = '+' if direction == 'LONG' else '-'
        sid = add_signal(
            token=token,
            direction=direction,
            signal_type='{unique_type_name}',   # distinct from any other signal!
            source=f'{sig_prefix}-{char}',
            confidence=conf,
            value=...,
            price=float(price),
            exchange='hyperliquid',
            timeframe=...,
        )
        if sid:
            added += 1
            _log(f'SIGNAL: {token} {direction} conf={conf:.1f}')

    _log(f'Done: {added} signals added')
    return added

if __name__ == '__main__':
    run()
```

### 3. Register in signals/__init__.py

**Import block** (after existing signal imports):
```python
try:
    from signals.{name} import run as _{name}_run
except Exception:
    _{name}_run = None
```

**Registry entry** (in SIGNAL_REGISTRY list):
```python
{'name': '{name}', 'enabled': '{NAME}_ENABLED', 'run': _{name}_run},
```

### 4. Verify no conflicts

```bash
cd /root/.hermes/scripts && python3 -c "
from signals import get_registered_signals, SIGNAL_REGISTRY
print('All:', [s['name'] for s in SIGNAL_REGISTRY])
print('Available:', [s['name'] for s in get_registered_signals()])
"
```

### 5. Verify syntax
```bash
cd /root/.hermes/scripts && python3 -m py_compile signals/{name}.py && echo "OK"
```

---

## Common Imports Needed

| From | Used for |
|------|---------|
| `signal_schema` | `add_signal`, `get_all_latest_prices`, `get_price_history`, `price_age_minutes` |
| `hermes_constants` | `*_ENABLED`, `*_PLUS_ENABLED`, `*_MINUS_ENABLED`, `SHORT_BLACKLIST`, `LONG_BLACKLIST` |
| `macd_rules` | `get_macd_params`, `compute_mtf_macd_alignment`, `cascade_entry_signal` |
| `signal_gen` | `get_tf_zscores` (for z-score dependent signals) |
| `hyperliquid_exchange` | `is_delisted` |

## Cascade Boost Logic

From mtf_macd extraction (macd_rules cascade_entry_signal):
```python
cascade = cascade_entry_signal(token)
if cascade['cascade_direction'] == mtf_direction:
    conf += 10          # boost if agrees
elif cascade['cascade_direction'] is not None:
    cascade_blocked = True   # block if opposes
```

## Testing the Extraction

```python
# Quick dry-run (flag=False exits immediately)
cd /root/.hermes/scripts && python3 signals/{name}.py

# With flag enabled:
# Temporarily set {NAME}_ENABLED = True in hermes_constants, then:
cd /root/.hermes/scripts && python3 signals/{name}.py 2>&1 | head -30
```

## Key Lesson: signal_type Collision

**Problem:** `hmacd.py` (bare histogram agreement) and `mtf_macd.py` (z-score + histogram) both used `signal_type='hmacd'`. This made it impossible to distinguish them in backtests or hot-set filtering.

**Fix:** Rename to `hmacd_bare` and `hmacd_mtf`. The `source` field still carries `hmacd+`/`hmacd-` for directional tagging. The `signal_type` column now cleanly differentiates the signal logic variant.

**Rule:** When extracting a signal from inline code, check if the original used `signal_type` that other signals also use. If so, pick a unique name that reflects the distinguishing characteristic.