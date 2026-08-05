# Signal Quality Triggers — 2026-05-21 Session Findings

**Extends:** `hermes-signal-debugging/SKILL.md` triggers section

## New Triggers Added (2026-05-21)

```yaml
- "zscore-pump+ every combo loses"   # CONFIRMED: all accel-300+,rs-sXX,zscore-pump+ combos lose avg -0.6%
- "accel-300+ loses on flat market LONGs"  # FLAT market: SHORT avg +6.65%, LONG avg -3.48%
- "atr_sl_hit systematic bleed — why do we keep getting stopped out"  # 620 trades, -$172 total, avg -0.28%
- "how do we not be on the wrong side of the trade"  # entry timing: accel-300+ fires 4-10 bars after cross = local top
- "all our signals combined with zscore_pump are losing"  # zscore_pump is 1m box scanner, not a signal
- "profit-monster wins but entries are bad"  # exit engine sound (215 PM trades avg +2.68%); problem is entry timing
```

## Key Signal Findings

| Signal Type | Status | Evidence |
|-------------|--------|---------|
| accel-300+ LONG on FLAT market | LOSING | avg -3.48%, 533 trades |
| accel-300+ SHORT on FLAT market | WINNING | avg +6.65%, 398 trades |
| zscore_pump alone | SLOT MACHINE | +100%/-100% in consecutive 1m candles |
| accel-300+ + zscore_pump+ combo | LOSING | avg -0.6%, all rs-sXX variants |
| profit-monster exit | WINNING | 215 trades, avg +2.68%, total +$575 |
| hhh-long4 with high confluence | WINNING | DYDX +2.61%, ETH +2.61% |

## Root Causes
1. **accel-300+ fires too late** — requires 3-5 bars of persistence after EMA cross; by the time signal fires, entry is at the local top
2. **zscore_pump is noise** — 1m scanner combined with multi-bar signals creates 50/50 coin flips
3. **flat market LONGs fail** — the 1m slope filter in accel_300.py is insufficient to prevent false break entries

## Diagnostic Queries (for next session)
```sql
-- Find all signal combos with zscore_pump
SELECT signal, COUNT(*) as cnt, AVG(pnl_pct) as avg, SUM(pnl_pct) as total
FROM trades WHERE pnl_pct IS NOT NULL AND signal LIKE '%zscore-pump%'
GROUP BY signal ORDER BY cnt DESC;

-- Losing accel-300+ combos
SELECT signal, COUNT(*) as cnt, AVG(pnl_pct) as avg
FROM trades WHERE pnl_pct IS NOT NULL AND signal LIKE 'accel-300+%'
GROUP BY signal HAVING COUNT(*) >= 2 ORDER BY avg ASC LIMIT 10;

-- Regime breakdown for accel-300+
SELECT direction, COUNT(*) as cnt, AVG(pnl_pct) as avg
FROM trades WHERE pnl_pct IS NOT NULL AND signal LIKE 'accel-300+%'
GROUP BY direction;
```