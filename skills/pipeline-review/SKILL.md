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

### IMPORTANT — Verify DB Paths First

The signals DB path may have changed. Always verify before running:

```bash
# Check which DBs are active (most recently modified)
ls -lat /root/.hermes/data/*.db | head -10

# predictions.db is often the ACTIVE output (128K+ rows)
# signals_hermes_runtime.db may be EMPTY (0 signals) — legacy/dead path
sqlite3 /root/.hermes/data/predictions.db "SELECT COUNT(*) FROM predictions"
```

### Step 1 — Collect Data

**Primary DB: predictions.db** (active pipeline output, ~128K rows)
```python
import sqlite3
sc = sqlite3.connect('/root/.hermes/data/predictions.db')
q = sc.cursor()

# Direction accuracy (most important check)
q.execute("""
    SELECT direction, COUNT(*) as n,
           SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END) as correct,
           AVG(predicted_move_pct) as avg_pred,
           AVG(actual_move_pct) as avg_actual
    FROM predictions WHERE correct IS NOT NULL GROUP BY direction
""")

# Direction ratio
q.execute("""
    SELECT direction, COUNT(*) FROM predictions GROUP BY direction
""")

# Confidence tier accuracy
q.execute("""
    SELECT
        CASE
            WHEN confidence < 50 THEN '<50'
            WHEN confidence >= 50 AND confidence < 60 THEN '50-60'
            WHEN confidence >= 60 AND confidence < 70 THEN '60-70'
            WHEN confidence >= 70 AND confidence < 80 THEN '70-80'
            ELSE '80+'
        END as tier,
        COUNT(*) as n,
        SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END) as correct
    FROM predictions WHERE correct IS NOT NULL GROUP BY tier
""")
```

**Legacy signals DB** (may be empty — check first):
```python
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

## Key Findings from 2026-04-12 Run

| # | Severity | Finding |
|---|----------|---------|
| 1 | CRITICAL | signals_hermes_runtime.db EMPTY (0 signals) — ai_decider not writing there. predictions.db is the active DB (128K+ rows) |
| 2 | CRITICAL | DOWN predictions at 27% WR (anti-correct) vs UP at 95.7%. Model is systematically wrong on shorts. Root cause: candle_predictor.py build_prediction_prompt() LLM maps elevated price → DOWN countertrend (wrong direction) |
| 3 | CRITICAL | 8.6x LONG bias — 115K UP vs 13K DOWN predictions. Double the previous 4x HIGH threshold |
| 4 | CRITICAL | Confidence tiers are INVERSE of accuracy: conf 50-60 = 89% WR, conf 80+ = 33% WR. Confidence cannot be used as approval gate |
| 5 | HIGH | All 86 closed trades have signal="unknown" — no attribution, can't analyze WR by signal type |
| 6 | OK | predictions.db generating ~4 predictions/sec across 84 tokens — generation healthy |

## Key Findings from 2026-04-02 Run (Legacy)

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

## Key Findings from 2026-04-13 Run (Decider Timeout Investigation)

| # | Severity | Finding |
|---|----------|---------|
| 1 | CRITICAL | decider_run timing out at 240s step limit — LLM calls in `ai_decider.py` had NO timeout. OpenAI SDK defaults to infinite wait on network issues |
| 2 | CRITICAL | HL `/info` rate-limit gap was 10s between calls — HL allows ~10 req/s, so 1s gap is safe and 10x faster. FileLock prevents concurrent access anyway |
| 3 | HIGH | HL API `_http_post` retry backoff escalated to 64s per attempt (1→2→4→8→16→32→64s). Capped at 10s — 64s waits were blocking decider_run |
| 4 | HIGH | Token counter at exactly 1,200,000 / 1,200,000 cap — all LLM calls blocked. Reset `ai_decider_daily_tokens.json` |
| 5 | MEDIUM | Orphaned HL positions (AVAX LONG, MOVE LONG) detected by decider_run — exist on Hyperliquid but NOT in paper PostgreSQL. Runs in DRY mode, requires human decision |
| 6 | MEDIUM | `hermes-trades-api.py` `get_trades()` returns 0 rows due to `WHERE server='Hermes'` filter — `server` column may be NULL. Always verify actual column values before filtering |

## Pipeline Timer Verification

**Critical: Timer files can lie.** The timer `.timer` file defines WHEN the service fires, but the service script itself may have internal gating that further limits frequency. Always check BOTH.

```bash
# Step 1: Check what the timer file claims
systemctl cat hermes-pipeline.timer
# Look for OnCalendar=*:0/10:00 (every 10 min) vs *:0/1:00 (every 1 min)

