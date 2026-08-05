# accel-300 Loop Start Bug — Jun 2026

## The Bug

Signal was completely silent on 700-bar datasets. Detection loop never executed.

**Root cause:** The loop start was `PERIOD + LOOKBACK = 300 + 500 = 800`. On a 700-bar dataset, `range(800, 698, -1)` is empty. The entire detection loop was skipped.

Also: the minimum bars check was `n < PERIOD + LOOKBACK + PERSISTENCE_BARS + 5 = 809` — same problem, required 809 bars.

**Secondary bugs found during diagnosis:**
- Cross_bar search crashed on EMA warmup bars (`ema300[j-1]` is None before index 300) — added None guard
- ACCEL_300_STALE_BARS check was inside `if i < newest_idx` — only ran for non-latest bars, stale signals at n-2 slipped through
- Chop filter used `ema300[n-50:n]` instead of `ema300[i-50:i]` — angle computed from dataset end, not detection bar
- Fallback cross gap_expansion was meaningless (gap_at_cross≈0%, any positive gap passes) — added cross_is_fallback flag to skip gap_expansion for fallback crosses

## Fixes Applied

**hermes_constants.py:**
- `ACCEL_300_LOOKBACK: 35 → 500`

**accel_300.py:**
1. Loop start: `PERIOD + LOOKBACK` → `PERIOD + PERSISTENCE_BARS` (304, not 800)
2. Minimum bars: `PERIOD + LOOKBACK + PERSISTENCE_BARS + 5` → `350`
3. EMA warmup guard: added `ema300[j-1] is not None` check in cross_bar search
4. Stale gate: moved `bars_since_cross > ACCEL_300_STALE_BARS` OUTSIDE `if i < newest_idx` — now blocks all stale signals regardless of position
5. Chop filter: fixed EMA angle to use `ema300[i-chop_window:i]` (detection bar context)
6. Fallback gap_expansion: added `cross_is_fallback` flag, skip gap_expansion for fallback crosses

## Debugging Technique Used

When function returns None but manual trace shows all gates should pass:
1. Add `print(f"[{token}] Starting detect: n={n}, range(...)")` at loop start — confirms loop is running
2. If no print appears: check minimum bars check AND loop start constant
3. If print appears but no signal: add print at signal detection point
4. If signal detected but None returned: check final_verify block (gap direction, stale gate)
5. Clear `__pycache__` after any source change — Python caches .pyc aggressively

## Key Lesson

When increasing LOOKBACK (or any loop-related constant), always check:
- The loop start expression `PERIOD + CONSTANT` — does it still make sense after the change?
- The minimum bars check — does it use the same expression?
- The loop must start LOWER than `len(closes) - 2` on the smallest dataset you support (700 bars)

When the signal silently returns None on a dataset that should pass: check the minimum bars gate first, then the loop start, before adding debug prints.