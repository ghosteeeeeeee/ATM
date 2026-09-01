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

## Step 0: Verify data source exists

Before writing code, confirm your data is available:

```bash
cd /root/.hermes/scripts && python3 -c "
import sqlite3
from paths import HERMES_DATA
import os
db = os.path.join(HERMES_DATA, 'candles.db')
conn = sqlite3.connect(db)
for t in ['candles_1m', 'candles_5m', 'candles_15m', 'candles_1h', 'candles_4h']:
    try:
        count = conn.execute(f'SELECT COUNT(DISTINCT token) FROM {t}').fetchone()[0]
        print(f'{t}: {count} tokens')
    except: print(f'{t}: NOT FOUND')
conn.close()
"
```

If using `latest_prices` from `signals_hermes.db`:
```python
from signal_schema import get_all_latest_prices
prices = get_all_latest_prices()  # dict of token -> {'price': float}
```

---

## Step 1: Create signal script

**File**: `/root/.hermes/scripts/signals/<signal_name>.py`

```python
#!/usr/bin/env python3
"""signal_name — brief description"""
import sys, os, sqlite3, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

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

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')  # if using candles

def _get_closes(token, table, limit):
    """DB fetch with proper connection cleanup. Returns oldest-first."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(f\"\"\"
            SELECT close FROM {table}
            WHERE token = ? ORDER BY ts DESC LIMIT ?
        \"\"\", (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        return [r[0] for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()

def detect(token, ...):
    """Return {direction, confidence, value, price} or None."""
    ...
    return {
        'direction': direction,       # 'LONG' or 'SHORT'
        'confidence': conf,           # 50-88
        'value': some_value,
        'price': price,
    }

def scan_signals() -> int:
    added = 0
    for token in all_tokens:
        # Guards
        if price_age_minutes(token) > 10:
            continue

        sig = detect(token, ...)
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

        # Cooldown
        if get_cooldown(token, direction=direction):
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
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
            z_score=sig.get('z_score'),
        )
        if sid:
            added += 1
            set_cooldown(token, direction, hours=3)
    return added

def run():
    """Entry point for signals_runner.
    Use run() with no params if signal reads from DB directly (not prices_dict).
    Using run(prices_dict=None) causes signals_runner to call get_all_latest_prices()
    even when your signal doesn't need it — wasteful DB query every cycle.
    """
    return scan_signals()
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
YOUR_SIGNAL_COOLDOWN_HOURS = 3          # per token+direction cooldown
YOUR_SIGNAL_PARAM_A = 3.0               # threshold for X
YOUR_SIGNAL_PARAM_B = 0.3               # threshold for Y
YOUR_SIGNAL_CONF_BASE = 75              # base confidence
YOUR_SIGNAL_CONF_FLOOR = 50             # min confidence
YOUR_SIGNAL_CONF_CAP = 88               # max confidence (system ceiling)
# ... all other signal-specific params
```

### Naming convention

```
SIGNAL_NAME_ENABLED          # master
SIGNAL_NAME_PLUS_ENABLED     # LONG
SIGNAL_NAME_MINUS_ENABLED    # SHORT
SIGNAL_NAME_<PARAM>          # all tweakable values
```

### Rule: NO hardcoded magic numbers in the signal script

Every threshold, period, weight, and confidence value MUST live in hermes_constants.py. This allows runtime tuning without code changes. If you find yourself writing a number directly in the signal script, move it to constants.

What belongs in hermes_constants:
- Thresholds (entry filters, overextension, velocity)
- Periods / lookback windows
- Confidence (base, floor, cap, bonus/penalty amounts)
- Cooldown durations
- Weight factors
- Any value you might want to tune after observing live performance

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

### 3D. If signal scans all tokens (>60s), add to slow set (~line 338)

If your signal iterates over all ~191 tokens, it's a slow signal. Add it:

```python
_SLOW_SIGNALS = {'momentum', 'mtf_momentum', 'your_signal'}
```

Slow signals run every 5 min instead of every 1 min. Symptom of missing this: pipeline timeout, signal runner blocks fast signals.

---

## Step 4: Layer 2 enforcement in signal_schema.py

**File**: `/root/.hermes/scripts/signal_schema.py`

**Two locations to edit** — both are mandatory. Missing either causes crashes or silent bypasses.

### 4A. `add_signal()` component loop (~line 990+)

In `add_signal()`, inside the `for _comp in _components:` loop, add:

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

### 4B. `is_component_disabled()` function (~line 2080+)

**⚠️ CRITICAL — missing this = NameError crash that kills ALL signal compaction.**

This function has its OWN import block at the top (~line 2082-2139). You must:

