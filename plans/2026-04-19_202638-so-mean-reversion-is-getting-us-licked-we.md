# Plan: Trend-Following Signals for Hermes

## Goal

Replace or supplement mean-reversion signals (hzscore, hwave) with trend-following signals that ride momentum rather than fade it. The core thesis: in strongly trending crypto markets, mean-reversion gets stopped out repeatedly while trend-following captures larger directional moves.

## Context

- **Problem:** hzscore fires when z-score is displaced from mean (e.g., z=-2 → LONG, expecting bounce back). In strong trends, price stays displaced for long periods, burning through SL/TP before mean reversion fires.
- **What we've seen:** 43% of executed signals are re-trades of same token+direction, many losses from failed mean-reversion entries.
- **Counter-regime signals:** Currently let through per-coin regime filter, but the signal TYPES (hzscore, hwave) are inherently mean-reversion.
- **Surfing thesis:** When T's surfing theory aligns with trend-following — ride the wave in the direction of the trend, not against it.

---

## Proposed Signal: `trend-is-your-friend`

### Core Logic

Only fire directional signals when they align with the dominant trend. Specifically:

1. **Identify trend direction** using a longer TF moving average (e.g., 200 EMA on 4H or 1D)
2. **Identify momentum** using shorter TF alignment (e.g., 50 EMA above/below 200 EMA)
3. **Fire only in direction of trend** — if 200 EMA is sloping up (uptrend), only LONG signals fire; SHORT signals suppressed

This is NOT a new indicator — it's a **filter layer** applied to existing signals. Signals like hzscore+ (SHORT when z displaced above mean) would be blocked in an uptrend.

### Implementation Options

#### Option A: Trend Filter on Existing Signals (Simpler)
- Compute EMA slope on 4H or 1D for the token
- If `ema_200_4h > ema_200_4h[10 bars ago]` → uptrend → only LONG hzscore/hwave signals fire
- If `ema_200_4h < ema_200_4h[10 bars ago]` → downtrend → only SHORT hzscore/hwave signals fire
- If no clear slope → neutral → all signals fire normally

**Pros:** Minimal new code, leverages existing signal infrastructure
**Cons:** Still fires mean-reversion signals, just in the trend direction

#### Option B: Pure Trend-Following Signal (New `trend-momentum` type)
- Track rate-of-change (ROC) or momentum across multiple TFs
- Fire `trend+` when: 4H/1H/15m all have positive ROC and ADX > 25
- Fire `trend-` when: 4H/1H/15m all have negative ROC and ADX > 25
- **Confidence based on:** ADX strength (higher ADX = stronger trend = higher confidence)

**Pros:** True momentum signal, matches what T describes as "with the trend"
**Cons:** Needs ADX computation, new signal type, more complex

#### Option C: ADX + DI Crossover Signal (Balanced)
- Compute ADX and +DI/-DI from HL candles
- `trend+` (LONG): +DI crosses above -DI AND ADX > 20 (confirming uptrend)
- `trend-` (SHORT): -DI crosses above +DI AND ADX > 20
- Confidence: ADX value directly (ADX 20→40 = low/med, ADX 40→60 = high, 60+ = very high)

**Pros:** Classic technical analysis, proven in crypto markets, straightforward computation
**Cons:** ADX is a new computation not currently in the codebase

---

## Recommended: Option C (ADX+DI Crossover)

### Why ADX+DI?
- **Purpose-built for this:** ADX measures trend strength, +DI/-DI crossover gives exact entry direction
- **Crypto-proven:** Works particularly well on 24/7 crypto markets with clear trending regimes
- **HTF-compatible:** Computed from HL candle data, same as existing signals
- **Confluence-friendly:** Can combine with existing signals (e.g., hzscore+DI crossover = high confidence)

### Parameters
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| ADX threshold | > 20 | Minimum to confirm trending (not ranging) |
| DI crossover | +DI vs -DI | Directional entry |
| Lookback | 14 periods (standard) | Standard Wilder ADX period |
| Timeframe | 1H primary, confirm with 4H | Balance between signal speed and reliability |

### Confidence Scale
| ADX Range | Confidence | Interpretation |
|-----------|------------|----------------|
| 20-30 | 60-70 | Weak trend, low conviction |
| 30-40 | 70-80 | Moderate trend |
| 40-50 | 80-85 | Strong trend |
| 50+ | 85-90 | Very strong trend |

