# Weather Vane v3 — Predictive Detection (Updated)

**Date:** 2026-08-13
**Status:** BACKTESTED (14 days) — design revision needed
**Based on:** market structure + multiple indicators as leading indicators

---

## 14-Day Backtest Results

### Structure Shifts: Directional, Not Agnostic

The 7-day backtest was misleading. Over 14 days:

**SHORT (267 trades):**
| Category | Trades | WR | PnL |
|----------|--------|-----|-----|
| SHIFT | 59 | 47% | **+$0.21** (profitable!) |
| EMERGING | 88 | 48% | +$0.21 |
| STABLE | 120 | 38% | **-$0.57** (worst) |

**LONG (245 trades):**
| Category | Trades | WR | PnL |
|----------|--------|-----|-----|
| SHIFT | 85 | 38% | **-$0.76** (worst) |
| EMERGING | 65 | 49% | +$0.10 |
| STABLE | 95 | 47% | +$0.13 |

### Key Insight

Structure shifts are **bad for LONG** but **not bad for SHORT**. The filter must be **directional**:
- Suppress LONG during shifts ✓
- Do NOT suppress SHORT during shifts ✗

### Why This Makes Sense

- LONG profits from trending markets (stable structure)
- SHORT profits from volatile/uncertain markets (shifts)
- Structure shift = volatility = opportunity for SHORT, risk for LONG

---

## Revised Design: Directional Structure Shift Filter

### Rule

```
Structure shifted → suppress LONG (0.75x penalty)
Structure shifted → do NOT suppress SHORT (let it trade)
```

### Implementation

```python
# In _score_signal():
if STRUCTURE_SHIFT_ENABLED and direction == 'LONG':
    if check_structure_shift(token):
        dir_outcome_mult = min(dir_outcome_mult, STRUCTURE_SHIFT_PENALTY)
```

### Params

```python
STRUCTURE_SHIFT_ENABLED = True
STRUCTURE_SHIFT_PENALTY = 0.75           # penalty for LONG during shifts
STRUCTURE_SHIFT_WINDOW = 50              # 1h candles
STRUCTURE_SHIFT_MIN_SWINGS = 10
STRUCTURE_SHIFT_CIRCUIT_BREAKER = 0.20
```

---

## Brainstorm: Other Predictive Methods

### Method 1: Volume Spike Detection

**Concept:** Unusual volume spikes often precede price reversals. If a token's volume spikes 3x+ above its 24h average, a move is coming.

**Application:** When volume spikes on a token, suppress signals in the direction AGAINST the volume spike direction.

**Data:** candles_1h volume column.

### Method 2: Volatility Expansion

**Concept:** Periods of low volatility (tight BB, low ATR) are followed by explosive moves. Detect compression → expect expansion → suppress signals during expansion.

**Application:** When ATR expands 2x+ from its recent average, suppress all signals for that token.

**Data:** ATR from candles or speed_tracker.

### Method 3: Multi-Token Correlation Break

**Concept:** When correlated tokens (e.g., SOL ecosystem: SOL, RAY, JTO) start diverging, the market is shifting. Correlation break = regime change.

**Application:** Track price correlation between token pairs. When correlation drops below threshold, suppress signals for both tokens.

**Data:** Price history, correlation calculation.

### Method 4: Time-of-Day Pattern

**Concept:** Certain hours consistently produce worse trades. The 14-day data shows hourly patterns — some hours are loss-prone.

**Application:** Suppress signals during historically bad hours.

**Data:** Hourly trade outcomes.

### Method 5: Consecutive Loss Counter (Per-Token)

**Concept:** Track consecutive losses per token (not per direction). If a token has 3+ consecutive losses, suppress ALL signals for that token.

**Application:** Per-token lock after consecutive losses.

**Data:** signal_outcomes table.

### Method 6: Entry Price vs Recent Range

**Concept:** If entry price is at the extreme of the recent range (top for LONG, bottom for SHORT), the trade is chasing. Enter only when price is in the middle of the range.

**Application:** Suppress signals when price is at 90th/10th percentile of recent range.

**Data:** candles_5m high/low.

### Method 7: Regime Scanner Alignment

**Concept:** If the 4h regime scanner says LONG_BIAS but the Weather Vane says SHORT is winning, there's a conflict. Trust the real-time data over the lagging scanner.

**Application:** When regime scanner and Weather Vane disagree, use the Weather Vane's signal.

**Data:** regime_4h.json + signal_outcomes.

### Method 8: Spread/Tightness Monitor

**Concept:** Wide bid-ask spreads indicate illiquidity or uncertainty. Signals fired during wide spreads get worse fills.

**Application:** Suppress signals when spread exceeds threshold.

**Data:** Would need real-time spread data (not currently tracked).
