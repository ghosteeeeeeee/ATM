# ATR Debug Logging — 2026-05-15

Added comprehensive debug output to all ATR functions in `position_manager.py` and `tpsl_utils.py` to diagnose DASH/ZK SHORT SL being above entry.

## Functions Instrumented

### `_collect_atr_updates()` — position_manager.py line 1680

```python
print(f"  [ATR] {token} {direction}: k={k:.3f} ATR={atr:.4f} ({atr_pct*100:.2f}%) "
      f"→ SL={new_sl:.6f} TP={new_tp:.6f} "
      f"[anchor={_debug_sl_anchor} ref={ref_price:.6f} peak_low={_peak_low:.6f} peak_high={_peak_high:.6f} "
      f"entry={_entry:.6f} current={current_price:.6f} "
      f"state={_debug_sl_reason} is_new={is_new_trade} in_profit={_in_profit} "
      f"eff_sl={effective_sl_pct*100:.3f}% eff_tp={effective_tp_pct*100:.3f}%]"
      f" SL_entry_dist={_sl_entry_dist:.2f}%")
```

Key fields:
- `SL_entry_dist` — % distance from entry to SL. SHORT: negative = below entry (correct), positive = above entry (BUG)
- `anchor` — shows which price was used as SL reference (`ref_price(_peak_low)` for SHORT)
- `state` — NEW_TRADE / IN_PROFIT / ESTABLISHED

### `_persist_atr_levels()` — position_manager.py line 1851

```python
print(f"  [PERSIST] trade_id={trade_id} token={u.get('token')} dir={u.get('direction')} "
      f"SL_write={new_sl:.6f} TP_write={new_tp:.6f} "
      f"atr={u.get('atr')} atr_pct={u.get('atr_pct',0)*100:.2f}% k={u.get('k')} "
      f"old_sl={u.get('old_sl')} old_tp={u.get('old_tp')} "
      f"entry={u.get('entry_price')}")
```

Every DB write is logged with full context. Filter: `grep "\[PERSIST\]"`.

### `_compute_dynamic_sl()` — position_manager.py line 1423

```python
print(f"  [_dynSL] {token} {direction}: entry={entry_price:.6f} current={current_price:.6f} "
      f"ATR={atr:.4f} atr_pct={atr_pct*100:.2f}% k={k:.3f} "
      f"eff_sl={effective_sl_pct*100:.3f}% → SL={result:.6f}")
```

Also: SHORT bug-check prints SL-entry% and SL-current% distances.

### `_compute_dynamic_tp()` — position_manager.py line 1462

```python
print(f"  [_dynTP] {token} {direction}: entry={entry_price:.6f} current={current_price:.6f} "
      f"ATR={atr:.4f} atr_pct={atr_pct*100:.2f}% k={k:.3f} k_tp={k_tp:.3f} "
      f"eff_tp={effective_tp_pct*100:.3f}% → TP={result:.6f}")
```

### `tpsl_utils.compute_atr_sl_price()` — tpsl_utils.py line 92

```python
print(f"  [TPSL] compute_atr_sl_price {token} {direction}: "
      f"entry={entry_price:.6f} current={current_price:.6f} "
      f"ATR={atr:.4f} ({atr_pct*100:.2f}%) k={k:.3f} "
      f"eff_sl={effective_sl_pct*100:.3f}% → SL={result:.6f}")
```

Also: SHORT bug-check prints SL-entry% distance.

### Main loop — position_manager.py line 2452

```python
else:
    print(f"  [ATR] HL orders DISABLED — SL/TP managed locally by guardian via DB")
```

Confirms HL orders are disabled every cycle.

## Reading the Logs

```bash
# Filter ATR updates for all tokens
grep "\[ATR\]" /root/.hermes/logs/position_manager.log | grep -v "HL orders DISABLED"

# Filter specific token (ZK SHORT)
grep "\[ATR\].*ZK.*SHORT" /root/.hermes/logs/position_manager.log

# Filter persist writes
grep "\[PERSIST\]" /root/.hermes/logs/position_manager.log

# Find SHORT SL above entry (positive SL_entry_dist)
grep "\[ATR\].*SHORT" /root/.hermes/logs/position_manager.log | awk '$NF ~ /%$/ {gsub(/%/,"",$NF); if($NF+0 > 0) print}'

# Check HL orders disabled confirmation
grep "HL orders DISABLED" /root/.hermes/logs/position_manager.log
```

## What to Look For

1. **SHORT with SL_entry_dist > 0** — bug still active, SL is above entry
2. **anchor=ref_price(_peak_low)** for SHORT — confirms ref_price anchor used (correct after fix)
3. **anchor=_entry** for in-profit SHORT — bug still active (pre-fix state)
4. **[PERSIST]** missing for a token — position_manager not writing SL/TP to DB for that trade
5. **Two different k values in same ATR log** — `_collect_atr_updates` and `_compute_dynamic_sl` using different k paths (confirm `_compute_dynamic_sl` is dead code)

## Verification After Fix

After the fix (ref_price for ALL SHORT states), running the diagnostic query should show:

```python
# DASH SHORT — SL should now be BELOW entry (negative SL_entry_dist)
# ZK SHORT — SL should now be BELOW entry (negative SL_entry_dist)
# If still positive → fix not applied or position_manager not running
```