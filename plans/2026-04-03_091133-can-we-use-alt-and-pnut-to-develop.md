# Plan: Speed-Armed Cascade Flip System

**Date:** 2026-04-03
**Context:** ALT and PNUT trades were opened via unauthorized confluence bypass. We are on the wrong side of both trades. Speed is increasing (tokens moving against us). We want to build a speed-armed cascade flip system that flips losing positions proactively, using HL's native reverse-order capability.
**Status:** PLANNING ONLY — do not execute

---

## Goal

Implement a speed-armed cascade flip system where:

1. **Armed state:** Position is losing AND speed is increasing → system is "armed" (not yet flipping)
2. **Flip trigger:** Position hits ≥1% loss AND armed → execute cascade flip via HL reverse order
3. **Post-flip trailing:** After flip, trailing stop monitors at **0.5% in the new direction** (opposite of original)
4. **Flip limit:** Max **3 flips per token** (including the original entry = 4 total directional commitments max)

---

## Current System (what exists)

### Cascade Flip (already implemented)
- `CASCADE_FLIP_MIN_LOSS = -0.5%` — fires at 0.5% loss (NO speed check, NO armed state)
- `CASCADE_FLIP_MIN_CONF = 70.0` — opposite signal must have ≥70% confidence
- `CASCADE_FLIP_MAX_AGE_M = 15` — opposite signal must be <15 min old
- `cascade_flip()` at line 1493: closes position, then calls `place_market_order()` for new direction
- **Problem:** No speed check, no armed state, no 1% hard trigger, uses separate close+open (not HL reverse)

### SpeedTracker (already implemented)
- `speed_tracker.py` — tracks per-token velocity and speed percentile
- `speed_tracker.get_speed(token)` returns `(speed, percentile)`
- Higher percentile = more momentum

---

## What Needs to Change

### 1. New Constants (position_manager.py, near line 83)

```python
# Speed-armed cascade flip
CASCADE_FLIP_ARM_LOSS     = -0.5   # Loss % at which system ARMED (speed check triggers)
CASCADE_FLIP_TRIGGER_LOSS = -1.0   # Loss % at which system FLIPS (if armed)
CASCADE_FLIP_MAX          = 3      # Max flips per token (original entry = 1, flip 1 = 2, etc.)
                                       # After 3 flips, cascade flip is permanently disabled for that token
CASCADE_FLIP_POST_TRAIL_PCT = 0.5  # After a flip, trailing SL window is 0.5% (tight)
                                       # Override default TRAILING_SL_WINDOW during post-flip monitoring
```

### 2. Track Flip Count Per Token

Need to persist `flip_count` per token so it survives across pipeline runs.

**Option A — Brain DB:** Add `flip_count` column to brain `positions` table.
**Option B — File:** Store in `/var/www/hermes/data/flip_counts.json`.
**Option C — In-memory:** Only track within session, reset on restart (not durable).

**Recommendation: Option B (file)** — simpler than schema migration, survives restarts.

```python
FLIP_COUNTS_FILE = '/var/www/hermes/data/flip_counts.json'
```

Schema:
```json
{
  "ALT": {"flips": 1, "last_flip_dir": "SHORT", "last_flip_time": "2026-04-03T09:11:00"},
  "PNUT": {"flips": 0, "last_flip_dir": null, "last_flip_time": null}
}
```

Read/write with `json.load()` + `json.dump()` — not high frequency, simple is fine.

### 3. Speed Check in `check_cascade_flip()`

Modify `check_cascade_flip()` signature and logic:

```python
def check_cascade_flip(token: str, position_direction: str,
                      live_pnl: float, speed_tracker=None) -> Optional[Dict]:
```

**New logic:**
```
IF live_pnl > CASCADE_FLIP_ARM_LOSS:
    return None  # Not even armed yet

IF live_pnl < CASCADE_FLIP_TRIGGER_LOSS:
    # Hit the hard trigger — check if armed
    IF speed_increasing(token, speed_tracker):
        return flip_info  # ARMED + TRIGGERED → proceed with flip
    ELSE:
        return None  # Not armed, don't flip

ELSE:
    # Between -0.5% and -1.0% — armed but not triggered yet
    IF speed_increasing(token, speed_tracker):
        log(f"  [CASCADE ARMED] {token} armed for flip (loss={live_pnl:+.2f}%, speed rising)")
    return None  # Armed but haven't hit trigger yet
```

