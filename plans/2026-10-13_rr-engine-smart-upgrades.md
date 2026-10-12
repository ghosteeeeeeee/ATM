# RR Engine Smart Upgrades — Plan

**Created:** 2026-10-13
**Status:** SPEC — ready for implementation
**Priority:** Signal starvation is the #1 issue. Momentum-aware R:R (#2) is the core fix.

---

## The Core Problem: Signal Starvation

**Every signal type is being crushed by the RR engine at the extremes — exactly when trades have the most edge.**

**Example:** BTC at 82,315 (dumped from 83,086), RSI 16.1, z-score -2.4. The RR engine says SHORT R:R=0.75 grade D — "poor." Twenty SHORT signals across two batches, every single one crushed by grade C/D R:R.

**Why this happens:** The engine measures R:R at the **current price** using existing S/R levels:
- During a dump: TP is close (price near support), SL is far (price just broke down from resistance) → R:R looks terrible
- During a pump: TP is close (price near resistance), SL is far (price just broke up from support) → R:R looks terrible
- **But the dump/pump is CONTINUING** — the trade thesis is momentum continuation, not structural bounce

**The engine is measuring risk/reward at the bottom of the dump, not at the top.** It penalizes entries for being extended, which is exactly when the trade has the most edge. This is a structural flaw, not a tuning issue.

**Evidence:** 
- 20 SHORT signals across two batches — all crushed by grade C/D R:R
- BTC SHORT at RSI 16.1 (extreme oversold) — R:R=0.75 "poor"
- The signal passed every other filter (confluence, chop gate, continuum, trend alignment)
- RR engine killed it at the last step

---

## Upgrade 1: Momentum-Aware R:R (CORE FIX)

**Problem:** The engine measures R:R from current price using nearest S/R. During a dump, price is already near support (small TP) and far from resistance (large SL). But the dump is continuing — the TP should be projected further down using recent velocity.

**Solution:** When price is actively moving in the trade direction, project the TP target using recent momentum, not just the nearest S/R level.

**Implementation:**
- Read last 5 candles from `candles_5m` to compute 5-minute velocity (price change % per candle)
- If momentum is aligned with trade direction (dump → SHORT, pump → LONG):
  - Compute projected TP = current price + (velocity × MOMENTUM_PROJECTION_BARS)
  - Use this projected TP if it's further than the nearest S/R (extends the target)
  - Cap projection at `MOMENTUM_TP_MAX_EXTENSION` (e.g., 2%)
- If momentum is against trade direction: no projection (standard R:R)
- **Key:** The projected TP represents "where the dump is heading," not "where the nearest floor is"

**Example:**
- BTC at 82,315, dumping. Last 5 candles: -0.3% each = -1.5% total velocity
- Nearest support: 82,000 (0.38% below) → TP=0.38%
- Projected TP: 82,315 × (1 - 0.015) = 81,080 (1.5% below) → TP=1.5%
- SL (nearest resistance): 82,800 (0.59% above)
- R:R without projection: 0.38/0.59 = 0.64 (blocked)
- R:R with projection: 1.5/0.59 = 2.54 (passes)

**Constants:**
```
RR_ENGINE_MOMENTUM_PROJECTION = True      # master switch
RR_ENGINE_MOMENTUM_BARS = 5               # candles for velocity calculation
RR_ENGINE_MOMENTUM_MIN_VELOCITY = 0.1     # minimum velocity% per candle to activate
RR_ENGINE_MOMENTUM_TP_MAX_EXTENSION = 0.02 # cap projection at 2%
RR_ENGINE_MOMENTUM_PROJECTION_BARS = 3    # project velocity forward N candles
```

**Risk:** Projecting TP too aggressively sets unreachable targets. Mitigated by: cap at 2%, only project when velocity is confirmed (5 candles), and still respect hard SL floor.

---

## Upgrade 2: Timeframe-Aware SL/TP

**Problem:** A 1m scalping signal and a 4h swing signal get the same R:R treatment. The engine applies the same SL/TP caps regardless of trade intent.

