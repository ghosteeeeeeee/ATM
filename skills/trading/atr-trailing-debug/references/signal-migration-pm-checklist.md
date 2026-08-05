# Signal Migration → PM Exclusion Filter Checklist
**Date:** 2026-05-17
**Type:** Prevention checklist

---

## The Rule

When migrating a **standalone executor** (a `*_hunter.py` script that was opened positions and set its own SL/TP) into the **pipeline signal** model (`signals/*.py`):

> **The PM exclusion filter update is the FIRST action after migration — not the last.**

A signal in the exclusion filter → PM never touches it → it gets whatever SL/TP the old executor wrote at entry → those values are permanently stale.

---

## Why It Breaks

| Component | What it does | After migration |
|-----------|-------------|-----------------|
| `signals/*.py` | Produces signal only, no SL/TP | ✓ Still correct |
| `decider_run.py` | Writes pump-mode SL/TP at entry (1.5%/2.5%) | ✓ Correct — needs PM override |
| `position_manager.py` | Overrides entry SL/TP with ATR values | ✗ Blocked by exclusion filter |
| Old executor | Hardcoded SL/TP, then deleted | ✓ Removed — but filter still had it |

The exclusion filter was correct when the old executor existed (it managed SL/TL independently). After deleting the executor and migrating to pipeline signal, the filter becomes wrong — PM must now manage those trades.

---

## Step-by-Step Migration Checklist

### Phase 1: Before the old executor is removed

- [ ] Confirm `signals/*.py` version of the signal runs correctly in `signals_runner`
- [ ] Confirm the pipeline signal does NOT write SL/TP to DB (signal only, no `INSERT INTO trades`)
- [ ] Identify the exclusion filter entries in `position_manager.py` (search for the signal name in SQL queries)
- [ ] **Add the signal to a "pending removal" list** — do not remove yet

### Phase 2: Remove old executor

- [ ] Delete `*_hunter.py` from `/root/.hermes/scripts/`
- [ ] Disable and delete systemd service + timer (e.g. `hermes-zscore-pump-hunter.service`)
- [ ] `daemon-reload`

### Phase 3: Update PM exclusion filter — IMMEDIATELY

- [ ] Edit `position_manager.py` — remove the migrated signal from the exclusion filter SQL
- [ ] Verify only signals that actually manage their own SL/TL remain in the filter (currently: `pump_hunter` only)
- [ ] Syntax check: `python3 -m py_compile position_manager.py`

### Phase 4: Fix existing open trades from that signal

For any open trade that has the migrated signal and `atr_managed=FALSE`:
```sql
UPDATE trades
SET stop_loss = 0, target = 0, atr_managed = FALSE
WHERE status = 'open' AND signal LIKE 'signal-name-%';
```

This forces PM's staleness detection (`current_sl <= 0`) to fire on next cycle and write fresh ATR values.

### Phase 5: Verify

- [ ] Run PM manually, check `[TPSL]` log lines for the migrated signal's trades
- [ ] Confirm they now appear in PM output and have ATR-based SL/TP
- [ ] Confirm `atr_managed = TRUE` in DB after one cycle

---

## PM Exclusion Filter Locations

In `position_manager.py`, three queries have the exclusion filter:
```bash
grep -n "pump_hunter\|zscore_pump\|exclusion" position_manager.py
```

Current state (2026-05-17): Only `pump_hunter` should remain in the filter. Any other signal name there = investigate whether it was migrated.

## Current Signals in PM Exclusion Filter

| Signal | Reason for exclusion | Should it be there? |
|--------|---------------------|---------------------|
| `pump_hunter` | `pump_hunter.py` manages its own HL orders directly | ✓ YES — until migrated |
| `zscore_pump` | **REMOVED 2026-05-17** — was excluded because old `zscore_pump_hunter.py` existed; that executor is deleted | ✗ NO — was a bug |

## How to Detect This Bug Without Knowing About It

```bash
# Check for open trades with pump-mode (1.5%) SL but atr_managed=FALSE
psql brain postgres -c "
SELECT token, direction, entry_price, stop_loss, target, atr_managed, signal
FROM trades
WHERE status='open' AND atr_managed=FALSE
AND (stop_loss > 0 AND target > 0);
"
```

Any result = stale pump-mode values that PM is blocked from overwriting.

## The Underlying Pattern

The pipeline has **two SL/TL writers** that can conflict:
1. `decider_run.py` — writes at entry (pump-mode defaults or 0/0 for deferral)
2. `position_manager.py` — overwrites with ATR values within 1 cycle

When PM is blocked from running (exclusion filter), writer #2 never fires. Writer #1's values persist forever.

The exclusion filter is the **gate** — keep it surgically precise. Only exclude signals that truly manage their own SL/TL outside the PM pipeline.