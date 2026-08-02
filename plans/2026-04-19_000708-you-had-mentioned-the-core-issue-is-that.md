# Plan: Momentum Signal for Hermes

## Goal
Design and implement a momentum-direction signal for Hermes that complements the existing mean-reversion signals (`hzscore`, `pct-hermes`, `vel-hermes`). The new signal fires when price momentum is likely to **continue** in either direction, rather than revert.

---

## Context / Problem Statement

**Mean reversion signals** (`hzscore`, `pct-hermes`, `vel-hermes`) work by detecting when price has moved away from a historical baseline — they expect the price to snap back. This works in ranging markets but causes repeated stop-outs in strongly trending markets.

**Example failure mode:** A coin rallies 30% in 4 hours. `hzscore` fires SHORT at z=3.0 expecting reversion. Price pauses briefly then continues to +50%. The SHORT gets stopped out. `hzscore` fires again at z=3.2. Repeat until trend exhausts.

**The fundamental mismatch:**
- Mean reversion: "stretched → expect reversal"
- Trending market: "stretched → expect continuation"

A momentum signal captures the latter.

---

## Proposed Approach: `mom-hermes` (Momentum)

### Core Intuition
Track the **acceleration** of price change. When momentum is building — rate of change increasing session-over-session — the trend is likely to continue. When momentum is decelerating, the move may be exhausting.

### Calculation (per token, per direction)

For **LONG**:
```
mom_roc = ROC(close, period=8)          # rate of change over 8 candles
mom_roc_prev = ROC(close, period=8, shift=1)  # prior cycle's ROC

momentum_score = mom_roc - mom_roc_prev  # acceleration
mom_signal = momentum_score > threshold  # >0 = accelerating upward
```

For **SHORT**:
```
mom_signal = momentum_score < -threshold  # <0 = accelerating downward
```

### Alternative: ADX-based Directional Momentum

ADX (Average Directional Index) measures trend strength without direction. Combined with +DI/-DI:

```
+DI > -DI  →  bullish directional strength  →  LONG momentum
-DI > +DI  →  bearish directional strength  →  SHORT momentum
ADX > 25   →  trend is strong enough to be exploitable
```

This is more robust than ROC acceleration because it uses true range normalization.

### Recommended Implementation: Hybrid `mom-hermes`

Combine ROC acceleration with ADX confirmation:

```python
def mom_hermes_signal(token: str, direction: str, candles_df) -> tuple[float, str]:
    """
    Returns (confidence, signal_type) for momentum confirmation.

    Logic:
    1. Compute ROC(8) and ROC(8) shifted by 1 period (acceleration)
    2. Compute ADX +DI / -DI
    3. LONG: acceleration > 0 AND +DI > -DI AND ADX > 20
    4. SHORT: acceleration < 0 AND -DI > +DI AND ADX > 20
    5. Confidence = min(100, ADX * 4)  # ADX 25 → 100% confidence
    """
```

---

## Integration with Existing Signal Pipeline

### Where it fits in signal_gen.py

Add a new `mom_hermes` indicator alongside the existing ones:

```
signal_gen.py:
  if mom_hermes(token, direction, candles_df):
      confidence = min(100, adx * 4)
      add_signal(token, direction, source='mom-hermes+', confidence=confidence)
```

### How it interacts with confluence

`mom-hermes` can coexist with `hzscore`, `pct-hermes`, etc. in the confluence pipeline:
- In a **ranging** market: `hzscore` fires, `mom-hermes` is suppressed (ADX < 20), no trade
- In a **trending** market: `mom-hermes` fires, `hzscore` may also fire but loses the ADX tiebreaker
- **Both** can fire in early trend — confluence helps confirm the move has real substance

### Confluence with momentum signals only

A separate momentum confluence could be constructed:
```
source='mom-hermes+,roc-hermes+'  # both ROC acceleration AND momentum ADX agree
```

---

## Step-by-Step Implementation Plan

### Step 1: Add `mom_hermes()` function to signal_gen.py

**File:** `/root/.hermes/scripts/signal_gen.py`

