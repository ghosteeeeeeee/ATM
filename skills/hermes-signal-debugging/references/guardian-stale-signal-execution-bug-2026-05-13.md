# Bug: Guardian Executes Stale-Signal Direction — 2026-05-13

## Bug 3 (NEW): Guardian has no pre-execution EMA direction check

**File:** `hl-sync-guardian.py`
**Symptom:** TAO SHORT and NIL SHORT executed while price was ABOVE EMA300 — directly against the signal direction. Trades closed as losers immediately. Same pattern as 2026-05-11 session.

**Root cause:** The guardian reads signals from `signals_hermes_runtime.db` and executes them without verifying that the current price direction matches the signal direction. The signal script computes gap% from EMA(300) using data in `signals_hermes.db`, but by execution time the price may have crossed the EMA. The guardian fires blindly.

**Mechanism:**
1. `accel_300.py` scans ALL 700 bars, fires at the FIRST bar meeting conditions (could be minutes old)
2. The signal's returned `gap_pct` and `price` are from that historical bar, not current
3. Guardian reads the signal from runtime DB and dispatches to Hyperliquid — no EMA re-check
4. If price crossed EMA between signal creation and execution, trade goes the wrong way

**Fix (applied):**
Added `_get_ema300_gap()` helper and `_verify_direction_vs_ema()` guard to `hl-sync-guardian.py`:
- Batch execution path (line ~2319): checks EMA direction before placing order
- `live_missing` fallback path (line ~2445): same check before `mirror_open`
- Skipped trades are closed with reason `EMA_DIRECTION_MISMATCH`

```python
# New helper function
def _get_ema300_gap(token):
    """Returns (gap_pct, ema_val, direction) from live signals_hermes.db"""
    # Fetch 700 bars from signals_hermes.db, compute EMA(300), return gap
    
def _verify_direction_vs_ema(token, signal_direction, curr_price):
    """Returns True if current price direction matches signal direction"""
    gap, ema, direction = _get_ema300_gap(token)
    mismatch = (signal_direction == 'LONG' and direction != 'LONG') or \
               (signal_direction == 'SHORT' and direction != 'SHORT')
    if mismatch:
        _log(f"[EMA-VERIFY] SKIP {token} {signal_direction} — gap={gap:.4f}% direction={direction}")
    return not mismatch
```

**Verification:** All 5 tokens (TAO, NIL, LAYER, PURR, PEOPLE) were LONG territory (gap=+0.02% to +2.41%). NIL SHORT and TAO SHORT would now be blocked.

**Deploy:** Guardian restart required to load new code.

---

## Bug 4: accel-300 SHORT gap_growth sign inverted

**File:** `accel_300.py` lines 248-257
**Symptom:** accel-300- (SHORT) fires on price bounces (gap becoming less negative), not on downward acceleration (gap becoming more negative).

**Root cause:** OLD formula `gap_now - gap_then` for SHORT fires when `gap_now > gap_then` (gap less negative = price bouncing up). NEW formula `gap_then - gap_now` fires when `gap_now < gap_then` (gap more negative = price accelerating below EMA).

**Fix:**
```python
# OLD (fires on bounce — WRONG for SHORT):
gap_growth = gap_now - gap_then  # fires when gap goes -0.10 → -0.05

# NEW (fires on acceleration — CORRECT):
if direction == 'LONG':
    gap_growth = gap_now - gap_then
else:
    gap_growth = gap_then - gap_now  # fires when gap goes -0.05 → -0.10
```

**Note:** The `delta_last >= delta_prev` marginal acceleration check (lines 301-306) was already correct for SHORT. Only the gap_growth formula was wrong.

**Verified with SKY:** gap_then=-0.1773%, gap_now=-0.3353% (price fell further below EMA) → OLD growth=+0.158 (fires on bounce = wrong), NEW growth=+0.158 (fires because price accelerated down = correct).

---

## Diagnostic Commands

```bash
# Check current EMA gaps for all tokens
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hl_sync_guardian_helpers import _get_ema300_gap
tokens = ['TAO','NIL','LAYER','PURR','PEOPLE','UNI','XMR','ZK']
for t in tokens:
    try:
        gap, ema, d = _get_ema300_gap(t)
        print(f'{t}: gap={gap:+.4f}% dir={d}')
    except: print(f'{t}: error')
"

# Check signals fired in runtime DB
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, signal_type, confidence, price, created_at FROM signals ORDER BY created_at DESC LIMIT 10"

# Check guardian execution log
grep -a "EMA-VERIFY\|EMA_DIRECTION_MISMATCH" /root/.hermes/logs/pipeline.log
```

## Related
- `references/counter-trend-entry-bug-2026-05-13.md` — same root cause (no guardian EMA check) caused 15 losing LONGs earlier same day
- `references/accel-300-short-sign-fix-2026-05-13.md` — accel-300 SHORT sign fix
- `references/accel-300-marginal-acceleration-bug-2026-05-13.md` — marginal accel check was correct