---

## Step-by-Step Implementation Plan

### Step 1: Add ADX+DI computation utility
**File:** `signal_gen.py` (new function)

```
_compute_adx_di(token, timeframe='1h', period=14)
  - Fetch HL candle data for token/timeframe
  - Compute True Range (TR), Directional Movement (+DM, -DM)
  - Smooth with Wilder's smoothing (same period)
  - Compute +DI, -DI, DX, then ADX = Wilder EMA of DX
  - Return: (adx_value, plus_di, minus_di, direction)
```

**Reference:** Standard ADX formula (Wilder, 1978) — all steps computable with existing HL candle data.

### Step 2: Add `_run_adx_di_signals()` function
**File:** `signal_gen.py`

```
def _run_adx_di_signals():
  For each candidate token:
    - Get ADX, +DI, -DI for 1H and 4H
    - Check 4H first: must confirm trending (ADX > 20)
    - Check 1H for crossover: +DI > -DI for LONG, -DI > +DI for SHORT
    - ADX crossover confirmation: ADX crossed above 20 on this bar (new trend)
    - Confidence = ADX value (scaled to signal range)
    - Call add_signal(type='adx_di', source='adx+' or 'adx-')
    - Return count of signals added
```

### Step 3: Integrate into signal_gen main loop
**File:** `signal_gen.py`

- Add call to `_run_adx_di_signals()` in the main loop (same section as mtf_macd, hzscore)
- Add to `analyze_token()` or equivalent hot-token loop
- Signals should be independent — not replacing hzscore/hwave, adding a new source

### Step 4: Ensure signal_compactor handles new type
**File:** `signal_compactor.py`

- Verify `adx+` and `adx-` are NOT in SIGNAL_SOURCE_BLACKLIST
- Verify new signals pass through Step 11 (open position filter) and Step 15 (entries_count)
- No changes likely needed if signal_compactor is schema-agnostic

### Step 5: Test with paper trading
- Run pipeline for 1-2 days with new signals active
- Monitor: Do `adx+` signals correlate with profitable trades vs `hzscore`?
- Check: Do `adx+` signals appear for tokens that are already trending (confirming trend-first thesis)?

### Step 6: Optional — Trend Filter on hzscore (if Option A also desired)
If Option C works well and T wants to also filter existing signals:

```
Modified hzscore/hwave call in signal_gen.py:
  - Compute ema_200 slope on 4H
  - If uptrend AND hzscore trying to SHORT → suppress
  - If downtrend AND hzscore trying to LONG → suppress
```

---

## Files Likely to Change

| File | Change |
|------|--------|
| `/root/.hermes/scripts/signal_gen.py` | Add `_compute_adx_di()`, `_run_adx_di_signals()`, integrate into main loop |
| `/root/.hermes/scripts/signal_compactor.py` | Likely no change, verify `adx+/-` passthrough |
| `brain/trading.md` | Document new signal type and results |

---

## Validation

1. **Smoke test:** `python3 -c "import signal_gen as sg; print(sg._compute_adx_di('BTC', '1h'))"` returns ADX > 0
2. **Cycle test:** Run signal_gen for 1 cycle, check signals DB has new `adx+`/`adx-` entries
3. **Compactor test:** Run signal_compactor, verify `adx+`/`adx-` appear in hotset
4. **Paper trade:** Monitor for 24-48h, compare trade outcomes for `adx+` vs `hzscore` signals

---

## Risks & Tradeoffs

| Risk | Mitigation |
|------|------------|
| ADX is lagging — crossover confirmed after move started | Use with other confirmations; ADX crossover confirms trend START, not mid-trend |
| ADX needs sufficient history (14+ bars) | Works fine for liquid tokens; low-liquidity may have noisy ADX |
| New signals compete with existing for slot in hotset | Existing signals still fire; adx adds another confluent source |
| ADX computation complexity | Standard formula, ~50 lines of Python, well-tested |

---

## Open Questions for T

1. **ADX parameters:** Use standard 14-period, or shorter/longer for crypto? (Shorter = more signals but more noise)
2. **Confirmation required:** Should `adx+` require hzscore also present (confluence), or fire standalone?
3. **Trend filter on hzscore:** Also implement Option A to suppress counter-trend hzscore, or just add new adx signal?
4. **HTF confirmation:** Require 4H ADX confirm, or is 1H ADX alone sufficient?
