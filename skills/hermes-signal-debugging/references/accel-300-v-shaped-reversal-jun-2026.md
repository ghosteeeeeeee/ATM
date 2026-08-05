# accel-300 V-Shaped Reversal — Signal Correctly Suppressed (Not a Bug)
## 2026-06-15 Session

## The Move (User's Claim)
- 19:08 EST: price = 0.3930 (swing low)
- 19:08–22:05 EST: rallied to 0.4114 (+4.7%)
- User expected accel-300 LONG to fire on the rally

## What Actually Happened

### Signal fired CORRECTLY on the SHORT side
accel_300_short fired 4 times at the bottom:
- 17:53 EST: price=0.3935, gap=-0.1066%
- 17:58 EST: price=0.3932, gap=-0.1065%
- 18:03 EST: price=0.3932, gap=-0.1065%
- 18:09 EST: price=0.3939, gap=-0.1064%
- 18:16 EST: price=0.3945, gap=-0.1139%
- 18:21 EST: price=0.3936, gap=-0.1139%
- 18:49 EST: price=0.3937, gap=-0.1762%
- 18:55 EST: price=0.3937, gap=-0.1762%
- 19:01 EST: price=0.3936, gap=-0.1762%  ← local low at ~0.3930 was here

Then accel_300_short fired again on the pullback:
- 22:30 EST: price=0.4085, gap=-0.2883%
- 22:35 EST: price=0.4087, gap=-0.2883%

### Why No LONG on the Rally
accel_300 requires ALL of these simultaneously:
1. Gap >= 0.20% above EMA (persistent)
2. Gap actively GROWING over the window
3. Price oscillating around EMA (gap going from -1.75% to +0.25% to 0% = no persistent gap)

The V-shaped recovery crossed through EMA multiple times without establishing a persistent gap >= 0.20%. The signal is designed for slow-breakout confirmation, not V-shaped momentum spikes.

## Critical Data Mismatch
signals_hermes_runtime.db shows actual fired signals at 0.3935-0.3945 range.
signals_hermes.db price_history shows latest UMA price at 0.4067 — NOT the 0.3930→0.4114 range.

**The user's "current price" of 0.4098 did not come from signals_hermes.db.**
Tokyo server Binance feed may differ from what the HL chart shows.

## Diagnostic Commands
```python
# Check what signals actually fired for a token
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c.execute('''
    SELECT signal_type, source, direction, confidence, value, price, created_at
    FROM signals WHERE token = ? ORDER BY created_at DESC LIMIT 50
''', ('UMA',))
```

## What NOT to Change
- Don't relax ACCEL_300_MIN_GAP_PCT_LONG for V-shaped moves
- Don't reduce PERSISTENCE_BARS
- The signal is working correctly — it identified the SHORT at the bottom
- V-shaped reversals are a known gap in accel-300's design (not a bug)

## Umbrella Context
- Related: `accel-300-market-chop-not-a-bug-jun-2026.md` — same lesson: signal correctly suppresses, not a bug
- Related: `rs-uma-bounce-lookback-jun-2026.md` — RS missed the same move for different reasons
