# Float 0.0 Is Falsy — The `if x` Null Check Bug

## The Bug (brain.py:637, 2026-05-20)

```python
# WRONG — 0.0 triggers fallback
calc_notional = float(hl_notional_usdt) if hl_notional_usdt else amount_usdt

# CORRECT — only None triggers fallback, 0.0 is treated as real
calc_notional = float(hl_notional_usdt) if hl_notional_usdt is not None else amount_usdt
```

## Why This Matters

- `hl_notional_usdt = 0.0` is a legitimate value (tiny HL position, ~$7)
- `hl_notional_usdt = None` means "not set" (legacy trade before column existed)
- `if hl_notional_usdt` evaluates `0.0` as falsy → falls back to `amount_usdt` ($50)
- Result: real $1 HL profit → computed as $5 in DB (5x inflation)

## Python Truth Table

| Value | `if x` | `x is not None` |
|-------|--------|-----------------|
| `0.0` | False (falsy) | True |
| `None` | False (falsy) | False |
| `1.0` | True | True |
| `""` | False (falsy) | True (empty string is not None) |
| `[]` | False (falsy) | True (empty list is not None) |

## The Fix Pattern

For any nullable numeric field where `0` is a legitimate value:
```python
value = float(x) if x is not None else default
```

## Related Bugs Found in Session

- `brain.py:637` — `calc_notional = float(hl_notional_usdt) if hl_notional_usdt else amount_usdt` → PnL ~5x inflated for legacy trades
- Any `if amount_usdt else DEFAULT` pattern for position sizing could have same issue