# Subagent False Positive: Param-Count Mismatch (2026-05-19)

## What happened
Delegated audit of `hl-sync-guardian.py` patched regions to ai-engineer subagent.
Subagent returned:
```
BUG-[1]: CRASH — Param/placeholder COUNT MISMATCH in UPDATE query
  UPDATE with 10 placeholders (%s) but 11 values passed in tuple
```

## Why it was wrong
The subagent miscounted. The actual SQL:
```sql
UPDATE trades SET
    status='closed',         -- hardcoded string, NOT a placeholder
    close_reason=%s,
    exit_reason=%s,
    guardian_closed=TRUE,   -- hardcoded boolean, NOT a placeholder
    exit_price=%s,
    pnl_pct=%s,
    pnl_usdt=%s,
    hype_realized_pnl_usdt=%s,
    hype_realized_pnl_pct=%s
WHERE id=%s
```
`status='closed'` and `guardian_closed=TRUE` are literal values, not `%s` placeholders.
8 placeholders, 8 params — correct match.

## Root cause
Subagent's file-read tool returned partial content, causing it to miscount the SQL string.
It saw `status='closed'` and treated it as if it were `status=%s`.

## Verification method
Always run Python to verify param counts:
```python
query = """UPDATE trades SET status='closed', close_reason=%s, ..."""
print(f'Placeholders: {query.count("%s")}')  # 8
params = ('val1', 'val2', ...)
print(f'Params: {len(params)}')              # 8
```

## Lesson
When a subagent reports a param/placeholder mismatch, verify by running
`query.count('%s')` against `len(params)` in Python before accepting.