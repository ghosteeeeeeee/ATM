# Regime Directionality Fix — 2026-05-11

## What changed

### 1. Compactor regime multiplier (signal_compactor.py:217-230)

Old values:
- `LONG_BIAS+LONG` → 1.15x
- `SHORT_BIAS+SHORT` → 1.15x
- counter-regime → 0.70x
- NEUTRAL → 1.0x (no effect)

New values:
- aligned → **1.50x**
- counter-regime → **0.50x**
- NEUTRAL → **0.50x**
- no data → **0.50x floor**

```python
# Regime multiplier: +50% aligned, -50% counter-regime, -50% neutral
reg_mult = 1.0
if regime_conf > 0:
    if (regime == 'LONG_BIAS' and direction == 'LONG') or \
       (regime == 'SHORT_BIAS' and direction == 'SHORT'):
        reg_mult = 1.50
    elif (regime == 'LONG_BIAS' and direction == 'SHORT') or \
         (regime == 'SHORT_BIAS' and direction == 'LONG'):
        reg_mult = 0.50
    elif regime == 'NEUTRAL':
        reg_mult = 0.50
else:
    reg_mult = 0.50
```

### 2. RS signal regime directionality (signals/rs.py:477-534)

Model B applied — when both support and resistance are near price:

```
if both support AND resistance are near:
  LONG_BIAS  → suppress rs-r, fire only rs-s  (support bounces in uptrend)
  SHORT_BIAS → suppress rs-s, fire only rs-r  (resistance rejects in downtrend)
  NEUTRAL    → keep higher confidence wins (existing behavior)

Counter-regime penalties (on top of compactor 0.5x):
  SHORT_BIAS + LONG  → 80% confidence haircut
  LONG_BIAS + SHORT  → 80% confidence haircut
  NEUTRAL (>55 conf) → 85% confidence haircut
```

`_get_regime_5m()` helper added to rs.py (reads regime_5m.json directly, same logic as signal_compactor.get_regime_5m).

---

## How to add regime directionality to a new signal

Pattern for any signal that fires in both directions:

```python
# At top of detect function (or main scanner):
regime, regime_conf = _get_regime_5m(token)

# Model B: when both directions are present, let regime pick
if has_long_signal and has_short_signal:
    if regime == 'LONG_BIAS':
        short_signal = None
    elif regime == 'SHORT_BIAS':
        long_signal = None

# Counter-regime confidence penalty
if long_signal and regime == 'SHORT_BIAS' and regime_conf > 50:
    confidence *= 0.80
if short_signal and regime == 'LONG_BIAS' and regime_conf > 50:
    confidence *= 0.80
```

---

## Regime data sources

- File: `/var/www/hermes/data/regime_5m.json`
- Updated by: `15m_regime_scanner.py` every 15 min
- Schema: `{regimes: {TOKEN: {regime, confidence, slope_pct, r2}}}`
- Scan threshold (from 15m_regime_scanner.py:162-173):
  - `LONG_BIAS`: slope_pct > +0.35 AND r2 > 0.5
  - `SHORT_BIAS`: slope_pct < -0.35 AND r2 > 0.5
  - else: `NEUTRAL`

## Typical regime distribution

Usually 103-106 of ~107 tokens are NEUTRAL. In trending markets this shifts. Currently only LAYER (LONG_BIAS) and TON/NIL/FOGO (SHORT_BIAS) are non-neutral.

## Common mistakes to avoid

1. **Don't hard-code regime thresholds in signal files** — use `_get_regime_5m()` which reads from the regime file. Thresholds are centralized in `15m_regime_scanner.py`.

2. **Don't suppress counter-regime signals entirely** — penalize through confidence + compactor 0.5x multiplier. Complete suppression loses good reversal setups.

3. **Always check regime_conf > 50 before applying penalty** — below 50 is too uncertain to act on.

4. **Model B only acts when BOTH directions are present** — a token with only a support signal in a SHORT_BIAS market should still fire (but get penalized). Only suppress when both exist and regime would pick one.