**Speed increasing check:**
```python
def _speed_increasing(token: str, speed_tracker) -> bool:
    if speed_tracker is None:
        return True  # If no speed data, allow flip (fail open)
    try:
        speed, percentile = speed_tracker.get_speed(token)
        # Speed is "increasing" if percentile is high (top 50%) — token has momentum
        return percentile >= 50.0
    except Exception:
        return True  # Fail open
```

### 4. Use HL Reverse Order Instead of Separate Close+Open

The current `cascade_flip()` does:
1. `close_paper_position(trade_id, ...)` — closes
2. `place_market_order(...)` — opens new direction

This is two separate operations. If the market moves between them, you could end up with an unintended position or no position at all.

**Hyperliquid supports "reduce-only + reverse" order semantics** — or use `close_position()` then immediately `place_order()` with `side='Buy'/'Sell'` for the new direction.

**Check `hyperliquid_exchange.py` for reverse order support:**

Look at `close_position()` at line 502:
```python
def close_position(name, slippage=0.02):
    # Closes by placing order in opposite direction with full size
```

For a true reverse (close + open atomically), we need to use the `sz` (size) from the closing order to immediately place the opening order. Hyperliquid supports `closePx` field or we can fetch position size.

**Proposed approach in `cascade_flip()`:**
```python
# 1. Get current position size
position = get_position_from_hl(token)
if not position:
    return False
size = position['sz']

# 2. Close with reduce-only order (or close_position which does this)
close_ok = close_paper_position(trade_id, f"cascade_flip_{live_pnl:+.2f}%")
if not close_ok:
    return False

# 3. Immediately open opposite direction with same size
# (Hyperliquid doesn't support true atomic reverse, but close→open within
# the same API call frame minimizes slippage risk)
ok = place_market_order(
    token=token,
    direction=opposite_dir,
    entry_price=current_price,
    confidence=conf,
    source=f"cascade-{source}",
    trade_id=None,
)
```

**Note:** Hyperliquid's `close_position()` uses the full position size and closes by placing an order in the opposite direction. The new entry should use similar sizing. Using `sz` from HL directly is better than calculating from notional.

### 5. Post-Flip Trailing Stop Tightening

After a cascade flip, the trailing SL window should be **0.5% instead of the default**.

**Approach:** Store a `post_flip_until_price` or a `tight_trailing` flag in the position dict or a side-channel.

In `should_use_trailing_stop()`, after a flip:
```python
# If this position was entered via cascade flip, use tighter trailing window
was_flipped = (source and source.startswith('cascade-'))
if was_flipped:
    return live_pnl <= -0.5  # 0.5% adverse move triggers trail
else:
    return live_pnl <= -(TRAILING_SL_WINDOW or 1.0)
```

Or track it in the brain DB `trades` table via a `flipped_from` column.

**Simpler approach:** The `source` field in `place_market_order()` is `cascade-{original_source}`. Check this in `should_use_trailing_stop()`:
```python
position_source = position.get('source', '') or ''
if 'cascade-' in position_source:
    # Post-flip position — use tighter trailing window
    return live_pnl <= -0.5
```

### 6. Flip Count Enforcement

Before executing a cascade flip:
```python
flip_counts = _load_flip_counts()
current_flips = flip_counts.get(token.upper(), {}).get('flips', 0)
if current_flips >= CASCADE_FLIP_MAX:
    log(f"  [CASCADE FLIP] ❌ {token} hit max flips ({CASCADE_FLIP_MAX}) — skipping")
    return False
```

