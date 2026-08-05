# Signal Quality Degradation — 2026-05-21

## Session Summary
- 20 trades over 3 days analyzed from `brain.trades` via PostgreSQL (host=/var/run/postgresql, db=brain, user=postgres)
- Signal quality shifted sharply: winners early evening (2026-05-20 20:00-23:00), losers late night/morning (2026-05-21 00:00+)
- Root causes identified: signal metadata not persisting + RS level quality not being filtered at entry

## Key Findings

### 1. signal_z_score always NULL in trade records
Even when zscore-pump is in the signal name, signal_z_score column is NULL. This means:
- z-score filtering/validation isn't working at entry
- Confluence scoring is broken for zscore-pump signals
- The value is computed in zscore_pump.py but not being written through to the trade INSERT

**Check:** signals/zscore_pump.py — does it call signal_schema.add_signal() with z_score field? Does signal_schema.add_signal() write z_score to DB? Does the guardian read signal_z_score at entry?

### 2. regime always NULL in trade records
All 20 trades show regime=None. The regime_5m.json lookup in rs.py either:
- Isn't being called at entry time, OR
- Result isn't being stored in the trade record

Without regime in the trade, counter-regime signals can't be filtered at execution time.

**Check:** signals/rs.py — _get_regime_5m() called? Result passed to add_signal? guardian reads regime at entry?

### 3. RS touch count not enforced at guardian entry
Low-touch levels (<100 touches) are getting through and losing. Extremely high touch counts (10k+) are also losing — over-tested congested levels.

| Touch Count | Outcome | Example |
|-------------|---------|---------|
| <100 touches | All lost | UMA (20 touches, -0.75%), XLM (111, -0.32%), 0G (48, -0.70%) |
| 100-500 touches | Mixed | GRIFFAIN (108+88, +0.50%), BSV (294, +1.51%) |
| 1000+ touches | Mixed | AAVE (2533, +3.31% win), APEX (16785, -1.12% loss) |
| 5000+ touches | Likely congestion | APEX ancient level — too tested, price doesn't bounce cleanly |

RS_RECENCY_WINDOW and RS_RECENCY_BOOST_K exist in rs.py but aren't being applied at scoring/execution time.

### 4. zscore-pump providing false momentum confluence
- z=None in trade records despite zscore-pump+ in signal → z-score may be computed but not validated
- Low-touch RS levels + weak z-score = losing combo
- Double RS confirmation (e.g., rs-s108,rs-s88,zscore-pump+) worked (GRIFFAIN +0.50%)

## Trade Table (3 days)

```
TOKEN     DIR   LEV   OPEN      CLOSE     PNL%    EXIT           SIGNAL
ASTER     SHORT  5   20:25:17  21:59:07  -0.68%  atr_sl_hit     rs-r77,zscore-pump-
BSV       SHORT  3   20:25:07  22:04:49  +1.51%  profit-monster  rs-r294,zscore-pump-
DOT       SHORT  5   22:06:08  22:06:11  +0.05%  atr_sl_hit      rs-r856,zscore-pump-
AAVE      SHORT  5   20:25:37  22:12:52  +3.31%  profit-monster  rs-r2533,zscore-pump-
ANIME     SHORT  3   20:25:47  22:23:56  +1.73%  profit-monster  rs-r498,zscore-pump-
CHIP      SHORT  3   22:25:08  22:44:05  +1.63%  profit-monster  rs-r490,rs-r689
BRETT     SHORT  3   22:13:07  22:50:07  -0.49%  atr_sl_hit      rs-r69,zscore-pump-
ADA       SHORT  5   20:25:27  23:17:16  +2.53%  profit-monster  rs-r3415,zscore-pump-
0G        LONG   3   22:00:08  23:19:05  -0.70%  atr_sl_hit      rs-s48,zscore-pump+
APEX      SHORT  3   22:46:07  23:21:06  -1.12%  atr_sl_hit      rs-r16785,zscore-pump-
ICP       SHORT  5   23:22:07  23:22:10  -0.02%  atr_sl_hit      rs-r112,zscore-pump-
BSV       LONG   3   23:10:07  23:29:06  -0.32%  atr_sl_hit      rs-s48,zscore-pump+
CHIP      SHORT  3   23:20:08  23:36:05  -0.36%  atr_sl_hit      rs-r1492,zscore-pump-
XLM       SHORT  5   22:07:08  00:04:08  -0.32%  atr_sl_hit      rs-r111,zscore-pump-
GRIFFAIN  LONG   3   00:05:08  00:14:37  +0.50%  profit-monster  rs-s108,rs-s88,zscore-pump+
UMA       SHORT  3   23:23:09  00:16:07  -0.75%  atr_sl_hit      rs-r20,zscore-pump-
ENS       SHORT  5   00:17:17  00:45:09  -0.20%  atr_sl_hit      rs-r224,zscore-pump-
BSV       SHORT  3   23:38:07  00:45:12  -0.25%  atr_sl_hit      rs-r212,rs-r475,zscore-pump-
ANIME     SHORT  3   23:18:08  00:45:22  -0.76%  atr_sl_hit      rs-r3071,zscore-pump-
```

## DB Query for This Analysis
```python
import psycopg2
conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres", password="hermes123")
q = """
SELECT token, direction, open_time, close_time, exit_reason, 
       signal, signal_z_score, signal_z_score_tier, regime,
       strategy, leverage, pnl_usdt, pnl_pct
FROM trades WHERE close_time >= NOW() - INTERVAL '3 days' ORDER BY close_time ASC
"""
```

## Fixes to Investigate
1. signal_z_score: trace the write path from zscore_pump.py → signal_schema.add_signal() → trade INSERT
2. regime: trace _get_regime_5m() in rs.py → add_signal() → trade record
3. RS touch minimum: add guard in decider_run or guardian entry — reject <50 touches unless strong z (|z|>2.5)
4. RS recency boost: apply RS_RECENCY_WINDOW/RS_RECENCY_BOOST_K at scoring time
5. Ancient level filter: downgrade levels with 10k+ touches unless recency-weighted score > threshold