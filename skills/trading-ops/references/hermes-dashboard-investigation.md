---
name: hermes-dashboard-investigation
description: Dashboard data investigation for Hermes — trades.html and signals.html pipelines. Absorbed into trading-ops as a reference.
---

# Hermes Dashboard Investigation — Absorbed into trading-ops

Umbrella is `trading-ops`. Reference content below.

## Two Dashboards

### trades.html Pipeline
`Guardian → PostgreSQL → hermes-trades-api.py → trades.json → nginx → trades.html`

Key files:
- Two `trades.json` files: `/var/www/hermes/data/trades.json` (LIVE) vs `/root/.hermes/data/trades.json` (STALE/SEED)
- PostgreSQL brain DB: `host=/var/run/postgresql database=brain`
- Common issue: Guardian reverts `trades.json` edits — always close in postgres first

### signals.html Pipeline
`signal_gen → signals DB → signal_compactor.py → hotset.json + signals DB → hermes-trades-api.py → signals.json → nginx → signals.html`

Key files:
- hotset.json is `{hotset: [...]}` (dict), not a flat list — common schema bug
- Decision states: APPROVED / PENDING / EXECUTED / SKIPPED / EXPIRED
- signals.json updates on-request, not on-timer — can show stale data
- Schema bugs: flat-list access, Unix timestamp vs SQLite datetime, blocked signals marked EXECUTED

## Unified Investigation Checklist

1. Identify which dashboard has the issue
2. Check file staleness — `os.stat()` mtime comparison
3. Check schema — hotset.json is `{hotset: [...]}`, not flat list
4. Check decision cross-contamination — tokens in multiple tabs
5. Check EXECUTED cross-reference — every `decision='EXECUTED'` must have a trades.json entry
6. Check pipeline logs — `grep -i "err\|traceback\|TypeError" /root/.hermes/logs/pipeline.log`
7. Check PostgreSQL — `psql "host=/var/run/postgresql dbname=brain user=postgres"`

## Before Changing Shared Function Signatures

`signal_schema.py`, `signal_compactor.py`, `signal_gen.py` — Hermes is multi-script. One caller's crash causes silent pipeline failure. Audit procedure:
1. Find ALL callers of the function
2. Check each call site for compatibility
3. Update ALL callers atomically
4. Verify pipeline recovery

See also: `hermes-signature-change-audit.md` reference in `hermes-pipeline-debug`.