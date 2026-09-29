# Thesis Validation System (TVS) — Spec v2

## Problem Statement

The system generates 350+ signals per day but executes only 5 (98.6% expiry rate). Signals that validate their thesis (price moves in predicted direction) are treated as fresh starts on re-entry — no memory of past success. Cooldowns block re-entry even when the setup has improved.

**Data-driven motivation:** 82% of SHORT signals and 84% of LONG signals have MFE > 0 (price moved in predicted direction at some point). The system is right most of the time but doesn't leverage this on re-entry.

## Solution: Thesis Validation Score (TVS)

### Core Concept
Track whether each signal's thesis validated (price moved in predicted direction). Use this history to:
- Boost score for re-entries after validated thesis
- Override cooldowns when setup improves
- Rank signals by thesis quality

**What TVS does NOT override:** RSI blocks, blacklist blocks, volatility gate blocks, RR hard blocks, Hall of Shame. These are hard safety filters.

### Data Model

#### signal_outcomes table (existing, extend)
Add columns:
- `thesis_validated` INTEGER — 1 if MFE > 0 (price moved in predicted direction), 0 if MFE <= 0, NULL if MFE unknown
- `thesis_mfe` REAL — Max favorable excursion % (how much thesis validated)

**No new table needed.** The existing `signal_outcomes` table already tracks token, direction, signal_type, is_win, pnl, regime. Adding thesis columns keeps everything in one place.

### Score Formula Addition

Add `thesis_validation_mult` to the score formula in `signal_compactor.py` line 1955:

```
final_score = ... * thesis_validation_mult * ...
```

#### _get_thesis_history() — Core lookup function

```python
def _get_thesis_history(token, direction, signal_type, lookback_trades=5):
    """
    Look up thesis validation history for token+direction+signal_type.
    
    Returns: dict with 'validated' (bool), 'mfe' (float), 'count' (int), 'validated_pct' (float)
    
    Lookback: last 5 trades for this exact token+direction+signal_type combination.
    If no history: returns None (neutral multiplier).
    """
    # Query signal_outcomes for last 5 trades matching token+direction+signal_type
    # where thesis_validated IS NOT NULL
    # Compute: validated_pct = sum(validated) / count
    # Return: {'validated': validated_pct > 0.5, 'mfe': avg_mfe, 'count': n, 'validated_pct': validated_pct}
```

#### Score multiplier logic

| History | Multiplier | Rationale |
|---------|-----------|-----------|
| No history | 1.0 | Neutral — first signal for this combo |
| >50% thesis validated (last 5 trades) | **1.15** | Previous signals confirmed direction |
| >80% thesis validated + avg MFE > 2% | **1.25** | Strong pattern — validated multiple times |
| >50% thesis invalidated | **0.85** | Pattern broken — reduce priority |
| MFE unknown (None) | 1.0 | Neutral — don't penalize missing data |

**Note:** Reduced from 1.4x to 1.25x max. Thesis validation (price briefly moved) is a weaker signal than R:R quality (1.30x boost). Don't give thesis validation disproportionate power.

### Cooldown Override Rules

In `signal_compactor.py` where cooldowns are checked (line ~2929):

```python
if _is_loss_cooldown_active(token, direction):
    # Check thesis history
    thesis = _get_thesis_history(token, direction, source)
    if (thesis and thesis['validated'] and thesis['count'] >= 2
        and _check_setup_improvement(token, direction, current_rsi, current_price)):
        log(f"  ✅ [THESIS-OVERRIDE] {token} {direction}: cooldown overridden "
            f"(thesis validated {thesis['validated_pct']:.0%}, setup improved)")
        # Don't skip — allow re-entry
```

**CRITICAL: Also update `_filter_safe_prev_hotset()` (line ~4712)** — the preserve path checks cooldown independently. If we override in the main loop but not in the preserve filter, the override is undone on the next cycle.

**Safety guard:** Max 1 thesis override per token:direction per 4 hours. After 1 override, respect cooldown for 3 cycles. This prevents revenge-trading loops on repeatedly-failing tokens.

```python
# Track override count
_thesis_override_count = {}  # {(token, direction): count}
_THESIS_OVERRIDE_WINDOW = 14400  # 4 hours
_THESIS_OVERRIDE_MAX = 1

def _can_override_cooldown(token, direction):
    key = (token, direction)
    count, first_time = _thesis_override_count.get(key, (0, 0))
    if time.time() - first_time > _THESIS_OVERRIDE_WINDOW:
        _thesis_override_count[key] = (0, time.time())
        return True
    return count < _THESIS_OVERRIDE_MAX
```

### Setup Improvement Detection

