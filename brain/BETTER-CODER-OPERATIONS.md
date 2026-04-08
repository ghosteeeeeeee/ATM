# Better Coder Operations Guide

## System Overview

The Better Coder system consists of:
- **hermes-coding-mcp.service** - MCP server providing file ops, code search, command execution
- **hermes-better-coder.service** - Dispatcher that runs coding tasks from TASKS.md
- **hermes-better-coder.timer** - Triggers dispatcher every 30 minutes

## Service Management

### Start/Stop/Restart Commands

```bash
# MCP Server
sudo systemctl start hermes-coding-mcp.service
sudo systemctl stop hermes-coding-mcp.service
sudo systemctl restart hermes-coding-mcp.service

# Dispatcher (runs on timer, but can be triggered manually)
sudo systemctl start hermes-better-coder.service
sudo systemctl stop hermes-better-coder.service  # Just kills current run
sudo systemctl restart hermes-better-coder.service

# Timer
sudo systemctl start hermes-better-coder.timer
sudo systemctl stop hermes-better-coder.timer
```

### Check Service Status

```bash
# Quick status
systemctl status hermes-coding-mcp.service --no-pager
systemctl status hermes-better-coder.service --no-pager

# Show if timer is active
systemctl status hermes-better-coder.timer --no-pager
```

### Check Logs

```bash
# MCP Server logs (journald)
journalctl -u hermes-coding-mcp.service --no-pager -f

# Dispatcher logs (file-based)
tail -f /root/.hermes/logs/better-coder.log

# All hermes services
journalctl -u hermes.target --no-pager -f
```

## Self-Healing Features

### What Auto-Heals

| Failure Mode | How It Heals |
|--------------|---------------|
| MCP server crashes | systemd Restart=on-failure (5s delay) |
| MCP server unresponsive | WatchdogSec=30s auto-restart after missed watchdog pings |
| Dispatcher crashes | systemd Restart=on-failure (30s delay) |
| Lock file left behind | Automatically cleaned on next run |
| Concurrent dispatcher runs | File lock prevents (fcntl.LOCK_NB) |
| Task extraction fails | Falls back to empty task list |
| MCP tool timeout | 180s default timeout on execute_command |
| Low disk space | Skips dispatcher run, logs warning (500MB minimum) |

### Scheduled Health Monitors

| Timer | Schedule | Purpose |
|-------|----------|---------|
| hermes-better-coder-audit.timer | Sun 03:00 | Weekly self-healing audit (services + dry-run) |
| hermes-better-coder-health.timer | Daily 06:00 | Daily disk space check, cleanup if low |

### Manual Recovery

```bash
# Remove stale lock file
rm -f /tmp/hermes-better-coder.lock

# Force restart MCP server
sudo systemctl kill -s SIGKILL hermes-coding-mcp.service
# Server will auto-restart within 5 seconds

# Restart dispatcher immediately
systemctl restart hermes-better-coder.service
```

## Common Issues & Resolution

### Issue: Dispatcher stuck in "activating (auto-restart)"

**Cause:** Usually a stale lock file or bug in the script.

**Fix:**
```bash
rm -f /tmp/hermes-better-coder.lock
systemctl reset-failed hermes-better-coder.service
systemctl restart hermes-better-coder.service
```

### Issue: MCP server not responding

**Cause:** Process crashed or port conflict.

**Fix:**
```bash
sudo systemctl restart hermes-coding-mcp.service
```

### Issue: Tasks not being picked up

**Cause:** TASKS.md may not exist or have no open tasks.

**Fix:**
```bash
# Check if file exists
ls -la /root/.hermes/brain/TASKS.md

# Check contents
grep -c "\[ \]" /root/.hermes/brain/TASKS.md
```

### Issue: Dispatcher skips all tasks with "Disk space too low"

**Cause:** Less than 500MB free on /root or /tmp.

**Fix:**
```bash
# Check disk space
df -h /root /tmp

# Clean up temp files
find /tmp -type f -name '*.tmp' -mtime +1 -delete
rm -rf /tmp/*.tmp /var/tmp/*.tmp

# Re-run dispatcher
systemctl start hermes-better-coder.service
```

## Manual Dispatcher Run

To trigger the dispatcher manually outside the timer:

```bash
cd /root/.hermes
python3 /root/.hermes/scripts/run_better_coder.py
```

Or via systemd (one-shot):
```bash
systemctl start hermes-better-coder.service
```

## Architecture Notes

### Lock File Mechanism
- Location: `/tmp/hermes-better-coder.lock`
- Uses `fcntl.flock()` for process-level locking
- PID written to file for stale lock detection
- On next run, dead PIDs are detected and lock is cleaned

### MCP Server Transport
- Runs SSE on port 8765 (internal)
- Mount path: `/mcp`
- Actually uses Uvicorn on port 8000 internally

### Dispatcher Flow
1. Acquire lock file
2. Extract open tasks from TASKS.md
3. Create ParallelDispatcher with PipelineWorkers
4. Workers route tasks using pattern matching (simple) or embeddings (full)
5. Execute tool calls through MCP server
6. Release lock on completion

## Verification Commands

```bash
# Verify MCP server is responding
curl -s http://127.0.0.1:8000/health 2>/dev/null || echo "No health endpoint"

# Verify dispatcher can run
python3 /root/.hermes/scripts/run_better_coder.py --dry-run 2>/dev/null || echo "No dry-run"

# Check if services will start on boot
systemctl is-enabled hermes-coding-mcp.service
systemctl is-enabled hermes-better-coder.timer

# Memory usage
systemctl status hermes-coding-mcp.service --no-pager | grep Memory
```
