# System Improvements Spec

Date: 2026-08-05
Source: Video transcript analysis → 5 priority actions

---

## 1. Dependency Audit (`pip-audit` weekly)

### Current State
- No `requirements.txt` at root level
- Dependencies unpinned (floating `>=`)
- `pip-audit` not installed

### Spec

**Create:** `/root/.hermes/scripts/audit_dependencies.py`
```python
# Runs pip-audit on installed packages
# Outputs: /root/.hermes/data/dependency_audit.json
# Alerts: any HIGH/CRITICAL vulnerabilities
```

**Create:** `/root/.hermes/requirements.txt`
- Pin all actively-used packages (psycopg2, requests, sqlite3 is stdlib)
- Run `pip freeze > requirements.txt` as baseline

**Create:** `systemd/hermes-dependency-audit.timer`
- Runs weekly (Sunday 03:00 UTC)
- Writes results to `data/dependency_audit.json`
- Alerts via pipeline log if vulnerabilities found

**Modify:** `run_pipeline.py`
- Add dependency audit check in health-monitor step

### Effort: Low (2-3 hours)

---

## 2. Pipeline Watchdog Timer

### Current State
- Lock file (`/tmp/hermes-pipeline.lock`) prevents overlap
- Per-step timeouts (300s default)
- `trading-checklist.py` reports hourly but doesn't remediate
- No stall detection

### Spec

**Create:** `/root/.hermes/scripts/pipeline_watchdog.py`
```python
# Checks every 2 minutes:
# 1. Is pipeline.lock older than 5 min? → pipeline stuck
# 2. Last signal timestamp > 3 min ago? → signal production halted
# 3. Last trade timestamp > 1h ago? → execution stalled
# 4. Any steps ERROR in last 10 min? → step failure
# 5. signal_outcomes table growing without trades? → data corruption

# Actions:
# - Log warnings to pipeline.log
# - If critical: restart pipeline timer
# - If data corruption: pause trading, alert T
```

**Create:** `systemd/hermes-watchdog.timer`
- Runs every 2 minutes
- Independent of pipeline timer

**Modify:** `run_pipeline.py`
- Add `watchdog_heartbeat` file write on each successful run
- Watchdog checks heartbeat freshness

### Effort: Medium (4-5 hours)

---

## 3. Memory Staleness Audit

### Current State
- Hebbian engine has `decay_all()` but not called by any timer
- `session_summaries` table has no TTL
- OpenMemory has no local cleanup
- Memory entries accumulate without pruning

### Spec

**Create:** `/root/.hermes/scripts/audit_memory.py`
```python
# 1. Hebbian memory:
#    - Run decay_all() (WEIGHT_FLOOR=0.5, min_age_days=7)
#    - Delete synapses with weight < 0.6 (effectively dead)
#    - Report: total nodes, total synapses, avg weight, dead synapses

# 2. session_summaries:
#    - Delete entries older than 30 days
#    - Report: entries deleted, remaining count

# 3. OpenMemory (via MCP query):
#    - Query memories not reinforced in 30+ days
#    - Report list for manual review (don't auto-delete)
```

**Create:** `systemd/hermes-memory-audit.timer`
- Runs weekly (Sunday 04:00 UTC)
- Writes results to `data/memory_audit.json`

**Modify:** `hebbian_engine.py`
- Add `cleanup_dead_synapses()` method
- Add `prune_old_sessions(days=30)` method

### Effort: Low (2-3 hours)

---

## 4. Weekly Signal Quality Self-Check

### Current State
- `signal_decay_detector.py` runs every 6h (hard block at WR<20%, n>=3)
- `signal_rotator.py` runs every 4h (max 2 changes/cycle)
- `monte_carlo_gate.py` blocks if P(profit)<35%
- `signal_quality_tracker.py` tracks metrics
- No weekly aggregation or trend analysis

### Spec

