# Closed Trade Analysis — 2026-05-21 Session Findings

**Archive DB:** `/root/.hermes/archive/trades_analysis.db`
**Schema:** `trades` (with columns: id, token, direction, entry_price, exit_price, pnl_pct, signal, confidence, leverage, entry_rsi_14, entry_macd_hist, entry_regime_4h, entry_trend, entry_slope_4h, close_reason, exit_reason, open_time, close_time, and many more including _signal_* prefixed fields)

## Key Query Patterns

```sql
-- Basic losing trade analysis
SELECT token, direction, pnl_pct, signal, close_reason, 
  ROUND((julianday(close_time) - julianday(open_time)) * 1440, 1) as dur_min
FROM trades WHERE close_reason = 'atr_sl_hit' AND pnl_pct < -0.3
ORDER BY close_time DESC;

-- Signal combos ranked by avg PnL (min 3 trades)
SELECT signal, COUNT(*) as cnt, AVG(pnl_pct) as avg, SUM(pnl_pct) as total
FROM trades WHERE pnl_pct IS NOT NULL
GROUP BY signal HAVING COUNT(*) >= 3
ORDER BY avg;

-- Close reason breakdown
SELECT close_reason, COUNT(*) as trades, AVG(pnl_pct) as avg, SUM(pnl_pct) as total
FROM trades WHERE pnl_pct IS NOT NULL AND close_reason IS NOT NULL
GROUP BY close_reason ORDER BY total;

-- Direction + market slope analysis
SELECT 
  CASE WHEN entry_slope_4h > 0.0001 THEN 'UP_SLOPE'
       WHEN entry_slope_4h < -0.0001 THEN 'DOWN_SLOPE'
       ELSE 'FLAT' END as slope_bucket,
  direction, COUNT(*) as trades, AVG(pnl_pct) as avg
FROM trades WHERE pnl_pct IS NOT NULL
GROUP BY 1, 2 ORDER BY avg;
```

## Findings Summary

### The Two Loss Sources
1. **atr_sl_hit** — 620 trades, avg -0.28%, total -$172.54. Systematic bleed.
2. **zscore_pump_SL** — 20 trades, -100% each. zscore_pump is a 1m slot machine, not a signal.

### Systematic Losers
- Every `accel-300+,rs-sXX,zscore-pump+` combo loses. Examples:
  - `accel-300+,rs-s144` (3 trades, avg -0.74%)
  - `accel-300+,rs-s30` (3 trades, avg -0.63%)
  - `accel-300+,rs-s152` (2 trades, avg -0.62%)
- Root cause: accel_300 fires when price has already run 4-10 bars from EMA cross. Entry is at the top of the move.

### Market Regime Pattern
| slope | direction | trades | avg_pnl |
|-------|-----------|--------|---------|
| FLAT | SHORT | 398 | +6.65% |
| FLAT | LONG | 533 | -3.48% |

In flat markets, SHORTs win, LONGs lose badly. accel_300 fires LONG on first upside flick — often a false break that reverses.

### What's Working
- **profit-monster exits** — 215 trades, avg +2.68%, total +$575.75. The exit engine is sound.
- **zscore_pump_TP** — 24 trades, +100% each (but 20 zscore_pump_SL offset it — net ~$400, not skill)

### The Three Core Problems
1. **accel-300+ fires on mature moves** — requires PERSISTENCE_BARS consecutive bars + growing gap. By the time 3-5 bars confirm, you're entering at the local top.
2. **zscore_pump adds noise** — 1m scanner combined with multi-bar confirmation creates worst-of-both-worlds. Every trade becomes a 50/50.
3. **RS + accel-300 mismatch in flat markets** — "bounce off support with momentum confirmation" in a flat market is a reversal trap.

### What Winners Have in Common
- They follow the market's natural rhythm — trend continues, trailing stop locks in profit.
- DYDX LONG +2.61%: "hhh-long4,hhh-long5,rs-s551" — multiple confluence signals
- ETH LONG +2.61%: "hhh-long4,zscore-pump+" with 98% confidence
- Key: signals with HIGH confluence (multiple different signal types agreeing) win. Single-source or weak-confluence signals lose.

## Signal Source Reference
Available signals in `/root/.hermes/scripts/signals/`:
- `accel_300.py` — persistent gap above EMA300 with growing gap (source: accel-300+ / accel-300-)
- `rs.py` — support/resistance bounce (source: rs-sXX / rs-rXX)  
- `zscore_pump.py` — 1m box breakout (source: zscore-pump+ / zscore-pump-)
- `hhh*.py` — higher-high/higher-low structure (source: hhh-long4 etc.)
- `ema_angle.py` — EMA angle trend (source: ema-angle-)
- `macd_accel.py` — MACD acceleration
- `volume_hl.py` — volume breakouts