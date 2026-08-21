=== Signal Performance Report ===
Period: Last 6h | 24h | 7d
Generated: 2026-08-21

## 24h Summary
- **18 trades, 61.1% WR, -$0.48 PnL**
- Volume significantly down (was 98 trades/day on Aug 12)

## 7d Summary
- **236 trades, 53.4% WR, -$1.47 PnL**

## KILLED (executed)
None — all kill candidates already disabled or stale (no trades in 7d).

## KILL CANDIDATES (already handled)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| wave_catcher+ | LONG | 37.5% | -$0.32 | 8 | DISABLED (Aug 17) |
| range_finder+ | LONG | 33.3% | -$0.24 | 9 | DISABLED (Aug 16) |
| mover+ | LONG | 16.7% | -$0.35 | 6 | STALE (last Aug 14) |
| ct-hot+ | LONG | 39.4% | -$0.57 | 33 | RE-ENABLED today (CEO_PROTECTED) |

## BOOSTED (executed)
None — winners already performing well, no param changes needed.

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2-trend-long6 | LONG | 100.0% | +$0.49 | 7 | ACTIVE — best performer |
| r2-trend-long4 | LONG | 64.7% | +$0.17 | 17 | ACTIVE |
| return_exhaustion_long | LONG | 66.7% | +$0.21 | 9 | ACTIVE |
| bb_bounce+,hl_copy_trader | LONG | 57.1% | +$0.30 | 7 | ACTIVE |
| r2-trend-long5 | LONG | 66.7% | +$0.08 | 6 | ACTIVE |
| wave_catcher+ | SHORT | 50.0% | +$0.09 | 6 | DISABLED (master killed) |

## ISSUES:
1. **CRITICAL: Trade volume collapsed 82% in 8 days** (98→18 trades/day). Signal generation healthy (hl_copy_plus: 209 signals today) but execution pipeline heavily filtered. Root causes: confluence gate, dead_hours, velocity filters, broad_market_z gate.

2. **No inversions found** — no direction mismatches detected.

3. **392 tokens in cooldown** — high cooldown count may be contributing to volume decline.

4. **r2-trend-long3 is the volume leader (31T/7d) but negative PnL (-$0.15)** — 54.8% WR but losses exceed wins. Fires on blacklisted tokens (ORDI, BABY, ZEN, PUMP, AIXBT, COMP all lost).

5. **CONTINUATION_ENABLED=True but PLUS/MINUS both False** — effectively dead. Consider setting master to False for clarity.

## DAILY TREND:
| Date | Trades | WR | PnL |
|------|--------|-----|-----|
| Aug 20 | 18 | 61.1% | -$0.48 |
| Aug 19 | 26 | 65.4% | +$0.58 |
| Aug 18 | 15 | 46.7% | -$0.35 |
| Aug 17 | 33 | 66.7% | +$0.28 |
| Aug 16 | 36 | 44.4% | -$0.52 |
| Aug 15 | 52 | 48.1% | -$0.19 |
| Aug 14 | 79 | 54.4% | -$0.65 |
| Aug 13 | 53 | 43.4% | -$1.69 |
| Aug 12 | 98 | 58.2% | +$0.56 |
