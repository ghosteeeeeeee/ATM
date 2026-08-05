# Hot-Set / Approved DB Desync Bug (2026-05-21)

## Symptom
- `hotset.json` has 10 entries (ENS, 0G, ETHFI, etc.)
- `get_approved_signals()` returns **0 rows**
- `decider_run` iterates over `get_approved_signals()` → `scored = []` → no trades fire
- Live trading is enabled, no blacklisted tokens, no open positions blocking

## Root Cause

**Architecture: two separate write paths**

1. **DB path** — `signal_compactor` transitions PENDING→APPROVED in `signals_hermes_runtime.db` (Step 1-14)
2. **JSON path** — `_enrich_and_write_signals()` writes `hotset.json` directly without writing APPROVED rows

**`decider_run` reads DB APPROVED, NOT hotset.json**

`decider_run` calls `get_approved_signals()` which queries the DB. It never reads `hotset.json` directly. So entries in `hotset.json` without corresponding APPROVED DB rows are invisible to decider_run.

## Why APPROVED Rows Are Missing

Signal compactor has two ways to produce a hot-set entry:

### Path A: Normal PENDING→APPROVED transition (broken for single-source)
- Requires 2+ sources (confluence check at line 1135: `len(src_parts) < 2` blocks single-source)
- 5-minute staleness gate (lines 387-396) expires PENDING signals before they build confluence
- Result: single-source signals (e.g. `zscore-pump-`) can never reach APPROVED via this path

### Path B: PRESERVE path (broken for null-combo_key entries)
- Lines 770-820, triggered when `_preserved_won = True`
- Requires `combo_key` match with `prev_hotset_by_combo`
- When combo_key is null (new entry, never had one), PRESERVE path doesn't fire
- Even when PRESERVE fires and writes to hotset.json: the APPROVED-DB upsert at lines 1016-1070 only fires for `prev_entry` that won a merge — it does NOT create new APPROVED rows for entries that are purely new

### Path C: _enrich_and_write_signals() direct write (broken — no DB upsert)
- Line 1355: writes entries to `hotset.json` and `signals.json`
- Sets `combo_key: None` for preserved entries (line 826)
- **Never creates or refreshes APPROVED rows in the DB**
- `decider_run` reads DB → empty → no trades

## DB State (2026-05-21)
```
APPROVED: 0
PENDING: 50+
EXPIRED: 319
EXECUTED: ...
```

## The Fix

In `_enrich_and_write_signals()` (around line 1355), after building `hotset_final`, for each entry **upsert an APPROVED row**:

```python
# For each entry in hotset_final, ensure APPROVED row exists
for entry in hotset_final:
    token = entry['token']
    direction = entry['direction']
    combo_key = entry.get('combo_key') or f"{token}:{direction}:{entry.get('source', '').split('-')[0]}"
    # Upsert APPROVED
    cur.execute("""
        INSERT INTO signals (token, direction, decision, combo_key, created_at, source, confidence)
        VALUES (?, ?, 'APPROVED', ?, datetime('now'), ?, ?)
        ON CONFLICT DO UPDATE SET
            decision='APPROVED',
            created_at=datetime('now'),
            combo_key=excluded.combo_key
        WHERE decision != 'APPROVED'
    """, (token, direction, combo_key, entry.get('source',''), entry.get('confidence', 0)))
```

Also refresh `survival_rounds` for existing APPROVED entries in hot-set (matching lines 1197-1210).

## Key Code Locations
- `signal_compactor.py:770-820` — PRESERVE path (skipped for null combo_key)
- `signal_compactor.py:1016-1070` — PRESERVE-APPROVED upsert (only fires when `_preserved_won`)
- `signal_compactor.py:1135-1144` — confluence check (blocks single-source)
- `signal_compactor.py:1355` — `_enrich_and_write_signals()` — **where fix goes**
- `decider_run.py:400` — `get_approved_signals()` reads DB, NOT hotset.json
- `signal_schema.py` — `get_approved_signals()` query