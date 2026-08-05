# Subagent DB Type Bug — False Positive → Real Bug (2026-05-19)

## What Happened

Subagent reported BUG-1 (UPDATE param mismatch) and BUG-2 (division-by-zero) on `hl-sync-guardian.py` patched region.

### BUG-1: FALSE POSITIVE
Subagent counted 10 params but only 8 placeholders in UPDATE. Verified in main session:
- 9 columns in UPDATE (status, close_reason, exit_reason, guardian_closed, exit_price, pnl_pct, pnl_usdt, hype_realized_pnl_usdt, hype_realized_pnl_pct)
- `status='closed'` is hardcoded — not a placeholder
- 8 `%s` placeholders, 8 params → MATCH confirmed

**Lesson:** When a subagent reports a count mismatch, count directly in Python using the actual query string. Do not trust the subagent's line-count-based counting.

### BUG-2: HALF FALSE POSITIVE — Wrong Root Cause
Subagent said `amount_usdt` could be falsy (0 or None) causing division-by-zero. This is technically possible but `amount_usdt=50.0` default prevents it in practice.

The ACTUAL bug the subagent was sensing (without correctly identifying):
- `hl_notional_usdt` is PostgreSQL `real` → returns `float` or `None`
- `amount_usdt` is PostgreSQL `numeric` → returns `Decimal`, NOT `float`
- `calc_notional = hl_notional if hl_notional else amount_usdt` → when `hl_notional=None`, `calc_notional=Decimal('50.00')`
- `realized_pnl / calc_notional * 100` → `TypeError: float / Decimal` — CRASH on every self-close

**Root cause diagnosis requires checking actual PostgreSQL column types:**
```sql
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name='trades' AND column_name IN ('hl_notional_usdt', 'amount_usdt', 'pnl_usdt');
```
Result: `hl_notional_usdt=real`, `amount_usdt=numeric`.

**Fix applied:**
```python
hl_notional_raw = db_trade.get('hl_notional_usdt')
amount_usdt_raw = db_trade.get('amount_usdt', 50.0)
try:
    hl_notional = float(hl_notional_raw) if hl_notional_raw is not None else None
except (ValueError, TypeError):
    hl_notional = None
try:
    amount_usdt = float(amount_usdt_raw) if amount_usdt_raw is not None else 50.0
except (ValueError, TypeError):
    amount_usdt = 50.0
calc_notional = hl_notional if hl_notional else amount_usdt
if not calc_notional:
    calc_notional = 50.0  # hard fallback — never divide by zero
```

**Rule:** When subagent reports a type-related runtime error, always query `information_schema.columns` in the same session to get actual DB column types BEFORE accepting the subagent's diagnosis. `numeric` = Python `Decimal`, `real`/`double` = Python `float`.

## New Patterns to Add to ai-engineer SKILL.md

**Pattern 20 — DB numeric types cause TypeError at runtime:**
PostgreSQL `numeric` returns `Decimal`, `real` returns `float`. Mixed float/Decimal arithmetic raises `TypeError`. Always coerce to `float` before arithmetic. Query column types with `information_schema.columns`.

**Pattern 21 — `if x else y` passes 0.0 through:**
`calc_notional = hl_notional if hl_notional else amount_usdt` — if `amount_usdt=0.0` or `hl_notional=0.0`, the falsy check falls through but the value is 0 → divide by zero. Add explicit zero check.
