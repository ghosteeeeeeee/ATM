# Signal Quality Improvement Plan — 2026-05-10

## Context from May 9 closed trade analysis (43 trades)

### Core findings:
- **accel-300+ is the only profitable signal**: all 8 big winners (>1%) are accel-300+. RS alone produces nothing. pct-hermes- SHORTs: 0% WR, -0.29% avg.
- **Entry timing is the main problem**: 78% of losses hit SL on the first counter-candle within 0.1-3 minutes. Move already exhausted when signal fires.
- **Confidence scoring is backwards**: conf 70-79 = 100% WR, +3.13% avg. conf 90-99 = 28.6% WR, +0.26% avg.
- **All SHORTs lose**: 4 shorts, 0 wins. System is fundamentally long-biased.
- **RS high-touch levels are dead money**: 100+ touches = 40% WR but +0.03% avg. Level respected but no reactive bounce.
- **TP never hit**: 0 trades closed at ATR TP. profit-monster closes trades manually at +0.5-2%.

---

## Changes to Implement

### 1. Turn OFF tl_break signal
- **File**: `/root/.hermes/scripts/hermes_constants.py`
- **Change**: `TL_BREAK_ENABLED = True` → `TL_BREAK_ENABLED = False`
- **Reason**: tl_break needs fine-tuning. All SHORT signals (including tl_break_short) are losing. The current tl_break params are uncalibrated and producing bad SHORT entries (e.g., GRIFFAIN SHORT: -0.30%, XRP SHORT still open).
- **Risk**: None — this just removes one uncalibrated signal source.

### 2. Wire regime scanner into accel-300+ as a filter gate

**Problem**: accel-300+ fires in ALL regimes — trending, neutral, and chop. The 15m_regime_scanner.py already computes per-token regime (LONG_BIAS / SHORT_BIAS / NEUTRAL) every cycle and writes to `/var/www/hermes/data/regime_5m.json` and PostgreSQL `momentum_cache`. But signal_compactor.py never reads it.

**Change**: Add a regime read step in `signal_compactor.py` that filters accel-300+ signals:
- accel-300+ LONG: only pass if token's regime is `LONG_BIAS` (not NEUTRAL, not SHORT_BIAS)
- accel-300+ SHORT: only pass if token's regime is `SHORT_BIAS` (not NEUTRAL, not LONG_BIAS)

**Implementation location**: `signal_compactor.py` — check regime_5m.json before allowing accel-300+ entry to pass the confluence gate.

**Fallback**: If regime_5m.json is missing/stale, apply NO filter (don't block on missing data).

**Expected impact**: Filter out accel-300+ breakouts that happen in chop/neutral markets — the main source of the "first counter-candle hits SL" losses.

### 3. Use trend_purity as a built-in co-signal filter (not competing signal)

**Problem**: trend_purity fires as a standalone signal competing for hot-set space. It has conf=60-80 and is a co-signal that confirms "clean trend." But it's not being used as a prerequisite gate.

**Insight**: trend_purity's `purity` metric = fraction of last 15 bars above EMA30. This is a better trend quality filter than the linear-slope regime scanner because it measures actual trend cleanliness, not just direction.

**Change**: In signal_compactor.py, before passing accel-300+ to the hot-set:
- Check if trend_purity+ is present for LONG (purity >= 0.45 = confirmed clean uptrend)
- Check if trend_purity- is present for SHORT (confirmed clean downtrend)
- If trend_purity is NOT present, DEMOTE accel-300+ confidence significantly (e.g., -20 confidence) instead of blocking entirely — we don't want to block on missing co-signal, just reduce confidence

**Alternative (simpler)**: Raise the MIN_GAP_PCT for accel-300+ when trend_purity+ is absent, requiring a stronger gap to compensate for uncertain trend quality.

**Expected impact**: trend_purity+ fires at conf=60-80 when price is cleanly above EMA30. accel-300+ breaking out of a clean trend is a much better setup than accel-300+ breaking out of chop.

---

## What NOT to change (yet)

1. **RS touch count filter**: Already addressed in prior session with RS_PROXIMITY_K=0.70, RS_MIN_TOUCHES=3, RS_RECENCY_WINDOW=200, RS_RECENCY_BOOST_K=3.0. Need live trading data to verify behavior before further changes.

2. **Confidence scoring over-boost**: pct-hermes+ and trend_purity+ boost mediocre entries to conf=99. Don't touch this yet — first implement regime filter and see if bad entries are naturally filtered out.

3. **ATR SL/TP params**: 0 trades hit ATR TP. Don't tighten TP further without seeing regime-filtered results.

4. **Leverage**: 5x has better avg PnL than 3x (+0.62% vs +0.04%), even with lower WR. Don't change.

---

## Files to Modify

| File | Change |
|------|--------|
| `hermes_constants.py:395` | `TL_BREAK_ENABLED = False` |
| `signal_compactor.py` | Read regime_5m.json, filter accel-300+ by regime direction |
| `signal_compactor.py` | Check trend_purity presence, demote conf if absent |

---

## Testing Plan

1. **AST check** on all modified files
2. **Dry run**: Run signal_compactor.py in dry-run mode, verify regime filter doesn't block all signals
3. **Verify** LAYER trade (opened at 04:58, already +17.5%): check if LAYER's regime was LONG_BIAS at open time (retroactively check regime_5m.json timestamp)
4. **Monitor**: Track over next 24h — do regime-filtered accel-300+ entries have better WR than unfiltered?