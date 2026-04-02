---
name: pipeline-review
description: Full pipeline health review for Hermes trading system — signals, execution, expiry, directional bias, win rate, and ranked recommendations. Replaces the one-off pipeline-analyst subagent run with a reusable, documented skill.
category: trading
author: T
created: 2026-04-02
---

# Pipeline Review

Full diagnostic of the Hermes signal → trade pipeline. Use whenever signals appear stale, execution rates drop, or as a routine weekly health check.

**Last run:** 2026-04-02 — found 3 CRITICAL issues (signal expiry, APPROVED→EXECUTED bottleneck, directional bias).

---

## What This Checks

1. **Funnel Velocity** — EXECUTED/SKIPPED/PENDING/EXPIRED/APPROVED/WAIT/COMPACTED breakdown with avg confidence per decision
2. **Directional Bias** — SHORT vs LONG ratios per signal type; flags any >4x bias
3. **Execution Quality** — SKIPPED avg_conf vs EXECUTED avg_conf; flags if good signals are being rejected
4. **Confluence Diagnostics** — why high-confluence signals (avg 82-90%) mostly SKIPPED or EXPIRED
5. **Hot Set Health** — review_count distribution; flags if hot set is broken
6. **Pipeline Freshness** — signals generated in last 24h; flags if generation is dead
7. **EXPIRED Signal Analysis** — age at expiry, confidence vs expiry timing
8. **Trade Outcomes** — win rate, net PnL, direction breakdown (PostgreSQL)
9. **Intervention Recommendations** — ranked fix list with impact estimates

---

## Critical Thresholds

| Rule | Severity | Threshold |
|------|----------|-----------|
| review_count = 0 everywhere | CRITICAL | Hot set broken |
| 0 signals in 24h | CRITICAL | signal_gen dead |
| SKIPPED avg_conf > EXECUTED avg_conf | CRITICAL | ai-decider rejecting better signals |
| Any signal_type ratio > 4x | HIGH | Directional bias |
| Confluence avg_conf >80% but exec rate <5% | HIGH | Auto-approval threshold too high |
| Net PnL < 0 across 20+ trades | HIGH | Signals not translating to profit |
| EXPIRED > 50% of total | CRITICAL | Signals timing out before execution |
| EXPIRED avg_conf >= PENDING avg_conf | HIGH | Good signals expiring before bad ones |

---

## How to Run

### Step 1 — Collect Data

Run all queries against both databases:

**SQLite signals DB:**
```python
import sqlite3
sc = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
q = sc.cursor()

# 1. Overall funnel
q.execute("SELECT decision, COUNT(*), AVG(confidence) FROM signals GROUP BY decision")
funnel = q.fetchall()

# 2. Execution by type + direction
q.execute("""
    SELECT signal_type, direction, decision, COUNT(*), AVG(confidence)
    FROM signals GROUP BY signal_type, direction, decision
    ORDER BY signal_type, decision
""")
exec_by_type = q.fetchall()

# 3. Side ratio per type
q.execute("""
    SELECT signal_type,
        SUM(CASE WHEN direction='SHORT' THEN 1 ELSE 0 END) as short_n,
        SUM(CASE WHEN direction='LONG' THEN 1 ELSE 0 END) as long_n
    FROM signals GROUP BY signal_type
""")
side_ratio = q.fetchall()

# 4. Confluence quality
q.execute("""
    SELECT decision, COUNT(*), AVG(confidence), MIN(confidence), MAX(confidence)
    FROM signals WHERE signal_type='confluence' GROUP BY decision
""")
confluence_q = q.fetchall()

# 5. Hot set review_count
q.execute("SELECT review_count, COUNT(*) FROM signals GROUP BY review_count ORDER BY review_count")
hot_set = q.fetchall()

# 6. Freshness
q.execute("""
    SELECT MAX(created_at), MIN(created_at), COUNT(*)
    FROM signals WHERE created_at > datetime('now','-24 hours')
""")
freshness = q.fetchall()

# 7. PENDING age
q.execute("""
    SELECT token, direction, signal_type, confidence, decision, review_count,
           strftime('%Y-%m-%d %H:%M', created_at) as created,
           ROUND((julianday('now') - julianday(created_at)) * 24, 1) as age_hours
    FROM signals WHERE decision IN ('PENDING','APPROVED') ORDER BY age_hours DESC LIMIT 20
""")
pending_age = q.fetchall()

# 8. EXPIRED analysis
q.execute("""
    SELECT token, direction, signal_type, confidence,
           strftime('%Y-%m-%d %H:%M', created_at) as created,
           ROUND((julianday('now') - julianday(created_at)) * 24, 1) as age_hours
    FROM signals WHERE decision='EXPIRED' ORDER BY age_hours DESC LIMIT 20
""")
expired_sample = q.fetchall()

# 9. Decision ages
q.execute("""
    SELECT decision, COUNT(*),
           MIN(julianday('now') - julianday(created_at)) as min_age_days,
           MAX(julianday('now') - julianday(created_at)) as max_age_days
    FROM signals GROUP BY decision
""")
decision_ages = q.fetchall()
```

