# Post-Change Verdict: resistance_break Signal Integration

**Date:** 2026-09-06  
**Verifier:** delegated subagent (post-change auditor)  
**Scope:** Full integration check — syntax, imports, registry, constants, Layer 2, compactor, volatility gate, edge cases, connection leaks

---

## Verification Checklist

### 1. Syntax — `python3 -m py_compile` on all changed files
| File | Result |
|------|--------|
| `scripts/signals/resistance_break.py` | ✅ PASS |
| `scripts/hermes_constants.py` | ✅ PASS |
| `scripts/signals/__init__.py` | ✅ PASS |
| `scripts/signal_schema.py` | ✅ PASS |
| `scripts/signal_compactor.py` | ✅ PASS |
| `scripts/volatility_gate.py` | ✅ PASS |

All 6 files compile cleanly with zero syntax errors.

---

### 2. Import Chain — Signal loads from registry, constants are importable
**PASS** ✅

- `from signals.resistance_break import run` — succeeds, `run` is callable
- `from signals import get_registered_signals` — `resistance_break` found in registry (1 of 27 total signals)
- `get_fast_signals()` — `resistance_break` correctly classified as fast signal (25 total fast signals)
- All 12 `RESISTANCE_BREAK_*` constants importable from `hermes_constants`:
  - `RESISTANCE_BREAK_ENABLED = True`
  - `RESISTANCE_BREAK_PLUS_ENABLED = True`
  - `RESISTANCE_BREAK_MINUS_ENABLED = False`
  - Plus 9 detection/tuning params (LOOKBACK=200, MIN_TOUCHES=5, etc.)

---

### 3. Source String Consistency — `'resistance-break+'` matches everywhere
**PASS** ✅

| Location | Source String | Match? |
|----------|--------------|--------|
| `resistance_break.py` line 46 | `SOURCE_LONG = 'resistance-break+'` | ✅ |
| `signal_compactor.py` line 519 | `('resistance_break_long', 'resistance-break+')` | ✅ |
| `signal_schema.py` line 1832 | `if _comp == 'resistance-break+':` | ✅ |
| `signal_schema.py` line 2580 | `if c == 'resistance-break+':` | ✅ |
| `volatility_gate.py` line 98 | `'resistance-break+'` (NORMAL) | ✅ |
| `volatility_gate.py` line 141 | `'resistance-break+'` (HIGH) | ✅ |
| `volatility_gate.py` line 171 | `'resistance-break+'` (EXTREME) | ✅ |
| `hermes_constants.py` line 1148 | `'resistance-break'` (PROFIT_MONSTER_BYPASS — bare, prefix-match) | ✅ correct pattern |
| `hermes_constants.py` line 1969 | `'resistance-break'` (STANDALONE_BYPASS — bare, prefix-match) | ✅ correct pattern |

Bare `'resistance-break'` in PROFIT_MONSTER and STANDALONE bypass tuples is intentional — they use prefix matching.

---

### 4. REGIME_SIGNALS — NORMAL, HIGH, EXTREME (not FLAT)
**PASS** ✅

```python
FLAT:    False  ← correct (breakout signals should not fire in range-bound markets)
NORMAL:  True   ← works in trending markets
HIGH:    True   ← works in volatile breakouts
EXTREME: True   ← works in extreme vol
```

Verified programmatically:
```python
from volatility_gate import REGIME_SIGNALS
assert 'resistance-break+' not in REGIME_SIGNALS['FLAT']    # PASS
assert 'resistance-break+' in REGIME_SIGNALS['NORMAL']     # PASS
assert 'resistance-break+' in REGIME_SIGNALS['HIGH']       # PASS
assert 'resistance-break+' in REGIME_SIGNALS['EXTREME']    # PASS
```

---

### 5. STANDALONE_BYPASS — Present
**PASS** ✅

`hermes_constants.py` line 1969:
```python
STANDALONE_BYPASS_SIGNALS = (
    ...
    'resistance-break',  # resistance break + pullback LONG — structural breakout, works solo
    ...
)
```

---

### 6. PROFIT_MONSTER_BYPASS — Present
**PASS** ✅

`hermes_constants.py` line 1148:
```python
PROFIT_MONSTER_BYPASS_SIGNALS = (
    ...
    'resistance-break',      # resistance break + pullback — ATR SL, not PM Trail
    ...
)
```

---

