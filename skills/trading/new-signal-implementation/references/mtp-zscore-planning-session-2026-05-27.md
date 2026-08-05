# mtp-zscore — Planning Session 2026-05-27

## Source
Plan mode session (T invoked `/plan`). Design session before implementation.

## Design — LOCKED

### Philosophy
- **Trend-following, NOT mean-reversion**. Ride momentum until profit-monster / ATR SL closes it.
- No divergence gate. zscore_pump's divergence gate rejects extended moves — that's anti-momentum (mean-reversion logic). mtp-zscore is the opposite: when 3 periods agree, it's a structural trend to ride.
- Exit = profit-monster / ATR SL ONLY. No z-score crossing 0.

### Named periods (short / medium / long)
| Period | Lookback | LB constant | Z_MIN const | Z_MAX const |
|--------|----------|------------|-------------|-------------|
| short | 50 | MTP_ZSCORE_LB_SHORT | Z_SHORT_Z_MIN | Z_SHORT_Z_MAX |
| medium | 100 | MTP_ZSCORE_LB_MID | Z_MID_Z_MIN | Z_MID_Z_MAX |
| long | 150 | MTP_ZSCORE_LB_LONG | Z_LONG_Z_MIN | Z_LONG_Z_MAX |

All 6 bounds constants in hermes_constants.py — T tunes each period independently.

### Core Logic (per token)
1. Fetch max(lookbacks)+50 1m closes from signals_hermes.db (≈200 bars)
2. Per period: compute z-score over that lookback
3. BOUNDS check per period: `z_abs = abs(z)`. Reject if `z_abs < Z_MIN` (not meaningful for THIS period). Reject if `z_abs > Z_MAX` (too extended — reject THIS period only).
4. After all 3 pass/reject decisions → direction vote: z>0=LONG vote, z<0=SHORT vote
5. Fire if 2+ periods vote same direction. No signal if disagreement (1+2).

### Implementation pitfalls (from zscore_pump hard lessons)

**1. abs() only for BOUNDS check, direction from raw z sign**

```python
# WRONG — direction from abs() destroys sign
if abs(z) < threshold:
    return None
direction = 'LONG' if abs(z) > 0 else 'SHORT'  # never do this

# CORRECT
if abs(z) < threshold:
    return None
direction = 'LONG' if z > 0 else 'SHORT'
```

**2. Zero stddev guard — flat price = divide-by-zero**
```python
def compute_zscore(values):
    if len(values) < 2:
        return None
    std = statistics.stdev(values)
    if std == 0:  # flat price series — must guard
        return None
    return (values[-1] - mean) / std
```

**3. Negative z = SHORT (expected, not an error)**
`(last - mean) / stdev` is negative when price < mean. Sign handles direction correctly.

**4. abs() in Z_MIN/Z_MAX — both ±z checked the same way**
`z_short=-3.0` with `Z_SHORT_Z_MAX=2.0` → abs(-3.0)=3.0 > 2.0 → reject. Correct — magnitude checks both directions uniformly.

**5. Cooldown: set_cooldown takes hours. 1 bar = 1 minute on 1m data**
```python
set_cooldown(token, direction, hours=MTP_ZSCORE_COOLDOWN_BARS / 60.0)
# 20 bars → 20/60 hours ≈ 20 min
```

**6. Price staleness check**
```python
most_recent_ts = rows[-1][0]
if (time.time() - most_recent_ts) > 120:
    _log(f"[mtp-zscore] {token}: stale price_history … skipping")
    return []
```

**7. Minimum data length (longest period governs)**
```python
if len(prices) < MTP_ZSCORE_LB_LONG + 2:
    continue
```

**8. Falsy-0.0 bug — NEVER use `or 0` with float fields**
```python
# WRONG: float(0.0) or 0 → int 0 (loses real 0.0)
z = float(row['z_score'] or 0)

# CORRECT: explicit None check preserves real values
z = float(row['z_score']) if row['z_score'] is not None else None
```

**9. Multi-field z-score storage → JSON**
```python
import json
metadata = json.dumps({'z_short': round(z_short,3), 'z_mid': round(z_mid,3), 'z_long': round(z_long,3)})
```

## hermes_constants additions needed

```python
MTP_ZSCORE_ENABLED       = True
MTP_ZSCORE_PLUS_ENABLED  = True
MTP_ZSCORE_MINUS_ENABLED = True
MTP_ZSCORE_LB_SHORT      = 50
MTP_ZSCORE_LB_MID        = 100
MTP_ZSCORE_LB_LONG       = 150
Z_SHORT_Z_MIN            = 0.5
Z_SHORT_Z_MAX            = 2.0
Z_MID_Z_MIN             = 0.5
Z_MID_Z_MAX             = 2.5
Z_LONG_Z_MIN            = 0.5
Z_LONG_Z_MAX            = 3.0
MTP_ZSCORE_MIN_AGREE     = 2        # 2/3 periods must agree
MTP_ZSCORE_BASE_CONF     = 80
MTP_ZSCORE_CONF_BONUS   = 5        # +5 per additional agreeing period
MTP_ZSCORE_COOLDOWN_BARS = 20      # ~20 min cooldown
```

## Files to create/change

| File | Change |
|------|--------|
| `scripts/signals/mtp_zscore.py` | **NEW** — ~350-400 lines |
| `scripts/hermes_constants.py` | Add MTP_ZSCORE_* + Z_SHORT/MID/LONG_* blocks |
| `scripts/signals/__init__.py` | Import + register signal + add to name_to_module |
| `scripts/signal_compactor.py` | Add SOURCE_WEIGHTS entries for mtp-zscore+ / mtp-zscore- |

## Plan file
`.hermes/plans/2026-05-27_120000-mtp-zscore-signal.md`
