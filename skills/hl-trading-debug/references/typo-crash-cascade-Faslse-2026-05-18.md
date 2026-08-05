# Typo Crash Cascade — `Faslse` → `False` (2026-05-18)

## What Happened

`hermes_constants.py` line 24 had a typo:
```python
LIVE_TRADING_ENABLED = Faslse  # NameError at import
```

This cascaded into a full pipeline failure:
1. `position_manager.py` imports `hermes_constants` → `NameError: name 'Faslse' is not defined` → module dead
2. `hermes-trades-api.py` same import crash → dead
3. `hype_paper_sync.py` same crash → dead
4. Pipeline ran without position_manager → trades opened on HL (brain.py `mirror_open` succeeded) but no DB record created → orphan HL positions
5. Guardian detected orphans → closed them → position_manager was down so it couldn't record them properly
6. Guardian orphan INSERT failed with `duplicate key` (LIT/TIA already had closed trades)

## Symptom Timeline

```
21:57:03  brain.py opens TIA LONG on HL (mirror_open succeeded)
21:57:09  Guardian: "ORPHAN DETECTED — no DB record"  
21:57:10  Guardian closes TIA LONG @ $0.39914
21:57:16  Pipeline crashes: position_manager + hermes-trades-api import errors
21:58:05  brain.py opens LIT SHORT on HL
21:58:09  Guardian: "ORPHAN DETECTED — no DB record"
21:58:09  Guardian closes LIT SHORT @ $0.91395
21:58:21  Pipeline: same crash repeats
```

## Why Guardian Orphan Logic Is Correct

Guardian's orphan detection and close is **working as designed**:
- HL has position, DB has no record → orphan
- Closes HL position to prevent phantom live trade
- Attempts to write audit record

The `duplicate key` error on the audit record is secondary — the orphan close itself succeeded. The audit INSERT fails because LIT/TIA already have closed rows from prior sessions (pre-existing records).

## Fix Applied

```python
# hermes_constants.py line 24
LIVE_TRADING_ENABLED = False  # was Faslse
```

## Diagnostic Pattern

When trades open on HL but guardian immediately treats them as orphans:
1. Check `pipeline.err.log` or `pipeline.log` for import/NameError
2. Check if `position_manager` shows "Traceback" in pipeline log
3. The crash prevents DB INSERT, leaving HL-only positions → guardian orphan path fires correctly
4. Root cause is upstream, not guardian

## Key Lesson

**Typo in a critical constant crashes the entire import chain silently.** `Faslse` is a valid Python identifier (it's a name), so `py_compile` passes it — only runtime import fails. Use a lint rule or static analysis to catch this class of error.

## Related

- Guardian orphan logic is correct — fires when `mirror_open` succeeds but `add_trade()` DB INSERT fails
- Root cause: import crash, not PnL sync changes (orthogonal)
- PnL sync changes (DEFAULT_TRADE_SIZE_USDT, hl_notional_usdt column) compile clean and don't affect this crash