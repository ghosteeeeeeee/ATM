# Signal Performance Report
**Generated:** 2026-08-27 17:09 UTC | **Period:** Last 6h + 24h

---

## KILLED (executed this cycle)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Action |
|--------|-----|-------|--------|---------|--------|
| atr-spike+ | LONG | 7 | 28.6% | -$0.15 | DISABLED + NEVER_REENABLE |

**Reason:** WR<30% with 7+ trades, net PnL -$0.15. Also 7d: 7T 28.6% WR -$0.15.

---

## BOOSTED (executed this cycle)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Action |
|--------|-----|-------|--------|---------|--------|
| macd-div- | SHORT | 5 | 80.0% | +$0.24 | Weight 1.0 → 1.25 |

**Reason:** WR>55% with 5+ trades, net PnL +$0.24. Consistent performer.

---

## WINNERS (WR > 55%, PnL > 0, 24h)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| macd-div- | SHORT | 2 | 100% | +$0.07 | 5 | 80.0% | +$0.24 | ✅ BOOSTED |
| r2-trend-long4 | LONG | 2 | 50% | -$0.05 | 3 | 66.7% | +$0.01 | OK |

---

## LOSERS (WR < 30%, PnL < -$0.10, 24h)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|-------|--------|---------|--------|
| pump-catcher+ | LONG | 17 | 29.4% | -$0.35 | ALREADY KILLED (NEVER_REENABLE) |
| slow-grind- | SHORT | 4 | 25.0% | -$0.30 | ALREADY KILLED (NEVER_REENABLE) |
| atr-spike+ | LONG | 7 | 28.6% | -$0.15 | KILLED THIS CYCLE |

---

## MARGINAL (30-50% WR, 24h)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|-------|--------|---------|--------|
| bb-bounce-short | SHORT | 3 | 33.3% | -$0.14 | ENABLED — needs more data |

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## ACTIONS TAKEN

1. **KILL:** `ATR_SPIKE_PLUS_ENABLED = False` in hermes_constants.py (line 2056)
2. **NEVER_REENABLE:** Added `ATR_SPIKE_PLUS_ENABLED` to NEVER_REENABLE_FLAGS
3. **BOOST:** `macd-div-` SHORT weight 1.0 → 1.25 in signal_compactor.py (line 256)

---

## WATCH LIST

- `bb-bounce-short` SHORT — 3T, 33.3% WR, -$0.14. Low sample size. Monitor next cycle.
