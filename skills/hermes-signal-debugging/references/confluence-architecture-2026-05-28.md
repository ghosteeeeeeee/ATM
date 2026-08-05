# Confluence Architecture — Why Hotset Stays Empty (2026-05-28)

## The Symptom
- price_collector works: 92 tokens stored, ~80s runtime, all TFs aggregated
- mtp_zscore fires: STBL SHORT conf=85% z=-2.174 observed in signals.log
- signal_compactor blocks ALL signals: "only 1 unique types {mtp-zscore-} — need 2+"
- hotset stays empty → no trades

## Root Cause: Parallel-Write Architecture Cannot Produce Multi-Source Signals

### How signals are written (signals/__init__.py)
1. Signal scripts (rs.py, mtp_zscore.py, etc.) run in **parallel via ThreadPoolExecutor** (21 workers)
2. Each script calls `add_signal()` independently — writes to `signals.json` by token+direction
3. `add_signal()` does NOT combine multiple generators into one multi-source entry
4. Result: last-write-wins for same token+direction → always single-source

### Why confluence gate fires
- `CONFLUENCE_REQUIRED = True` in hermes_constants.py (line 668)
- Gate requires `unique_signal_types >= 2` — needs 2+ distinct signal-type prefixes
- Single-source signals (e.g., `source='mtp-zscore-'`) are always blocked

### Historical evidence from signals.json
```
mtp-zscore-: 41 entries  ← only mtp_zscore fires consistently
rs-s30: 10 entries      ← rs fires sometimes but never combines with mtp_zscore
mtp-zscore+,rs-s72: 1 entry  ← combo entry exists but very rare
```

## What Would Fix It

### Option 1: Disable CONFLUENCE_REQUIRED (short-term)
```python
# hermes_constants.py line 668
CONFLUENCE_REQUIRED = False  # bypass 2+ source requirement
```
Hotset will populate but loses multi-source safety net.

### Option 2: Signal aggregator (architectural)
Create a post-processing step that combines multiple signal generators'
outputs for the same token+direction within one pipeline cycle into
ONE multi-source entry before DB write.

### Option 3: Investigate why rs.py not firing alongside mtp_zscore
- Check if rs.py actually generates signals in current run (grep signals.log)
- Check RS_PROXIMITY_K = 0.70 (tightened from 1.75) — may block most tokens
- If both fires but separately, add_signal still merges them → confluence still fails

## Key Files
- `/root/.hermes/scripts/signal_compactor.py` — lines 563-584 (CONFLUENCE-GATE)
- `/root/.hermes/scripts/signals/__init__.py` — add_signal() merge logic (token+direction only)
- `/root/.hermes/scripts/hermes_constants.py:668` — CONFLUENCE_REQUIRED flag