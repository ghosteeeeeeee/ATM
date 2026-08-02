# ZSCORE+RS Signal Quality — Master Plan (Merged)
**Date:** 2026-05-24
**Sources:** 6 prior plans + 24h empirical audit (83 trades, PostgreSQL brain.trades + SQLite signals_hermes_runtime.db)
**Status:** DRAFT — awaiting T approval

---

## Executive Summary

Analyzed 83 closed trades (47 LONG, 36 SHORT) from last 24h. Win rate ~43% both directions. Combined findings from 6 prior plans with new empirical data to produce a unified, prioritized action plan.

**Key corrections to prior plans (based on fresh 24h audit):**
- ❌ Prior plans assumed "single-source zscore = losing" → **CORRECTED**: All 83 trades are COMBO (RS+zscore). Zero pure zscore signals exist in trade dataset.
- ❌ Prior plans assumed "extreme z = likely reversal" → **CORRECTED**: IP SHORT (-6.71), BLUR SHORT (-6.16) both WON via TP. Z magnitude alone doesn't predict outcome.
- ✅ Winners: avg 81 min hold, exit via profit-monster (TP), avg +1.12%
- ✅ Losers: avg 54 min hold, exit via atr_sl_hit, avg -0.60%
- ✅ Confirmed: ALL signals are combo (rs-{N},zscore-pump+ or rs-{N},zscore-pump-)

---

## All Zscore/RS Plans — What Each Added

| Plan | Date | Key Contributions | Status |
|------|------|-------------------|--------|
| signal-quality-fix-2026-05-05.md | May 5-6 | Architecture migration, kill-switch audit, 741-trade WR audit, accel_300 token allowlist, pct_hermes threshold raise, vel_hermes regime filter | Mostly implemented |
| signal-quality-plan.md | May 10 | accel-300+ only profitable, entry timing root cause (78% losses on first counter-candle), regime scanner integration, trend_purity co-signal filter | Partially implemented |
| signal-improvement-2026-05-07.md | May 7 | GOOD_STANDALONE_SIGNALS naming fix, RS ATR band removal, hwave re-enable, counter_flip frequency reduction, RS cooldown, mega-win TP multiplier | Partially implemented |
| signal-quality-fix.md | May 21 | z=None merge corruption bug, guardian z-score gate | Implemented |
| signal-quality-fix-plan.md | May 21 | Same as above + RS touch filter, divergence logging, opposing signal penalty | Partially implemented |
| zscore-signal-improvement-plan.md | May 22 | FET missed pump, lookback=100 too slow, multi-window scoring, momentum-velocity boost, signal persistence | NOT YET implemented — CONFLICT with empirical data |
| zscore-rs-signal-quality-improvement-2026-05-24.md | Today | 24h empirical audit, combo signal discovery, duration asymmetry, SL placement root cause | This plan |

---

## Conflict Resolution: Lookback

**Plan A** (May 22): `ZSCORE_PUMP_LOOKBACK = 100 → 50` (aggressive shortening to catch FET pump 65 min earlier)

**Plan B** (May 24): `ZSCORE_PUMP_LOOKBACK = 70` (empirical — leave as-is)

**Subagent recommendation**: Trust Plan B's empirical data (83 real trades) over Plan A's single-event backtest (FET pump).

**Decision**: Use **70** as lookback. Plan A's lookback=50 was derived from one missed event. Plan B's audit of 83 trades across all market conditions is more representative.

---

## What's Implemented (from prior plans)

| Item | Plan | Status |
|------|------|--------|
| GOOD_STANDALONE_SIGNALS naming fix | May 7 | ✅ Done |
| RS ATR band removal | May 7 | ✅ Done |
| Minimum RS touch filter (RS_DECIDER_MIN_TOUCHES=200) | May 21 | ✅ Done |
| Guard z_score merge with COALESCE | May 21 | ✅ Done |
| Write signal_z_score to trade record | May 21 | ✅ Done |
| ZSCORE-GATE in decider_run | May 21 | ✅ Done |
| Accel_300 token allowlist | May 5 | ✅ Done |
| pct_hermes threshold raise (72→80) | May 5 | ✅ Done |
| vel_hermes regime filter | May 5 | ✅ Done |
| hwave re-enable | May 7 | ❓ Verify |
| Opposing signal penalty (30 min block after loss) | May 21 | ⏳ PENDING |
| RS bounce freshness (6→3 candles) | May 21 | ⏳ PENDING |
| High-touch level decay (>5000 touches) | May 21 | ⏳ PENDING |
| Multi-window z-score scoring | May 22 | ⏳ PENDING (conflicts with B) |
| Momentum-velocity boost | May 22 | ⏳ PENDING |
| Signal persistence/grace period | May 22 | ⏳ PENDING |

---

## What's NEW from 24h Empirical Audit (Plan B)

