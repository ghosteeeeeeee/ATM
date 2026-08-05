# ATR SL Floor Override — Phase Multipliers Bypassed (2026-05-24)

## Finding

In 24h of trading (49 trades, 2026-05-24):
- `profit-monster`: 14 trades avg +1.14% → ALL winners
- `atr_sl_hit`: 30 trades avg -0.61% → ALL losers

**Root cause:** ATR phase multipliers (0.01-0.07 for ACCEL phase) are overridden by the 1.0% floor in almost all real trades.

## How the Override Happens

1. `position_manager.py` calls `get_momentum_stats(token)` → passes to `tpsl_utils.compute_atr_sl_tp()`
2. `tpsl_utils.py` line 108: `if momentum_stats is None: return base_k`
3. If `momentum_stats` is None → `base_k = ATR_K_NORMAL_VOL = 1.0` → no phase scaling
4. For a coin with atr_pct=1.5%: `sl_pct = 1.0 × 1.5% = 1.5%`
5. Floor: `ATR_SL_MIN_ACCEL = 0.01 (1.0%)` → caps sl_pct at 1.0%
6. **Result:** The phase multiplier (meant to tighten SL on ACCEL to 0.01×) is completely bypassed — floor overrides everything.

## The "First Candle Out" Policy

T wants: "first candle against us we're out" — cut losing trades in 1-3 bars, let winners run.

| Token | Direction | PnL% | Duration | Entry Price | SL | What Happened |
|-------|-----------|------|----------|-------------|-----|---------------|
| 2Z SHORT | SHORT | +0.85% | 51min | 0.10587 | 0.10602 | Immediate move down → profit-monster exit |
| MORPHO SHORT | SHORT | -0.91% | 56min | 2.0889 | 2.1098 | Price went UP against SHORT (guardian_sl) |
| GALA SHORT | SHORT | -1.67% | 1h | 0.003243 | 0.003267 | Immediate move against SHORT |
| ME LONG | LONG | +4.27% | 49min | 0.09528 | 0.10129 | Huge winner but ATR SL hit early at +4.27% |

**ME was the biggest insight:** Signal was correct (+4.27%), but ATR SL gave back $0.06 of $0.43 profit. 1.0% initial floor was too tight — price pulled back 1% during consolidation and hit SL before the full move.

## What ATR Thresholds Would Implement "First Candle Out"

```python
ATR_SL_MIN_INIT = 0.004   # was 0.01 — 0.4% floor (catches 3-bar reversals)
ATR_SL_MIN_ACCEL = 0.003  # was 0.01 — 0.3% floor (tighten after first move)
```

With these on 2Z SHORT (ATR ~1.5%, entry 0.10676):
- sl_pct = 1.0 × 1.5% = 1.5% → floored to 0.4%
- SL = 0.10676 × (1 + 0.004) = 0.10719
- First candle 0.5% adverse → hits SL at 0.10719 → exit -0.4%
- vs current 1.0% stop → exit at -1.0%

## Key Insight: INIT and ACCEL Floors Are Currently Identical

```python
ATR_SL_MIN_INIT  = 0.01  # was 0.01 — 1.0%
ATR_SL_MIN_ACCEL = 0.01  # was 0.01 — 1.0% (SAME VALUE)
```

When INIT == ACCEL, there is NO trailing tightening — price moves either direction and the floor is the same. For "first candle out":
- INIT should be wider (entry needs breathing room)
- ACCEL should be tighter (established trades tighten on first adverse move)

## Winners vs Losers — What Made Winners Different

From 24h analysis of 16 winning trades (avg +1.14%):
- 2Z SHORT: immediate favorable move in first 5 min
- SKR LONG: held 9+ hours, price moved up consistently
- TIA SHORT: 5 consecutive RS shorts, price dropped steadily
- XRP LONG: brief clean entry, moved up 1.2%

Losers commonalities:
- Entered at resistance in consolidation (bounce setups that failed)
- No momentum confirmation — rsi_14, macd_hist all NULL in signals
- Re-fired same signal 5-10 times in 20 min (COOLDOWN=5 too short)
- Extreme z-score (z > 4.0) with no divergence check for SHORT direction

## Related

- `hermes-signal-debugging/references/divergence-long-only-short-vulnerable-2026-05-24.md` — SHORT divergence is unprotected
- `tpsl_utils.py` line 108: `if momentum_stats is None: return base_k` — phase bypass when momentum unavailable