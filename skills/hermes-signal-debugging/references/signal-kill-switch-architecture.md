# Signal Kill-Switch Architecture (2026-05-05)

## The Problem

`SIGNAL_SOURCE_BLACKLIST` in `hermes_constants.py` blocks signals at the `add_signal()` level in `signal_schema.py`. But T wants a more explicit, user-facing kill switch — a simple `PCT_HERMES_ENABLED = True/False` flag in `hermes_constants.py` that can be flipped without editing blacklist entries or understanding the blacklist structure.

## Signal Kill-Switch Design

### Placement — Three Layers

Signals can be killed at three independent layers. All three should be consistent:

**Layer 1 — Generation (primary)**:
```python
# In each signal's generation block in signal_gen.py (or standalone script):
if PCT_HERMES_ENABLED:
    sid = add_signal(token, pct_signal_dir, 'percentile_rank', f'pct-hermes{pct_dir_char}', ...)
```

**Layer 2 — Schema gate (secondary)**:
```python
# In signal_schema.py add_signal(), after confidence floor:
try:
    from hermes_constants import PCT_HERMES_ENABLED, VEL_HERMES_ENABLED, ...
    if not PCT_HERMES_ENABLED and source and 'pct-hermes' in source:
        return None  # silently skip
    if not VEL_HERMES_ENABLED and source and 'vel-hermes' in source:
        return None
    # ... same for each flag
except ImportError:
    pass
```

**Layer 3 — Execution gate (defense-in-depth)**:
```python
# In decider_run.py before executing approved signals:
try:
    from hermes_constants import PCT_HERMES_ENABLED, ACCEL_300_ENABLED, ...
    for sig in approved:
        src = sig.get('source', '')
        if 'pct-hermes' in src and not PCT_HERMES_ENABLED:
            log(f"SKIP {sig['token']}: PCT_HERMES_ENABLED=False")
            continue
        # ... same pattern
except ImportError:
    pass
```

### Constants to Add in hermes_constants.py

```python
# ── Signal Kill Switches ──────────────────────────────────────────────────────
# True = signal type can fire, False = code path never executes.
# Flipping False → True re-enables without other changes.
PCT_HERMES_ENABLED      = True   # pct-hermes+/-
VEL_HERMES_ENABLED      = True   # vel-hermes+/-
HZSCORE_ENABLED         = True   # hzscore+/-
HMACD_ENABLED           = True   # hmacd+/-
MTF_MOMENTUM_ENABLED    = True   # mtf-momentum+ (momentum combo)
PHASE_ACCEL_ENABLED     = True   # phase-accel+/-
FAST_MOMENTUM_ENABLED   = True   # fast-momentum+/-
ACCEL_300_ENABLED       = True   # accel-300+ (primary signal)
RS_ENABLED              = True   # rs-r*, rs-s*
GAP_300_ENABLED        = False  # gap-300+ (blocked — 14.3% WR)
MA_CROSS_ENABLED       = True   # ma_cross
MA_CROSS_5M_ENABLED    = True   # ma_cross_5m
HH_HL_ENABLED          = True   # hh_hl (already exists)
GUPPY_ENABLED          = True   # guppy
MACD_ACCEL_ENABLED     = True   # macd_accel
TREND_PURITY_ENABLED   = True   # trend_purity
EMA9_SMA20_ENABLED     = True   # ema9_sma20
R2_REV_ENABLED         = False  # r2_rev (blocked)
R2_TREND_ENABLED       = True   # r2_trend
VOLUME_HL_ENABLED      = True   # volume_hl
MA300_CANDLE_ENABLED   = True   # ma300_candle_confirm
ATR_COMPRESSION_ENABLED = True   # atr_compression
EXHAUSTION_ENABLED      = True   # exhaustion
COUNTER_FLIP_ENABLED   = True   # counter_flip
```

## Signal Generation Map (18 scripts)

