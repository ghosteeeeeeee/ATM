# Signal Top Winners — 2026-05-07

All-time biggest wins from signal_outcomes DB, cross-referenced with signal combinations.

## Top 20 All-Time Wins

| Token | Dir | Signal | Peak% | Key Co-signal |
|-------|-----|--------|-------|---------------|
| ORDI | SHORT | hzscore,pct-hermes- | +873% | pct-hermes- (extreme overbought) |
| APE | LONG | hzscore-,momentum+,vel-hermes+ | +858% | 3-signal confluence |
| GRIFFAIN | LONG | accel-300+,rs-s150,trend_purity+ | +526% | rs-s150 (150 touches) |
| AVNT | SHORT | hzscore,pct-hermes | +508% | hzscore+pct-hermes |
| ETH | LONG | hzscore,pct-hermes,vel-hermes | +505% | 3-signal confluence |
| TAO | LONG | hl_reconcile | +505% | phantom/hl_reconcile |
| DASH | LONG | accel-300+,momentum,mtf-macd,rsi | +480% | multi-timeframe |
| PURR | LONG | accel-300+,rs-s48 | +474% | rs-s48 (proven support) |
| MEME | LONG | ma-golden14,rs-s162 | +420% | rs-s162 + ma-golden14 |
| DASH | LONG | accel-300+ | +406% | bare accel (smaller win) |
| DYM | LONG | gap-300+,pct-hermes+,zscore-momentum+ | +350% | gap + pct-hermes+ + zscore |
| DASH | LONG | accel-300+,rs-s72 | +344% | rs-s72 |
| S | LONG | accel-300+,rs-s16 | +307% | rs-s16 (low-touch, valid) |
| DOT | SHORT | oc-zscore-v9-,zscore-momentum- | +256% | oc-zscore-v9- |
| VVV | LONG | accel-300+,ma-golden10,rs-s46,trend_purity+ | +213% | multi-co-signal |

## RS Touch Count — The Quality Filter

RS signals have a touch_count parameter encoded in the source (e.g., rs-s48 = support touched 48 times).

**accel-300+ + rs-s{touch_count} performance by touch range:**

| Touch Count | Trades | WR | Avg Peak | Verdict |
|-------------|--------|-----|---------|---------|
| rs-s16 to rs-s150 | 11 | 100% | +343% | GOLD ZONE |
| rs-s150+ | 4 | 75% | +175% | Still profitable |
| rs-s < 16 | ~8 | 0% | catastrophic | Too weak |
| rs-s > 300 | ~5 | 0% | -72% to -90% | Stale, ignore |

**Key finding**: The touch_count range of 16-150 is the "structural support" sweet spot.
Below 16 touches = immature/weak level. Above 150 = stale level price has outgrown.
The touch_count IS encoded in the source field (rs-s48, rs-s72, etc.) and IS visible
in signal_outcomes winners.

## RS Signal Architecture

- `RS_SOURCE_PREFIX = 'rs'` — produces `rs-s{touch_count}` and `rs-r{touch_count}`
- `RS_SIGNAL_TYPE = 'support_resistance'` (PROBLEM: not parseable by _extract_signal_parts)
- `RS_MIN_TOUCHES = 5` — minimum touches to be a valid level
- `RS_LOOKBACK_CANDLES = 4700` — ~3 days of 1-min candles
- `RS_COOLDOWN_HOURS = 4` — max 6 firings per token per day
- `_RS_ATR_BAND_SOFT_MIN = 0.30`, `_RS_ATR_BAND_SOFT_MAX = 0.60` — **OVERLY RESTRICTIVE**

**Why RS doesn't fire**: The ATR band filter rejects anything 0.00-0.30 ATRs from a level
("too close — could be AT the level") or >0.60 ATRs ("comfortably outside"). But in trending
markets, price is frequently within 0.30 ATR of a level — these valid bounce setups are
silently rejected. Fix: raise _RS_ATR_BAND_SOFT_MAX to 1.0 or remove the upper bound.

**RS source field IS correct**: rs.py line 383 sets `source = 'rs-s{touch_count}'` which
IS the format found in signal_outcomes winners. Only the `signal_type = 'support_resistance'`
is unparseable by `_extract_signal_parts()`.

## Top SHORT Signal Winners (regime-dependent)

| Signal | Trades | WR | Avg Peak | Best Trade |
|--------|--------|-----|---------|-----------|
| hwave+,hzscore+ | 4 | 50% | +27.4% | AXS +153% (DISABLED) |
| oc-zscore-v9-,zscore-momentum- | 16 | 25% | +26.1% | DOT +256% |
| ma-cross-5m-short,zscore-short | 26 | 38% | +21.9% | CAKE +372% |
| hzscore+,pct-hermes- | 10 | 20% | +460% best | ORDI +873% (outlier) |

**hwave was disabled April 18** — biggest gap in SHORT arsenal. When regime shifts back
to mean-reversion, hwave+,hzscore+ may work again.

## Best LONG Signal Winners (current bullish regime)

| Signal | Trades | WR | Avg Peak | Best Trade |
|--------|--------|-----|---------|-----------|
| accel-300+,rs-s(16-150) | 11 | 100% | +343% | GRIFFAIN +526% |
| accel-300+,momentum,mtf-macd,rsi | 1 | 100% | +480% | DASH |
| hzscore-,momentum+,vel-hermes+ | 22 | 27% | +7.8% | APE +859% |
| gap-300+,pct-hermes+,zscore-momentum+ | ~5 | 50% | +260% | DYM +350% |

## Key SQL for Winners Analysis

```sql
-- Top winners by peak pnl
SELECT token, direction, signal_type, ROUND(MAX(pnl_pct),2) as peak_pnl
FROM signal_outcomes WHERE is_win=1
GROUP BY token, direction, signal_type
ORDER BY peak_pnl DESC LIMIT 40;

-- accel-300+ RS combos (verify touch_count in source)
SELECT token, source, pnl_pct FROM signal_outcomes
WHERE signal_type LIKE '%accel%' AND source LIKE '%rs-s%'
ORDER BY pnl_pct DESC LIMIT 20;

-- RS touch_count breakdown
SELECT source, COUNT(*) cnt, AVG(pnl_pct) avg_pnl,
       SUM(is_win) wins, ROUND(100.0*SUM(is_win)/COUNT(*),1) wr
FROM signal_outcomes
WHERE source LIKE 'rs-s%'
GROUP BY source ORDER BY cnt DESC LIMIT 20;
```
