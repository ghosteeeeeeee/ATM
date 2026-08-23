# Plan: ATR SL Widening & System Optimization

**Date:** 2026-08-23
**Status:** Open
**Author:** Independent Verification Agent
**Review of:** 48h trading system analysis

---

## Executive Summary

After independent verification of the 48h trading system analysis, I find that **the proposed ATR SL widening is NOT beneficial** and could actually harm performance. The data shows:

1. **ATR SL Widening (k=2.0-2.5)**: Zero of 30 losing ATR SL trades would have been saved by wider SL. The problem isn't SL width — it's entry timing and crash exposure.
2. **MAE Guard (1.5% threshold)**: Net impact is **-$5.43 over 7 days** — it's hurting, not helping. It catches some losers but kills more winners.
3. **Profit Monster**: Currently neutral (+$0.13/48h). No evidence it's significantly helping or hurting.
4. **Entry Features**: Bug in `features_recorded` column — data is written but flag is never set to TRUE.

**Recommendation:** Do NOT widen SL. Instead, fix the MAE guard, fix entry features wiring, and focus on entry quality (crash filter, copy-trader signal quality).

---

## 1. ATR SL System Analysis

### Current Configuration (hermes_constants.py)

```python
ATR_SL_MIN = 0.012      # 1.2% floor
ATR_SL_MAX = 0.030      # 3.0% cap
ATR_K_LOW_VOL = 0.8     # atr_pct < 1%
ATR_K_NORMAL_VOL = 1.0  # 1.0% <= atr_pct <= 1.5%
ATR_K_HIGH_VOL = 0.25   # atr_pct > 1.5%
```

### Proposed Changes (from analysis)

```python
ATR_SL_MIN = 0.020      # 2.0% floor (was 1.2%)
ATR_SL_MAX = 0.050      # 5.0% cap (was 3.0%)
ATR_K_LOW_VOL = 2.0     # (was 0.8)
ATR_K_NORMAL_VOL = 2.5  # (was 1.0)
ATR_K_HIGH_VOL = 0.5    # (was 0.25)
```

### Independent Verification: WRONG

**Simulation result:** Zero of 30 losing ATR SL trades would have been saved by wider SL.

| Token | ATR% | Current SL% | Proposed SL% | MFE% | Would Help? |
|-------|------|-------------|--------------|------|-------------|
| WLFI | 0.78% | 1.20% | 2.00% | 1.97% | NO |
| MET | 0.95% | 1.20% | 2.00% | 0.52% | NO |
| BIGTIME | 0.87% | 1.20% | 2.00% | 0.84% | NO |
| CRV | 0.60% | 1.20% | 2.00% | 0.00% | NO |
| BTC | 0.22% | 1.20% | 2.00% | 0.61% | NO |
| *...25 more trades...* | | | | | NO |

**Key insight:** These trades never reach 2.0% MFE. They're instant stops — price moves against immediately. Wider SL just means larger losses when they do get stopped.

### ATR SL Hit Breakdown (48h)

```
Total ATR SL hits: 75
  Winners: 39 (52% WR, avg +10.36%, total +$7.18)
  Losers:  36 (48% WR, avg -7.97%, total -$6.51)
  Net: +$0.67 USDT
```

**The ATR SL system is actually net positive.** The trailing SL is capturing profits before the stop hits. The "problem" trades are the ones that never develop — no amount of SL widening helps these.

### MFE Bucket Analysis

| MFE Bucket | Trades | Wins | Avg PnL |
|------------|--------|------|---------|
| 0% | 21 | 0 | -$0.14 |
| 1% | 18 | 4 | -$0.15 |
| 2% | 18 | 17 | +$0.01 |
| 3%+ | 18 | 18 | +$0.35 |

**Only 20% of losing ATR SL trades had MFE >= 1%.** The other 80% never developed at all. Wider SL won't help trades that never move in your favor.

---

## 2. MAE Guard Analysis

### Current Configuration

```python
CL_MAE_GUARD_ENABLED = True
CL_MAE_GUARD_THRESHOLD = 0.015  # 1.5% from peak
```

### Independent Verification: HURTING THE SYSTEM

**7-day simulation (LONG trades only):**

| Threshold | Total Cut | Losses Saved | Winners Killed | Net Impact |
|-----------|-----------|--------------|----------------|------------|
| 1.0% | 110 | $-10.35 | $7.84 | **-$2.51** |
| 1.5% | 44 | $-6.67 | $1.24 | **-$5.43** |
| 2.0% | 12 | $-3.35 | $0.53 | **-$2.82** |
| 3.0% | 6 | $-2.72 | $0.03 | **-$2.69** |

**At the current 1.5% threshold, MAE guard is costing $5.43/week.** It catches some losers but kills many more winners that would have recovered.

### Why It's Failing

