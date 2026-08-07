---
name: add-signal
description: Use when the user wants to add a new trading signal to the Hermes pipeline. Triggers on keywords like "add signal", "new signal", "create signal", "signal template", "signal checklist".
---

# Add Signal — Complete Checklist

Step-by-step guide for adding a new signal to the Hermes trading pipeline. Follow every step. No shortcuts.

## Architecture

```
signal script → add_signal() → signals table (PENDING)
  → signal_compactor scores/ranks → hotset.json (APPROVED)
    → decider_run.py → brain.py → Hyperliquid
```

3 enforcement layers:
- **Layer 1**: Signal script's own guards (kill-switch, blacklists, cooldown)
- **Layer 2**: `add_signal()` in signal_schema.py (kill-switch, blacklists, confidence cap)
- **Layer 3**: `signal_compactor.py` (hot-set scoring, confluence, WR filter)

---

## Step 1: Create signal script

**File**: `/root/.hermes/scripts/signals/<signal_name>.py`

Use `vortex_break.py` or `return_exhaustion.py` as template.

```python
#!/usr/bin/env python3
"""signal_name — brief description"""
import sys, os, sqlite3, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes

# ── Constants (from hermes_constants.py) ──────────────────────────────────
from hermes_constants import (
    YOUR_SIGNAL_ENABLED,
    YOUR_SIGNAL_PLUS_ENABLED,
    YOUR_SIGNAL_MINUS_ENABLED,
    LONG_BLACKLIST, SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG  = 'your_signal_long'
SIGNAL_TYPE_SHORT = 'your_signal_short'
SOURCE_LONG       = 'your-signal+'
SOURCE_SHORT      = 'your-signal-'

# ── Detection ─────────────────────────────────────────────────────────────
def detect(token, prices, ...):
    """Return {direction, confidence, value, price} or None."""
    ...
    return {
        'direction': direction,       # 'LONG' or 'SHORT'
        'confidence': conf,           # 50-88
        'value': some_value,
        'price': price,
    }

# ── Scanner ───────────────────────────────────────────────────────────────
def scan_signals(prices_dict: dict) -> int:
    added = 0
    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        # Guards
        if price_age_minutes(token) > 10:
            continue
        if get_cooldown(token, direction=direction):
            continue

        sig = detect(token, prices, ...)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not YOUR_SIGNAL_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not YOUR_SIGNAL_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        sid = add_signal(
            token=token.upper(),
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=sig['confidence'],
            value=sig.get('value'),
            price=price,
            exchange='hyperliquid',
            timeframe='5m',
            z_score=sig.get('z_score'),
        )
        if sid:
            added += 1
            from signal_gen import set_cooldown
            set_cooldown(token, direction, hours=3)
    return added

def run(prices_dict=None):
    """Entry point for signals_runner."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_signals(prices_dict)
```

### Source string convention

| Direction | Source format | Example |
|-----------|--------------|---------|
| Both | `signal-name+` / `signal-name-` | `mover+`, `mover-` |
| Both (underscore) | `signal_name_long` / `signal_name_short` | `vortex_break_long` |
| Bare (no direction) | `signal-name` | `bb_bounce` (Layer 2 uses direction param instead) |

**Critical**: Layer 2 source matching must match your source string exactly.

---

## Step 2: Add flags to hermes_constants.py

**File**: `/root/.hermes/scripts/hermes_constants.py`

Add in the signal kill-switches section (~line 674+):

```python
# ── Your Signal Name (description) ───────────────────────────────────────
# your_signal.py — brief description
YOUR_SIGNAL_ENABLED = True              # master kill-switch
YOUR_SIGNAL_PLUS_ENABLED = True         # LONG direction
YOUR_SIGNAL_MINUS_ENABLED = True        # SHORT direction
YOUR_SIGNAL_COOLDOWN_HOURS = 3          # optional
YOUR_SIGNAL_MIN_CONFIDENCE = 70         # optional
# ... signal-specific params (thresholds, periods, etc.)
```

### Naming convention

```
SIGNAL_NAME_ENABLED          # master
SIGNAL_NAME_PLUS_ENABLED     # LONG
SIGNAL_NAME_MINUS_ENABLED    # SHORT
```

---

## Step 3: Register in signals/__init__.py

**File**: `/root/.hermes/scripts/signals/__init__.py`

### 3A. Import flags (in the `from hermes_constants import (...)` block, ~line 15-60)

```python
YOUR_SIGNAL_ENABLED, YOUR_SIGNAL_PLUS_ENABLED, YOUR_SIGNAL_MINUS_ENABLED,
```

### 3B. Import run function (in the `try/except` block, ~line 67-270)

```python
try:
    from signals.your_signal import run as _your_signal_run
except Exception:
    _your_signal_run = None
```

### 3C. Add to SIGNAL_REGISTRY (~line 288-331)

```python
{'name': 'your_signal', 'enabled': 'YOUR_SIGNAL_ENABLED', 'run': _your_signal_run},
```

### 3D. If signal takes >60s, add to slow set (~line 338)

```python
_SLOW_SIGNALS = {'momentum', 'mtf_momentum', 'your_signal'}
```

---

## Step 4: Layer 2 enforcement in signal_schema.py

**File**: `/root/.hermes/scripts/signal_schema.py`

