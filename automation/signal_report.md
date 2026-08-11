# Signal Performance Report
**Generated:** 2026-08-11 13:48 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 3330 | **Last 24h:** 37 trades, -$0.13 PnL, 40% WR
- **Date range:** 2026-05-20 → 2026-08-11

---

## KILLED (executed)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Action |
|--------|-----|-------|--------|---------|--------|
| bb_bounce+,hzscore+ | LONG | 13 | 23.1% | -$0.33 | **COSIG-GATE blocked** — poison combo, 23% WR hemorrhaging |

**Method:** Added poison block in `signal_compactor.py:613-615` — blocks `bb_bounce+ + hzscore+` LONG at signal creation time. Individual components (`bb_bounce+`, `hzscore+`) remain enabled for other profitable combos.

---

## WINNERS (WR > 55%, PnL > 0, 24h)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Avg PnL |
|--------|-----|-------|--------|---------|---------|
| hzscore-,range_breakout- | SHORT | 2 | 100% | +$0.10 | +$0.050 |
| hzscore-,vortex_break_short | SHORT | 2 | 50% | +$0.07 | +$0.035 |
| ht_sig6 | LONG | 1 | 100% | +$0.11 | +$0.110 |
| continuation+,range_breakout+ | LONG | 1 | 100% | +$0.08 | +$0.080 |

**7d top performers:**
- `bb_bounce+,range_finder+` LONG: 53T, 58.5% WR, +$0.71 — system workhorse
- `bb_bounce` LONG: 14T, 57.1% WR, +$0.24
- `bb_bounce,hzscore+` LONG: 5T, 100% WR, +$0.20 (note: different from `bb_bounce+,hzscore+` which is now blocked)
- `continuation+,hzscore+` LONG: 7T, 42.9% WR, +$0.20

---

## LOSERS — WATCH LIST (24h)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|-------|--------|---------|--------|
| hzscore+,range_finder+ | LONG | 1 | 0% | -$0.13 | WATCH — 1 trade, needs data |
| range_breakout+,rs-s52 | LONG | 1 | 0% | -$0.10 | WATCH — 1 trade |
| hl_copy_trader,range_breakout- | SHORT | 2 | 50% | -$0.04 | WATCH — needs more data |
| bb-bounce-short,hzscore- | SHORT | 2 | 50% | -$0.02 | WATCH — 7d is +$0.12 |

**7d losers to watch:**
- `ma100-cross,return_exhaustion-` SHORT: 7T, 42.9% WR, -$0.28 — bleeding
- `ma100-cross-,range_finder-` SHORT: 5T, 40% WR, -$0.19
- `hzscore-,return_exhaustion-` SHORT: 10T, 50% WR, -$0.18 — 50% WR but negative PnL = asymmetric losses

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## ISSUES

- `bb_bounce+,hzscore+` LONG collapsed today: 25% WR (4T, -$0.09 today alone). 7d was +$0.20 but recent cluster of losses triggered kill.
- No open trades except stale `ht_sig4` LONG (HTTST4, opened Aug 10 20:03 UTC) — may need manual close.

---

*Report generated 2026-08-11 13:48 UTC. Next report: ~6h.*
