---
name: pipeline-analyst
description: Run the Pipeline Analyst subagent against Hermes signal/trading data. Produces a full pipeline health report with velocity metrics, quality diagnostics, funnel analysis, win rate breakdown, and actionable recommendations.
category: trading
---

# Pipeline Analyst Skill

Run the Pipeline Analyst subagent against Hermes signal and trading data. Use this after any signal generation session or whenever pipeline health needs a diagnostic check.

## Context (always inject this)

Connect to both DBs:
- **Signals SQLite:** `/root/.hermes/data/signals_hermes_runtime.db`
- **Trades PostgreSQL:** `host=/var/run/postgresql database=brain user=postgres`
  - Note: column is `pnl_usdt` not `pnl_usd`; use `amount_usdt` not `size`; closed trades use `close_time` not `closed_at`; status values are `open`/`closed`

## Data Collection Queries

Run ALL of these before generating the report:

### Signals DB (SQLite)
```python
import sqlite3
sc = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
q = sc.cursor()

# 1. Overall funnel
q.execute("SELECT decision, COUNT(*), AVG(confidence) FROM signals GROUP BY decision")
# → shows EXPIRED/EXECUTED/SKIPPED/PENDING/APPROVED/WAIT/COMPACTED breakdown

# 2. Execution rate by signal_type and direction
q.execute("""
    SELECT signal_type, direction, decision, COUNT(*), AVG(confidence)
    FROM signals
    GROUP BY signal_type, direction, decision
    ORDER BY signal_type, decision
""")

# 3. SHORT vs LONG ratio per signal_type
q.execute("""
    SELECT signal_type,
        SUM(CASE WHEN direction='SHORT' THEN 1 ELSE 0 END) as short_n,
        SUM(CASE WHEN direction='LONG' THEN 1 ELSE 0 END) as long_n,
        ROUND(1.0*SUM(CASE WHEN direction='SHORT' THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN direction='LONG' THEN 1 ELSE 0 END),0), 1) as ratio
    FROM signals
    GROUP BY signal_type
""")

# 4. Confluence quality: what confidence leads to each decision?
q.execute("""
    SELECT decision, COUNT(*), AVG(confidence), MIN(confidence), MAX(confidence)
    FROM signals
    WHERE signal_type='confluence'
    GROUP BY decision
""")

# 5. Hot set health: review_count distribution (should show review_count >= 2)
q.execute("SELECT review_count, COUNT(*) FROM signals GROUP BY review_count ORDER BY review_count")
# If review_count=0 for everything, the hot set is broken — flag CRITICAL

# 6. Last signal timestamps — are we generating?
q.execute("SELECT MAX(created_at), MIN(created_at), COUNT(*) FROM signals WHERE created_at > datetime('now','-24h')")
# If 0 recent signals, pipeline is dead — flag CRITICAL

# 7. PENDING signals age
q.execute("""
    SELECT token, direction, signal_type, confidence, decision, review_count,
           strftime('%Y-%m-%d %H:%M', created_at) as created,
           ROUND((julianday('now') - julianday(created_at)) * 24, 1) as age_hours
    FROM signals
    WHERE decision IN ('PENDING','APPROVED')
    ORDER BY age_hours DESC
""")

# 8. SKIPPED signals — these are high-confidence rejections
q.execute("""
    SELECT token, direction, signal_type, confidence, decision,
           strftime('%Y-%m-%d %H:%M', created_at) as created
    FROM signals
    WHERE decision='SKIPPED' AND confidence >= 70
    ORDER BY confidence DESC, created DESC
    LIMIT 20
""")
```

### Trades DB (PostgreSQL)
```python
import psycopg2
db = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='***')
c = db.cursor()

# 1. Win rate
c.execute("SELECT COUNT(*) FROM trades WHERE status='closed'")
total_closed = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM trades WHERE status='closed' AND pnl_usdt > 0")
wins = c.fetchone()[0]
c.execute("SELECT SUM(pnl_usdt) FROM trades WHERE status='closed'")
net = c.fetchone()[0]
print(f"WR={wins/total_closed*100:.0f}% | Net={net}")

# 2. Open positions
c.execute("SELECT token, direction, entry_price, current_price, pnl_usdt, amount_usdt FROM trades WHERE status='open'")

# 3. Closed trades last 30d
c.execute("""
    SELECT token, direction, entry_price, exit_price, pnl_usdt, pnl_pct, close_time, exit_reason
    FROM trades
    WHERE status='closed' AND close_time > NOW() - INTERVAL '30 days'
    ORDER BY close_time DESC
""")
```

## Output Format

After collecting all data, produce a **Pipeline Health Report** with these sections:

1. **Funnel Velocity** — EXECUTED/SKIPPED/PENDING/EXPIRED rates, avg confidence by decision
2. **Directional Bias** — SHORT vs LONG ratios per signal type; flag if any type >3x bias
3. **Execution Quality** — Are we executing high-confidence signals? Compare SKIPPED avg conf vs EXECUTED avg conf
4. **Confluence Diagnostics** — Why are high-confluence signals (avg 93%) mostly SKIPPED?
5. **Hot Set Health** — review_count distribution; flag if 0 signals have review_count >= 2
6. **Pipeline Freshness** — Last signal timestamp; flag CRITICAL if 0 signals in 24h
7. **Trade Outcomes** — Win rate, net PnL, direction breakdown
8. **Intervention Recommendations** — Specific ranked list of fixes with revenue/quality impact

## Diagnostic Rules (always apply)

- review_count = 0 everywhere → **CRITICAL: hot set is broken**
- 0 signals in 24h → **CRITICAL: signal_gen is not running**
- SKIPPED avg_conf > EXECUTED avg_conf → **CRITICAL: ai-decider is rejecting better signals**
- Any signal_type ratio > 4x → **HIGH: directional bias needs investigation**
- Confluence avg_conf ~93% but execution rate < 5% → **HIGH: confluence auto-approval threshold too high**
- Net PnL < 0 across 20+ trades → **HIGH: signal quality not translating to profit**
