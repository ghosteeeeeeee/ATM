# Confluence Bypass — Complete Fix (2026-05-12)

## Background
Prior session (2026-05-11) documented the **merge-step bypass**: `_filter_safe_prev_hotset()` at signal_compactor.py:1333 re-approved entries from the previous hot-set without re-running confluence. Fix: added confluence check in merge step.

This session (2026-05-12) found that single-source signals are STILL getting through via a different path, requiring a second layer of defense.

## New Root Cause: decider_run.py Has No Source Count Check

decider_run.py approves and executes signals from `hotset_final` without verifying source count. The confluence gate in signal_compactor.py (Step 2, line 553) correctly blocks single-source, BUT:

1. signal_compactor Step 2 confluence gate: queries DB grouped by `combo_key`. Single-source combo_key (e.g. `0G:LONG:accel-300+`) and multi-source combo_key (e.g. `0G:LONG:accel-300+,rs-s99`) are DIFFERENT combo_keys — scored independently. Single-source fails its own gate but the multi-source version also gets scored separately.
2. `_filter_safe_prev_hotset()` has the breakout exemption at line 1333 — `if src == 'breakout': pass`. This is intentional for breakout engine but means ANY source exactly equal to `'breakout'` bypasses confluence.
3. decider_run.py has NO final source-count gate — if a single-source entry somehow reaches the decider loop, it gets executed.

## Evidence from Live Trades (2026-05-12 13:59)

```
ZEN   LONG accel-300+,rs-s212    ← 2 sources ✓
BRETT LONG accel-300+            ← 1 source ✗ BUG
NEAR  LONG accel-300+            ← 1 source ✗ BUG
AXS   LONG accel-300+            ← 1 source ✗ BUG
TIA   SHORT accel-300-           ← 1 source ✗ BUG
...
```

8 of 25 trades in the session were single-source — all `accel-300+` or `accel-300-` alone.

## The Fix: Two-Layer Defense

### Layer 1 — signal_compactor.py (already has confluence gate, but needs hardening)

In `_filter_safe_prev_hotset()` at line 1333:
```python
if src == 'breakout':
    pass  # breakout exempt — intentional
elif len(source_parts) < 2:
    continue  # blocks single-source (breakout exempt only)
```

This is correct but the `breakout` exact-match string exemption is a risk. Consider making it more restrictive or adding logging when the exemption fires.

### Layer 2 — decider_run.py (NEW — execution backstop)

Add at the top of the decider loop (around line 1811), as the very last gate before `enter_trade()`:

```python
# === EXECUTION BACKSTOP: block single-source signals ===
source_parts = [p.strip() for p in (raw_source or '').split(',') if p.strip()]
if len(source_parts) < 2 and raw_source != 'breakout':
    log(f'  🚫 [EXEC-BLOCK] {token} {direction} blocked: single-source {{{raw_source}}} (need 2+)')
    skipped += 1
    continue
```

This ensures that even if signal_compactor's confluence gate is bypassed through any path, single-source signals are blocked at execution time.

## Why Both Layers?

- signal_compactor's confluence gate is the PRIMARY defense — efficient, keeps single-source out of hot-set entirely
- decider_run's execution backstop is the FAIL-SAFE — catches anything that slips through the primary (merge bugs, race conditions, hot-set.json corruption, etc.)

Defense in depth for a production trading system.

## Diagnostic: Which Trades Were Single-Source?

```python
import sqlite3, re
DB = '/root/.hermes/data/signals_hermes_runtime.db'
conn = sqlite3.connect(DB)
rows = conn.execute(
    "SELECT token, direction, source, created_at, decision FROM signals "
    "WHERE created_at >= '2026-05-12' AND decision IN ('EXECUTED','APPROVED') "
    "ORDER BY created_at"
).fetchall()

for token, direction, source, created, decision in rows:
    parts = [p.strip() for p in (source or '').split(',') if p.strip()]
    unique_types = set()
    for p in parts:
        m = re.match(r'^([a-z][a-z0-9_-]*)([+-]?)(\d+)$', p)
        unique_types.add(m.group(1)+m.group(2) if m else p)
    if len(unique_types) < 2 and source != 'breakout':
        print(f"SINGLE-SOURCE: {token} {direction} src={source!r} decision={decision} @ {created}")
conn.close()
```

## Related Files
- `signal_compactor.py:1333` — `_filter_safe_prev_hotset()` breakout exemption
- `signal_compactor.py:553` — Step 2 confluence gate (primary)
- `decider_run.py:1811` — execution backstop (failsafe) — **add the check here**
- `references/single-source-approvED-bypass.md` — prior session's root cause analysis