**PostgreSQL trades DB:**
```python
import psycopg2
db = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
c = db.cursor()

c.execute("SELECT COUNT(*) FROM trades WHERE status='closed'")
total_closed = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM trades WHERE status='closed' AND pnl_usdt > 0")
wins = c.fetchone()[0]
c.execute("SELECT SUM(pnl_usdt) FROM trades WHERE status='closed'")
net = c.fetchone()[0]
print(f"WR={wins/total_closed*100:.0f}% | Net={net} | Closed={total_closed}")

c.execute("""
    SELECT token, direction, entry_price, exit_price, pnl_usdt, pnl_pct,
           close_time::text, exit_reason
    FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '30 days'
    ORDER BY close_time DESC
""")
closed_30d = c.fetchall()

c.execute("""
    SELECT direction, COUNT(*) as total,
           SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as wr_pct,
           SUM(pnl_usdt) as net
    FROM trades WHERE status='closed' GROUP BY direction
""")
wr_by_dir = c.fetchall()

c.execute("""
    SELECT signal, direction, COUNT(*) as n, SUM(pnl_usdt) as net, AVG(pnl_usdt) as avg
    FROM trades WHERE status='closed' GROUP BY signal, direction ORDER BY n DESC
""")
by_signal = c.fetchall()
```

### Step 2 — Analyze and Report

Apply the Critical Thresholds table above to the collected data. Produce a ranked intervention list.

### Step 3 — Save Output

Write the report to `/root/.hermes/pipeline_health_report_YYYY-MM-DD.txt`.

---

## Key Findings from 2026-04-02 Run

| # | Severity | Finding |
|---|----------|---------|
| 1 | CRITICAL | 64% of signals EXPIRED (~3.8h TTL) — expiry window too short for review workflow |
| 2 | CRITICAL | 97 APPROVED signals, only 11 EXECUTED — execution worker bottleneck |
| 3 | CRITICAL | Severe directional bias: rsi_individual 144:1 LONG, rsi_confluence 85:1 SHORT, momentum 100% LONG |
| 4 | HIGH | Net PnL negative (-2.86 USDT, 38% WR over 8 trades) — signals not translating to profit |
| 5 | HIGH | Confluence avg_conf 81-90% but execution rate 0.02% — good signals expiring |
| 6 | OK | Pipeline generating 54,730 signals/24h — generation healthy |
| 7 | OK | Hot set review_count distribution reasonable — not broken |

**Root cause of "all signals expired":** ~3.8h TTL is shorter than the human review → approval → execution cycle. Signals are approved but expire before the execution worker processes them.

---

## Recommended Immediate Actions

1. **[CRITICAL]** Increase signal TTL from ~3.8h to 8-12h in `signal_schema.py`
2. **[CRITICAL]** Investigate APPROVED→EXECUTED bottleneck — check `decider-run.py` execution loop and `position_manager.py` approval processor
3. **[CRITICAL]** Audit RSI and momentum signal generation for directional bias bugs
4. **[HIGH]** Lower confluence auto-approval threshold (currently requires 95%+?)
5. **[HIGH]** Review COMPACTOR logic — 286 signals (avg 94% conf) compacted without review
6. **[MEDIUM]** Review trailing stop parameters — many small losses at `trailing_exit_-0.9%`

---

## Files

- Report output: `/root/.hermes/pipeline_health_report_YYYY-MM-DD.txt`
- Signals DB: `/root/.hermes/data/signals_hermes_runtime.db`
- Trades DB: PostgreSQL `brain` database, `host=/var/run/postgresql`