# 🔍 Independent Audit: Block LONG when BB Position ≥ 1.0

**Auditor:** Independent (fresh analysis, no prior conclusions trusted)
**Date:** 2026-09-21
**Data Source:** PostgreSQL brain DB (trades table)
**Claim Source:** 2026-09-21-losing-streak-audit-v2.md (line 183)

---

## Claim to Verify

> "Block LONG when BB Position ≥ 1.0 removes 48 trades with 43.8% WR and -$2.40 total PnL. BB data is available for all trades."

---

## VERDICT

```
╔══════════════════════════════════════════════════════════════════════╗
║  Verdict: DISAGREE                                                  ║
║  All three specific numbers in the claim are wrong.                 ║
║  BB data is NOT available for all trades (40% coverage).            ║
║  Blocking these trades actually HURTS performance.                  ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Evidence

### 1. BB Data Availability — CLAIM FALSE

**Claim:** "BB data is available for all trades"
**Reality:**

| Source | Coverage | Missing |
|--------|----------|---------|
| `entry_bb_position` | 913/2,278 (40.1%) | 1,365 trades |
| `_signal_metadata` BB | 858/2,278 (37.7%) | 1,420 trades |

BB position data is **missing for ~60% of all LONG trades**. The first LONG without entry_bb_position is from 2026-07-28, and the last is from 2026-09-16. This means the column was likely introduced around late July 2026 but wasn't populated for all trades until later.

### 2. Trade Count — CLAIM WRONG

| Metric | Claimed | Actual (entry_bb) | Actual (meta BB) |
|--------|---------|-------------------|------------------|
| Trades blocked | **48** | **155** | **90** |

Neither BB position source produces exactly 48 trades. The closest match would require a date-range or signal-type filter that isn't stated in the claim.

### 3. Win Rate — CLAIM WRONG

| Metric | Claimed | Actual (entry_bb) | Actual (meta BB) |
|--------|---------|-------------------|------------------|
| Win Rate | **43.8%** | **40.6%** | **48.9%** |

Neither source matches 43.8%.

### 4. Total PnL — CLAIM WRONG

| Metric | Claimed | Actual (entry_bb) | Actual (meta BB) |
|--------|---------|-------------------|------------------|
| Total PnL | **-$2.40** | **+$0.12** | **+$0.06** |

Both sources show **POSITIVE** total PnL for BB ≥ 1.0 trades, not negative. The claimed -$2.40 is not reproducible.

### 5. Blocking BB ≥ 1.0 HURTS Performance

Using `entry_bb_position` (the only column directly on the trades table):

| Metric | Before Filter | After Filter | Change |
|--------|---------------|--------------|--------|
| Trades | 913 | 758 | -155 |
| Win Rate | 39.1% | 38.8% | **-0.3 pp** |
| Total PnL | -$1.62 | -$1.74 | **-$0.12** |

**Blocking BB ≥ 1.0 removes 155 trades that are actually ABOVE average (40.6% WR vs 39.1% overall).** The filter makes the system worse, not better.

### 6. Threshold Sensitivity Analysis

| Threshold | Blocked | WR | Total PnL | Avg PnL |
|-----------|---------|-----|-----------|---------|
| ≥ 0.85 | 365 | 41.9% | +$0.98 | $0.003 |
| ≥ 0.90 | 293 | 40.6% | +$1.03 | $0.004 |
| ≥ 0.95 | 227 | 40.1% | -$0.77 | -$0.003 |
| **≥ 1.0** | **155** | **40.6%** | **+$0.12** | **$0.001** |
| ≥ 1.05 | 95 | 38.9% | +$0.06 | $0.001 |
| ≥ 1.10 | 61 | 34.4% | -$0.70 | -$0.011 |

**BB ≥ 1.10 is the first threshold where blocking meaningfully helps** (removes 61 trades at 34.4% WR, saving -$0.70). But even this is marginal.

### 7. Time Period Breakdown

| Period | Total LONG | Blocked (≥1.0) | Blocked WR | Blocked PnL |
|--------|------------|----------------|------------|-------------|
| May–Jul 2026 | 729 | 149 | 40.3% | +$0.01 |
| Aug–Sep 2026 | 184 | 6 | 50.0% | +$0.11 |

The Aug–Sep period has almost no BB ≥ 1.0 trades (only 6), making any filter in that period negligible.

### 8. Distribution by Entry BB Range

| Range | N | WR | Total PnL | Avg PnL |
|-------|-----|--------|-----------|---------|
| 0.0–0.5 | 211 | 37.9% | -$2.15 | -$0.0102 |
| 0.5–0.7 | 140 | 39.3% | +$2.05 | +$0.0146 |
| 0.7–0.85 | 178 | 34.8% | -$1.42 | -$0.0080 |
| 0.85–0.9 | 72 | 47.2% | -$0.05 | -$0.0007 |
| 0.9–0.95 | 66 | 42.4% | +$1.80 | +$0.0273 |
| 0.95–1.0 | 72 | 38.9% | -$0.89 | -$0.0124 |
| **1.0–1.5** | **155** | **40.6%** | **+$0.12** | **+$0.0008** |

**BB 0.7–0.85 is actually the worst bucket** (34.8% WR, -$1.42), not BB ≥ 1.0.

---

## Root Cause of Claim Discrepancy

The claim originates from the `2026-09-21-losing-streak-audit-v2.md` file, which used `_signal_metadata->>'bb_position'` on a **filtered subset** of 391 trades (only those with continuum.db BTC state match, covering Sep 4–21 only). The numbers in that audit were:
- 48 trades, 43.8% WR, -$0.44 PnL

These numbers were specific to that 18-day filtered dataset. When applied to the full trades table, the numbers change significantly:
- 90 trades (meta BB), 48.9% WR, +$0.06 PnL
- 155 trades (entry_bb), 40.6% WR, +$0.12 PnL

The claim further mutated the PnL from -$0.44 to -$2.40, which doesn't match any source.

---

## Recommendations

1. **Do NOT implement Block LONG when BB ≥ 1.0.** It removes trades that are slightly above average and hurts total PnL.

2. **If a BB filter is desired, consider BB ≥ 1.1.** This removes 61 trades at 34.4% WR (clearly below average) with -$0.70 PnL. However, even this is marginal.

3. **The real performance drag is in the BB 0.7–0.85 range** (34.8% WR, -$1.42 PnL, 178 trades). This is where investigation should focus.

4. **BB data coverage needs improvement.** Only 40% of trades have entry_bb_position. Any BB-based filter will miss 60% of trades.

5. **Source audit numbers carefully.** The original audit used a 17.3% filtered subset (391/2,262 trades). Filtered results should not be extrapolated to the full dataset without disclosure.

---

## Summary Table

| Claim Element | Claimed | Verified | Match? |
|---------------|---------|----------|--------|
| Trade count | 48 | 155 (entry_bb) / 90 (meta) | ❌ |
| Win rate | 43.8% | 40.6% (entry_bb) / 48.9% (meta) | ❌ |
| Total PnL | -$2.40 | +$0.12 (entry_bb) / +$0.06 (meta) | ❌ |
| BB data universal | Yes | No (40.1% coverage) | ❌ |
| Filter improves system | Implied | No (WR -0.3pp, PnL -$0.12) | ❌ |

---

*Audited by independent agent from scratch. All SQL queries run against live PostgreSQL. No prior analysis trusted.*
