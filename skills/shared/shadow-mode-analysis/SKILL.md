---
name: shadow-mode-analysis
description: Analyze shadow-mode paper trading data to find trends, winners, losers, and gate/filter impact. Use when asked about shadow data, signal quality, exit engine performance, gate analysis, or "what's working in shadow mode". Triggers: "shadow analysis", "shadow mode analysis", "analyze shadow data", "which signals work", "which gates help", "exit engine comparison".
---

# Shadow-Mode Analysis

Analyze shadow-mode paper trading data to find trends, winners, losers, and gate/filter impact.

## Quick Start

```bash
# Full analysis
python3 scripts/shadow_trader.py --report

# HML threshold + dead signals
python3 scripts/shadow_trader.py --analyze-hml

# Flip test (test if reversing a losing signal would be profitable)
python3 scripts/shadow_trader.py --flip-test --flip-signal <signal_type>

# Exit engine comparison
python3 scripts/shadow_trader.py --analyze-exits --exit-signal <signal_type>

# Hold time analysis
python3 scripts/shadow_trader.py --analyze-hold --hold-signal <signal_type>

# Arm timeout sweep
python3 scripts/shadow_trader.py --sweep-arm --sweep-signal <signal_type> --sweep-dir <direction>

# HML threshold sweep
python3 scripts/shadow_trader.py --sweep-hml
```

## Analysis Framework

### 1. Overall Health Check

Run `--report` to get:
- Total signals recorded/closed
- Gate justification (which gates blocked what)
- Exit engine A/B comparison
- Signal quality by source

**Key metrics:**
- Win Rate (WR): % of trades with positive PnL
- Total PnL: sum of all net_pnl_pct (percent-points)
- Avg PnL: average per trade
- MFE: Max Favorable Excursion (best price during hold)
- MAE: Max Adverse Excursion (worst price during hold)

### 2. Direction Analysis

Check if LONG or SHORT is performing better:
```sql
SELECT direction, COUNT(*), 
  ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
  ROUND(SUM(net_pnl_pct),1) total,
  ROUND(AVG(net_pnl_pct),3) avg
FROM shadow_trades WHERE closed=1
GROUP BY direction;
```

### 3. Exit Engine Analysis

Run `--analyze-exits` to compare which exit engine would have been best:
- **PM Trail**: Activates at +0.40%, trails from peak. Best for trending moves.
- **ATR SL/TP**: Continuous peak-trailing. Default engine.
- **Hard Max Loss**: Cuts at CUT_LOSER_PNL/leverage. Loss-only, 0% WR by design.
- **Cut Loser**: Two-tier loss cutting. Loss-only, 0% WR by design.
- **Universal Hold**: Fixed 8h/24h hold. Frees capital for new trades.
- **Speed Stale**: Exits stalled trades. Fidelity gap (no speed_percentile gate).
- **Trail Arm Timeout**: Exits trades that never reach activation.

**Key insight**: PM Trail 100% WR is structural (activates at +0.40%, always profitable by design). Hard Max/Cut Loser 0% WR is by design (loss-only engines).

### 4. Hold Time Analysis

Run `--analyze-hold` to see winners vs losers hold times:
- Winners typically hold LONGER than losers
- If arm timeout is culling winners, increase the timeout
- If trades lose money over time, decrease the timeout

**Key insight**: Trades held 2+ hours are often profitable. Trades held <1h are often losers. The exit engines may be exiting too early.

### 5. Gate/Filter Analysis

Check which gates are helping vs hurting:
```sql
-- Which gates blocked signals, and what would have happened?
SELECT gate_name, COUNT(*) n,
  ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
  ROUND(SUM(net_pnl_pct),1) total,
  ROUND(AVG(net_pnl_pct),3) avg
FROM shadow_trades 
WHERE closed=1 AND gate_blocked=1 AND gate_name IS NOT NULL
GROUP BY gate_name HAVING COUNT(*) >= 10
ORDER BY total;
```

**Interpretation:**
- **HELPING**: Gate blocked signals that would have lost (total << 0)
- **HURTING**: Gate blocked signals that would have won (total >> 0)
- **NEUTRAL**: Gate blocked signals that would have broken even

### 6. Confidence Threshold Analysis

Check if higher confidence correlates with better performance:
```sql
SELECT CASE 
  WHEN confidence < 60 THEN '<60'
  WHEN confidence < 70 THEN '60-69'
  WHEN confidence < 80 THEN '70-79'
  ELSE '80+' 
END band, COUNT(*),
  ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
  ROUND(AVG(net_pnl_pct),3) avg
FROM shadow_trades WHERE closed=1
GROUP BY band ORDER BY band;
```

