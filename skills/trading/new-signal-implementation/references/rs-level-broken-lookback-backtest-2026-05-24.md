# RS Level Broken Lookback — Backtest Findings (2026-05-24)

## Context: Why This Matters

BCH and UMA LONG trades entered on valid support (rs-s##) bounces but immediately reversed because the support level had **become resistance** — broken hours earlier, price rallied back to it, and the bounce entry caught the wrong side of the flip.

The proposed fix: `_level_recently_broken` lookback moved from hardcoded 20 to `RS_LEVEL_BROKEN_LOOKBACK` constant in hermes_constants.py.

## Backtest: AAVE, AVAX, APT, ATOM (~15 months of 1m data each)

| Lookback | ~Hours on 1m | Block Rate | Clean Signals | Verdict |
|----------|-------------|------------|--------------|---------|
| 20 | 20 min | 5-62% | 4,000-10,700 | Too loose — catches little |
| 50 | 50 min | 13-79% | 2,000-9,700 | Better |
| 100 | 1.7 hrs | 26-89% | 1,000-9,300 | Good balance |
| **200** | **3.3 hrs** | **34-96%** | **500-8,200** | **Recommended** |
| 300 | 5 hrs | 43-98% | 200-7,100 | Aggressive |
| **500** | **8.3 hrs** | **50-100%** | **0-2,000** | **Overkill** |

## The BCH Failure Case

- BCH support at $350 was broken **25 hours** before entry (2026-05-23 15:30 UTC → 2026-05-24 16:27 UTC)
- Lookback 500 (~8.3 hrs) would **NOT** catch this
- BUT: **RS_LEVEL_BROKEN_LOOKBACK = 200** (~3.3 hrs) is also insufficient for this case
- A 1500+ candle lookback needed — which suggests the real fix is not just lookback tuning

## Key Metric: Clean Signal Retention

At LB=200: clean signal retention = 4-77% depending on token. AAVE loses 96% of signals at LB=200 (only 43 clean out of 1,068 total). This is token-dependent — AAVE has highly dynamic S/R that breaks frequently.

At LB=100: retention = 11-87%. Still aggressive for AAVE, fine for AVAX/APT/ATOM.

## Recommended Value

**`RS_LEVEL_BROKEN_LOOKBACK = 200`** — catches levels broken within ~3.3 hours on 1m.

500 was rejected: it effectively disables the RS signal on some tokens (100% block rate on AAVE's history), and still wouldn't catch the BCH case (25-hour gap).

## Important: 1m-Only Constraint

The system reads 1m candles. A level broken 25 hours ago (BCH case) requires LB=1500 to catch on 1m. This is not practical — such a large lookback would block nearly all signals.

**The real problem is not lookback depth — the system already sees the full history. The gap is in the REJECTION logic:** `_level_recently_broken` only checks if the level was broken recently, but does NOT check if the nearest resistance (for LONG) or support (for SHORT) is an old level that has flipped polarity.

## The Complementary Fix (Not Just Lookback)

The proposed `RS_LONG_MAX_DIST_RESIST` constant (block LONG if nearest resistance > 2.5x ATR above entry) would NOT have helped BCH — resistance was 21.9x ATR above entry. But it addresses the ~90% of cases where resistance IS within 2.5x ATR.

## Backtest Code Pattern

```python
# Sweep lookback values on historical candles
LOOKBACKS = [20, 50, 100, 150, 200, 300, 500]

for lb in LOOKBACKS:
    total = clean = blocked = 0
    for i in range(warmup + lb, len(candles), step):
        # Find nearest support
        # Check if broken within lb candles
        # Record whether signal would have fired
        was_broken = any(closes[j-1] > nearest_support > closes[j]
                         for j in range(max(0, i-lb), i))
        total += 1
        if was_broken: blocked += 1
        else: clean += 1
    print(f"LB={lb:3d}: {clean}/{total} clean ({clean/total*100:.0f}%)")
```

Key: step=3-5 candles for speed, full scan is too slow on 54k candles/token.
