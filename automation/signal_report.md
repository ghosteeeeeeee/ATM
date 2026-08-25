# Signal Performance Report
**Generated:** 2026-08-25 17:00 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 1,417 | **WR:** 48.7% | **PnL:** -69.02%
- **Date range:** 2026-07-29 → 2026-08-25

---

## KILLED (executed this run)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| tl_break_short | SHORT | 28.6% | -$0.32 | 7 | DISABLED — added to NEVER_REENABLE_FLAGS |

---

## BOOSTED (executed this run)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+ | LONG | 66.7% | +$0.08 | 18 | STAY ENABLED — best performer |

---

## WINNERS (WR > 55%, PnL > 0, 24h)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+ | LONG | 66.7% | +$0.08 | 18 | ENABLED |

---

## LOSERS — KILLED (24h, all kill criteria met)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ct-hot+ | LONG | 0.0% | -$0.70 | 5 | Already killed (2026-08-24) |
| hl_copy_trader | SHORT | 25.0% | -$0.52 | 4 | Already killed (2026-08-25) |
| tl_break_short | SHORT | 28.6% | -$0.32 | 7 | **KILLED NOW** |

---

## WATCH LIST (negative PnL, not kill criteria yet)

| Signal | Dir | WR | PnL | Trades | Note |
|--------|-----|-----|-----|--------|------|
| hl_copy_trader | LONG | 40.0% | -$0.49 | 10 | High volume but negative PnL. Watch next 6h. |
| macd-div- | SHORT | 55.6% | -$0.46 | 9 | Good WR but poor R:R. Watch for PnL improvement. |

---

## ISSUES
- No signal inversions detected
- tl_break_short master flag (TL_BREAK_ENABLED) was True despite NEVER_REENABLE — fixed to False
- Current losers cluster around SHORT direction (3 of 5 negative signals are SHORT)
