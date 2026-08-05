# Hot-Set Starvation: When WR Filter Blocks Everything

## Symptom (2026-05-11)

After implementing per-coin WR filter in signal_compactor, hot-set drops to 0 tokens:

```
signal_compactor --dry:
  🚫 [HOTSET-FILTER] EIGEN LONG: WR=33% (3 trades)
  🚫 [HOTSET-FILTER] DASH LONG: WR=33% (3 trades)
  🚫 [HOTSET-FILTER] AXS LONG: WR=0% (3 trades)
Compaction done — 0 tokens in hotset
```

The WR filter is working correctly but every token in the signal generation pipeline has a losing trade history.

## Why This Happens

Signal generation (`accel_300_long`) fires for tokens that already have PostgreSQL history:
- ASTER: 15 trades, 46.7% WR → blocked
- BRETT: 13 trades, 46.2% WR → blocked
- MON: 9 trades, 44.4% WR → blocked
- All tokens with ≥3 trades in the last 7 days have sub-50% WR

The signal generation pipeline doesn't produce signals for tokens with zero history — it produces signals for tokens with momentum that happen to already be in the trade database with a losing record.

## The Chain

```
signal_compactor builds hot-set from PENDING signals (top-10 by score)
        ↓
decider_run reads hot-set.json + APPROVED signals from DB
        ↓
WR gate at decider_run: blocks tokens with <50% WR and ≥3 trades
        ↓
Now signal_compactor ALSO blocks at hot-set build time
        ↓
Result: hot-set = 0, no trades execute
```

## This Is Actually Correct Behavior

The system is working as designed:
- Bad tokens (sub-50% WR, ≥3 trades) should NOT enter the hot-set
- The fix just moves the filter earlier (from decider_run to signal_compactor)
- Tokens in the pipeline with losing history are correctly identified and blocked

## Recovery Path

1. **7-day window drains** — old trades age out, trade counts drop below 3, WR defaults to 50%, tokens start passing again
2. **New momentum tokens** — signal generation finds tokens without trade history
3. **Manual WR reset** — clear PostgreSQL history for specific tokens (risky)

**LTC SHORT in WR cooldown — verified (2026-05-26):**
```
LTC SHORT: total=3, wins=1, WR=33.3%
  oldest=2026-05-22, newest=2026-05-26 01:32
  All 3 trades within last 7 days → blocked by WR filter
```
Initial diagnostic error: checked `hotset.json` first (empty), then `trades.json` (wrong schema), concluded "no cooldown." The WR filter was firing silently in signal_compactor's live process. Direct PostgreSQL query confirmed LTC SHORT is blocked.

**Diagnostic:** When hot-set is empty and WR filter hasn't been confirmed, go straight to PostgreSQL via `_get_token_wr()` logic. Don't rely on `hotset.json` (can be empty due to starving) or `trades.json` (doesn't carry WR state). The authoritative source is:
```bash
python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', connect_timeout=5)
cur = conn.cursor()
cur.execute('''
    SELECT token, direction, COUNT(*) as total,
           SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins
    FROM trades
    WHERE status = '\''closed'\''
      AND close_time >= NOW() - INTERVAL '\''7 days'\''
      AND token = '\''LTC'\''
    GROUP BY token, direction
''')
rows = cur.fetchall()
for r in rows:
    wr = round((r[3] or 0) / r[2] * 100, 1) if r[2] > 0 else 50.0
    blocked = r[2] >= 3 and wr < 50
    print(f'{r[0]} {r[1]}: total={r[2]}, wins={r[3]}, WR={wr:.0f}% → {\"BLOCKED\" if blocked else \"passing\"}')
"
```