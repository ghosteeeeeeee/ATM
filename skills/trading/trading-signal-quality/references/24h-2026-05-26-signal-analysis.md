# 24h Signal Analysis — May 26, 2026

## Data Sources

**PostgreSQL brain DB** (`/var/run/postgresql`, dbname=`brain`):
- `trades` table: closed trades with pnl_usdt, signal, direction, exit_reason, close_time
- Connection: `psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres', password='postgres')`

**SQLite signals_hermes_runtime.db** (`/root/.hermes/data/signals_hermes_runtime.db`):
- `signals` table: all signals with decision, z_score, confidence, source, created_at
- Connection: `sqlite3.connect(RUNTIME_DB)`

**SQLite signals_hermes.db** (`/root/.hermes/data/signals_hermes.db`):
- `price_history` table: 1m close prices (timestamp in Unix seconds)
- Connection: `sqlite3.connect(PRICE_DB)`

## Methodology

### Joining Trades to Signals

```python
# Get EXECUTED signals in time window
cur.execute("""
SELECT token, direction, source, confidence, z_score, created_at, decision
FROM signals
WHERE decision = 'EXECUTED'
  AND created_at >= ?
ORDER IN BY created_at DESC
""", (since_ts,))
```

### Signal Z vs Spot Z Computation

Signal_z: computed by zscore_pump.py on 150-bar lookback. Stored in signal record at creation.

Spot_z: independently computed from price_history using 30-bar lookback — the "immediate" momentum state.

Gap = signal_z - spot_z. Positive gap = move was building on longer timeframe, not fresh.

## 24h Results (May 25 22:36 → May 26 21:58)

34 closed trades: 16 winners, 18 losers, net ≈+$0.08

All winners: exit_reason=profit-monster, all had rs-sXXXX,zscore-pump+ or rs-rXXXX,zscore-pump-
All losers: exit_reason=atr_sl_hit (17 trades) or HARD_SL_CLOSE_FAILED (1 trade)

## Same-Token Re-entry — Core Failure Mode

AVAX LONG winner at 05:37 (+1.40%) vs AVAX LONG loser at 10:32 (-0.96%) — same signals, same direction, 5 hours apart, opposite outcomes.

Winner: 10-bar mom +0.08%, 20-bar mom +0.11% — barely moving at entry
Loser: 10-bar mom +0.30%, 20-bar mom +0.97% — already 1% extended

Same pattern for CAKE, ZK, MOVE.

## Gap Gate Results

| Token | Outcome | Sig_z | Spot_z | Gap | Gap > 2.0? |
|-------|---------|-------|--------|-----|------------|
| CAKE LOSE | -0.91% | 5.327 | 1.357 | +3.97 | YES |
| AVAX LOSE | -0.96% | 4.971 | 2.022 | +2.95 | YES |
| ETH LOSE | -0.80% | 3.503 | 1.120 | +2.38 | YES |
| AVAX WIN | +1.40% | 3.124 | 1.151 | +1.97 | NO (accept) |
| ZK WIN | +1.26% | 3.721 | 1.890 | +1.83 | NO (accept) |
| CAKE WIN | +0.97% | 3.226 | 4.531 | -1.31 | NO (accept) |

**Gap gate at 2.0 would have caught CAKE LOSE, AVAX LOSE, ETH LOSE before entry.**

## Divergence Check Failure

DIVERGENCE_EXTREME_Z=3.5 on 30-bar spot lookback missed all major losers:
- AVAX LOSE: spot_z=3.892 (barely over 3.5, z-velocity 0-0.2, never got to -0.5/bar)
- ETH LOSE: spot_z=3.887 (same story)
- CAKE LOSE: spot_z=2.634 (NEVER reached 3.5, gate never consulted)
- BLUR LOSE: spot_z=4.016 (over threshold but velocity flipped positive)

## Key Findings

1. **Same-token re-entry = #1 failure mode**
2. **z-score magnitude NOT discriminative** (losers had similar |z| to winners)
3. **Pre-signal momentum extension is the differentiator** — 20-bar mom > +0.9% losing for LONGs
4. **Gap gate > 2.0 catches the actionable cases**
5. **COOLDOWN_BARS=5 too short** — 30 bars (~30 min) needed
6. **DIVERGENCE_EXTREME_Z=3.5 on 30-bar misses most losers**
7. **Time-of-day: winners at 04:00-06:00 EST (Asia), losers at 10:00-14:00 EST (US morning)**

## Constants Changes

| Constant | Current | Proposed |
|----------|---------|----------|
| ZSCORE_PUMP_COOLDOWN_BARS | 5 | 30 |
| ZSCORE_PUMP_DIVERGENCE_EXTREME_Z | 3.5 | 2.5 |
| ZSCORE_PUMP_DIVERGENCE_VEL_THD | -0.5 | -0.2 |
| ZSCORE_PUMP_DIVERGENCE_BARS | 5 | 8 |
| ZSCORE_PUMP_GAP_THRESHOLD | N/A | 2.0 (needs code change) |
