# mtp-zscore Design — Multi-Timeperiod Z-Score Trend-Following Signal

## Core Philosophy

**Trend-following, NOT mean-reversion.** Ride the momentum as far as it goes. Exit is handled entirely by profit-monster / ATR SL — NOT z-score crossing 0. No divergence gate.

This is the opposite of zscore_pump's philosophy. zscore_pump rejects signals when z was extremely elevated then crashing (negative divergence = reversal trap). mtp-zscore has no such filter — when all three periods agree, that's a structural trend that should be ridden.

## Signal Identity

- `signal_type`: `mtp_zscore_long`, `mtp_zscore_debug_short`
- `source`: `mtp-zscore+` (LONG), `mtp-zscore-` (SHORT)
- Data: 1m closes from `signals_hermes.db` price_history (~200 bars per token)

## Three-Period Logic

| Period | Lookback | Role |
|--------|----------|------|
| X | 50 bars | Fast move |
| Y | 100 bars | Medium-term trend |
| Z | 150 bars | Structural trend |

Per-period: compute z-score over `closes[-lookback:]`.
- z > 0 → bullish for that period
- z < 0 → bearish for that period

## Firing Rule

At least **2/3 periods must agree on the same direction** to fire.

- 3/3 agree → highest conviction, confidence = base + 2×bonus
- 2/3 agree → standard conviction, confidence = base + 1×bonus
- Disagreement (e.g. 1 LONG + 2 SHORT) → **no signal** (not blocked, just withheld)

## Constants (hermes_constants.py)

```python
MTP_ZSCORE_ENABLED        = True
MTP_ZSCORE_PLUS_ENABLED  = True
MTP_ZSCORE_MINUS_ENABLED = True
MTP_ZSCORE_LB_SHORT       = 50
MTP_ZSCORE_LB_MID         = 100
MTP_ZSCORE_LB_LONG        = 150
MTP_ZSCORE_THRESHOLD      = 2.5   # per-period z threshold (sign checked separately)
MTP_ZSCORE_MIN_AGREE      = 2     # 2/3 periods must agree
MTP_ZSCORE_BASE_CONF      = 80
MTP_ZSCORE_CONF_BONUS     = 5     # +5 per additional agreeing period
MTP_ZSCORE_COOLDOWN_BARS  = 20    # longer than zscore_pump's 5 — stricter signal
```

## Key Difference from zscore_pump

| Aspect | zscore_pump | mtp-zscore |
|--------|-------------|------------|
| Lookbacks | Single (150) | Three (50/100/150) |
| Philosophy | Momentum confirmation | Multi-TF trend confirmation |
| Exit | profit-monster / SL | profit-monster / SL |
| Divergence gate | Yes (rejects reversal traps) | **NO** — anti-momentum |
| Threshold | |z| > threshold | z sign agreement across periods |
| Cooldown | 5 bars | 20 bars |

## Files to Change

1. `scripts/hermes_constants.py` — add MTP_ZSCORE_* block
2. `scripts/signals/mtp_zscore.py` — new file (~300 lines)
3. `scripts/signals/__init__.py` — import + register + name_to_module dict
4. `scripts/signal_compactor.py` — SOURCE_WEIGHTS for mtp-zscore+/mtp-zscore-

## z_score Field

Store the **average z-score of agreeing periods** as `z_score`. Not max, not min — average. This gives a composite momentum reading that reflects the strength of the agreement.

## z_score_tier (optional Enhancement)

Flag if all 3/3 agreed (`z_score_tier = 'perfect'`). Useful for post-trade analysis.
