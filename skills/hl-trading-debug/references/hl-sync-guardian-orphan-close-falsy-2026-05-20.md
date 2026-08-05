# hl-sync-guardian.py 0.0-Falsy Bugs — Orphan Close Path

**Fixed 2026-05-20** in session fixing PnL inflation/discrepancy.

## Bugs Found

### Bug 1: `_close_orphan_paper_trade_by_id()` — amount_usdt

**Location**: hl-sync-guardian.py:2692-2694

**Before**:
```python
amount_usdt = float(row[1]) if row[1] else DEFAULT_TRADE_SIZE_USDT
```

**Problem**: `float(0.0 or 50.0)` = `50.0` when actual amount_usdt=0.0 (paper orphan). Inflates fee base and understates pnl_pct by ~50x.

**After**:
```python
amount_usdt = float(row[1]) if row[1] is not None else DEFAULT_TRADE_SIZE_USDT
```

---

### Bug 2: `_close_orphan_paper_trade_by_id()` — calc_notional

**Location**: hl-sync-guardian.py:2695-2696

**Before**:
```python
calc_notional = float(row[2]) if row[2] else amount_usdt
pnl_pct = unrealized_pnl / calc_notional * 100
```

**Problem**: `if row[2]` treats `0.0` as falsy → falls back to amount_usdt ($50) instead of $0. Wrong denominator inflates pnl_pct when calc_notional should be $0.

**After**:
```python
calc_notional = float(row[2]) if row[2] is not None else amount_usdt
```

---

### Bug 3: `get_db_open_trades()` — parts[5]

**Location**: hl-sync-guardian.py:694-696

**Before**:
```python
if parts[5]:
    amount_usdt = float(parts[5])
else:
    amount_usdt = DEFAULT_TRADE_SIZE_USDT
```

**Problem**: `'0'` (string zero, from CSV export) is truthy but float('0') = 0.0. Also `if parts[5]` is falsy for `'0'`. Actually the real bug here is `if parts[5]` where parts[5] could be '0' string or empty string '' — both need explicit None/empty check.

**After**:
```python
if parts[5] is not None and parts[5] != '':
    amount_usdt = float(parts[5])
else:
    amount_usdt = DEFAULT_TRADE_SIZE_USDT
```

## All Affected Files — 0.0 Falsy Pattern

| File | Line | Variable | Before | After |
|------|------|----------|--------|-------|
| brain.py | 637 | hl_notional_usdt | `if hl_notional_usdt` | `if hl_notional_usdt is not None` |
| brain.py | 640 | amount_usdt | `or DEFAULT_TRADE_SIZE_USDT` | `if ... is not None else DEFAULT_TRADE_SIZE_USDT` |
| position_manager.py | 883 | amount_usdt | `or DEFAULT_TRADE_SIZE_USDT` | `if row[...] is not None else DEFAULT_TRADE_SIZE_USDT` |
| position_manager.py | 884 | hl_notional_usdt | `if row[...]` | `if row[...] is not None` |
| position_manager.py | 1096 | amt (HL backfill) | `or DEFAULT_TRADE_SIZE_USDT` | `if row[0] is not None else DEFAULT_TRADE_SIZE_USDT` |
| hl-sync-guardian.py | 696 | parts[5] | `if parts[5]` | `if parts[5] is not None and parts[5] != ''` |
| hl-sync-guardian.py | 2694 | row[1] amount_usdt | `or DEFAULT_TRADE_SIZE_USDT` | `if row[1] is not None else DEFAULT_TRADE_SIZE_USDT` |
| hl-sync-guardian.py | 2696 | row[2] calc_notional | `if row[2]` | `if row[2] is not None` |

## Verification

All 6 files compile clean:
```
python3 -m py_compile hl-sync-guardian.py brain.py position_manager.py signal_compactor.py away_detector.py decider_run.py
```