**Solution:** Accept a timeframe hint and scale SL/TP expectations.

**Implementation:**
- Add `timeframe` parameter to `evaluate_rr()` and `rr_confidence_multiplier()`
- Map timeframes to SL/TP profiles:

| Timeframe | SL range | TP range | Min R:R |
|-----------|----------|----------|---------|
| 1m | 0.3-0.8% | 0.3-1.0% | 1.0 |
| 5m | 0.5-1.5% | 0.5-2.0% | 1.2 |
| 15m | 0.8-2.0% | 1.0-3.0% | 1.5 |
| 1h | 1.0-2.0% | 1.5-4.0% | 1.8 |
| 4h | 1.5-3.0% | 2.0-6.0% | 2.0 |

- Default to 5m when not provided (most common)

**Constants:**
```
RR_ENGINE_TF_PROFILES = {
    '1m':  {'sl_min': 0.003, 'sl_max': 0.008, 'tp_min': 0.003, 'tp_max': 0.010, 'min_rr': 1.0},
    '5m':  {'sl_min': 0.005, 'sl_max': 0.015, 'tp_min': 0.005, 'tp_max': 0.020, 'min_rr': 1.2},
    '15m': {'sl_min': 0.008, 'sl_max': 0.020, 'tp_min': 0.010, 'tp_max': 0.030, 'min_rr': 1.5},
    '1h':  {'sl_min': 0.010, 'sl_max': 0.020, 'tp_min': 0.015, 'tp_max': 0.040, 'min_rr': 1.8},
    '4h':  {'sl_min': 0.015, 'sl_max': 0.030, 'tp_min': 0.020, 'tp_max': 0.060, 'min_rr': 2.0},
}
```

---

## Upgrade 3: Signal Quality Context

**Problem:** A signal that passed confluence + trend alignment (1.40x boost) gets the same R:R treatment as a weak signal.

**Solution:** Thread signal quality into `rr_confidence_multiplier()`. High-quality signals get softer R:R requirements.

**Implementation:**
- Add `signal_quality` parameter (0.0-1.0)
- `signal_quality > 0.7`: lower hard block from 0.55 to 0.35
- `signal_quality > 0.9`: no hard block (penalty only)
- Thread from `signal_compactor._score_signal()` (already has confluence count + trend alignment)

---

## Upgrade 4: Fibonacci Retracement Levels

**Existing code to reuse:**
- `hh_hl_signals.py:342-361` — Fibonacci 61.8% retracement from HH/HL swings
- `coin_tracker_analysis.py:336` — "Relaxed Fibonacci retracements"
- `hermes_constants.py:1566` — `HH_HL_PB_MAX_PULLBACK_PCT = 0.618`

**Problem:** S/R map only uses swing highs/lows and order book. Fibonacci levels (0.236, 0.382, 0.500, 0.618, 0.786) are widely-watched structural levels, especially useful for open skies trades.

**Solution:** Add Fibonacci levels from the most recent significant swing to the S/R map. Reuse `hh_hl_signals.py` logic.

---

## Implementation Order

1. **Upgrade 1 (momentum-aware)** — core fix for signal starvation, highest impact
2. **Upgrade 2 (timeframe-aware)** — CEO's favorite, scales expectations correctly
3. **Upgrade 3 (signal quality)** — softens hard block for proven signals
4. **Upgrade 4 (Fibonacci)** — fills structural gaps

## Related Plans
- `plans/structural-awareness-overhaul.md` — integrating Wyckoff/Elliott Wave
- `plans/sl-memory-sr-system-v2.md` — SL zones from historical stops
- `brain/specs/risk_reward_engine_spec.md` — original spec
- `brain/specs/rr_engine_bug_hunt_2.md` — latest bug hunt

## Verification
Each upgrade needs:
1. Bug hunter verification after implementation
2. Shadow mode logging for 7 days
3. Backtest: would the upgrade have saved the 20 crushed SHORT signals?
