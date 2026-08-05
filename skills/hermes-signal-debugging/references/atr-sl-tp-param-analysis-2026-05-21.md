# ATR SL/TP Parameter Analysis — 2026-05-21

## Root Cause
After T's param tweaks (K_PHASE 0.10→0.08, ATR_K tiers 2.0/2.5/1.0 → 0.50/0.25/0.75, ATR_SL_MIN 0.50%→1.00%), the system survives volatility but does not close on profit.

**Phase multipliers are fully negated by the floor.**
- K_PHASE_ACCEL/EXH/EXT_FAST = 0.08 × base_k (0.75/0.50/0.25) → k_eff = 0.06/0.04/0.02
- All below ATR_SL_MIN_ACCEL=0.70% floor → every ACCELERATING/EXHAUSTION/EXTREME established trade gets exactly 0.70% SL
- Phase multipliers become dead code

**TP is floor-constrained for low-ATR tokens.**
- At k=0.50, TP multiplier 1.25 → TP = 0.625% ATR, below ATR_TP_MIN=1.1% floor
- TP multiplier has no effect on tokens with ATR < ~1.2%

**TP-SL gap is razor-thin.**
| ATR% | Tier | SL% (floor) | TP% (floor) | Gap |
|------|------|-------------|-------------|-----|
| 0.50 | LOW | 1.00 | 1.10 | 0.10% |
| 0.75 | LOW | 1.00 | 1.10 | 0.10% |
| 1.00 | MED | 1.00 | 1.25 | 0.25% |
| 1.50 | MED | 1.30 | 1.50 | 0.20% |

A 2-4 candle pullback hits SL before TP is ever reached.

## Evidence from Closed Trades (2026-05-17 to 2026-05-20)

### profit-monster (winners) — correctly captures swings
```
GRIFFAIN SHORT  -0.68% move → +203.5% pnl   (entry at top, exit at bottom)
GALA    SHORT  -0.67% move → +200.7% pnl
BCH     LONG   +0.59% move → +297.2% pnl
NEAR    LONG   +1.04% move → +519.9% pnl
```
PM works because it has no tight ATR SL constraint.

### atr_sl_hit (losers) — hit on tiny 0.3-0.9% adverse moves
```
PURR  SHORT  +1.41% move → -140.7% loss  dur=27min  sl_dist=1.5
ORDI  SHORT  +0.65% move → -64.8% loss   dur=74min  sl_dist=1.5
MERL  SHORT  +0.46% move → -45.9% loss   dur=29min  sl_dist=1.5
NIL   SHORT  +0.77% move → -77.0% loss   dur=9min   sl_dist=1.5
TRB   SHORT  +0.69% move → -69.3% loss   dur=6min   sl_dist=1.5
LIT   SHORT  +0.90% move → -90.0% loss   dur=8min   sl_dist=1.5
ONDO  SHORT  +1.65% move → -164.9% loss  dur=13min  sl_dist=1.5

BCH   SHORT  +0.37% move → -36.9% loss   dur=29min  sl_dist=0.0
APEX  SHORT  +0.34% move → -33.7% loss   dur=21min  sl_dist=0.0
GALA  SHORT  +0.85% move → -85.2% loss   dur=26min  sl_dist=0.0
DASH  SHORT  +0.74% move → -74.4% loss   dur=9min   sl_dist=0.0
ZEN   SHORT  +0.57% move → -57.4% loss   dur=35min  sl_dist=0.0
```
These tokens moved only 0.3-0.9% against direction and got stopped out for -30% to -90% loss. The trade had almost no room to breathe.

## The Mechanism
For a token with 1.5% ATR under new params:
- Old: k=2.0 → SL = 3.0%
- New: k=0.5 → SL = 0.75%, floored at 0.70% → **0.70% SL**

A position that opens and immediately moves 0.2% against direction has lowest_price set from an early candle. SL = entry × (1 + 0.007) = 0.70% away. Exit hits at +0.6% from entry → SL triggered. The trade never gets a chance to develop.

## Recommendations
1. **Raise ATR_SL_MIN_INIT from 0.70% to 1.0%** — new trades need breathing room
2. **Raise K_PHASE_ACCEL_FAST from 0.08 toward 0.15-0.20** — the 0.08 value is too aggressive; phase multipliers are negated anyway at current floor
3. **Add MIN_PROFIT_TO_ARM_TRAILING = 0.5%** — trailing SL mechanism should only arm after trade is in profit by ≥0.5%
4. **Skip tokens with ATR < 0.4%** — minimum ATR threshold for entry to prevent razor-thin SL on ultra-low-vol tokens
5. **Widen the TP-SL gap for LOW_VOL tier** — consider ATR_TP_MIN=1.5% for LOW_VOL to give trades room to work

## What NOT to change
- ATR_K_NORMAL_VOL=0.5 is correct — fixed the core problem of 4-6% SL on 2% ATR tokens
- The problem is not k, it's the floor interaction and the razor-thin gap