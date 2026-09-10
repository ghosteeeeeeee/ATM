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
  ├─ 0. SAFETY CHECK (FIRST — before any logic)
  │     - Load NEVER_REENABLE_FLAGS from hermes_constants.py
  │     - Load CEO_PROTECTED_FLAGS from hermes_constants.py
  │     - Load currently enabled flags
  │     - SKIP any signal in NEVER_REENABLE_FLAGS (hard stop, no exceptions)
  │     - SKIP any signal in CEO_PROTECTED_FLAGS (protected until expiry)
  │
  ├─ 1. SCAN: Query all signals from PostgreSQL trades table
  │     - Group by signal + direction + volatility_regime
  │     - Use COALESCE(volatility_regime, 'NORMAL') for NULL values
  │     - Calculate WR, PnL, trade count per regime
  │
  ├─ 2. MAP: Convert signal names to family names
  │     - Use market_phase_gate.signal_family() for VOL_PHASE_MULTS mapping
  │     - Use signal_family lookup table for per-direction enable flags
  │
  ├─ 3. CLASSIFY: For each signal (excluding NEVER_REENABLED), determine:
  │     - Winning regimes (WR >= 50%, min 5 trades)
  │     - Losing regimes (WR < 40%, min 5 trades)
  │     - Current enable status
  │
  ├─ 4. RECOMMEND: Generate recommendations:
  │     - DISABLED signal with winning regime → RE-ENABLE with blocks
  │     - ENABLED signal with no winning regime → DISABLE (CEO review)
  │     - ENABLED signal with losing regime → ADD BLOCK
  │
  ├─ 5. AUTO-EXECUTE: Apply low-risk changes automatically:
  │     - Add regime blocks (0.0x multiplier) for losing regimes
  │     - Re-enable signals with clear winning regimes (50+ trades, 3+ regimes)
  │     - Use atomic writes with backup + rollback on syntax error
  │
  ├─ 6. FLAG FOR REVIEW: Queue high-risk changes for CEO:
  │     - Disable enabled signals (needs human confirmation)
  │     - Re-enable signals with marginal data (< 50 trades)
  │
  └─ 7. REPORT: Generate weekly regime report
        - Summary of changes made
        - Recommendations pending review
        - Regime performance trends
```

### Input Data

```sql
-- Query for regime analysis (with COALESCE for NULL regimes, per-direction)
SELECT 
    signal,
    direction,
    COALESCE(volatility_regime, 'NORMAL') as regime,
    COUNT(*) as trades,
    SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/COUNT(*), 1) as wr,
    ROUND(SUM(pnl_usdt), 2) as pnl,
    ROUND(AVG(pnl_pct), 2) as avg_pct
FROM trades 
WHERE status = 'closed'
AND close_time > NOW() - INTERVAL '60 days'  -- 60 days for low-frequency signals
GROUP BY signal, direction, COALESCE(volatility_regime, 'NORMAL')
HAVING COUNT(*) >= 5
ORDER BY signal, direction, pnl DESC
```

### Signal → Family Mapping (H2 Fix)

The tuner MUST map signal names to family names before writing to VOL_PHASE_MULTS:

```python
# From market_phase_gate.py
from market_phase_gate import signal_family

# Example mapping:
# 'bb_bounce+' → 'Bollinger'
# 'tl_break_short' → 'Trendline'
# 'r2_trend_long' → 'R2'
# 'accel_300_v3_long' → 'Accelerate'

def get_family_multiplier_key(signal_name):
    """Convert signal name to family name for VOL_PHASE_MULTS."""
    family = signal_family(signal_name)
    return family if family else signal_name  # fallback to raw name
