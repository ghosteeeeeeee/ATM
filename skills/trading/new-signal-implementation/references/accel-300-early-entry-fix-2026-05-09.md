# accel_300 Parameter Fix — 2026-05-09

**Problem**: accel-300+ was firing 2-3 bars after the EMA cross — catching local peaks.
Winners showed bars_since_cross=2-4; losers reversed within 0.1-3 min of entry.

**Fix applied** (`/root/.hermes/scripts/signals/accel_300.py`):
```
PERSISTENCE_BARS:  2 → 1   (fires on first bar close above EMA)
MIN_GAP_PCT:     0.10 → 0.15  (filters thin-gap entries that reverse fast)
```

**Why acceleration gate still protects with PERSISTENCE_BARS=1:**

With PB=1, gap_then_idx = i-1:
- `avg_gap_growth = gap_now - gap_1` (delta_last)
- MIN_GAP_GROWTH_PCT=0.02 gate: delta_last > 0.02%
- Acceleration gate: delta_last > delta_prev (momentum still building)

Together these two conditions filter false breakouts even at 1-bar persistence.

**Verified on live tokens:**
```
PERSISTENCE_BARS=1
MIN_GAP_PCT=0.15

BTC: gap=0.201% growth=0.068% bars_since_cross=24 ✓
LINK: gap=0.185% growth=0.105% bars_since_cross=2 ✓
2Z: gap=0.512% growth=0.804% bars_since_cross=0 ✓ (fires immediately)
MON: gap=0.755% growth=0.648% bars_since_cross=4 ✓
```

**Trade outcome analysis (27 closed trades, session 2026-05-09):**
| Metric | Value |
|--------|-------|
| Winners | 10 (avg +2.60%) |
| Losers | 17 (avg -0.31%) |
| Close reason | 20/27 = atr_sl_hit |
| conf=99 (with RS) | 29% WR, 17L/7W |
| conf=75 (no RS) | 100% WR |

**Key insight**: conf=99 signals (RS-boosted) underperform conf=75 (no RS) — RS is boosting mediocre entries, not filtering them. This is a signal_compactor issue, not an accel_300 fix.

**Watch for after deploying:**
- Signal frequency increases (more fires per cycle)
- If `atr_sl_hit` rate climbs above 50% → raise MIN_GAP_PCT back to 0.12
- If volume too high → raise MIN_GAP_GROWTH_PCT to 0.03

**Verification test:**
```bash
cd /root/.hermes/scripts && python3 -c "
import sys; sys.path.insert(0,'.')
from signals.accel_300 import PERSISTENCE_BARS, MIN_GAP_PCT
print(f'PERSISTENCE_BARS={PERSISTENCE_BARS}, MIN_GAP_PCT={MIN_GAP_PCT}')
from signals.accel_300 import _get_1m_prices, detect_accel_300
for token in ['BTC','LINK','MON','S','FET']:
    p = _get_1m_prices(token, lookback=700)
    if p:
        r = detect_accel_300(token, p)
        if r: print(f'{token}: gap={r[\"gap_pct\"]:.3f}% growth={r[\"gap_growth\"]:.3f}% bars={r[\"bars_since_cross\"]}')
"
```