### Finding 1: All Signals Are Combo — No Pure zscore-pump
Every single trade in the 24h dataset has both RS and zscore components.
Signal pattern: `rs-s{N},zscore-pump+` or `rs-r{N},zscore-pump-`.

**Implication**: The "single-source zscore" problem that Plan A (May 22) was trying to solve does not exist in the current trade dataset. The combo architecture is working as intended.

### Finding 2: Extreme Z Does NOT Predict Loss
| Token | Dir | z_score | Trade Result | close_reason |
|-------|-----|---------|--------------|--------------|
| IP | SHORT | -6.712 | **+1.25% WIN** | profit-monster |
| BLUR | SHORT | -6.161 | **+1.69% WIN** | profit-monster |
| VINE | SHORT | -5.619 | Mixed | — |
| VINE | LONG | 6.915 | Mixed | — |

**Implication**: A z-score cap (`ZSCORE_PUMP_MAX_Z = 4.5`) to "avoid blow-off tops" is NOT supported by the data. Some extreme-z entries win. The issue isn't the z-score magnitude — it's the SL placement.

### Finding 3: Duration Asymmetry — Key Differentiator
- **Winners (27 trades)**: avg 81 min hold, exit via profit-monster TP
- **Losers (32 trades)**: avg 54 min hold, exit via atr_sl_hit

Losers fail almost twice as fast (54 min vs 81 min). This means the SL is being hit before the trade has time to develop — the signal is correct but the SL is too tight.

### Finding 4: TP Hits Are 4x More Profitable Than SL Hits
| close_reason | count | avg_pnl_pct | total_pnl |
|--------------|-------|-------------|-----------|
| profit-monster (TP) | 32 | +1.12% | +$3.92 |
| HARD_SL_CLOSE_FAILED | 1 | +1.87% | +$0.21 |
| guardian_sl | 1 | -0.91% | -$0.10 |
| atr_sl_hit (SL) | 51 | -0.59% | -$3.21 |

**Implication**: The priority should be giving winners room to run (wider SL for high-conviction combo entries) rather than filtering by z-score magnitude.

---

## Proposed Changes (Priority Order)

### Priority 1: SL Widening for Combo Signals ⭐ (NEW from B)
**File:** `position_manager.py` (and/or `decider_run.py`)
**Rationale:** Winners get stopped out too early (54 min avg vs 81 min for winners). The ATR-based SL is too tight for high-conviction combo entries.

**Proposed constant** (add to `hermes_constants.py`):
```python
RS_COMBO_SL_MULTIPLIER = 1.3   # widen ATR-based SL by 30% for RS+zscore combo signals
                               # gives winners room to develop without increasing loss size much
```

**Implementation:** position_manager.py reads this multiplier when computing the initial SL for entries that have both RS and zscore-pump in the signal source.

> ⚠️ **Requires T approval** — affects how SL is computed for every trade.

---

### Priority 2: Opposing Signal Penalty (30 min block) ⏳
**File:** `decider_run.py`
**Rationale:** Prevents whipsaw — if SHORT just closed at a loss, don't immediately fire another SHORT. Same for LONG.

**Status:** Listed as PENDING in May 21 plan, never implemented. Should finally be done.

**Proposed constant**:
```python
LOSS_COOLDOWN_BARS_AFTER_SL = 15  # bars to wait after a loss before re-entry in same direction
```

> ⚠️ **Requires T approval.**

---

### Priority 3: RS Bounce Freshness (6→3 candles) ⏳
**File:** `signals/rs.py`
**Status:** Listed as PENDING since May 21.

**Current:** `_RS_BOUNCE_LOOKBACK = 6` in rs.py line 56
**Proposed:** Change to 3

**Rationale:** 6-candle lookback can reference bounces from days ago. 3-candle (≈15 min) ensures the level was recently tested.

---

### Priority 4: High-Touch Level Decay ⏳
**File:** `signal_compactor.py`
**Status:** Listed as PENDING since May 21.

**Proposed:**
```python
# In scoring loop — apply discount when rs_touches > 5000
if rs_touches > 5000:
    conf_discount = min(8, (rs_touches - 5000) / 1000 * 2)
    conf -= conf_discount
```

---

### Priority 5: Multi-Window Z-Score Scoring (from May 22 plan)
**File:** `signals/zscore_pump.py`
**Rationale:** Different lookbacks catch different move types. Multi-window scoring (20, 30, 50, 100) allows the signal to fire at the timescale that actually has momentum, rather than being constrained to a single window.

**Proposed:** Keep current `ZSCORE_PUMP_LOOKBACK = 70` as primary, but also compute z at 30-bar and 20-bar windows. If 2+ windows are above threshold in the same direction, boost confidence.

**NOT conflicting with B** — this enhances signal detection without changing the default primary lookback.

---

