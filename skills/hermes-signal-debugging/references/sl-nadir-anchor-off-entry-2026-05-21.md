# SL Tightness: Why Signals Are Right But SL Catches Reversal First

## The Core Problem (Session 2026-05-21)

**Pattern**: Signal fires correctly → trade opens → price moves in our favor → then reverses slightly → **SL hits before TP** → small loss despite correct directional call.

**Root cause**: Two separate bugs interacting.

---

## Bug 1: SL anchored to NADIR, not ENTRY

`compute_atr_sl_tp()` in tpsl_utils.py computes SL from `lowest_price` (SHORT) or `highest_price` (LONG) — the nadir/peak tracker — not from entry price.

```
Example: BSV SHORT
  Entry: 14.937
  Nadir: 14.870 (set by first adverse 1m candle BEFORE first favorable move)
  SL = nadir × (1 + ACCEL_floor 0.70%) = 14.870 × 1.007 = 14.97409
  SL from entry = (14.97409 - 14.937) / 14.937 = 0.248%
  At 3× leverage: 0.248% × 3 = 0.74% loss if hit
  Price then recovered to 14.9545
  SL from current = (14.97409 - 14.9545) / 14.9545 = 0.131%
  → Only $0.0195 away from being stopped out despite correct direction
```

**Why nadir gets set off-entry**: On the first `_collect_atr_updates()` cycle after position open, the nadir/peak is initialized to the first live price tick. If price immediately moved against us (favorable for SHORT direction), nadir < entry for SHORT. The IS_NEW_TRADE check then fires based on `abs(lowest_price - entry) / entry < 0.001` (0.10% tolerance). If nadir is 0.30%+ below entry, IS_NEW_TRADE=false and ACCEL_floor (0.70%) applies instead of INIT_floor (0.30%) — but the anchor is still the wrong nadir.

**IS_NEW_TRADE detection is broken for this flow**:
```
T=0: Entry at 14.937. is_new_trade = True (lowest_price = entry)
T=1: Price drops to 14.890 (first candle, 0.31% below entry → outside 0.10% tolerance)
     is_new_trade = abs(14.890-14.937)/14.937 = 0.31% > 0.10% → FALSE
     ACCEL floor (0.70%) applies
     SL = 14.890 × 1.007 = 14.990
T=2: Price rebounds to 14.9545. Trailing hasn't activated (moved 0.31% in our favor, need 1%)
     SL stays at 14.990. Current is 14.9545.
     SL from current = 0.24% → One more 0.24% adverse move and SL hits.
```

---

## Bug 2: TRAILING_ACTIVATION=1% is too coarse for low-ATR tokens

All 5 open positions (2026-05-21) have ATR < 0.10%:

| Token | ATR | 1% trailing activation | ATR-proportional (3× ATR) |
|-------|-----|----------------------|--------------------------|
| BSV | 0.036% | $0.15 | $0.0075 |
| LINEA | 0.041% | $0.000035 | $0.0000012 |
| IP | 0.078% | $0.0039 | $0.00024 |
| TAO | 0.028% | $2.80 | $0.08 |
| FET | 0.042% | $0.0019 | $0.00006 |

For FET at $0.19: 1% = $0.0019 per share. A 0.13% favorable move (the profit we saw) = $0.00025 — only 13% of the activation threshold. Trailing never starts.

---

## Why This Hurts Specifically Low-ATR Tokens

For tokens with ATR < 0.10%:
- k_eff × ATR = 0.01-0.04% (near zero)
- **Floor (0.70%) dominates everything**
- The floor is applied to the NADIR, not entry
- If nadir is even 0.10% below entry for a SHORT (or above for LONG), the SL is set only 0.60% from entry (0.70% - 0.10% = 0.60%)
- At 5× leverage: 0.60% × 5 = 3% buffer — one 0.20% reversal = -1% loss

---

## The Three-Failure Pattern

```
1. Signal fires at local top (entry near high of day)
2. Price immediately moves against us → nadir set off-entry
3. SL placed from nadir with ACCEL floor (0.70%)
4. Price oscillates → 1% trailing activation never crossed
5. Small reversal → SL hits → small loss
6. Price then continues in original direction (signal was RIGHT!)
```

---

## Fixes Needed (Report — No Changes Made)

1. **SL anchor: compute from ENTRY as absolute floor, not nadir**
   - `SL = max(nadir_based_SL, entry × (1 - MIN_SL_PCT))`
   - Ensures minimum 0.30% (INIT) or 0.70% (ACCEL) buffer from ENTRY regardless of nadir

2. **Trailing activation must be ATR-proportional**
   - `trailing_activation = max(0.002, atr_pct × 3)` — for FET (0.042% ATR): 0.126%
   - Current 1% = $0.0019, ATR-proportional = $0.00024 (8× more responsive)

3. **Profit-taking: if pnl_pct > 1% and SL from current < 0.30%, auto-tighten SL**
   - Prevents "in profit but SL will get hit on small reversal" scenario
   - Lock in 0.5% minimum gain when 1% profit is on the board

4. **IS_NEW_TRADE tolerance should be wider (0.30% not 0.10%)**
   - Current 0.10% tolerance is too tight — first adverse 1m candle fires ACCEL immediately
   - Widen to 0.30% so INIT floor applies longer for new positions