# Plan: Replace `_macd_crossover` with `compute_mtf_macd_alignment` (TRUE-MACD)

## Goal
Replace the old `_macd_crossover()` EMA-aggregation MACD in `signal_gen.py` with the full-featured `compute_mtf_macd_alignment()` from `macd_rules.py`, so the TRUE-MACD drives signal generation instead of just boosting confidence.

## Current Context

**Three MACDs in the system:**

| Name | Location | Used for signals? | Role |
|---|---|---|---|
| `_macd_crossover()` | `signal_gen.py` (local, line 1353) | **YES — base signal** | EMA(12/26/9) aggregated from raw 90s candles, simple histogram sign + crossover detection |
| `compute_mtf_macd_alignment()` | `macd_rules.py` (line 684) | **YES — boost only** | Full state machine: regime detection, crossover freshness, histogram rate, 4H/1H/15m agreement |
| `compute_mtf_macd()` | `candle_predictor.py` | **NO — dashboard only** | Builds LLM prompt context; never calls `add_signal` |

**Current flow in `signal_gen.py` (lines 1524–1622):**
1. Call `_macd_crossover(token, 240/60/15)` for each TF → get `(histogram, macd_line, signal_line, crossover_dir)`
2. Score agreement across TFs → determine `direction` and base `confidence`
3. Call `compute_mtf_macd_alignment()` as a **post-processing boost** → +5–10% if aligned
4. Call `cascade_entry_signal()` → additional boost or block
5. Call `add_signal(..., 'mtf_macd', 'hmacd-', conf)` ← **this is the traded signal**

**Problem:** `_macd_crossover` is a simple EMA aggregator. `compute_mtf_macd_alignment` is a much richer state machine. The base signal is weak while the boost is strong. Replacing the base makes the whole signal better.

## Proposed Approach

**Replace the signal-generation logic** (steps 1–2 above) to use `compute_mtf_macd_alignment()` as the primary signal source, not just the boost.

### Key differences to handle

| `_macd_crossover` | `compute_mtf_macd_alignment` |
|---|---|
| Returns `(histogram, macd_line, signal_line, crossover_dir)` per TF | Returns `{'mtf_score': 0-3, 'mtf_direction': 'LONG'/'SHORT'/'NEUTRAL', 'mtf_confidence': 0.0-1.0, 'all_tfs_bullish', 'all_tfs_bearish', 'tf_states'}` |
| Crossover detection: MACD line crosses signal | Full regime + histogram sign + crossover freshness |
| 3 separate calls (4H, 1H, 15m) | 1 call, fetches all 3 TFs internally |
| Aggregates raw 90s candles into TF candles | Fetches HTF candles directly from Binance |
| direction = sign of weighted bullish_tfs | direction = explicit from mtf_direction |
| strength = weighted bullish count | confidence = 0.0/0.25/0.75/1.0 |

## Step-by-Step Plan

### Step 1: Replace `_macd_crossover` call block with `compute_mtf_macd_alignment`

**File:** `signal_gen.py`, approx lines 1524–1550

**Before (pseudo-code):**
```python
xo_4h  = _macd_crossover(token, 240)
xo_1h  = _macd_crossover(token, 60)
xo_15m = _macd_crossover(token, 15)

valid = {}
for tf, xo in [('4h', xo_4h), ...]:
    if xo is not None:
        valid[tf] = xo

if len(valid) >= 2:
    # score crossover agreement → direction, strength
    ...
elif len(valid) == 1:
    # single TF → direction from crossover_dir or histogram sign
    ...
else:
    continue  # no MACD data

conf = min(95, base_conf * 1.35)
```

**After:**
```python
from macd_rules import compute_mtf_macd_alignment

mtf = compute_mtf_macd_alignment(token)
if mtf is None:
    continue  # no MACD data at all

mtf_direction  = mtf['mtf_direction']
mtf_score      = mtf['mtf_score']       # 0-3
mtf_confidence = mtf['mtf_confidence'] # 0.0 / 0.25 / 0.75 / 1.0

if mtf_direction == 'NEUTRAL':
    continue  # no actionable signal

direction = mtf_direction

# Confidence: seed from mtf_confidence, then scale to execution range
# mtf_confidence 1.0 → seed 85, 0.75 → 70, 0.25 → 40
base_conf = 40 + mtf_score * 15        # 0→40, 1→55, 2→70, 3→85
conf = min(95, base_conf * 1.35)       # 3tf → 99, 2tf → 94, 1tf → 54
```

