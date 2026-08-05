# RS Bounce Confirmation — Threshold Fix (2026-05-08)

## Symptom
RS signals dropped from ~110/cycle (May 6) to ~3/day (May 7-8). Valid structural levels
exist but `detect_rs_signal()` returns `None`. Root cause was the `_bounce_confirmation`
2-candle sequential logic being too strict for ranging markets.

## Three Historical States

### Original (d31692f: scripts/rs_signals.py) — EASIER, HIGH VOLUME
```python
if direction == 'LONG':
    for c in recent:
        touch_pct = abs(c['low'] - level) / level * 100.0
        if touch_pct < 0.20:           # wick touched level
            if c['close'] > c['open']:  # THIS candle was bullish → bounce confirmed
                return True
```
Used wick (low/high) for touch detection. Single candle check. Fired ~110/cycle on May 6.

### Initial signals/rs.py (d31692f) — HARDER, LOW VOLUME
```python
for i, c in enumerate(recent):
    if abs(c['close'] - level) < thresh:  # close must be AT level
        if i + 1 < len(recent):
            next_close = recent[i + 1]['close']
            if next_close > c['close'] * 1.0005:  # NEXT candle >0.05% follow-through
                return True
```
Close-only touch + 2-candle sequential requirement. Much stricter. RS dropped to ~3/day.

### Applied Middle Ground (2026-05-08) — RESTORED CONDITION (A)
```python
if direction == 'LONG':
    for i, c in enumerate(recent):
        if abs(c['close'] - level) < thresh:
            if c['close'] > c['open']:           # (a) this candle was bullish → fire
                return True
            if i + 1 < len(recent):
                if next_close > c['close'] * 1.00025:  # (b) next candle >0.025% partial follow-through
                    return True
```
**Condition (a)**: restored original single-candle logic — if the touch candle is bullish,
bounce is confirmed immediately. **Condition (b)**: new softer check — next candle only
needs to move >0.025% (half the old 0.05% threshold) for partial follow-through.

## Result (2026-05-08 live test)
```
Signals written to DB: 59
bounce=True: 3 tokens (SUSHI SHORT, APE LONG, KSHIB SHORT — passed both conditions)
bounce=False: 56 tokens (passed condition (a) only — touch candle was directional but no follow-through)
```
Up from ~3/day to ~59/scan. 106 RS signals in last 10 min in DB.

## Key Finding: signal_compactor.py has NO uncommitted changes
The signal IS working — market conditions (flat ranges, no follow-through) were the
bottleneck, not code bugs. The `_bounce_confirmation` middle-ground fix was the only change needed.

## `scan_rs_signals` return format
Returns `(added: int, signaled_tokens: list[str])`. The `signaled_tokens` is a list of
token strings, NOT signal output strings. Count signals with the return tuple's first
element, not by parsing output.

## DB path: `/root/.hermes/data/signals_hermes_runtime.db` (47MB)
NOT the 0-byte file at `/var/www/hermes/data/signals_hermes_runtime.db`.

## Related Triggers
- "RS bounce always false"
- "RS signals not firing"
- "RS level recently broken always false"
- "RS signals not firing despite valid levels"