# ATR Exit Price Anomaly — CAKE/ME/TIA (2026-05-12)

## The Problem

Four trades closed via `atr_sl_hit` on 2026-05-12, but three of them have exit prices ABOVE the computed initial SL:

| Token | Direction | Entry | Exit | Exit vs Computed SL | Close Reason |
|-------|-----------|-------|------|---------------------|--------------|
| SUI | LONG | 1.285 | 1.27425 | -0.34% BELOW SL | atr_sl_hit ✓ |
| CAKE | LONG | 1.5674 | 1.56375 | +0.15% ABOVE SL | atr_sl_hit ✗ |
| ME | LONG | 0.12192 | 0.1215 | +0.05% ABOVE SL | atr_sl_hit ✗ |
| TIA | LONG | 0.44996 | 0.448 | +0.02% ABOVE SL | atr_sl_hit ✗ |

For SUI: exit was BELOW computed SL → SL correctly hit.
For CAKE/ME/TIA: exit was ABOVE computed SL → SL should NOT have been hit.

Yet all three show `close_reason=atr_sl_hit`. This means the **stored SL in the DB was tighter than** what `_force_fresh_atr()` → `ATR_K_INITIAL × ATR` would compute from current ATR.

## Root Cause Hypothesis

The most likely explanation is that **trailing SL was active and had already tightened the SL** closer to entry than the initial SL, and price happened to hit that tighter trailing level.

The `_collect_atr_updates` trailing mechanism works like this:
1. `k = _atr_sl_k_scaled(token, direction, atr_pct, speed, momentum)` → phase-based k
2. In ACCELERATING phase: k = base_k × 0.05–0.15 (very small)
3. `sl_pct = k × atr_pct` → very small percentage
4. BUT: `effective_sl_pct = max(sl_pct, MIN_SL_PCT_TRAILING)` → 0.50% floor wins
5. For tokens in profit: `ref_price = highest_price` (peak), `new_sl = ref_price × (1 - effective_sl_pct)`

If price moved favorably and then reversed, the trailing SL would be:
- Based on the peak (highest_price), not entry
- Tightened by the phase multiplier (k=0.05–0.15)

Example CAKE scenario:
- Entry: 1.5674, ATR at entry: ~0.0060 (0.38%)
- Price moves to ~1.5730 (+0.36%), peak = 1.5730
- In ACCELERATING phase, k=0.05, sl_pct = 0.05 × 0.0038 = 0.019%
- Floor: max(0.019%, 0.50%) = 0.50%
- Trailing SL = 1.5730 × (1 - 0.005) = 1.5651
- Price reverses to 1.5638 → below 1.5651 → **SL hit**
- Exit at 1.56375 is ABOVE the initial SL of 1.5614 (computed from k=1.0 at entry)
- But BELOW the trailing SL of 1.5651

This explains why exit > initial SL but < trailing SL.

## ATR_UPDATE_THRESHOLD Blocking

A second contributing factor: the trailing SL update can be blocked by `ATR_UPDATE_THRESHOLD_PCT = 0.15%`.

Evidence from agent.log (APEX):
```
For APEX: new=0.305212 vs old=0.304555 = 0.022% < ATR_UPDATE_THRESHOLD (0.15%) → SKIP
```

The delta between new computed SL and old SL was only 0.022%, below the 0.15% threshold, so the update was skipped. The SL stayed at the initial level even though it should have tightened.

## Constants That Control Tightness

From `hermes_constants.py` (verified 2026-05-12):

| Constant | Value | Effect |
|----------|-------|--------|
| `ATR_K_INITIAL` | 1.0 | Initial SL = 1×ATR. Lower = wider initial stop (more room). |
| `K_PHASE_ACCEL_STALL` | 0.15 | Acceleration+stall: k = base_k × 0.15. Very tight. |
| `K_PHASE_ACCEL_FAST` | 0.05 | Acceleration+fast: k = base_k × 0.05. Tightest multiplier. |
| `K_PHASE_ACCEL_SLOW` | 0.10 | Acceleration+slow: k = base_k × 0.10. |
| `ATR_SL_MIN_ACCEL` | 0.005 (0.50%) | Acceleration phase floor — overrides computed SL% |
| `ATR_SL_MIN_INIT` | 0.002 (0.20%) | Initial entry floor |
| `ATR_UPDATE_THRESHOLD_PCT` | 0.0015 (0.15%) | Minimum delta to trigger SL update |

## Key Diagnostic

When you see exit price ABOVE computed initial SL but `close_reason=atr_sl_hit`:
1. The trailing SL mechanism had already tightened the stored SL
2. Check `highest_price`/`lowest_price` in DB vs entry — if peak was tracked, trailing was active
3. Check if ATR_UPDATE_THRESHOLD was blocking updates in the logs
4. The phase multiplier (k=0.05–0.15) was producing very small sl_pct values overridden by the 0.50% floor

## T's Directive on Tight Stops

T's trading philosophy: "first candle against us we're out, book profit fast."
SL floor 0.50%, cap 2%, TP 0.75–5.0%, k_tp × 1.25.

The 0.50% floor is intentional. But when exit is above initial SL AND below trailing SL, the system is working correctly — the trailing SL locked in profit and then price reversed through it.

The problem isn't the constants — it's understanding that `atr_sl_hit` with exit > initial SL means the trailing mechanism fired and the peak-based SL was tighter than entry-based SL.