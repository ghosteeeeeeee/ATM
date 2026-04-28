---
name: cascade-flip-debug
description: Debug why cascade flip isn't firing for a losing position — trace state machine, check thresholds, find blockers
---

# Cascade Flip Debug — SKILL.md

## When to Use
Cascade flip not firing for a losing position. Position is down but no flip executes.
Signal is wrong direction but system doesn't flip.

## Diagnostic Steps

### Step 1 — Check position state
```bash
cat /var/www/hermes/data/trades.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
open_trades = d.get('open',[])
coin = 'LINK'  # replace with token
pos=[x for x in open_trades if coin in x.get('coin','')]
print(json.dumps(pos,indent=2))
"
```
Key fields: `pnl_pct`, `direction`, `trailing_sl`, `signal`, `opened`

### Step 2 — Check cascade flip thresholds
```bash
grep -n "CASCADE_FLIP_ARM\|CASCADE_FLIP_TRIGGER\|CASCADE_FLIP_HF\|trailing_active\|MIN_TYPES\|MIN_CONF" \
  /root/.hermes/scripts/position_manager.py | head -20
```

Key thresholds (as of 2026-04-22):
- `CASCADE_FLIP_ARM_LOSS`: -0.10% — armed at this loss
- `CASCADE_FLIP_TRIGGER_LOSS`: -0.15% — flip fires
- `CASCADE_FLIP_HF_TRIGGER_LOSS`: -0.15% — fast flip (high momentum)
- `trailing_active`: must be False for flip to fire

### Step 3 — Understand the state machine
Location: `scripts/position_manager.py`, `check_cascade_flip()` around line 2650

Flow:
1. `pnl > ARM_LOSS` → not armed, return None
2. `flips >= CASCADE_FLIP_MAX` → at max, skip
3. `speed_increasing == False` → armed but waiting
4. `pnl > trigger_pct` → armed, waiting
5. **Signal check** → was: required DB signal in opposite direction with conf >= 60%
   - Now (2026-04-22): momentum-based only (regime_conf >= 20%)

### Step 4 — Check speed/momentum
Speed tracker: `speed_percentile` must be >= 50 for `_speed_increasing()` to return True.
Use `speed_tracker.get_token_speed(token)` — returns dict with `price_velocity_5m`, `price_acceleration`.

### Step 5 — Common failure modes
| Symptom | Cause | Fix |
|---|---|---|
| "CASCADE ARMED" logged, no flip | `pnl > trigger_pct` — waiting to hit loss threshold | Lower `CASCADE_FLIP_TRIGGER_LOSS` |
| No "CASCADE ARMED" log | `pnl > ARM_LOSS` — not even armed yet | Lower `CASCADE_FLIP_ARM_LOSS` |
| "speed not increasing" | speed_percentile < 50 | Check speed tracker data |
| "no opposite confluence" | Old code required opposing signal | Remove signal check, use momentum-only |
| `trailing_sl` not null | Trailing active blocks cascade flip | Wait for trailing to expire or disable |

## Key Code Locations
- `check_cascade_flip()`: line ~2650, `scripts/position_manager.py`
- Cascade constants: lines ~80-111, `scripts/position_manager.py`
- `_speed_increasing()`: line ~175, `scripts/position_manager.py`
- `cascade_flip()`: `scripts/cascade_flip.py`

## Fix Applied 2026-04-22
- ARM_LOSS: -0.25% → -0.10%
- TRIGGER_LOSS: -0.50% → -0.15%
- HF_TRIGGER_LOSS: -0.35% → -0.15%
- Signal requirement: **removed** — now flips on momentum alone (regime_conf >= 20%)
- Removed DB signal query entirely — use `speed_tracker.get_token_speed()` instead