After successful flip:
```python
flip_counts[token.upper()] = {
    'flips': current_flips + 1,
    'last_flip_dir': opposite_dir,
    'last_flip_time': datetime.now().isoformat(),
}
_save_flip_counts(flip_counts)
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `/root/.hermes/scripts/position_manager.py` | New constants, `check_cascade_flip()` speed logic, `cascade_flip()` HL reverse, flip count enforcement, post-flip trailing |
| `/root/.hermes/scripts/hyperliquid_exchange.py` | Add `place_market_order()` wrapper (currently referenced but missing — import from wherever it's defined, or create stub) |
| `/root/.hermes/scripts/brain.py` | Optionally add `flip_count` column to brain `positions` table (if using DB approach) |

---

## Step-by-Step Implementation Plan

### Step 1: Verify `place_market_order` exists
Search the codebase for `def place_market_order`. It's imported in `cascade_flip()` at line 1517 but not defined in `hyperliquid_exchange.py`. Find the actual module that has it.

### Step 2: Add constants to position_manager.py
Add near line 83:
- `CASCADE_FLIP_ARM_LOSS = -0.5`
- `CASCADE_FLIP_TRIGGER_LOSS = -1.0`
- `CASCADE_FLIP_MAX = 3`
- `CASCADE_FLIP_POST_TRAIL_PCT = 0.5`
- `FLIP_COUNTS_FILE = '/var/www/hermes/data/flip_counts.json'`

### Step 3: Add flip count persistence helpers
```python
def _load_flip_counts() -> dict:
    if os.path.exists(FLIP_COUNTS_FILE):
        with open(FLIP_COUNTS_FILE) as f:
            return json.load(f)
    return {}

def _save_flip_counts(counts: dict):
    os.makedirs(os.path.dirname(FLIP_COUNTS_FILE), exist_ok=True)
    with open(FLIP_COUNTS_FILE, 'w') as f:
        json.dump(counts, f, indent=2)
```

### Step 4: Add `_speed_increasing()` helper
Check speed percentile >= 50 as the "increasing" threshold.

### Step 5: Rewrite `check_cascade_flip()`
Update signature to accept `speed_tracker=None`. Add armed/triggered state machine:
- `-0.5% > pnl`: not armed yet
- `-1.0% <= pnl < -0.5%`: armed (speed check → log armed state)
- `pnl <= -1.0%` AND speed increasing: triggered → return flip_info
- `pnl <= -1.0%` AND NOT speed increasing: don't flip

### Step 6: Update `should_manage_position()` call site
Pass `speed_tracker` into `check_cascade_flip()`:
```python
flip_info = check_cascade_flip(token, direction, live_pnl, speed_tracker)
```

### Step 7: Update `cascade_flip()`
- Add flip count check at entry
- Increment flip count on success
- Use `cascade-reverse-{source}` as source string for post-flip trailing detection
- Ensure `place_market_order` is correctly imported

### Step 8: Update `should_use_trailing_stop()`
Check if position source contains `cascade-` → use 0.5% instead of default window.

### Step 9: Validate with ALT and PNUT
- Check current flip counts for ALT and PNUT (should both be 0)
- Check current speed percentile for both
- Manually trigger a test cycle to verify armed state logs

---

## Validation / Testing

1. **Simulate ALT at -0.6% loss with rising speed:**
   - Verify "ARMED" log message appears
   - Verify NO flip fires yet
2. **Simulate ALT at -1.0% loss with rising speed:**
   - Verify flip executes
   - Verify flip count increments to 1
   - Verify new position is opposite direction
3. **Simulate ALT after 3rd flip:**
   - Verify flip is blocked with "max flips" message
4. **Post-flip trailing:**
   - Open ALT LONG via cascade flip
   - Verify trailing SL triggers at -0.5% (not default 1.0%)

---

## Open Questions

1. **Where is `place_market_order()` defined?** It's imported at line 1517 of position_manager.py but not found in hyperliquid_exchange.py or any other scripts file. Need to find before implementing.

2. **Sizing on reverse:** Should the new position use the same size (notional) as the closed position, or recalculate based on confidence? Current `cascade_flip()` doesn't specify size — it relies on `place_market_order()` default. Need to verify what default is.

3. **What is "speed increasing"?** Is it `percentile >= 50`, or should we compare current vs previous speed (delta)? Current SpeedTracker tracks percentile — using delta would require comparing against last run's value. Using absolute percentile >= 50 is simpler and consistent with "token has momentum."

4. **Should we also check HL's native trailing stop feature?** Hyperliquid supports native trailing stop orders. Using native instead of brain-computed trailing would be more reliable. Investigate `place_order(..., order_type='Trigger', ...)` for trailing.
