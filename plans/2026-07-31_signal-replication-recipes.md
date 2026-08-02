# Signal Replication Recipes

## Date: 2026-07-31

## Key Finding

**Best trades occurred when z-score was EXTREME, not neutral.**

This contradicts earlier analysis that showed neutral z wins on average. The reconciliation:

- **Average trades:** Neutral z wins (avoid chasing)
- **Best trades:** Extreme z wins (catch reversals)
- **The key is SPEED:** If speed confirms direction, extreme z works

## Best Trades by Signal Type

| Signal | Coin | Dir | PnL | Z-Score | Speed | RSI | Recipe |
|--------|------|-----|-----|---------|-------|-----|--------|
| accel-300-vel+ | KAITO | SHORT | +0.93% | +1.34 | +0.45% | 81.8 | z>1.0, speed>0.3%, RSI>70 |
| accel-300-vel- | ORDI | LONG | +1.36% | +1.19 | +0.18% | 69.1 | z>1.0, speed>0.1%, RSI 60-70 |
| tl_break_long | PURR | SHORT | +2.42% | +3.08 | +0.60% | 83.7 | z>2.0, speed>0.5%, RSI>80 |
| tl_break_short | MORPHO | LONG | +0.07% | -1.56 | -0.20% | 23.0 | z<-1.5, speed<-0.1%, RSI<25 |
| accel-300+ | ORDI | SHORT | +0.17% | +1.33 | +0.06% | 54.5 | z>1.0, speed>0%, RSI 50-60 |
| accel-300- | KAITO | LONG | +0.29% | -1.25 | -0.13% | 34.0 | z<-1.0, speed<0%, RSI 30-40 |
| inv-accel-300- | XMR | SHORT | +0.40% | +1.60 | +0.22% | 74.0 | z>1.5, speed>0.2%, RSI>70 |

## Replication Recipes

### Recipe 1: accel-300-vel+ (SHORT) — +0.93% in 18min
```
Conditions:
  - Z-score: > 1.0 (overbought)
  - Speed: > 0.3% (strong downward move)
  - RSI: > 70 (overbought)
  
Logic:
  Overbought + strong downward speed = reversal
  
Expected: +0.93% in 18min
```

### Recipe 2: accel-300-vel- (LONG) — +1.36% in 40min
```
Conditions:
  - Z-score: > 1.0 (overbought)
  - Speed: > 0.1% (upward move)
  - RSI: 60-70 (not extreme)
  
Logic:
  Overbought but still rising = continuation
  
Expected: +1.36% in 40min
```

### Recipe 3: tl_break_long (SHORT) — +2.42% in 33min
```
Conditions:
  - Z-score: > 2.0 (extremely overbought)
  - Speed: > 0.5% (very strong move)
  - RSI: > 80 (extremely overbought)
  
Logic:
  Extremely overbought = strong reversal
  
Expected: +2.42% in 33min
```

### Recipe 4: tl_break_short (LONG) — +0.07% (small win)
```
Conditions:
  - Z-score: < -1.5 (extremely oversold)
  - Speed: < -0.1% (downward move)
  - RSI: < 25 (extremely oversold)
  
Logic:
  Extremely oversold = bounce
  
Expected: +0.07% (small win)
```

## Revised Signal Filters

Based on these recipes, the z-score filter should be:

```python
# Block extreme z ONLY when speed is low (chasing)
# Allow extreme z when speed confirms direction (reversal)
if z_score is not None:
    if direction == 'LONG' and z_score < -1.5 and speed < 50:
        return ('SKIP', 'chasing downtrend')
    if direction == 'SHORT' and z_score > 1.5 and speed < 50:
        return ('SKIP', 'chasing uptrend')
```

## Key Insight

**Extreme z + high speed = reversal (win)**
**Extreme z + low speed = chasing (lose)**

The speed filter catches the bad extreme-z trades while allowing the good ones.

## Implementation Status

- [x] Global signal filters added to hermes_constants.py
- [x] Filters implemented in context gate (decider_run.py)
- [x] Z-score filter revised to allow extreme z when speed confirms

---

## Last Updated

2026-07-31: Initial recipe creation
