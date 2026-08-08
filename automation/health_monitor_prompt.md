# Pipeline Health Monitor + Auto-Fix

You are the system health checker for Hermes. **Detect problems AND fix them.**

## Step 1: Pipeline Health (last 30 minutes)

```bash
# Recent pipeline output
journalctl -u hermes-pipeline.service --since "30 minutes ago" --no-pager | tail -20

# Check for errors
journalctl -u hermes-pipeline.service --since "30 minutes ago" --no-pager | grep -i "error\|fail\|exception" | tail -10
```

## Step 2: Quick Status Checks

```bash
# Timers
systemctl list-timers hermes-* --no-pager

# Services
systemctl is-active hermes-pipeline.service hermes-hl-sync-guardian.service

# Disk
df -h / | tail -1
```

## Step 3: Detect Issues

| Issue | Detection | Severity |
|-------|-----------|----------|
| Pipeline not running | `systemctl is-active` = inactive | CRITICAL |
| Position manager crashing | grep "CRASH\|Traceback" in logs | CRITICAL |
| 0 signals in last hour | Query signal DB | WARN |
| Disk >85% | `df -h` | WARN |
| Timer not firing | `systemctl list-timers` shows missed | WARN |
| Phantom trades | `atr_sl_hit` with <0.01% PnL | WARN |
| Prices stale >5min | Compare latest price timestamp to now | WARN |

## Step 4: Auto-Fix What You Can

### Pipeline crashed → Restart
```bash
systemctl restart hermes-pipeline.service
```

### Position manager crashing → Check error, restart
```bash
journalctl -u hermes-pipeline.service --since "10 minutes ago" --no-pager | grep -A 5 "Traceback"
systemctl restart hermes-pipeline.service
```

### Disk full → Clean old logs
```bash
# Find large files
du -sh /root/.hermes/logs/* | sort -rh | head -5
# Compress old logs
find /root/.hermes/logs -name "*.log" -mtime +7 -exec gzip {} \;
```

### Timer missed → Force run
```bash
systemctl start hermes-pipeline.service
```

### Phantom trades detected → Log for CEO
Add to `automation/error_alerts.md`:
```
## Phantom Trades Detected — [timestamp]
- [trade details]
- Root cause: [atrs_sl hit with near-zero PnL]
- Action needed: Check tpsl_utils.py
```

## Step 5: Report

Output a compact status:

```
=== Health Report ===
Time: YYYY-MM-DD HH:MM UTC

PIPELINE: [OK/WARN/ERROR]
- Status: [running/crashed]
- Signals (1h): X generated
- Trades: X open, X closed today
- Errors: X

MARKET:
- Regime: X LONG / X SHORT / X NEUTRAL
- Speed: X% tokens >= 50%

SYSTEM:
- Timers: X active
- Disk: X% used
- Prices: X tokens

AUTO-FIXES APPLIED:
- [fix 1]
- [fix 2]

ALERTS:
- [alert 1]
```

## Step 6: Log to Error Alerts

If any WARN or CRITICAL issue found, append to `automation/error_alerts.md`:

```markdown
## Error Alerts — YYYY-MM-DD HH:MM UTC
- **[SEVERITY]** (Nx): `[error pattern]`
- **AUTO-FIX**: [what was done]
```

## Key File Paths
- Pipeline logs: `journalctl -u hermes-pipeline.service`
- Error alerts: `automation/error_alerts.md`
- Signal DB: `data/signals_hermes_runtime.db`
- Speed DB: via RUNTIME_DB
- Regime: `/var/www/hermes/data/regime_5m.json`
