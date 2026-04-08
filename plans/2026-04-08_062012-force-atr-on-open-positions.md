# Plan: Force ATR SL/TP on Open Positions + Ensure Ongoing Monitoring

## Goal
Apply ATR-based stop-loss and take-profit to all currently open trades immediately, then confirm they are monitored going forward on every position-manager cycle.

---

## Current Context

- `position_manager.py` runs every 60 seconds via `hermes-price-collector.timer` (systemd)
- `check_and_manage_positions()` is the entry point, called once per cycle
- ATR-adaptive SL/TP bulk push runs **inside** that loop (lines 1767–1779):
  - `_collect_atr_updates(open_positions)` — collects positions needing SL/TP refresh
  - `_execute_atr_bulk_updates(updates)` — pushes to Hyperliquid
  - Only fires if delta > `ATR_UPDATE_THRESHOLD_PCT` (0.3%)
- Currently open positions in `hermes.db` (PostgreSQL, Tokyo) — no JSON flat file

---

## Step 1: Build One-Shot ATR Force Script

**File:** `/root/.hermes/scripts/force_atr_update.py`

### What it does
1. Reads all open positions from `hermes.db`
2. For each open position, computes new ATR-based SL and TP via the same `_collect_atr_updates` logic
3. Pushes all updates to Hyperliquid **regardless of ATR_UPDATE_THRESHOLD_PCT** (force push = override the threshold)
4. Logs results

### Key logic
```python
# Force-push = set threshold to 0, bypass deduplicate cache
# Use _force_fresh_atr() for every token to ensure current ATR
# Build update dicts same shape as _collect_atr_updates output
# Call _execute_atr_bulk_updates() directly
```

### Files changed
- `hermes/scripts/force_atr_update.py` (new)

### Validation
```bash
python3 /root/.hermes/scripts/force_atr_update.py
# Expected: prints [ATR] lines for each updated position
```

---

## Step 2: Confirm Ongoing Monitoring

The ATR bulk push already runs inside `check_and_manage_positions()` — which fires every 60s via systemd timer. **No new cron or service needed.**

To verify:
```bash
systemctl status hermes-price-collector.timer
# Should show: active (running)
```

And in `position_manager.py` at the ATR bulk push section:
```
if open_positions:
    updates = _collect_atr_updates(open_positions)
    if updates:
        result = _execute_atr_bulk_updates(updates)
```

This means every subsequent candle cycle will re-evaluate all open positions for ATR drift and push updates automatically.

---

## Step 3: Data Fix (Optional — Do After Step 1)

The `.strip()` on token names was causing invalid API calls. Verify positions in `hermes.db` don't have whitespace:
```python
# If any token has trailing whitespace, the token = token.upper() fix
# (removing .strip()) will handle it going forward.
# Past positions that failed API calls may need re-sync from HL.
```

If any open positions have stale/wrong SL-TP values because prior API calls failed, the force script in Step 1 will correct them.

---

## Open Questions

1. Should the one-shot script run in **paper mode** first to verify no errors before touching live HL orders?
   - Default: run in paper mode (paper=True flag)
   - Optional: add `--live` flag to push to real HL

2. Do you want a summary printed of which tokens had their SL/TP changed before vs after?

---

## Files Likely to Change

| File | Change |
|---|---|
| `/root/.hermes/scripts/force_atr_update.py` | **New** — one-shot ATR force push |
| `/root/.hermes/brain/trading.md` | Log the run and results |

## Tests / Validation

```bash
# 1. Dry run (paper mode — default)
python3 /root/.hermes/scripts/force_atr_update.py

# 2. Check output matches expected SL/TP formula:
#    SL = entry * (1 - k * atr_pct)
#    TP = entry * (1 + 2 * k * atr_pct)  floored at +8%
#    where k = _atr_multiplier(atr_pct)

# 3. Verify no errors in HL order history after running
```
