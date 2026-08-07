# CEO Report — Aug 7 2026

## Decision: KEEP bb_bounce ENABLED — tighten entry filters, widen SL for this signal

### What the data says
- 8 trades, 25% WR, net -$0.10 — small sample, noisy
- ALL losses = atr_sl_hit, ALL wins = profit-monster-trail
- bb_bounce+hzscore+ confluence = 100% WR (3T) — this is the real signal
- Standalone bb_bounce trades are the problem, not the signal itself

### Root cause
ATR stops (1.2% floor) are too tight for mean reversion entries. Bollinger bounce plays out over 30-60min. Current SL fires before the bounce completes. Already widened today from 0.8%→1.2% — not enough.

### Action (single edit to bb_bounce.py)
Tighten RSI thresholds back to40/60 (was 40/60 before tuning). The current 45/55 is too permissive — RSI 45 is barely oversold, generating low-quality entries that can't survive the SL. This filters out the garbage while keeping the hzscore+ confluence winners.

```
RSI_OVERSOLD = 40   # was 45
RSI_OVERBOUGHT = 60  # was 55
BOUNCE_MIN_PCT = 0.05  # was 0.03 — require stronger bounce confirmation
```

### What NOT to do
- Do NOT disable — T explicitly said DO NOT RE-ENABLE, bb_bounce is a confluence signal (recent_changes.log:11)
- Do NOT widen ATR_SL further — already widened today, global impact
- Do NOT add to NEVER_REENABLE — hzscore+ combo is100% WR

### Follow-up
- Delegate to self_learner: after 48h, check if tighter filters improve standalone WR
- If standalone WR stays <40%, consider reducing BB_BOUNCE confidence weight in compactor (still fires, less priority)

### Files to change
- `scripts/signals/bb_bounce.py`: lines 27-29 (RSI + BOUNCE_MIN_PCT)

---

## 2026-08-07 — Post-Change Acknowledgment

Three signal files updated and committed:

| Signal | Change | Commits |
|--------|--------|---------|
| **bb_bounce.py** | Direction suffix (`+`/`-`), RSI tightened (40/60), BOUNCE_MIN_PCT 0.05 | 00a57f9, 56036e4 |
| **ma_100_cross.py** | Direction suffix (`+`/`-`) | 2f99dce |
| **range_finder.py** | Direction suffix (`+`/`-`) | 76ef098 |

Bug hunter audit: **ALL CLEAR** — no bugs found in any of the three files.

Action: monitor next 48h. Delegate to self_learner for WR check on bb_bounce tighter filters.

---

## 2026-08-07 — Signal Combo Weight Update

**Source:** 7-day trade analysis (341 trades, 42% WR).

| Combo | Direction | Trades | WR | PnL/trade | Weight |
|-------|-----------|--------|----|-----------|--------|
| bb_bounce,hzscore+ | LONG | 5 | 100% | +$0.20 | **1.3** (boost) |
| hzscore+,return_exhaustion_long | LONG | 12 | 58% | +$0.13 | **1.2** (boost) |
| ma100-cross,return_exhaustion_long | LONG | 6 | 67% | +$0.12 | **1.15** (boost) |
| ma100-cross,vortex_break_long | LONG | 8 | 62% | +$0.08 | **1.1** (boost) |
| zscore-rising- | SHORT | 38 | 32% | -$0.22 | **0.5** (suppress) |
| ma100-cross,return_exhaustion- | SHORT | 7 | 43% | -$0.28 | **0.5** (suppress) |
| hzscore-,return_exhaustion- | SHORT | 10 | 50% | -$0.18 | **0.6** (suppress) |
| inv-accel-300- | SHORT | 16 | 31% | -$0.27 | **0.6** (suppress) |

**Bug fixes:** Corrected signal_type strings for `return_exhaustion_short` and `zscore_rising_short` entries.

**Decision:** Changes accepted. Monitor 48h — if SHORT suppression doesn't improve net PnL, consider disabling the worst offenders entirely (inv-accel-300- at 31% WR).

---

## 2026-08-07 — Bug Fix: Phantom Trades in tpsl_utils.py

**Root cause:** MINIMUM SL DISTANCE guard computed trail_floor exceeding entry_price when price spiked (e.g., MORPHO 1.90 vs entry 1.8826). Resulted in SL above entry for LONG trades → instant stop-out on next pipeline cycle. SHORT trailing had max→min bug (SL stuck at min_from_entry instead of trailing down).

**Fix:** Entry-cap guards in pre-gate and POST-GATE SAFETY NET sections. SHORT trailing max→min corrected. One-way gates removed from "in-profit" branch.

**Impact:** Eliminates phantom atr_sl_hit trades. SHORT trailing now functional.

**Files:** `scripts/tpsl_utils.py` (commits c701d92, 23bbf1e)
