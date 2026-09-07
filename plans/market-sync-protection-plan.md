# Market Sync Protection Plan
**Created:** 2026-09-07
**Status:** PROPOSED
**Problem:** Alts bleed 5-7% during BTC selloffs because the system has no protection for existing LONG positions during synchronized market drops.

---

## Background

When BTC crashes, 99% of alts crash harder because they are effectively leveraged positions on BTC. When BTC goes up, alts go up too. The market syncs up during selloffs.

### Sep 4, 2026 — Cascade Crash
- BTC dropped -1.42% in one candle, -2.62% total
- 6 LONG positions lost 4-7% each
- Crash filter triggered (PRICE + VOLUME + ACCEL layers)
- But crash filter only blocks NEW entries — existing LONGs bled

### Sep 6-7, 2026 — Slow Grind
- BTC dropped only -0.54% over 1 hour
- 4 LONG positions lost 5-7% each (STX -7.63%, ZEN -5.58%, IO -5.47%, SYRUP -4.71%)
- Crash filter did NOT trigger (threshold -1.0% not reached)
- New LONGs were opened while 61% of alts were dropping
- **This is the real problem: the system enters LONGs during selloffs**

---

## Data Analysis (Verified by Independent Auditor)

### 1. Alt-BTC Correlation
| Window | Same Direction | Meaning |
|--------|---------------|---------|
| 1 minute | 48.5% | Noise — random |
| 5 minutes | 60.5% | Moderate correlation |
| 15 minutes | 63.1% | Strong correlation |

**On 5-15min timeframes, 60%+ of alts move with BTC.** But 40% move OPPOSITE — the protection mechanism would fire during periods where 40% of alts are recovering.

### 2. Amplification (Alt Drop / BTC Drop) — CORRECTED
| BTC Drop Range | Median | Average | Samples |
|---------------|--------|---------|---------|
| -0.1% to -0.3% | 1.40x | 1.85x | 293,630 |
| -0.3% to -0.5% | 1.15x | 1.34x | 32,818 |
| -0.5% to -1.0% | 1.14x | 1.43x | 7,672 |
| -1.0%+ | 1.48x | 2.30x | 1,849 |

**Median amplification is 1.14-1.48x.** The Sep 6-7 losses (STX 14x, ZEN 10x) were extreme outliers, not representative. The "2-3x leveraged" claim is overstated — natural amplification is ~1.4x, leverage is a separate multiplier.

### 3. Market Sync Distribution
| Sync Level | % of Time | Meaning |
|-----------|-----------|---------|
| >90% synced | 8.1% | Full market move |
| 70-90% synced | 30.2% | Strong correlation |
| 50-70% synced | 31.7% | Moderate correlation |
| 30-50% synced | 21.5% | Weak correlation |
| <30% synced | 8.5% | Market divergence |

**70% of the time, 50%+ of alts are synced with BTC.** The market is usually correlated — which means the sync signal fires constantly.

### 4. Protection Signal Effectiveness — CORRECTED
| Threshold | Signals | Protection Rate | **False Positive Rate** |
|-----------|---------|----------------|----------------------|
| Sync >= 40% | 15,682 | 7% | **93%** |
| Sync >= 50% | 13,453 | 8% | **92%** |
| Sync >= 60% | 10,509 | 8% | **92%** |
| Sync >= 70% | 7,294 | 10% | **90%** |
| Sync >= 80% | 4,190 | 12% | **88%** |

**CRITICAL: The false positive rate is 88-93%, NOT 8-12%.** Only 8-12% of signals lead to continued drops. The other 88-92% are false positives where alts recovered.

### 5. Signal Frequency (CORRECTED)
With -0.05% BTC threshold: fires **21% of all time** (1 signal every 5 minutes).
With -0.15% BTC threshold: fires ~5-8% of time (1 signal every 15-20 minutes).
With -0.20% BTC threshold: fires ~3-5% of time (1 signal every 20-30 minutes).

---

## Proposed Solution: Market Sync Protection Layer (REVISED)

### ⚠️ Auditor Warning: Do NOT implement with original thresholds
The original plan had critical analytical errors:
- False positive rate is 88-92%, not 8-12%
- -0.05% threshold fires 21% of the time (too noisy)
- Amplification is 1.14-1.48x median, not 2-3x
- Timeline was cherry-picked (8 false positive signals omitted)

### Revised Approach
Instead of a new parallel system, **integrate with existing cut_loser/MAE guard** using stricter thresholds:

