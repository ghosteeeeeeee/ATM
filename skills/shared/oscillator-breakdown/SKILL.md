---
name: oscillator-breakdown
description: Break down a signal's trades by BTC oscillator state (score, linreg, trend, zscore). Shows WR, PnL, and correlations. Use when user says "oscillator breakdown for [signal]", "oscillator analysis", or "check [signal] vs BTC".
---

# Oscillator Breakdown — Signal Performance by BTC State

Break down a signal's closed trades by the BTC continuum oscillator state at entry time.

## Trigger

"oscillator breakdown for [signal]"
"oscillator analysis for [signal]"
"check [signal] vs BTC"
"[signal] BTC correlation"
"how does [signal] perform with BTC"

## What It Does

1. Query PostgreSQL `trades` for all closed trades of the given signal
2. Query `continuum.db` → `continuum_states` for BTC oscillator data at each trade's entry time
3. Group by BTC score ranges, linreg bias, trend, and zscore
4. Calculate WR, PnL, and avg PnL per group
5. Identify correlations and sweet spots

## Output Format

```
[SIGNAL] — BTC Oscillator Analysis
Total trades: [N] (matched with BTC data)

=== BTC Score Ranges ===
Score       Trades  Wins   WR      PnL     Avg PnL
---------------------------------------------------
0-20        [T]     [W]    [%]    $[P]    $[A]
20-40       [T]     [W]    [%]    $[P]    $[A]
40-60       [T]     [W]    [%]    $[P]    $[A]
60-80       [T]     [W]    [%]    $[P]    $[A]
80-100      [T]     [W]    [%]    $[P]    $[A]

=== Linreg Bias ===
Linreg      Trades  Wins   WR      PnL     Avg PnL
---------------------------------------------------
BULL        [T]     [W]    [%]    $[P]    $[A]
BEAR        [T]     [W]    [%]    $[P]    $[A]
MIXED       [T]     [W]    [%]    $[P]    $[A]

=== BTC Trend ===
Trend       Trades  Wins   WR      PnL     Avg PnL
---------------------------------------------------
STRONG_UP   [T]     [W]    [%]    $[P]    $[A]
UP          [T]     [W]    [%]    $[P]    $[A]
CALM        [T]     [W]    [%]    $[P]    $[A]
STRONG_DOWN [T]     [W]    [%]    $[P]    $[A]
DOWN        [T]     [W]    [%]    $[P]    $[A]

=== Follow vs Fight ===
Setup                           Trades  Wins   WR      PnL
-----------------------------------------------------------
LONG + BTC Bullish (follow)     [T]     [W]    [%]    $[P]
LONG + BTC Bearish (fight)      [T]     [W]    [%]    $[P]
SHORT + BTC Bearish (follow)    [T]     [W]    [%]    $[P]
SHORT + BTC Bullish (fight)     [T]     [W]    [%]    $[P]

Key Insight: [one-line summary of what the data shows]
Recommendation: [actionable recommendation]
```

## SQL Queries

### 1. BTC Score Ranges
```sql
SELECT 
    CASE 
        WHEN btc_score < 20 THEN '0-20'
        WHEN btc_score < 40 THEN '20-40'
        WHEN btc_score < 60 THEN '40-60'
        WHEN btc_score < 80 THEN '60-80'
        ELSE '80-100'
    END as score_range,
    COUNT(*) as trades,
    SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(pnl_usdt), 2) as total_pnl,
    ROUND(AVG(pnl_usdt), 3) as avg_pnl
FROM trades t
JOIN continuum_states c ON ABS(EXTRACT(EPOCH FROM (t.open_time - TO_TIMESTAMP(c.ts)))) < 300
WHERE c.token = 'BTC'
  AND t.signal LIKE '%[SIGNAL]%'
  AND t.status = 'closed'
GROUP BY score_range
ORDER BY MIN(btc_score);
```

### 2. Linreg Bias
```sql
SELECT 
    CASE 
        WHEN c.linreg_direction LIKE '%BULL%' AND c.linreg_alignment > 0 THEN 'BULL'
        WHEN c.linreg_direction LIKE '%BEAR%' AND c.linreg_alignment < 0 THEN 'BEAR'
        ELSE 'MIXED'
    END as linreg_bias,
    COUNT(*) as trades,
    SUM(CASE WHEN t.pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(t.pnl_usdt), 2) as total_pnl
FROM trades t
JOIN continuum_states c ON ABS(EXTRACT(EPOCH FROM (t.open_time - TO_TIMESTAMP(c.ts)))) < 300
WHERE c.token = 'BTC'
  AND t.signal LIKE '%[SIGNAL]%'
  AND t.status = 'closed'
GROUP BY linreg_bias
ORDER BY total_pnl DESC;
```

