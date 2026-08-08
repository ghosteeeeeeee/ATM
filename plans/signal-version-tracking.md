# Spec: Signal Version Tracking + Regression Detection

**Problem**: We tune signal params, performance degrades, we can't roll back. No version history, no regression alerts.

**Root cause**: Params are edited directly in `hermes_constants.py`. No record of what was changed, when, or what the performance was before/after.

**Solution**: Version tracking + regression monitoring + auto-rollback.

---

## 1. Param Version Tracking

Every signal param change gets logged with:
- What changed (param name, old value, new value)
- When (timestamp)
- Who (human, CEO, self_learner, auto_1hr)
- Performance at time of change (WR, PnL, trade count)
- Reason (if available)

### Storage

**New file: `data/signal_versions.json`**
```json
{
  "bb_bounce": {
    "versions": [
      {
        "version": 1,
        "timestamp": "2026-08-07T14:00:00Z",
        "params": {"RSI_OVERSOLD": 45, "RSI_OVERBOUGHT": 55, "BOUNCE_MIN_PCT": 0.03},
        "metrics": {"wr": 36.8, "pnl": -0.62, "trades": 19},
        "changed_by": "T",
        "reason": "Initial deploy"
      },
      {
        "version": 2,
        "timestamp": "2026-08-07T22:00:00Z",
        "params": {"RSI_OVERSOLD": 40, "RSI_OVERBOUGHT": 60, "BOUNCE_MIN_PCT": 0.05},
        "metrics": {"wr": 36.8, "pnl": -0.62, "trades": 19},
        "changed_by": "CEO",
        "reason": "Tighten filters — standalone WR too low",
        "prev_version": 1
      }
    ],
    "current_version": 2
  }
}
```

### Who Writes

| Change Source | Writes Version | How |
|---------------|----------------|-----|
| Human (T) | Manual | `python3 scripts/signal_version.py log bb_bounce --reason "tighten RSI"` |
| CEO | Auto | After editing hermes_constants.py |
| self_learner | Auto | After tuning params |
| auto_1hr | Auto | After implementing changes |

### Implementation

**New script: `scripts/signal_version.py`**
```python
"""Signal parameter version tracking."""

VERSIONS_FILE = '/root/.hermes/data/signal_versions.json'

def log_version(signal: str, params: dict, metrics: dict, 
                changed_by: str, reason: str = ''):
    """Log a new param version."""
    # Load existing versions
    # Append new version with timestamp
    # Save to file
    
def get_current_version(signal: str) -> dict:
    """Get current param version for a signal."""
    
def get_version_history(signal: str) -> list:
    """Get all versions for a signal."""
    
def rollback(signal: str, target_version: int) -> dict:
    """Get params from a previous version for rollback."""
```

---

## 2. Regression Detection

After each param change, compare performance before vs after. If performance degraded beyond threshold, alert.

### Metrics to Track

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Win rate change | -2% | -5% | -10% |
| PnL/trade change | -$0.02 | -$0.05 | -$0.10 |
| Trade count change | -20% | -50% | -80% |

### Detection Logic

```python
def check_regression(signal: str, lookback_hours: int = 48) -> dict:
    """Check if recent performance regressed vs previous version."""
    current = get_metrics(signal, lookback_hours)
    prev = get_metrics_before_last_change(signal)
    
    wr_delta = current['wr'] - prev['wr']
    pnl_delta = current['avg_pnl'] - prev['avg_pnl']
    
    if wr_delta < -10 or pnl_delta < -0.10:
        return {'status': 'CRITICAL', 'action': 'ROLLBACK'}
    elif wr_delta < -5 or pnl_delta < -0.05:
        return {'status': 'WARNING', 'action': 'INVESTIGATE'}
    return {'status': 'OK'}
```

### When to Check

- Every 6h (signal_reporter runs)
- After any param change (immediate check)
- CEO reads on every run

---

## 3. Auto-Rollback

When regression is detected, automatically revert to last known good version.

### Rollback Rules

| Regression Severity | Action |
|---------------------|--------|
| CRITICAL (-10% WR) | Auto-rollback + alert CEO |
| WARNING (-5% WR) | Alert CEO, no auto-rollback |
| OK | No action |

### Rollback Process

1. Detect regression (signal_reporter or CEO)
2. Identify last good version (from signal_versions.json)
3. Read params from that version
4. Apply to hermes_constants.py
5. Log rollback as new version
6. Git commit
7. Report to kanban

### Implementation

**Add to `scripts/signal_version.py`:**
```python
def auto_rollback(signal: str) -> bool:
    """Rollback to last known good version if regression detected."""
    regression = check_regression(signal)
    if regression['status'] != 'CRITICAL':
        return False
    
    # Find last good version
    versions = get_version_history(signal)
    good_version = find_last_good_version(versions)
    
    # Apply params
    apply_params(signal, good_version['params'])
    
    # Log as new version
    log_version(
        signal=signal,
        params=good_version['params'],
        metrics=get_current_metrics(signal),
        changed_by='auto-rollback',
        reason=f"Regression detected: {regression['reason']}"
    )
    
    return True
```

---

## 4. Dashboard / Monitoring

### New section in signal_report.md:

```
=== Signal Version Status ===

SIGNAL        | VERSION | LAST CHANGE | WR PREV | WR NOW | DELTA | STATUS
bb_bounce     | v2      | 6h ago      | 36.8%   | 42.9%  | +6.1% | ✅ IMPROVED
ma_100_cross  | v1      | 24h ago     | 51.1%   | 55.6%  | +4.5% | ✅ IMPROVED
range_finder  | v3      | 12h ago     | 45.0%   | 38.2%  | -6.8% | ⚠️ WARNING
continuation  | v1      | 48h ago     | NEW     | 65.0%  | N/A   | 🆕 MONITORING

RECENT ROLLBACKS:
- range_finder v3→v2 (2026-08-07 18:00) — WR dropped 8% after param change
```

### CEO reads on every run:
- Check for WARNING/CRITICAL signals
- Review rollback history
- Decide on further action

---

## 5. Integration with Existing Automations

### signal_reporter
- After reporting winners/losers, check regression for each signal
- Log version status in report
- Auto-rollback if CRITICAL

### auto_1hr
- Before making changes, log current version
- After making changes, log new version
- Check regression immediately

### CEO
- On every run, read version status from signal_report.md
- If CRITICAL regression detected, CEO decides: rollback or investigate
- CEO can manually rollback via `signal_version.py rollback`

### self_learner
- Before tuning, log current version
- After tuning, log new version with backtest metrics
- Auto-rollback if backtest shows regression

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `scripts/signal_version.py` | CREATE | Version tracking script |
| `data/signal_versions.json` | CREATE | Version storage |
| `automation/signal_reporter_prompt.md` | MODIFY | Add regression check |
| `automation/auto_1hr_prompt.md` | MODIFY | Add version logging |
| `automation/ceo_prompt.md` | MODIFY | Add version status to workflow |
| `AGENTS.md` | MODIFY | Document version tracking |

---

## Effort

- Version tracking script: 2 hours
- Regression detection: 1 hour
- Auto-rollback: 1 hour
- Integration with automations: 1 hour
- Dashboard: 30 min
- **Total: 5-6 hours**

## Expected Impact

| Before | After |
|--------|-------|
| Param change → hope it works | Param change → track + monitor |
| Regression found in 24-48h | Regression found in 6h |
| Manual rollback (grep git log) | Auto-rollback in 5 min |
| No version history | Full version history with metrics |
| "What did we change?" | "We changed X from A→B, WR went from Y→Z" |
