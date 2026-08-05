---
name: json-field-rename
description: Rename a field key in a shared JSON data store consumed by multiple services — finds all writers and readers, updates atomically, verifies.
category: software-development
tags: [json, refactor, distributed, debugging]
---

# JSON Field Rename Across Multi-Service System

When a JSON file is written by one service and consumed by many, renaming a field requires tracking down EVERY writer and reader.

## The Pattern

A shared JSON file (e.g. `trades.json`) has:
- **Writers** — scripts that produce the file
- **Readers** — scripts that parse it

Rename a field (e.g. `"token"` → `"coin"`) by updating ALL of them.

## Step-by-Step

### 1. Find all writers
```bash
grep -rn "OUT_TRADES\|PAPER_JSON\|TRADES_JSON" /root/.hermes/scripts/ --include="*.py"
```

### 2. Find all readers
```bash
grep -rn "trades\.json\|PAPER_JSON\|TRADES_JSON\|OUT_TRADES" /root/.hermes/scripts/ --include="*.py" -l
```

### 3. For each reader, find field access patterns
```bash
grep -rn "p\['token'\]\|t\['token'\]\|jt\['token'\]\|\.get('token'" /root/.hermes/scripts/ --include="*.py"
```
Look for: `p['token']`, `t.get("token")`, `jt["token"]`, dict key reads.

### 4. Update writers first, then readers
- **Writers**: change the key in the output dict
- **Readers**: change the key in the input parsing

### 5. Update dashboard/UI labels too
```bash
grep -rn "\.token\|'token'" /var/www/hermes/ --include="*.html" --include="*.js"
```

### 6. Verify with a parse test
```python
import json
with open('/var/www/hermes/data/trades.json') as f:
    data = json.load(f)
# Test all reader patterns
open_trades = data.get('open', [])
coins = [p.get('coin') for p in open_trades]  # reader pattern
print('All coins:', coins)
```

### 7. Check the raw bytes
```bash
head -c 500 /var/www/hermes/data/trades.json | cat -v
```
If `cat -v` shows `***` but Python json.load shows real names — the file was written with corrupted data. Trigger a fresh write by running the writer script.

## Common Pitfall

**Multiple writers**: There may be more than one script that writes the file. In Hermes:
- `hermes-trades-api.py` writes `trades.json` via API timer
- `update-trades-json.py` is a standalone writer

Both must be updated.

**Reader patterns vary**:
- `p['token']` — direct dict key access (crashes if wrong)
- `p.get('token')` — safe get (returns None)
- `{t["token"] for t in list}` — set comprehension
- `jt.get('token', '')` — safe get with fallback

Update all patterns to match.

## When `***` Appears in Raw Bytes

If `cat -v` shows `***` but `python3 -c "import json; print(json.load(open(f))['open'][0]['coin'])"` shows the real value — the file may be in a different encoding, have special bytes, or be a different file than expected. Use `stat`, `file`, `md5sum`, and `realpath` to confirm which file is actually being served.

## Files in scope (Hermes example)

Writers: `hermes-trades-api.py`, `update-trades-json.py`
Readers: `hype-paper-sync.py`, `hl-paper-sync.py`, `hl-sync-guardian.py`, `wasp.py`
UI: `trades.html` (table headers + JS render functions)
