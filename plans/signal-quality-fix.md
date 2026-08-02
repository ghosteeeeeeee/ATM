# Signal Quality Fix Plan — 2026-05-21

## Context
Analysis of 19 closed trades (2026-05-20/21) revealed systematic signal quality degradation:
- 12 losses, 7 winners
- Root cause: `z=None` in combo signals corrupts confluence; guardian has no z-score gate
- RS levels with <100 touches correlated with losses
- Opposing-direction trades on same coin within 45 min (BSV)

---

## Fixes (in order)

### Fix 1: Guardian z-score gate
**File:** `hl-sync-guardian.py` (or wherever guardian evaluates entries)

**Logic:**
- If `zscore-pump` in signal source AND `z_score IS NULL`:
  - Downgrade: tighten SL to max -1.5%
  - Reduce position size by 50%
  - Log warning: "zscore-pump in source but no valid z — treating as RS-only"

**Status:** TODO

---

### Fix 2: Write z_score to trade record
**File:** Guardian trade entry write

**Logic:**
- Persist `signal_z_score` column in trade record at entry
- Needed for feedback loop and post-trade analysis

**Status:** TODO

---

### Fix 3: Minimum RS touch filter at guardian level
**File:** Guardian entry gate

**Logic:**
- Reject if RS touches < 100 AND |z_score| < 2.5
- Log: "RS level too weak (N touches) and no strong z-score confirmation"

**Status:** TODO

---

### Fix 4: Divergence detection logging
**File:** `signals/zscore_pump.py`

**Logic:**
- When divergence check rejects a signal, write to signal record:
  - `rejection_reason='negative_divergence'`
  - `z_score` still written so Guardian can see it was evaluated

**Status:** TODO

---

### Fix 5: Opposing signal penalty at guardian level
**File:** Guardian entry gate

**Logic:**
- Block re-entry if opposite direction was closed at a loss within 30 min
- Block re-entry if same coin+direction has a surviving opposing signal in hotset

**Status:** TODO

---

### Fix 6: RS bounce confirmation freshness
**File:** `signals/rs.py`

**Logic:**
- Reduce bounce lookback from 6 candles to 3 candles
- Only count as valid bounce if price touched level within last 3 candles

**Status:** TODO

---

### Fix 7: High-touch level decay
**File:** `signals/rs.py` + signal_compactor scoring

**Logic:**
- If touch_count > 5000: apply -10% confidence discount
- Prevents ancient congested levels (10k+ touches) from over-influencing entries

**Status:** TODO

---