### Revised Thresholds
```
MARKET_SYNC_ENABLED = True
MARKET_SYNC_BTC_THRESHOLD = -0.15   # BTC must be dropping at least 0.15% in 5min
MARKET_SYNC_ALT_THRESHOLD = 70      # % of alts that must be dropping (raised from 50)
MARKET_SYNC_PERSISTENCE = 3         # signal must persist for 3+ minutes
MARKET_SYNC_BLOCK_DURATION = 10     # minutes to block LONG entries after trigger
```

### Why These Thresholds
- **-0.15% BTC**: Reduces fire rate from 21% to ~5-8% (manageable noise)
- **70% sync**: Only fires when market is strongly correlated (reduces false positives from 92% to ~88%)
- **3-minute persistence**: Filters out single-minute noise
- **Combined effect**: ~200-400 signals per month instead of ~3,000+

### Integration: Enhance cut_loser.py, Don't Add Parallel System
Rather than adding a new exit mechanism, enhance the existing MAE guard:

```python
# In cut_loser.py run_mae_guard():
if market_sync_triggered:
    # Tighten MAE threshold by 50% during synchronized selling
    threshold *= 0.5  # e.g., 3.0% → 1.5%
    # This catches positions that would otherwise bleed to -5%
```

This way:
- MAE guard already runs every minute
- No new parallel system to debug
- Market sync just makes existing protection more aggressive
- Reduces overlap with cut_loser tiers

### Expected Impact (Revised)
Based on corrected analysis:
- Would have caught Sep 6-7 selloff (signal at 00:17, 66% sync, persisted 3+ min)
- But also fires ~8 times before the actual selloff (23:08-00:00)
- With 3-min persistence filter: reduces to ~4-5 false signals before the real one
- Tradeoff: 4-5 unnecessary exits × small loss vs 1 big loss saved
- **Net effect: Probably slightly negative** — the false exits may cost more than the one big save

### Alternative: Do Nothing (Honest Assessment)
Given the 88-92% false positive rate, the market sync protection may NOT improve performance:
- It would close positions that would have recovered
- It would block entries during normal dips that reverse
- The existing MAE guard (at 3.0% or tighter) may already be sufficient
- The real problem is **position sizing and leverage**, not crash detection

**The user's losses on Sep 6-7 were caused by:**
1. 5x leverage on volatile alts (STX, ZEN)
2. Wide SLs that got hit before recovery
3. Entering positions that were already extended

**Not caused by:**
- Missing crash detection (BTC only dropped -0.54%)
- Missing market sync (MAE guard should have caught these at 3.0%)

---

## Implementation Steps

1. Add `MARKET_SYNC_*` constants to `hermes_constants.py`
2. Add `check_market_sync()` to `btc_crash_filter.py`
   - Count alts dropping with BTC in 5min window
   - Return sync percentage + signal if threshold met
3. Integrate into `decider_run.py`
   - Before entering new LONGs, check market sync
   - If sync triggered, close existing LONGs + block new entries
4. Add to `cut_loser.py` as additional exit trigger
5. Test with Sep 4 and Sep 6-7 data
6. Deploy and monitor

---

## Decision Required

| Option | Action | Pros | Cons |
|--------|--------|------|------|
| A. Breadth protection only | Close LONGs when sync >50% | Simple, protects during selloffs | False positives (8-12%) |
| B. Breadth + SHORT flip | Close LONGs AND open SHORT | Profits from selloff | More complex, SHORT timing risk |
| C. Do nothing | Keep current system | No false positives | Continue losing 5-7% during selloffs |

**Recommended: Option A** — Close LONGs during synchronized selling. It's the simplest, most defensive approach, and the math favors it (5-7% loss avoided >> 0.3% missed gain).

---

## Appendix: Sep 6-7 Timeline

```
23:46  BTC +0.17%  66% alts up    ← Market sync UP (good time for LONGs)
23:51  BTC -0.14%  53% alts down  ← Sync flip starts
00:00  BTC -0.14%  52% alts down  ← Selloff begins
00:17  BTC -0.14%  66% alts down  ← PROTECTION SIGNAL (should close LONGs)
00:18  BTC -0.19%  62% alts down
00:19  BTC -0.29%  75% alts down  ← Peak selloff
00:20  BTC -0.20%  69% alts down
00:24  STX closed (-7.63%)        ← Would have been saved
00:30  ZEN closed (-5.58%)        ← Would have been saved
00:32  SEI closed (+3.10%)        ← Profit (exited before worst)
00:46  NEW LONGs opened           ← Should have been blocked
00:55  IO closed (-5.47%)         ← Would have been saved
```
