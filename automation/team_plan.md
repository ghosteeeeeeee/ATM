# Hermes Automation Team Plan

## Current Members (Active)

| Member | Schedule | Role | Status |
|--------|----------|------|--------|
| WASP | 30min | Bug detector, anomaly finder | ACTIVE |
| health-monitor | Hourly | Pipeline health | ACTIVE |
| auto-1hr | Hourly | Trade analysis | ACTIVE |
| signal-reporter | 6h | Signal performance | ACTIVE |
| blacklist-tester | 12h | Token trials | ACTIVE |
| summarizer | 12h | Results summary | ACTIVE |
| upgrade-implementer | 12h | Plan implementation | ACTIVE |
| daily-orchestrator | 12h | Implementation pipeline | ACTIVE |
| CEO | 24h | Strategic oversight | ACTIVE |

## Proposed New Members

### 1. Risk Manager (HIGH PRIORITY)
- **Purpose**: Monitor max drawdown, position correlation, stop trading if limits exceeded
- **Schedule**: Every 5 minutes (or continuous)
- **Responsibilities**:
  - Track real-time PnL
  - Monitor max drawdown (daily, weekly, monthly)
  - Check position correlation
  - Emergency stop if limits exceeded
  - Alert CEO when risk limits approached
- **Files**: `automation/risk_manager_prompt.md`

### 2. Data Quality Checker (HIGH PRIORITY)
- **Purpose**: Ensure price data is clean, no gaps, no stale data
- **Schedule**: Every hour
- **Responsibilities**:
  - Check price data freshness
  - Detect gaps in price history
  - Validate candle data integrity
  - Alert on data anomalies
- **Files**: `automation/data_quality_prompt.md`

### 3. Backtester (MEDIUM PRIORITY)
- **Purpose**: Validate signals on historical data before deploying
- **Schedule**: On demand (when new signal proposed)
- **Responsibilities**:
  - Run backtests on proposed signals
  - Calculate risk-adjusted returns
  - Stress test under different market conditions
  - Report results to CEO
- **Files**: `automation/backtester_prompt.md`

### 4. Market Regime Detector (MEDIUM PRIORITY)
- **Purpose**: Identify regime changes, adjust strategy accordingly
- **Schedule**: Every 4 hours
- **Responsibilities**:
  - Monitor market regime (trending/ranging/volatile)
  - Detect regime shifts
  - Recommend strategy adjustments
  - Update regime parameters
- **Files**: `automation/regime_detector_prompt.md`

### 5. Audit Logger (LOW PRIORITY)
- **Purpose**: Log all parameter changes for debugging
- **Schedule**: Continuous (event-driven)
- **Responsibilities**:
  - Log all hermes_constants.py changes
  - Track who made what change and when
  - Provide audit trail for debugging
  - Archive old logs
- **Files**: `automation/audit_logger_prompt.md`

## CEO Recommendations (2026-08-01)

### Verdict: Build 2, Skip 3

| Proposed | Decision | Why |
|----------|----------|-----|
| Risk Manager | **BUILD — P1** | No equivalent exists. Emergency stop + drawdown monitoring is non-negotiable for capital protection. |
| Data Quality Checker | **BUILD — P2** | Ad-hoc checks exist in 5+ files but no centralized gate. Worth having, but not urgent. |
| Backtester | **SKIP** | We already have `trading-mcp_backtest_strategy` and `compare_strategies`. Building a custom one is YAGNI. |
| Market Regime Detector | **SKIP** | `15m_regime_scanner.py` and `4h_regime_scanner.py` already run on systemd timers. This duplicates them. |
| Audit Logger | **SKIP** | Git history + existing logs cover this. A separate service for "who changed what" is overkill when `git log` exists. |

### Implementation Priority

1. **Risk Manager** — Build first, fills real gap
2. **Data Quality Checker** — Build after Risk Manager is live

### Rationale

> "Don't add automations that duplicate existing timers — more services = more things to debug at 3am."

## Implementation Priority

1. ~~**Risk Manager**~~ — **APPROVED BY CEO** — Build first
2. ~~**Data Quality Checker**~~ — **APPROVED BY CEO** — Build second
3. ~~**Market Regime Detector~~** — **SKIPPED** — Duplicates existing
4. ~~**Backtester**~~ — **SKIPPED** — YAGNI
5. ~~**Audit Logger**~~ — **SKIPPED** — Git covers this

## Timing Considerations

Current load:
- Hourly: 2 automations
- 6-hourly: 1 automation
- 12-hourly: 4 automations
- 24-hourly: 1 automation

Adding Risk Manager (5min) and Data Quality (hourly) would increase load moderately.

## Notes

- Risk Manager should have ability to pause trading (critical safety feature)
- Data Quality Checker should run before signal generation
- Backtester should be triggered on demand, not on schedule
- Market Regime Detector should feed into CEO decisions
- Audit Logger should be event-driven, not polling
