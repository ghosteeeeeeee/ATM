# Thesis Validation System (TVS) — Spec

## Problem Statement

The system generates 350+ signals per day but executes only 5 (98.6% expiry rate). Signals that validate their thesis (price moves in predicted direction) are treated as fresh starts on re-entry — no memory of past success. Cooldowns block re-entry even when the setup has improved.

**Example:**
1. BABY SHORT fires at RSI 50 → stopped out at -1.3%
2. Price drops 3% (thesis was RIGHT)
3. Same signal fires again → blocked by cooldown
4. But now RSI is 40, price has dropped, setup is BETTER
5. System misses the re-entry

**Data shows:** 82-84% of signals validate their thesis (MFE > 0). The system is right most of the time but doesn't leverage this.

## Solution: Thesis Validation Score (TVS)

### Core Concept
Track whether each signal's thesis validated (price moved in predicted direction). Use this history to:
- Boost score for re-entries after validated thesis
- Override cooldowns when setup improves
- Rank signals by thesis quality

### Data Model

#### signal_outcomes table (existing, extend)
Add columns:
- `thesis_validated` BOOLEAN — True if MFE > 0 (price moved in predicted direction)
- `thesis_mfe` REAL — Max favorable excursion % (how much thesis validated)
- `setup_improved` BOOLEAN — True if current setup better than previous entry
- `reentry_boost` REAL — Score multiplier from thesis validation (1.0 = no boost, 1.2 = +20%)

#### New: thesis_history table
```sql
CREATE TABLE thesis_history (
    id INTEGER PRIMARY KEY,
    token TEXT NOT NULL,
    direction TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    entry_price REAL,
    mfe_pct REAL,           -- max favorable excursion
    thesis_validated INTEGER, -- 1=validated, 0=invalidated
    validated_at TIMESTAMP,
    regime TEXT,
    rsi_at_entry REAL,
    volatility_regime TEXT
);
```

### Score Formula Addition

Add `thesis_validation_mult` to the score formula in `signal_compactor.py` line 1955:

```
final_score = ... * thesis_validation_mult * ...
```

Logic:
- No history: 1.0 (neutral)
- Previous thesis validated (MFE > 0): **1.2** (+20% boost)
- Previous thesis strongly validated (MFE > 2%): **1.4** (+40% boost)
- Previous thesis invalidated (MFE <= 0): **0.8** (-20% penalty)
- Multiple validated signals: compound (max 1.5x)

### Cooldown Override Rules

In `signal_compactor.py` where cooldowns are checked:

```python
# Current: cooldown blocks all re-entries
# New: override cooldown if thesis validated + setup improved

if _is_loss_cooldown_active(token, direction):
    # Check thesis history
    thesis = _get_thesis_history(token, direction)
    if thesis and thesis['validated'] and thesis['setup_improved']:
        log(f"  ✅ [THESIS-OVERRIDE] {token} {direction}: cooldown overridden "
            f"(previous thesis validated, MFE={thesis['mfe']:.2f}%, setup improved)")
        # Don't skip — allow re-entry
```

### Setup Improvement Detection

Compare current signal vs previous entry:

```python
def _check_setup_improvement(token, direction, current_rsi, current_price, prev_entry):
    """Check if current setup is better than previous entry."""
    improvements = 0
    
    # 1. RSI improved (more favorable for entry direction)
    if direction == 'SHORT' and current_rsi < prev_entry['rsi']:
        improvements += 1  # RSI lower = more room to fall
    elif direction == 'LONG' and current_rsi > prev_entry['rsi']:
        improvements += 1  # RSI higher = more room to rise
    
    # 2. Price moved in predicted direction (confirmation)
    if direction == 'SHORT' and current_price < prev_entry['price']:
        improvements += 1
    elif direction == 'LONG' and current_price > prev_entry['price']:
        improvements += 1
    
    # 3. Volatility regime aligned
    if current_vol_regime in ('EXTREME', 'HIGH'):
        improvements += 1  # trending markets favor momentum
    
    return improvements >= 2  # need 2+ improvements
```

### MFE Tracking

After each trade closes, compute MFE from price history:

```python
def _compute_thesis_validation(trade):
    """Check if trade's thesis was validated by MFE."""
    entry = trade['entry_price']
    direction = trade['direction']
    mfe = trade.get('mfe_pct', 0)
    
    if direction == 'LONG':
        thesis_validated = mfe > 0  # price went up at some point
    else:  # SHORT
        thesis_validated = mfe > 0  # MFE is already directional
    
    return {
        'thesis_validated': thesis_validated,
        'thesis_mfe': mfe,
        'setup_improved': False  # computed later
    }
```

### Hotset Ranking

In the hotset_final loop, apply thesis validation boost:

```python
# After scoring, before ranking
for entry in scored:
    thesis_mult = _get_thesis_validation_mult(entry['token'], entry['direction'])
    entry['score'] *= thesis_mult
    if thesis_mult > 1.0:
        log(f"  🎯 [THESIS-BOOST] {entry['token']} {entry['direction']}: "
            f"score × {thesis_mult:.2f} (previous thesis validated)")
```

### Integration Points

1. **signal_compactor.py** — Add thesis_validation_mult to score formula
2. **signal_compactor.py** — Override cooldowns when thesis validated
3. **signal_compactor.py** — Apply thesis boost in hotset ranking
4. **hl-sync-guardian.py** — Update signal_outcomes with MFE data after trade close
5. **cut_loser.py** — Record thesis validation when cutting losing trades
6. **New: thesis_tracker.py** — Background job to compute MFE and update thesis_history

### Files to Modify

| File | Change |
|------|--------|
| `scripts/signal_compactor.py` | Add thesis_validation_mult to score, override cooldowns, boost hotset |
| `scripts/hl-sync-guardian.py` | Update signal_outcomes with thesis data after trade close |
| `scripts/hermes_constants.py` | Add TVS config (boost values, cooldown override rules) |
| `scripts/thesis_tracker.py` | NEW: Background job to compute MFE and validate thesis |
| `scripts/signal_schema.py` | Add thesis_history table creation |

### Config (hermes_constants.py)

```python
# Thesis Validation System
TVS_ENABLED = True
TVS_MFE_THRESHOLD_VALIDATED = 0.0     # MFE > 0 = thesis validated
TVS_MFE_THRESHOLD_STRONG = 2.0        # MFE > 2% = strongly validated
TVS_BOOST_VALIDATED = 1.2             # +20% score boost
TVS_BOOST_STRONG = 1.4                # +40% score boost
TVS_PENALTY_INVALIDATED = 0.8         # -20% score penalty
TVS_COOLDOWN_OVERRIDE = True          # override cooldown when thesis validated
TVS_COOLDOWN_MIN_CONFIDENCE = 80      # min confidence to override cooldown
TVS_SETUP_IMPROVEMENT_THRESHOLD = 2   # min improvements needed
```

### Expected Impact

Based on 30d data:
- 82-84% of signals validate thesis → 20-40% score boost on re-entry
- Cooldown overrides for validated setups → more re-entries on confirmed moves
- Better hotset ranking → validated signals bubble to top
- Estimated: +15-25% more executed trades with higher quality

### Risk Mitigation

- TVS is additive — doesn't replace existing filters
- Cooldown override requires high confidence (>80%)
- Setup improvement requires 2+ improvements (not just one)
- MFE tracking is post-hoc — doesn't affect live trading
- Can be disabled with TVS_ENABLED = False
