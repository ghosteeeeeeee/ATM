# RS Signal Failure: Falling Knives & Ancient Levels (2026-05-17)

## Problem
RS (support/resistance) signal fires on:
1. Price near a structurally valid level that was broken hours/days ago (catching the knife)
2. Price in a flat, directionless period — level is valid but no catalyst

Result: 50+ consecutive losing trades across all rs-sX and rs-rX combos.

## Root Cause 1: Ancient Levels Treated as Fresh

RS detects levels with hundreds of historical touches. A level like rs-s442 (USUAL, 442 touches) is valid structurally, but 400+ touches are ancient — from weeks/months ago when price was in a completely different regime.

The `RS_RECENCY_WINDOW = 200` and `RS_RECENCY_BOOST_K = 3.0` attempt to weight fresh touches, but:
- Low-touch fresh levels (1-20 touches) have 44% WR and +0.80% avg — BETTER than high-touch ancient
- Ancient levels (100+ touches) have 40% WR and +0.03% avg — nearly zero edge
- The recency bonus in `_compute_confidence()` adds +0 to +8, but a level with 400 touches from 2 months ago is still scored as high confidence

The bounce confirmation is also unreliable: price_history is close-only (open=high=low=close per row), so bounce detection cannot see intra-candle wicks. It detects bounces that may not exist.

## Root Cause 2: RS_PROXIMITY_K Too Loose

`RS_PROXIMITY_K = 1.20` means price can be 1.2 ATRs away from a level and still fire.

Example: ETH at $1850, ATR(14) = $60 (3.2%)
- 1.2 ATRs = 3.9% = $72 from the level
- Level at $1800, price at $1850 → 2.7% away → 0.84 ATRs → fires
- But $72 away in a flat market means you're entering based on a level from a completely different price regime

## Key Data from signal_outcomes (May 16-17)

All zscore-pump+ combos with rs-sX are LOSERS:
```
rs-s128,zscore-pump+  : -414% total (2 trades)
rs-s58,zscore-pump+   : -258% total (2 trades)
rs-s30,zscore-pump+   : -234% total (2 trades)
rs-s42,zscore-pump+   : -235% total (2 trades)
rs-s409,zscore-pump+  : -247% total (2 trades)
```

Every single rs-sX,zscore-pump+ combo is negative. The RS+ (support bounce) direction is fundamentally broken when paired with zscore-pump+.

## Constants That Need Changing

| Constant | Current | Proposed | Why |
|---|---|---|---|
| `RS_PROXIMITY_K` | 1.20 | 0.60 | Fire only within 0.6 ATRs — tighter entry |
| `RS_MIN_TOUCHES` | 4 | 6 | More historical validation |
| `RS_LEVEL_LOOKBACK` | 100 | 60 | Smaller window = more recent structure |

## DB Navigation
- `signals_hermes_runtime.db` → signals table: source, confidence, z_score, decision, executed
- `signals_hermes_runtime.db` → signal_outcomes: is_win, pnl_pct, closed_at (key table for trade analysis)
- Query recent outcomes: `WHERE closed_at > '2026-05-16'`
- signal_outcomes JOIN signals on token — but signal_type is on signal_outcomes (no join needed for type filtering)