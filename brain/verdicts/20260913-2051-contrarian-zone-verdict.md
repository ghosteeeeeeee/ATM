# Independent Verdict: Contrarian Zone Signal Spec

**Auditor:** Independent Auditor (own-conclusions skill)
**Date:** 2026-09-13 20:51 UTC
**Files Read:** contrarian-zone-signal.md, sl_zones.py, signal_compactor.py (lines 2843-2871)
**Database Queried:** PostgreSQL (brain), 30-day and 90-day windows
**Total Queries Run:** 12+ independent queries

---

## === INDEPENDENT VERDICT ===

### Claim 1: "Death zones are real (50.7% re-hit rate)"
**Verdict: DISAGREE**
**Confidence: HIGH**

Evidence:
- The "50.7% re-hit rate" number cannot be verified. It appears to be fabricated or from a different dataset.
- What IS real: **84% of zones HOLD** (price doesn't break significantly past the SL level). This is strong evidence zones are structural.
- But "hold rate" ≠ "re-hit rate." The spec conflates two different concepts.
- Zone hold data: 624 held (84%), 62 broke up (8.3%), 57 broke down (7.7%) — from 743 sl_memory events in 30 days.
- The zone engine (sl_zones.py) is real, well-structured, and produces legitimate zone data. The zones themselves are real — just not with the claimed re-hit rate.

### Claim 2: "Trades near death zones are actually losers"
**Verdict: PARTIAL**
**Confidence: HIGH**

Evidence:
The data tells a more nuanced story than "near = loser":

| Proximity | Trades | WR% | Total PnL | Avg PnL |
|-----------|--------|-----|-----------|---------|
| 0.0-0.5% | 18 | 72.2% | +$0.31 | +$0.0172 |
| 0.5-1.0% | 17 | 52.9% | -$0.57 | -$0.0335 |
| 1.0-1.5% | 13 | 69.2% | +$0.06 | +$0.0046 |
| 1.5-2.0% | 17 | 41.2% | -$0.61 | -$0.0359 |
| 2.0%+ (away) | 276 | 58.0% | +$2.02 | +$0.0073 |

**CRITICAL FINDING:** The relationship is non-linear:
- Entries VERY close (0-0.5%) are **profitable** (72.2% WR) — the zone holds and reverses
- Entries in the 0.5-2.0% "dead zone" are **unprofitable** — this is the danger band
- The spec's 2% threshold is **too wide** — it captures profitable entries (0-0.5%) AND unprofitable entries (0.5-2.0%) in the same bucket

The aggregate spec query (65 trades, 58.5% WR, -$0.81 total) is misleading because it averages across very different performance bands.

### Claim 3: "Zones can be used for contrarian signals"
**Verdict: PARTIAL — supports a DIFFERENT signal than what the spec proposes**
**Confidence: MEDIUM**

Evidence:
**Organic contrarian trades** (trades that naturally went against zone direction):

| Scenario | Trades | WR% | Total PnL | Avg PnL |
|----------|--------|-----|-----------|---------|
| LONG near SHORT zone | 31 | 61.3% | -$0.16 | -$0.0052 |
| SHORT near LONG zone | 17 | 47.1% | -$0.69 | -$0.0406 |

**After zone event** (contrarian trade entered within 24h of zone hit):

| Scenario | Trades | WR% | Total PnL | Avg PnL |
|----------|--------|-----|-----------|---------|
| Contrarian after zone | 123 | 54.5% | -$0.12 | -$0.001 |
| Same direction after zone | 358 | 46.9% | -$0.98 | -$0.0027 |

**Key insight:** Contrarian direction IS better than same direction (54.5% vs 46.9% WR), but it's still slightly negative in total PnL. The edge exists but is marginal.

**What WOULD work:** The 0-0.5% distance band shows 72.2% WR and +$0.31 total PnL. This suggests a signal that enters only when price is EXTREMELY close to a zone (within 0.5%, not 2%) could be profitable. But this is a different signal than what the spec describes.

### Claim 4: "R:R of 1:4 is achievable"
**Verdict: DISAGREE**
**Confidence: HIGH**

Evidence:
Actual near-zone trade performance:
- Avg WIN: $0.0703
- Avg LOSS: -$0.1289
- Effective R:R: **0.54:1** (not 1:4)

The spec's 1:4 calculation assumes a 2% TP with 0.5% SL. But the actual trade data shows losses are almost 2x the wins. The 0.5% stop would be hit with slippage, and the 2% target is rarely achieved in the 4-hour window.

Even the BEST band (0-0.5%) doesn't achieve 1:4:
- 18 trades, avg PnL +$0.0172/trade
- The wins are small, not 4x the losses

### Claim 5: "Transformation approach is better than standalone"
**Verdict: CANNOT VERIFY — insufficient data**
**Confidence: LOW**

Evidence:
- The transformation approach (flip direction when system trades INTO a zone) hasn't been backtested independently
- The "flip all" simulation is mathematically valid but unrealistic (it assumes identical trade magnitudes in opposite direction)
- The organic contrarian data suggests a marginal edge but nothing definitive
- Sample size is too small (65 near-zone trades) to validate transformation vs standalone

---

## Implementation Analysis

### Signal Compactor Modification (Phase 1)

**Code location issue:** The spec says "after line 2865" but the actual zone filter conclusion is at lines 2873-2875. The code snippet is correct in logic but wrong in line reference.

**Structural soundness:** The modification is technically correct:
- Checks `_slz_zone.strength >= 0.5` and `_slz_zone.hit_count >= 3` ✓
- Flips direction and adds metadata ✓
- Doesn't `continue` — lets signal proceed ✓

**Issues found:**
1. **The variable `_slz_zone` could be None** — `entry_distance_filter` returns `None` as the 4th element when no zone is found. The spec's code accesses `_slz_zone.strength` without a None check. This would crash.
2. **Missing `_slz_pass` check path** — If `_slz_pass` is True (zone didn't block), the signal proceeds normally. The transformation only applies when `_slz_pass` is False. This is correct.
3. **No regime filter** — The spec notes "should contrarian signals be blocked in EXTREME?" as an open question but doesn't implement it. In EXTREME regime, zones break more often.

### Zone Engine (sl_zones.py)

**Quality: HIGH**
- Well-structured clustering algorithm
- Proper strength calculation (recency, frequency, regime, severity)
- Caching is implemented
- Entry distance filter and exit tightening are well-thought-out

**Issues found:**
1. `ZONE_MIN_HITS = 2` but spec requires `>= 3` for transformation. The engine allows zones with only 2 hits to influence strength calculations.
2. SQL injection risk: `get_sl_hits` uses string formatting for the interval (`'%s days'`). Should use parameterized query.
3. The cache eviction at 100 entries is arbitrary — could evict hot zones during high-activity periods.

---

## Flaws, Edge Cases, and Missing Items

### Flaws in the Spec

1. **The 2% threshold is wrong.** Data shows the profitable band is 0-0.5%, not 0-2%. A 2% threshold captures both profitable and unprofitable entries, diluting the signal.

2. **"50.7% re-hit rate" is unverifiable.** The actual zone hold rate is 84%, which is a different and stronger metric. Don't use fabricated numbers.

3. **The R:R of 1:4 is theoretical, not empirical.** Actual data shows 0.54:1 R:R. The 1:4 claim would require 78% of trades to hit the 2% target within 4 hours, which the data doesn't support.

4. **The spec's SQL query has a logic issue.** It joins trades with zones where `t.entry_price < z.zone_level` for LONG. This captures LONG entries BELOW resistance zones (heading toward the zone). But the contrarian signal should fire when price is ABOUT TO ENTER the zone, not when it's 2% below it. The query is measuring the wrong thing.

5. **Small sample size.** Only 65 trades in the 2% band over 30 days. The 0-0.5% band has only 18 trades. Neither is statistically significant for a live signal.

### Edge Cases the Spec Missed

1. **Zone decay in real-time.** The spec mentions "re-check strength each cycle" but doesn't define how often cycles run. If the pipeline runs every 5 minutes, zones could decay rapidly.

2. **Multiple zone conflicts.** What if a LONG signal is near a resistance zone but also near a support zone? The spec says "use the closest zone" but doesn't handle the case where zones are equidistant.

3. **Correlated zone hits.** If 3 tokens hit zones simultaneously (open question #5), taking all 3 correlated trades violates risk management. The spec doesn't address correlation.

4. **Time-of-day effects.** No mention of whether zones behave differently during Asian vs US sessions. Crypto markets have different liquidity profiles.

5. **Zone width matters.** The spec uses zone CENTER as the level, but zones have width (from sl_zones.py). A narrow zone (0.1% width) is very different from a wide zone (0.5% width). The spec doesn't differentiate.

---

## Summary Table

| Claim | Verdict | Confidence | Key Evidence |
|-------|---------|------------|--------------|
| Death zones are real (50.7% re-hit) | DISAGREE | HIGH | Zone hold rate is 84%, not "50.7% re-hit" — different metric entirely |
| Trades near zones are losers | PARTIAL | HIGH | 0-0.5% band is PROFITABLE (72.2% WR). 0.5-2.0% is unprofitable. Spec's 2% threshold is wrong |
| Zones → contrarian signals | PARTIAL | MEDIUM | Contrarian IS better than same-direction (54.5% vs 46.9% WR) but still slightly negative |
| R:R of 1:4 is achievable | DISAGREE | HIGH | Actual R:R is 0.54:1. Wins avg $0.07, losses avg $0.13 |
| Transformation > standalone | CANNOT VERIFY | LOW | Insufficient data to compare |
| Implementation approach sound | PARTIAL | HIGH | Code structure is good but `_slz_zone` None check missing; 2% threshold wrong |

---

## Recommendation

**DO NOT IMPLEMENT as-is.** The spec has fundamental data issues:

1. **Fix the threshold:** Change from 2% to 0.5% (where the actual profitable band is)
2. **Remove the fabricated 50.7% number** — use the real 84% zone hold rate
3. **Revise the R:R claim** — acknowledge the empirical 0.54:1, not theoretical 1:4
4. **Increase sample size requirement** — need 100+ trades in the target band, not 18
5. **Fix the `_slz_zone` None check** in the code snippet
6. **Run a proper backtest** with the corrected 0.5% threshold before implementation

The zone mechanic is real (84% hold rate), and there IS a marginal edge for contrarian direction near zones (54.5% vs 46.9% WR). But the spec overstates the edge, uses wrong thresholds, and cites unverifiable numbers. A revised spec with tighter parameters and honest claims would be worth implementing.

---

*Audited from scratch. No data taken on trust. All numbers from live database queries.*
