# accel-300+ LONG — RS Confirmation Is Backwards

## Finding (2026-06-06)

96h trade analysis of 200 closed trades:

| Signal | Trades | Win Rate | Avg PnL |
|--------|--------|----------|----------|
| accel-300+ LONG (all RS-confirmed) | 45 | 22.2% | -0.41% |
| accel-300- SHORT rs-broken | 139 | 53.2% | +0.20% |
| accel-300- SHORT rs-confirmed | 16 | 37.5% | -0.00% |
| rs-broken (all signals) | 139 | 53.2% | +0.20% |
| rs-confirmed (all signals) | 61 | 26.2% | -0.30% |

## Root Cause

accel-300+ LONG had 45 trades, ALL RS-confirmed, 0 rs-broken. Every single LONG was paired with a confirmed (non-broken) RS level.

- **RS-confirmed levels** = consolidation zones where price respects a level repeatedly = weak momentum = the opposite of what accel_300 measures (acceleration)
- **RS-broken levels** = level invalidation = strong momentum breakout = ideal for accel model

The RS confirmation filter was systematically selecting for the worst possible signals for accel-300+ LONG.

## Data Source

`/var/www/hermes/data/trades.json` — 200 closed trades, 2026-06-04 to 2026-06-06.

## Fix Options

1. **Best**: `ACCEL_300_PLUS_RS_BROKEN_ONLY = True` — only fire accel-300+ LONG on rs-broken signals (strong momentum)
2. **Alternative**: Raise `RS_DECIDER_CONF_FLOOR` to 70-75 and `RS_DECIDER_MIN_TOUCHES` to 175-200 to filter out weak confirmed levels
3. **Killswitch**: Disable accel-300+ LONG entirely until fixed

## Verified Facts

- 0 of 45 accel-300+ LONG trades had rs-broken — the filter actively blocked all the good ones
- 139 of 155 accel-300- SHORT trades had rs-broken — SHORT naturally breaks levels (downtrends)
- RS-confirmed is anti-correlated with accel-300+ success
