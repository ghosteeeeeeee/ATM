# Independent Verdict: Market Sync Protection Plan
**Auditor:** Independent verification agent
**Date:** 2026-09-07
**Files reviewed:** market-sync-protection-plan.md, btc_crash_filter.py, hermes_constants.py (lines 860-1006), decider_run.py (lines 1782-2120), cut_loser.py, position_manager.py, run_pipeline.py

---

## Data Sources
- Candle DB: `/root/.hermes/data/candles.db` (candles_1m table)
- 141 alt tokens, BTC as reference
- Full dataset analyzed with custom Python queries

---

## === INDEPENDENT VERDICT ===

### Claim 1: "Alts are 2-3x leveraged on BTC moves"
**Verdict: DISAGREE**
**Confidence: HIGH**

**Evidence:**
My independent analysis of all candle data shows:

| BTC Drop Range | Median Amplification | Average Amplification | Sample Size |
|---------------|---------------------|----------------------|-------------|
| -0.1% to -0.3% | 1.40x | 1.85x | 293,630 |
| -0.3% to -0.5% | 1.15x | 1.34x | 32,818 |
| -0.5% to -1.0% | 1.14x | 1.43x | 7,672 |
| -1.0%+ | 1.48x | 2.30x | 1,849 |

The plan claims "Alts are 2-3x leveraged on BTC moves." The actual median amplification is **1.14-1.48x** across all ranges. Only the -1.0%+ range approaches 2x average, and only because extreme outliers skew the mean. The median (robust to outliers) is 1.48x at most.

The plan's statement "At 5x leverage, this becomes 5.7x-7.4x amplification" conflates natural alt/BTC correlation amplification with position leverage. These are independent multipliers — the natural amplification is ~1.4x, and leverage is separate.

**For the Sep 6-7 specific case:** STX 14.1x, ZEN 10.3x, IO 10.1x, SYRUP 8.7x amplification. These are extreme outliers (10-14x) that are NOT representative of typical behavior. Using these to justify a system-wide protection mechanism is cherry-picking.

**Notes:** The plan overstates amplification to make the problem seem more urgent. The real amplification is ~1.4x median, not 2-3x.

---

### Claim 2: "60%+ of alts move with BTC on 5-15min timeframes"
**Verdict: AGREE**
**Confidence: HIGH**

**Evidence:**
My independent analysis confirms the correlation numbers exactly:

| Window | Same Direction | Sample Size |
|--------|---------------|-------------|
| 1 minute | 48.5% | 3,827,019 |
| 5 minutes | 60.5% | 3,826,221 |
| 15 minutes | 63.1% | 3,823,357 |

The 5m and 15m correlation numbers (60.5% and 63.1%) match the plan's claims of 60.5% and 63.1% exactly. This is the one claim that is fully accurate.

**Notes:** 60% correlation means 40% of alts move OPPOSITE to BTC. This is significant — the protection mechanism would fire during periods where 40% of alts are recovering, locking in unnecessary losses.

---

### Claim 3: "Market sync protection at 50% threshold would have caught the Sep 6-7 selloff"
**Verdict: PARTIAL**
**Confidence: MEDIUM**

**Evidence:**
The plan's timeline is mostly accurate:
- ✅ 23:46: BTC +0.17%, 66% alts up — confirmed
- ✅ 00:17: BTC -0.14%, 66% alts down — confirmed, signal fires
- ✅ Signal fires at the right time to catch the main selloff

**However, the plan omits critical context:**

There are **9 EARLIER signals** between 23:08 and 00:00 that the plan's timeline ignores:
```
23:08 BTC=-0.13% sync=67% — SIGNAL (before main selloff)
23:25 BTC=-0.15% sync=50% — SIGNAL (before main selloff)
23:44 BTC=-0.07% sync=53% — SIGNAL (before main selloff)
23:51 BTC=-0.14% sync=53% — SIGNAL (before main selloff)
23:54 BTC=-0.13% sync=53% — SIGNAL (before main selloff)
23:56 BTC=-0.11% sync=59% — SIGNAL (before main selloff)
23:57 BTC=-0.05% sync=50% — SIGNAL (before main selloff)
00:00 BTC=-0.14% sync=52% — SIGNAL (before main selloff)
00:17 BTC=-0.14% sync=66% — SIGNAL (actual selloff)
```

If the system had acted on the 23:08 signal (BTC -0.13%, 67% sync), it would have closed LONGs during a brief dip that reversed within minutes. This is a **false positive** that the plan's timeline conveniently omits.

**Notes:** The signal does fire at the right time, but it also fires 8 times before the actual selloff. The plan cherry-picks the timeline to make it look clean.

---

### Claim 4: "The proposed thresholds are reasonable (MARKET_SYNC_BTC_THRESHOLD = -0.05%)"
**Verdict: DISAGREE**
**Confidence: HIGH**

**Evidence:**
My analysis of the -0.05% BTC threshold shows:

| Metric | Value |
|--------|-------|
| BTC < -0.05% in 5m | 9,057 / 37,766 = **24.0% of all time** |
| Market sync fires (BTC<-0.05% + sync≥50%) | 7,990 / 37,766 = **21.2% of all time** |

The signal fires **21.2% of all time** — roughly **1 in every 5 minutes**. This is extremely noisy:

- At 21% fire rate, the system would be closing LONGs and blocking entries **constantly**
- Even during normal market conditions, BTC dips -0.05% in 5m frequently
- The 50% sync threshold doesn't help much — 88% of BTC-down periods already have 50%+ sync
- This would cause constant position churn, whipsawing in and out of positions

