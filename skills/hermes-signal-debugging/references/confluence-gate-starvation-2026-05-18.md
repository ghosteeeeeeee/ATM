# Confluence Gate Starvation (2026-05-18)

## Problem
Hot-set is empty despite signals existing in the DB. All signals blocked at confluence gate.

## Root Cause
`signal_compactor.py` requires ≥2 **unique signal types** (not just sources) per token to pass the confluence gate.

**Single-type signals blocked regardless of confidence:**

```
BRETT SHORT: zscore-pump- only → BLOCKED (need 2+ types)
PEOPLE SHORT: zscore-pump- only → BLOCKED  
CHILLGUY SHORT: zscore-pump- only → BLOCKED
rs-s252 LONG: rs only → BLOCKED
rs-s264 LONG: rs only → BLOCKED
```

**Only signal that passed:** `MERL SHORT: rs-r33,rs-r45,zscore-pump-`
- 3 sources but only 2 unique types (`rs` + `zscore-pump`)
- Blocked by OPEN-POS-FILTER (MERL already traded this cycle)

## Architecture
Signal type = source category (rs, zscore-pump, pct-hermes, vel-hermes, etc.)
Source = individual level identifier (rs-s252, rs-r33, zscore-pump-, etc.)

The **CONFLUENCE_REQUIRED** flag in `hermes_constants.py` (line 617) enforces 2+ unique signal types.

The grouping query at signal_compactor.py line 537 uses `GROUP_CONCAT(DISTINCT source)` — so multiple `rs` levels (rs-r33, rs-r45) count as ONE type.

## Diagnostic Commands
```bash
# Check signals in DB (last 5 min)
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, source, confidence FROM signals \
   WHERE created_at > datetime('now', '-5 minutes') ORDER BY confidence DESC"

# Dry-run signal_compactor to see confluence gate decisions
python3 /root/.hermes/scripts/signal_compactor.py --dry --verbose 2>&1 | grep -E "CONFLUENCE|PASS|BLOCK"

# Count signals by type
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT source, direction, COUNT(*) FROM signals \
   WHERE created_at > datetime('now', '-30 minutes') GROUP BY source, direction"
```

## Key Code Locations
- Confluence gate: `signal_compactor.py` lines ~555-577
- Unique type check: `signal_compactor.py` line 562 (`len(unique_signal_types) < 2`)
- GROUP_CONCAT grouping: `signal_compactor.py` line ~537
- CONFLUENCE_REQUIRED flag: `hermes_constants.py` line 617

## Related Triggers
- "hot-set only has one signal type" — this is the precursor symptom
- "signals not combining" — upstream of this issue
- "signal_compactor running but hot-set empty" — the observed outcome