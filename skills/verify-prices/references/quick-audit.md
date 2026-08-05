---
name: verify-prices-summary
description: Comprehensive candle and price data integrity audit for Hermes — umbrella is hermes-pipeline-debug. This file kept for discoverability.
---

# Verify Prices — Absorbed into hermes-pipeline-debug

For full audit procedures, use `hermes-pipeline-debug` → `references/verify-prices.md`.

## Quick Run

```bash
# Step 1 — Quick Health Summary
cd /root/.hermes && python3 << 'EOF'
import sqlite3
db = '/root/.hermes/data/candles.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
for tf in ['candles_1m','candles_5m','candles_15m','candles_1h','candles_4h']:
    cur.execute(f"SELECT COUNT(DISTINCT token), COUNT(*) FROM {tf}")
    ntok, nrows = cur.fetchone()
    cur.execute(f"PRAGMA table_info({tf})")
    cols = [r[1] for r in cur.fetchall()]
    print(f"{tf}: {ntok} tokens, {nrows} rows, is_closed={'YES' if 'is_closed' in cols else 'NO'}")
conn.close()
EOF
```

## Key Decision Tree
```
prices seem wrong?
├── All tokens same gaps at same timestamps → 429 rate limits → use gap-filling pattern
├── All tokens show is_closed=0 on higher TFs → NORMAL, not stale
├── gap-300 fires but price moved → read hermes-pipeline-debug references/verify-prices.md
└── speed_history.json all stale → use token_speeds table, not speed_history.json
```

## Known Traps
- `is_closed=0` on 1h/4h = developing candle, NOT stale
- `speed_history.json` = abandoned since Apr 29, use `token_speeds` table
- `price_history.db` = 0 bytes EMPTY, do not use
- `hl_cache.json` reader uses `mids` key but API returns `allMids`
- gap300_5m reading `candles_1m` (stale) instead of `price_history` (live)