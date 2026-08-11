# Spec: Closing Gaps from Video Analysis

**Source:** "How To Build A Self-Improving AI Trading Agent" (YouTube)
**Date:** 2026-08-11
**Status:** Partial — #1 and #3 implemented

## Context

The video describes a self-improving trading agent using Hermes-like concepts. Our system already implements most of what's described, but the analysis surfaced four gaps:

1. No structured weekly reflection cycle
2. No PnL/Sharpe in the learning loop (WR-only)
3. No goal progress tracking
4. Slow kill threshold for underperforming signals

## Changes

### 1. Goal Progress State File

**What:** Write current performance + targets to a JSON file that self_learner and CEO can query.

**Why:** Right now goals are hardcoded constants in hermes_constants.py. No runtime visibility into "how close are we to the target."

**File:** `/root/.hermes/data/goal_progress.json`

**Schema:**
```json
{
  "updated_at": "2026-08-11T12:00:00Z",
  "targets": {
    "win_rate": 0.40,
    "daily_pnl": 0.05,
    "min_sharpe_30d": 1.0
  },
  "current": {
    "win_rate_30d": 0.38,
    "daily_pnl_7d": 0.03,
    "sharpe_30d": 0.85,
    "total_trades_30d": 142,
    "consecutive_losses": 2
  },
  "trend": {
    "win_rate_delta_7d": 0.02,
    "pnl_delta_7d": 0.01
  }
}
```

**Implementation:**
- self_learner.py already queries signal_outcomes — add a block at the end that computes these metrics and writes the file
- CEO prompt reads this file to understand current state without recomputing
- Trivial change: ~30 lines in self_learner.py

---

### 2. PnL + Sharpe in Self-Learner Tuning

**What:** Add PnL-based and Sharpe-based decisions alongside the existing WR-based logic.

**Why:** WR alone can be gamed. A signal with 55% WR but tiny wins and huge losses looks good on paper but loses money. Adding Sharpe catches this.

**File:** `/root/.hermes/scripts/self_learner.py`

**Current logic (simplified):**
```
if WR < 30%: tighten
if WR > 60%: loosen
```

**New logic:**
```
sharpe = compute_sharpe(trades_30d)
pnl_30d = sum(trade.pnl for trade in trades_30d)

if WR < 30% OR sharpe < 0.5 OR pnl_30d < -1.0:
    tighten
if WR > 60% AND sharpe > 1.5 AND pnl_30d > 2.0:
    loosen
```

**Sharpe calculation:**
```python
def compute_sharpe(trades, risk_free=0.0):
    returns = [t['pnl_pct'] for t in trades]
    if len(returns) < 10:
        return None  # not enough data
    mean_r = sum(returns) / len(returns)
    std_r = (sum((r - mean_r)**2 for r in returns) / len(returns)) ** 0.5
    if std_r == 0:
        return 0
    return (mean_r - risk_free) / std_r
```

**Effort:** ~40 lines added to self_learner.py. No new dependencies.

---

### 3. Faster Kill Threshold

**What:** Auto-disable a signal if its 50-trade PnL is negative OR it has 10+ consecutive losses.

**Why:** Currently a signal can hover at 30-35% WR for weeks before CEO kills it. This adds a mechanical kill that doesn't wait for CEO review.

**File:** `/root/.hermes/scripts/self_learner.py` (add to existing tuning loop)

**Logic:**
```python
trades_50 = query_last_n(signal_type, n=50)
pnl_50 = sum(t['pnl_usdt'] for t in trades_50)
max_consec = max_consecutive_losses(trades_50)

if pnl_50 < -2.0 or max_consec >= 10:
    # Disable signal
    disable_signal(signal_type)
    log_kill(signal_type, pnl_50, max_consec)
```

**Safety:** Only fires if we have 50+ trades (avoids killing on small samples). Logs the kill reason. CEO can override.

**Effort:** ~25 lines in self_learner.py.

---

### 4. Scheduled Weekly Review Prompt

**What:** Add a systemd timer that fires the CEO every Sunday at 18:00 UTC with a weekly review prompt.

**Why:** Currently CEO fires on silence detection (away_detector.py). A proactive weekly cycle catches drift between sessions.

**Files:**
- New: `/root/.hermes/automation/weekly_review_prompt.md`
- New: systemd timer + service unit

**Timer unit:**
```ini
[Unit]
Description=Hermes Weekly CEO Review

[Timer]
OnCalendar=Sun 18:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Prompt content:**
```markdown
Weekly review. Read goal_progress.json. For each active signal:
1. WR, PnL, Sharpe over last 7d and 30d
2. Trend: improving or decaying?
3. Any signal with 7d PnL < -$1.00 → recommend disable
4. Any signal with 7d WR > 65% → recommend loosen params
5. Compare current state to targets in goal_progress.json
6. Output a one-paragraph status + recommended actions
```

**Effort:** 2 systemd files + 1 prompt file. ~15 lines total.

---

## Files Changed

| File | Change |
|------|--------|
| `scripts/self_learner.py` | Add Sharpe/PnL logic, kill threshold, goal_progress.json writer |
| `automation/weekly_review_prompt.md` | New — weekly review prompt |
| `systemd/weekly-review.timer` | New — Sunday 18:00 UTC timer |
| `systemd/weekly-review.service` | New — calls CEO with review prompt |

## Verification

1. Run `self_learner.py` manually — check `goal_progress.json` is written
2. Check Sharpe calculation against known data (inject test trades)
3. Verify kill threshold fires at 10 consecutive losses (inject test data)
4. `systemctl list-timers` — confirm weekly-review.timer shows next run
5. CEO prompt loads correctly when triggered
