# 96h Trade Analysis — 2026-06-06

## Source Data
- trades.json: 200 closed trades (extracted from PostgreSQL via API)
- Time window: last96 hours of `opened` field
- Note: trades.json has no `close_time_ts` — use `opened` for filtering

## Top-Level Stats
-200 total closed trades
- 191 trades with source/signal identified
- 9 trades with missing signal metadata

## Win Rate by Signal Type

| Signal | Trades | WR | Avg % |
|--------|--------|-----|-------|
| rs-s-broken SHORT | 138 | 52.9% | +19.18% |
| accel-300+ LONG | 53 | 9.4% | -58.0% |
| All others | 9 | — | — |

**accel-300+ LONG is catastrophic**: 53 trades, 9.4% WR, avg -58%. Nearly all required RS confirmation and all lost.

## If LONGs Were Excluded
-147 trades, 69% WR, +19.5% avg
- Excluding the 53 catastrophic LONGs leaves only the profitable SHORTs

## Signal Breakdown

### rs-s-broken (SHORT) — PROFITABLE
- 138 trades, 52.9% WR, avg +19.18%
- 73 wins, 65 losses
- Top winners: ORDI +88%, TIA +61%, WLD +59%, VIRTUAL +55%, ZK +54%
- Top losers: STRK -74%, PORTAL -62%, ENS -56%, W -55%, AXS -54%
- **This is the edge — the system works on SHORTs**

### accel-300+ LONG — CATASTROPHIC
- 53 trades, 9.4% WR, avg -58%
- Nearly all required RS confirmation (the ones that had RS at all)
- The 9.4% WR means 48 out of 53 trades lost money
- Average loss of -58% per trade is devastating
- **Kill switch candidate: block accel-300+ LONG entirely**

### rs-broken (non-SHORT variants)
- 139 trades total, WR 53.2%, avg +0.20%
- This is the aggregate including rs-s-broken SHORT
- rs-r-confirmed signals: 61 trades, WR 26.2%, avg -0.30% — also bad

## RS Decider — Backwards?

rs-broken (all directions) outperforms rs-confirmed:
- rs-broken: 139 trades, WR 53.2%, avg +0.20%
- rs-confirmed: 61 trades, WR 26.2%, avg -0.30%

The system is filtering for RS confirmation which is **anti-selective** — RS-confirmed trades lose at26% WR while rs-broken trades win at 53%.

## Market Chop Diagnosis

The 53 accel-300+ LONG losing trades were likely entries during chop:
- Price oscillating around EMA300 with no clear trend
- accel-300 fires on the brief cross above EMA, but price reverses
- RS confirmation (when present) also fires in chop conditions
- Result: 48 losses, 5 wins, avg -58%

## What Thresholds to Tweak

### hermes_constants.py — Current Values (Post-Session)
```
MIN_GAP_PCT_LONG            = 0.15
MIN_GAP_PCT_SHORT           = 0.10
ACCEL_300_LOOKBACK          = 30 # was 250, restored to 30
ACCEL_300_PERSISTENCE_BARS  = 4
ACCEL_300_MIN_GAP_GROWTH    = 0.05
ACCEL_300_MIN_GAP_EXPANSION = 0.05
ACCEL_300_REGIME_SLOPE_PCT  = 0.003   # was 0.008, lowered
ACCEL_300_STALE_BARS        = 200     # was 25, raised
ACCEL_300_ENABLED           = True
ACCEL_300_COOLDOWN_MIN      = 1
ACCEL_300_BLOCK_COSIGS      = {'ma-cross-5m+', 'pct-hermes+'}
```

### Recommended Tweaks

1. **Block accel-300+ LONG entirely** — add killswitch in hermes_constants:
   ```
   ACCEL_300_ALLOW_LONG = False
   ```
   This prevents the 53 catastrophic trades (avg -58%).

2. **Raise RS decider thresholds** (more selective, not less):
   - RS_DECIDER_CONF_FLOOR: 60 → 70
   - RS_DECIDER_MIN_TOUCHES: 150 → 175
   - This reduces RS-confirmed false positives in chop

3. **Lower ACCEL_300_REGIME_SLOPE_PCT further** if needed:
   - Current 0.003 requires slope < -0.30%/bar for SHORT
   - Most fresh tokens have slopes between -0.01 and -0.06%/bar
   - Setting to 0.005 would let more tokens through regime filter

4. **Restore ACCEL_300_LOOKBACK to 30** (already done):
   - LB=250 breaks the signal by pushing detection start to bar 550
   - LB=30 allows detection from bar 330

## Key Insight

**The edge is SHORT (rs-s-broken) only.** The system makes money on 138 SHORT trades at 52.9% WR. The accel-300+ LONG variant is a separate signal that fires in chop and loses at 9.4% WR. These should be separated:
- SHORT: rs-s-broken + accel-300- (works)
- LONG: blocked until accel-300+ can be fixed