1. Add your constant to the import block:
```python
# In the try/except ImportError block at the top of is_component_disabled():
from hermes_constants import (
    ...
    YOUR_SIGNAL_ENABLED, YOUR_SIGNAL_PLUS_ENABLED, YOUR_SIGNAL_MINUS_ENABLED,
)
```

2. Add the component checks in the function body:
```python
# your-signal (bare)
if c == 'your-signal': return not YOUR_SIGNAL_ENABLED
# your-signal+ (LONG)
if c in ('your-signal+', 'your-signal-'): return not YOUR_SIGNAL_PLUS_ENABLED
```

**Why this matters:** `is_component_disabled()` is called by signal_compactor during hotset scoring. If your constant isn't imported, Python raises `NameError` which crashes the ENTIRE compaction run — no signals get compacted, not just yours.

### Source matching rules

| Source format | Layer 2 match |
|--------------|---------------|
| `your-signal+` | `_comp == 'your-signal+'` checks PLUS_ENABLED |
| `your-signal-` | `_comp == 'your-signal-'` checks MINUS_ENABLED |
| `your-signal` (bare) | `_comp == 'your-signal'` checks ENABLED |
| `your_signal_long` | `_comp in ('your-signal+', 'your_signal_long')` checks PLUS_ENABLED |
| `your_signal_short` | `_comp in ('your-signal-', 'your_signal_short')` checks MINUS_ENABLED |
| Asymmetric (e.g. `return_exhaustion_long` / `return_exhaustion-`) | `_comp in (...)` with both variants |

**Bug patterns to avoid**:
1. If your source is bare (no `+`/`-`), the `+`/`-` Layer 2 checks are dead code. Use `direction` param or add direction suffix to source.
2. Asymmetric sources (different format per direction) — list BOTH variants in `_comp in (...)`.
3. **Forgetting `is_component_disabled()`** — causes NameError crash in compactor. Always add BOTH locations.

---

## Step 5: Source weight in signal_compactor.py (recommended)

**File**: `/root/.hermes/scripts/signal_compactor.py`

In `SIGNAL_SOURCE_WEIGHTS` (~line 177-253):

```python
('your_signal_long',  'your-signal+'):  1.0,
('your_signal_short', 'your-signal-'):  1.0,
```

---

## Step 5a: STANDALONE_BYPASS_SIGNALS (if signal works solo)

**File**: `/root/.hermes/scripts/hermes_constants.py`

If your signal fires on a single source (not a combo) and should bypass the confluence gate (which normally requires 2+ unique signal types), add it to `STANDALONE_BYPASS_SIGNALS`:

```python
STANDALONE_BYPASS_SIGNALS = (
    ...,
    'your-signal',  # structural breakout signal, works solo
)
```

**When to add:** Momentum/structural signals that fire solo (e.g., `accel-300-v2-long`, `r2-trend-long`, `atr-spike`).

**When NOT to add:** Combo/meta signals that rely on confluence (e.g., `confluence`, `signal_confluence`).

**What happens without it:** The compactor's confluence gate blocks single-source signals unless they merge with another signal for the same token+direction. Your signal will fire but never reach the hotset.

---

## Step 5b: Volatility filter — TWO layers (mandatory)

Your signal must pass **both** volatility filters or it will be silently blocked at Layer 3.

### Layer A: Volatility Floor (`signal_compactor.py`)

**File**: `/root/.hermes/scripts/signal_compactor.py` — `check_volatility_floor()`

Blocks signals when a token's 5m price volatility < `VOL_FLOOR_THRESHOLD` (0.15%). This is automatic — no action needed unless your signal reads from a non-candle source.

**What you need to do:** Nothing. The compactor checks the token's candle data, not your signal's data source. New tokens with < 20 candles fail open.

### Layer B: Volatility Gate / Regime Filter (`volatility_gate.py`) ⚠️ CRITICAL

**File**: `/root/.hermes/scripts/volatility_gate.py` — `REGIME_SIGNALS`

This is the **severe/normal/flat/extreme** regime filter. `decider_run.py` calls `should_trade(token, signal=source)` and **SKIPS** your signal if it's not in the regime list.

**4 Regimes (ATR% based):**
| Regime | ATR% | Best for |
|--------|------|----------|
| FLAT | < 0.48% | Mean reversion |
| NORMAL | 0.48-1.0% | Trend following |
| HIGH | 1.0-1.5% | Breakout |
| EXTREME | > 1.5% | Continuation (or skip) |

**What you MUST do:** Add your source strings to `REGIME_SIGNALS` in `volatility_gate.py`:

