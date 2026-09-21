# Oscillator Matrix Data Verification — Independent Audit

**Date:** 2026-09-22
**Auditor:** Independent Verification Agent (own-conclusions protocol)
**Data Source:** PostgreSQL `brain` database, `trades` table
**Database:** `/var/run/postgresql/brain` (user: postgres)
**Claim Under Review:** Corrected OSCILLATOR_MULTS based on "90d data"

---

## === INDEPENDENT VERDICT ===

### Executive Summary

The proposed oscillator matrix was verified against live PostgreSQL data. **The data does NOT span 90 days — it spans only ~10 days (Sep 12-21, 2026).** Coverage is critically low: only 8.5% of 90-day trades have the required btc_score field. Of the 12 proposed multipliers, **1 is WRONG directionally, 2 have minor stat discrepancies, and 6 of 12 cells have critically small samples (≤9 trades).**

**Overall Assessment: UNCERTAIN — Premature for production**

---

## 1. CRITICAL FINDING: Data Window is 10 Days, Not 90

The proposal claims "90d data." This is **false**.

```
earliest_btc_score_trade: 2026-09-12 00:16:29
latest_btc_score_trade:   2026-09-21 14:05:34
total trades with btc_score: 282
```

The `btc_score` field was introduced into `_signal_metadata` around Sep 12, 2026. All 282 trades with btc_score fall within a 10-day window. The "90d" framing dramatically overstates the data foundation.

**Impact:** Multipliers derived from 10 days of data in a single market regime are not robust. Market conditions can shift completely in 10 days.

---

## 2. Data Coverage

| Metric | Count (90d window) | Percentage |
|--------|---------------------|------------|
| Total closed trades | 3,335 | 100% |
| Has `btc_score` | 284 | **8.5%** |
| Has `wave_phase` | 1,454 | 43.5% |
| Has **both** btc_score AND wave_phase | 284 | **8.5%** |
| Neutral wave_phase (excluded from matrix) | ~2 | — |

**Verdict:** The matrix would only affect **8.5% of all trades.** Over 91% of trades have no btc_score and would default to 1.0x (no multiplier). The system-wide impact of this matrix is marginal.

---

## 3. Multiplier-by-Multiplier Verification

