---
name: clear-all
description: Complete reset of Hermes trading state — clears all open/closed trades from DB and JSON files, purges hot-set, cooldowns, and pending signals. Use when starting fresh or after manual trade intervention.
tags: [hermes, trading, maintenance, reset]
author: T
created: 2026-04-08
updated: 2026-04-08
---

# Clear All — Complete Trading State Reset

Closes ALL open Hyperliquid positions, purges all trades from DB and JSON caches, clears hot-set files, and resets all cooldowns. Use when starting fresh or after manual intervention.

## Quick Run

```bash
python3 << 'EOF'
import sys, time
sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import close_position, get_open_hype_positions
from _secrets import BRAIN_DB_DICT
import psycopg2, json

# ── 1. Close all HL positions (15s apart) ────────────────────
positions = get_open_hype_positions()
tokens = [p['coin'] for p in positions]
print(f"Closing {len(tokens)} HL positions...")

for i, token in enumerate(tokens):
    result = close_position(token)
    print(f"  [{i+1}/{len(tokens)}] {token}: {'✅' if result.get('success') else '❌'} {result}")
    if i < len(tokens) - 1:
        time.sleep(15)

# ── 2. Archive + clear DB trades ───────────────────────────
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
TS = datetime.now().strftime('%Y%m%d_%H%M')

cur.execute(f"CREATE TABLE IF NOT EXISTS trades_archive_{TS} AS SELECT * FROM trades WHERE status='closed'")
cur.execute("DELETE FROM trades WHERE status IN ('closed', 'open', 'pending')")
cur.execute("DELETE FROM ab_results")
conn.commit()
print(f"\nArchived {cur.rowcount} trades to trades_archive_{TS}")

# ── 3. Purge cooldowns ──────────────────────────────────────
for table in ['signal_cooldowns', 'loss_cooldowns']:
    try:
        cur.execute(f"DELETE FROM {table}")
        print(f"Cleared {table}: {cur.rowcount} rows")
    except: pass

conn.commit()
cur.close()
conn.close()

# ── 4. Clear JSON cache files ───────────────────────────────
# NOTE: hotset.json must be a dict with "hotset" key, NOT a plain list "[]"
hotset_template = {"hotset": [], "timestamp": 0}
trades_template = {"open": [], "closed": []}
files = {
    '/root/.hermes/data/trades.json': json.dumps(trades_template),
    '/var/www/hermes/data/trades.json': json.dumps(trades_template),
    '/root/.hermes/data/hotset.json': json.dumps(hotset_template),
    '/var/www/hermes/data/hotset.json': json.dumps(hotset_template),
    '/var/www/hermes/data/hotset_approval_rate.json': '[]',
    '/var/www/hermes/data/hotset_failures.json': '[]',
    '/var/www/hermes/data/hotset_last_updated.json': '[]',
}
for path, content in files.items():
    try:
        with open(path, 'w') as f: f.write(content)
        print(f"Cleared {path}")
    except: pass

print("\n✅ All clear")
EOF
```

## What Gets Cleared

| Target | Action |
|--------|--------|
| Open HL positions | Market-close each, 15s apart |
| DB `trades` table | Archive to `trades_archive_{TS}` then DELETE |
| DB `ab_results` | DELETE all |
| DB `signal_cooldowns` | DELETE all |
| DB `loss_cooldowns` | DELETE all |
| `/root/.hermes/data/trades.json` | Overwrite with `{"open": [], "closed": []}` |
| `/var/www/hermes/data/trades.json` | Overwrite with `{"open": [], "closed": []}` |
| `/var/www/hermes/data/hotset.json` | Overwrite with `{"hotset": [], "timestamp": 0}` |
| Hot-set rate/failure files | Overwrite with `[]` |

## Verification

```python
# Verify clean state
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM trades WHERE status IN ('open','pending','closed')")
assert cur.fetchone()[0] == 0, "trades not empty!"
cur.execute("SELECT COUNT(*) FROM signal_cooldowns")
assert cur.fetchone()[0] == 0, "cooldowns not empty!"
# HL positions
positions = get_open_hype_positions()
assert len(positions) == 0, f"HL still has {len(positions)} positions!"
print("✅ All clean")
```

## When to Use

- After manual trade intervention on Hyperliquid
- Before starting a fresh trading cycle with clean slate
- After bulk-closing positions (e.g. end of trading session)
- When hot-set is stale and needs full rebuild

## Notes

- Always archive before deleting — never DELETE without archiving
- Closed HL positions that don't appear in DB still need manual DB cleanup
- The `hotset.json` is served by nginx on port 54321 — clearing it forces a hot-set rebuild on next pipeline run
- JSON files may exist in both `/root/.hermes/data/` and `/var/www/hermes/data/` — clear both
