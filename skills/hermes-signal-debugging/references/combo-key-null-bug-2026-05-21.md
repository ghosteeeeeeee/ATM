# combo_key=None Bug — 2026-05-21

## Symptom
Signals appear in hotset.json but no trades execute. DB has 0 APPROVED signals.

## Root Cause
`_preserve_previous_hotset()` (signal_compactor.py:1598) loads entries from the previous hotset.json and merges them into the new hotset. These entries have `combo_key=None` because:
1. They were NOT produced by the GROUP BY query (line 406) — that query fetches DB entries keyed by combo_key.
2. They survived via `_filter_safe_prev_hotset()` instead (line 1493).
3. When `combo_key=None` entries are written to hotset.json and later loaded as `prev_hotset`, the cycle repeats — combo_key stays None forever.

## Why This Breaks Trades
1. `get_approved_signals()` (signal_schema.py:1208) returns empty because:
   - APPROVED rows written by signal_compactor have `combo_key=None`
   - The expiry gate at signal_compactor.py:1237 `OR (combo_key IS NULL)` immediately expires all null-combo_key APPROVED signals
2. decider_run reads DB APPROVED → empty → no trades

## The Fix (line ~1638 in _preserve_previous_hotset)
Before appending to `hotset_output`, reconstruct combo_key if None:
```python
src = entry.get('source') or ''
src_parts = sorted([p.strip() for p in src.split(',') if p.strip()])
entry['combo_key'] = f"{entry['token']}:{entry['direction']}:{','.join(src_parts)}"
```

## Related Bugs Found
- P0: `SIGNAL_SOURCE_BLACKLIST` in hermes_constants.py never imported/enforced in decider_run.py before execute_trade
- P2: `log(msg)` at decider_run.py:219 takes 1 arg but called with 2 at line 2012 (`'WARN'` silently dropped)

## Key Files
- `/root/.hermes/scripts/signal_compactor.py` — `_preserve_previous_hotset()` at line 1598, expiry gate at 1237
- `/root/.hermes/scripts/decider_run.py` — reads DB APPROVED, `SIGNAL_SOURCE_BLACKLIST` not enforced
- `/root/.hermes/scripts/signal_schema.py` — `get_approved_signals()` at line 1208