**Key insight**: Confidence often doesn't correlate with performance. High-confidence signals can still lose.

### 7. RSI Filter Analysis

Check which RSI bands perform best:
```sql
SELECT CASE 
  WHEN json_extract(context, '$.rsi_14') < 30 THEN '<30 (oversold)'
  WHEN json_extract(context, '$.rsi_14') < 40 THEN '30-40'
  WHEN json_extract(context, '$.rsi_14') < 50 THEN '40-50'
  WHEN json_extract(context, '$.rsi_14') < 60 THEN '50-60'
  WHEN json_extract(context, '$.rsi_14') < 70 THEN '60-70'
  ELSE '>70 (overbought)'
END rsi_band, COUNT(*),
  ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
  ROUND(AVG(net_pnl_pct),3) avg
FROM shadow_trades WHERE closed=1 
  AND json_extract(context, '$.rsi_14') IS NOT NULL
GROUP BY rsi_band ORDER BY rsi_band;
```

### 8. Direction x Regime Cross-Analysis

Check which direction works best in which regime:
```sql
SELECT direction, json_extract(context, '$.vol_regime') vol, COUNT(*),
  ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
  ROUND(AVG(net_pnl_pct),3) avg
FROM shadow_trades WHERE closed=1
GROUP BY direction, vol HAVING COUNT(*) >= 50
ORDER BY avg DESC;
```

### 9. Token Analysis

Check which tokens perform best/worst:
```sql
-- Best tokens
SELECT token, COUNT(*),
  ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
  ROUND(SUM(net_pnl_pct),1) total
FROM shadow_trades WHERE closed=1
GROUP BY token HAVING COUNT(*) >= 20
ORDER BY total DESC LIMIT 10;

-- Worst tokens
SELECT token, COUNT(*),
  ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) wr,
  ROUND(SUM(net_pnl_pct),1) total
FROM shadow_trades WHERE closed=1
GROUP BY token HAVING COUNT(*) >= 20
ORDER BY total ASC LIMIT 10;
```

### 10. Flip Test

For losing signals, test if flipping direction would be profitable:
```bash
python3 scripts/shadow_trader.py --flip-test --flip-signal <signal_type>
```

**When to flip:**
- Signal has WR < 35% with n >= 30
- Signal has high MFE but negative outcome (peak buyer)
- Signal has MAE > 2x MFE (wrong side)

### 11. Parameter Sweeps

Test different parameter values:
```bash
# Arm timeout sweep
python3 scripts/shadow_trader.py --sweep-arm --sweep-signal <signal_type> --sweep-dir <direction>

# HML threshold sweep
python3 scripts/shadow_trader.py --sweep-hml
```

## Common Findings & Patterns

### Pattern: Peak Buyers
Signals with high MFE but negative outcome — they spike up then crash down.
- **Diagnosis**: Entry is chasing the pump, not waiting for pullback
- **Fix**: Add pullback filter (enter on dip, not at peak)

### Pattern: Wrong Side
Signals with MAE > 2x MFE — immediately go against us.
- **Diagnosis**: Signal is firing at the wrong time
- **Fix**: Investigate entry conditions, add timing filter

### Pattern: Giveback
Signals with high MFE but give back all gains — winning trades become losers.
- **Diagnosis**: Trail isn't catching gains
- **Fix**: Tighter trail or earlier partial profit-taking

### Pattern: Hold Time Asymmetry
Winners hold LONGER than losers — arm timeout is culling winners.
- **Diagnosis**: Fixed timeout is too aggressive
- **Fix**: Increase timeout, or use PnL-scaled timeout

## Output Format

When reporting shadow analysis findings:

1. **Overall stats**: Total signals, WR, Total PnL, Avg PnL
2. **Winners**: Top signals by total PnL (n>=10)
3. **Losers**: Bottom signals by total PnL (n>=10)
4. **Exit engines**: Which engine performs best
5. **Gates**: Which gates are helping vs hurting
6. **Patterns**: Peak buyers, wrong side, giveback, hold time asymmetry
7. **Recommendations**: What to flip, what to filter, what to change

## Data Source

Shadow data is stored in `/root/.hermes/brain/shadow_trades.db`:
- `shadow_trades` table: all signals with exit engine simulations
- `meta` table: watermarks for incremental recording

## Related Skills

- `signal-backtest` — backtest signals on historical data
- `trade-analysis` — analyze live trade performance
- `signal-quality-tuner` — tune signal parameters
- `gate_shadow` — per-gate shadow WR (existing system)