In `add_signal()`, inside the `for _comp in _components:` loop (~line 657+), add:

```python
# your-signal
if _comp == 'your-signal':
    try:
        from hermes_constants import YOUR_SIGNAL_ENABLED
        if not YOUR_SIGNAL_ENABLED:
            print(f'  DEBUG add_signal BLOCKED: {token} {direction} source="{source}" YOUR_SIGNAL_ENABLED=False', flush=True)
            return None
    except ImportError:
        pass
if _comp == 'your-signal+':
    try:
        from hermes_constants import YOUR_SIGNAL_PLUS_ENABLED
        if not YOUR_SIGNAL_PLUS_ENABLED:
            print(f'  DEBUG add_signal BLOCKED: {token} {direction} source="{source}" YOUR_SIGNAL_PLUS_ENABLED=False', flush=True)
            return None
    except ImportError:
        pass
if _comp == 'your-signal-':
    try:
        from hermes_constants import YOUR_SIGNAL_MINUS_ENABLED
        if not YOUR_SIGNAL_MINUS_ENABLED:
            print(f'  DEBUG add_signal BLOCKED: {token} {direction} source="{source}" YOUR_SIGNAL_MINUS_ENABLED=False', flush=True)
            return None
    except ImportError:
        pass
```

### Source matching rules

| Source format | Layer 2 match |
|--------------|---------------|
| `your-signal+` | `_comp == 'your-signal+'` checks PLUS_ENABLED |
| `your-signal-` | `_comp == 'your-signal-'` checks MINUS_ENABLED |
| `your-signal` (bare) | `_comp == 'your-signal'` checks ENABLED |
| `your_signal_long` | `_comp in ('your-signal+', 'your_signal_long')` checks PLUS_ENABLED |
| `your_signal_short` | `_comp in ('your-signal-', 'your_signal_short')` checks MINUS_ENABLED |

**Bug pattern to avoid**: If your source is bare (no `+`/`-`), the `+`/`-` Layer 2 checks are dead code. Use `direction` param or add direction suffix to source.

---

## Step 5: Source weight in signal_compactor.py (optional)

**File**: `/root/.hermes/scripts/signal_compactor.py`

In `SIGNAL_SOURCE_WEIGHTS` (~line 177-253):

```python
('your_signal_long',  'your-signal+'):  1.0,
('your_signal_short', 'your-signal-'):  1.0,
```

---

## Step 6: Verification

```bash
# 1. Syntax check
python3 -c "import py_compile; py_compile.compile('scripts/signals/your_signal.py', doraise=True)"

# 2. Dry run
cd /root/.hermes/scripts && python3 signals/your_signal.py --dry

# 3. Check logs
tail -100 /root/.hermes/logs/pipeline.log | grep your_signal

# 4. Test kill-switch: set flag to False, verify Layer 2 blocks
# In hermes_constants.py: YOUR_SIGNAL_ENABLED = False
# Run add_signal with your source → should see "DEBUG add_signal BLOCKED"

# 5. Check hotset
cat /var/www/hermes/data/hotset.json | python3 -m json.tool | grep your_signal

# 6. Monitor WR (after first trades)
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
rows = conn.execute('SELECT signal_type, COUNT(*), SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) FROM signal_outcomes WHERE signal_type LIKE \"%your_signal%\" GROUP BY signal_type').fetchall()
for r in rows: print(f'{r[0]}: {r[1]} trades, {r[2]}/{r[1]} WR')
conn.close()
"
```

---

## Things you do NOT need to touch

| Component | Why |
|-----------|-----|
| `signals_runner.py` | Auto-discovers from registry |
| `signal_outcomes` table | Auto-created by position_manager |
| DB schema | Uses existing `signals` table |
| systemd timers | Pipeline runs signals_runner automatically |
| `decider_run.py` | Layer 3 auto-applies |
| `monte_carlo_gate.py` | Auto-queries signal_outcomes |
| `signal_auditor.py` | Auto-discovers from registry |
| `signal_decay_detector.py` | Auto-monitors by signal_type |

---

## Permanent death

If the signal is killed forever, add to `NEVER_REENABLE_FLAGS` in hermes_constants.py:

```python
NEVER_REENABLE_FLAGS = {
    ...
    'YOUR_SIGNAL_ENABLED',
    'YOUR_SIGNAL_PLUS_ENABLED',
    'YOUR_SIGNAL_MINUS_ENABLED',
}
```

This prevents `signal_rotator.py` from auto-re-enabling it.

---

## Common bugs to avoid

1. **Bare source = dead Layer 2 +/- checks** — if source is `'your-signal'` (no suffix), the `_comp == 'your-signal+'` check never matches. Use direction in source or check `direction` param.

2. **Case mismatch** — `_comp` is the raw source string (not uppercased). Match exact case.

3. **Missing try/except ImportError** — Layer 2 imports must be wrapped or a missing constant crashes ALL signals.

4. **return None in loop** — use `continue` to skip current token, not `return None` which kills the entire scan.

5. **Local flag shadow** — don't define `YOUR_SIGNAL_ENABLED = True` locally in the script if hermes_constants has it False. Import from constants.

6. **Wrong column names** — use `pnl_usdt` and `amount_usdt`, never `pnl_usd` or `size`.

7. **SQL placeholders** — use `?` or named params, never `***`.
