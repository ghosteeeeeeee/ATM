# trades.json server filter bug — 2026-05-08

## Symptom
`/var/www/hermes/data/trades.json` shows `"open": []` and `"closed": []` with
`"open_count": 0, "closed_count: 0"` — but PostgreSQL brain DB has 2 closed trades.

## Root cause
`update-trades-json.py` queries `server='Hermes' OR server IS NULL`:
```python
cur.execute("""
    SELECT COUNT(*) FROM trades
    WHERE (server='Hermes' OR server IS NULL) AND status='closed'
""")
```

All live trades are written by the guardian on **Tokyo** with `server='Tokyo'`.
The query returns 0 because the filter is wrong.

## Fix
Remove the server filter entirely — `update-trades-json.py` doesn't know about
Tokyo (it's a standalone writer meant for any server context):
```python
cur.execute("SELECT COUNT(*) FROM trades WHERE status='closed'")
# and for the closed trades query:
FROM trades WHERE status='closed'
```

## Files affected
- `/root/.hermes/scripts/update-trades-json.py` — lines 48-59

## Verification
```bash
# Check server values in brain DB
psql "host=/var/run/postgresql dbname=brain user=postgres password=Brain123" \
  -c "SELECT DISTINCT server, status, COUNT(*) FROM trades GROUP BY server, status"

# Run the writer
cd /root/.hermes/scripts && python3 update-trades-json.py
# Should show: open=N closed=M (not all 0)

# Check output
cat /var/www/hermes/data/trades.json
```