# Step 2: Check the actual pipeline script for internal gating
grep -n "minute % 10\|every_10\|STEPS_EVERY" /root/.hermes/scripts/run_pipeline.py
# This shows which steps run every cycle vs every 10 cycles

# Step 3: Verify actual recent executions
journalctl -u hermes-pipeline.service --since "1 hour ago" | grep "Pipeline"
# Or check pipeline log:
tail -5 /root/.hermes/logs/pipeline.log

# Step 4: Check pipeline log timestamp spacing
# If timer is every 10min but script has internal gating every 10th run,
# steps will appear to run every 10min even if timer fires every 1min
```

**Common misconfiguration pattern:**
- Timer fires every 10 min (`*:0/10:00`)
- T expects pipeline steps every 1 min
- Fix: change timer to `*:0/1:00` — pipeline script has its own `minute % 10` gating for 10-min steps

**Timer locations:**
- `/etc/systemd/system/hermes-pipeline.timer` — pipeline steps (signal_gen, decider, etc.)
- `/etc/systemd/system/hermes-hl-sync-guardian.timer` — ATR/SL/TP recalculation (every 2 min)
- `/etc/systemd/system/hermes-hype-paper-sync.timer` — HL ↔ paper reconciliation (every 10 min)

## HL API Rate Limit — Critical Learning

```
# WRONG (found in hyperliquid_exchange.py line ~369):
time.sleep(10)  # between every /info call — was causing 150s+ decider_run

# CORRECT:
time.sleep(1)   # HL allows ~10 req/s, 1s gap is safe with FileLock

# For /exchange endpoints: time.sleep(10) still applies (heavier operations)
```

## LLM Timeout Pattern — Always Required

```python
# All OpenAI() constructor calls in ai_decider.py need explicit timeout:
_client = OpenAI(api_key=_token, base_url='...', timeout=60)  # 60s max

# Without timeout=60, the SDK waits forever on network issues → decider_run timeout
```

## Orphaned HL Positions — Correct DRY RUN Behavior

decider_run correctly detects positions on Hyperliquid not in paper DB:
```
[WARN] AVAX: on HL but NOT in paper → DRY LONG @ ?
[WARN] MOVE: on HL but NOT in paper → DRY LONG @ ?
Result: 2 confirmed in sync | 2 orphaned (need closing)
DRY RUN — re-run with --apply to close orphaned positions
```
Always runs in DRY mode by default. Human must decide: import to paper DB or close with `--apply`.

## PostgreSQL server Column Filter Gotcha

```python
# This query may return 0 rows even when positions exist:
cur.execute("SELECT ... WHERE server='Hermes' AND status='open'")  # returns 0!

# Check actual column values first:
cur.execute("SELECT DISTINCT server FROM trades LIMIT 10")  # see what values exist

# Safe pattern — use COALESCE or no filter:
cur.execute("SELECT ... WHERE COALESCE(server, 'Hermes') = 'Hermes' AND status='open'")
# OR just:
cur.execute("SELECT ... WHERE status='open'")
```

---

## Recommended Immediate Actions (2026-04-13)

1. **[CRITICAL]** Verify `timeout=60` on all 3 OpenAI SDK calls in `ai_decider.py` (lines ~1331, ~2241, ~2565) — was missing, causing infinite hangs
2. **[CRITICAL]** Confirm rate-limit gap in `hyperliquid_exchange.py` `_info_rate_limit()` is 1s (not 10s) — was causing decider_run to take 150s+ for 15 tokens
3. **[CRITICAL]** Confirm retry backoff cap is 10s in `_http_post` — was reaching 64s (6 retries × ~10s each = 60s wasted)
4. **[HIGH]** Monitor for orphaned HL positions — decider_run correctly detects them in DRY mode. Investigate root cause (pipeline outage? DB write failure?)
5. **[HIGH]** Fix `hermes-trades-api.py` `get_trades()` `server='Hermes'` filter — returns 0 rows. Verify actual server column values
6. **[MEDIUM]** Check `ab_learner` double-writing (two patterns.json writes seen in logs) — may be running twice per cycle
7. **[MEDIUM]** After pipeline restart, verify `hotset.json` freshness — was falling back to DB query when LLM calls timed out

## Recommended Immediate Actions (Legacy)

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