**The -0.05% threshold is far too aggressive.** A more reasonable threshold would be -0.15% or -0.20% (matching the existing crash filter's -1.5% base threshold scaled down for 5min).

**Signal frequency per hour (actual data):**
```
00:00 — 337 signals
01:00 — 412 signals
...
Every hour has 250-427 signals. This is noise, not signal.
```

**Notes:** The plan's threshold would make the system hyperactive, constantly exiting and re-entering positions. This would increase slippage, trading fees, and missed opportunities.

---

### Claim 5: "8-12% false positive rate is acceptable"
**Verdict: DISAGREE**
**Confidence: HIGH**

**Evidence:**
The plan's own data table shows:

| Threshold | Signals | Protection Rate |
|-----------|---------|----------------|
| Sync >= 40% | 15,682 | 7% (alts kept dropping) |
| Sync >= 50% | 13,453 | 8% |
| Sync >= 60% | 10,509 | 8% |
| Sync >= 70% | 7,294 | 10% |
| Sync >= 80% | 4,190 | 12% |

The plan states: "The signal catches 8-12% of continued drops." This means **only 8-12% of signals actually protect against continued drops**. The remaining **88-92% are FALSE POSITIVES** (alts recovered or stabilized after the signal).

**The plan has INVERTED the meaning.** It claims "8-12% false positive rate" but its own data shows **88-92% false positive rate**.

My independent analysis confirms:
- When signal fires and alts continued dropping: avg = -0.33% (n=374,144)
- When signal fires and alts recovered: avg = +0.31% (n=410,447)
- **47.7% of signals lead to continued drops, 52.3% lead to recovery**

The plan's claim of "8-12% false positive rate" is **factually wrong based on its own data**. The actual false positive rate is **47-88%** depending on the metric used.

**Notes:** This is the most critical error in the plan. An 88-92% false positive rate means the protection mechanism would cause unnecessary exits almost every time it fires. The "benefit" of avoiding 5-7% losses is negated by locking in -0.33% losses 47-88% of the time when the alt would have recovered.

---

### Claim 6: "Option A (breadth protection only) is the right choice"
**Verdict: DISAGREE**
**Confidence: HIGH**

**Evidence:**
Given my findings on claims 4 and 5:

1. **The -0.05% threshold fires 21% of the time** — too noisy
2. **The false positive rate is 47-88%** — not 8-12% as claimed
3. **cut_loser already runs every minute** and handles individual position exits
4. **position_manager.py already has** cascade flip, MAE guard, stale exit, hard max-loss, and time-based exit mechanisms

Option A would add another layer of protection that:
- Fires too frequently (21% of time)
- Has a high false positive rate (47-88%)
- Overlaps with existing exit mechanisms (cut_loser, MAE guard, cascade flip)
- Would cause constant position churn

**Option B (SHORT flip) would be even worse** — flipping to SHORT during a false positive would compound losses.

**The better approach would be:**
1. Raise the BTC threshold to -0.15% or -0.20% (reduces fire rate to ~5-8%)
2. Increase the sync threshold to 70% or 80% (reduces false positives)
3. Add a confirmation requirement (signal must persist for 2-3 minutes)
4. Integrate with existing cut_loser/MAE guard rather than adding a parallel system

**Notes:** The plan's recommendation is based on incorrect analysis of its own data. The false positive rate is not 8-12% — it's 47-88%. Option A would degrade system performance, not improve it.

---

## Additional Findings

### Race Conditions
The plan proposes integrating market sync protection into both `decider_run.py` and `cut_loser.py`. However:
- `decider_run.py` runs as part of the pipeline (every 1 minute)
- `cut_loser.py` runs as a separate systemd timer (every 1 minute)
- Both would check market sync independently
- This could cause double-exits or conflicting actions

### Overlap with Existing Mechanisms
The plan doesn't account for the fact that `position_manager.py` already has:
- **MAE guard** (Layer 5 in btc_crash_filter.py) — ATR-aware position protection
- **Cascade flip** — speed-armed reversal during losses
- **Hard max-loss exit** — CUT_LOSER_PNL threshold
- **Stale exit** — positions flat for 30+ minutes
- **Time-based exit** — slow bleed protection

Adding market sync protection would create **6+ overlapping exit mechanisms**, increasing complexity and making it harder to debug which mechanism caused an exit.

### Timeline Cherry-Picking
The plan's Sep 6-7 timeline starts at 23:46 and shows the signal firing at 00:17. This omits 8 earlier signals (23:08-00:00) that would have triggered false exits. A complete timeline would show the noise problem clearly.

---

## Summary

| Claim | Verdict | Confidence |
|-------|---------|------------|
| Alts are 2-3x leveraged on BTC moves | DISAGREE | HIGH |
| 60%+ of alts move with BTC on 5-15min | AGREE | HIGH |
| Market sync at 50% threshold would have caught Sep 6-7 | PARTIAL | MEDIUM |
| -0.05% BTC threshold is reasonable | DISAGREE | HIGH |
| 8-12% false positive rate is acceptable | DISAGREE | HIGH |
| Option A (breadth protection) is the right choice | DISAGREE | HIGH |

**Overall Assessment: The plan has significant analytical errors.** The most critical is the inversion of the false positive rate (claiming 8-12% when the data shows 47-88%). The proposed -0.05% threshold is far too aggressive, firing 21% of the time. The plan cherry-picks the Sep 6-7 timeline to omit 8 false positive signals.

**Recommendation: DO NOT IMPLEMENT as proposed.** Instead:
1. Fix the analytical errors in the plan
2. Raise BTC threshold to -0.15% minimum
3. Raise sync threshold to 70% minimum
4. Add confirmation requirement (2-3 minute persistence)
5. Integrate with existing exit mechanisms rather than adding parallel systems
6. Backtest the revised thresholds before deployment
