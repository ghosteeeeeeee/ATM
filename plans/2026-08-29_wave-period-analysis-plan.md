# Wave Period Analysis — Plan & Next Steps

**Created:** 2026-08-29
**Status:** Phase 1 Complete (Discovery), Phase 2 Pending (Validation + Integration)
**Context:** ZRO choppy trades sparked investigation into wave periodicity

---

## What Was Done (Phase 1 — Discovery)

### Scripts Created
| Script | Purpose |
|--------|---------|
| `scripts/wave_period_detector.py` | Core wave period analysis — peaks/troughs, periodicity, frequency changes |
| `scripts/wave_trade_context.py` | Analyzes trades in context of wave patterns |
| `scripts/wave_classifier.py` | Multi-token wave pattern classification |
| `brain/wave_pattern_buckets.md` | Pattern bucket definitions and trading implications |
| `brain/wave_period_analysis_ZRO.md` | ZRO-specific analysis |

### Key Findings (CORRECTED after bug fix)

**Pattern Buckets (20 tokens):**

| Bucket | Count | Example Tokens | Dominant Period | Trading Style |
|--------|-------|----------------|-----------------|---------------|
| **MEDIUM_FREQ_TREND** | 19 | BTC, ETH, SOL, ZRO, TRUMP, ARB, etc. | 2-8h (67-84%) | Swing trade, trend-follow |
| **CHAOTIC** | 1 | WIF | No dominant period | Reduce exposure |

**Amplitude sub-buckets:**
- LOW_AMP (<1.5%): BTC, ETH
- MED_AMP (1.5-2.5%): SOL, LINK, HYPE, DOGE, AAVE, ONDO, POPCAT, KAS, XRP
- HIGH_AMP (>2.5%): ARB, ZRO, TRUMP, SUI, WLD, TURBO, SPX, FET

**ZRO classification:** MEDIUM_FREQ_TREND with HIGH_AMP (4.28%). Not high-frequency noise — wide swings with medium-frequency structure.

---

## Uncertain Decisions (from /decisions)

These choices need validation before integration:

| # | Decision | Current Value | Alternative | Status |
|---|----------|---------------|-------------|--------|
| 1 | Extrema detection window | `window=3` | 2, 4, 5 | ⚠️ Partially validated — BTC flips to CHAOTIC at window=5 |
| 2 | Period bucket boundaries | 1h, 2h, 4h, 8h, 16h | Custom cutoffs | ✅ Validated — 2-8h captures 67-84% for most tokens |
| 3 | Pattern classification threshold | >60% dominance | 50%, 70% | ✅ Validated — 60% threshold correctly separates MEDIUM_FREQ |
| 4 | Analysis lookback | 720 candles (30 days) | 1460 (60d), 2190 (90d) | ⚠️ Needs validation — data gaps distort CV |
| 5 | Price type for extrema | Close prices only | High/Low/Typical | ⚠️ Needs validation — flat close prices caused bug |
| 6 | Amplitude thresholds | LOW <1.5%, MED 1.5-2.5%, HIGH >2.5% | Backtest-derived | ✅ Validated — separates BTC/ETH from ZRO/TRUMP clearly |
| 7 | Single timeframe | 1h only | Multi-timeframe (15m + 1h + 4h) | ⚠️ Needs validation — see Step 2 |

---

## Phase 2 — Validation (In Progress)

### Step 1: Validate Window Size ✅ Partially Done
Window=3 works for most tokens. BTC becomes CHAOTIC at window=5 (too strict). WIF is CHAOTIC regardless.

**Conclusion:** window=3 is reasonable. Not a critical variable.

### Step 2: Multi-Timeframe Classification ⏳ Next
Test ZRO, BTC, LINK on 15m, 1h, 4h — check if bucket changes.

### Step 3: Backtest Wave Strategies Per Bucket ⏳ Pending
Since we now have 2 buckets (MEDIUM_FREQ + CHAOTIC), test:

| Bucket | Strategy to Test | Success Metric |
|--------|------------------|----------------|
| MEDIUM_FREQ_TREND | accel-300-v2 (current) | Win rate >55%, Sharpe >1.0 |
| MEDIUM_FREQ + HIGH_AMP | Wider stops (3-5%) | Win rate >50% with wider SL |
| CHAOTIC | Reduced size, wider stops | Profitable or at least breakeven |

