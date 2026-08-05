# 24h Closed-Trade Analysis — 2026-07-14

**28 closed trades, 10W/18L, -4.70% net, 35.7% WR (LOSS day).**

Source of truth: PostgreSQL `trades` table via `psycopg2.connect(**BRAIN_DB_DICT)` —
the same conn pattern that `run_pipeline.py` uses for its summary line at the end
of every cron run. `server='Hermes'`, `status='closed'`, `close_time > NOW() - INTERVAL '24 hours'`.

## Canonical 24h Post-Mortem Query (CRITICAL — use this, not trades.json)

`run_pipeline.py` line 217-228 prints `Portfolio: X open | Y closed today | Z% PnL`.
That summary is from Postgres, NOT from `trades.json` (which is empty/stale).
Always re-run the same query when investigating:

```python
import psycopg2, sys
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()

# Same query as run_pipeline.py:217-228
cur.execute("""
  SELECT COUNT(*), COALESCE(SUM(pnl_pct),0), COALESCE(AVG(pnl_pct),0)
  FROM trades
  WHERE server='Hermes' AND status='closed'
    AND close_time > NOW() - INTERVAL '24 hours'
""")
n, sum_pnl, avg_pnl = cur.fetchone()
```

**Pitfall (lost a turn on this):** the column is `token`, NOT `symbol`. Any ad-hoc
query that says `SELECT symbol FROM trades` errors with `column "symbol" does not exist`.
This is consistent with HL token-based naming throughout the codebase. Always use `token`.

