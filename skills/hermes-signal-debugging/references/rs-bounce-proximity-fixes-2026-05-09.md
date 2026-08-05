# RS Signal Fixes Applied 2026-05-09
**Files:** `signals/rs.py`

## Fixes Applied

### `_BOUNCE_THRESH_ATR`: 0.20 → 1.00
0.20× ATR was 31-33x too tight for low-ATR tokens. For ADA (price $0.272, ATR=0.024%), threshold was 0.0048% of price — price must be within 0.005% of level to count as a touch. This was noise-level and unreachable.

**Result:** bounce=True now achievable for the first time. BIGTIME is first token to achieve it. Signal count dropped from 11 → 8 (fewer, stronger).

### `RS_MIN_TOUCHES`: 5 → 8
Compensates for looser bounce threshold. Only structural levels (8+ touches) qualify for the bounce bonus.

### `RS_PROXIMITY_K`: 1.20 → 1.00
Fires within 1 ATR instead of 1.2 ATR — catches the move closer to the level for earlier entry.

## Root Cause
ATR-normalized thresholds vary wildly by token. A threshold that seems reasonable for BTC (ATR ~0.5%) becomes unreachable for low-ATR tokens. The fallback path (`price * 0.0015`) was 31x wider than the ATR-normalized path — making the bounce confirmation practically impossible for most tokens.

## Verification
```python
cd /root/.hermes/scripts && python3 -c "
import sys; sys.path.insert(0,'.')
from signal_schema import get_all_latest_prices
from signals.rs import scan_rs_signals
prices = get_all_latest_prices()
added, tokens = scan_rs_signals(prices)
print(f'RS signals: {added}')
"
```