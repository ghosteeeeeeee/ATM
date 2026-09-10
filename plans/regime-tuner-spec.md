# Spec: Weekly Regime Tuner — Automated Signal Habitat Management

**Date:** 2026-09-09
**Status:** SPEC — not yet implemented
**Scope:** All active and disabled signals

---

## Problem

Currently, regime analysis is done manually when signals underperform. This means:
- Winning signals stay disabled too long (blanket-killed)
- Losing signals stay enabled too long (no regime check)
- Regime blocks are added reactively, not proactively

## Goal

A weekly automated system that:
1. Analyzes every signal's performance by volatility regime
2. Re-enables disabled signals that have winning regimes (with blocks on losing regimes)
3. Disables enabled signals that have no winning regimes
4. Adds regime blocks for enabled signals that lose in specific regimes
5. Generates a report for CEO review

---

## Existing Pieces

| Component | Status | Location |
|-----------|--------|----------|
| Regime memory | ✅ Built | `scripts/regime_memory.py`, `data/signal_regime_memory.json` |
| Volatility gate multipliers | ✅ Built | `scripts/volatility_gate_v2.py` |
| Signal family mapping | ✅ Built | `scripts/market_phase_gate.py` (FAMILY_MAP) |
| Signal enable/disable flags | ✅ Exists | `scripts/hermes_constants.py` |
| NEVER_REENABLE_FLAGS | ✅ Exists | `scripts/hermes_constants.py` |
| Self-learner weekly cycle | ✅ Exists | `scripts/self_learner.py` |
| Trade data with volatility_regime | ✅ Built | PostgreSQL `trades.volatility_regime` |

---

## New Component: `scripts/regime_tuner.py`

### What It Does

Weekly automated regime analysis and tuning for ALL signals.

### Flow

```
Weekly (Sunday 06:00 UTC via systemd timer)
  │
  ├─ 1. SCAN: Query all signals from PostgreSQL trades table
  │     - Group by signal type + volatility_regime
  │     - Calculate WR, PnL, trade count per regime
  │
  ├─ 2. CLASSIFY: For each signal, determine:
  │     - Winning regimes (WR >= 55%, min 5 trades)
  │     - Losing regimes (WR < 45%, min 5 trades)
  │     - Current enable status
  │
  ├─ 3. RECOMMEND: Generate recommendations:
  │     - DISABLED signal with winning regime → RE-ENABLE with blocks
  │     - ENABLED signal with no winning regime → DISABLE
  │     - ENABLED signal with losing regime → ADD BLOCK
  │
  ├─ 4. AUTO-EXECUTE: Apply low-risk changes automatically:
  │     - Add regime blocks (0.0x multiplier) for losing regimes
  │     - Re-enable signals with clear winning regimes (3+ regimes, 50+ trades)
  │
  ├─ 5. FLAG FOR REVIEW: Queue high-risk changes for CEO:
  │     - Disable enabled signals (needs human confirmation)
  │     - Re-enable signals with marginal data (< 20 trades)
  │
  └─ 6. REPORT: Generate weekly regime report
        - Summary of changes made
        - Recommendations pending review
        - Regime performance trends
```

### Input Data

```sql
-- Query for regime analysis
SELECT 
    signal,
    volatility_regime,
    COUNT(*) as trades,
    SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*), 1) as wr,
    ROUND(SUM(pnl_usdt), 2) as pnl,
    ROUND(AVG(pnl_pct), 2) as avg_pct
FROM trades 
WHERE status = 'closed'
AND close_time > NOW() - INTERVAL '30 days'
GROUP BY signal, volatility_regime
HAVING COUNT(*) >= 5
ORDER BY signal, pnl DESC
```

### Decision Matrix

| Current State | Regime Performance | Action |
|--------------|-------------------|--------|
| DISABLED | Has regime with WR >= 55% (5+ trades) | **RE-ENABLE** with 0.0x blocks on losing regimes |
| DISABLED | No regime with WR >= 55% | Stay disabled |
| ENABLED | All regimes WR >= 45% | No change |
| ENABLED | Any regime WR < 45% (5+ trades) | **ADD BLOCK** (0.0x multiplier) |
| ENABLED | All regimes WR < 45% | **DISABLE** (needs CEO review) |

### Safety Thresholds

```python
MIN_TRADES_PER_REGIME = 5      # Minimum trades to evaluate a regime
WINNING_WR_THRESHOLD = 55      # WR >= 55% = winning regime
LOSING_WR_THRESHOLD = 45       # WR < 45% = losing regime
MIN_TRADES_TO_REENABLE = 20    # Minimum total trades to auto-reeable
MIN_TRADES_FOR_REVIEW = 10     # Between 10-20 trades = needs CEO review
```

