# Profitability Fix Plan — October 2026

**Date:** 2026-10-07
**Status:** Analysis complete, recommendations pending CEO approval
**Context:** System has been losing money for months. BTC went from 80k→90k in 24hrs but only 2 trades went according to plan. Need fundamental improvements to entry timing and signal quality.

---

## Executive Summary

The system detects pumps correctly but executes too late. Signals fire AFTER the big candle (the reversal candle), not during the accumulation before it. Winners (APT +23.9%, LTC +13.6%) entered DURING the dump; losers entered AFTER the dump was already over.

**Root cause:** The pump-chain signal detects the SPIKE. We need it to detect the GRIND before the spike.

---

## Key Findings

### 1. Entry Timing Is the Core Problem

Traced price action for all pump-chain trades (last 3 days):

| Trade | 30min Before | 60min After | Pattern |
|-------|-------------|-------------|---------|
| APT +23.9% | -0.58% (dumping) | -4.67% (continued) | ✅ EARLY — caught the dump |
| LTC +13.6% | 0.00% (flat) | -0.33% (slow bleed) | ✅ GOOD entry |
| IO -3.1% | -1.27% (already dumped) | +0.29% (bounced) | ❌ LATE — move done |
| LDO -1.6% | -1.09% (already dumped) | -0.67% (bounced) | ❌ LATE — move done |
| INJ -1.4% | +0.08% | +1.06% (went up) | ❌ Wrong direction |

**Winners entered BEFORE the dump. Losers entered AFTER the dump was over.**

### 2. Entry Conditions Are Not the Problem

RSI × BB analysis shows winners and losers have SIMILAR entry conditions:
- Both have RSI 13-40, BB 0.08-0.35
- The difference is TIMING, not entry quality
- Wider stops won't help — we need earlier detection

### 3. Velocity Filters Help Marginality

| Filter | Threshold | Allowed WR | Improvement |
|--------|-----------|------------|-------------|
| None (baseline) | — | 48.0% | — |
| 30m velocity | 3.0% | 51.5% | +3.5% |
| 5m velocity | 0.5% | 52.0% | +4.0% |

The 5m velocity filter at 0.5% blocks trades where token already moved >0.5% in 5min. This catches some "late" entries but doesn't solve the core timing problem.

### 4. SHORT Signals Were Mass-Blocked

- **505 pump-chain SHORT signals expired** in 24h
- **Root cause:** SHORT-CONTINUUM filter (BTC score > 40 blocks SHORTs)
- **Fix applied:** Raised SHORT_CONTINUUM_SCORE_MAX from 40 to 60
- BTC was neutral (score 43-55), blocking all SHORTs despite philosophy "every dump is a SHORT opportunity"

### 5. Hard Max Loss Too Tight

| Leverage | CUT_LOSER_PNL | HARD_MAX_LOSS_PCT (price) | Actual exit price move |
|----------|---------------|---------------------------|----------------------|
| 5x | -1.00% | -0.20% | +0.28% to +1.11% |
| 3x | -1.00% | -0.33% | +0.54% to +1.18% |

The hard_max_loss fires at -0.20% price move (5x leverage), but actual exits happen at +0.28% to +1.11% due to slippage. Winners need room to run.

### 6. BTC Oscillator Data Coverage Is Insufficient

- Only **12.6% of trades** (660/5,235) have BTC continuum data matched
- Continuum.db only covers Sep 4-21 (17 days)
- Any oscillator-based filter is validated on a tiny, recent subset
- **Need to backfill continuum.db to cover full trading history**

---

## Recommendations

### Priority 1: Move-Done Filter (Quick Win)

Add 5m velocity filter to pump-chain signal:

```python
# In pump_flow_signal.py, after existing velocity checks
PUMP_FLOW_MOVE_DONE_THRESHOLD = 0.5  # 5m velocity threshold

if direction == 'SHORT' and token_5m_vel < -PUMP_FLOW_MOVE_DONE_THRESHOLD:
    continue  # token already dumped in 5min — move likely over
if direction == 'LONG' and token_5m_vel > PUMP_FLOW_MOVE_DONE_THRESHOLD:
    continue  # token already pumped in 5min — pullback likely
```

