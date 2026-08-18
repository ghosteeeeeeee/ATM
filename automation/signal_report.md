=== Signal Performance Report ===
Period: 2026-08-18 23:00 UTC — Last 6h / 24h / 7d
Generated: 2026-08-18 23:08 UTC

## Summary
- **24h**: 15 trades, all LONG, -$0.38 total PnL (46.7% WR)
- **7d**: 200+ trades across all signals. System slightly negative overall.
- **30d**: 1455 trades, -$3.20, 39% WR
- **Inversions**: PASS — no direction mismatches found (24h or 7d)

---

## KILLED (executed this cycle)

None — all previous losers already disabled.

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No new kills needed |

---

## PREVIOUSLY KILLED (confirmed still disabled)

| Signal | Dir | 7d WR | 7d PnL | Status |
|--------|-----|-------|--------|--------|
| ct-hot+ | LONG | 42.4% | -$0.42 | DISABLED — COIN_TRACKER_HOT_PLUS_ENABLED=False, NEVER_REENABLE |
| wave_catcher+ | LONG | 37.5% | -$0.42 | DISABLED — WAVE_CATCHER_PLUS_ENABLED=False, NEVER_REENABLE |
| range_breakout+ | LONG | 25.0% | -$0.41 | DISABLED — RANGE_BREAKOUT_PLUS_ENABLED=False, NEVER_REENABLE |
| accel-300- | SHORT | 55.0% | -$0.30 | NEVER_REENABLE (55% WR but net negative, inverted R:R) |
| hzscore+ | LONG | 25.0% | -$0.14 | DISABLED — NEVER_REENABLE |
| hzscore- | SHORT | 56.3% | -$0.14 | DISABLED — NEVER_REENABLE (inverted R:R) |
| continuation+ | LONG | 40.0% | -$0.17 | DISABLED — CONTINUATION_ENABLED=False |
| range_breakout_short | SHORT | 46.4% | -$0.21 | DISABLED — NEVER_REENABLE |
| inv-accel-300+ | LONG | 14.3% | -$0.31 | NEVER_REENABLE |
| inv-accel-300- | SHORT | 22.4% | -$0.30 | NEVER_REENABLE |

---

## WATCH LIST (tuning candidates)

| Signal | Dir | 7d WR | 7d PnL | Trades | Avg PnL | Notes |
|--------|-----|-------|--------|--------|---------|-------|
| r2-trend-long3 | LONG | 52.0% | -$0.23 | 25 | -$0.009 | High WR but inverted R:R — avg win small, avg loss large. Tuning candidate, not kill. |
| range_finder+ | LONG | 33.3% | -$0.14 | 9 | -$0.016 | DISABLED — R:R 0.12:1. Already killed. |
| mover+ | LONG | 28.6% | -$0.15 | 7 | -$0.021 | Momentum leaderboard — PLUS already killed. MINUS still active. |

---

## WINNERS (7d, >=5 trades)

| Signal | Dir | 7d WR | 7d PnL | Trades | Status |
|--------|-----|-------|--------|--------|--------|
| r2-trend-long2 | LONG | 64.7% | +$0.19 | 17 | ACTIVE — strong performer |
| bb_bounce+,hl_copy_trader | LONG | 42.9% | +$0.19 | 7 | ACTIVE |
| wave_catcher+ | SHORT | 42.9% | +$0.15 | 7 | KILLED (master switch) — SHORT was profitable but master killed |
| return_exhaustion_long | LONG | 55.6% | +$0.11 | 9 | ACTIVE |
| bb_bounce+ | LONG | 56.3% | +$0.09 | 16 | ACTIVE |
| r2-trend-long6 | LONG | 100.0% | +$0.20 | 4 | ACTIVE — small sample but perfect |

### 30d top performers (>=10 trades, WR>50%)

| Signal | Dir | 30d WR | 30d PnL | Trades |
|--------|-----|--------|---------|--------|
| bb_bounce+,range_finder+ | LONG | 58.5% | +$0.71 | 53 |
| bb_bounce | LONG | 57.1% | +$0.24 | 14 |
| r2-trend-long2 | LONG | 64.7% | +$0.19 | 17 |
| bb_bounce+ | LONG | 56.0% | +$0.17 | 25 |
| bb-bounce-short,hzscore- | SHORT | 61.1% | +$0.14 | 18 |

---

## ISSUES

1. **Low trade volume** — Only 15 trades in 24h. Market may be in consolidation.
2. **r2-trend-long3 inverted R:R** — 52% WR but -$0.23/7d. Wins average +$0.04, losses average -$0.08. Needs ATR SL tuning or profit target adjustment.
3. **No direction inversions** — system health OK.
4. **30d system slightly negative** — -$3.20 across 1455 trades. Edge is thin.

---

## ACTIONS TAKEN

- No kills executed (all losers already disabled)
- No boosts executed (winners already active)
- Report generated — next run in 6h
