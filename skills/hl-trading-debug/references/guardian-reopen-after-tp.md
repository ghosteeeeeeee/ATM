# Guardian Re-Opens After TP Close — 2026-05-07

## Symptom

Same signal (`accel-300+`) closes DASH at +4.06% profit, then re-enters DASH 67 minutes later and closes at -4.05% loss.

signal_outcomes shows 4 rows for DASH accel-300+:
- id 3135: +4.06% (win, entry)
- id 3136: +3.16% (win, exit)
- id 3145: -3.15% (loss, entry)
- id 3146: -4.05% (loss, exit)

Two separate trades on same token, same signal, opposite outcomes within 67 minutes.

## Pattern Across accel-300+

22 unique accel-300+ trades:
- 4 big wins: +154% to +406%
- 18 big losses: -105% to -405%

System is systematically cutting winners (TP at +4%) and re-entering on the same signal, then getting stopped out.

## SQL Detection

```sql
-- Find duplicate entry/exit pairs for same signal+token
SELECT token, signal_type, created_at, pnl_pct, id,
  LAG(pnl_pct) OVER (PARTITION BY token, signal_type ORDER BY id) as prev_pnl,
  LAG(created_at) OVER (PARTITION BY token, signal_type ORDER BY id) as prev_time
FROM signal_outcomes
WHERE signal_type = 'accel-300+'
ORDER BY token, id;

-- Look for: is_win=1 followed by is_win=0 on same token within 2 hours
WITH pairs AS (
  SELECT token, signal_type, created_at, pnl_pct, is_win,
    LAG(is_win) OVER (PARTITION BY token, signal_type ORDER BY id) as prev_win,
    LAG(created_at) OVER (PARTITION BY token, signal_type ORDER BY id) as prev_time
  FROM signal_outcomes
)
SELECT token, signal_type, prev_time, created_at,
  ROUND((julianday(created_at) - julianday(prev_time))*1440, 1) as gap_min,
  prev_win, is_win, pnl_pct
FROM pairs
WHERE prev_win = 1 AND is_win = 0
  AND created_at > datetime('now', '-7 days')
ORDER BY gap_min ASC;
```

## Likely Cause

Profit-monster or guardian TP logic is too aggressive for leveraged positions:
- At 10-20X leverage, +4% price move = +40-80% of equity
- System closes at +4% (reasonable TP)
- Same signal still active in hot-set or re-triggers via signal_compactor
- Guardian re-opens on the same signal
- Price reverses, SL hits at -0.5% to -4%

## Fix

After a TP close, block re-entry on the same token+signal combo for a cooldown window. Options:
1. Add a cooldown entry in signal_cooldowns.json for the specific token+signal
2. Guardian should not re-open if last close_reason was 'take_profit'
3. After TP close, signal should be marked as "used" for at least N minutes