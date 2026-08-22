=== Signal Performance Report ===
Generated: 2026-08-22 11:10 UTC

Period: Last 6h | 24h | 7d

KILLED (executed):
| Signal              | Dir  | WR    | PnL    | Trades | Action                    |
|---------------------|------|-------|--------|--------|---------------------------|
| COIN_TRACKER_HOT-   | SHORT| 0.0%  | -$0.17 | 3 (7d) | Set False (was True)      |

ALREADY KILLED (today):
| Signal              | Dir  | WR    | PnL    | Trades | Action                    |
|---------------------|------|-------|--------|--------|---------------------------|
| COIN_TRACKER_HOT+   | LONG | 28.1% | -$4.02 | 32 (24h)| Killed 09:00 UTC by auto_1hr|

WATCH LIST (no action — too few trades):
| Signal              | Dir  | WR    | PnL    | Trades | Status                    |
|---------------------|------|-------|--------|--------|---------------------------|
| hl_copy_trader      | SHORT| 0.0%  | -$0.13 | 1 (24h)| Insufficient data         |
| r2-trend-short2     | SHORT| 0.0%  | -$0.22 | 3 (7d) | Low volume, monitor       |
| ct-hot-             | SHORT| 0.0%  | -$0.17 | 3 (7d) | NOW DISABLED              |

WINNERS:
| Signal              | Dir  | WR    | PnL    | Trades | Status                    |
|---------------------|------|-------|--------|--------|---------------------------|
| hl_copy_trader      | LONG | 56.3% | +$1.38 | 32 (24h)| ACTIVE — top performer    |
| hl_copy_trader      | LONG | 58.5% | +$2.05 | 41 (7d) | ACTIVE — consistent       |
| r2-trend-long4      | LONG | 71.4% | +$0.22 | 14 (7d) | ACTIVE — high WR          |
| r2-trend-long3      | LONG | 54.2% | +$0.14 | 24 (7d) | ACTIVE — high volume      |
| r2-trend-long6      | LONG | 100%  | +$0.29 | 4 (7d)  | ACTIVE — perfect WR       |
| return_exhaustion   | LONG | 55.6% | +$0.12 | 9 (7d)  | ACTIVE                    |
| bb_bounce+          | LONG | 66.7% | +$0.33 | 6 (7d)  | ACTIVE                    |

ISSUES:
- No direction inversions found (3d check)
- CT-HOT family 62T/7d 32.3% WR -$4.04 total — worst family by far
  - ct-hot+ LONG killed (32T/24h, 28.1% WR, -$4.02)
  - ct-hot- SHORT killed (3T/7d, 0% WR, -$0.17)
  - Master switch COIN_TRACKER_HOT_ENABLED still True (CEO_PROTECTED)
- System activity very low today — BTC crash at 05:08 UTC likely chilling signals
- 24h total: 64 closed trades, ~$-2.64 net

SUMMARY:
- 1 signal killed (ct-hot- SHORT)
- 1 signal already dead (ct-hot+ LONG, killed earlier today)
- 0 signals boosted (winners already enabled)
- 0 inversions found
- Net 24h: negative (ct-hot family dragging system)