### Auto-Execute Rules

**Auto-apply (no review needed):**
- Add 0.0x multiplier to volatility_gate_v2.py for losing regimes
- Re-enable signal if: 50+ total trades, 3+ regimes with WR >= 55%

**Require CEO review:**
- Disable an enabled signal
- Re-enable signal with 10-49 total trades
- Any change to NEVER_REENABLE_FLAGS

---

## Output Files

### 1. `data/regime_tuner_report.json`

```json
{
  "run_at": "2026-09-14T06:00:00Z",
  "signals_analyzed": 45,
  "changes_made": [
    {
      "signal": "bb_bounce+",
      "action": "ADD_REGIME_BLOCK",
      "regime": "HIGH",
      "multiplier": 0.0,
      "reason": "50% WR in HIGH (16T), wins in NORMAL (77%) and EXTREME (62%)"
    }
  ],
  "pending_review": [
    {
      "signal": "ichimoku",
      "action": "RE-ENABLE",
      "winning_regimes": ["NORMAL"],
      "total_trades": 37,
      "reason": "60% WR in NORMAL (5T), but only 1 regime"
    }
  ],
  "regime_performance": {
    "bb_bounce+": {"FLAT": null, "NORMAL": 76.9, "HIGH": 50.0, "EXTREME": 61.5},
    ...
  }
}
```

### 2. `automation/regime_tuner_report.md`

Human-readable report with:
- Summary of changes
- Recommendations pending review
- Regime performance heat map
- Trend analysis (is a signal improving/worsening in a regime?)

---

## Integration Points

### 1. Systemd Timer

```ini
# /etc/systemd/system/hermes-regime-tuner.timer
[Unit]
Description=Hermes Regime Tuner (weekly)

[Timer]
OnCalendar=Sun *-*-* 06:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

### 2. volatility_gate_v2.py Integration

The tuner writes directly to `VOL_PHASE_MULTS` in volatility_gate_v2.py:

```python
# Example auto-applied change
('HIGH', '*'): {
    'Bollinger': 0.0,  # NEW — bb_bounce 50% WR in HIGH
    'Coiled_Spring': 0.0,
    ...
}
```

### 3. hermes_constants.py Integration

The tuner writes enable/disable flags:

```python
# Example auto-applied change
BB_BOUNCE_MINUS_ENABLED = True  # RE-ENABLED by regime_tuner 2026-09-14
```

### 4. CEO Prompt Integration

The CEO reads the regime_tuner_report.json in Step 1:

```bash
cat data/regime_tuner_report.json | python3 -m json.tool | head -50
```

---

## Risk Mitigation

1. **Dry-run mode:** `python3 scripts/regime_tuner.py --dry` shows what would change without applying
2. **Rollback:** Keep backup of volatility_gate_v2.py before changes
3. **Max changes per run:** Limit to 5 auto-applied changes
4. **Cooldown:** Don't re-enable a signal that was disabled in last 7 days
5. **NEVER_REENABLE protection:** Never auto-enable signals in NEVER_REENABLE_FLAGS

---

## Implementation Order

| Step | File | Change |
|------|------|--------|
| 1 | `scripts/regime_tuner.py` | **NEW** — main tuner script |
| 2 | `config/hermes-regime-tuner.timer` | **NEW** — systemd timer |
| 3 | `scripts/regime_memory.py` | Add `analyze_all_signals()` function |
| 4 | `scripts/volatility_gate_v2.py` | Add `apply_regime_blocks()` function |
| 5 | `automation/ceo_prompt.md` | Add regime_tuner report reading |
| 6 | Test with `--dry` mode | Validate recommendations |
| 7 | Enable weekly timer | Go live |

---

## Testing Plan

1. **Dry run:** `python3 scripts/regime_tuner.py --dry` — verify recommendations match manual analysis
2. **Compare:** Run tuner output against our manual regime analysis from today
3. **Backtest:** Apply tuner logic to last 30 days of data, simulate what changes it would have made
4. **Paper trade:** Run with auto-execute disabled for 1 week, review recommendations
5. **Live:** Enable auto-execute for low-risk changes (regime blocks only)

---

## Open Questions

1. **Should the tuner also update FAMILY_MAP?** Or keep that manual?
2. **How to handle signals with no volatility_regime data?** (206 tl_break trades have UNKNOWN regime)
3. **Should we backfill volatility_regime for all historical trades?** Or only track going forward?
4. **Integration with self_learner?** Should regime_tuner feed into self_learner's param tuning?

---

*Spec created by CEO agent — 2026-09-09*
