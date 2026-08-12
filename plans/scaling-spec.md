# Scaling In/Out Spec — Book-Based Position Management

**Date**: 2026-08-12
**Status**: Draft
**Problem**: AVNT trades stopped out prematurely (trail too tight) or entered late (after move exhausted)

---

## Problem Analysis

### Trade 13652 (Correct Signal, Stopped Out)
- Entry: 0.0941 at 01:27
- Peak: 0.09451 at 01:45 (+0.43%)
- Stopped out: 0.09389 at 02:10
- **Root cause**: Fixed 0.60% trail distance doesn't survive normal pullbacks

### Trade 13656 (Late Entry, Move Already Over)
- Entry: 0.094306 at 03:26
- Price peaked: 0.095240 at 03:15 (11 min BEFORE entry)
- Stopped out: 0.093332 at 03:48
- **Root cause**: No late entry filter — signal fired after exhaustion

---

## Book Sources

| Book | Key Insight | Implementation |
|------|-------------|----------------|
| **Heitkoetter** | 1/3 at TP1, 1/3 at S/R, 1/3 trailing | Scale out levels |
| **Wyckoff** | Pyramid on profits, stop behind average cost | Scale in logic |
| **Woods** | Trail below pattern low / swing low | Structure-based trail |
| **Cardoza** | ATR-based trailing | ATR trail distance |
| **Porwal** | Trail below pattern low, exit on opposite signal | Exit rules |
| **Warrior Trading** | Scale in as trade proves correct | Scale in confirmation |

---

## Solution Components

### 1. Late Entry Filter (Simplest)
**Purpose**: Avoid entering after price has already moved

**Logic**:
```
Before executing signal:
1. Get price from LATE_ENTRY_LOOKBACK_MINUTES ago
2. Calculate price_change_pct = abs(current - old) / old
3. If price_change_pct > LATE_ENTRY_MAX_MOVE_PCT:
   - Skip signal
   - Log reason: 'late_entry_filter'
```

**Constants**:
```python
LATE_ENTRY_FILTER_ENABLED = True
LATE_ENTRY_MAX_MOVE_PCT = 0.005  # 0.5%
LATE_ENTRY_LOOKBACK_MINUTES = 15
```

**Integration Point**: `signal_compactor.py` or `signals_runner.py`

---

### 2. ATR-Based Trailing (Moderate)
**Purpose**: Replace fixed 0.60% trail with volatility-adaptive trail

**Logic**:
```
Trail distance = TRAILING_ATR_MULTIPLE × ATR(14)
For LONG: trail_from = highest_price (peak)
For SHORT: trail_from = lowest_price (nadir)

new_sl = trail_from × (1 - trail_distance)
new_sl = max(new_sl, entry_price × (1 - ATR_SL_MIN))  # floor at entry

One-way enforcement: new_sl >= current_sl (LONG)
```

**Constants**:
```python
TRAILING_MODE = 'ATR'  # 'ATR', 'STRUCTURE', or 'FIXED'
TRAILING_ATR_MULTIPLE = 1.5  # trail at 1.5x ATR from peak
TRAILING_ACTIVATION_PCT = 0.003  # 0.3% — trail activates after this profit
```

**Integration Point**: `tpsl_utils.py` — modify `compute_atr_sl_tp()`

**Key Change**: Replace `TRAILING_DISTANCE_PCT = 0.006` with dynamic ATR-based distance

---

### 3. Scale Out — Partial Profits (Complex)
**Purpose**: Lock profits at multiple levels, let runners run

**Logic**:
```
TP1 = entry + SCALE_OUT_LEVELS[0] × ATR  (e.g., 1.5 × ATR)
TP2 = entry + SCALE_OUT_LEVELS[1] × ATR  (e.g., 3.0 × ATR)

When price hits TP1:
  - Close SCALE_OUT_SIZES[0] (e.g., 33%)
  - Move stop to breakeven
  
When price hits TP2:
  - Close SCALE_OUT_SIZES[1] (e.g., 33%)
  - Trail remaining with ATR stop
  
Remaining 34%: trail until stopped or opposite signal
```

**Constants**:
```python
SCALE_OUT_ENABLED = True
SCALE_OUT_LEVELS = [1.5, 3.0]  # ATR multiples
SCALE_OUT_SIZES = [0.33, 0.33]  # fractions to close at each level
SCALE_OUT_MOVE_SL_TO_BE = True  # move stop to breakeven after TP1
```

**Integration Point**: `profit_monster.py` — extend trailing tier