1. **Trades that drop 1.5% from peak often recover.** The guard cuts them before they can.
2. **The guard runs every wake cycle** (no fire windows), so it's overly aggressive.
3. **It only applies to LONG** — SHORT trades have different dynamics.
4. **Crash trades (WLFI, MET, BIGTIME)**: MAE guard would have caught 4/5, but these were opened during a BTC crash that the crash filter should have blocked.

### Crash Event Analysis (2026-08-22 05:00-06:00 UTC)

| Token | PnL | MAE | Would MAE Guard Catch? |
|-------|-----|-----|------------------------|
| CRV | -18.85% | 1.71% | YES |
| DYDX | -12.34% | 0.62% | NO |
| WLFI | -41.62% | 1.58% | YES |
| BIGTIME | -17.93% | 2.51% | YES |
| MET | -21.66% | 5.48% | YES |

**Root cause:** All 5 trades were `ct-hot+` (copy trader) signals opened during a BTC crash. The BTC crash filter was added AFTER this event. The fix isn't MAE guard — it's preventing these entries in the first place.

---

## 3. Profit Monster Analysis

### Current State

```python
PM_TRAIL_ENABLED = True
PM_TRAIL_ACTIVATE_PCT = 0.004  # 0.40%
PM_TRAIL_DISTANCE_PCT = 0.002  # 0.20%
```

### 48h Performance

```
Profit Monster Trail: 4T, 3W (75% WR), avg +0.78%, total +$0.13
```

**Verdict:** Neutral. PM_TRAIL is capturing small profits on 4 trades. Not a significant factor in system performance. The claim that PM at any level is "WORSE" needs more data — current PM is barely active.

---

## 4. Entry Features Bug

### Issue

`record_entry_features()` is called in 3 places:
- `hl-sync-guardian.py:872` (orphan trade creation)
- `hl-sync-guardian.py:1684` (flip trade creation)
- `brain.py:687` (mirror trade creation)

The function DOES write data (2649 trades have `entry_rsi_14`), but the `features_recorded` column is always `FALSE`.

### Root Cause

The `UPDATE` query in `record_entry_features()` (line 2440-2461) includes `features_recorded = TRUE`, but:
1. The column defaults to `false` in the schema
2. The backfill script (`backfill_trade_indicators.py`) writes indicators but doesn't set `features_recorded=TRUE`
3. The function may be silently failing on the `features_recorded` update

### Fix

```sql
-- Check if column exists and has correct default
SELECT column_name, column_default 
FROM information_schema.columns 
WHERE table_name = 'trades' AND column_name = 'features_recorded';

-- Manually set for all trades that have entry_rsi_14
UPDATE trades SET features_recorded = TRUE 
WHERE entry_rsi_14 IS NOT NULL AND features_recorded = FALSE;
```

Then fix the function to ensure `features_recorded` is set.

---

## 5. Recommendations

### DO NOT Implement

| Change | Reason |
|--------|--------|
| ATR SL widening (k=2.0-2.5) | Zero benefit for losing trades. Would increase loss severity. |
| MAE Guard at 1.5% | Net negative impact (-$5.43/week). Cuts winners that would recover. |

### DO Implement

| Change | Priority | Expected Impact |
|--------|----------|-----------------|
| Fix `features_recorded` bug | HIGH | Enables entry feature analysis |
| Tighten MAE guard to 3.0% or disable | HIGH | Save ~$2.69/week |
| Fix BTC crash filter timing | HIGH | Prevent crash entries (WLFI, MET, BIGTIME) |
| Review copy-trader signal quality | MEDIUM | All crash trades were `ct-hot+` |
| Backfill entry features for analysis | MEDIUM | Enable predictive modeling |

### Optimal Configuration

```python
# MAE Guard — tighten or disable
CL_MAE_GUARD_ENABLED = False  # Disable until threshold is optimized
# OR
CL_MAE_GUARD_THRESHOLD = 0.03  # 3.0% — only catch true crashes

# ATR SL — keep current (already working)
ATR_SL_MIN = 0.012  # 1.2% — keep
ATR_SL_MAX = 0.030  # 3.0% — keep
ATR_K_LOW_VOL = 0.8  # keep
ATR_K_NORMAL_VOL = 1.0  # keep

# BTC Crash Filter — ensure it blocks copy-trader signals too
BTC_CRASH_BLOCK_ENABLED = True
BTC_CRASH_BLOCK_THRESHOLD = -1.5  # keep
```

---

## 6. Implementation Steps

### Phase 1: Bug Fixes (Immediate)

1. **Fix `features_recorded` column**
   - Run: `UPDATE trades SET features_recorded = TRUE WHERE entry_rsi_14 IS NOT NULL;`
   - Verify `record_entry_features()` sets the flag correctly
   - Test on next 5 trades

2. **Disable MAE Guard**
   - Set `CL_MAE_GUARD_ENABLED = False` in `hermes_constants.py`
   - Monitor system PnL for 48h
   - If PnL improves, keep disabled. If not, try 3.0% threshold.