**Method:** SQL query against PostgreSQL. Win rate computed as `AVG(CASE WHEN pnl_usdt > 0 THEN 1.0 ELSE 0.0 END) * 100` (matching the claim's WR methodology). Total PnL = `SUM(pnl_usdt)`.

### Verification Table

| Cell | Claim | Actual | Trade Count | WR (USDT) | Total PnL | Multiplier | Verdict |
|------|-------|--------|-------------|-----------|-----------|------------|---------|
| (LOW, falling) | 35T, 22.9%WR, -$3.16 | 35T, 22.9%WR, -$3.16 | ✅ Match | ✅ Match | ✅ Match | 0.6 | **VERIFIED** |
| (LOW, accelerating) | 36T, 52.8%WR, +$0.46 | 36T, 52.8%WR, +$0.46 | ✅ Match | ✅ Match | ✅ Match | 1.1 | **VERIFIED** |
| (LOW, bottoming) | 4T, 75%WR, +$0.33 | 4T, 75.0%WR, +$0.33 | ✅ Match | ✅ Match | ✅ Match | 1.3 | **UNCERTAIN** — 4 trades is statistically meaningless |
| (LOW, decelerating) | 7T, 57.1%WR, -$0.08 | 7T, 57.1%WR, -$0.08 | ✅ Match | ✅ Match | ✅ Match | 0.95 | **VERIFIED** — but borderline |
| (MID, falling) | 35T, 42.9%WR, +$0.53 | **36T, 44.4%WR, +$0.54** | ❌ Off by 1 | ❌ Off by 1.5% | ❌ Off by $0.01 | 1.0 | **WRONG** — stale claim (1 new trade added) |
| (MID, accelerating) | 54T, 55.6%WR, +$2.49 | 54T, 55.6%WR, +$2.49 | ✅ Match | ✅ Match | ✅ Match | 1.1 | **VERIFIED** |
| (MID, bottoming) | 9T, 66.7%WR, -$0.29 | 9T, 66.7%WR, -$0.29 | ✅ Match | ✅ Match | ✅ Match | 0.8 | **VERIFIED** |
| (MID, decelerating) | 7T, 57.1%WR, +$0.27 | 7T, 57.1%WR, +$0.27 | ✅ Match | ✅ Match | ✅ Match | 1.15 | **WRONG** — see analysis below |
| (HIGH, falling) | 43T, 48.8%WR, -$0.01 | 43T, 48.8%WR, -$0.01 | ✅ Match | ✅ Match | ✅ Match | 0.8 | **VERIFIED** |
| (HIGH, accelerating) | 34T, 61.8%WR, +$1.30 | 34T, 61.8%WR, +$1.30 | ✅ Match | ✅ Match | ✅ Match | 1.2 | **VERIFIED** |
| (HIGH, bottoming) | 9T, 77.8%WR, +$0.82 | 9T, 77.8%WR, +$0.82 | ✅ Match | ✅ Match | ✅ Match | 1.3 | **UNCERTAIN** — 9 trades, wide CI |
| (HIGH, decelerating) | 5T, 60%WR, +$0.20 | 5T, 60.0%WR, +$0.20 | ✅ Match | ✅ Match | ✅ Match | 1.1 | **UNCERTAIN** — 5 trades, meaningless |

---

## 4. Detailed Analysis of Problematic Cells

### 4a. (MID, decelerating) — 1.15x is WRONG

**The stats match but the multiplier direction is unjustified.**

| Metric | Value |
|--------|-------|
| Trades | 7 |
| Total PnL | +$0.27 |
| Avg PnL% | **-0.59%** |
| Win Rate (USDT) | 57.1% |
| StdDev PnL% | 5.55% |
| Sharpe-like (avg/σ) | **-0.106** |

**Why 1.15x is wrong:**
- The avg PnL% is **negative** (-0.59%). A boost multiplier implies this cell is profitable on average — it is not.
- The total PnL is barely positive (+$0.27) because one trade (BABY, +$0.30) carried the cell. Remove BABY and the cell is -$0.03.
- The Sharpe-like ratio is negative (-0.106), meaning the mean is below zero relative to noise.
- A 1.15x boost would increase confidence for a cell that is statistically indistinguishable from breakeven.

**Correct multiplier:** 0.9–1.0 (neutral to slight penalty). Not 1.15.

### 4b. (MID, falling) — Stale Claim

**The data in the claim is off by 1 trade and small PnL/WR differences.**

| Metric | Claimed | Actual | Delta |
|--------|---------|--------|-------|
| Trades | 35 | 36 | +1 new trade |
| WR (USDT) | 42.9% | 44.4% | +1.5% |
| Total PnL | +$0.53 | +$0.54 | +$0.01 |

One new trade (likely closed Sep 20-21) was added since the claim was generated. The multiplier 1.0 (neutral) is still reasonable for this cell, but the underlying numbers should be refreshed.

### 4c. (LOW, bottoming) — 4 Trades is Meaningless

- 75% WR sounds impressive, but with 4 trades, the 95% confidence interval for WR is approximately **29%–95%** (Clopper-Pearson).
- The $0.33 total PnL is statistically indistinguishable from zero.
- The 1.3x boost is based on essentially noise.

### 4d. (HIGH, decelerating) — 5 Trades is Meaningless

- 60% WR with 5 trades → CI approximately **23%–92%**.
- The $0.20 total PnL is noise.
- The 1.1x boost is unjustified.

---

## 5. Statistical Concerns

### 5a. Sample Size Assessment

| Category | Cells | Assessment |
|----------|-------|------------|
| Critically small (≤5 trades) | LOW/bottoming (4), HIGH/decelerating (5) | **Cannot draw conclusions** |
| Small (6-10 trades) | LOW/decelerating (7), MID/bottoming (9), MID/decelerating (7), HIGH/bottoming (9) | **Weak evidence** |
| Adequate (30+ trades) | LOW/falling (35), LOW/accelerating (36), MID/falling (36), MID/accelerating (54), HIGH/falling (43), HIGH/accelerating (34) | **Some signal** |

**Half the matrix (6/12 cells) has ≤9 trades.** This is insufficient for reliable multiplier estimation.

### 5b. Signal-to-Noise (Sharpe-like Ratio: avg PnL% / stddev PnL%)

| Cell | Sharpe-like | Interpretation |
|------|-------------|----------------|
| LOW/falling | -0.633 | **Strong signal** (negative) |
| HIGH/bottoming | +0.736 | **Strong signal** (positive) |
| LOW/bottoming | +0.460 | Moderate (but only 4 trades) |
| HIGH/accelerating | +0.247 | Weak |
| HIGH/decelerating | +0.232 | Weak (5 trades) |
| MID/accelerating | +0.205 | Weak |
| LOW/accelerating | +0.194 | Weak |
| LOW/decelerating | +0.085 | Noise |
| MID/falling | +0.042 | Noise |
| HIGH/falling | -0.084 | Noise |
| MID/decelerating | -0.106 | Noise (negative) |
| MID/bottoming | -0.182 | Noise (negative) |

**Only 2 of 12 cells have strong signals** (LOW/falling and HIGH/bottoming). The rest are weak to pure noise.

### 5c. Variance Warning

The stddev of PnL% ranges from 4.56% to 9.96% across cells. This means individual trade outcomes vary wildly — a single trade can swing the cell's statistics dramatically. The MID/decelerating cell is a perfect example: one BABY trade (+$0.30) flips the cell from negative to barely positive.

---

## 6. Multiplier Logic Audit

The proposed multipliers should follow this logic:
- **Profitable cell** (positive total PnL, WR > 50%) → **Boost** (>1.0)
- **Unprofitable cell** (negative total PnL, WR < 50%) → **Penalty** (<1.0)
- **Ambiguous cell** (mixed signals) → **Neutral** (~1.0)

### Direction Check

| Cell | Total PnL | Avg PnL% | WR | Mult | Direction Correct? |
|------|-----------|----------|-----|------|-------------------|
| LOW/falling | -$3.16 | -2.88% | 22.9% | 0.6 | ✅ YES — clear penalty |
| LOW/accelerating | +$0.46 | +0.99% | 52.8% | 1.1 | ✅ YES — moderate boost |
| LOW/bottoming | +$0.33 | +2.44% | 75% | 1.3 | ⚠️ MAYBE — direction ok, magnitude unsupported by4 trades |
| LOW/decelerating | -$0.08 | +0.54% | 57.1% | 0.95 | ✅ YES — near-neutral, slight penalty for net loss |
| MID/falling | +$0.54 | +0.26% | 44.4% | 1.0 | ✅ YES — neutral for ambiguous cell |
| MID/accelerating | +$2.49 | +2.04% | 55.6% | 1.1 | ✅ YES — best total PnL |
| MID/bottoming | -$0.29 | -0.83% | 66.7% | 0.8 | ✅ YES — high WR but negative PnL (losers bigger) |
| **MID/decelerating** | **+$0.27** | **-0.59%** | **57.1%** | **1.15** | **❌ NO — negative avg PnL, negative Sharpe, gets boost** |
| HIGH/falling | -$0.01 | -0.43% | 48.8% | 0.8 | ✅ YES — slight penalty |
| HIGH/accelerating | +$1.30 | +1.45% | 61.8% | 1.2 | ✅ YES — strong performer |
| HIGH/bottoming | +$0.82 | +3.44% | 77.8% | 1.3 | ✅ YES — best avg PnL, highest WR |
| HIGH/decelerating | +$0.20 | +1.65% | 60% | 1.1 | ✅ YES — moderate boost |

**11 of 12 directionally correct. 1 clearly wrong (MID/decelerating).**

---

## 7. Confidence Assessment

### Per-Multiplier Confidence

| Cell | Trade Count | Signal Strength | Verdict | Confidence |
|------|-------------|-----------------|---------|------------|
| LOW/falling | 35 | Strong (-0.633) | VERIFIED | **HIGH** |
| LOW/accelerating | 36 | Weak (0.194) | VERIFIED | **MEDIUM** |
| LOW/bottoming | 4 | Moderate (0.460) | UNCERTAIN | **LOW** — 4 trades |
| LOW/decelerating | 7 | Noise (0.085) | VERIFIED | **LOW** — 7 trades |
| MID/falling | 36 | Noise (0.042) | WRONG (stale) | **MEDIUM** — needs refresh |
| MID/accelerating | 54 | Weak (0.205) | VERIFIED | **MEDIUM** |
| MID/bottoming | 9 | Noise (-0.182) | VERIFIED | **LOW** — 9 trades, negative Sharpe |
| MID/decelerating | 7 | Noise (-0.106) | **WRONG** | **LOW** — directionally wrong |
| HIGH/falling | 43 | Noise (-0.084) | VERIFIED | **MEDIUM** |
| HIGH/accelerating | 34 | Weak (0.247) | VERIFIED | **MEDIUM** |
| HIGH/bottoming | 9 | Strong (0.736) | UNCERTAIN | **LOW** — 9 trades |
| HIGH/decelerating | 5 | Weak (0.232) | UNCERTAIN | **LOW** — 5 trades |

### Overall Confidence: **LOW**

**Reasons:**
1. Data spans 10 days, not 90 — overstates data foundation
2. Only 8.5% of trades have the required btc_score
3. Half the cells have ≤9 trades (statistically insignificant)
4. 1 multiplier is directionally wrong (MID/decelerating: 1.15x on negative-avg-PnL cell)
5. Only 2 of 12 cells have statistically meaningful signals (|Sharpe| > 0.4)
6. High variance (stddev 4.6%-10.0%) means single trades can flip cell statistics

---

## 8. Recommendations

### Must-Fix Before Any Use

1. **Fix (MID, decelerating):** Change from 1.15 to **0.9–1.0**. The cell has negative avg PnL% and negative Sharpe-like ratio. A boost is wrong.

2. **Refresh (MID, falling):** Update claim from 35T to 36T, 42.9% to 44.4%, +$0.53 to +$0.54. The multiplier 1.0 is still reasonable.

3. **Remove "90d data" framing:** The btc_score field exists for 10 days only (Sep 12-21, 2026). Call it what it is.

### Statistical Warnings

4. **Flag small-sample cells:** LOW/bottoming (4T), HIGH/decelerating (5T) should either use default 1.0 or have a confidence-weighted blend toward 1.0.

5. **Consider shrinkage:** For cells with <15 trades, blend the observed multiplier toward 1.0 proportional to sample size. This prevents overfitting to noise.

6. **Collect more data:** Wait for 50+ trades per cell before trusting multipliers. At current rate (~28 btc_score trades/day), this takes ~2 more weeks for the busiest cells, and months for the smallest ones.

### System-Level Consideration

7. **8.5% coverage means 91.5% of trades are unaffected.** The entire matrix has marginal system-level impact. Prioritize signals or filters that cover 100% of trades.

---

## 9. Appendix: Raw SQL Queries Used

### Data Coverage
```sql
SELECT 
    COUNT(*) as total_trades,
    COUNT(CASE WHEN _signal_metadata->'btc_score' IS NOT NULL THEN 1 END) as has_btc_score,
    COUNT(CASE WHEN _signal_metadata->'wave_phase' IS NOT NULL THEN 1 END) as has_wave_phase,
    COUNT(CASE WHEN _signal_metadata->'btc_score' IS NOT NULL AND _signal_metadata->'wave_phase' IS NOT NULL THEN 1 END) as has_both
FROM trades
WHERE status = 'closed' AND close_time >= now() - interval '90 days';
```

### Zone/Phase Performance (Primary Query)
```sql
WITH btc_zone AS (
    SELECT 
        id, pnl_usdt, pnl_pct,
        CASE 
            WHEN (_signal_metadata->>'btc_score')::float < 30 THEN 'LOW'
            WHEN (_signal_metadata->>'btc_score')::float <= 70 THEN 'MID'
            ELSE 'HIGH'
        END as btc_zone,
        _signal_metadata->>'wave_phase' as wave_phase
    FROM trades
    WHERE status = 'closed'
      AND close_time >= now() - interval '90 days'
      AND _signal_metadata->'btc_score' IS NOT NULL
      AND _signal_metadata->'wave_phase' IS NOT NULL
)
SELECT 
    btc_zone, wave_phase,
    COUNT(*) as trades,
    ROUND(AVG(pnl_pct)::numeric, 2) as avg_pnl_pct,
    ROUND(SUM(pnl_usdt)::numeric, 2) as total_pnl_usdt,
    ROUND(AVG(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0.0 END)::numeric * 100, 1) as win_rate_by_pct,
    ROUND(AVG(CASE WHEN pnl_usdt > 0 THEN 1.0 ELSE 0.0 END)::numeric * 100, 1) as win_rate_by_usdt
FROM btc_zone
WHERE wave_phase IN ('falling', 'accelerating', 'bottoming', 'decelerating')
GROUP BY btc_zone, wave_phase
ORDER BY btc_zone, wave_phase;
```

### Standard Deviation and Sharpe-like
```sql
-- Same CTE as above, then:
SELECT 
    btc_zone, wave_phase, COUNT(*) as trades,
    ROUND(AVG(pnl_pct)::numeric, 2) as avg_pnl_pct,
    ROUND(STDDEV(pnl_pct)::numeric, 2) as stddev_pnl_pct,
    ROUND(AVG(pnl_pct)::numeric / NULLIF(STDDEV(pnl_pct), 0), 3) as sharpe_like
FROM btc_zone
WHERE wave_phase IN ('falling', 'accelerating', 'bottoming', 'decelerating')
GROUP BY btc_zone, wave_phase;
```

### btc_score Temporal Coverage
```sql
SELECT DATE_TRUNC('day', open_time) as day, COUNT(*) as trades_with_btc_score
FROM trades
WHERE _signal_metadata->'btc_score' IS NOT NULL AND status = 'closed'
GROUP BY DATE_TRUNC('day', open_time) ORDER BY day;
```

### Win Rate Cross-Validation (pnl_usdt vs pnl_pct)
```sql
-- Verified that claim WR matches pnl_usdt > 0 method, not pnl_pct > 0
SELECT 
    btc_zone, wave_phase,
    ROUND(AVG(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0.0 END)*100, 1) as wr_by_pct,
    ROUND(AVG(CASE WHEN pnl_usdt > 0 THEN 1.0 ELSE 0.0 END)*100, 1) as wr_by_usdt
FROM btc_zone GROUP BY btc_zone, wave_phase;
```

---

## 10. Summary Verdict

```
=== INDEPENDENT VERDICT ===

Multipliers verified: 10/12 data-stats match (2 stale/wrong)
Multipliers directionally correct: 11/12 (MID/decelerating is wrong)
Multipliers with adequate statistical backing: 2/12 (LOW/falling, HIGH/bottoming)

Data coverage: 8.5% (284/3,335 trades in 90d)
Actual data window: ~10 days (Sep 12-21), NOT 90 days

Cell verdicts:
  (LOW, falling):        VERIFIED     — 35T, strong negative signal, 0.6 is justified
  (LOW, accelerating):   VERIFIED     — 36T, moderate positive, 1.1 is reasonable
  (LOW, bottoming):      UNCERTAIN    — 4T, statistically meaningless sample
  (LOW, decelerating):   VERIFIED     — 7T, borderline, 0.95 is conservative
  (MID, falling):        WRONG        — stale (35→36T), needs refresh
  (MID, accelerating):   VERIFIED     — 54T, best total PnL, 1.1 justified
  (MID, bottoming):      VERIFIED     — 9T, high WR but neg avg PnL, 0.8 correct
  (MID, decelerating):   WRONG        — 1.15x on negative-avg-PnL cell, should be 0.9-1.0
  (HIGH, falling):       VERIFIED     — 43T, slight loser, 0.8 correct
  (HIGH, accelerating):  VERIFIED     — 34T, solid performer, 1.2 justified
  (HIGH, bottoming):     UNCERTAIN    — 9T, strong signal but small sample
  (HIGH, decelerating):  UNCERTAIN    — 5T, statistically meaningless sample

Confidence: LOW
  - 10-day data, not 90
  - 8.5% coverage
  - 6/12 cells with ≤9 trades
  - 1 multiplier directionally wrong
  - High variance (stddev 4.6-10%)
```

---

**Auditor:** Independent Verification Agent
**Verification Date:** 2026-09-22
**Database:** PostgreSQL brain (5,228 total trades; 284 with btc_score in 90d window)
**Protocol:** own-conclusions — fresh SQL queries, no reliance on prior analysis