### Step 2: Remove the redundant `compute_mtf_macd_alignment` boost call

The boost call at lines ~1572–1586 becomes **unnecessary** since alignment IS the signal now. Remove it to avoid double-counting.

**Remove this block:**
```python
# ── MTF MACD Alignment Boost (2026-04-06) ───────────────────────────────
from macd_rules import compute_mtf_macd_alignment
mtf_align = compute_mtf_macd_alignment(token)
if mtf_align is not None:
    align_score = mtf_align['mtf_score']
    align_dir   = mtf_align['mtf_direction']
    ...
    if align_score >= 3:
        conf += 10
    elif align_score >= 2 and align_dir == direction:
        conf += 5
```

### Step 3: Keep `cascade_entry_signal` as-is

Cascade is a separate state machine signal. It still boosts (+10) or blocks (continue) correctly — no change needed.

### Step 4: Update the `add_signal` call — fields may change

Current:
```python
add_signal(token, direction, 'mtf_macd', 'hmacd-',
           confidence=conf, value=strength, price=price,
           macd_value=macd_val, macd_hist=macd_hist,
           ...)
```

New — `macd_val` and `macd_hist` now come from the aggregate state. Extract from `mtf['tf_states']`:
```python
# Use primary TF (1H) for indicator values in the signal record
tf_states = mtf['tf_states']
primary = tf_states.get('1h') or tf_states.get('4h') or tf_states.get('15m')
if primary:
    macd_val  = round(primary.macd_line - primary.signal_line, 6)  # histogram
    macd_line = round(primary.macd_line, 6)
    macd_sig  = round(primary.signal_line, 6)
else:
    macd_val = macd_line = macd_sig = None

add_signal(token, direction, 'mtf_macd', 'hmacd-',
           confidence=conf, value=mtf_score, price=price,
           macd_value=macd_line, macd_hist=macd_val,
           ...)
```

### Step 5: Remove `_macd_crossover` function

Delete lines 1353–1450 (the entire `_macd_crossover` function). No other callers.

### Step 6: Update docstring comment above the MACD block

The comment currently says "Use histogram (MACD line - signal line) for direction" — update to reflect the new state-machine approach.

## Files Likely to Change

| File | Change |
|---|---|
| `signal_gen.py` | Replace MACD call block, remove boost, remove `_macd_crossover` |
| `macd_rules.py` | No changes |
| `brain/trading.md` | Document the change under `## SELF-INIT RUN` |

## Verification Steps

1. **Dry-run signal gen:** `cd /root/.hermes/scripts && python3 signal_gen.py 2>&1 | grep -E "MTF ALIGN|macd_rules|added"` — should still see `[MTF ALIGN]` log lines (cascade still fires), no `_macd_crossover` output
2. **DB check:** After one pipeline run, `sqlite3 data/signals_hermes_runtime.db "SELECT token, direction, confidence, source, signal_types FROM signals WHERE decision='PENDING' ORDER BY created_at DESC LIMIT 10"` — signals should still be written
3. **Confirm old function gone:** `grep "_macd_crossover" signal_gen.py` should return nothing
4. **Check pipeline.log:** `[MTF ALIGN]` lines should still appear (from cascade, which also uses `compute_mtf_macd_alignment`)

## Risks & Tradeoffs

- **Risk:** `_macd_crossover` aggregates raw 90s candles from the local DB. `compute_mtf_macd_alignment` fetches from Binance directly. Latency/data source difference may produce slightly different signals at transition.
  - **Mitigation:** Both use the same `compute_macd_state` state machine for direction. The Binance fetch is fast (40 candles per TF).
- **Risk:** Removing the +5/+10 boost may lower some signal confidences.
  - **Fix:** The base confidence formula (`40 + mtf_score * 15`) gives 3tf=85, which with the 1.35x multiplier reaches 99 — same as before. The boost was redundant.
- **Open question:** Should we also remove the separate `hmacd-` source prefix now that there's only one MACD path? No — keep the prefix for W&B audit trail consistency.

## What This Does NOT Change

- `candle_predictor.py`'s `compute_mtf_macd()` — stays, dashboard only
- `macd_rules.py`'s `compute_macd_state`, `get_macd_entry_signal`, `cascade_entry_signal` — all unchanged
- Open trades — untouched
- `decider-run.py` execution logic — unchanged
