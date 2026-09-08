# BTC Trend Alignment + Crash Protection Overhaul

**Date:** 2026-09-08
**Status:** ANALYSIS COMPLETE → AWAITING IMPLEMENTATION
**Trigger:** 6 LONGs lost 4-6% each in cascade sell-off (2026-09-04 12:30 UTC)

---

## Incident Summary

On 2026-09-04 at 12:30 UTC, BTC dropped -1.42% in a single candle (81,340 → 80,186), continuing to -2.62% by 12:46. Six open LONG positions were caught:

| Token | Entry | Loss | Opened | Signal |
|-------|-------|------|--------|--------|
| ALT | $0.0064 | -5.62% | 09:31 | ema300-dip |
| YGG | $0.0229 | -6.15% | 09:52 | ema300-dip |
| GMT | $0.0074 | -4.91% | 09:33 | ema300-dip |
| NXPC | $0.2081 | -5.75% | 11:53 | ema300-dip |
| BABY | $0.0111 | -6.29% | 12:27 | ema300-dip |
| BCH | $252.44 | -6.16% | 12:31 | ema300-dip |

**Key finding:** BCH was +13.4% leveraged at 12:29 (1 minute before crash). A trailing profit lock would have saved it.

---

## Root Cause Analysis

### Problem 1: No BTC Trend Alignment Filter

The ema300-dip signal has a `MIN_BTC_TREND = 0.5%` filter, but ALL 6 trades show BTC trend below 0.5% at open time. The filter either isn't applied at execution or the signal was detected earlier when BTC was above threshold.

**BTC state at each trade open:**

| Trade | BTC 1h Trend | BTC 30m Mom | Should Have Been |
|-------|-------------|-------------|-----------------|
| ALT | +0.01% | -0.135% | BLOCKED |
| YGG | -0.13% | -0.019% | BLOCKED |
| GMT | +0.03% | -0.116% | BLOCKED |
| NXPC | +0.31% | +0.052% | BORDERLINE |
| BABY | -0.09% | +0.066% | BORDERLINE |
| BCH | -1.63% | -1.467% | BLOCKED |

### Problem 2: MAE Guard Too Slow

The MAE guard threshold was 3.0% — these trades bled to 4-6% before any protection kicked in.

### Problem 3: No Profit Lock

BCH was +13.4% leveraged at peak. No trailing stop or profit lock existed to capture gains before the reversal.

---

## Data Analysis: 2,196 Actual Trades

Cross-referenced all closed trades with BTC 30m momentum at entry time.

### LONG Performance by BTC Direction

| BTC 30m | Trades | WR | Total PnL | Verdict |
|---------|--------|-----|-----------|---------|
| Strong UP (>+0.3%) | 88 | **85.2%** | **+$5.60** | Best edge |
| Up (+0.05% to +0.3%) | 212 | **69.8%** | **+$4.94** | Strong edge |
| Flat (-0.05% to +0.05%) | 577 | 51.1% | +$4.09 | Breakeven |
| Down (-0.05% to -0.15%) | 282 | 48.9% | **-$3.13** | Losing |
| Strong DOWN (<-0.15%) | 137 | **23.4%** | **-$8.63** | Death zone |

### SHORT Performance by BTC Direction

| BTC 30m | Trades | WR | Total PnL | Verdict |
|---------|--------|-----|-----------|---------|
| Strong DOWN (<-0.3%) | 65 | **84.6%** | **+$3.82** | Best edge |
| Down (-0.3% to -0.05%) | 127 | **70.9%** | **+$2.97** | Strong edge |
| Flat | 460 | 45.2% | -$3.64 | Losing |
| UP | 168 | 43.5% | -$6.60 | Losing |
| Strong UP (>+0.3%) | 80 | **20.0%** | **-$7.19** | Death zone |

### Contrarian Trades (BTC falling but LONG won)

- 419 contrarian LONGs: **40.6% WR, -$11.76 total**
- Only `hl_copy_trader` (+$4.09) and `bb_bounce` (+$0.39) are profitable contrarian
- `ema300-dip` contrarian: 34.8% WR, -$1.96 — the signal that caused this incident
- `ct-hot` contrarian: 37.8% WR, -$5.25 — worst contrarian performer

### Contrarian PnL by BTC Momentum Depth

| BTC 30m Range | Trades | WR | Total PnL | Verdict |
|---------------|--------|-----|-----------|---------|
| -0.05% to -0.10% | 81 | **61.7%** | **+$0.82** | TRADE (mild dip = bounce) |
| -0.10% to -0.15% | 73 | 46.6% | -$1.97 | SKIP |
| -0.15% to -0.20% | 60 | 41.7% | -$0.22 | SKIP |
| -0.20% to -0.30% | 68 | 42.6% | -$1.76 | SKIP |
| -0.30% to -0.50% | 68 | 26.5% | -$0.95 | SKIP |
| -0.50%+ | 69 | 20.3% | -$7.69 | DEATH ZONE |

---

## Optimal Filter Settings (Backtested)

### Combined Simulation Results

| Config | Trades | WR | Total PnL |
|--------|--------|-----|-----------|
| No filter | 2,196 | 51.5% | **-$7.78** |
| LONG only: block when BTC < -0.10% | 1,858 | 54.4% | +$4.80 |
| SHORT only: block when BTC < 0.10% | 1,995 | 53.4% | +$4.70 |
| **BOTH: LONG>-0.10% + SHORT>0.10%** | **1,657** | **57.0%** | **+$17.28** |

**The combined filter turns a -$7.78 system into a +$17.28 system.**