**State File**: `scale_state.json`
```json
{
  "13652": {
    "token": "AVNT",
    "direction": "LONG",
    "entry_price": 0.0941,
    "size": 1.0,
    "remaining": 1.0,
    "tp1_hit": false,
    "tp2_hit": false,
    "atr": 0.0008,
    "sl": 0.0935
  }
}
```

---

### 4. Scale In — Pyramid (Most Complex)
**Purpose**: Add to winning positions at better average

**Logic**:
```
Entry 1: SCALE_IN_SIZES[0] (e.g., 50%) at signal
Entry 2: SCALE_IN_SIZES[1] (e.g., 50%) at +SCALE_IN_CONFIRMATION_PCT

Stop for all: average_cost × (1 - ATR_SL_MIN)
```

**Constants**:
```python
SCALE_IN_ENABLED = True
SCALE_IN_ENTRIES = 2
SCALE_IN_SIZES = [0.5, 0.5]
SCALE_IN_CONFIRMATION_PCT = 0.003  # 0.3% — add when price moves this much
```

**Integration Point**: `position_manager.py` — modify `get_trade_params()`

**State File**: `scale_state.json` (same as scale out)

---

## Implementation Order

| Phase | Component | Effort | Risk | Value |
|-------|-----------|--------|------|-------|
| 1 | Late Entry Filter | Low | Low | High — prevents late entries |
| 2 | ATR Trailing | Medium | Medium | High — survives pullbacks |
| 3 | Scale Out | High | Medium | High — locks profits |
| 4 | Scale In | High | High | Medium — better average |

**Recommendation**: Start with Phase 1 + 2 (late filter + ATR trail). These address both AVNT problems directly. Scale in/out can follow.

---

## Backtesting Plan

Before implementing, validate with AVNT data:

```bash
# Get AVNT candles for trade period
python3 -c "
from paths import CANDLES_DB
import sqlite3
conn = sqlite3.connect(CANDLES_DB)
c = conn.cursor()
c.execute('SELECT ts, open, high, low, close FROM candles_5m WHERE token = ? ORDER BY ts', ('AVNT',))
for row in c.fetchall():
    print(row)
"
```

**Test Scenarios**:
1. Trade 13652 with ATR trail (1.5×ATR vs fixed 0.60%)
2. Trade 13656 with late entry filter (skip after +0.5% in 15min)
3. Both trades with scale out (1/3 at 1.5×ATR, 1/3 at 3×ATR)

**Metrics to Compare**:
- Total PnL
- Max drawdown
- Win rate
- Average holding time

---

## Constants Summary (hermes_constants.py)

```python
# ── Late Entry Filter ──────────────────────────────────────────────
LATE_ENTRY_FILTER_ENABLED = True
LATE_ENTRY_MAX_MOVE_PCT = 0.005  # 0.5%
LATE_ENTRY_LOOKBACK_MINUTES = 15

# ── ATR Trailing ──────────────────────────────────────────────────
TRAILING_MODE = 'ATR'  # 'ATR', 'STRUCTURE', 'FIXED'
TRAILING_ATR_MULTIPLE = 1.5
TRAILING_ACTIVATION_PCT = 0.003  # 0.3%

# ── Scale Out ─────────────────────────────────────────────────────
SCALE_OUT_ENABLED = True
SCALE_OUT_LEVELS = [1.5, 3.0]  # ATR multiples for TP targets
SCALE_OUT_SIZES = [0.33, 0.33]  # fractions to close
SCALE_OUT_MOVE_SL_TO_BE = True

# ── Scale In ──────────────────────────────────────────────────────
SCALE_IN_ENABLED = True
SCALE_IN_ENTRIES = 2
SCALE_IN_SIZES = [0.5, 0.5]
SCALE_IN_CONFIRMATION_PCT = 0.003  # 0.3%
```

---

## Risk Controls

1. **Max position size**: Unchanged (MAX_POSITIONS, MAX_LEVERAGE)
2. **Stop always active**: Even with scale out, remaining position has trailing stop
3. **One-way enforcement**: Trail never loosens (existing logic)
4. **ATR_SL_MIN floor**: SL never tighter than 1.0% from entry (existing)
5. **Kill switch**: SCALE_OUT_ENABLED / SCALE_IN_ENABLED can disable each feature

---

## Testing Checklist

- [ ] Backtest AVNT with new rules
- [ ] Backtest top 10 tokens by trade count
- [ ] Compare win rate, avg PnL, max drawdown
- [ ] Paper trade 1 week
- [ ] Review edge cases: low ATR tokens, high volatility
- [ ] Verify scale state file cleanup on trade close
- [ ] Test late entry filter with continuation moves (may miss some)
