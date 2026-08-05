# Confluence Gate Bug — 2026-05-21

## Root Cause

The confluence gate at `signal_compactor.py:1081` requires `len(src_parts) >= 2` for PENDING→APPROVED transitions. All signals fire as single-source:

- `rs-s###` fires alone (source='rs-s264')
- `zscore-pump+` fires alone (source='zscore-pump+')
- The 5-minute add_signal() merge window is too short for rs+zscore to ever overlap
- Result: APPROVED count in DB = 0 → nothing enters execution path

## Log Evidence

Every compaction cycle:
```
🔒 [CONFLUENCE-GATE-BLOCK] AXS LONG: only 1 unique types {rs-s80} — need 2+
🔒 [PENDING-APPROVE-BLOCK] PEOPLE:LONG single-source blocked from APPROVE — src='zscore-pump+' parts=1
```

## Fix Options

1. **Extend merge window** (signal_schema.py:645): 5min → 30min so rs+zscore can combine
2. **Single-source bypass**: confidence ≥ 70 + `source='zscore-pump+'` → allow without 2-source
3. **Approve preserves**: when preserve path writes entry with 2+ sources, also UPDATE DB row to APPROVED
4. **Pre-pair zscore-pump**: generate companion signal alongside zscore-pump so it always has 2 sources

## Pipeline Flow Reference

```
zscore_pump.py → signals_hermes_runtime.db (PENDING, source='zscore-pump+')
rs.py          → signals_hermes_runtime.db (PENDING, source='rs-s264')
add_signal() merge window = 5 min → rarely combines
signal_compactor PENDING→APPROVE check: src_parts < 2 → BLOCK
APPROVED=0 → get_approved_signals() returns [] → decider_run returns early
```