**Create:** `/root/.hermes/scripts/weekly_signal_review.py`
```python
# Runs weekly (Sunday 05:00 UTC)
# 
# 1. Aggregate 7-day performance by signal type:
#    - WR, PnL, trade count, profit factor
#    - Compare to 30-day baseline
#
# 2. Detect degradation:
#    - Any signal with WR drop >15% vs baseline → ALERT
#    - Any signal with PnL negative for 7+ days → REVIEW
#    - Overall system WR < 10% → CRITICAL ALERT
#
# 3. Generate report:
#    - data/weekly_signal_review.json
#    - Summary in pipeline.log
#
# 4. Auto-actions (if CRITICAL):
#    - Pause trading (set LIVE_TRADING_ENABLED=False)
#    - Write alert to data/alerts.json
```

**Create:** `systemd/hermes-weekly-review.timer`
- Runs Sunday 05:00 UTC

**Modify:** `run_pipeline.py`
- Check `data/alerts.json` on startup → pause if critical alert exists

### Effort: Medium (4-5 hours)

---

## 5. Security Documentation

### Current State
- No SECURITY.md
- `.secrets.local` gitignored
- `_secrets.py` centralizes loading
- `bug_hunter.py` checks for hardcoded secrets
- No dependency auditing
- No API key rotation schedule

### Spec

**Create:** `/root/.hermes/SECURITY.md`
```markdown
# Security Architecture

## Principles
- Polling over webhooks (no inbound ports except nginx)
- Secrets in .secrets.local (gitignored)
- Centralized secret loading via _secrets.py
- Kill switches: LIVE_TRADING_ENABLED + runtime JSON

## Secrets Management
- Location: .secrets.local, .env
- Loading: _secrets.py (centralized)
- Rotation: quarterly (exchange API keys)
- Min permissions: read-only where possible

## Dependency Security
- Audit: weekly via pip-audit
- Pinning: requirements.txt with pinned versions
- CVE monitoring: check HIGH/CRITICAL weekly

## Network Security
- No inbound ports (polling architecture)
- nginx: only public surface (port 443)
- Rate limiting on dashboard

## Incident Response
- If vulnerability found: pause trading, rotate keys, update deps
- If breach suspected: rotate all keys immediately, check logs
```

**Create:** `/root/.hermes/scripts/check_key_rotation.py`
```python
# Checks .secrets.local modification date
# Alerts if any key older than 90 days
# Reports to data/key_rotation_status.json
```

**Modify:** `.gitignore`
- Ensure all secret patterns covered

### Effort: Low (2-3 hours)

---

## Implementation Order

| # | Action | Effort | Dependencies |
|---|--------|--------|--------------|
| 1 | Security documentation | Low | None |
| 2 | Dependency audit | Low | None |
| 3 | Memory staleness audit | Low | None |
| 4 | Pipeline watchdog | Medium | None |
| 5 | Weekly signal review | Medium | #4 (watchdog) |

**Total estimated effort:** 15-19 hours

## Files to Create

| File | Purpose |
|------|---------|
| `scripts/audit_dependencies.py` | Weekly pip-audit |
| `scripts/pipeline_watchdog.py` | Stall detection |
| `scripts/audit_memory.py` | Hebbian/OpenMemory cleanup |
| `scripts/weekly_signal_review.py` | Signal quality trends |
| `scripts/check_key_rotation.py` | API key age check |
| `SECURITY.md` | Security architecture docs |
| `requirements.txt` | Pinned dependencies |
| `systemd/hermes-dependency-audit.timer` | Weekly dependency check |
| `systemd/hermes-watchdog.timer` | 2-min pipeline health |
| `systemd/hermes-memory-audit.timer` | Weekly memory cleanup |
| `systemd/hermes-weekly-review.timer` | Weekly signal review |

## Files to Modify

| File | Change |
|------|--------|
| `run_pipeline.py` | Add watchdog heartbeat, alert check |
| `hebbian_engine.py` | Add cleanup methods |
| `.gitignore` | Verify secret patterns |
