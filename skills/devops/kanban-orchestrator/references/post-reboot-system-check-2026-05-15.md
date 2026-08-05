# Post-Reboot System Check Results — 2026-05-15

## Running Services

| Service | Status | Notes |
|---------|--------|-------|
| hl-sync-guardian.py | RUNNING (PID 41017) | Primary trading guardian |
| hermes-price-collector.service | RUNNING | Price data aggregation |
| hermes-metrics.service | RUNNING | System metrics collection |
| hermes-coding-mcp.service | RUNNING | MCP server |
| hermes-pipeline.service | OK | Ran at 06:59 — 2/5 open, +8.61% PnL today |
| hermes-1m-candle.service | OK | Ran at 06:59 — 46272 windows, 182 tokens |
| hermes-zscore-pump-hunter.service | INACTIVE | Correctly disabled (killswitch ZSCORE_PUMP_ENABLED=False) |

## Failed Services

| Service | Status | Fix |
|---------|--------|-----|
| hermes-git-release.service | failed | wandb path issue — non-critical |
| hermes-trading-checklist.service | failed | Missing `/root/.hermes/data/trailing_stops.json` |
| hermes-self-close-watcher.service | inactive | Expected — UNPROTECTABLE_COINS=frozenset() disables it |
| hermes-pump-hunter.service | inactive | Expected — disabled |

## Quick Fixes

```bash
# Fix missing trailing_stops.json
sudo touch /root/.hermes/data/trailing_stops.json
```

## ZSCORE_PUMP Never Started

zscore-pump was NEVER going to start post-reboot because:
1. The killswitch `ZSCORE_PUMP_ENABLED = False` was added during the 04:30 session
2. Pre-existing positions (GRIFFAIN, EIGEN, DYDX etc.) were from before the killswitch
3. User correctly called this out — never assume a feature that never worked starts working after reboot

## Correct System Check Commands

```bash
# Check running services (non-sudo — avoids hostname resolution errors)
systemctl list-units --type=service --state=running | grep -E 'hermes|hl|signal|guardian'

# Check timers (often used for scheduled trading tasks)
systemctl list-units --type=timer --state=active | grep -E 'hermes|hl|signal'

# Check pipeline log (filter by date since log is huge)
journalctl -u hermes-pipeline --since "1 hour ago" | tail -30

# Check guardian directly
ps aux | grep hl-sync-guardian | grep -v grep
```

## DB Query — Open Positions at 07:00 UTC

```
TAO SHORT: entry=302.750, SL=303.365 (+0.20% above entry), pnl=-0.21%, lowest_price=301.256
2Z SHORT: entry=0.100350, SL=0.101052 (+0.70% above entry), pnl=+0.25%, lowest_price=0
ZK SHORT: entry=0.017633, SL=0.017756 (+0.70% above entry), pnl=+1.13%, lowest_price=0
```

All THREE open SHORTs have SL above entry — same bug as FIL SHORT (2026-05-14). See `references/short-sl-above-entry-bug-2026-05-15.md` for fix.