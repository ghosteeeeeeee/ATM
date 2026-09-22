# Independent Audit — Pump-Chain V5 Continuum Evidence

**Auditor:** Independent subagent (no priming, fresh queries from PostgreSQL brain DB)
**Date:** 2026-09-22
**Source:** `public.trades` table, `_signal_metadata` JSONB column
**Filter:** `signal LIKE '%pump-chain%' AND direction = 'LONG' AND _signal_metadata IS NOT NULL`
**Sample:** 82 unique trades (confirmed via `COUNT(DISTINCT id)`)

---

## CLAIM 1: Wave Phase Performance

### Claimed Table vs Actual (verified via PostgreSQL)

| Phase | Claimed Trades | Actual | Claimed WR | Actual WR | Claimed PnL | Actual PnL |
|-------|---------------|--------|-----------|-----------|------------|------------|
| accelerating | 36 | 36 ✓ | 44.4% | 44.4% ✓ | +$47.97 | +47.97 ✓ |
| bottoming | 8 | 8 ✓ | 37.5% | 37.5% ✓ | -$12.50 | -12.50 ✓ |
| decelerating | 9 | 9 ✓ | 55.6% | 55.6% ✓ | +$6.34 | +6.34 ✓ |
| falling | 29 | 29 ✓ | 48.3% | 48.3% ✓ | +$21.37 | +21.37 ✓ |

**Note on PnL:** The "$" values in the claim are `SUM(pnl_pct)` (percentage points), NOT `SUM(pnl_usdt)` (actual dollars). Real USDT PnL sums: accelerating=$0.84, bottoming=-$0.46, decelerating=$0.14, falling=$0.27. The claim labels them as "$" which is misleading but the numbers are correct for pnl_pct.

### Verdict: AGREE
- All numbers match exactly
- "bottoming" IS the worst by WR (37.5%) among wave phases
- "bottoming" IS the only wave phase with negative total PnL (-12.50)
- Confidence: **HIGH**

---

## CLAIM 2: Momentum State Performance

### Claimed Table vs Actual

| State | Claimed Trades | Actual | Claimed WR | Actual WR | Claimed PnL | Actual PnL |
|-------|---------------|--------|-----------|-----------|------------|------------|
| rising | 65 | 65 ✓ | 49.2% | 49.2% ✓ | +$83.07 | +83.07 ✓ |
| flat | 11 | 11 ✓ | 27.3% | 27.3% ✓ | -$35.36 | -35.36 ✓ |
| falling | 6 | 6 ✓ | 50.0% | 50.0% ✓ | +$15.48 | +15.48 ✓ |

### Verdict: AGREE
- All numbers match exactly
- "flat" IS the worst by both WR (27.3%) and PnL (-35.36)
- Confidence: **HIGH**

---

## CLAIM 3: Momentum Score Performance

### Claimed Table vs Actual

| Range | Claimed Trades | Actual | Claimed WR | Actual WR | Claimed PnL | Actual PnL |
|-------|---------------|--------|-----------|-----------|------------|------------|
| 40-49 | 4 | 4 ✓ | 50.0% | 50.0% ✓ | +$6.57 | +6.57 ✓ |
| 30-39 | 26 | 26 ✓ | 46.2% | 46.2% ✓ | +$15.03 | +15.03 ✓ |
| 20-29 | 23 | 23 ✓ | 47.8% | 47.8% ✓ | +$80.60 | +80.60 ✓ |
| 10-19 | 21 | 21 ✓ | 52.4% | 52.4% ✓ | -$22.82 | -22.82 ✓ |
| 0-9 | 8 | 8 ✓ | 25.0% | 25.0% ✓ | -$16.18 | -16.18 ✓ |

