---
name: post-reboot-health-check
description: Correct sequence for verifying Hermes trading system health after a reboot or service disruption. Covers pipeline vs standalone timers, killswitch verification, and critical service states.
category: trading
author: Hermes
created: 2026-05-15
---

# Post-Reboot Health Check — Correct Sequence

## The Core Lesson

**Don't theorize about what should be running — verify against journalctl and pipeline.log.**

The assistant initially assumed `signal_compactor` was dead because the standalone timer (`hermes-signal-compactor.timer`) was inactive. The user correctly pushed back on this. In reality:

1. `run_pipeline.py` runs signal_compactor as step #1 in `STEPS_EVERY_MIN` every 1 minute
2. The standalone `hermes-signal-compactor.timer` is **disabled by design** — it's redundant, not broken
3. `signal_compactor` WAS running (confirmed by pipeline.log at line 2834341)

**Verification before speculation is the only correct approach.**

---

## Investigation Sequence

### Step 1 — Check Pipeline Log (Canonical Source)

```bash
# Pipeline log is the canonical record of what actually ran
tail -50 /root/.hermes/logs/pipeline.log
grep "Running signal_compactor\|Running decider_run\|Running signals_runner" /root/.hermes/logs/pipeline.log | tail -20
grep "Compaction done\|hotset.json" /root/.hermes/logs/pipeline.log | tail -10

# Find recent May entries (log is large, date filter is essential)
awk '/2026-05-15 04:/ {print NR": "$0}' /root/.hermes/logs/pipeline.log | head -30
```

The pipeline log is at `/root/.hermes/logs/pipeline.log` — 2.8M lines, with entries from April. Always filter by date when looking for recent entries.

### Step 2 — Check Running Processes

```bash
ps aux | grep -E 'signal_gen|signal_runner|guardian|hl-sync|position_manager|decider|hyperliquid' | grep -v grep
```

### Step 3 — Check systemd Services + Timers

```bash
# Running services
systemctl list-units --type=service --state=running | grep -E 'hermes|signal|guardian|hl|trading'

# All timers and their next fire time
systemctl list-timers --all | grep -E 'zscore|pump|signal|decider|compactor|guardian'

# Failed services
systemctl list-units --type=service --state=failed | grep hermes

# Per-service journal (for kill switch verification)
journalctl -u hermes-zscore-pump-hunter.service --since "4 hours ago" | tail -20
```

### Step 4 — Kill Switch Verification

Kill switches in `hermes_constants.py` block signals at the **function entry**, before any trading action:

```python
# Example: ZSCORE_PUMP_ENABLED=False in hermes_constants.py
from hermes_constants import ZSCORE_PUMP_ENABLED
if not ZSCORE_PUMP_ENABLED:
    log("ZSCORE_PUMP_ENABLED=False — block zscore_pump from firing", "OFF")
    return []  # completely silent
```

The journal proves it's working — every minute:
```
[OFF] ZSCORE_PUMP_ENABLED=False — block zscore_pump from firing
[DONE] ZScore Pump Hunter cycle complete.
```

Kill switch is effective when: the service/timer runs but the guard at the top of `scan_and_fire()` returns early. The timer fires but no trades execute.

---

## Critical Distinction: Timer Disabled vs Script Dead

| State | Meaning | Action |
|-------|---------|--------|
| Timer: `inactive (dead)` + service never fired | Timer is OFF/DISABLED | Check if script runs via another path (pipeline) |
| Timer: `active (waiting)` | Timer is running | Check if service actually fired (journalctl) |
| Service: runs every minute, exits immediately | Kill switch active | CONFIRMED WORKING — not a problem |

**Example:** `hermes-signal-compactor.timer` shows `inactive (dead)` but `signal_compactor` IS running. The standalone timer is disabled because `run_pipeline.py` (via cron/timer) handles it in `STEPS_EVERY_MIN`. The disabled timer is **correct by design**, not a failure.

---

## Common Post-Reboot Issues

### 1. trailing_stops.json missing → hermes-trading-checklist fails

```bash
# Fix:
touch /root/.hermes/data/trailing_stops.json
systemctl restart hermes-trading-checklist.service
```

### 2. signal-purge.timer has invalid calendar syntax

```bash
# Wrong (rejected by systemd):
OnCalendar=*:0/1:00:00  # too many fields

# Correct:
OnCalendar=*:0/1        # every hour at :00 and :01
```

```bash
# Fix:
cat > /etc/systemd/system/hermes-signal-purge.timer << 'EOF'
[Unit]
Description=Signal Purge Timer — every 1 hour
[Timer]
OnBootSec=60
OnCalendar=*:0/1
Persistent=true
[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl start hermes-signal-purge.timer
```

### 3. WASP service fails on Ollama API errors

The wasp log shows:
```
⚠️ [WARNING] ai-decider: No signals reviewed by AI in last 2h — Ollama may be down
❌ [ERROR] ollama: Generate request returned 400
```

This is a known pre-existing issue — Ollama endpoint returning 400. Not critical for live trading.

---

## Full Health Report Template

| Component | Status | Notes |
|-----------|--------|-------|
| **Guardian** (hl-sync-guardian) | ✅/❌ | PID, sync every Ns, X/X positions matched |
| **Pipeline** (run_pipeline.py) | ✅/❌ | Steps running: signal_compactor, decider_run, position_manager |
| **Hot-set** (hotset.json) | ✅/❌ | N entries, freshness |
| **Self-contained signals** | ✅/❌ | Kill switches confirmed via journalctl |
| **Failed services** | ❌ | List each with error from journal |
| **Broken timers** | ❌ | Calendar syntax error, etc. |

---

## Key Paths (Verify, Don't Assume)

```bash
# Hot-set (NOT /root/.hermes/hot-set.json):
/var/www/hermes/data/hotset.json

# Pipeline log:
/root/.hermes/logs/pipeline.log  # 2.8M lines, filter by date

# Guardian log:
/root/.hermes/logs/sync-guardian.log  # 10MB, recent entries only

# Kill switches in:
/root/.hermes/scripts/hermes_constants.py

# Self-contained signal executors:
/root/.hermes/scripts/zscore_pump_hunter.py   # ZSCORE_PUMP_ENABLED guard
/root/.hermes/scripts/pump_hunter.py           # PUMP_HUNTER_ENABLED guard
```

---

## Lessons Learned 2026-05-15

1. **Timer being disabled is not always a failure** — it might be redundant by design. Check if the script runs via another path (pipeline) before declaring it dead.

2. **zscore-pump timer resumed post-reboot** — the timer was always running, the killswitch was what stopped it. Before the killswitch (added during 04:30 session), it had fired trades in GRIFFAIN, EIGEN, DYDX, etc. — those positions were from before the killswitch was added, not post-reboot new activity.

3. **journalctl is the kill-switch proof** — not the pipeline log, not assumptions. Every minute of output shows the OFF/OFF block.

4. **The pipeline.log IS the canonical record** for what the trading system is doing. It's the first place to look, not process lists or timer states.

5. **pipeline.log is large (2.8M lines)** — always filter by date (`awk '/2026-05-15 04:/'`) or line range when looking for recent entries.