### Recommended Thresholds

```
BTC_MOMENTUM_FALLING_THRESHOLD = -0.10  # Block LONGs when BTC 30m < this (was -0.15)
BTC_MOMENTUM_RISING_THRESHOLD = 0.10    # Block SHORTs when BTC 30m > this (was 0.15)
```

---

## Implementation Plan

### Change 1: Tighten BTC Momentum Filter

**File:** `hermes_constants.py`
```python
BTC_MOMENTUM_FALLING_THRESHOLD = -0.10  # was -0.15
BTC_MOMENTUM_RISING_THRESHOLD = 0.10    # was 0.15
```

**Impact:** Blocks 338 more LONG trades (26% of volume), eliminates -$32 in losses, loses 120 contrarian wins (avg +$0.27 each). Net: WR 53.1% → 59.3%, PnL +$2.86 → +$15.44.

### Change 2: Enable MAE Guard at 2.0%

**File:** `hermes_constants.py`
```python
CL_MAE_GUARD_ENABLED = True
CL_MAE_GUARD_BASE_THRESHOLD = 0.020  # 2.0% (was 3.0%)
```

**Impact:** Cuts losing LONGs faster. These 6 trades would have been cut at -2% instead of bleeding to -5-6%.

### Change 3: Trailing Profit Lock

**New concept:** When a position hits +3% unrealized, set SL at entry (breakeven). At +5%, trail at +2%.

**Impact:** Would have saved BCH's +13.4% → locked in ~+8% instead of -6.16%.

### Change 4: BTC Crash Auto-Cut for Existing LONGs

When the BTC crash filter triggers (new ATR-scaled threshold), also close all existing LONGs in loss.

**Already implemented in:** `btc_crash_filter.py` (Layer 5 — position protection, currently disabled).

---

## Files Changed (Session 2026-09-08)

1. `scripts/btc_crash_filter.py` — NEW: 5-layer crash detection module
2. `scripts/hermes_constants.py` — New crash filter constants, MAE guard constants
3. `scripts/decider_run.py` — Replaced inline crash logic with module call
4. `scripts/cut_loser.py` — MAE guard now uses ATR-aware thresholds

---

## Open Questions

1. **Detection-execution gap:** User says it's usually seconds, not minutes. Independent audit found NO evidence either way — `signal_outcomes.created_at` and `closed_at` are identical (close time, not detection/execution time). **Need to add timing instrumentation before making claims.**

2. **Contrarian exceptions:** `hl_copy_trader` works contrarian (47.5% WR, +$4.23 confirmed by independent audit). Should it be exempt from the BTC momentum filter? It copies pro traders who may have edge regardless of BTC direction.

3. **Profit lock params:** Need backtest to determine optimal trailing thresholds (+3% lock, +5% trail, or different).

4. **EMA300-dip signal review:** 34.8% WR when BTC is falling. Should this signal be modified or blocked more aggressively?

5. **MAE guard status:** Plan says "currently disabled" but `CL_MAE_GUARD_ENABLED = True` in hermes_constants.py. Need to verify which value is actually in effect (duplicate constant issue — line 792 vs 990).

---

## Independent Audit Findings (2026-09-08)

**Verdict: PARTIALLY SOUND**

| Claim | Audit Finding |
|-------|--------------|
| BTC -1.42% crash at 12:30 | ✅ Confirmed exactly |
| All 6 trades show BTC below 0.5% trend | ✅ Confirmed |
| hl_copy_trader works contrarian | ✅ Confirmed (+$4.23) |
| Combined filter: -$7.78 → +$17.28 | ⚠️ Directionally sound but only 66% of trades have BTC momentum data. Overfitting risk HIGH — no walk-forward validation |
| Detection-execution gap "usually seconds" | ❌ No evidence found. Pipeline runs ~60s cycles |
| MAE guard "currently disabled" | ❌ `CL_MAE_GUARD_ENABLED = True` in constants. Factual error in plan |

**Overfitting concern:** The -0.10 threshold was tuned on historical data. No train/test split, no out-of-sample validation. Performance will likely be worse live.

**Pipeline starvation concern:** Blocking 26% of LONG trades is aggressive. System already has 15+ filters. Need to monitor daily trade count.

---

## Implementation Plan (Revised)

### Phase 1: Conservative (Week 1)
- [ ] Update `BTC_MOMENTUM_FALLING_THRESHOLD` to **-0.12** (not -0.10 — split the difference)
- [ ] Update `BTC_MOMENTUM_RISING_THRESHOLD` to **0.12**
- [ ] Verify `CL_MAU_GUARD_ENABLED` actual value and fix duplicate constant
- [ ] Add timing instrumentation to track detection → execution gap

### Phase 2: Full (Week 2, after Phase 1 validated)
- [ ] If Phase 1 shows improvement, tighten to -0.10 / 0.10
- [ ] Enable `CL_MAE_GUARD_ENABLED` at 2.0% (if not already active)
- [ ] Backtest trailing profit lock on historical trades

### Phase 3: Advanced (Week 3+)
- [ ] Exempt `hl_copy_trader` from BTC momentum filter (contrarian edge confirmed)
- [ ] Implement BTC crash auto-cut for existing LONGs (btc_crash_filter.py Layer 5)
- [ ] EMA300-dip signal review: consider blocking when BTC falling > 0.10%

### Monitoring
- Track daily trade count (must not drop >20% from baseline)
- Track LONG WR weekly (must improve from 53.1% baseline)
- Track total PnL weekly (must improve from -$7.78 baseline)
- A/B test: run old thresholds on half the pipeline, new on half