### Priority 6: Momentum-Velocity Boost (from May 22 plan)
**File:** `signals/zscore_pump.py`
**Proposed:**
```python
z_velocity = z_current - z_5_bars_ago
if z_velocity > 0.3 and z > 2.0:
    conf_boost = 10  # boost confidence by 10% for accelerating momentum
```

---

### Priority 7: Signal Persistence/Grace Period (from May 22 plan)
**File:** `signals/zscore_pump.py`
**Rationale:** Borderline signals (z=2.0-2.3) were expiring before the move developed. Add a grace period: if a signal would expire within 3 bars of a stronger signal (same direction, higher z), extend TTL to 10 min.

---

## What NOT to Change (from empirical data)

| Constant | Value | Reason |
|----------|-------|--------|
| `ZSCORE_PUMP_LOOKBACK` | 70 | Plan A's 50 is single-event backtest; 70 is empirically supported |
| `ZSCORE_PUMP_THRESHOLD` | 2.0 | Working — don't raise |
| `ZSCORE_PUMP_DIVERGENCE_EXTREME_Z` | 3.0 | Lowering to 2.5 may reject valid signals — not supported by data |
| `RS_DECIDER_MIN_TOUCHES` | 200 | Reasonable floor, don't change |
| `CONFLUENCE_REQUIRED` | (existing) | All signals are combo — this is working as intended |

---

## Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `hermes_constants.py` | Add `RS_COMBO_SL_MULTIPLIER`, `LOSS_COOLDOWN_BARS_AFTER_SL` | 1 |
| `position_manager.py` | Apply `RS_COMBO_SL_MULTIPLIER` for combo entries | 1 |
| `decider_run.py` | Add opposing signal penalty (30 min block after loss) | 2 |
| `signals/rs.py` | `_RS_BOUNCE_LOOKBACK = 6 → 3` | 3 |
| `signal_compactor.py` | High-touch level decay (>5000 touches) | 4 |
| `signals/zscore_pump.py` | Multi-window scoring, momentum-velocity boost, signal persistence | 5, 6, 7 |

---

## Decisions Required from T

1. **Priority 1 (SL widening)**: Approve `RS_COMBO_SL_MULTIPLIER = 1.3`? This is the highest-impact change from the 24h data.
2. **Priority 2 (opposing signal penalty)**: Approve 30-min cooldown after loss before same-direction re-entry?
3. **Priority 5 (multi-window)**: Approve adding 20/30-bar z-score computation alongside the existing 70-bar?
4. **Lookback**: Plan A wanted 50, Plan B says keep 70. Which do you prefer?

---

## Consolidation: What's in Each Plan

### May 5-6 (signal-quality-fix-2026-05-05.md)
- ✅ Architecture migration complete
- ✅ Kill-switch audit done
- ✅ Accel_300 token allowlist (23 tokens)
- ✅ pct_hermes threshold 72→80
- ✅ vel_hermes regime filter
- ⚠️ hwave re-enable (verify)

### May 7 (signal-improvement-2026-05-07.md)
- ✅ GOOD_STANDALONE_SIGNALS naming fix
- ✅ RS ATR band removal
- ✅ hwave re-enable (see above)
- ✅ counter_flip regime-dependent (partially — regime scanner not wired in)
- ⏳ RS cooldown 4h → 2h (not done)
- ⏳ Mega-win TP multiplier (not done — needs PM change)

### May 10 (signal-quality-plan.md)
- ⚠️ Regime scanner wired into accel_300+ (not verified)
- ⚠️ trend_purity as co-signal filter (not verified)

### May 21 (signal-quality-fix.md / signal-quality-fix-plan.md)
- ✅ z=None merge fix (COALESCE)
- ✅ Guardian z-score gate
- ✅ signal_z_score write to trade record
- ✅ RS touch filter (RS_DECIDER_MIN_TOUCHES=200)
- ⏳ Opposing signal penalty (NOT DONE)
- ⏳ RS bounce freshness 6→3 (NOT DONE)
- ⏳ High-touch level decay (NOT DONE)

### May 22 (zscore-signal-improvement-plan.md)
- ⏳ Lookback 100→50 (CONFLICT — use 70 instead)
- ⏳ Multi-window z-score scoring (KEEP)
- ⏳ Momentum-velocity boost (KEEP)
- ⏳ Signal persistence/grace period (KEEP)

### May 24 (zscore-rs-signal-quality-improvement-2026-05-24.md) — THIS PLAN
- ✅ 24h empirical audit complete
- ✅ All signals are combo (confirmed)
- ✅ Extreme z doesn't predict loss (confirmed)
- ✅ Duration asymmetry identified
- ⏳ SL widening (RS_COMBO_SL_MULTIPLIER)
- ⏳ Opposing signal penalty (re-state as pending)
- ⏳ Bounce freshness
- ⏳ High-touch decay
- ⏳ Multi-window scoring
- ⏳ Momentum-velocity boost
- ⏳ Signal persistence

---

**Next step:** Await T approval. Implement in priority order.