**Expected impact:** +4.0% WR improvement (48% → 52%)
**Risk:** Blocks 20 winners out of 125 (16% miss rate)
**Status:** Constant added, filter code added, needs testing

### Priority 2: Widen Hard Max Loss

Change `CUT_LOSER_PNL` from -1.00 to -2.50:

```python
CUT_LOSER_PNL = -2.50  # was -1.00
```

**Expected impact:** Gives trades 2.5x more room before stop triggers. Allows APT/LTC-type winners to develop.
**Risk:** Larger losses on real losers. Need to monitor.
**Status:** Pending CEO approval

### Priority 3: Grind Detection (Long-term)

Build a signal that detects the GRIND phase before the spike:

**Grind characteristics:**
- Low ATR (< 0.15% of price)
- Tight range (< 0.5% over 60 candles)
- Rising MA180 slope (positive linreg)
- Volume declining (accumulation, not distribution)

**Entry trigger:**
- Volume spike (> 2.5x 30-bar average)
- Bullish candle (close > open)
- Close breaks above range high

**This is what the BTC grind spike signal was designed for. Need to adapt it for pump-chain.**

**Status:** Conceptual, needs design

### Priority 4: Backfill Continuum DB

Extend continuum.db to cover full trading history (May-Sep):

**Current coverage:** Sep 4-21 only (17 days)
**Needed:** May 20 - Oct 7 (140 days)

**Without this, any oscillator-based filter is validated on 12.6% of trades.**

**Status:** Not started

---

## What We Already Fixed

| Change | Date | Impact |
|--------|------|--------|
| SHORT_CONTINUUM_SCORE_MAX 40→60 | Oct 6 | Unblocks SHORT signals in neutral zones |
| PUMP_CHAIN_V5 re-enabled | Oct 4 | Restores 68.3% WR bare form |
| pump-chain+/- and mover+/- re-enabled | Sep 22 | All signals active in all regimes |
| CHASE_GAP_MAX_PCT 1.0→3.0 | Sep 21 | Allows valid pumps despite pipeline latency |
| Continuum override in chop gate | Sep 21 | BTC structure overrides velocity-based chop |
| btc_grind_spike signal created | Sep 18 | Detects grind→spike pattern (untested) |

---

## Data Limitations

1. **Continuum DB coverage:** 12.6% of trades — need backfill
2. **RSI/BB data:** Only 25.4% of trades have entry_rsi_14 and entry_bb_position
3. **Sample sizes:** Many analysis buckets have <30 trades — not statistically significant
4. **Temporal bias:** All oscillator analysis is from Sep 4-21 only

---

## Monitoring Plan

After implementing Priority 1 and 2:

1. **Track pump-chain WR** — should improve from 48% to 52%
2. **Track hard_max_loss frequency** — should decrease as trades get more room
3. **Track big winners** — should see more APT/LTC-type trades (+10%+ PnL)
4. **Monitor for 48 hours** — if WR drops below 45%, revert changes

---

## Open Questions for CEO

1. **Priority 1 (move-done filter):** Approve the 0.5% 5m velocity threshold? Or adjust?
2. **Priority 2 (widen cut-loser):** Approve CUT_LOSER_PNL -1.00 → -2.50? Or different value?
3. **Priority 3 (grind detection):** Should we invest time in building this, or focus on other improvements?
4. **Priority 4 (backfill continuum):** How important is oscillator data for future filters?

---

## Files Changed

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | SHORT_CONTINUUM_SCORE_MAX=60, PUMP_FLOW_MOVE_DONE_THRESHOLD=0.5, CUT_LOSER_PNL unchanged |
| `scripts/signals/pump_flow_signal.py` | Added move-done filter (5m velocity) |
| `scripts/signals/btc_grind_spike.py` | New signal (untested) |
| `scripts/signal_compactor.py` | Continuum override in chop gate |
| `scripts/chop_detector.py` | Continuum override in chop detector |
| `data/continuum.db` | Needs backfill |