```python
REGIME_SIGNALS = {
    'FLAT': {
        ...,
        'your-signal', 'your-signal+', 'your-signal-',  # your signal
    },
    'NORMAL': {
        ...,
        'your-signal', 'your-signal+', 'your-signal-',
    },
    'HIGH': {
        ...,
        'your-signal', 'your-signal+', 'your-signal-',
    },
    'EXTREME': {
        ...,
        'your-signal', 'your-signal+', 'your-signal-',
    },
}
```

**Which regimes?** Think about when your signal works:
- **Structural signals** (liquidation clusters, order book, copy trade) → all 4 regimes
- **Momentum signals** → NORMAL + HIGH
- **Mean reversion signals** → FLAT + NORMAL
- **Breakout signals** → HIGH + EXTREME
- **Counter-trend signals** → FLAT only (dangerous in trending markets)

**Verification:**
```python
from volatility_gate import should_trade, REGIME_SIGNALS
# Check your signal is in all target regimes
for regime, sigs in REGIME_SIGNALS.items():
    assert any('your-signal' in s for s in sigs), f'MISSING from {regime}'

# Simulate should_trade
result = should_trade('BTC', signal='your-signal+')
assert result[0] == 'TRADE', f'BLOCKED: {result}'
```

---

## Step 5c: PROFIT_MONSTER_BYPASS_SIGNALS (if signal manages its own exits)

**File**: `/root/.hermes/scripts/hermes_constants.py`

If your signal has its own ATR SL/TP logic and you don't want `profit_monster.py` to interfere with exits, add it to `PROFIT_MONSTER_BYPASS_SIGNALS`:

```python
PROFIT_MONSTER_BYPASS_SIGNALS = (
    ...,
    'your-signal',  # manage via ATR SL, not PM Trail
)
```

**When to add:** Momentum signals with ATR-based trailing stops (e.g., `accel-300-v2-long`, `atr-spike`, `r2-trend-long`).

**When NOT to add:** Signals that benefit from PM Trail's quick profit-taking (e.g., `bb-bounce`, `confluence`). These are losing signals that PM Trail helps cut quickly.

**What happens without it:** profit_monster may close your winning trades early (at 0.5-2% profit via Tier 1) instead of letting ATR trailing capture the full move.

---

## Step 6: Verification

```bash
# 1. Syntax check ALL changed files (not just your script)
cd /root/.hermes/scripts
python3 -c "
import py_compile
files = [
    'signals/your_signal.py',
    'hermes_constants.py',
    'signals/__init__.py',
    'signal_schema.py',
    'signal_compactor.py',
    'volatility_gate.py',
]
for f in files:
    py_compile.compile(f, doraise=True)
    print(f'{f}: OK')
print('All syntax checks passed')
"

# 2. Import chain verification — catches missing constants and circular imports
cd /root/.hermes/scripts && python3 -c "
from signals.your_signal import run
from signals import get_fast_signals
fast = get_fast_signals()
your = [s for s in fast if s['name'] == 'your_signal']
assert len(your) > 0, 'NOT in registry'
assert your[0]['run'] is not None, 'run function is None'
print(f'Registry: OK (enabled={your[0][\"enabled\"]})')

from volatility_gate import REGIME_SIGNALS
for regime in ['NORMAL', 'HIGH']:
    found = any('your-signal' in s for s in REGIME_SIGNALS.get(regime, set()))
    assert found, f'MISSING from {regime}'
print('Volatility gate: OK')
"

# 3. Dry run
cd /root/.hermes/scripts && timeout 30 python3 signals/your_signal.py --dry

# 4. Check logs
tail -100 /root/.hermes/logs/pipeline.log | grep your_signal
```

### Pre-flight checklist (verify before bug_hunter)

