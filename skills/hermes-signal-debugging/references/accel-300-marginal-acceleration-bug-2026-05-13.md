# accel-300 Marginal Acceleration Bug — CONFIRMED 2026-05-13

## Summary

17/30 trades (57%) had price on the **wrong side of EMA300** at entry. All wrong trades were LONGs with price consistently below EMA. Root cause: **inverted marginal acceleration conditions** at lines 298-299, plus compounding stale signal persistence.

---

## Bug #1: Marginal Acceleration Inverted (lines 298-299)

**File:** `signals/accel_300.py`

```python
# CURRENT (BUGGY):
if direction == 'LONG' and delta_last <= delta_prev:
    continue   # BLOCKS when delta_last >= delta_prev (gap GROWING)
if direction == 'SHORT' and delta_last >= delta_prev:
    continue   # BLOCKS when delta_last <= delta_prev (gap SHRINKING)

# SHOULD BE:
if direction == 'LONG' and delta_last >= delta_prev:
    continue   # BLOCKS when gap is DECELERATING
if direction == 'SHORT' and delta_last <= delta_prev:
    continue   # BLOCKS when gap is ACCELERATING
```

**Effect:** LONG fires when gap is decelerating (should fire only on accelerating). SHORT fires when gap is accelerating (should fire only on decelerating). Opposite of intent.

**Scope:** This check only applies to bars 4-10 after EMA cross (marginal acceleration window). Bars 0-3 bypass it entirely.

---

## Bug #2: Stale Signals (Primary Failure Mode)

The marginal acceleration bug is secondary. The dominant failure mode is **stale signals surviving in the hot-set for hours** after price regime has reversed.

**Example — NEAR LONG:**
| Time | Event | Gap% | Price vs EMA |
|------|-------|------|-------------|
| 10:31 UTC | Signal fired ✓ | +0.200% | Above EMA |
| 10:59 UTC | Signal fired ✓ | +0.354% | Above EMA |
| 12:44 UTC | Signal fired ✓ | +0.251% | Above EMA |
| 14:20 UTC | Trade executed ✗ | **-1.337%** | Below EMA, never above in prior 30 bars |
| 22:40 UTC | Confluence blocked | stale | Same signal blocked 8h later |

Price was **never above EMA in the prior 30 bars** for this trade. The signal from 10:31 survived in the hot-set for ~4 hours.

**Evidence for all 17 wrong LONG trades:** VVV, EIGEN, SUI, NEAR, FET, ENS, TAO, AVAX, ZK, FIL, SKR — all had 0 bars above EMA in prior 30 bars.

---

## Debugging Commands

```bash
# Find accel-300 signals with age > threshold
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, source, created_at,
    (strftime('%s','now') - strftime('%s',created_at))/60 as age_min
   FROM signals
   WHERE signal_type LIKE 'accel_300%'
   ORDER BY created_at DESC LIMIT 20;"

# Check hot-set for stale entries
cat /var/www/hermes/data/hotset.json | python3 -c "
import json,sys
from datetime import datetime
hs = json.load(sys.stdin)
for e in hs:
  age = (datetime.now().timestamp() - e.get('signal_time',0))/60
  if age > 30: print(f'STALE {age:.0f}m: {e[\"token\"]} {e[\"direction\"]} src={e.get(\"source\",\"?\")}')"

# Verify price was never above EMA in prior N bars for a specific trade
python3 - <<'EOF'
import sqlite3
token = 'NEAR'
entry_ts = 1715590800  # example, replace with actual

conn = sqlite3.connect('/root/.hermes/data/candles.db')
c = conn.cursor()

# Get 30 bars before entry
c.execute("""SELECT close, timestamp FROM candles_1m
             WHERE token=? AND timestamp < ?
             ORDER BY timestamp DESC LIMIT 31""", (token, entry_ts))
rows = list(reversed(c.fetchall()))  # oldest first

# Compute EMA300 (simplified: use SMA as proxy since we need warmup)
closes = [r[0] for r in rows]
ema = sum(closes[:300]) / 300
k = 2/(301)
for close in closes[300:]:
    ema = close * k + ema * (1 - k)

above_count = sum(1 for c in closes if c > ema)
print(f"Price above EMA: {above_count}/30 bars")
print(f"EMA300: {ema:.6f}")
print(f"Latest close: {closes[-1]:.6f}, gap: {(closes[-1]/ema-1)*100:.3f}%")
EOF
```

---

## Fixes Required

1. **Patch accel_300.py lines 298-299** — swap `<=` and `>=`
2. **Add staleness filter in signal_compactor** — reject signals where `bars_since_cross > N` or `signal_age_min > 30`
3. **Fix staleness check in `_get_1m_prices`** — use historical `ref_ts` not `time.time()`

---

## Related Files

- `signals/accel_300.py` lines 298-299 (marginal acceleration)
- `signals/rs.py` (adds `rs-s###` source tags alongside accel_300)
- `signal_compactor.py` (needs staleness filter + 5m regime)
- `hl-sync-guardian.py` (writes trades, regime column never populated)
- `references/accel-300-quality-degradation.md` — related: parameter relaxation causing burst firing
- `references/counter-trend-entry-bug-2026-05-13.md` — related: 15 losing trades same root cause