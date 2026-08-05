# Signal Outcome Live Audit — 2026-05-07
# Source: /root/.hermes/data/signals_hermes_runtime.db, signal_outcomes table
# Total trades: 3,280 | Overall WR: 11.2% | Overall avg_pnl: -65.3%

## System Reality Check

**If your signal's claimed WR in GOOD_STANDALONE_SIGNALS doesn't match what you see in
live SQL output, trust the SQL.** The hardcoded values are from small-sample audits.

```bash
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT signal_type, direction, COUNT(*) cnt, SUM(is_win) wins,
          ROUND(100.0*SUM(is_win)/COUNT(*),1) wr,
          ROUND(100.0*AVG(pnl_pct),3) avg_pnl,
          ROUND(100.0*SUM(pnl_pct),3) total_pnl
   FROM signal_outcomes
   GROUP BY signal_type, direction
   HAVING cnt >= 5
   ORDER BY wr DESC, avg_pnl DESC
   LIMIT 30;"
```

## Full Live Results (cnt >= 5, ordered by WR desc)

| signal_type | dir | cnt | wins | wr | avg_pnl | total_pnl |
|-------------|-----|-----|------|----|---------|-----------|
| hl_reconcile | SHORT | 35 | 20 | 57.1 | -1453.5 | -50873.4 |
| hl_reconcile | LONG | 16 | 6 | 37.5 | -4.75 | -76.0 |
| hzscore-,pct-hermes- | SHORT | 26 | 9 | 34.6 | -4.86 | -126.5 |
| hwave-,hzscore+ | SHORT | 12 | 4 | 33.3 | -19.5 | -234.0 |
| hzscore-,momentum+,vel-hermes+ | LONG | 22 | 6 | 27.3 | +7.77 | +171.0 |
| oc-zscore-v9-,zscore-momentum- | SHORT | 16 | 4 | 25.0 | -18.87 | -302.0 |
| hzscore+,pct-hermes+,vel-hermes+ | LONG | 38 | 9 | 23.7 | -31.91 | -1212.7 |
| ma-cross-5m-short,zscore-short | SHORT | 26 | 6 | 23.1 | -23.09 | -600.3 |
| ma-cross-5m-long,pct-hermes+ | LONG | 38 | 8 | 21.1 | -49.03 | -1863.0 |
| hzscore+,pct-hermes+ | LONG | 24 | 5 | 20.8 | -16.34 | -392.1 |
| hzscore+ | SHORT | 73 | 15 | 20.5 | -33.82 | -2469.1 |
| ma-cross-5m-long,volume-1m-long,zscore-long | LONG | 10 | 2 | 20.0 | -56.91 | -569.1 |
| accel-300+,hzscore- | LONG | 52 | 8 | 15.4 | -35.74 | -1858.7 |
| gap-300+,zscore-momentum+ | LONG | 128 | 23 | 18.0 | -55.85 | -7149.0 |
| pct-hermes+,zscore-momentum+ | LONG | 28 | 5 | 17.9 | -44.38 | -1242.7 |
| hzscore-,pct-hermes-,vel-hermes- | SHORT | 35 | 6 | 17.1 | -26.81 | -938.2 |
| oc-mtf-rsi+,pct-hermes+ | LONG | 34 | 5 | 14.7 | -46.62 | -1585.1 |
| hzscore-,momentum+ | LONG | 33 | 6 | 18.2 | -44.05 | -1453.7 |
| hzscore- | LONG | 76 | 12 | 15.8 | -70.40 | -5350.2 |
| hzscore+,vel-hermes- | SHORT | 44 | 3 | 6.8 | -51.06 | -2246.7 |
| accel-300+ | LONG | 42 | 8 | 19.0 | -27.03 | -1135.4 |
| gap-300+,pct-hermes+ | LONG | 80 | 8 | 10.0 | -64.82 | -5185.6 |
| hzscore+,pct-hermes-,vel-hermes- | SHORT | 64 | 0 | 0.0 | -53.20 | -3404.6 |
| pct-hermes+ | LONG | 64 | 3 | 4.7 | -52.85 | -3382.2 |
| pct-hermes- | SHORT | 32 | 0 | 0.0 | -52.31 | -1674.0 |
| ma-cross-5m+ | LONG | 28 | 0 | 0.0 | -55.14 | -1543.8 |
| gap-300- | LONG | 132 | 6 | 4.5 | -45.61 | -6020.8 |