### Verdict: PARTIAL
- All numbers match exactly ✓
- "No clear pattern" claim is **partially wrong**:
  - There IS a clear pattern at the low end: scores 0-9 and 10-19 BOTH have negative total PnL (-16.18 and -22.82)
  - The 0-9 range has terrible WR (25.0%) and negative PnL
  - The pattern is non-monotonic though: 10-19 has the HIGHEST WR (52.4%) but NEGATIVE total PnL, while 20-29 has the BEST total PnL (+80.60)
  - A more accurate statement would be: "Momentum scores below 20 are net losers, but the relationship is non-linear"
- Confidence: **HIGH** (numbers verified, interpretation disputed)

---

## FILTERING IMPACT ANALYSIS

### Removing "bottoming" wave phase:
| Metric | Baseline (82) | No bottoming (74) | Change |
|--------|--------------|-------------------|--------|
| Win Rate | 46.3% | 47.3% | +1.0pp |
| Total PnL (pnl_pct) | +63.19 | +75.69 | +19.8% |
| Avg PnL per trade | +0.77 | +1.02 | +32.5% |

### Removing "flat" momentum state:
| Metric | Baseline (82) | No flat (71) | Change |
|--------|--------------|--------------|--------|
| Win Rate | 46.3% | 49.3% | +3.0pp |
| Total PnL (pnl_pct) | +63.19 | +98.55 | +56.0% |
| Avg PnL per trade | +0.77 | +1.39 | +80.5% |

### Removing BOTH (bottoming AND flat):
| Metric | Baseline (82) | Filtered (64) | Change |
|--------|--------------|---------------|--------|
| Win Rate | 46.3% | 50.0% | +3.7pp |
| Total PnL (pnl_pct) | +63.19 | +106.05 | +67.8% |
| Avg PnL per trade | +0.77 | +1.66 | +115.6% |

### Overlap:
Only **1 trade** is both bottoming AND flat. The two filters are largely independent — their benefits stack almost additively.

---

## CROSS-TABULATION: wave_phase × momentum_state (sorted by PnL)

| wave_phase | momentum_state | Trades | WR | PnL (pnl_pct) |
|-----------|----------------|--------|-----|---------------|
| falling | flat | 5 | 20.0% | -21.74 |
| accelerating | flat | 4 | 25.0% | -14.07 |
| bottoming | falling | 3 | 0.0% | -10.82 |
| bottoming | flat | 1 | 0.0% | -5.00 |
| decelerating | rising | 8 | 50.0% | +0.89 |
| bottoming | rising | 4 | 75.0% | +3.32 |
| decelerating | flat | 1 | 100.0% | +5.45 |
| accelerating | falling | 2 | 100.0% | +12.80 |
| falling | falling | 1 | 100.0% | +13.49 |
| falling | rising | 23 | 52.2% | +29.62 |
| accelerating | rising | 30 | 43.3% | +49.24 |

**Key insight:** "flat" is bad regardless of wave_phase. "bottoming" is bad regardless of momentum_state (except when combined with rising — but only 4 trades, too small to trust).

---

## FINAL VERDICT SUMMARY

| Claim | Verdict | Confidence |
|-------|---------|------------|
| "bottoming wave phase is worst (37.5% WR, -$12.50)" | **AGREE** | HIGH |
| "flat momentum state is worst (27.3% WR, -$35.36)" | **AGREE** | HIGH |
| "No clear pattern in momentum_score" | **PARTIAL** | HIGH |
| "Filtering out bottoming+flat would improve performance" | **AGREE** (confirmed: +67.8% PnL improvement) | HIGH |

### Caveats:
1. **Sample size:** 82 trades is small. Removing 18 trades (22%) leaves only 64. Statistical significance is limited.
2. **PnL units:** The claim uses "$" to label pnl_pct sums, which are percentage points, not actual dollars. Real USDT PnL is ~60x smaller.
3. **Survivorship:** This is closed-trade analysis only. No consideration of what might have been different if those trades hadn't been placed.
4. **Non-monotonic momentum_score:** The claim oversimplifies by saying "no clear pattern" when scores < 20 consistently lose money.
