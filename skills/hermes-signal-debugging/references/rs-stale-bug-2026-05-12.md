# RS Signal Silent Failure — 2026-05-12

## Symptom
RS signals completely stopped firing. All other signals (accel_300, ma_cross, hh_hl, macd_accel) continued normally. Pipeline log showed no RS output at all.

## True Root Cause: `add_signal()` Missing Required Args

`signals/rs.py` `scan_rs_signals()` was calling `add_signal()` with only 3 of 5 required positional arguments:

```python
# BROKEN — causes TypeError crash per token, silently swallows ALL RS signals
sid = add_signal(
    token=token.upper(),
    direction=sig['direction'],
    signal_type=RS_SIGNAL_TYPE,
    # source=sig['source'],      # MISSING
    # confidence=sig['confidence'],  # MISSING
)
```

`add_signal()` signature: `add_signal(token, direction, signal_type, source, confidence, ...)`.
`source` and `confidence` are **required positional args** — not kwargs with defaults.
Python raises `TypeError: add_signal() missing 2 required positional arguments: 'source' and 'confidence'`.
This crashed on every token, so zero signals were ever written.

## Fix Applied

```python
# FIXED
sid = add_signal(
    token=token.upper(),
    direction=sig['direction'],
    signal_type=RS_SIGNAL_TYPE,
    source=sig['source'],
    confidence=sig['confidence'],
)
```

Verified working: RS scan fired 56 signals in 10.7s.

## False Lead: Staleness Check

The original bug report claimed `rows[-1][0]` checked the wrong edge of the lookback window.
**This was wrong.** The query structure:

```sql
SELECT timestamp, price FROM (
    SELECT timestamp, price FROM price_history
    WHERE token = ? ORDER BY timestamp DESC LIMIT 4700
) sub
ORDER BY timestamp ASC
```

After the outer `ORDER BY timestamp ASC`, `rows[-1][0]` IS the newest candle — correct for staleness checking.
The staleness check itself is fine. The real bug was the TypeError.

## Stale Tokens (Legitimate Skips)

These tokens have genuinely stale `price_history` (7+ days old) and are correctly skipped:
MAV, MAVIA, MEW, PROMPT, SCR, USTC, YZY, ZEREBRO.

## Diagnostic Pattern

When RS is completely silent and other signals work:

```bash
cd /root/.hermes/scripts && python3 -c "
import sys; sys.path.insert(0,'.')
from signal_schema import get_all_latest_prices
from signals.rs import scan_rs_signals
prices = get_all_latest_prices()
added, tokens = scan_rs_signals(prices)
print(f'RS added={added}')
" 2>&1 | grep -E "TypeError|added|rs.*stale"
```

If `TypeError` appears → missing `source`/`confidence` in `add_signal()` call.
If `added=0` with no TypeError → check blacklist, cooldown, or direction flags (RS_PLUS_ENABLED/RS_MINUS_ENABLED).

## Also: RS_PLUS/RS_MINUS Direction Kill-Switches

`scan_rs_signals()` checks `hermes_constants.RS_PLUS_ENABLED` and `RS_MINUS_ENABLED`:
```python
if sig['direction'] == 'LONG' and not RS_PLUS_ENABLED:
    continue
if sig['direction'] == 'SHORT' and not RS_MINUS_ENABLED:
    continue
```
Both default True. If one is False, that direction is silently dropped.