## CEO Report — 2026-09-13 ~03:15 UTC

### Diagnosis
rr_structural signal has 12 trades/7d. Only 1 (INJ SHORT) actually fired through detect() — all others assigned by signal_compactor. Current thresholds (R:R≥3.0, Score≥70) are too restrictive. INJ passed detect() with R:R 6.96/Score 87 but the context was terrible (SHORTING at support, price acceleration against trade). NEO (+30.98% winner) had R:R 2.26/Score 65.25 — below thresholds, never had a chance to fire.

### Verified Numbers
- 24h: 25T, 56% WR, -$0.03 (flat)
- 7d: 334T, 56.6% WR, +$0.53 (profitable)
- rr-struct 7d: 12T, 75% WR, +$1.04 (strong — mostly signal_compactor assigned)
- NEO LONG: +30.98%, price_accel=+0.0062 (aligned), RSI=50.0, regime NEUTRAL
- INJ SHORT: -6.52%, price_accel=+0.0044 (against trade), RSI=40.43, regime NEUTRAL, bb_position=0.38 (mid-range, not at support)

### Decision: APPROVED (2 of 3 changes)

**Change 1 — APPROVED: Lower Detection Thresholds**
```
RR_STRUCTURAL_MIN_RR     = 2.0   (was 3.0)
RR_STRUCTURAL_MIN_SCORE  = 60    (was 70)
```
Rationale: Catches trades like NEO that have good structure but moderate R:R. System is at breakeven (56% WR, R:R 0.67) — need to increase signal volume from detect() without sacrificing quality. The existing RSI and regime filters already block bad entries.

**Change 2 — APPROVED: Price Acceleration Direction Filter**
- Block SHORT when price_acceleration > 0 (price going UP against SHORT)
- Block LONG when price_acceleration < 0 (price going DOWN against LONG)
- Computed from last 10 1m candle closes (roc check)
Rationale: Clean momentum filter. NEO had accel=+0.0062 aligned with LONG ✅. INJ had accel=+0.0044 against SHORT ❌. No counter-examples in the 12-trade sample. Simple, low-risk addition.

**Change 3 — REJECTED: Range Position Filter**
Rationale: Too brittle. "Bottom 20% of 1h range" is context-dependent — NEO was at 12% of range and WON (+30.98%). INJ was at 6.3% and LOST, but it lost because of price acceleration against the trade, not because of range position. The range filter would have blocked NEO too if we'd set it wrong. The price acceleration filter (Change 2) already covers the INJ case more reliably. Adding range position is redundant complexity.

### Implementation Directive
1. Apply Changes 1 and 2 to hermes_constants.py and rr_structural.py
2. Add `price_acceleration` filter in detect() — compute from candles_1m, block misaligned trades
3. Run in shadow mode (log signals without trading) for 48h before enabling live
4. Monitor: signal volume increase, false positive rate, WR of detect()-fired trades

### What Was Skipped
- Range position filter (Change 3) — redundant with accel filter, too many edge cases
- Regime-specific param tuning — not enough rr-struct trades per regime yet (12 total, all NEUTRAL)
- New signal development — system flat, legacy aging out, focus on structural fixes first

### Next Review
48h after shadow mode activation — check signal volume, WR, and whether accel filter blocked any good trades.
