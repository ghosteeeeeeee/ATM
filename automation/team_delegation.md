# Automation Team — Delegation Matrix

## Team Members & Responsibilities

| Member | Timer | Responsibility | Delegated By |
|--------|-------|----------------|--------------|
| signal_compactor | 1 min | Compact signals into hotset | Pipeline |
| signal_analyst | 1 min | Score signals 0-100 | Pipeline |
| self_learner | Daily 06:00 | Adjust parameters | CEO |
| bug_hunter | 8 hours | Find bugs | CEO |
| away_detector | 15 min | Call CEO when T away | System |
| price_collector | 1 min | Collect prices | Pipeline |
| hl_sync_guardian | Daemon | Sync with HL | Pipeline |
| pipeline | 1 min | Run trading loop | System |

## CEO Delegation Rules

### When CEO Identifies a Problem

| Problem | Delegate To | Task |
|---------|-------------|------|
| Signal has 0% WR | self_learner | Disable signal |
| Bug found | bug_hunter | Fix bug |
| Signal needs tuning | self_learner | Adjust parameters |
| New signal needed | signal_analyst | Build signal |
| Token blacklisting | self_learner | Update blacklist |

### When CEO Monitors Progress

| Check | Frequency | How |
|-------|-----------|-----|
| Signals firing | Every 6h | Query signal_outcomes |
| Parameters adjusted | Every 6h | Check self_learning_log.json |
| Bugs fixed | Every 8h | Check bug_report.json |
| Pipeline health | Every 6h | Check systemctl status |

### Delegation Format in Kanban

```
## CEO DECISIONS
- [ ] 2026-08-05 00:50 — DELEGATE to self_learner: Disable signals with 0% WR
- [ ] 2026-08-05 00:50 — DELEGATE to bug_hunter: Fix connection leak in signal_analyst.py
- [ ] 2026-08-05 00:50 — DELEGATE to signal_analyst: Build new mean-reversion signal
```

### Monitoring Checklist

CEO checks on next run:
1. Were delegated tasks completed? (Check kanban DONE)
2. Are team members producing output? (Check their log files)
3. Is the system improving? (Check WR trend)
