# Thesis Validation System (TVS) — Spec v2

## Plain English: What We're Building

### The Problem

Our system fires 350+ signals per day but only executes 5. Here's why:

1. **Signal fires** → BABY SHORT at RSI 50 (88% confidence)
2. **Trade opens** → Gets stopped out at -1.3%
3. **Price drops 3%** → Our thesis was RIGHT
4. **Same signal fires again** → Blocked by cooldown
5. **But now RSI is 40, price has dropped** → Setup is BETTER
6. **System misses the re-entry** → We lose the move

**The system has no memory.** Every signal is treated as a fresh start. It doesn't know that 82% of its signals validate their thesis (price moves in the predicted direction).

### What We're Building

A system that remembers:

**"I was right about BABY SHORT last time. Price moved in my direction. The thesis was correct. When the same signal fires again, boost it to the top of the queue."**

### How It Works

1. **Track MFE after each trade** — Did price move in the predicted direction?
   - MFE > 0 → Thesis validated ✅
   - MFE > 2% → Thesis strongly validated 💪
   - MFE ≤ 0 → Thesis invalidated ❌

2. **Score boost for re-entries** — When the same signal fires again:
   - Previous thesis validated → **+15% score boost**
   - Previous thesis strongly validated → **+25% score boost**
   - Previous thesis invalidated → **-15% score penalty**

3. **Override cooldowns** — If the thesis was validated AND the setup improved:
   - Price moved in the right direction
   - RSI improved (more favorable for entry)
   - Volatility regime aligned
   → Override cooldown, re-enter with higher priority

4. **Safety guard** — Max 1 override per token per 4 hours. Prevents revenge-trading loops.

### What It Doesn't Do

- Doesn't override RSI blocks (if RSI says don't trade, don't trade)
- Doesn't override blacklist (if token is banned, stay banned)
- Doesn't override RR engine (if risk:reward is bad, don't enter)
- Doesn't override Hall of Shame (if 30-day WR is bad, stay blocked)

### The Goal

Turn our 98.6% signal expiry rate into more executed trades — but only the GOOD ones. Signals that proved they were right should get priority. Signals that proved they were wrong should get penalized.

**In one sentence:** The system learns from its own predictions and double-downs on winners.

---

## Technical Specification

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
def _check_setup_improvement(token, direction, current_rsi, current_price, prev_entry, _vol_regime):
    """
    Check if current setup is better than previous entry.
    Strategy-aware: momentum vs mean-reversion have different "improvement" definitions.
    
    prev_entry: dict with keys 'price' (float) and 'rsi' (float)
    Data source: PostgreSQL trades table — most recent trade for same token+direction+signal_type.
    RSI at entry: Use signal_rsi_14 column (stored at trade open by position_manager.py line 1279).
                  If NULL, back-calculate from candles_1m using trade open_time timestamp.
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
    signal_family = _signal_family(signal_type)  # from market_phase_gate.py (aliased in signal_compactor.py)
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

**Integration point:** `record_signal_outcome()` in `signal_schema.py` (line ~4042) — update with thesis validation AFTER trade close. This function is called from `position_manager.py`, `cut_loser.py`, and `profit_monster.py`.

**MFE data flow (Option A — pass MFE as parameter):**
1. Guardian computes MFE in `_compute_mfe_mae()` → writes to PostgreSQL `trades.mfe_pct`
2. Position manager calls `record_signal_outcome()` after trade close
3. Position manager queries `trades.mfe_pct` for this trade_id
4. Passes `mfe_pct` as new parameter to `record_signal_outcome()`
5. `record_signal_outcome()` writes `thesis_validated` and `thesis_mfe` to signal_outcomes

```python
# In position_manager.py, after trade close (~line 1279):
mfe = None
try:
    pg_conn = psycopg2.connect(...)
    pg_cur = pg_conn.cursor()
    pg_cur.execute("SELECT mfe_pct FROM trades WHERE trade_id = %s", (trade_id,))
    row = pg_cur.fetchone()
    if row: mfe = row[0]
    pg_conn.close()
except: pass

record_signal_outcome(token, direction, signal_type, is_win, pnl_pct, 
                      pnl_usdt, confidence, regime, mfe_pct=mfe)
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
| `scripts/signal_schema.py` | Add mfe_pct param to `record_signal_outcome()`, write thesis_validated/thesis_mfe |
| `scripts/position_manager.py` | ALTER TABLE migration for thesis columns (~line 562), pass MFE to record_signal_outcome (~line 1279) |
| `scripts/hermes_constants.py` | Add TVS config constants |

### Schema Migration

```sql
-- Run in both position_manager.py (CREATE TABLE location) and signal_schema.py
-- Use idempotent pattern:
ALTER TABLE signal_outcomes ADD COLUMN thesis_validated INTEGER DEFAULT NULL;
ALTER TABLE signal_outcomes ADD COLUMN thesis_mfe REAL DEFAULT NULL;
-- Wrap in try/except for idempotency (column may already exist):
try:
    conn.execute("ALTER TABLE signal_outcomes ADD COLUMN thesis_validated INTEGER DEFAULT NULL")
except sqlite3.OperationalError:
    pass  # column already exists
try:
    conn.execute("ALTER TABLE signal_outcomes ADD COLUMN thesis_mfe REAL DEFAULT NULL")
except sqlite3.OperationalError:
    pass
```

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
