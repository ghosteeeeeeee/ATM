# Loss Cooldown Debugging Reference

## How It Works
- Per-token+direction (BSV LONG ≠ BSV SHORT)
- Incremental: streak=1 → 10min, streak=2 → 20min, streak=3 → 40min (capped at MAX)
- Formula: `hours = min(BASE * 2^(streak-1), MAX)` where BASE=10/60, MAX=40/60

## Key Files
- `/root/.hermes/data/loss_cooldowns.json` — live cooldown state (streak, hours_remaining)
- `position_manager.py`: `set_loss_cooldown()` (line ~2904), `is_loss_cooldown_active()` (line ~2841)
- `signal_compactor.py`: uses `is_loss_cooldown_active()` to filter hot-set entries
- `signal_schema.py`: `_is_loss_cooldown_active()` reads JSON file

## Verify It's Working
```bash
# Journalctl logs — shows streak bumps
journalctl -u hermes-pipeline --no-pager | grep "LOSS COOLDOWN" | tail -20

# JSON state
cat /root/.hermes/data/loss_cooldowns.json | python3 -m json.tool
```

## Important: Loss Cooldown NOT in ATR Close Path
`check_atr_tp_sl_hits()` does NOT call `is_loss_cooldown_active()`. The loss cooldown only blocks NEW entries in signal_compactor. ATR SL fires independently.

When a position closes via ATR SL → `close_paper_position()` → `_close_trade_internal()` → `set_loss_cooldown()`. The close event sets the streak based on the current value in loss_cooldowns.json.

## Streak Bump Logic
If a token has streak=1 and hits another loss → becomes streak=2 (20min). No streak=1 entry in journal is required — if the prior loss set streak=1 and then a new loss occurs before the cooldown expired, it bumps to 2 in one step.

## Common Bugs
1. **WR filter reads wrong DB** — `_get_token_wr` in signal_compactor reads PostgreSQL which is empty post-archive. Should read archive SQLite at `/root/.hermes/archive/trades_analysis.db`.
2. **cascade_flip.py import crash** — `cascade_flip.py` imports `RUNTIME_DB`, `FLIP_COUNTS_FILE`, `LOSS_COOLDOWN_FILE` from `hermes_constants` but they weren't defined there. Fixed by adding to `hermes_constants.py` lines 4-18.
3. **signal_schema.py imports from paths.py** — not from hermes_constants. Uses `LOSS_COOLDOWN_FILE` from paths.py. Two separate sources.