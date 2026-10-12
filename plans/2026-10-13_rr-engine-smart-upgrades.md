# RR Engine Smart Upgrades — Plan

**Created:** 2026-10-13
**Status:** SPEC — ready for implementation
**Priority:** #3 (timeframe-aware) is CEO's favorite
**Context:** After 4 rounds of bug fixes, the RR engine correctly kills ~8% of real signals (down from 55%). But it's still backward-looking — it measures R:R from current price using existing S/R levels, which gives bad R:R during pumps/dumps when price has already moved. These upgrades make it forward-looking.

---

## Upgrade 1: Signal Quality Context

**Problem:** A signal that passed confluence + trend alignment (1.40x boost) gets the same R:R treatment as a weak signal. The engine kills it at the last step regardless of how many other filters it passed.

**Solution:** Thread `signal_type` into `rr_confidence_multiplier()`. When the signal has high confluence (2+ sources) or trend alignment boost, soften the R:R hard block.

**Implementation:**
- Add `signal_quality` parameter to `rr_confidence_multiplier()` (0.0-1.0, where 1.0 = all other filters passed with boosts)
- When `signal_quality > 0.7`: lower the hard block threshold from 0.55 to 0.35
- When `signal_quality > 0.9`: no hard block at all (penalty only)
- Thread from `signal_compactor._score_signal()` — it already has `source` (confluence count) and `reg_mult` (trend alignment)

**Constants:**
```
RR_ENGINE_QUALITY_SOFTEN_THRESHOLD = 0.7  # quality above this softens hard block
RR_ENGINE_QUALITY_HARD_BYPASS = 0.9       # quality above this skips hard block entirely
RR_ENGINE_QUALITY_SOFTENED_RR = 0.35      # softened hard block threshold
```

**Risk:** Too-lenient hard block for high-quality signals that still have bad R:R. Mitigated by: only softening, never removing the 0.70x penalty.

---

## Upgrade 2: Momentum-Aware R:R

**Problem:** During a dump, SHORT R:R looks bad because price has already dropped — the nearest support (TP) is close, the nearest resistance (SL) is far. The engine measures reward from where price IS, not where the dump is HEADING.

**Solution:** When price is actively moving in the trade direction, project the TP target beyond the nearest S/R using recent momentum.

