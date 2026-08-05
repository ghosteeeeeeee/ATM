---
name: analyze-trades
description: Archive closed trades, reconcile prices, rebuild A/B test data, analyze results, and apply winning adjustments to Hermes trading system.
tags: [hermes, trading, analysis, ab-test, trades]
author: T
created: 2026-04-01
updated: 2026-04-04
---

# Analyze Trades — Hermes Trading Analysis

Archives closed trades, rebuilds A/B test data with corrected experiment parsing, analyzes results, and applies indicator weight adjustments.

## Quick Run

```bash
# 1. Archive closed trades to /root/.hermes/archive/trades/
python3 << 'EOF'
import psycopg2, json, os
from datetime import datetime

ARCHIVE_DIR = '/root/.hermes/archive/trades'
BRAIN = dict(host='/var/run/postgresql', dbname='brain', user='postgres', password='postgres')

conn = psycopg2.connect(**BRAIN)
conn.autocommit = True
cur = conn.cursor()

cur.execute('SELECT row_to_json(t) FROM trades t WHERE status=%s', ('closed',))
rows = [r[0] for r in cur.fetchall()]
count = len(rows)

ts = datetime.now().strftime('%Y%m%d_%H%M%S')
out_path = f'{ARCHIVE_DIR}/trades_archive_{ts}.json'
with open(out_path, 'w') as f:
    json.dump({
        'archived_at': datetime.now().isoformat(),
        'source': 'live_trades_closed',
        'count': count,
        'columns': list(rows[0].keys()) if rows else [],
        'trades': rows
    }, f, indent=2, default=str)

print(f"Exported {count} closed trades -> {out_path}")
cur.execute('DELETE FROM trades WHERE status=%s', ('closed',))
print(f"Deleted {cur.rowcount} rows from trades table")
cur.close(); conn.close()
EOF
```

## Key Findings (2026-04-06 — 209 closed trades after cleanup)

### System Bug Summary
| Bug | Count | Impact |
|-----|-------|--------|
| hl_position_missing | 19 DELETED | Orphan HL positions with corrupted entry prices (~$10). Root cause: `add_orphan_trade` parameter swap (entry_price ↔ amount_usdt). Fix applied 2026-04-05. |
| guardian_missing | ~50 | Guardian lost track, forced near-zero close — top winners |
| trailing_exit | ~30 | Trailing SL triggered — solid wins |

### System Health (cleaned)
- **Total closed:** 209 trades (after 19 corrupted deletions)
- **Net PnL:** +$17.90 | LONG: +$10.84 | SHORT: +$7.06
- LONG: 92 trades (43W/49L, 47% WR)
- SHORT: 117 trades (53W/64L, 45% WR) ← unexpectedly strong

### Systematic Losers
| Token | Direction | n | Net | Action |
|-------|-----------|---|-----|--------|
| ME | LONG | 10 | -$2.77 | **ADDED TO BLACKLIST** 2026-04-06 |

## BLACKLIST UPDATES (2026-04-06)
- **+ME** to LONG_BLACKLIST — 10 trades, net -$2.77 (hermes_constants.py)

## Actions Required

1. **ME LONG blacklist** — Added to LONG_BLACKLIST in hermes_constants.py.
2. **Corrupted trades purged** — 19 `hl_position_missing` trades with entry ~$10 deleted. DB now clean.
3. **SHORT vs LONG balance** — MONITOR: SHORT WR 45% vs LONG WR 47% in recent batch. Consider relaxing SHORT regime filter.
4. **Guardian aggressiveness** — Consider: guardian is closing trades before trailing SL triggers. Top winners close at 1-2% via guardian while trailing SL could capture 3-5%.

## Hot Set Validation Rules

Tokens in hot set must have ALL of:
- `z_score` not NULL
- `rsi_14` not NULL
- `macd_hist` not NULL
- `confidence` > 60
- Minimum regime alignment check (per-token z_score_tier + macro regime)
- NOT in HOTSET_BLOCKLIST

### Archive Exploration — Querying Existing Archives

Archived trades live in **`/root/.hermes/archive/trades/`** as JSON files (PostgreSQL archive tables were dropped 2026-05-08).

**rebuild_ab_results.py is DEPRECATED** — it references PostgreSQL tables that no longer exist. For experiment/AB analysis, parse the JSON archives directly.

```bash
# Inspect a JSON archive
python3 -c "
import json
d = json.load(open('/root/.hermes/archive/trades/trades_archive_20260508_015041.json'))
print(d['count'], 'trades')
print('Columns:', d['columns'])
print('Sample:', d['trades'][0])
"

# Export a specific archive to CSV
python3 -c "
import json, csv, sys
d = json.load(open('/root/.hermes/archive/trades/trades_archive_20260508_015041.json'))
rows = d['trades']
if rows:
    writer = csv.DictWriter(open('/tmp/trades.csv', 'w'), fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    print(f'Exported {len(rows)} to /tmp/trades.csv')
"
```

Archive structure:
```
/root/.hermes/archive/trades/
  trades_archive_YYYYMMDD_HHMMSS.json          — live closed trades snapshot
  trades_archive_YYYYMMDD_HHMM.json              — brain DB table dumps (32 files, ~3,800 trades)
  archive_closed_trades_20260414_184604.json   — 865 closed trades
  closed_trades_archive.json                    — 86 closed trades
  archive_*_duplicates_*.json                  — duplicate cleanup logs
  archive_*_phantoms_*.json                     — phantom cleanup logs
```

Each JSON: `{"archived_at", "source", "count", "columns", "trades": [...]}`

```bash
# Quick count all archives
python3 -c "
import json, os, glob
total = 0
for f in sorted(glob.glob('/root/.hermes/archive/trades/*.json')):
    try:
        d = json.load(open(f))
        n = len(d.get('trades', []))
        print(f'{os.path.basename(f):50s} {n:5d}')
        total += n
    except: pass
print(f'TOTAL: {total}')
"
```

## Re-run Analysis

Run this skill weekly or after major pipeline changes. Archive before each run.