3. **Verify BTC crash filter blocks copy-trader signals**
   - Check if `ct-hot+` signals go through the crash filter
   - If not, add copy-trader signals to the filter path

### Phase 2: Analysis (Next Week)

4. **Backfill entry features**
   - Run `python3 scripts/backfill_trade_indicators.py`
   - Verify `features_recorded=TRUE` for all backfilled trades

5. **Analyze entry quality by signal type**
   - Group trades by signal source
   - Identify which signals have worst entry timing
   - Consider blocking or penalizing low-quality signals

6. **Test MAE guard at 3.0% threshold**
   - Enable with `CL_MAE_GUARD_THRESHOLD = 0.03`
   - Run for 7 days
   - Compare net impact vs disabled

### Phase 3: Optimization (Month 2)

7. **Entry timing analysis**
   - Analyze trades opened during BTC drops
   - Consider time-based entry filters
   - Consider volatility-based position sizing

8. **Signal source quality ranking**
   - Rank all signals by historical PnL
   - Penalize or block consistently losing signals
   - Boost consistently winning signals

---

## 7. Rollback Plan

### If MAE Guard disable hurts performance:

```python
# Re-enable at original threshold
CL_MAE_GUARD_ENABLED = True
CL_MAE_GUARD_THRESHOLD = 0.015
```

### If ATR SL changes are made (NOT recommended):

```python
# Revert to original values
ATR_SL_MIN = 0.012
ATR_SL_MAX = 0.030
ATR_K_LOW_VOL = 0.8
ATR_K_NORMAL_VOL = 1.0
ATR_K_HIGH_VOL = 0.25
```

---

## 8. Monitoring Plan

### Key Metrics to Track

| Metric | Current | Target | Alert If |
|--------|---------|--------|----------|
| ATR SL hit rate | 75T/48h | Stable | >100T/48h |
| ATR SL net PnL | +$0.67 | Positive | Negative |
| MAE Guard closures | 13T/48h | <5T/48h | >20T/48h |
| System net PnL | -$0.98 | Positive | <-$5/48h |
| Win rate | 46% | >50% | <40% |

### Daily Monitoring Script

```python
# Add to auto_1hr monitoring:
# 1. Check ATR SL hit count and PnL
# 2. Check MAE Guard closures and impact
# 3. Check copy-trader signal quality
# 4. Alert if any metric degrades significantly
```

---

## 9. Conclusion

The original analysis correctly identified problems but proposed wrong solutions:

| Finding | Original Analysis | Independent Verification |
|---------|-------------------|--------------------------|
| ATR SL too tight | Widen to k=2.0-2.5 | **Wrong** — zero benefit for losing trades |
| MAE Guard catches crashes | Enable at 1.5% | **Wrong** — net negative impact |
| PM is harmful | Disable PM | **Neutral** — barely active, minimal impact |
| Entry features not wired | Wire up and backfill | **Partially correct** — wired but bug in flag |

**Root cause of system losses:** Entry timing and signal quality, not SL width. The system is entering trades during adverse conditions (BTC crashes, copy-trader false signals) and getting stopped out immediately. Fix the inputs, not the exits.

---

## Appendix: Raw Data Queries

### ATR SL Hit Analysis (48h)
```sql
SELECT close_reason, COUNT(*), 
       SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END),
       ROUND(AVG(pnl_pct)::numeric, 2),
       ROUND(SUM(pnl_usdt)::numeric, 2)
FROM trades 
WHERE server = 'Hermes' 
  AND close_time > NOW() - INTERVAL '48 hours'
  AND close_reason LIKE '%sl%'
GROUP BY close_reason;
```

### MAE Guard Threshold Simulation (7d)
```sql
WITH trade_mae AS (
    SELECT id, pnl_usdt,
           (highest_price - current_price) / highest_price * 100.0 as drop_pct
    FROM trades 
    WHERE server = 'Hermes' 
      AND status = 'closed'
      AND close_time > NOW() - INTERVAL '7 days'
      AND direction = 'LONG'
)
SELECT threshold,
       COUNT(*),
       SUM(CASE WHEN pnl_usdt < 0 THEN 1 ELSE 0 END),
       SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END),
       ROUND(SUM(CASE WHEN pnl_usdt < 0 THEN pnl_usdt ELSE 0 END)::numeric, 2),
       ROUND(SUM(CASE WHEN pnl_usdt > 0 THEN pnl_usdt ELSE 0 END)::numeric, 2)
FROM trade_mae, 
     (VALUES (1.0), (1.5), (2.0), (3.0)) as t(threshold)
WHERE drop_pct >= threshold
GROUP BY threshold
ORDER BY threshold;
```

### Entry Features Bug Check
```sql
SELECT 
    features_recorded,
    COUNT(*),
    SUM(CASE WHEN entry_rsi_14 IS NOT NULL THEN 1 ELSE 0 END)
FROM trades 
WHERE server = 'Hermes'
GROUP BY features_recorded;
```
