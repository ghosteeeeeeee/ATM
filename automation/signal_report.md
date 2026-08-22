# Signal Performance Report
**Generated:** 2026-08-22 22:00 UTC | **Period:** Last 6h + 24h + 7d

## Overall Stats
- **24h:** 46 trades, PnL: $-2.45
- **7d:** 234 trades, PnL: $-1.46
- **6h:** 0 trades (system quiet)

---

## KILLED (executed this report):

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| ct-hot+ | LONG | 32.7% | -$3.77 | 55T/7d | KILLED — parent flag COIN_TRACKER_HOT_ENABLED set False. PLUS/MINUS already False. Entire family dead. |
| ct-hot- | SHORT | 0.0% | -$0.09 | 2T/7d | Already killed (COIN_TRACKER_HOT_MINUS_ENABLED=False) |

**Note:** ct-hot+ was killed by auto_1hr earlier today (PLUS/MINUS=False). This report killed the parent flag COIN_TRACKER_HOT_ENABLED which was still True. Verified: line 1850 now reads `= False`.

---

## BOOSTED:

None. No signal meets boost criteria (WR>55%, PnL>$0.05, 5+ trades) with enough consistency across tokens.

---

## WINNERS:

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| hl_copy_trader | LONG | 60.0% | $2.05 | 40T/7d | Active — top performer |
| r2-trend-long6 | LONG | 100.0% | $0.29 | 4T/7d | Active — small sample |
| bb_bounce+,hl_copy_trader | LONG | 66.7% | $0.33 | 6T/7d | Active — combo winner |
| r2-trend-long4 | LONG | 71.4% | $0.22 | 14T/7d | Active — solid |
| r2-trend-long5 | LONG | 75.0% | $0.10 | 4T/7d | Active |
| r2-trend-long3 | LONG | 54.2% | $0.14 | 24T/7d | Active — high volume |
| return_exhaustion_long | LONG | 55.6% | $0.12 | 9T/7d | Active |

---

## LOSERS (watch list):

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2-trend-short2 | SHORT | 0.0% | -$0.22 | 3T/7d | Watch — low sample |
| range_breakout_short | SHORT | 0.0% | -$0.17 | 2T/7d | Watch — low sample |
| stop_hunt_reversal_long+ | LONG | 60.0% | -$0.04 | 10T/7d | Watch — break-even, NEVER_REENABLED |
| hl_copy_trader | SHORT | 0.0% | -$0.24 | 2T/7d | Watch — SHORT side weak |

---

## ISSUES:
- **No inversions found.** All signals respect direction labels.
- **24h net PnL is negative (-$2.45)** — system slightly bleeding. ct-hot+ LONG was the main drag (-$3.65/24h). Now killed.
- **7d net PnL is negative (-$1.46)** — mostly from ct-hot+ family (-$3.86 combined). Killing it should flip 7d to positive.
- **SHORT signals underperforming** — hl_copy_trader SHORT, r2-trend-short2, range_breakout_short all 0% WR. Consider blocking SHORT for these if pattern persists.

---

*Report auto-generated. Next report: ~6h from now.*
