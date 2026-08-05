# Single-Source Signal Bypass Root Cause

## Symptom
Single-source `accel-300+` (or any bare signal) gets APPROVED and executed without a second source.

## Two Paths Into APPROVED

| Path | Entry | Confluence Check | Status |
|------|-------|-----------------|--------|
| DB path | add_signal() to top-10 | Line ~537 confluence gate | OK |
| PENDING-APPROVED path | Line ~1037 | NONE | BUG |

When `accel-300+` fires for a token with an EXPIRED multi-source entry, `add_signal()` (signal_schema.py line 620-700) UPDATEs the existing row back to PENDING. The PENDING-APPROVED step at signal_compactor.py line 1037-1057 promotes it to APPROVED — bypassing the confluence gate.

## Fix

In signal_compactor.py line ~1039, inside the `if key in top10_keys` block:

```python
src_parts = [p.strip() for p in (source or '').split(',') if p.strip()]
if len(src_parts) < 2:
    continue  # skip single-source even if in top-10
```

This is the authoritative fix. Two additional guards were added at line ~929 (HOTSET-FINAL-BLOCK) and line ~957 (PRESERVE-MERGE-BLOCK) as defense-in-depth, but they do NOT catch the PENDING-APPROVED path.

## Key Files

- signal_compactor.py line 1037-1057: PENDING-APPROVED transition — THE BUG
- signal_compactor.py line 1136-1156: APPROVED expiry else-branch (stale APPROVED leak)
- signal_schema.py line 620-700: add_signal() merge/UPDATE — can revert multi-source to single
- signal_compactor.py line 537: Confluence gate (only fires for new DB entries)

## Verification

```bash
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT id, token, decision, source, combo_key, confidence, created_at \
   FROM signals WHERE decision='APPROVED' AND source NOT LIKE '%,%';"
```
