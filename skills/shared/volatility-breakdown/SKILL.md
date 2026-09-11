---
name: volatility-breakdown
description: Break down a signal's trades by volatility regime (FLAT/NORMAL/HIGH/EXTREME). Shows WR, PnL, and avg PnL per regime. Use when user says "volatility breakdown for [signal]" or "break down [signal] by regime".
---

# Volatility Breakdown — Signal Performance by Regime

Break down a signal's closed trades by the volatility regime at entry time.

## Trigger

"volatility breakdown for [signal]"
"break down [signal] by regime"
"[signal] regime analysis"

## What It Does

1. Query `signal_outcomes` for all closed trades of the given signal
2. Group by `regime` field (FLAT, NORMAL, HIGH, EXTREME)
3. Calculate WR, PnL, and avg PnL per regime
4. Show total performance

## Output Format

```
[SIGNAL] — Performance by Volatility Regime
Total trades: [N]

Regime       WR                   PnL        Avg PnL
-------------------------------------------------------
FLAT         [W]/[T] ([%])        $[PnL]     $[Avg]
NORMAL       [W]/[T] ([%])        $[PnL]     $[Avg]
HIGH         [W]/[T] ([%])        $[PnL]     $[Avg]
EXTREME      [W]/[T] ([%])        $[PnL]     $[Avg]
-------------------------------------------------------
TOTAL        [W]/[T] ([%])        $[PnL]

Key Insight: [one-line summary of what the data shows]
```

## SQL Query

```sql
SELECT 
    regime,
    COUNT(*) as trades,
    SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(pnl_usdt), 2) as total_pnl,
    ROUND(AVG(pnl_usdt), 2) as avg_pnl
FROM signal_outcomes
WHERE signal_type LIKE '%[SIGNAL]%'
GROUP BY regime
ORDER BY total_pnl DESC;
```

## Key Insights to Highlight

- Which regime has highest WR?
- Which regime has best PnL?
- Which regime is dragging performance?
- Should any regime be blocked? (negative PnL = candidate for blocking)

## Regime Definitions

| Regime | ATR% Range | Description |
|--------|-----------|-------------|
| FLAT | < 0.48% | Low volatility, range-bound |
| NORMAL | 0.48-1.0% | Sweet spot, standard conditions |
| HIGH | 1.0-1.5% | High volatility, big moves |
| EXTREME | > 1.5% | Storm conditions, skip most signals |
