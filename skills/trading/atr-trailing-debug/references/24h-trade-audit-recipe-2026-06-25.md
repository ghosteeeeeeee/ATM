# 24h Trade Audit Recipe — Diagnosing TPSL Bugs from Closed Trades

Session: 2026-06-25 — 24h closed-trade audit confirmed the
lowest_price init bug, phase-multiplier dead-code pattern, and
missing profit-lock feature first documented in
`2026-06-24-merl-short-lowest-trail-bug.md`. This file is the
**reusable recipe** for doing this kind of audit on any future
24h window.

## When to use this recipe

Run a 24h trade audit when:
- T asks "why are we not profitable" or "we had a winning streak
  then lost it all" or "analyze the closed trades"
- WR drops below 55% or net PnL goes negative for a day
- A new signal type starts firing and you need its hit rate
- A token is suspected of being a serial loser (blacklist candidate)
- You need to verify a TPSL fix is working (compare pre/post
  24h windows for the same metric)

## The recipe (5 steps)

### Step 1 — Pull all closed trades from PostgreSQL

DB location: `host=/var/run/postgresql dbname=brain user=postgres`.
Password is in `/root/.hermes/scripts/_secrets.py` as `BRAIN_PASSWORD`
or env var `BRAIN_DB_PASSWORD`.

```sql
SELECT id, token, direction, entry_price, exit_price, pnl_usdt, pnl_pct,
       exit_reason, open_time, close_time, signal, confidence, leverage,
       stop_loss, target, highest_price, lowest_price
FROM trades
WHERE status='closed' AND close_time > NOW() - INTERVAL '24 hours'
ORDER BY open_time ASC;
```

Critical columns for TPSL analysis:
- `highest_price`, `lowest_price` — peak tracking state
- `stop_loss`, `target` — what was the SL/TP at close
- `exit_reason` — `atr_sl_hit` vs `profit-monster` vs `guardian_*`
- `leverage` — 3x vs 5x breakdown

### Step 2 — Join with 1m price_history from signals_hermes.db

**Critical location note (learned 2026-06-25):** the 1m price data
is in `/root/.hermes/data/signals_hermes.db`, table `price_history`,
column `timestamp` (NOT `ts`). The runtime DB
`signals_hermes_runtime.db` has the `signals` table, NOT the
price history. Don't try `candles_1m` first — that table is empty.

```python
import sqlite3
db = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = db.cursor()
cur.execute("""
    SELECT timestamp, price FROM price_history
    WHERE token=? AND timestamp BETWEEN ? AND ?
    ORDER BY timestamp
""", (token, open_unix, close_unix))
```

For trades where 1m data is missing (newer tokens like MERL/AVNT),
fall back to 5m candles from `/root/.hermes/data/candles.db`:

```python
db2 = sqlite3.connect('/root/.hermes/data/candles.db')
cur2.execute("""
    SELECT ts, open, high, low, close FROM candles_5m
    WHERE token=? AND ts BETWEEN ? AND ?
    ORDER BY ts
""", (token, open_unix, close_unix))
```

### Step 3 — Compute MFE/MAE for every trade

For each trade, look up the price path during the trade and compute:
- **MFE** (Max Favorable Excursion): how far price moved IN our favor
- **MAE** (Max Adverse Excursion): how far price moved AGAINST us
- **maxFavClose** / **endFav**: did price stay favorable at close, or
  did it reverse?

For LONG: `MFE = (max(prices) - entry) / entry`, `MAE = (entry - min(prices)) / entry`
For SHORT: `MFE = (entry - min(prices)) / entry`, `MAE = (max(prices) - entry) / entry`

**MFE/MAE ratio is a leading indicator:**
- Winners: ratio > 2.0 (trend in favor > 2x adverse)
- Losers: ratio < 1.0 (adverse 2x larger than favorable)

When MFE/MAE < 1.0 in first 10-15 min, the trade is a LOSER. This
is a quantifiable filter candidate.

### Step 4 — Check DB integrity for peak tracking

```sql
-- How many trades have lowest_price=0 (broken trailing for SHORT)?
SELECT id, token, direction, lowest_price, highest_price
FROM trades
WHERE status='closed' AND close_time > NOW() - INTERVAL '24 hours'
  AND direction='SHORT' AND lowest_price=0;

-- How many have highest_price=0 (broken trailing for LONG)?
SELECT id, token, direction, lowest_price, highest_price
FROM trades
WHERE status='closed' AND close_time > NOW() - INTERVAL '24 hours'
  AND direction='LONG' AND highest_price=0;
```

Expected after the one-line fix in
`2026-06-24-merl-short-lowest-trail-bug.md`:
- SHORT trades: `lowest_price > 0` for ALL new trades
- LONG trades: `highest_price > 0` for ALL new trades
- (Pre-fix baseline: 32% of SHORT trades had lowest_price=0)

### Step 5 — Cross-reference with pipeline log for SL trail

For any specific trade where the SL looked broken, pull the
per-minute TPSL print from pipeline.log:

