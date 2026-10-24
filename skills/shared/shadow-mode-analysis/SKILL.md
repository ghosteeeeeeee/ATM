---
name: shadow-mode-analysis
description: Analyze shadow-mode paper trading data to find trends, winners, losers, gate/filter impact, and optimal SL levels. Use when asked about shadow data, signal quality, exit engine performance, gate analysis, stop-loss optimization, or "what's working in shadow mode". Triggers: "shadow analysis", "shadow mode analysis", "analyze shadow data", "which signals work", "which gates help", "exit engine comparison", "SL sweep", "stop loss optimization", "best stop loss".
---

# Shadow-Mode Analysis

Analyze shadow-mode paper trading data to find trends, winners, losers, gate/filter impact, and optimal stop-loss levels.

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

# SL level sweep (find optimal stop-loss)
python3 scripts/shadow_trader.py --sweep-sl
python3 scripts/shadow_trader.py --sweep-sl --sweep-signal <signal_type>
python3 scripts/shadow_trader.py --sweep-sl --sweep-dir LONG
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

### 7.5 SL Level Sweep (Stop-Loss Optimization)

Find the optimal stop-loss level for each signal type. Tests SL from 0.5% to 50%.

**When to use:** When trades are being stopped out too soon, or when looking to optimize exit parameters.

```bash
# Global SL sweep (all signals)
python3 scripts/shadow_trader.py --sweep-sl

# Per-signal SL sweep
python3 scripts/shadow_trader.py --sweep-sl --sweep-signal <signal_type>

# Direction-specific
python3 scripts/shadow_trader.py --sweep-sl --sweep-dir LONG
python3 scripts/shadow_trader.py --sweep-sl --sweep-dir SHORT
```

**Key findings from 2026-10-21 analysis:**
- Current ATR SL (0.35-1.03%) is in the WORST zone — stops out 58-79% of trades
- Best SL: 8.0% (WR=52.7%, +405% total, 6% stopped)
- Sweet spot: 8% SL. Beyond 10%, held losers drag down average.
- LONG signals benefit from wider SL (3-8%), SHORT signals harder to profit from

**Interpretation:**
- **High stopped%**: SL too tight, cutting winners before they develop
- **Low stopped% + negative total**: SL too wide, holding losers too long
- **Optimal**: Balance between stopped% and total PnL (typically 3-8%)

**Per-signal optimization:** Different signals have different optimal SL levels. Run `--sweep-sl --sweep-signal <type>` to find signal-specific optima.

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

# SL level sweep (stop-loss optimization)
python3 scripts/shadow_trader.py --sweep-sl
python3 scripts/shadow_trader.py --sweep-sl --sweep-signal <signal_type>
```

## Common Findings & Patterns

### Pattern: Tight SL (Stopped Out Too Soon)
Trades stopped out before they have room to breathe. Price moves favorably after stop-out.
- **Diagnosis**: Run `--sweep-sl`. If high SL levels (3-8%) show much better PnL than current, SL is too tight.
- **Symptoms**: High stopped% at low SL levels, STX/CFX-type trades (stopped at -0.5%, then +1% within 1h)
- **Fix**: Widen SL, or use per-signal SL optimization
- **Key insight**: LONG signals typically benefit from wider SL (3-8%). Current ATR SL (0.35-1.03%) may be too tight for current market conditions.

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
6. **SL optimization**: Optimal stop-loss levels (global and per-signal)
7. **Patterns**: Tight SL, peak buyers, wrong side, giveback, hold time asymmetry
8. **Recommendations**: What to flip, what to filter, what to change, optimal SL

## Reports

Saved reports:
- `reports/20261021-shadow-sl-sweep.md` — SL sweep analysis
- `reports/2026-10-24-shadow-mode-disabled-signals-analysis.md` — Disabled signals & gate impact analysis

## Shadow-Bypass Registry (Re-Enabled Signals)

The shadow-bypass registry contains 16 signals disabled in the main system but tracked in shadow mode. Defined in `hermes_constants.py:3168` as `SHADOW_BYPASS_SIGNALS`.

### Query Shadow-Bypass Signals

```sql
-- Get shadow stats for all bypass signals
SELECT source, direction, COUNT(*) as n,
  ROUND(100.0*SUM(CASE WHEN net_pnl_pct>0 THEN 1 ELSE 0 END)/COUNT(*),1) as wr,
  ROUND(AVG(net_pnl_pct),3) as avg_pnl,
  ROUND(SUM(net_pnl_pct),1) as total_pnl,
  ROUND(AVG(mfe_pct),3) as avg_mfe,
  ROUND(AVG(mae_pct),3) as avg_mae
