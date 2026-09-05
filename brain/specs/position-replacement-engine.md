# Position Replacement Engine — Design Spec

## Overview

Dynamic portfolio management system that continuously upgrades open positions by comparing their R:R against new opportunities. When a new signal has significantly better R:R than the worst open position, the system swaps them.

**Core principle:** Always hold the N best opportunities. Don't let capital sit in degrading setups when better ones exist.

---

## Architecture

```
Pipeline Cycle
    │
    ├── risk_reward_engine.evaluate_rr() → open position R:R
    │
    ├── risk_reward_engine.evaluate_rr() → new signal R:R
    │
    └── replacement_engine.evaluate()
            │
            ├── Compare R:R (new vs worst open)
            │
            ├── IF new_R:R > worst_R:R × REPLACEMENT_MULTIPLIER:
            │     ├── Close worst position (cut_loser or position_manager)
            │     └── Execute new signal (decider_run)
            │
            └── Log: [REPLACEMENT] TOKEN closed (R:R 0.5) → NEW_TOKEN opened (R:R 3.5)
```

---

## Key Parameters (hermes_constants.py)

```python
# ── Position Replacement Engine ──────────────────────────────────────────────
REPLACEMENT_ENABLED = True
REPLACEMENT_MULTIPLIER = 1.5        # new R:R must be 1.5x (50%) better than worst
REPLACEMENT_MAX_SWAPS_PER_HOUR = 2  # prevent churning
REPLACEMENT_COOLDOWN_MIN = 30       # minutes before same token can be re-entered
REPLACEMENT_MIN_OPEN_AGE_SEC = 300  # don't swap positions < 5 minutes old
REPLACEMENT_FEE_ESTIMATE_PCT = 0.06 # estimated round-trip fee (0.03% × 2)
REPLACEMENT_MIN_RR_IMPROVEMENT = 0.5 # minimum absolute R:R improvement (e.g., 0.5 → 1.0)
```

---

## R:R Calculation

### For Open Positions

Use `risk_reward_engine.evaluate_rr(token, direction, current_price)`:
- Finds nearest S/R levels from candle swings + liquidation clusters
- Computes SL = nearest opposing S/R level
- Computes TP = nearest supporting S/R level (in trade direction)
- Returns: `rr_ratio = distance_to_tp / distance_to_sl`

**Edge cases:**
- Position in profit: use current price as entry, compute forward R:R
- Position at breakeven: same as above
- Position in loss: the R:R reflects remaining opportunity from current price

### For New Signals

Use the R:R already computed by `entry_gates.rr_gate()` at signal generation time.
- Store `rr_ratio` in signal metadata during compaction
- At replacement evaluation, compare stored R:R against open position R:R

---

## Replacement Logic

### Pseudocode

```python
def evaluate_replacement(open_positions, new_signals):
    """Evaluate whether any open position should be replaced by a new signal."""
    
    if not REPLACEMENT_ENABLED:
        return []
    
    # 1. Check swap rate limit
    swaps_this_hour = get_swaps_in_last_hour()
    if swaps_this_hour >= REPLACEMENT_MAX_SWAPS_PER_HOUR:
        return []
    
    # 2. Compute R:R for all open positions
    position_rr = []
    for pos in open_positions:
        if time.time() - pos.opened_at < REPLACEMENT_MIN_OPEN_AGE_SEC:
            continue  # skip recently opened positions
        rr = evaluate_rr(pos.token, pos.direction, pos.current_price)
        if rr is not None:
            position_rr.append((pos, rr))
    
    if not position_rr:
        return []
    
    # 3. Find worst open position (lowest R:R)
    worst_pos, worst_rr = min(position_rr, key=lambda x: x[1])
    
    # 4. Compute R:R for new signals
    signal_rr = []
    for sig in new_signals:
        if sig.token in [p.token for p in open_positions]:
            continue  # skip if already have this token open
        if sig.rr_ratio is None:
            continue
        signal_rr.append((sig, sig.rr_ratio))
    
    if not signal_rr:
        return []
    
    # 5. Find best new signal (highest R:R)
    best_sig, best_rr = max(signal_rr, key=lambda x: x[1])
    
    # 6. Check if replacement is justified
    rr_ratio = best_rr / worst_rr if worst_rr > 0 else float('inf')
    absolute_improvement = best_rr - worst_rr
    
    # Account for fees
    fee_adjusted_improvement = absolute_improvement - REPLACEMENT_FEE_ESTIMATE_PCT
    
    if rr_ratio >= REPLACEMENT_MULTIPLIER and fee_adjusted_improvement >= REPLACEMENT_MIN_RR_IMPROVEMENT:
        return [Replacement(worst_pos, best_sig, reason=f"R:R {worst_rr:.2f} → {best_rr:.2f} ({rr_ratio:.1f}x)")]
    
    return []
```

