# RS Signal Quality — June 3 2026 Session

## Key Finding: rs.py Signals Are 50/50 Directional

Executed signals today: 34 total. Sample of 16 with price data:
- Direction correct on next candle: 8/16 (exactly 50%)
- Direction wrong on next candle: 8/16 (50%)

This is NOT a code bug. rs.py is a mean-reversion signal — it fires when price
bounces from a structural level. In trending markets, price doesn't bounce — it
breaks through. The signal logic is correct; the market regime defeats it.

## Bounce Threshold — No Inconsistency (Verified 2026-06-03)

Earlier session claimed "bounce threshold inconsistency" between touch and bounce.
Verification shows this was WRONG:

| Parameter | Value | Calculation |
|-----------|-------|-------------|
| Touch threshold | 1.00 ATR | _BOUNCE_THRESH_ATR = 1.00 |
| Bounce follow-through | >0.025% | next_close > c['close'] * 1.00025 (LONG) |
| Bounce follow-through | >0.025% | next_close < c['close'] * 0.99975 (SHORT) |

0.025% of a typical coin price ≈ ~1 ATR. Thresholds are consistent.

## RS Signal Source Tag Decoding

Source tags encode level touch count: `rs-s42` = support level with 42 historical
touches. Higher touch count = more tested, more reliable level.

Session analysis by touch count (accel+RS combos, small n):
- 20-50 touches: 3/3 WR=100%, avg +0.34%
- 200+ touches: 3/5 WR=60%, avg +0.12%
- 50-100 touches: 0/2 WR=0%, avg -0.28%
- 100-200 touches: 1/2 WR=50%, avg -0.07%

## Pending Signals After Confluence Fix (2026-06-03)

After `_signal_type_key` normalization (rs-s-broken + rs-r collapsed to 1 type):
- 129 pending signals all blocked at confluence (0 would pass)
- Pipeline shows Approved signals: 0 — fix is active and working

Signal families now blocked by confluence:
- rs-sXXX alone: blocked (1 unique type)
- rs-rXXX alone: blocked (1 unique type)
- rs-rXXX,rs-s-broken: blocked (both → rs after normalization = 1 type)

## All Loss Categories Hit ATR SL

Today's losing trades by category:
- accel-300-+rs: 8W/13L (38% WR) — worst group
- rs-only (no accel): 10W/12L (45% WR)
- rs-r+rs-s-broken: now blocked by confluence fix
- accel-300++rs: 6W/7L (46% WR)

All loss categories hit `atr_sl_hit`. ATR stops are working — entries are
directionally wrong, not missing stops.

## Mean-Reversion Signal Design Limitation

rs.py is a mean-reversion bounce signal. It detects when price approaches a
structural level (support or resistance) and expects a bounce.

Failure mode: In trending markets (like current crypto), price approaches
resistance and DOESN'T bounce — it breaks through. rs.py fires SHORT expecting
the bounce, but price continues up. Result: 50/50 directional accuracy.

## What Would Actually Help (outside rs.py scope)

- Better regime detection (more accurate SHORT_BIAS/LONG_BIAS calls)
- Stronger momentum co-signals (accel-300 helps but insufficient alone)
- Stops calibrated to actual market noise (ATR is too tight for trending markets)
- Consider blocking accel-300-,rs-s-broken (worst performing at 38% WR)