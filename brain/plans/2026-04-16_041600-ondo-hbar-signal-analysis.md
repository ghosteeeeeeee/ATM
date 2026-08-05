# ONDO/HBAR Signal Analysis & Improvement Plan
**Date:** 2026-04-16
**Status:** OPEN — will revisit when ONDO SHORT and HBAR LONG close
**Type:** Signal Quality Improvement

---

## What Happened

Two trades opened with near-identical signal patterns on 15m chart:

**ONDO SHORT** (opened ~04:02)
- Signal: `hzscore,pct-hermes-` — confidence 89-90%
- Entry: $0.26062 → current $0.2613 (slight loss)
- z-score: +0.546 (barely above mean — weak for SHORT)
- pct_long: 79 (79% of prices below → elevated → SHORT)
- RSI: 50.61 (neutral)
- Problem: z-score and percentile are weakly aligned. pct-hermes says elevated, but z=+0.55 is barely stretched.

**HBAR LONG** (opened ~03:18)
- Signal: `hzscore,pattern_scanner,pct-hermes+` — confidence 96%
- Entry: $0.087546 → current $0.08773 (+0.2%)
- z-score: -1.49 (genuinely below mean — strong for LONG)
- Pattern: micro bullish flag confirmed by pattern_scanner
- RSI: 43.09 (healthy, not overbought)
- Status: Cleaner signal, z-score deeply negative, pattern confirmed

**Why charts looked identical:** Both had `hzscore` and `pct-hermes±` — the pattern scanner added conviction to HBAR but ONDO lacked that extra confirmation.

---

## Root Cause: hzscore+pct-hermes Fires on Weak Alignments

### How hzscore signal is built:
1. `hzscore` source fires when MTF z-score (4H/1H/15m averaged) is extreme (z > 1.5 for SHORT, z < -1.5 for LONG)
2. `pct-hermes-` fires when pct_long ≥ 72 (price elevated vs history)
3. When both exist within ~1 hour, decider_run merges them → `hzscore,pct-hermes`

### The conflict:
- `pct-hermes-` says: price is at percentile 79 → elevated → SHORT
- `hzscore` source (from MTF z-score): measures z-score magnitude, not direction consistency
- **These measure different things.** The merged signal doesn't tell us HOW extreme the z-score was.

### Evidence from backtest:
```
hzscore,pct-hermes SHORT:  9.1% WR, avg -0.71%  ← BAD
hzscore,pct-hermes LONG:  16.7% WR, avg -0.13%  ← MEDIOCRE
hzscore,pct-hermes (all): 13.8% WR              ← TERRIBLE

hzscore,pct-hermes,vel-hermes: 58.1% WR        ← PROOF VEL HELPS
```

The `vel-hermes` filter (z-score momentum) dramatically improved WR because it confirms mean-reversion is actually happening, not just that z is elevated.

---

## Fix Options (Decision Pending — Revisit When Positions Close)

### Option 1: Gate hzscore on minimum z-score magnitude
Require |z| > some threshold (e.g., 1.0 or 1.5) before hzscore contributes to a merged signal.
```python
# Only emit hzscore if z is genuinely extreme
if abs(avg_z) < 1.0:
    skip  # not extreme enough for mean-reversion confidence
```
**Pros:** Simple filter, directly addresses weak hzscore signals
**Cons:** May miss valid signals where MTF averaging smooths z

### Option 2: Require vel-hermes for ALL hzscore signals
The backtest proved `hzscore,pct-hermes,vel-hermes` at 58.1% WR vs 13.8% without vel. Make vel-hermes mandatory, not optional.
```python
# hzscore without vel-hermes = too weak, block from hot-set
if sig_src == 'hzscore' and 'vel-hermes' not in sig_src:
    block
```
**Pros:** Backtest-proven improvement, vel-hermes is already working
**Cons:** vel threshold was raised to 0.05 (from 0.03) to avoid conflicts — may reduce signal volume

### Option 3: Directional gate on pct-hermes by z-score
When `pct-hermes-` fires for SHORT, require z > minimum (e.g., z > 0.3) to confirm elevation is real.
```python
if pct_signal_dir == 'SHORT' and avg_z < 0.3:
    skip  # z too low to confirm SHORT elevation
if pct_signal_dir == 'LONG' and avg_z > -0.3:
    skip  # z too high to confirm LONG suppression
```
**Pros:** Addresses the ONDO problem directly (z=+0.55 but pct_long=79)
**Cons:** Needs backtest validation, may be too tight

### Option 4: +/- encoding on hzscore (like pct-hermes±)
Encode z-score direction into source name, require matching signs:
- `hzscore+` = positive z → SHORT confirmation
- `hzscore-` = negative z → LONG confirmation
```python
z_source = 'hzscore+' if avg_z > 0 else 'hzscore-'
# Merged signal: 'hzscore+,pct-hermes-' = z agrees with pct direction
#                'hzscore+,pct-hermes+' = z DISAGREES with pct direction → lower confidence or block
```
**Pros:** Full directional clarity in signal source
**Cons:** More complex, needs DB schema change for source field

### Option 5: Separate z-score strength tiers
Add confidence tiers based on z magnitude:
- |z| < 1.0: LOW confidence hzscore
- |z| 1.0-2.0: MEDIUM
- |z| > 2.0: HIGH
Apply multiplier to signal confidence based on tier.

---

## Decision Framework

| Priority | Option | Why |
|----------|--------|-----|
| 1 | Option 2 (require vel-hermes) | Backtest-proven: 13.8% → 58.1% WR |
| 2 | Option 3 (z-score gate on pct-hermes) | Addresses ONDO root cause directly |
| 3 | Option 1 (min z threshold) | Simple but may not be specific enough |
| 4 | Option 4 (± encoding) | Cleanest signal semantics but most change |
| 5 | Option 5 (z-strength tiers) | Good additive info but complex |

---

## AAVE Duplication (Separate Issue)
AAVE closed as duplicate — two separate entries ($106.385 and $105.78). This is the ongoing guardian race condition. NOT resolved in this session.

---

## Files Involved
- `/root/.hermes/scripts/signal_gen.py` — signal generation (hzscore, pct-hermes, vel-hermes)
- `/root/.hermes/scripts/decider_run.py` — hot-set filtering (SOURCE_WEIGHTS, hzscore combo-only rule)
- `/root/.hermes/scripts/rsi_backtest.py` — backtest script for signal validation
