# Phase Accel Signal — Extracted Reference

**Source:** `/root/.hermes/scripts/signals/phase_accel.py` (extracted from `signal_gen.py` lines ~1782-1857, 2026-05-05)

**Signal type:** `phase_accel_long` / `phase_accel_short`

**Source tags:** `phase-accel+` (LONG), `phase-accel-` (SHORT)

**Signal logic:**
- Fires when `phase == 'accelerating'` AND `prev_phase != 'accelerating'` (new transition into accelerating)
- Direction: `momentum_state == 'bullish'` → LONG, `bearish` → SHORT
- Confidence: `min(99.0, percentile)` where percentile comes from `get_momentum_stats`

**Key constants (from hermes_constants):**
```python
PHASE_ACCEL_ENABLED      # master toggle
PHASE_ACCEL_PLUS_ENABLED   # LONG direction gate
PHASE_ACCEL_MINUS_ENABLED  # SHORT direction gate
```

**Required imports from signal_gen:**
```python
from signal_gen import (
    get_momentum_stats,   # returns {phase, momentum_state, percentile, velocity, avg_z, z_direction, rsi_14}
    is_reasonable_price,
    log,                  # writes to signals.log
    recent_trade_exists,
    MIN_TRADE_INTERVAL_MINUTES,
)
```

**Reading previous phase (momentum_cache pattern):**
```python
_RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'

def _get_previous_phase(token):
    conn = sqlite3.connect(_RUNTIME_DB, timeout=5)
    cur = conn.cursor()
    cur.execute("SELECT prev_phase FROM momentum_cache WHERE token = ?", (token.upper(),))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None
```

**Key architectural point — prev_phase column:**
The `momentum_cache` table has a `prev_phase` column (separate from `phase`) that stores the phase from the prior pipeline run. `get_momentum_stats()` writes the current phase to `phase` and the prior phase to `prev_phase` in the same UPSERT. Reading `prev_phase` (not `phase`) correctly detects phase transitions.

**Bug fixed on extraction (signal_gen.py lines 1827-1828):**
```python
# ORIGINAL (bug — duplicate direction assignment):
if momentum_state == 'bullish':
    direction = 'LONG'
    direction = 'LONG'    # ← spurious duplicate, second overwrites nothing useful
    sig_type = 'phase_accel_long'

# FIXED:
if momentum_state == 'bullish':
    direction = 'LONG'
    sig_type = 'phase_accel_long'
```

**Module path:** `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` — parent of `signals/` directory (i.e., `/root/.hermes/scripts`) so modules like `signal_schema` and `signal_gen` resolve correctly.
