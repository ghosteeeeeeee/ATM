# Signal Performance Report

**Period:** Last 6h | 24h  
**Generated:** 2026-09-07 04:00 UTC

---

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| coil-spring+ | LONG | 38.5% | -$0.62 | 13 | **KILLED** — 5 consecutive losses, main signal already dead |

**Changes:**
- `COILED_SPRING_TRIGGER_LONG_ENABLED = False` (was True)
- `COILED_SPRING_TRIGGER_LONG_PLUS_ENABLED = False` (was True)

---

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 77.8% | +$0.28 | 9 | **BOOST** — strong performer, 77.8% WR |

**Note:** No confidence weight changes needed — signal already performing well.

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| slow-grind+ | LONG | 35.7% | -$0.88 | 14 | **WATCH** — 6 consecutive losses, borderline kill (WR 35.7% > 30% threshold) |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 100% | +$0.11 | 4 | Good — below 5-trade threshold for boost |
| bb-bounce-v2-long+ | LONG | 77.8% | +$0.28 | 9 | **STRONG** — consistent winner |
| open-skies+ | LONG | 100% | +$0.02 | 1 | Insufficient data |
| liq-hunt+ | LONG | 100% | +$0.04 | 1 | Insufficient data |

---

## ISSUES

- **slow-grind+ borderline:** WR 35.7% (above 30% kill threshold) but 6 consecutive losses. Monitor closely — if WR drops below 30% with 5+ trades, kill immediately.
- **No signal inversions detected** — all signals firing correct directions.

---

## Summary

| Metric | Value |
|--------|-------|
| Signals killed | 1 (coil-spring trigger) |
| Signals boosted | 0 (bb-bounce-v2 already strong) |
| Watch list | 1 (slow-grind+) |
| Inversions | 0 |
| Net PnL (24h) | -$1.07 (slow-grind+ -$0.88, coil-spring+ -$0.62, offset by winners) |