FROM shadow_trades WHERE closed=1
  AND (source LIKE '%bb-squeeze-%' OR source LIKE '%bb-bounce-v3%' 
       OR source LIKE '%volume-breakout-long%' OR source LIKE '%hmacd_mtf-+%'
       OR source LIKE '%doji-bottom%' OR source LIKE '%ichimoku-%'
       OR source LIKE '%ichimoku+%' OR source LIKE '%rs-r%' OR source LIKE '%rs-s%'
       OR source LIKE '%open-skies%' OR source LIKE '%squeeze-cross%'
       OR source LIKE '%rs-broken%' OR source LIKE '%vel-hermes%')
GROUP BY source, direction
ORDER BY n DESC;
```

### Bypass Signal Categories

**Stage A: Parameter-Killed / Regime-Specific Winners**
- `bb-squeeze-` (SHORT) — SHORT side killed
- `bb-bounce-v3-long` (LONG) — Removed from STANDALONE_BYPASS
- `volume-breakout-long+` (LONG) — KILLED Oct 13
- `hmacd_mtf-+` (LONG) — HMACD_MTF_PLUS_ENABLED=False
- `doji-bottom-long` (LONG) — Needs different exit

**Stage B: Gate-Blocked Signals**
- `ichimoku-` (SHORT) — Blocked by SHORT-REGIME-GATE
- `ichimoku+` (LONG) — Single-source, blocked by CONFLUENCE-GATE
- `rs-r` (LONG) — Single-source, blocked by CONFLUENCE-GATE
- `rs-s` (SHORT) — Single-source, blocked by CONFLUENCE-GATE

**Stage C: Killed Signals (NEVER_REENABLE)**
- `open-skies+` (LONG) — 13.6% WR
- `squeeze-cross+` (LONG) — 0% WR
- `squeeze-cross-` (SHORT) — no edge
- `rs-broken-short` (SHORT) — 26.5% WR, massive drag
- `rs-broken-resistance-long` (LONG) — momentum bearish
- `vel-hermes+` (LONG) — 0% WR, -$1.61
- `vel-hermes-` (SHORT) — AUTO-DISABLED

### Key Findings (2026-10-24 Analysis)

1. **All gates are HELPING** — removing all gates would add ~$1,172 in losses
2. **Entries are the problem** — ALL SL levels show negative avg PnL (even 50% SL = -0.224%)
3. **Disabled signals are mostly worse** — ichimoku- (1,591T, 61.1% WR) still loses -$173
4. **SHORT beats LONG by 10pp** — 52.3% vs 42.4% WR
5. **Only 4 signals positive (n≥20)** — volume_breakout_short, hl_copy_minus, ai-trader, grind_breakout_short
6. **pump-chain #1 bleeder** — 3,834T, 31.7% WR, -$442.2

## Data Source

Shadow data is stored in `/root/.hermes/brain/shadow_trades.db`:
- `shadow_trades` table: all signals with exit engine simulations
- `meta` table: watermarks for incremental recording

## Related Skills

- `signal-backtest` — backtest signals on historical data
- `trade-analysis` — analyze live trade performance
- `signal-quality-tuner` — tune signal parameters
- `gate_shadow` — per-gate shadow WR (existing system)