---

## Safety Guards

### 1. Swap Rate Limit
- Max 2 swaps per hour per portfolio
- Prevents churning during volatile markets

### 2. Position Age Filter
- Don't swap positions younger than 5 minutes
- Gives trades time to develop before replacement

### 3. Token Cooldown
- After closing a token, don't re-enter for 30 minutes
- Prevents whipsaw (close → re-open → close → re-open)

### 4. Fee Awareness
- Estimate round-trip fees (0.06%)
- Only swap if R:R improvement exceeds fees

### 5. Crash Protection Integration
- Don't swap during BTC crashes (use btc_crash_filter)
- Swapping during cascades = selling losers at worst prices

### 6. Directional Cap Integration
- New entry must respect DIRECTIONAL_CAP_MAX_PCT
- Can't swap LONG→SHORT if it would exceed cap

---

## What Gets Stored

### Signal Metadata
```json
{
  "token": "SOL",
  "direction": "LONG",
  "rr_ratio": 3.5,
  "rr_score": 85,
  "rr_grade": "A",
  "rr_tp_source": "structural_sr",
  "rr_sl_source": "atr_floor"
}
```

### Position Tracking
```json
{
  "token": "YGG",
  "direction": "LONG",
  "entry_price": 0.0229,
  "current_rr": 0.5,
  "rr_history": [
    {"ts": 1756985000, "rr": 2.1},
    {"ts": 1756985300, "rr": 1.4},
    {"ts": 1756985600, "rr": 0.5}
  ],
  "replaced_at": null,
  "replacement_reason": null
}
```

---

## Integration Points

| System | Integration |
|--------|------------|
| `risk_reward_engine.py` | Computes R:R for both open positions and new signals |
| `entry_gates.py` | Stores `rr_ratio` in signal metadata at generation time |
| `signal_compactor.py` | Passes R:R to hotset for comparison |
| `position_manager.py` | Executes the swap (close old + open new) |
| `cut_loser.py` | Handles the close leg of the swap |
| `btc_crash_filter.py` | Blocks swaps during crashes |
| `hermes_constants.py` | All parameters defined here |

---

## Expected Impact

### Scenario: Regime Transition
```
Before: 5 LONG positions, all losing R:R (0.3, 0.5, 0.7, 0.8, 1.2)
        System holds all 5 until SL triggers → all lose

After:   Cycle through positions, replacing worst with best new signals
         Position 1 (R:R 0.3) → replaced by SHORT (R:R 2.8)
         Position 2 (R:R 0.5) → replaced by SHORT (R:R 2.1)
         System adapts to new direction automatically
```

### Scenario: Winner Degradation
```
Before: BCH LONG at +13.4% but R:R dropped to 0.8 (near resistance)
        System holds until trailing stop → gives back gains

After:   BCH R:R degrades → new signal with R:R 3.5 available
         System swaps BCH for new signal
         Locks in gains + enters better opportunity
```

---

## Open Questions

1. **Should the replacement be immediate or queued?** (Immediate = close + open in same cycle. Queued = queue the swap for next cycle.)

2. **What if the new signal is same direction as the old one?** (e.g., replace LONG YGG with LONG SOL — is that worth the fees?)

3. **How to handle partial R:R degradation?** (Position went from R:R 2.0 to R:R 1.0 — not the worst, but declining. Should it be replaced?)

4. **Should we track R:R history?** (If a position's R:R has been declining for 3+ cycles, that's a stronger signal to replace.)

5. **Integration with trailing stops?** (If trailing is active, do we close at trail floor or current price?)