### 7. Layer 2 — add_signal() and is_component_disabled()
**PASS** ✅

**add_signal() Layer 2** (`signal_schema.py` lines 1831-1839):
```python
# resistance-break (resistance break + pullback LONG)
if _comp == 'resistance-break+':
    try:
        from hermes_constants import RESISTANCE_BREAK_PLUS_ENABLED
        if not RESISTANCE_BREAK_PLUS_ENABLED:
            print(f'  DEBUG add_signal BLOCKED: ...', flush=True)
            return None
    except ImportError:
        pass
```

**is_component_disabled()** (`signal_schema.py` lines 2579-2581):
```python
# resistance-break (resistance break + pullback LONG)
if c == 'resistance-break+': return not RESISTANCE_BREAK_PLUS_ENABLED
if c == 'resistance-break': return not RESISTANCE_BREAK_ENABLED
```

Both `add_signal()` and `is_component_disabled()` correctly enforce RESISTANCE_BREAK flags.

---

### 8. Dry Run — `python3 signals/resistance_break.py --dry`
**PASS** ✅

Output:
```
[resistance-break] Added 0 signals
```

Exits cleanly, no errors. Zero signals added is expected — no tokens have sufficient candle data + resistance setup in the current market. The important thing is no crash/error.

---

### 9. Edge Cases — Empty data, None values, zero division
**PASS** ✅

| Edge Case | Handler | Result |
|-----------|---------|--------|
| Empty candles list | `_find_resistance` returns `(None, 0)`, `detect` returns `None` | ✅ |
| Candles < lookback | `_find_resistance` returns `(None, 0)` | ✅ |
| No resistance touches | `_count_touches` returns `0`, filtered by `MIN_TOUCHES` | ✅ |
| Zero price (`close=0`) | `detect()` line 115: `if price <= 0: return None` | ✅ |
| Zero volume average | Line 162: `vol_spike = current['volume'] / vol_avg if vol_avg > 0 else 0` — no division by zero | ✅ |
| `pullback_zone == 0` | Line 143: `if pullback_zone > 0:` — zero division guarded | ✅ |
| `sma == 0` | Line 188: `ema_dist = ... if sma > 0 else 0` — zero division guarded | ✅ |

---

### 10. Connection Leaks — sqlite3 connections have finally blocks
**PASS** ✅

Two sqlite3 connection sites in `resistance_break.py`:

| Function | Line | Pattern | Leak-free? |
|----------|------|---------|------------|
| `_get_1m_candles()` | 59-73 | `conn = sqlite3.connect(...)` / `finally: if conn: conn.close()` | ✅ |
| `scan_signals()` | 219-230 | `conn = sqlite3.connect(...)` / `finally: if conn: conn.close()` | ✅ |

Both connections use try/finally with conditional close. No connection leaks.

---

## Signal Type vs Source Cross-Reference

| Attribute | Value |
|-----------|-------|
| `signal_type` | `resistance_break_long` |
| `source` | `resistance-break+` |
| `direction` | `LONG` |
| `SIGNAL_REGISTRY['name']` | `resistance_break` |
| `SIGNAL_REGISTRY['enabled']` | `RESISTANCE_BREAK_ENABLED` (string reference, resolved at runtime) |
| Compactor weight | `1.1` (slight boost) |

---

## Summary

| # | Check | Verdict |
|---|-------|---------|
| 1 | Syntax (py_compile) | ✅ PASS — all 6 files |
| 2 | Import chain | ✅ PASS — constants importable, registry entry found |
| 3 | Source string consistency | ✅ PASS — `'resistance-break+'` matches across all 7 locations |
| 4 | REGIME_SIGNALS | ✅ PASS — NORMAL/HIGH/EXTREME (not FLAT) |
| 5 | STANDALONE_BYPASS | ✅ PASS — present at line 1969 |
| 6 | PROFIT_MONSTER_BYPASS | ✅ PASS — present at line 1148 |
| 7 | Layer 2 enforcement | ✅ PASS — both add_signal() and is_component_disabled() |
| 8 | Dry run | ✅ PASS — exits cleanly, 0 signals (expected) |
| 9 | Edge cases | ✅ PASS — all zero/null/empty handled |
| 10 | Connection leaks | ✅ PASS — all connections have finally blocks |

## Verdict: ✅ ALL 10 CHECKS PASS

The `resistance_break` signal is correctly integrated into the Hermes trading system. No issues found.