All signals ultimately call `signal_schema.add_signal()` → filtered by `SIGNAL_SOURCE_BLACKLIST` → reach hot-set → `decider_run` executes.

| Script | Signals | Key Source |
|--------|---------|-----------|
| `signal_gen.py` | pct-hermes+/-, vel-hermes+/-, hzscore+/-, hmacd+/-, mtf-momentum+, phase-accel+/-, fast-momentum+/- | `signal_gen.py:1702` (pct), `signal_gen.py:1726` (vel), `signal_gen.py:1767` (hzscore) |
| `accel_300_signals.py` | accel-300+ | `accel_300_signals.py:372` |
| `rs_signals.py` | rs-r*, rs-s* | `rs_signals.py:509` |
| `gap300_signals.py` | gap-300+ | `gap300_signals.py:472` |
| `ma_cross_signals.py` | ma_cross | `ma_cross_signals.py:255` |
| `ma_cross_5m.py` | ma_cross_5m | `ma_cross_5m.py:613` |
| `hh_hl_signals.py` | hh_hl | `hh_hl_signals.py:533,563` |
| `guppy_signals.py` | guppy | `guppy_signals.py` |
| `macd_accel_signals.py` | macd_accel | `macd_accel_signals.py:245` |
| `trend_purity_signals.py` | trend_purity | `trend_purity_signals.py:197` |
| `ema9_sma20_signals.py` | ema9_sma20 | `ema9_sma20_signals.py:434` |
| `r2_rev_5m_signals.py` | r2_rev | `r2_rev_5m_signals.py:246` (blocked) |
| `volume_hl_signals.py` | volume_hl | `volume_hl_signals.py:155` |
| `ma300_candle_confirm_signals.py` | ma300_candle_confirm | `ma300_candle_confirm_signals.py:252` |
| `r2_trend_signals.py` | r2_trend | `r2_trend_signals.py:236` |
| `atr_compression_signals.py` | atr_compression | `atr_compression_signals.py:333` |
| `exhaustion_signals.py` | exhaustion | `exhaustion_signals.py:236` |
| `counter_flip_signal.py` | counter_flip | `counter_flip_signal.py:255` |

## The pct-hermes Blacklist Paradox

**Observed**: `pct-hermes-,rs-r827` appears in recent trades (SUSHI, ICP, MORPHO, etc.) with close_reason=`atr_sl_hit`, despite `pct-hermes-` being in `SIGNAL_SOURCE_BLACKLIST`.

**Investigation result**: The blacklist filtering at `signal_schema.add_signal()` line 411 (`component in SIGNAL_SOURCE_BLACKLIST`) IS working correctly — `validate_source('pct-hermes-,rs-r827')` returns `'unknown'` (blocked).

**But**: These trades still reached `trades.json`. Possible paths:
1. **Stale DB records**: Signals written before `pct-hermes-` was blacklisted (May 5, ~00:00 UTC) are still in the signals DB and got executed before being purged
2. **Direct brain.py bypass**: Some path calls `brain.py add_trade()` directly with signal strings not checked against blacklist
3. **Guardian orphan path**: `add_orphan_trade()` in `hl-sync-guardian.py` creates DB trades without going through `add_signal()`

**Immediate action**: If T wants to absolutely guarantee no pct-hermes signals execute:
1. Set `PCT_HERMES_ENABLED = False` in `hermes_constants.py` (generation layer)
2. Add the schema layer check (above)
3. Add the decider_run execution layer check (above)

## Adding a New Kill Switch

For any existing signal, the process is:
1. Add `SIGNAL_ENABLED = True` in `hermes_constants.py` under the Signal Kill Switches section
2. Wrap the `add_signal()` call in the generating script with `if SIGNAL_ENABLED:`
3. Add the schema-layer check in `signal_schema.py add_signal()`
4. Add the execution-layer check in `decider_run.py`

Order of implementation: Generation → Schema → Execution. All three are independent layers but consistency matters.