```bash
grep "TPSL.*MERL\|PERSIST.*MERL" /root/.hermes/logs/pipeline.log
```

Look for:
- `k=X` values — should differ across phases (if all k=0.5 with
  no variation, phase multipliers are bypassed)
- `eff_sl=X%` — should NOT be locked at 1.2% or 1.5% for the
  whole trade (that means floor dominates everything)
- `[PERSIST]` lines — should fire periodically with tightening SL

## Key findings from 2026-06-25 audit (38 trades)

| Metric | Winners (21) | Losers (16) |
|--------|--------------|-------------|
| Avg duration | 44 min | 62 min |
| Avg pnl_pct | +0.95% | -0.76% |
| Trajectory | "dropped continuously" | "rose continuously" |
| Exit reason | 100% profit-monster | 81% atr_sl_hit, 19% guardian |
| 3x leverage | 16 trades (all wins, +$1.07) | 7 trades (all losses, -$0.50) |
| 5x leverage | 5 trades (all wins, +$0.42 in sample) | 9 trades (all losses, -$0.81) |

**Cumulative PnL timeline:**
- 11:00-18:00 UTC: 15W/0L, +$1.29 peak
- 20:00-22:00 UTC: 1W/9L, $-0.61 (gave back most of peak)
- NET: +$0.68

**The losing streak pattern:** 100% 5x leverage, 100% mid/large
cap tokens (ENS, FET, TAO, ONDO, AAVE, UMA), 100% between
20:00-22:00 UTC.

**Per-token blacklist candidates (n>=3):**
- MERL: 4 trades, 25% WR, -$0.23
- ENS: 3 trades, 33% WR, -$0.13
- FET: 3 trades, 33% WR, -$0.09
- ASTER: 2 trades, 0% WR, -$0.06 (plus 10s re-open bug)

**ASTER 10s bug detail:**
- #12193: open 22:07:07, close 22:07:35 = 28 SECONDS
- #12194: open 22:08:07, close 01:38:19 = 3.5 HOURS
- Same token, same direction, opened 32s apart
- Different entries (0.61304 vs 0.61346)
- #12193: exit_reason=guardian_tp, pnl=$0.00, highest_price=1.0 (DEFAULT)
- #12194: exit_reason=guardian_sl, pnl=-$0.06
- **Bug:** No cooldown after orphan close → immediate re-entry

## Pattern: How a 24h audit surfaces TPSL bugs

A useful 24h audit looks for:
1. **Trades where `lowest_price=0` (or `highest_price=0`)** — these
   have broken trailing SL. Compare their pnl_pct to similar trades
   with proper trailing to estimate the bug's cost.
2. **MFE > 0.5% but pnl < 0** — these are "missed opportunity" trades
   where price moved in our favor but the SL hit anyway. Often a
   phase-multiplier dead-code issue.
3. **all k=0.5 (or all same) for a winning trade** — phase logic
   not engaging. Cross-reference with momentum_stats to see why.
4. **PnL distribution clustered at profit-monster floor (0.7%)** —
   winners being clipped short. If 90%+ of winners are at exactly
   0.7-0.8%, the profit-lock feature is missing.
5. **Time-of-day clustering of losses** — suggests macro/regime
   issue, not signal issue. Skip window is the fix.
6. **Re-entry within 60s of an orphan close** — no cooldown after
   guardian fires. Add cooldown for that token+direction.

## Output structure for a 24h audit report

When T asks for an audit, present findings in this order:
1. **Headline numbers** (WR, net PnL, profit factor)
2. **Timeline** (cumulative PnL by hour, peak-to-trough cycle)
3. **Winner vs Loser profile** (duration, leverage, trajectory, signals)
4. **Per-token breakdown** (with blacklist candidates)
5. **Time-of-day analysis** (good vs bad hours)
6. **Specific bug deep-dives** (MERL, ASTER, etc.)
7. **Recommended fixes** (organized by tier: bug vs constant vs filter)
8. **Expected outcomes** (delta PnL per fix, with confidence range)

Don't bury the headline in technical detail. T wants the answer
first, then the evidence.

## Related references

- `2026-06-24-merl-short-lowest-trail-bug.md` — original discovery
  of the 3 bugs (lowest_price init, phase dead-code, no profit-lock)
- `merl-2026-06-24-tpsl-timeline.md` — same content, alternate format
- `atr-24h-audit-2026-05-24.md` — May 24 audit (different findings:
  36.7% WR, 30 atr_sl_hit losses at avg -0.61%)
- `2026-04-16_041600-ondo-hbar-signal-analysis.md` — earliest 24h
  audit pattern in the skill library

## Companion script

See `scripts/analyze_24h_closed_trades.py` — full analyzer that
runs the recipe end-to-end. Reads PostgreSQL + 1m price_history
from signals_hermes.db, computes MFE/MAE per trade, prints
per-token / per-leverage / per-time-of-day breakdowns. Re-run
after any TPSL change to verify the fix improved outcomes.