Implement `mom_hermes(token, direction, candles_df)`:
1. Load candles from `candles.db` (price in **cents** — already handled by existing code)
2. Compute 8-period ROC (rate of change)
3. Compute prior period ROC for acceleration
4. Compute ADX, +DI, -DI using standard Wilder smoothing
5. Return (confidence, signal_type) if conditions met, else None

**Threshold calibration:**
- ADX threshold: 20 (below = no trend, filter out noise)
- ROC acceleration threshold: 0 (positive = accelerating, negative = decelerating)
- Confidence scaling: `min(100, ADX * 4)` — ADX of 25 = 100% confidence

### Step 2: Add `mom-hermes` to source taxonomy

**File:** `/root/.hermes/scripts/hermes_constants.py`

Add `'mom-hermes'` to the signal source list so it passes through the confluence merge logic.

### Step 3: Wire into `generate_signals()`

**File:** `/root/.hermes/scripts/signal_gen.py`

In the main signal generation loop, after computing indicators, call `mom_hermes()` and add its signal to the pending list if confidence > threshold.

### Step 4: Update signal_compactor scoring

**File:** `/root/.hermes/scripts/signal_compactor.py`

Add `mom-hermes` to the source taxonomy so it's recognized in the scoring/ranking. It should receive the same scoring treatment as `hzscore` and `pct-hermes`.

### Step 5: Validation — backtest against historical candles

**Test:** Run the signal on historical data for BTC, ETH, SOL during known trending periods (e.g., late 2024, early 2025). Compare:
- Mean reversion signal win rate during trends (should be low)
- Momentum signal win rate during trends (should be higher)

**Validation command:**
```bash
cd /root/.hermes/scripts && python3 -c "
from signal_gen import mom_hermes
from candles_db import get_candles
candles = get_candles('BTC', '1h', hours=200)
result = mom_hermes('BTC', 'LONG', candles)
print(f'BTC LONG momentum: {result}')
"
```

---

## Files Likely to Change

| File | Change |
|---|---|
| `/root/.hermes/scripts/signal_gen.py` | Add `mom_hermes()` function, wire into `generate_signals()` |
| `/root/.hermes/scripts/hermes_constants.py` | Add `'mom-hermes'` to signal source constants |
| `/root/.hermes/scripts/signal_compactor.py` | Add `'mom-hermes'` to source scoring (if needed) |

---

## Tests / Validation

1. **Syntax check:** `python3 -m py_compile signal_gen.py`
2. **Signal generation smoke test:** Run `generate_signals()` for a known trending token and confirm `mom-hermes` appears in output
3. **Backtest comparison:** Run 200h of BTC candles through both `hzscore` and `mom_hermes`, compare signal directions during trending vs ranging periods
4. **Confluence test:** Verify `source='hzscore+,mom-hermes+'` merges correctly in `add_signal()` merge logic

---

## Risks and Tradeoffs

| Risk | Mitigation |
|---|---|
| ADX is laggy ( Wilder smoothing = ~14 periods) | Use shorter period (8) for ADX calculation to reduce lag |
| ROC acceleration is noisy | Smooth ROC with 3-period SMA before computing acceleration |
| Conflicting signals (mom LONG + hzscore SHORT) | Use ADX threshold to suppress hzscore in strong trends |
| In range-bound chop, momentum signals fire on small moves | Require ADX > 20 to filter; momentum signals should be secondary to mean reversion |

---

## Open Question for T

**Should momentum signals operate as the PRIMARY signal in confluence** (replacing or supplementing hzscore in trending markets), or as a **filter/veto** on mean reversion signals (suppressing hzscore when ADX is high)?

Two modes:
- **Mode A — Primary:** `mom-hermes` fires as primary, `hzscore` acts as confirmation filter
- **Mode B — Veto:** `hzscore` fires first; if `mom-hermes` ALSO fires in the SAME direction, boost confidence; if `mom-hermes` fires in the OPPOSITE direction, suppress hzscore

Mode B is safer because it doesn't change the system's existing behavior in ranging markets. Mode A is more aggressive and could improve trend capture but requires more testing.