```python
def _check_setup_improvement(token, direction, current_rsi, current_price, prev_entry):
    """
    Check if current setup is better than previous entry.
    Strategy-aware: momentum vs mean-reversion have different "improvement" definitions.
    """
    improvements = 0
    
    # 1. Price moved in predicted direction (confirmation)
    if direction == 'SHORT' and current_price < prev_entry['price']:
        improvements += 1  # price dropped = thesis confirmed
    elif direction == 'LONG' and current_price > prev_entry['price']:
        improvements += 1  # price rose = thesis confirmed
    
    # 2. RSI improved — STRATEGY-AWARE
    # Momentum signals: RSI moving in direction = improvement
    # Mean-reversion signals: RSI at extreme = improvement
    signal_family = _get_family(signal_type)  # from market_phase_gate
    if signal_family in ('Momentum', 'Accelerate', 'Continuation'):
        # Momentum: RSI moving toward entry direction
        if direction == 'SHORT' and current_rsi < prev_entry['rsi']:
            improvements += 1
        elif direction == 'LONG' and current_rsi > prev_entry['rsi']:
            improvements += 1
    else:
        # Mean-reversion: RSI at extreme = improvement
        if direction == 'SHORT' and current_rsi > prev_entry['rsi']:
            improvements += 1  # RSI rising = overbought = SHORT opportunity
        elif direction == 'LONG' and current_rsi < prev_entry['rsi']:
            improvements += 1  # RSI falling = oversold = LONG opportunity
    
    # 3. Volatility regime aligned (parameter, not undefined variable)
    if _vol_regime in ('EXTREME', 'HIGH'):
        improvements += 1
    
    return improvements >= 2  # need 2+ improvements
```

### MFE Tracking

MFE is already computed in `hl-sync-guardian.py` `_compute_mfe_mae()` (line 2929-2973) and written to PostgreSQL `trades` table (line 3119).

**Integration point:** `_record_trade_outcome()` (line 3283) — update signal_outcomes with thesis validation AFTER trade close.

```python
def _record_trade_outcome(trade_id, token, direction, signal_type, is_win, 
                          pnl_pct, pnl_usdt, confidence, regime, mfe_pct):
    """Record trade outcome with thesis validation."""
    thesis_validated = None  # Unknown if MFE not computed
    if mfe_pct is not None:
        thesis_validated = 1 if mfe_pct > 0 else 0
    
    # Insert into signal_outcomes with thesis data
    ...
```

**Handle MFE=None gracefully:** If MFE cannot be computed (very short trades, no price data), set `thesis_validated = NULL`. The `_get_thesis_history()` function treats NULL as "unknown" → neutral multiplier (1.0).

### Hotset Ranking

In the hotset_final loop, apply thesis validation boost AFTER scoring:

```python
# After scoring, before ranking
for entry in scored:
    thesis_mult = _get_thesis_validation_mult(entry['token'], entry['direction'], entry.get('source'))
    entry['score'] *= thesis_mult
    if thesis_mult > 1.0:
        log(f"  🎯 [THESIS-BOOST] {entry['token']} {entry['direction']}: "
            f"score × {thesis_mult:.2f} (thesis validated {thesis_mult-1:.0%} boost)")
```

### Integration Points (Complete List)

| File | Line | Change | Notes |
|------|------|--------|-------|
| `signal_compactor.py` | ~1955 | Add `thesis_validation_mult` to score formula | One more `*` multiplier |
| `signal_compactor.py` | ~2929 | Override cooldown when thesis validated | Also update preserve filter |
| `signal_compactor.py` | ~4712 | Override cooldown in `_filter_safe_prev_hotset()` | Prevents undo on next cycle |
| `signal_compactor.py` | ~3709 | Apply thesis boost in hotset_final loop | Boost validated signals |
| `hl-sync-guardian.py` | ~3283 | Update signal_outcomes with MFE/thesis data | After trade close |
| `hermes_constants.py` | — | Add TVS config constants | See below |

### Config (hermes_constants.py)

```python
# Thesis Validation System
TVS_ENABLED = True
TVS_MFE_THRESHOLD_VALIDATED = 0.0     # MFE > 0 = thesis validated
TVS_MFE_THRESHOLD_STRONG = 2.0        # MFE > 2% = strongly validated
TVS_BOOST_VALIDATED = 1.15            # +15% score boost (was 1.2x, reduced per audit)
TVS_BOOST_STRONG = 1.25               # +25% score boost (was 1.4x, reduced per audit)
TVS_PENALTY_INVALIDATED = 0.85        # -15% score penalty
TVS_COOLDOWN_OVERRIDE = True          # override cooldown when thesis validated
TVS_COOLDOWN_OVERRIDE_MAX = 1         # max overrides per token:direction per 4h
TVS_COOLDOWN_OVERRIDE_WINDOW = 14400  # 4 hours
TVS_SETUP_IMPROVEMENT_THRESHOLD = 2   # min improvements needed
TVS_LOOKBACK_TRADES = 5               # last N trades to check thesis history
```

### Files to Modify

| File | Change |
|------|--------|
| `scripts/signal_compactor.py` | Add thesis_validation_mult to score, override cooldowns (both locations), boost hotset |
| `scripts/hl-sync-guardian.py` | Update signal_outcomes with MFE/thesis data after trade close |
| `scripts/hermes_constants.py` | Add TVS config constants |
| `scripts/signal_schema.py` | Add thesis_validated, thesis_mfe columns to signal_outcomes |

**No new files needed.** No new tables needed. Everything fits into existing infrastructure.

### Expected Impact

Based on 30d data (22 trades with MFE data):
- 82% SHORT thesis validated → 15% score boost on re-entry
- Cooldown overrides for validated setups → more re-entries on confirmed moves
- Better hotset ranking → validated signals bubble to top
- **Conservative estimate:** +10-15% more executed trades with higher quality

### Risk Mitigation

- TVS is additive — doesn't replace existing safety filters
- Cooldown override requires: thesis validated + 2+ previous signals + setup improved + max 1 override per 4h
- MFE=None treated as neutral (not penalized)
- TVS does NOT override: RSI blocks, blacklist, volatility gate, RR hard blocks, Hall of Shame
- Can be disabled with TVS_ENABLED = False
- Max override count prevents revenge-trading loops