## GOOD_STANDALONE_SIGNALS Reality Check

The current entries (from signal_compactor.py ~line 471):

```python
GOOD_STANDALONE_SIGNALS = {
    'pct-hermes-':   {'wr': 35, 'avg': 0.221, 'dir': 'SHORT'},  # LIVE: 0% WR, -52.3%
    'pct-hermes+':   {'wr': 100, 'avg': 0.770, 'dir': 'LONG'},  # LIVE: 4.7% WR, -52.9% — REMOVE
    'hzscore+':      {'wr': 32, 'avg': 0.195, 'dir': 'SHORT'},  # LIVE: 20.5% WR, -33.8%
    'hzscore-':      {'wr': 38, 'avg': 0.318, 'dir': 'LONG'},   # LIVE: 15.8% WR, -70.4%
    'accel-300+':    {'wr': 42, 'avg': 0.438, 'dir': 'LONG'},   # LIVE: 19.0% WR, -27.0%
    'trend_purity+': {'wr': 38, 'avg': 0.257, 'dir': 'LONG'},   # No live data in this audit
    'ma-cross-5m-':  {'wr': 47, 'avg': 0.062, 'dir': 'SHORT'}, # No live data in this audit
}
```

**Every single WR estimate in GOOD_STANDALONE_SIGNALS is significantly higher than live
outcomes show.** This means the confluence gate is letting through signals that the data
says should be blocked.

## What Actually Works (by total_pnl, top 5)

| signal_type | dir | cnt | wr | total_pnl |
|-------------|-----|-----|----|-----------|
| hzscore-,momentum+,vel-hermes+ | LONG | 22 | 27.3% | +$171 |
| hl_reconcile | LONG | 16 | 37.5% | -$76 (high WR but small sample) |
| hzscore-,pct-hermes- | SHORT | 26 | 34.6% | -$126 (lowest loss among combos) |

## Diagnostic Queries

```sql
-- Overall system health
SELECT COUNT(*) total, SUM(is_win) wins,
       ROUND(100.0*SUM(is_win)/COUNT(*),1) wr,
       ROUND(100.0*AVG(pnl_pct),3) avg_pnl,
       ROUND(100.0*SUM(pnl_pct),3) total_pnl
FROM signal_outcomes;

-- Check specific signal (replace pct-hermes+)
SELECT signal_type, direction, COUNT(*) cnt, SUM(is_win) wins,
       ROUND(100.0*SUM(is_win)/COUNT(*),1) wr,
       ROUND(100.0*AVG(pnl_pct),3) avg_pnl,
       ROUND(100.0*SUM(pnl_pct),3) total_pnl,
       MIN(pnl_pct) min_pnl, MAX(pnl_pct) max_pnl
FROM signal_outcomes
WHERE signal_type LIKE '%pct-hermes+%'
GROUP BY signal_type, direction;

-- Pending signals breakdown
SELECT source, direction, COUNT(*) cnt,
       SUM(CASE WHEN decision='PENDING' THEN 1 ELSE 0 END) pending,
       SUM(CASE WHEN decision='EXPIRED' THEN 1 ELSE 0 END) expired,
       SUM(CASE WHEN decision='EXECUTED' THEN 1 ELSE 0 END) executed
FROM signals WHERE age > 0 AND age < 7200
GROUP BY source, direction ORDER BY cnt DESC;
```

## The ATR SL Context

All the deeply negative avg_pnl figures may partly reflect the ATR SL being too tight
(0.15% floor before 2026-05-07, raised to 0.50%). Before declaring a signal "bad,"
check if the losses are from SL hits vs TP completions. A signal that consistently
hits its ATR SL at -0.5% (instead of running to +2%) has a structural TP/SL problem,
not necessarily a signal direction problem.

See: `references/sl-tightness-analysis-2026-05-07.md` for SL analysis (126 losses,
71/126 were RIGHT signal at time of SL hit — meaning the signal was correct but
the stop was too tight).