| Check | How | Fail = |
|-------|-----|--------|
| **DB connections safe** | Every `sqlite3.connect()` has matching `conn.close()` in `finally` block or uses `with` | Connection leak → "database locked" under load |
| **No hardcoded numbers** | Grep script for raw numbers: `grep -n '[=<>] *[0-9]' signals/your_signal.py` | Can't tune without code changes |
| **Blacklist in script** | Script checks `LONG_BLACKLIST`/`SHORT_BLACKLIST` before `add_signal()` | Blacklisted token gets signal |
| **Cooldown set** | Uses `set_cooldown()` or `get_cooldown()` | Spam signals on same token |
| **Not in _DEAD_SIGNALS** | `grep -n '_DEAD_SIGNALS\|DEAD_SOURCES' signal_schema.py` | Signal silently killed by add_signal() |
| **Source format consistent** | Uses `+`/`-` suffix consistently, not mixed bare+directional | Layer 2 checks may be dead code |
| **Source not blacklisted** | `python3 -c "from signal_schema import validate_source; print(validate_source('your-signal+'))"` | Signal enters DB but gets blocked in hotset |
| **Vol floor understood** | Signal will be blocked by Layer 3 if token vol < 0.15% — this is correct behavior | Low-vol tokens don't move enough to profit |
| **In REGIME_SIGNALS** ⚠️ | `grep -n 'your-signal' volatility_gate.py` — MUST appear in correct regimes | `should_trade()` silently SKIPS your signal at Layer 3 |
| **In `is_component_disabled()`** ⚠️ | `grep -n 'your-signal' signal_schema.py` — constant must be imported in that function | NameError crash kills ALL compaction |
| **In STANDALONE_BYPASS** (if solo) | `grep -n 'your-signal' hermes_constants.py` — check STANDALONE_BYPASS_SIGNALS | Single-source signals blocked by confluence gate |
| **In PROFIT_MONSTER_BYPASS** (if ATR-managed) | `grep -n 'your-signal' hermes_constants.py` — check PROFIT_MONSTER_BYPASS_SIGNALS | PM Trail cuts winners early |

---

## Step 7: bug_hunter — MANDATORY

**Do not skip. Do not commit before this.** Every signal addition has caught issues on the first bug_hunter pass.

Use the Task tool to run bug_hunter:

```
You are the bug_hunter. Audit these files for bugs:
- scripts/signals/your_signal.py (new signal script)
- scripts/signal_schema.py (Layer 2 entries in add_signal() AND is_component_disabled())
- scripts/hermes_constants.py (new constants, STANDALONE_BYPASS_SIGNALS, PROFIT_MONSTER_BYPASS_SIGNALS)
- scripts/signals/__init__.py (registry entry)
- scripts/signal_compactor.py (new source weights)
- scripts/volatility_gate.py (new REGIME_SIGNALS entries)

Check: SQL injection, connection leaks, import safety (especially
is_component_disabled() import block), source string consistency between
script/Layer 2/compactor, edge cases (empty data, None values, zero
division), direction logic, hardcoded numbers, missing from
STANDALONE_BYPASS_SIGNALS or PROFIT_MONSTER_BYPASS_SIGNALS.

Return: bugs with file:line references, or ALL CLEAR.
```

**Fix any bugs found, then re-run bug_hunter to verify fixes are clean.**

Bug_hunter checks:
- Source string matches between script and Layer 2 enforcement
- Import safety (try/except ImportError on all new checks)
- Flag naming consistency
- Control flow bugs (return None vs continue in loops)
- Missing blacklist checks
- Dead code paths
- DB connection leaks (cursor closed in finally block)
- Edge cases (ret == 0, empty data, None values)

---

## Step 8: Commit and wrap up

```bash
cd /root/.hermes
git add scripts/signals/your_signal.py scripts/hermes_constants.py scripts/signals/__init__.py scripts/signal_schema.py scripts/signal_compactor.py scripts/volatility_gate.py
git commit -m "signals: add your_signal — <brief description>

- New signal script: signals/your_signal.py
- hermes_constants: YOUR_SIGNAL_ENABLED/PLUS/MINUS flags + STANDALONE_BYPASS + PROFIT_MONSTER_BYPASS
- signals/__init__.py: registry entry
- signal_schema.py: Layer 2 enforcement + is_component_disabled
- signal_compactor.py: source weight
- volatility_gate.py: REGIME_SIGNALS entries"
```

Then run `/wrapup` — this triggers the full post-change workflow (bug_hunter re-verify → OpenMemory → CEO → push). **Do not skip /wrapup.**

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

8. **DB connection leak** — always close connections in `finally` block. Pattern:
   ```python
   conn = None
   try:
       conn = sqlite3.connect(db, timeout=10)
       # ... work ...
   except Exception:
       return []
   finally:
       if conn:
           conn.close()
   ```

9. **run(prices_dict=None) when signal doesn't use prices** — if your signal reads from candles.db or other DB directly, use `def run():` instead. Using `run(prices_dict=None)` causes signals_runner to call `get_all_latest_prices()` wastefully every cycle.

10. **Zero return edge case** — if `ret_1h == 0` (flat), the token has no momentum. Skip it or return None from direction decision. Don't arbitrarily pick LONG or SHORT.

11. **Hardcoded magic numbers** — every threshold, period, weight, and confidence value MUST live in hermes_constants.py. If you write a number directly in the signal script (`> 3.0`, `< 0.5`, `conf = 75`), move it to a constant. This allows runtime tuning without code changes or redeploys.

