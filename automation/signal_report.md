# Signal Performance Report
**Generated:** 2026-08-16 | **Period:** Last 6h + 24h

---

## KILLED (executed this run)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| wave_catcher- | SHORT | 25.0% | -$0.09 | 4 (6h) | Disabled WAVE_CATCHER_MINUS_ENABLED. Master already dead. |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2-trend-long2 | LONG | 68.8% | +$0.26 | 16 (24h) | ACTIVE — best performer |
| wave_catcher+ | SHORT | 42.9% | +$0.15 | 7 (24h) | ACTIVE — profitable SHORT |
| continuation+ | LONG | 66.7% | +$0.01 | 3 (24h) | ACTIVE |
| r2-trend-long2 | LONG | 100.0% | +$0.09 | 3 (6h) | ACTIVE |

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| wave_catcher+ | LONG | 37.5% | -$0.42 | 8 (24h) | DISABLED (already killed) |
| mover+ | LONG | 28.6% | -$0.15 | 7 (24h) | DISABLED (already killed) |
| r2-trend-long3 | LONG | 66.7% | -$0.12 | 9 (24h) | WATCH — high WR but negative PnL (inverted R:R) |
| r2-trend-long1 | LONG | 57.1% | -$0.02 | 7 (24h) | WATCH — marginal |
| wave_catcher- | SHORT | 25.0% | -$0.09 | 4 (24h) | DISABLED (this run) |

---

## ISSUES
- **No signal inversions found** — all trades match expected direction.
- **r2-trend-long3**: 66.7% WR but negative PnL = inverted R:R (avg win smaller than avg loss). Monitor for trailing SL tuning impact.
- All previously killed signals (wave_catcher+, mover+) remain dead.

---

## ACTIONS TAKEN
1. Disabled `WAVE_CATCHER_MINUS_ENABLED` (SHORT) — 25% WR, master switch already dead since 2026-08-16.