### 3. Follow vs Fight
```sql
SELECT 
    CASE 
        WHEN t.direction = 'LONG' AND c.state_score > 60 THEN 'LONG + BTC Bullish (follow)'
        WHEN t.direction = 'LONG' AND c.state_score < 40 THEN 'LONG + BTC Bearish (fight)'
        WHEN t.direction = 'SHORT' AND c.state_score < 40 THEN 'SHORT + BTC Bearish (follow)'
        WHEN t.direction = 'SHORT' AND c.state_score > 80 THEN 'SHORT + BTC Bullish (fight)'
        ELSE 'Other'
    END as setup,
    COUNT(*) as trades,
    SUM(CASE WHEN t.pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(t.pnl_usdt), 2) as total_pnl
FROM trades t
JOIN continuum_states c ON ABS(EXTRACT(EPOCH FROM (t.open_time - TO_TIMESTAMP(c.ts)))) < 300
WHERE c.token = 'BTC'
  AND t.signal LIKE '%[SIGNAL]%'
  AND t.status = 'closed'
GROUP BY setup
HAVING COUNT(*) >= 3
ORDER BY total_pnl DESC;
```

## Key Insights to Highlight

### BTC Score Analysis
- Which score range has highest WR?
- Which score range has best PnL?
- Is there an inverted-U pattern (sweet spot in middle)?
- Is there a death zone at extremes?

### Linreg Analysis
- Does Linreg BULL correlate with LONG wins?
- Does Linreg BEAR correlate with SHORT wins?
- Is Linreg a stronger predictor than score?

### Follow vs Fight
- Does following BTC trend improve performance?
- Does fighting BTC trend hurt performance?
- Which direction benefits most from alignment?

### Signal-Specific Patterns
- Do momentum signals work better at extremes?
- Do mean-reversion signals work better in neutral?
- Are there signal-type specific sweet spots?

## BTC Oscillator Fields

| Field | Source | Description |
|-------|--------|-------------|
| `state_score` | continuum_states | 0-100 composite score (>70 bullish, <30 bearish) |
| `zscore_val` | continuum_states | Position relative to mean (>0 = above mean) |
| `linreg_direction` | continuum_states | BULL, BEAR, LEAN_BULL, LEAN_BEAR, NEUTRAL |
| `linreg_alignment` | continuum_states | -1 to 1 (positive = aligned with direction) |
| `trend_quality` | continuum_states | STRONG_UP, UP, CALM, STRONG_DOWN, DOWN |
| `market_phase` | continuum_states | CALM, RECOVERY, DECLINING, CRISIS |
| `velocity_val` | continuum_states | Rate of change (positive = accelerating up) |

## Regime Definitions

| BTC Score | Interpretation | LONG Bias | SHORT Bias |
|-----------|---------------|-----------|------------|
| 0-20 | Deep bear | Avoid (catching knives) | OK (oversold bounce risk) |
| 20-40 | Bearish | Caution | Sweet spot |
| 40-60 | Neutral | Sweet spot | Caution |
| 60-80 | Bullish | Sweet spot | Caution |
| 80-100 | Strong bull | Death zone (chasing) | Sweet spot (lagging alts) |

## Example Usage

User: "oscillator breakdown for pump-chain"
Agent: Run queries, show score ranges, linreg bias, follow vs fight, identify sweet spots

User: "how does pullback-entry- perform with BTC"
Agent: Run queries, show that pullback-entry- SHORT wins when BTC is bearish (follow), loses when BTC is bullish (fight)

User: "check mover+ vs BTC oscillator"
Agent: Run queries, show that mover+ LONG works best at BTC 60-80, fails at 80-100

## Data Sources

| Source | Location | Update Frequency |
|--------|----------|-----------------|
| Trade data | PostgreSQL `trades` table | Per trade |
| BTC oscillator | SQLite `continuum.db` → `continuum_states` | Real-time (per candle) |

## Limitations

1. **Data coverage:** BTC oscillator data only available from Sep 4, 2026 (14 days so far)
2. **Sample size:** Some score ranges have <20 trades — statistically marginal
3. **Market regime bias:** Results may differ in bullish vs bearish periods
4. **Signal-type contamination:** Different signals within same family may have different correlations
