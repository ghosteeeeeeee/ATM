# EMA-Angle Signal — LONG vs SHORT Debugging Reference

## Signal Design Pattern

**Reference signal: PURR (2026-05-14)**
PURR's "flat-to-steep EMA angle" LONG fires when:
1. EMA300 angle transitions from flat (near p50) to steep (above p75)
2. Price above EMA300 by ≥0.5% (price/EMA ratio ≥ 1.005)
3. `was_below_p75 = True` — angle crossed from below p75
4. `was_below_p50 = True` — angle was near-zero/flat before crossing (was not already elevated)

**Core insight**: "Flat to steep" means angle was genuinely flat (near p50) before crossing. Oscillating just below p75 is NOT a flat base.

---

## Known Failure Modes

### Failure Mode 1: Marginal Crossover (was_below too loose)

**Symptom**: Signal fires when angle crosses p75 by a tiny amount (1-5% above p75), oscillating around p75 without genuine steepening.

**Root cause**: `was_below_p75 = angles[i-1] < p75` only checks if angle was below p75. If angle oscillates just below p75 (within noise), it still passes.

**Fix**: Require angle was below p50 before crossing (genuine flat base):
```python
was_below_p50 = angle_history[i-1] < p50  # angle was near-zero/flat
```

### Failure Mode 2: Price barely above EMA

**Symptom**: Signal fires when price is only 0.01-0.1% above EMA (essentially flat), creating bad entries that immediately reverse.

**Root cause**: `price_above_ema = closes[-1] > ema300[-1]` requires only ratio > 1.000.

**Fix**: Require minimum ratio threshold:
```python
MIN_PRICE_EMA_RATIO = 1.005  # price at least 0.5% above EMA
above_ema_by_ratio = closes[-1] >= ema300[-1] * MIN_PRICE_EMA_RATIO
```

**PURR benchmark**: PURR's 5 signals had ratios: 1.009, 1.005, 1.005, 1.007, 1.005 (all ≥0.5%).

### Failure Mode 3: Stale price/angle mismatch

**Symptom**: `price_above_ema` uses `closes[-1]` (current bar) while `angle` uses `angles[-1]` (bar -21). If price crosses EMA between those two bars, signal decision is inconsistent.

**Fix**: Align price check to the bar corresponding to the angle:
```python
# angle[-1] corresponds to closes[-21]
# price_above_ema must use closes[latest_idx] where latest_idx = len(closes) - 21
```

---

## Case Study: ZK LONG (2026-05-15 21:49, bad signal)

- **Entry**: 0.016665, **Exit**: 0.016538, **PnL**: -0.76%
- **Signal fire time**: ~17:15 (crossover), **Trade open**: 21:49 (pipeline delay)
- **Angle at crossover**: 0.002339°, **p75**: 0.001108° — only 1% above p75
- **Price/EMA at signal fire**: ratio=1.006378 (0.64% above EMA) — marginal, below PURR's 0.5% minimum
- **Price/EMA at trade open**: ratio=1.000158 (0.016% above EMA) — essentially flat
- **Root cause**: (1) `was_below_p75` passed because angle oscillated just below p75 for 20 bars — never genuinely flat; (2) price/EMA ratio too loose

**Two required fixes**:
1. `was_below_p50 = True` — angle was never near p50 before crossing
2. `price_above_ema` requires `ratio >= 1.005`

---

## SHORTS vs LONGS Asymmetry

**SHORTS work correctly** because:
- For SHORT, `price_above_ema=False` is a hard requirement (price must be below EMA)
- ZK SHORT logic at line 220: `not price_above_ema and was_above and angle < p25` — correctly requires price BELOW EMA

**Key asymmetry**: For SHORT, price_above_ema=False is hard. For LONG, price_above_ema=True is currently only `> 1.000` — extremely loose. This explains why bad LONGs fire while SHORTS are mostly correct.

---

## ema_angle.py Critical Lines (as of 2026-05-15)

- **Line ~185**: `price_above_ema = closes[-1] > ema300[-1]` — LOOSE, needs ratio threshold
- **Line ~193**: `if was_below and above_ema and ...` — only `was_below_p75`, needs `was_below_p50` too
- **Line ~220**: SHORT `not price_above_ema and was_above and angle < p25` — correctly requires price below EMA

---

## Validation Queries

```python
# Check PURR price/EMA ratios at signal times
purr_crossovers = [(ts, close, ema, close/ema) for each signal bar]
# Expected: all >= 1.005

# Check ZK angle history around bad signal
zk_angles_17_19 = angle_history[bar-21 to bar]
# Expected: angle oscillating just below p75, never near p50
```