**Implementation:**
- Read last 5 candles from `candles_5m` to compute 5-minute momentum (price change %)
- If momentum is aligned with trade direction (dump → SHORT, pump → LONG):
  - Extend TP target by `momentum_pct × MOMENTUM_TP_EXTENSION` (e.g., 1.0×)
  - Only extend up to the next S/R level (don't overshoot structure)
- If momentum is against trade direction: no extension (standard R:R)

**Constants:**
```
RR_ENGINE_MOMENTUM_TP_EXTENSION = 1.0   # extend TP by 1× recent momentum
RR_ENGINE_MOMENTUM_MIN_PCT = 0.3        # minimum momentum% to trigger extension
RR_ENGINE_MOMENTUM_MAX_EXTENSION = 0.02 # cap extension at 2%
```

**Risk:** Extending TP during momentum could set unreachable targets. Mitigated by: cap extension at 2% and only extend to next S/R level.

---

## Upgrade 3: Timeframe-Aware SL/TP (CEO FAVORITE)

**Problem:** A scalping signal (tight 0.5% TP) and a swing signal (3% TP) get the same R:R treatment. The engine doesn't know the trade's intended timeframe, so it applies the same SL/TP caps regardless.

**Solution:** Accept a timeframe hint from the signal and scale SL/TP expectations accordingly.

**Implementation:**
- Add `timeframe` parameter to `evaluate_rr()` and `rr_confidence_multiplier()`
- Map timeframes to SL/TP profiles:

| Timeframe | SL range | TP range | Min R:R | Use case |
|-----------|----------|----------|---------|----------|
| 1m | 0.3-0.8% | 0.3-1.0% | 1.0 | Scalping |
| 5m | 0.5-1.5% | 0.5-2.0% | 1.2 | Day trading |
| 15m | 0.8-2.0% | 1.0-3.0% | 1.5 | Swing |
| 1h | 1.0-2.0% | 1.5-4.0% | 1.8 | Swing |
| 4h | 1.5-3.0% | 2.0-6.0% | 2.0 | Position |

- Thread from signal files (most already have `timeframe` in their `add_signal()` call)
- Default to 5m when not provided (most common signal timeframe)

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

**Impact:** 1m scalping signals stop being killed by 15m-sized SL/TP caps. 4h swing signals get proper wide targets. The engine finally understands the trade's intent.

**Risk:** Signals may not pass accurate timeframes. Mitigated by: default to 5m (most common), and timeframes are advisory (hard block still applies if R:R is terrible regardless of timeframe).

---

## Upgrade 4: Fibonacci Retracement Levels

**Existing code to reuse (search before building):**
- `hh_hl_signals.py:342-361` — already computes Fibonacci 61.8% retracement from HH/HL swings
- `coin_tracker_analysis.py:336` — "Relaxed Fibonacci retracements"
- `hermes_constants.py:1566` — `HH_HL_PB_MAX_PULLBACK_PCT = 0.618`
- `hh_hl_signals.py:289` — Pullback zone 23.6%–61.8% Fibonacci

**Problem:** The S/R map only uses swing highs/lows and order book levels. Fibonacci retracement levels (0.236, 0.382, 0.500, 0.618, 0.786) are widely-watched structural levels that act as support/resistance. They're especially useful when there's no clear S/R (open skies trades).

**Solution:** Add Fibonacci levels derived from the most recent significant swing to the S/R map. Reuse the swing detection logic from `hh_hl_signals.py` (already battle-tested).

**Implementation:**
- Import `_find_swing_highs_lows()` from `hh_hl_signals.py` (or reuse `rs_signals._find_swing_highs_lows()`)
- Identify the most recent significant swing (last swing high → last swing low, or vice versa)
- Compute Fibonacci retracement levels between those two points using the same approach as `hh_hl_signals.py:342-361`:
  - 0.236 (shallow retracement)
  - 0.382 (moderate)
  - 0.500 (half — strongest psychological level)
  - 0.618 (golden ratio — strongest Fibonacci level, already used by HH/HL)
  - 0.786 (deep retracement)
- Add these as S/R levels with `source='FIB'`
- Weight them by swing significance (bigger swing = stronger levels)
- Fibonacci levels are most meaningful on higher timeframes (15m+, 1h, 4h)

**Constants:**
```
RR_ENGINE_FIB_ENABLED = True
RR_ENGINE_FIB_LEVELS = [0.236, 0.382, 0.500, 0.618, 0.786]
RR_ENGINE_FIB_MIN_SWING_PCT = 1.0    # minimum swing size (1%) for meaningful levels
RR_ENGINE_FIB_LOOKBACK = 100          # candles to find the last significant swing
RR_ENGINE_FIB_TIMEFRAME_MIN = '5m'    # only compute on 5m or higher
```

**Why Fibonacci works:**
- 0.618 (golden ratio) is the most watched retracement level globally
- Institutional algorithms cluster orders around these levels
- When no S/R exists (open skies), Fibonacci levels fill the structural gap
- Combined with existing S/R: Fibonacci levels that coincide with swing S/R get higher weight

**Integration with existing S/R:**
- Add to `_build_fib_sr()` in `risk_reward_engine.py`
- Merge into S/R map alongside candle/book/liquidation levels
- Levels that coincide with existing S/R (within 0.3%) get a strength boost

**Risk:** Fibonacci levels are subjective (which swing to use?). Mitigated by: use the most recent significant swing (objective), and only apply on 5m+ timeframes.

---

## Implementation Order

1. **Upgrade 3 (timeframe-aware)** — CEO's favorite, highest impact
2. **Upgrade 4 (Fibonacci)** — fills structural gaps, especially for open skies
3. **Upgrade 1 (signal quality context)** — softens hard block for proven signals
4. **Upgrade 2 (momentum-aware)** — most complex, needs careful testing

## Related Plans

- `plans/structural-awareness-overhaul.md` — integrating Wyckoff/Elliott Wave into execution
- `plans/sl-memory-sr-system-v2.md` — SL zones from historical stop hits
- `brain/specs/risk_reward_engine_spec.md` — original RR engine spec
- `brain/specs/rr_engine_bug_hunt_2.md` — latest bug hunt

## Verification

Each upgrade needs:
1. Bug hunter verification after implementation
2. Shadow mode logging for 7 days
3. Backtest against recent signals (would the upgrade have saved/flagged correctly?)
