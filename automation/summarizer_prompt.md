# Automations Results Summarizer

You are summarizing the results of all Hermes automations. Run every 12 hours.

## Step 1: Check All Automation Outputs

### 1. Auto-1hr (hourly trade analyzer)
```bash
# Last run
journalctl -u hermes-auto-1hr.service --since "12 hours ago" --no-pager | grep -E "Summary|Changes Implemented|CRITICAL|disabled|blacklist" | tail -20

# What changed
journalctl -u hermes-auto-1hr.service --since "12 hours ago" --no-pager | grep -E "Edit scripts|hermes_constants|decider_run" | tail -10
```

### 2. Health Monitor (hourly)
```bash
# Last 12h of health reports
journalctl -u hermes-health-monitor.service --since "12 hours ago" --no-pager | grep -E "=== Hermes Health|PIPELINE|MARKET|ALERTS" | tail -30
```

### 3. Signal Reporter (6h)
```bash
# Last signal report
journalctl -u hermes-signal-reporter.service --since "12 hours ago" --no-pager | grep -E "=== Signal|WINNERS|LOSERS|RECOMMENDATIONS" | tail -20
```

### 4. Blacklist Tester (12h)
```bash
# Check blacklist trial status
cat /root/.hermes/automation/blacklist_test_log.md
```

### 5. Pipeline Performance
```bash
# Trades in last 12h
journalctl -u hermes-pipeline.service --since "12 hours ago" --no-pager | grep "Portfolio:" | tail -5

# Current PnL
journalctl -u hermes-pipeline.service --since "5 minutes ago" --no-pager | grep "Portfolio:"
```

## Step 2: Check Trading Log for Changes

```bash
# Recent changes
tail -100 /root/.hermes/automation/trading_log.md | grep -E "^## |Changes Implemented|disabled|blacklist|CRITICAL"
```

## Step 3: Compile Summary

### Report Format

```
=== 12-Hour Automations Summary ===
Period: YYYY-MM-DD HH:MM to YYYY-MM-DD HH:MM UTC

PIPELINE PERFORMANCE:
- Trades opened: X
- Trades closed: X
- Win rate: X%
- PnL: X%
- Current positions: X open

AUTO-1HR CHANGES:
1. [time] — Change 1
2. [time] — Change 2
3. [time] — Change 3

SIGNAL STATUS:
- Active signals: X
- Disabled signals: X
- Best performer: [signal] (X% WR)
- Worst performer: [signal] (X% WR)

MARKET CONDITIONS:
- Regime: X LONG / X SHORT / X NEUTRAL
- Trend: [trending/ranging/quiet]
- Volatility: [high/medium/low]

BLACKLIST TRIALS:
- Tokens in trial: X
- Trials completed: X
- Kept: X
- Re-blacklisted: X

ALERTS:
- [alert 1]
- [alert 2]

KEY DECISIONS NEEDED:
1. [decision 1]
2. [decision 2]
```

## Step 4: Save Report

Save the report to `automation/summaries/YYYY-MM-DD_HH.md` (create directory if needed).

## Step 5: Check for Issues

Flag if:
- PnL < -3% in 12h → CRITICAL
- >3 consecutive losses → WARN
- Signal generation stopped for >2h → WARN
- Timer missed a run → WARN
- Blacklist trial completed with <3 trades → INSUFFICIENT DATA

## Key File Paths
- Trading log: `automation/trading_log.md`
- Blacklist log: `automation/blacklist_test_log.md`
- Signal report: `automation/signal_report.md`
- Summaries: `automation/summaries/`
- Pipeline logs: `journalctl -u hermes-pipeline.service`
- Auto-1hr logs: `journalctl -u hermes-auto-1hr.service`
