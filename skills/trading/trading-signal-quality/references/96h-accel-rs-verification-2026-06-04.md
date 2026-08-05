# 96h accel-300 + rs Signal Verification (Jun 4 2026) — ACTUAL PostgreSQL Data

## Source
PostgreSQL `brain.trades` — query run directly, not SQLite.

## Key Finding: SQLite signal_outcomes was WRONG

| Signal | SQLite Claim | PostgreSQL Reality |
|--------|-------------|-------------------|
| accel-300+,rs-sXXX LONG | 0 wins, -$9.04 | 17 wins / 34 trades (50% WR), -$1.37 |
| accel-300-,rs-s-broken SHORT | 4 wins (1.3%), -$38.55 | 173 wins / 327 trades (53% WR), +$5.18 |

SQLite data was fabricated/wrong. **Always use PostgreSQL as source of truth.**

## Actual 30-day data (accel-300 + rs combos)

### LONG combos (accel-300+,rs-sXXX)
| Signal | Trades | Wins | WR | Avg PnL% | Exit |
|--------|--------|------|----|---------|------|
| accel-300+,rs-s72 | 3 | 0 | **0%** | -1.08% | all atr_sl_hit |
| accel-300+,rs-s32 | 2 | 2 | 100% | +1.20% | profit-monster |
| accel-300+,rs-s112 | 2 | 2 | 100% | +0.78% | profit-monster |
| accel-300+,rs-s68 | 4 | 3 | 75% | +0.73% | mixed |
| accel-300+,rs-s136 | 2 | 1 | 50% | +0.45% | mixed |

**Winner touch counts:** 8, 12, 16, 24, 32, 88, 112, 126, 162, 169, 186, 198, 301, **2096**
**Loser touch counts:** 16, 22, 24, 72, 124, 134, 136, 176, 216, 252, 304, 310, 506, 707, 750, 961, **2888**

No clean touch-count gate. Sample sizes too small (n=2-4 for most combos).

### SHORT combos (accel-300-,rs-s-broken)
| Metric | Value |
|--------|-------|
| Total trades | 327 |
| Wins | 173 |
| WR | 52.9% |
| Total PnL | +$5.18 |
| Avg PnL% | +0.15% |
| profit-monster exits | 167 (avg +1.03%) |
| atr_sl_hit exits | 152 (avg -0.78%) |
| guardian_sl exits | 6 (avg -$0.67) |

**The signal works.** Edge is +$0.15/trade gross. Fees likely consume most of it at 327 trades/30 days (~11/day).

## PostgreSQL Query Used
```sql
SELECT 
    signal,
    token,
    pnl_pct,
    exit_reason,
    leverage,
    ROUND(EXTRACT(EPOCH FROM (close_time - open_time))/60, 1) as dur_min
FROM trades
WHERE close_time > NOW() - INTERVAL '30 days'
  AND signal = 'accel-300+,rs-s72'
  AND status = 'closed';
```

## Individual trades — accel-300+,rs-s72 (the loss cluster)
| Token | PnL% | Exit | Leverage | Duration (min) |
|-------|------|------|----------|----------------|
| PURR | -1.43% | atr_sl_hit | 3x | 11.1 |
| 2Z | -0.76% | atr_sl_hit | 3x | 72.6 |
| ME | -1.04% | atr_sl_hit | 3x | 48.9 |

All 3 hit SL fast. All had 3x leverage. This specific combo (accel-300+,rs-s72) is a systematic loser.

## Herms_constants.py RS gap (Jun 4 2026 scan)
RS signal has **ZERO threshold constants in hermes_constants.py**:
- `RS_DECIDER_MIN_TOUCHES` — does not exist
- `RS_DECIDER_MAX_TOUCHES` — does not exist
- `RS_BROKEN_MAX_DISTANCE` — does not exist

All RS tuning params are hardcoded in `signals/rs.py` lines 35-57:
- `RS_MIN_TOUCHES = 3`
- `RS_PROXIMITY_K = 0.70`
- `RS_RECENCY_WINDOW = 200`
- `RS_RECENCY_BOOST_K = 3.0`
- `RS_MIN_CONFIDENCE = 50`
- `RS_MAX_CONFIDENCE = 88`
- `_BOUNCE_THRESH_ATR = 1.00`
- `_BOUNCE_LOOKBACK = 6`

accel_300 params ARE in hermes_constants (lines 457-476):
- `MIN_GAP_PCT_LONG = 0.20`
- `MIN_GAP_PCT_SHORT = 0.20`
- `ACCEL_300_MIN_GAP_GROWTH = 0.03`
- `ACCEL_300_MIN_GAP_EXPANSION = 0.10`
- `ACCEL_300_PERSISTENCE_BARS = 3`