**Pitfall:** `hl_exit_price` is stored as `Decimal('0E-8')` for most rows (the
hl-sync backfill doesn't populate it). Don't use `IS NULL` checks — use
`hl_exit_price IS NOT NULL AND hl_exit_price != 0` (or just trust `exit_price`).

## Diagnostic Triad — Run All Three

When investigating any loss day, these three diagnostic cuts give 80% of the answer
in one Postgres pass:

```python
# 1. Win/loss + profit factor
cur.execute("""
  SELECT
    SUM(CASE WHEN pnl_pct>0 THEN 1 ELSE 0 END),
    SUM(CASE WHEN pnl_pct<0 THEN 1 ELSE 0 END),
    SUM(CASE WHEN pnl_pct>0 THEN pnl_pct ELSE 0 END),
    SUM(CASE WHEN pnl_pct<0 THEN pnl_pct ELSE 0 END)
  FROM trades WHERE server='Hermes' AND status='closed'
    AND close_time > NOW() - INTERVAL '24 hours'
""")
# wins, losses, gross_win, gross_loss → profit_factor = gross_win / abs(gross_loss)

# 2. Direction split (LONG vs SHORT)
cur.execute("""
  SELECT COALESCE(direction,'?'), COUNT(*),
         ROUND(AVG(pnl_pct)::numeric, 3),
         ROUND(SUM(pnl_pct)::numeric, 3)
  FROM trades WHERE server='Hermes' AND status='closed'
    AND close_time > NOW() - INTERVAL '24 hours'
  GROUP BY COALESCE(direction,'?') ORDER BY COUNT(*) DESC
""")

# 3. Exit-reason split (atr_sl_hit vs profit-monster vs guardian_*)
cur.execute("""
  SELECT COALESCE(exit_reason,'(none)'), COUNT(*),
         ROUND(AVG(pnl_pct)::numeric, 3)
  FROM trades WHERE server='Hermes' AND status='closed'
    AND close_time > NOW() - INTERVAL '24 hours'
  GROUP BY COALESCE(exit_reason,'(none)') ORDER BY COUNT(*) DESC
""")
```

If exit-reason dominates on `atr_sl_hit` with avg < 0, the issue is signal direction
(filter), not the SL mechanic. If `profit-monster` dominates, the issue is the
profit-take floor (winners clipped too early). If `guardian_sl/tp` dominates,
look at `hl-trading-debug` for self-close stale-TP/SL bugs.

## Today's Numbers (2026-07-14 15:20 UTC)

| Metric | Value |
|---|---|
| Closed trades (24h) | 28 |
| Wins / Losses | 10 / 18 (35.7% WR) |
| Sum PnL | **-4.70%** |
| Gross wins | +5.92% |
| Gross losses | -10.62% |
| Profit factor | **0.56** (losses are ~1.8× larger than wins) |
| Avg per trade | -0.17% |

## Directional Bleed — the Real Story

| Direction | n | Avg | Sum |
|---|---|---|---|
| SHORT | 21 | -0.08% | -1.62% |
| LONG | 7 | **-0.44%** | **-3.08%** |

**7 longs did 65% of the day's damage.** Shorts as a group are essentially
breakeven (-0.08% average, 21 trades). The 5x leverage compounding amplifies
each LONG loss; LONGs are typically the higher-conviction direction.

Most damaging individual loss: **CASHCAT LONG -2.25%** (atr_sl_hit) and
**CASHCAT LONG -1.30%** (atr_sl_hit) — the same token opened LONG twice
and lost both. This pattern (same token, same direction, repeated loss in 24h)
is a per-token blacklist candidate.

## Exit-Reason Breakdown

| Reason | n | Avg PnL |
|---|---|---|
| atr_sl_hit | 19 | -0.55% (the bleed) |
| profit-monster | 7 | +0.83% (working fine) |
| guardian_sl | 1 | -0.04% |
| guardian_tp | 1 | -0.03% |

**19 of 28 trades hit atr_sl_hit.** That's 68% — consistent with the
exit-distribution pattern from prior audits (most losers are SL hits, not
TP clips). The SL mechanic itself is functioning correctly; the signal
direction is the bug.

## Top 5 Losers (24h)

| Token | Dir | PnL | Reason | Strategy | Signal |
|---|---|---|---|---|---|
| CASHCAT | LONG | -2.25% | atr_sl_hit | Hermes-accel-300+ | accel-300+,rs-s46 |
| CASHCAT | LONG | -1.30% | atr_sl_hit | Hermes-accel-300+ | accel-300+,rs-s30 |
| UNI | SHORT | -1.11% | atr_sl_hit | Hermes-accel-300- | accel-300-,rs-s-broken |
| UNI | SHORT | -1.06% | atr_sl_hit | Hermes-accel-300- | accel-300-,rs-s-broken |
| AVAX | SHORT | -0.78% | atr_sl_hit | Hermes-accel-300- | accel-300-,rs-s-broken |

**Pattern: CASHCAT LONG opened twice with rs-s46 (46 touches, below 120 cap) and
rs-s30 (30 touches). Both lost.** The 46-touch and 30-touch levels were valid
by the cap but the underlying LONG direction was wrong.

## Top 5 Winners (24h)

| Token | Dir | PnL | Reason | Strategy | Signal |
|---|---|---|---|---|---|
| UNI | SHORT | +1.12% | profit-monster | Hermes-accel-300- | accel-300-,rs-s-broken |
| PEOPLE | SHORT | +0.92% | profit-monster | Hermes-accel-300- | accel-300-,rs-s-broken |
| GRAM | SHORT | +0.87% | profit-monster | Hermes-accel-300- | accel-300-,rs-s-broken |
| CHIP | SHORT | +0.82% | profit-monster | Hermes-accel-300- | accel-300-,rs-s-broken |
| GALA | LONG | +0.80% | profit-monster | Hermes-accel-300+ | accel-300+,rs-s60 |

All 5 winners: SHORT accel-300- OR LONG accel-300+ with healthy touch counts.
The same signal pattern that produces winners ALSO produces losers (UNI SHORT +
1.12% AND -1.11% in same 24h). The asymmetric payoff is structural, not random.

## Hourly PnL Concentration

| Hour UTC | n | Sum PnL |
|---|---|---|
| 2026-07-13 17:00 | 3 | +1.98% |
| 2026-07-13 19:00 | 2 | -1.81% |
| 2026-07-13 21:00 | 3 | -1.84% |
| 2026-07-13 22:00 | 2 | -1.84% |

The day's damage concentrates between **19:00–22:00 UTC**. The 17:00 hour was
profitable (+1.98%) and the system recovered a bit by 23:00. The 19-22 UTC
window has been a known-weak window in prior 24h-trade-analysis reference files
(2026-06-25 saw 20:00-22:00 = 1W/9L). Same pattern.

## What This Audit Did NOT Find

- No stuck/old open trades (all opens clean, 0 currently open)
- No phantom or duplicate trades (no guardian_orphan duplicates)
- No hl-sync discrepancies (all 28 closes have valid exit_price)
- No sub-10s false closes (no atr_sl_hit on favorable price moves)
- No mirror_open failures
- No memory crashes or pipeline exceptions

The system is healthy mechanically; the loss is real signal-direction underperformance.

## Conclusions / Next-Steps Candidates (not implemented)

1. **CASHCAT LONG goes on per-token blacklist pending data** — same token,
   same direction, two consecutive losses in 24h. Total n=2 so not
   stat-sig, but worth flagging.
2. **5x leverage on LONG accel-300+** — today's LONG losses were 5x leverage.
   Combined with 24h-trade-analysis-2026-06-25 finding ("NEVER 5x leverage
   on accel-300-"), the picture is: high leverage + wrong-direction trend
   = amplified loss.
3. **19:00-22:00 UTC "evening chop" filter** — multiple 24h-trade-analysis
   audits now identify this window as weak. A time-of-day filter at the
   confluence gate might cut the worst losses.

**DO NOT IMPLEMENT** — these are post-mortem observations only. Per `hl-trading-debug`
skill rule "Only report first, let's plan, then we'll implement": hand findings to T,
write plan, wait for approval.
