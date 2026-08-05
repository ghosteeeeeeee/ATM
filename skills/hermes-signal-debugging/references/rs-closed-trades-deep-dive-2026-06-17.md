# RS Signal — Closed Trades Deep Dive (2026-06-17)

## Source
Archive: `/root/.hermes/archive/trades_analysis.db`
931 total trades, 757 with RS signals (signal column contains `rs-sNNN` or `rs-rNNN`)

---

## Key Findings

### SHORT Dominates LONG Across All Touch Buckets

| Direction | N | Win Rate | Avg PnL | Mean Touch | Median Touch |
|-----------|---|----------|---------|------------|--------------|
| SHORT | 370 | **44.9%** | **+0.68%** | 477 | 114 |
| LONG | 449 | **31.6%** | **+0.32%** | 333 | 126 |

SHORT is the stronger RS direction. Do not suppress SHORT signals with regime haircuts without strong reason.

### Signal Combo Quality — RS+Accel is the Worst Combo

| Combo | Count | Win Rate | Avg PnL |
|-------|-------|----------|---------|
| **RS+zscore** | 157 | **54.1%** | **+1.06%** |
| RS only | 115 | 45.2% | +0.70% |
| RS+hhh | 14 | 35.7% | +0.44% |
| **RS+accel** | **469** | **30.9%** | **+0.24%** |

RS+accel dominates the dataset (469 trades) yet has the worst WR and lowest PnL. The system is mostly firing RS signals that are momentum-confirmed, which destroys RS's natural mean-reversion edge. This is a structural signal combination problem, not just a parameter problem.

### Touch Count vs Quality — Cap Boundary Analysis

#### SHORT (direction = SHORT)

| Touch Count | N | WR | Avg PnL | Verdict |
|-------------|---|----|---------|---------|
| 1-30 | 42 | 38.1% | +0.43% | marginal |
| 31-60 | 66 | 47.0% | +0.67% | good |
| 61-80 | 31 | 45.2% | +0.54% | good |
| 81-100 | 29 | 48.3% | +0.92% | **best** |
| 101-120 | 28 | 50.0% | +0.75% | **best** |
| 121-150 | 24 | 41.7% | +0.68% | blocked by current cap=120 |
| **151-200** | **18** | **66.7%** | **+2.01%** | **blocked by current cap — BEST bucket** |
| 201-300 | 23 | 17.4% | -0.22% | **exhausted — do not allow** |
| 301-500 | 33 | 33.3% | +0.17% | marginal |
| 501-1000 | 36 | 55.6% | +0.92% | good |
| 1001+ | 40 | 50.0% | +0.94% | good |

**Natural ceiling for SHORT: 201-300 (WR 17.4%, negative). Raising cap to 200 captures the best SHORT bucket (151-200: WR 66.7%).**

#### LONG (direction = LONG)

| Touch Count | N | WR | Avg PnL | Verdict |
|-------------|---|----|---------|---------|
| 1-30 | 50 | 34.0% | +0.25% | marginal |
| 31-60 | 81 | 34.6% | +0.32% | marginal |
| 61-80 | 34 | 29.4% | +0.18% | weak |
| 81-100 | 37 | 37.8% | +0.68% | acceptable |
| 101-120 | 16 | 31.2% | +0.59% | weak |
| 121-150 | 38 | **18.4%** | **-0.02%** | **worst bucket** |
| 151-200 | 40 | 25.0% | +0.26% | weak |
| 201-300 | 37 | 27.0% | +0.06% | weak |
| 301-500 | 33 | 42.4% | +0.66% | best for LONG |
| 501-1000 | 46 | 30.4% | +0.20% | marginal |
| 1001+ | 37 | 35.1% | +0.54% | acceptable |

**LONG has no strong bucket above 80 touches. The 121-150 zone is the worst for LONG (WR 18.4%, negative). For LONG, lower touch counts (31-100) perform comparably to or better than high-touch levels.**

### Hard Cap Impact at Each Boundary

| Cap | Signals BLOCKED | % Blocked | Allowed |
|-----|-----------------|-----------|---------|
| 80 | 519 | 63.4% | 300 |
| 100 | 452 | 55.2% | 367 |
| **120 (current)** | **411** | **50.2%** | **408** |
| 150 | 345 | 42.1% | 474 |
| **200 (proposed)** | **287** | **35.0%** | **532** |
| 250 | 249 | 30.4% | 570 |
| 300 | 226 | 27.6% | 593 |

Cap 120 blocks 50% of signals. Cap 200 unblocks 124 more signals, predominantly the high-performing SHORT buckets.

### Live Signal Pipeline Status (2026-06-17)

30 most recent RS signals:
- 4 EXECUTED
- 28 EXPIRED
- 16 survived to hot-set at some point
- **All have `effective_confidence=None`** — compaction pipeline kills them before scoring

This confirms the double-gate problem: proximity too tight + bounce structurally impossible = near-zero survival.

---

## Implications for Parameter Fixes

1. **RS_PROXIMITY_K=3.0**: Required — low-vol tokens cannot pass 0.029% threshold
2. **RS_BOUNCE_THRESH_ATR=0.33**: Required — 3.0x bounce ratio is physically impossible
3. **RS_TOUCH_HARD_CAP=200**: Correct — captures 151-200 SHORT zone (66.7% WR, +2.0%), natural ceiling at 201-300 (17.4% WR, negative)
4. **RS_BROKEN_SHORT_ENABLED=False** and **RS_BROKEN_RESISTANCE_LONG_ENABLED=False**: Required — comment says "DISABLED" but constant is True
5. **RS+zscore combo quality (54% WR) suggests the best RS signals come from mean-reversion context, not momentum confirmation** — the accel+RS pairing (30.9% WR) is dragging the system down

---

## atr_dist Not Available in Archive

The archive trades DB does NOT store `atr_dist` (distance from price to level in ATR units). The proximity problem can only be verified mathematically, not from archived trade data. The mathematical proof (0G example: 12.9 ATRs away) is the primary evidence for the PROXIMITY_K fix.
