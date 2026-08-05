# brain.py _params — 43 vs 44 Still Broken (2026-05-21)

## The Core Bug

SQL has 44 `%s` placeholders. `_params` tuple has 43 items. psycopg2 fires `IndexError: tuple index out of range` during `execute()`.

## Session Timeline

| Time | Event |
|------|-------|
| 2026-05-19 | Two-stage fix: removed duplicate `exp_metadata)` (44→43), added `signal_leverage` (43→44) |
| 2026-05-20 | ASTER/LTC/EIGEN fired → INSERT still failed → guardian orphan close |
| 2026-05-21 | I added `None` placeholder for flip_variant — but placed it at WRONG position |

## My Broken Fix (2026-05-21)

I replaced:
```
              trailing_phase2_dist, leverage, experiment,
              'signal-flip',  # col 24: flip_variant
              int(flipped_from_trade) if flipped_from_trade else 0,  # col 23: flipped_from_trade
```

With:
```
              trailing_phase2_dist, leverage, experiment,
              None,  # flip_variant placeholder (col 25) — was missing, causing IndexError
              int(flipped_from_trade) if flipped_from_trade else 0,
```

This placed `None` at position 22 (after experiment) instead of position 25 (after flipped_from_trade). Created a NEW shift, still 43 items.

## Actual _params Item Count (Verified by Execution)

```
Line 519: token, direction, amount_usdt, hl_entry = 4
Line 520: exchange, strategy, paper, stop_loss, target, server, 'open' = 7  → 11
Line 521: signal, confidence, None, 0.0, 0.0 = 5 → 16
Line 522: sl_distance = 1 → 17
Line 523: trailing_activation, trailing_distance = 2 → 19
Line 524: trailing_phase2_dist, leverage, experiment = 3 → 22
Line 525: None (my broken placeholder) = 1 → 23
Line 526: int(flipped_from_trade) if flipped_from_trade else 0 = 1 → 24
Line 527: hl_entry, hl_notional = 2 → 26
Line 528: hl_entry if direction == 'LONG' else 0 = 1 → 27
Line 529: hl_entry if direction == 'SHORT' else 0 = 1 → 28
Line 530: signal_z_score = 1 → 29
Line 531: signal_rsi_14, signal_macd_hist = 2 → 31
Line 532: signal_macd_value, signal_macd_signal = 2 → 33
Line 533: signal_momentum_state, signal_z_score_tier = 2 → 35
Line 534: signal_decision, signal_leverage, signal_created_at = 3 → 38
Line 535: test_sl_variant, test_timing_variant, test_trailing_variant = 3 → 41
Line 536: json.dumps(signal_metadata) ternary = 1 → 42
Line 537: _exp_metadata_str = 1 → 43
```

**43 items. SQL has 44 placeholders. DIFF = -1.**

## The Fix Needed

`brain.py` lines 519-537. The `flip_variant` (col 25) placeholder must be positioned AFTER `flipped_from_trade` (col 24):

```
trailing_phase2_dist, leverage, experiment,  # col 21, 22, 23
int(flipped_from_trade) if flipped_from_trade else 0,  # col 24: flipped_from_trade
None,  # col 25: flip_variant — THIS IS WHAT WAS MISSING
hl_entry, hl_notional,  # col 26, 27
...
```

And the count must come to 44.

## signal_compactor.py Crash (2026-05-21)

Line 843: `c.execute(sql, params, params2, params3)` — sqlite3 execute() takes at most 2 args (sql + sequence). Called with 11. TypeError: execute expected at most 2 arguments, got 11. Crashes every signal_compactor run. Hot-set never compacts. Primary pipeline blocker, separate from brain.py INSERT bug.

## decider_run.py stderr Capture Missing

Line 713: `subprocess.run(cmd, capture_output=True, text=True, timeout=30)` — capture_output captures stderr into `result.stderr` but the log only prints stdout. Brain.py exceptions go to stderr and are invisible to decider_run.

Fix: Add `stderr=subprocess.STDOUT` to subprocess.run call so brain.py exceptions appear in stdout and get logged.

## Verification Commands

```python
# Correct way to count _params: depth-tracking state machine
with open('/root/.hermes/scripts/brain.py') as f:
    content = f.read()
start = content.find('_params = (token, direction')
end = content.find('\n              )\n', start) + 3
tuple_body = content[start:end]
depth = 0; commas = 0
for ch in tuple_body[12:]:
    if ch in '([': depth += 1
    elif ch in ')]': depth -= 1
    elif ch == ',' and depth == 0: commas += 1
print(f'Items: {commas + 1}')  # Must be 44

# Confirm by actual execution
exec(open('/root/.hermes/scripts/brain.py').read().split('def add_trade')[0])
# ... set all variable values ...
print(f'_params: {len(_params)}')  # Must be 44
```