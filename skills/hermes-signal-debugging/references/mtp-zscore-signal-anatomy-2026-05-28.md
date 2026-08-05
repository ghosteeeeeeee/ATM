# mtp-zscore+ signal anatomy — BSV LONG 2026-05-28

## Signal that fired
```
BSV|LONG|mtp-zscore+,rs-s72|83.2|z=2.258
z_score_tier: {"z_short":2.388,"z_mid":2.081,"z_long":2.306,"agree_count":3}
```

## Constants verified (hermes_constants.py lines 631–649)
```
MTP_ZSCORE_LB_SHORT = 14   (short/fast period)
MTP_ZSCORE_LB_MID   = 50   (medium period)
MTP_ZSCORE_LB_LONG  = 150  (long/structural period)

Z_SHORT_Z_MIN/MAX = 2.0 / 3.0
Z_MID_Z_MIN/MAX   = 2.0 / 3.0
Z_LONG_Z_MIN/MAX  = 2.0 / 3.0

MTP_ZSCORE_MIN_AGREE  = 3   (3/3 — all periods must vote same direction)
MTP_ZSCORE_BASE_CONF  = 80
MTP_ZSCORE_CONF_BONUS = 5
MTP_ZSCORE_COOLDOWN_BARS = 5
```

## Bound verification (from DB z_score_tier)
| Period | Lookback | z-value | abs(z) | Bound [2.0,3.0] | Status |
|--------|----------|---------|--------|-----------------|--------|
| short  | 14-bar   | +2.388  | 2.388  | 2.388 in [2,3]  | PASS   |
| mid    | 50-bar   | +2.081  | 2.081  | 2.081 in [2,3]  | PASS   |
| long   | 150-bar  | +2.306  | 2.306  | 2.306 in [2,3]  | PASS   |

Direction: all positive → LONG. All 3 within bounds → **3/3 agree → FIRE**.

## Key design points (from mtp_zscore.py lines 149–223)
- **Direction** comes from the *sign* of z (positive → LONG, negative → SHORT)
- **abs(z)** is used ONLY for bounds comparison — never for direction
- Bounds check: BELOW Z_MIN → reject (not meaningful); ABOVE Z_MAX → reject (too extended)
- If ANY period returns None (flat series, stddev=0) → that period cannot vote
- All 3/3 must vote same direction to fire

## Confidence computation
```python
confidence = MTP_ZSCORE_BASE_CONF + MTP_ZSCORE_CONF_BONUS  # 80 + 5 = 85
```
DB shows 83.2 — compactor applied regime haircut + rs-s72 stacking.

## DB query for verification
```bash
cd /root/.hermes && sqlite3 data/signals_hermes_runtime.db \
  "SELECT created_at, source, z_score, z_score_tier FROM signals \
   WHERE token='BSV' AND source LIKE '%mtp-zscore%' ORDER BY created_at DESC LIMIT 5"
```

## Constant source
```bash
grep -n "MTP_ZSCORE\|Z_SHORT\|Z_MID\|Z_LONG" /root/.hermes/scripts/hermes_constants.py
```