# accel-300 Signal — Architecture, Bugs, Fixes

## What the signal does

Detects 1m EMA acceleration (gap gap_growth from cross bar). Fires when:
- Price crosses EMA and holds (>0.03% gap)
- Gap grows beyond cross-bar value (accelerating away)
- Price stays above/below EMA for N consecutive bars
- Gap expansion confirms clean trend not bounce

Direction: LONG (+) when price above EMA with accelerating gap; SHORT (-) when below.

## Key Architecture

```
PERIOD = 300, LOOKBACK = 30, PERSISTENCE_BARS = 3
gap_pcts[i] = (close[i] - ema300[i]) / ema300[i] * 100
Outer loop: for i in range(330, len(closes)-1)
Cross bar search: for j in range(max(310, i-LOOKBACK), i+1)
```

## Critical Bugs Fixed

### Bug 1: PERSISTENCE_BARS hardcoded to 2
`PERSISTENCE_BARS = 2` at line 67 shadows `ACCEL_300_PERSISTENCE_BARS = 3` from hermes_constants.
**Fix:** Import `ACCEL_300_PERSISTENCE_BARS` from hermes_constants, replace hardcoded 2.

### Bug 2: gap_bonus threshold misalignment
`gap_bonus` fired at threshold `0.05` but `MIN_GAP_GROWTH_PCT = 0.03`. Signals at 0.03-0.05% growth got no bonus.
**Fix:** `0.05` → `MIN_GAP_GROWTH_PCT` (0.03).

### Bug 3: gap_at_cross return guard
`round(gap_at_cross, 4) if cross_bar is not None else None` — cross_bar can be None but gap_at_cross valid.
**Fix:** `round(gap_at_cross, 4) if gap_at_cross is not None else None`

### Bug 4: Stale signal — loops backward, returns old bar
`detect_accel_300` loops from bar 330 backward, returns at FIRST valid signal. Current bar 708, COMP SHORT fires at bar 361 when price was below EMA. Now COMP is above EMA (+0.18%) but old SHORT returned.
**Fix (PART 1):** Added FINAL_VERIFY block — re-check current bar direction matches signal direction.
**Fix (PART 2):** Added current bar gap magnitude check — `abs(gap_pcts[current_bar_idx]) >= MIN_GAP_PCT_LONG/SHORT`.

### Bug 5: FINAL_VERIFY P0 fix broke all signals (REVERTED)
Changed to check `n-2` instead of detection bar `i`. Loop iterates over ALL bars from 330 to len-2 — only the LAST iteration satisfies `i == n-2`. All other iterations rejected → zero signals.
**Fix:** Reverted. Original: check n-2 when i < n-2, pass through when i == n-2.

### Bug 6: LONG signals catching falling knives (ROOT CAUSE OF LOSSES)
23.3% winrate on last 30 trades. All exits via `atr_sl_hit`. Root cause: accel-300 has no regime awareness — fires LONG in a declining (SHORT_BIAS) market, short-term pullback rallies get stopped out.
**Fix:** Added regime filter using linear regression on last 50 1m closes from candles.db.

## Regime Filter Implementation

```python
def get_regime_50(closes_50):
    n = len(closes_50)
    mean_x = (n - 1) / 2.0
    mean_y = statistics.mean(closes_50)
    cov = sum((i - mean_x) * (closes_50[i] - mean_y) for i in range(n))
    var_x = sum((i - mean_x) ** 2 for i in range(n))
    return cov / var_x if var_x > 0 else 0

# In detect_accel_300, before return:
try:
    conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=10)
    rows = conn.execute(
        "SELECT close FROM candles_1m WHERE token=? ORDER BY ts DESC LIMIT 50",
        (token,)
    ).fetchall()
    conn.close()
    slope = get_regime_50([r[0] for r in reversed(rows)])
    if direction == 'LONG' and slope < 0: return None      # SHORT_BIAS → block LONG
    if direction == 'SHORT' and slope > 0: return None    # LONG_BIAS → block SHORT
except:
    pass  # best-effort, don't block signals on DB errors
```

- Uses `candles.db` `candles_1m` table (same source as signal_compactor get_regime_1m)
- Wrapped in try/except — best-effort, DB errors don't block signals
- Slope > 0 = LONG_BIAS (block SHORT); slope < 0 = SHORT_BIAS (block LONG)

## Direction-Specific Constants

| Constant | Value | Notes |
|----------|-------|-------|
| `MIN_GAP_PCT_LONG` | 0.20 | From hermes_constants |
| `MIN_GAP_PCT_SHORT` | 0.20 | From hermes_constants |
| `ACCEL_300_MIN_GAP_GROWTH` | 0.03 | Gap must grow 0.03% from cross bar |
| `ACCEL_300_MIN_GAP_EXPANSION` | 0.10 | Price must be 0.10% farther from EMA than at cross |
| `ACCEL_300_PERSISTENCE_BARS` | 3 | Was hardcoded to 2 — fixed |

## Constants Source

All accel-300 constants are centralized in `hermes_constants.py`:
- `ACCEL_300_ENABLED`, `ACCEL_300_PLUS_ENABLED`, `ACCEL_300_MINUS_ENABLED` — on/off toggles
- `SHORT_BLACKLIST` — DOGE/SOL/BNB/apt/ARB/MATIC never fire SHORT
- `ACCEL_300_PERSISTENCE_BARS = 3`
- `ACCEL_300_MIN_GAP_GROWTH = 0.03`
- `ACCEL_300_MIN_GAP_EXPANSION = 0.10`
- `MIN_GAP_PCT_LONG = 0.20`, `MIN_GAP_PCT_SHORT = 0.20`

## Verified Non-Bugs (False Positives from Audits)

1. **`max(310, i - LOOKBACK)` floor**: Outer loop starts at 330, so `i - LOOKBACK >= 300` always. `max(310, ...) = 310` for all reachable i. Functionally equivalent to bare `i - LOOKBACK`. Not a bug.
2. **`gap_at_cross` outside outer loop**: `gap_at_cross = None` is at line 260, INSIDE the outer `for i in range(330, ...)` loop. Resets each iteration. No cross-contamination.
3. **`gap_at_cross` never assigned**: Assigned at line 304 after cross_bar found. FALSE POSITIVE from audit.

## Performance Context

- Last 30 accel-300 trades: 7 wins (23.3%), avg PnL -0.2077%, all exits via `atr_sl_hit`
- Root cause: regime-naive direction, fires LONG in declining market
- After regime filter: BTC/LONG, AVAX/LONG, ATOM/LONG, LINK/LONG, UNI/LONG, ADA/LONG (all LONG in LONG_BIAS) — signal direction now aligns with 50-bar trend

## Hot-Set Validation

Stale signals from accel-300 were polluting the hot-set (APEX/ATOM/COMP/AAVE/AVAX all firing SHORT, only ATOM valid). Root cause: loop returns at first valid historical bar, not current bar. Fix PART 1 + PART 2 address this.