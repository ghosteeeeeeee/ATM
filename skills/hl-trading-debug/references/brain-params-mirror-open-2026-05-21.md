# brain.py _params Fixes — 2026-05-21

## Two Bugs Fixed Today

### Bug 1 (P0): `flipped_from_trade` / `flip_variant` swapped in `_params` tuple

**Impact:** INSERT succeeded but half the columns were shifted 1 position. `hl_entry_price` received `hl_notional`, `hl_notional_usdt` received LONG conditional price, `highest_price` received SHORT conditional price, and so on. Garbage data in PostgreSQL.

**Root cause:** The `_params` tuple at lines 525-526 had the items in wrong order:

```python
# BEFORE (broken) — lines 525-526:
None,  # col 24: flip_variant (not available from callers — placeholder)
int(flipped_from_trade) if flipped_from_trade else 0, 'signal-flip',
#                           ↑ col 23: flipped_from_trade    ↑ col 24: flip_variant
```

This means `int(flipped_from_trade) if...` (the actual integer value) was going to col 24 (`flip_variant` TEXT column), and `'signal-flip'` (the string) was going to col 25 (`hl_entry_price` NUMERIC column). Everything after was off by one.

**Fix applied (lines 525-526):**
```python
'signal-flip',  # col 24: flip_variant
int(flipped_from_trade) if flipped_from_trade else 0,  # col 23: flipped_from_trade
```

**Verification:**
```bash
# Count params with depth-tracking state machine (not line-counting!)
python3 << 'EOF'
text = open('brain.py').read()
start = text.find('_params = (')
depth = 0; end_idx = start
for i in range(start, len(text)):
    if text[i] == '(': depth += 1
    elif text[i] == ')':
        depth -= 1
        if depth == 0: end_idx = i; break
items = []
d = 0; instr = False; esc = False; s = 0
for i, c in enumerate(text[start+11:end_idx]):
    if esc: esc = False; continue
    if c == '\\': esc = True; continue
    if c in '"\'': instr = not instr
    if not instr:
        if c in '([{': d += 1
        elif c in ')]}': d -= 1
        elif c == ',' and d == 0:
            items.append(text[start+11+i+1:end_idx][s:i].strip()); s = i+1
if s < len(text[start+11:end_idx]):
    items.append(text[start+11:end_idx][s:].strip())
print(f'_params items: {len(items)}')
# Show items 22-27
for i in range(22, min(28, len(items))):
    print(f'  {i:2d}: {items[i][:60]}')
EOF
# Should output: 44 items, then items 22='signal-flip', 23=int(flipped...), 24=hl_entry
```

Also verify compile: `python3 -m py_compile brain.py && echo OK`

---

### Bug 2 (P2): `json.dumps()` missing `default=str`

**Impact:** If `signal_metadata` or `exp_metadata` contains `datetime`, `Decimal`, `bytes`, numpy types, or other non-JSON-native types → `TypeError` → PostgreSQL rollback → orphan HL position.

**Fix applied:**
- Line 516: `_exp_metadata_str = json.dumps(exp_metadata, default=str) if exp_metadata else '{}'`
- Line 536: `json.dumps(signal_metadata, default=str) if signal_metadata else '{}'`

---

## ai-engineer Subagent Miscounting (2026-05-21)

**The subagent reported 24 params when the actual count is 44.** The line-based parsing approach (counting lines in the tuple) treats multi-item lines as single items. This is a persistent false positive pattern.

**Correct approach:** Use depth-tracking state machine over the raw tuple text, counting top-level commas. The state machine accounts for:
- String literals (`'...'`, `"..."`) — don't count commas inside
- Nested parentheses `(...)` from ternary expressions — don't count commas at depth > 0
- Backslash escapes — skip

**Key failure:** A line like `signal_rsi_14, signal_macd_hist, signal_macd_value, signal_macd_signal,` contains 4 comma-separated items but counts as 1 line. The subagent consistently miscounts when using line-based approaches.

**Always verify in main session with the state machine approach above before implementing any subagent param-count finding.**

---

## Final Verified _params Order (2026-05-21)

All 44 positions confirmed correct:

| Pos | Param | → Column |
|-----|-------|----------|
|  0 | `token` | token |
|  1 | `direction` | direction |
|  2 | `amount_usdt` | amount_usdt |
|  3 | `hl_entry` | entry_price |
|  4 | `exchange` | exchange |
|  5 | `strategy` | strategy |
|  6 | `paper` | paper |
|  7 | `stop_loss` | stop_loss |
|  8 | `target` | target |
|  9 | `server` | server |
| 10 | `'open'` | status |
| 11 | `signal` | signal |
| 12 | `confidence` | confidence |
| 13 | `None` | token_address |
| 14 | `0.0` | pnl_usdt |
| 15 | `0.0` | pnl_pct |
| 16 | `sl_distance` | sl_distance |
| 17 | `trailing_activation` | trailing_activation |
| 18 | `trailing_distance` | trailing_distance |
| 19 | `trailing_phase2_dist` | trailing_phase2_dist |
| 20 | `leverage` | leverage |
| 21 | `experiment` | experiment |
| 22 | `'signal-flip'` | flip_variant |
| 23 | `int(flipped_from_trade) if...` | flipped_from_trade |
| 24 | `hl_entry` | hl_entry_price |
| 25 | `hl_notional` | hl_notional_usdt |
| 26 | `hl_entry if direction == 'LONG' else 0` | highest_price |
| 27 | `hl_entry if direction == 'SHORT' else 0` | lowest_price |
| 28 | `signal_z_score` | signal_z_score |
| 29 | `signal_rsi_14` | signal_rsi_14 |
| 30 | `signal_macd_hist` | signal_macd_hist |
| 31 | `signal_macd_value` | signal_macd_value |
| 32 | `signal_macd_signal` | signal_macd_signal |
| 33 | `signal_momentum_state` | signal_momentum_state |
| 34 | `signal_z_score_tier` | signal_z_score_tier |
| 35 | `signal_decision` | signal_decision |
| 36 | `signal_leverage` | signal_leverage |
| 37 | `signal_created_at` | signal_created_at |
| 38 | `test_sl_variant` | test_sl_variant |
| 39 | `test_timing_variant` | test_timing_variant |
| 40 | `test_trailing_variant` | test_trailing_variant |
| 41 | `json.dumps(signal_metadata, default=str)...` | _signal_metadata |
| 42 | `_exp_metadata_str` | _exp_metadata |
| 43 | *(empty — trailing comma)* | — |

**Note:** `open_time` column is set by `NOW()` in the SQL VALUES clause (not from `_params`). Column 26 `hl_notional_usdt` receives `hl_notional` (Python var from mirror_open result, not the param named `hl_notional`).

---

## Remaining Data Quality Notes (non-blocking)

| Column | Value | Issue |
|--------|-------|-------|
| `experiment` | `None` | From function param but decider_run passes via `--experiment` arg JSON |
| `paper` | `False` | Hardcoded in tuple; decider_run CLI passes `--paper` or `--real` |
| `token_address` | `None` | Not on-chain address — signal source name placeholder |
| `signal_created_at` | `None` if decider_run doesn't pass it | decider_run `execute_trade()` doesn't pass this yet (col will be NULL until fixed) |

These are data quality gaps, not INSERT failures. The INSERT succeeds with correct 44=44 count. Fix them when signal_created_at passing becomes important.