12. **`_get_closes` query pattern** — use `SELECT close FROM {table} WHERE token=? ORDER BY ts DESC LIMIT ?` then `reversed(rows)` for oldest-first. Do NOT wrap in subquery with `ORDER BY ts ASC` — `ts` isn't in the subquery SELECT and SQLite throws a silent error caught by `except Exception: return []`.

13. **Staleness thresholds must match candle timeframe** — 1h candles update hourly, so a 15-minute staleness check kills all tokens. Use: 1m→120s, 5m→600s, 15m→1800s, 1h→5400s, 4h→21600s.

14. **Don't let short-TF noise dilute strong moves** — if your signal is a "leaderboard" or "mover" signal, weight the primary timeframe heavily (0.7+) in move_score. A 5%1h move with -0.5%5m shouldn't score below threshold because of 5m noise.

15. **Combo weights** — after your signal has 5+ trades, self_learner.py auto-tunes its weight in `data/combo_weights.json`. signal_compactor.py loads these on startup. You don't need to manually set `SIGNAL_SOURCE_WEIGHTS` for combos — the system does it automatically.

---

## Adding Solo Variants (Direction-Specific Versions)

Sometimes an existing signal only works for one direction (e.g., `r2_trend` is SHORT-only) and you need a separate file for the other direction (e.g., `r2_trend_long`). This is the "solo variant" pattern.

### When to use solo variants

- Existing signal is directional-only (SHORT or LONG) and you want the other direction
- The detection logic is similar but inverted (e.g., slope < 0 vs slope > 0)
- The signal needs its own kill-switch, source string, and registry entry

### Example: r2_trend → r2_trend_long

`r2_trend.py` detects confirmed downtrends (SHORT only: slope < 0, price below regression). `r2_trend_long.py` detects confirmed uptrends (LONG only: slope > 0, price above regression).

### Steps to add a solo variant

**Step 1: Create the new signal file**

Copy the existing signal and modify the detection logic for the opposite direction:

```python
# signals/r2_trend_long.py
#!/usr/bin/env python3
"""r2_trend_long.py — R² trend confirmation for LONG entries."""
# Same imports as parent signal
from signals.r2_trend import _ols_params  # reuse shared logic

def detect_r2_long(token, candles, price):
    """Inverted from detect_r2_short: slope > 0, price > intercept."""
    # Same R² calculation, but check for UPTREND instead of DOWNTREND
    ...
    return {
        'direction': 'LONG',  # <-- changed from 'SHORT'
        'source': f'r2l-long{bars_since}',  # <-- different source prefix
        ...
    }
```

**Step 2: Add flag to hermes_constants.py**

```python
R2_TREND_LONG_ENABLED = True    # new solo variant flag
```

Follow naming convention: `SIGNAL_NAME_<DIRECTION>_ENABLED`

**Step 3: Register in signals/__init__.py**

```python
# Import
try:
    from signals.r2_trend_long import run as _r2_trend_long_run
except Exception:
    _r2_trend_long_run = None

# Registry
{'name': 'r2_trend_long', 'enabled': R2_TREND_LONG_ENABLED, 'run': _r2_trend_long_run},
```

**Step 4: Layer 2 enforcement in signal_schema.py**

```python
# In add_signal() component loop:
if _comp == 'r2l-long' and not R2_TREND_LONG_ENABLED:
    print(f'  DEBUG add_signal BLOCKED: {token} {direction} source="{source}" R2_TREND_LONG_ENABLED=False', flush=True)
    return None
```

Also add to `is_component_disabled()`:
```python
if c == 'r2l-long': return not R2_TREND_LONG_ENABLED
```

**Step 5: Source weight in signal_compactor.py**

```python
('r2_trend_long', 'r2l-long'): 1.0,
```

### Key differences from parent signal

| Aspect | Parent (r2_trend) | Solo variant (r2_trend_long) |
|--------|-------------------|------------------------------|
| File | `signals/r2_trend.py` | `signals/r2_trend_long.py` |
| Flag | `R2_TREND_ENABLED` | `R2_TREND_LONG_ENABLED` |
| Direction | SHORT only | LONG only |
| Source prefix | `r2s` | `r2l` |
| Detection | slope < 0, price < intercept | slope > 0, price > intercept |
| Layer 2 match | `r2-trend-` | `r2l-long` |
| Registry name | `r2_trend` | `r2_trend_long` |

### Reuse pattern

Share helper functions with the parent signal to avoid duplication:

```python
from signals.r2_trend import _ols_params, _precompute_x  # reuse OLS logic
```

Only the detection function and scan loop need to be different.
