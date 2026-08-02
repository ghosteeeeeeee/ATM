# Hermes Automation Plan

## Automations to Create

### 1. Pipeline Health Monitor + System Status Dashboard
- **Status:** ACTIVE
- **Schedule:** Every hour at :20 (30min offset from auto-1hr)
- **Purpose:** Check pipeline health, signal generation, trade execution, show system status
- **File:** `automation/health_monitor_prompt.md`
- **Script:** `automation/run_health_monitor.sh`
- **Systemd:** `hermes-health-monitor.timer` / `hermes-health-monitor.service`
- **First run:** 2026-08-01 13:37 UTC ✓

### 2. Signal Performance Reporter
- **Status:** ACTIVE
- **Schedule:** Every 6 hours
- **Purpose:** Calculate WR by signal type, flag losers, suggest changes
- **File:** `automation/signal_reporter_prompt.md`
- **Script:** `automation/run_signal_reporter.sh`
- **Systemd:** `hermes-signal-reporter.timer` / `hermes-signal-reporter.service`
- **First run:** 2026-08-01 13:43 UTC ✓

### 3. Auto-1hr Results Summarizer
- **Status:** ACTIVE
- **Schedule:** Every 12 hours
- **Purpose:** Summarize all automation outputs, pipeline performance, key decisions
- **File:** `automation/summarizer_prompt.md`
- **Script:** `automation/run_summarizer.sh`
- **Systemd:** `hermes-summarizer.timer` / `hermes-summarizer.service`
- **First run:** 2026-08-01 13:44 UTC ✓

### 4. Blacklist Tester
- **Status:** ACTIVE
- **Schedule:** Every 12 hours
- **Purpose:** Rotate blacklisted tokens for trials, evaluate performance
- **File:** `automation/blacklist_tester_prompt.md`
- **Systemd:** `hermes-blacklist-tester.timer` / `hermes-blacklist-tester.service`
- **First run:** 2026-08-01 12:52 UTC ✓

### 5. Upgrade Implementer
- **Status:** ACTIVE
- **Schedule:** Every 12 hours
- **Purpose:** Scan plans/, evaluate projects, implement improvements progressively
- **File:** `automation/upgrade_implementer_prompt.md`
- **Script:** `automation/run_upgrade_implementer.sh`
- **Systemd:** `hermes-upgrade-implementer.timer` / `hermes-upgrade-implementer.service`
- **First run:** 2026-08-01 13:49 UTC ✓
- **Features:** Progressive difficulty (Level 1-4), audit trail, success tracking

### 6. Daily Orchestrator
- **Status:** ACTIVE
- **Schedule:** Every 12 hours
- **Purpose:** Autonomous pipeline manager, coordinate all automations, implement improvements
- **File:** `automation/orchestrator_prompt.md`
- **Script:** `automation/run_orchestrator.sh`
- **Systemd:** `hermes-daily-orchestrator.timer` / `hermes-daily-orchestrator.service`
- **First run:** 2026-08-01 17:22 UTC ✓
- **Features:** Gather intelligence, analyze, implement, validate, report

### 7. CEO
- **Status:** ACTIVE
- **Schedule:** Every 24 hours (staggered from orchestrator)
- **Purpose:** Strategic oversight, capital allocation, risk management, system governance
- **File:** `automation/ceo_prompt.md`
- **Script:** `automation/run_ceo.sh`
- **Systemd:** `hermes-ceo.timer` / `hermes-ceo.service`
- **First run:** 2026-08-01 17:27 UTC ✓
- **Features:** Performance review, capital allocation, strategic decisions, system health

## Existing Automations

| Timer | Schedule | Purpose |
|-------|----------|---------|
| hermes-auto-1hr | Every hour at :50 | Analyze trades, tune params |
| hermes-blacklist-tester | Every 12 hours | Test blacklisted tokens |
| hermes-pipeline | Every minute | Main trading pipeline |
| hermes-price-collector | Every ~1min | Collect prices |
| hermes-15m-regime-scanner | Every 15min | Regime analysis |

## Timing Layout

```
:00 - pipeline
:05 - price collector
:15 - regime scanner
:20 - health monitor (NEW)
:50 - auto-1hr analyzer
```
