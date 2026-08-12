# Scaling In/Out Spec — Book-Based Position Management

**Date**: 2026-08-12
**Status**: APPROVED (Phase 1+2) | DEFERRED (Phase 3) | REJECTED (Phase 4)
**CEO Decision**: 2026-08-12 — see `automation/ceo/ceo_report.md`

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

### System Context
- `atr_sl_hit` dominates 7d losses: 138 trades, -$7.81
- If ATR trail reduces this by 30% → +$2.34/week improvement

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

### 1. Late Entry Filter ✅ APPROVED
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

**Integration Point**: `position_manager.py` at trade execution time
**⚠️ CEO CORRECTION**: NOT in signal_compactor.py — filter runs at execution, not signal generation

---

### 2. ATR-Based Trailing ✅ APPROVED
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
**Lines to modify**: 528, 544, 551, 744, 769 in tpsl_utils.py

**Floor**: Keep `ATR_SL_MIN = 0.010` — SL must never be tighter than 1.0% from entry

---

### 3. Scale Out — Partial Profits ⏳ DEFERRED
**Purpose**: Lock profits at multiple levels, let runners run

**CEO Decision**: Defer until Phase 1+2 validated for 2+ weeks. If `atr_sl_hit` drops below 50% of losses, scale out becomes unnecessary. If it remains dominant, scale out becomes justified.

**Risk**: State file adds crash recovery complexity. If position_manager crashes between TP1 hit and state write, orphaned state = wrong behavior on next run. Need idempotent state recovery.

**Logic** (for future implementation):
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

**Constants** (deferred):
```python
SCALE_OUT_ENABLED = False  # DEFERRED — enable after Phase 1+2 validation
SCALE_OUT_LEVELS = [1.5, 3.0]  # ATR multiples
SCALE_OUT_SIZES = [0.33, 0.33]  # fractions to close at each level
SCALE_OUT_MOVE_SL_TO_BE = True  # move stop to breakeven after TP1
```

**Integration Point**: `profit_monster.py` — extend trailing tier

**State File**: `scale_state.json` (deferred)
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

### 4. Scale In — Pyramid ❌ REJECTED
**Purpose**: Add to winning positions at better average

**CEO Decision**: Rejected. Wrong philosophy for HFT system. Hermes is a high-frequency system with many small positions (50-100+ trades/week). Scale-in is a swing trading technique. Edge is in signal quality, not position sizing complexity. No backtest data provided — pure theory.

**Logic** (rejected, for reference):
```
Entry 1: SCALE_IN_SIZES[0] (e.g., 50%) at signal
Entry 2: SCALE_IN_SIZES[1] (e.g., 50%) at +SCALE_IN_CONFIRMATION_PCT

Stop for all: average_cost × (1 - ATR_SL_MIN)
```

**Constants** (rejected):
```python
SCALE_IN_ENABLED = False  # REJECTED — wrong philosophy for HFT
SCALE_IN_ENTRIES = 2
SCALE_IN_SIZES = [0.5, 0.5]
SCALE_IN_CONFIRMATION_PCT = 0.003  # 0.3%
```

---

## Implementation Order

| Phase | Component | Status | Effort | Risk | Value |
|-------|-----------|--------|--------|------|-------|
| 1 | Late Entry Filter | ✅ APPROVED | Low | Low | High — prevents late entries |
| 2 | ATR Trailing | ✅ APPROVED | Medium | Medium | High — survives pullbacks |
| 3 | Scale Out | ⏸️ DEFERRED | High | Medium | High — locks profits |
| 4 | Scale In | ❌ REJECTED | High | High | Medium — wrong philosophy |

**Next Step**: Implement Phase 1 + 2 after broader backtest validates across top 10 tokens.

---

## Backtesting Plan (REQUIRED before implementation)

**CEO Requirement**: Run backtest across top 10 tokens by trade count, not just AVNT.

```bash
# Get top 10 tokens by trade count
sudo -u postgres psql -d brain -c "
  SELECT token, COUNT(*) as trades, ROUND(SUM(pnl_usdt),2) as pnl
  FROM trades WHERE status = 'closed' AND close_time > NOW() - INTERVAL '7 days'
  GROUP BY token ORDER BY trades DESC LIMIT 10;
"
```

**Test Scenarios**:
1. Each token: ATR trail (1.5×ATR) vs fixed 0.60%
2. Each token: Late entry filter impact
3. Combined: ATR trail + late entry filter

**Metrics to Compare**:
- Total PnL
- Win rate
- `atr_sl_hit` count and PnL (target: reduce by 30%+)
- Max drawdown
- Average holding time

**Go/No-Go Criteria**:
- ATR trail must show positive PnL improvement across majority of tokens
- Late entry filter must not reduce win rate by more than 5%
- Combined must show net positive improvement

---

## Constants Summary (hermes_constants.py)

```python
# ── Late Entry Filter ✅ APPROVED ──────────────────────────────────
LATE_ENTRY_FILTER_ENABLED = True
LATE_ENTRY_MAX_MOVE_PCT = 0.005  # 0.5%
LATE_ENTRY_LOOKBACK_MINUTES = 15

# ── ATR Trailing ✅ APPROVED ──────────────────────────────────────
TRAILING_MODE = 'ATR'  # 'ATR', 'STRUCTURE', 'FIXED'
TRAILING_ATR_MULTIPLE = 1.5
TRAILING_ACTIVATION_PCT = 0.003  # 0.3%

# ── Scale Out ⏸️ DEFERRED ─────────────────────────────────────────
SCALE_OUT_ENABLED = False  # DEFERRED — enable after Phase 1+2 validation
SCALE_OUT_LEVELS = [1.5, 3.0]  # ATR multiples for TP targets
SCALE_OUT_SIZES = [0.33, 0.33]  # fractions to close
SCALE_OUT_MOVE_SL_TO_BE = True

# ── Scale In ❌ REJECTED ──────────────────────────────────────────
SCALE_IN_ENABLED = False  # REJECTED — wrong philosophy for HFT
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
5. **Kill switch**: Each feature has its own ENABLED flag
6. **Broader validation**: Must backtest top 10 tokens before deploy

---

## Testing Checklist

- [ ] Backtest top 10 tokens by trade count (REQUIRED)
- [ ] Compare ATR trail vs fixed across all tokens
- [ ] Late entry filter impact on win rate
- [ ] Combined PnL improvement
- [ ] Paper trade 1 week after backtest passes
- [ ] Review edge cases: low ATR tokens, high volatility
- [ ] Test late entry filter with continuation moves (may miss some)
- [ ] Verify ATR_SL_MIN floor not violated

---

## CEO Feedback Summary

**Approved**:
- Late entry filter (position_manager.py, not signal_compactor)
- ATR trailing (replaces fixed 0.60% with 1.5×ATR)

**Deferred**:
- Scale out (needs Phase 1+2 validation first, 2+ weeks)

**Rejected**:
- Scale in (wrong philosophy for HFT, no data, high risk)

**Key Insight**: `atr_sl_hit` dominates 7d losses at 138T -$7.81. ATR trail is the highest-leverage fix.

Full CEO analysis: `automation/ceo/ceo_report.md`
