# Signal Performance Report
**Generated:** 2026-08-29 05:08 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **24h:** 78 trades | WR: 52.6% | PnL: +$0.60
- **7d:** 437 trades | WR: 49.0% | PnL: -$5.20
- **7d (excl dead signals):** 349 trades | WR: 51.9% | PnL: -$0.41

---

## KILLED (executed)

None. No signals meet kill criteria (WR<30%, 5+ trades, 24h).

---

## BOOSTED (executed)

None. No signals meet boost criteria (WR>55%, 5+ trades, PnL>$0.05, 24h).

---

## WINNERS (24h)

| Signal | Dir | Trades | WR | PnL | Avg | Status |
|--------|-----|--------|-----|-----|-----|--------|
| accel-300-v2- | SHORT | 50 | 52.0% | +$0.89 | +$0.02 | ENABLED — workhorse |
| confluence-,engulfing-,r2-trend-short3 | SHORT | 1 | 100% | +$0.07 | +$0.07 | ENABLED |
| r2-trend-long3,rs-s142,rs-s155,rs-s47 | LONG | 1 | 100% | +$0.05 | +$0.05 | ENABLED |
| accel-300-v2-,rs-r190 | SHORT | 1 | 100% | +$0.04 | +$0.04 | ENABLED |
| bb-bounce-short | SHORT | 17 | 58.8% | +$0.06 | +$0.00 | ENABLED — consistent |
| macd-div- | SHORT | 2 | 50.0% | +$0.01 | +$0.01 | ENABLED — needs data |

---

## LOSERS (24h)

| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| accel-300-v2-short- | SHORT | 2 | 0% | -$0.19 | Low sample, watch |
| accel-300-v2-,rs-r156 | SHORT | 1 | 0% | -$0.12 | Low sample |
| accel-300-v2-,confluence-,rs-r52 | SHORT | 1 | 0% | -$0.11 | Low sample |
| accel-300-v2-,confluence-,rs-r102 | SHORT | 1 | 0% | -$0.11 | Low sample |

All losers are single-trade noise. No kill candidates.

---

## DEAD SIGNALS (historical bleed, now stopped)

| Signal | Last Trade | 7d WR | 7d PnL | Status |
|--------|-----------|-------|--------|--------|
| ct-hot+ | Aug 24 | 37.1% | -$1.09 | Kill switch WORKING (no trades since Aug 24) |
| hl_copy_trader | Aug 25 | 40.4% | -$1.02 | Stopped (no trades since Aug 25) |
| slow-grind- | — | 33.3% | -$0.64 | Already killed in constants |
| pump-catcher+ | — | 33.3% | -$0.39 | Already killed in constants |

**System 7d without dead signals: 51.9% WR, -$0.41** (vs 49.0% / -$5.20 with them).

---

## ISSUES

- **98.7% ATR_SL exit rate (24h):** Only 1 TP hit in 78 trades. System is cutting losses but barely capturing gains. PM_TRAIL should be catching winners — investigate if PM_TRAIL activation threshold (0.40%) is too high for current vol regime.
- **atr-spike+ still firing** despite being in NEVER_REENABLE_FLAGS — 6T/48h 16.7% WR, -$0.18. Verify kill switch is actually blocking at add_signal() level.

---

## SIGNAL INVERSIONS

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] ATR_SL dominance** — 98.7% of exits are stop losses. PM_TRAIL may need activation threshold lowered from 0.40% to capture more winners.
2. **[MONITOR] accel-300-v2-** — 50T/24h, 52% WR, +$0.89. Healthy but borderline WR. Watch for decay.
3. **[MONITOR] bb-bounce-short** — 17T/24h, 58.8% WR, +$0.06. Consistent, low avg PnL. Keep enabled.

---

*Report auto-generated. Next report: ~6h from now.*