### Step 4: Frequency Change as Signal ⏳ Pending
Test if detecting wave frequency acceleration/deceleration predicts breakouts.

- When frequency accelerates >20%: expect breakout
- When frequency decelerates >20%: expect reversal or consolidation

### Step 5: Amplitude-Based Position Sizing ⏳ Pending
Since amplitude is the key differentiator (not frequency), test:
- LOW_AMP tokens: Standard size, tight stops
- MED_AMP tokens: Standard size, standard stops
- HIGH_AMP tokens: 75% size, wider stops

---

## Phase 3 — Integration

### Step 1: Amplitude-Based Hotset Filter
**Goal:** Auto-adjust position sizing and stops based on amplitude class.

```
LOW_AMP  (<1.5%)  → Standard size, 1-2% SL
MED_AMP  (1.5-2.5%) → Standard size, 2-3% SL
HIGH_AMP (>2.5%)  → 75% size, 3-5% SL
CHAOTIC            → 50% size, 5%+ SL
```

### Step 2: Signal Confidence Modifier
**Goal:** Adjust signal confidence based on amplitude class.

HIGH_AMP tokens get more volatile swings — reduce confidence by 10-15% to account for wider stop runs.

```python
AMPLITUDE_CONFIDENCE_MODIFIER = {
    'LOW_AMP': 1.0,    # No change
    'MED_AMP': 0.95,   # 5% reduction
    'HIGH_AMP': 0.85,  # 15% reduction
    'CHAOTIC': 0.70,   # 30% reduction
}
```

### Step 3: Dashboard Integration
**Goal:** Show amplitude class on coin tracker.

Add amplitude badge to each token:
- 🟢 LOW_AMP (stable, tight stops)
- 🟡 MED_AMP (standard)
- 🔴 HIGH_AMP (volatile, wider stops)
- ⚫ CHAOTIC (avoid or discretionary only)

---

## Phase 4 — Refinement

### Step 1: Empirical Threshold Calibration
Use backtest results to optimize:
- Window size
- Bucket boundaries
- Amplitude thresholds
- Pattern classification percentages

### Step 2: Adaptive Classification
Token patterns change over time. Build system that:
1. Re-classifies tokens weekly
2. Detects pattern transitions
3. Adjusts strategy accordingly

### Step 3: Multi-Token Wave Correlation
Check if wave patterns correlate across tokens (e.g., when BTC and ETH are both MEDIUM_FREQ, does that improve altcoin signals?).

---

## File Inventory

| File | Status | Notes |
|------|--------|-------|
| `scripts/wave_period_detector.py` | ✅ Created | Core analysis tool |
| `scripts/wave_trade_context.py` | ✅ Created | Trade context analyzer |
| `scripts/wave_classifier.py` | ✅ Created | Multi-token classifier |
| `brain/wave_pattern_buckets.md` | ✅ Created | Pattern documentation |
| `brain/wave_period_analysis_ZRO.md` | ✅ Created | ZRO analysis |
| `plans/2026-08-29_wave-period-analysis-plan.md` | ✅ Created | This plan |
| `scripts/wave_backtest.py` | ✅ Existed | MACD-based backtester (already in codebase) |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-29 | Use close prices for extrema | Simplicity first, can add H/L later |
| 2026-08-29 | Window=3 as default | Balances sensitivity vs noise rejection |
| 2026-08-29 | 5 pattern buckets | Enough granularity without overfitting |
| 2026-08-29 | 720 candle lookback | 30 days足够看到patterns, avoid stale data |

---

## Open Questions

1. **Should wave pattern override signal confidence?** If ZRO is HIGH_FREQ, should accel-300-v2 confidence be automatically reduced?
2. **How often should tokens be re-classified?** Weekly? Daily? On significant price structure change?
3. **Can we detect pattern transitions in real-time?** If ZRO shifts from HIGH_FREQ to MEDIUM_FREQ, should we immediately start trading it differently?
4. **Does wave pattern predict regime changes?** Does HIGH_FREQ→MEDIUM_FREQ transition signal a trend is forming?

---

## Next Actions

- [ ] Run window size validation (Step 1)
- [ ] Run multi-timeframe classification (Step 2)
- [ ] Backtest MEDIUM_FREQ tokens with accel-300-v2
- [ ] Backtest HIGH_FREQ tokens with mean-reversion
- [ ] Run own-conclusions skill on this plan
