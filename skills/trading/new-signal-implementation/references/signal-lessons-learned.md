# Signal Implementation — Lessons Learned

Common failure modes from live debugging sessions. Apply these proactively when authoring new signals.

---

## 1. Regime-Naive Signals Destroy Winrate

**Problem:** Signal fires in both directions based purely on technical conditions (EMA gap, acceleration) without awareness of market regime. Fires LONG in a declining market → short-term pullback rallies get stopped out. All exits via `atr_sl_hit`. 23.3% winrate, -0.21% avg PnL.

**Fix:** Add regime filter before returning signal. Use linear regression on last 50 1m closes from `candles.db` — slope determines direction. Block counter-regime signals: LONG blocked if slope < 0 (SHORT_BIAS), SHORT blocked if slope > 0 (LONG_BIAS). Wrap in try/except — best-effort, don't block signals on DB errors.

**Pattern (identical to signal_compactor get_regime_1m):**
```python
import statistics, sqlite3

def get_regime_slope(token):
    conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=10)
    rows = conn.execute(
        "SELECT close FROM candles_1m WHERE token=? ORDER BY ts DESC LIMIT 50",
        (token,)
    ).fetchall()
    conn.close()
    closes = [r[0] for r in reversed(rows)]
    n = len(closes)
    mean_x = (n - 1) / 2.0
    mean_y = statistics.mean(closes)
    cov = sum((i - mean_x) * (closes[i] - mean_y) for i in range(n))
    var_x = sum((i - mean_x) ** 2 for i in range(n))
    return cov / var_x if var_x > 0 else 0

# Before return:
slope = get_regime_slope(token)
if direction == 'LONG' and slope < 0: return None
if direction == 'SHORT' and slope > 0: return None
```

---

## 2. FINAL_VERIFY Checking Wrong Bar Kills All Signals

**Problem:** Signal detector loops backward over ALL bars (e.g., range(330, len(closes)-1)). A fix changes verification to check `n-2` when `i != n-2`. Only the LAST iteration of the loop satisfies `i == n-2`. All other iterations (99% of bars) are rejected → zero signals fire.

**Root cause:** The loop runs across the entire dataset, not just the current bar. `i == n-2` is almost never true when the loop is running.

**Fix:** Revert. Check detection bar `i` directly against current bar conditions, not against `n-2`.

---

## 3. Hardcoded Constants Shadow Imported Ones

**Problem:** `PERSISTENCE_BARS = 2` hardcoded inside signal file shadows `ACCEL_300_PERSISTENCE_BARS = 3` from hermes_constants. Signal runs with wrong persistence threshold.

**Fix:** Always import constants from hermes_constants. Never re-declare signal-specific constants inside the signal file.

---

## 4. Return Guard Checks Wrong Variable

**Problem:** `round(gap_at_cross, 4) if cross_bar is not None else None` — cross_bar can be valid but gap_at_cross could be None if gap_pcts[cross_bar] was None. Checking cross_bar instead of gap_at_cross gives wrong result.

**Fix:** `round(gap_at_cross, 4) if gap_at_cross is not None else None`

---

## 5. Stale Signal Bug — Loop Returns Historical Bar

**Problem:** Detector loops backward from current bar, returns at FIRST valid historical bar. Current bar 708, COMP SHORT fires at bar 361 (price was below EMA). Now COMP is above EMA but old SHORT is returned. Hot-set shows wrong direction signals.

**Fix:** Before return, verify current bar direction matches signal direction. Also check current bar gap magnitude meets minimum threshold. If current bar contradicts signal direction, return None.

```python
# FINAL_VERIFY — current bar must confirm signal direction
current_bar_idx = len(closes) - 2
current_gap = gap_pcts[current_bar_idx]

if direction == 'LONG':
    if current_gap is None or current_gap <= 0:
        return None
elif direction == 'SHORT':
    if current_gap is None or current_gap >= 0:
        return None

# Also check gap magnitude
if abs(current_gap) < MIN_GAP_PCT_LONG:  # or MIN_GAP_PCT_SHORT
    return None
```

---

## 6. Audit False Positives — Verify Before Fixing

**Problem:** Multiple audits report "gap_at_cross initialized outside outer loop" and "max(310, i-LOOKBACK) is a bug". Both are false positives.

- `gap_at_cross = None` is INSIDE the outer loop (line 260), not outside — resets every iteration
- `max(310, i-30)` is functionally equivalent to bare `i-30` given outer loop starts at 330

**Fix:** Read the actual file before applying audit fixes. Verify the bug exists before patching.

---

## 7. PERSISTENCE_BARS Asymmetry Between Directions

When LONG and SHORT have asymmetric performance (e.g., SHORTS dominate), use separate constants:
```python
ACCEL_300_PERSISTENCE_BARS_LONG = 3  # more strict — avoid false LONG
ACCEL_300_PERSISTENCE_BARS_SHORT = 2  # allow SHORTS through faster
```

---

## 8. gap_bonus Threshold Must Match gap_growth Threshold

**Problem:** `gap_growth` fires at `MIN_GAP_GROWTH_PCT = 0.03` but `gap_bonus` checks `> 0.05`. Signals at 0.03-0.05% growth get no bonus — inconsistent.

**Fix:** `gap_bonus` threshold should equal `MIN_GAP_GROWTH_PCT`.