```

### Direction-Aware Analysis (M4 Fix)

Analyze LONG and SHORT separately, since enable flags are per-direction:

```python
# Per-direction flag mapping
DIRECTION_FLAGS = {
    'LONG': {
        'bb_bounce': 'BB_BOUNCE_PLUS_ENABLED',
        'tl_break': 'TL_BREAK_PLUS_ENABLED',
        'r2_trend': 'R2_TREND_LONG_ENABLED',
        'accel_300': 'ACCEL_300_LONG_ENABLED',
    },
    'SHORT': {
        'bb_bounce': 'BB_BOUNCE_MINUS_ENABLED',
        'tl_break': 'TL_BREAK_MINUS_ENABLED',
        'r2_trend': 'R2_TREND_SHORT_ENABLED',
        'accel_300': 'ACCEL_300_SHORT_ENABLED',
    }
}
```

### Decision Matrix

**FIRST CHECK: Is signal in NEVER_REENABLE_FLAGS?**
- YES → **SKIP entirely** (hard stop, no exceptions)
- NO → proceed to classification

| Current State | Regime Performance | Action |
|--------------|-------------------|--------|
| DISABLED (not in NEVER_REENABLE) | Has regime with WR >= 50% (5+ trades) | **RE-ENABLE** with 0.0x blocks on losing regimes |
| DISABLED (not in NEVER_REENABLE) | No regime with WR >= 50% | Stay disabled |
| ENABLED | All regimes WR >= 40% | No change |
| ENABLED | Any regime WR < 40% (5+ trades) | **ADD BLOCK** (0.0x multiplier) |
| ENABLED | All regimes WR < 40% | **DISABLE** (needs CEO review) |

### Safety Thresholds

```python
MIN_TRADES_PER_REGIME = 5      # Minimum trades to evaluate a regime
WINNING_WR_THRESHOLD = 50      # WR >= 50% = winning regime (matches regime_memory.py)
LOSING_WR_THRESHOLD = 40       # WR < 40% = losing regime (matches regime_memory.py)
MIN_TRADES_TO_REENABLE = 50    # Minimum total trades to auto-reeable
MIN_TRADES_FOR_REVIEW = 20     # Between 20-50 trades = needs CEO review
MAX_CHANGES_PER_RUN = 5        # Limit auto-applied changes
```

### Auto-Execute Rules

**Auto-apply (no review needed):**
- Add 0.0x multiplier to volatility_gate_v2.py for losing regimes
- Re-enable signal if: 50+ total trades, 3+ regimes with WR >= 50%

**Require CEO review:**
- Disable an enabled signal
- Re-enable signal with 20-49 total trades
- Any change to NEVER_REENABLE_FLAGS

### File Write Safety (H4 Fix)

**NEVER write directly to Python source files.** Instead:

1. **Use atomic writes with backup:**
   ```python
   def safe_write(path, new_content):
       backup = path + '.bak.' + str(int(time.time()))
       shutil.copy2(path, backup)
       try:
           with tempfile.NamedTemporaryFile(mode='w', dir=os.path.dirname(path), delete=False) as tmp:
               tmp.write(new_content)
           os.replace(tmp.name, path)
           # Verify syntax
           py_compile.compile(path, doraise=True)
       except Exception as e:
           shutil.copy2(backup, path)  # rollback
           raise
   ```

2. **Use AST parsing for volatility_gate_v2.py** (not regex):
   ```python
   import ast
   import astunparse
   
   with open('volatility_gate_v2.py') as f:
       tree = ast.parse(f.read())
   
   # Find VOL_PHASE_MULTS dict and modify
   # Write back with astunparse
   ```

3. **For hermes_constants.py:** Use the existing `_set_param_value()` pattern from self_learner.py (line 440-483) — it's proven safe.

### Race Condition Prevention (H3 Fix)

Use file locking to prevent concurrent modifications:

```python
import fcntl

LOCK_FILE = '/tmp/regime-tuner.lock'

def acquire_lock():
    fd = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        log("Another instance running (self_learner?), exiting")
        sys.exit(0)
```

Also check if self_learner is running:
```python
if os.path.exists('/tmp/self-learner.lock'):
    log("self_learner running, deferring to next window")
    sys.exit(0)
```

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

1. **NEVER_REENABLE protection:** FIRST check in decision matrix — hard stop, no exceptions
2. **Dry-run mode:** `python3 scripts/regime_tuner.py --dry` shows what would change without applying
3. **Atomic writes with rollback:** Backup before write, verify syntax after, rollback on error
4. **File locking:** Acquire lock before modifying hermes_constants.py or volatility_gate_v2.py
5. **Max changes per run:** Limit to 5 auto-applied changes (MAX_CHANGES_PER_RUN)
6. **Cooldown:** Don't re-enable a signal that was disabled in last 7 days (track via git log)
7. **CEO_PROTECTED protection:** Never auto-modify protected flags
8. **60-day lookback:** Extended from 30 days for low-frequency signals
9. **COALESCE for NULL regimes:** Use 'NORMAL' as fallback for missing volatility_regime
10. **Per-direction analysis:** Separate LONG and SHORT to match enable flag structure

---

## Implementation Order

| Step | File | Change |
|------|------|--------|
| 1 | `scripts/regime_tuner.py` | **NEW** — main tuner with NEVER_REENABLE check, signal→family mapping, atomic writes |
| 2 | `config/hermes-regime-tuner.timer` | **NEW** — systemd timer (Sunday 06:00 UTC) |
| 3 | `scripts/regime_memory.py` | Add `analyze_all_signals()` with direction-aware analysis |
| 4 | `scripts/market_phase_gate.py` | Verify `signal_family()` works for all signal names |
| 5 | `scripts/volatility_gate_v2.py` | Add `apply_regime_blocks()` with AST-based safe writes |
| 6 | `automation/ceo_prompt.md` | Add regime_tuner report reading + approval workflow |
| 7 | Test with `--dry` mode | Validate recommendations match manual analysis |
| 8 | Enable weekly timer | Go live with auto-execute for regime blocks only |

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
