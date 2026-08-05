# Forward-Scan + `break` Returns OLDEST Bar, Not Most Recent (2026-06-23)

**Severity:** P0 — silently produces wrong-direction signals at scale.

**Found in:** `signals/accel_300.py` line 267. Confirmed 31% of accel_300 signals fired with direction WRONG vs the actual price-vs-EMA relationship at signal-write time.

## The Bug Pattern

A signal detection loop that:
1. Walks forward through price history (oldest → newest)
2. Uses `break` on the FIRST qualifying bar
3. Returns that bar as the signal bar

...does NOT return the most recent qualifying bar. It returns the **OLDEST** qualifying bar in the entire lookback window.

The `signal_bar` dict captures that old bar's `gap_pct`, `bars_since_cross`, etc. — but the signal row's `price` field is set by the scanner to the **current live price**, not the bar's price. By the time the signal is written, the actual price may have reversed through the EMA. Result: LONG signal fires when current price is below EMA, or SHORT fires when current price is above EMA.

## Symptom Pattern

User reports: "I'm seeing LONG signals when the price is clearly below EMA300, and SHORT signals when price is above EMA300. Both should be blocked."

## Diagnostic Recipe

1. Identify the detection loop in the signal script — look for `for i in range(...)` followed by a `break` after a `signal_bar = {...}` assignment.
2. If the range starts at a small number (e.g., `PERIOD + LOOKBACK = 330`) and ends at `len(closes) - 1` (e.g., 799), the loop visits ALL bars in history.
3. `break` on first match returns the OLDEST qualifying bar.
4. Trace one recent signal back to the actual bar `i` that fired it. Confirm it's hours old (e.g., `bars_since_cross=24` with `bars_from_latest=154` means the signal bar is 154 minutes behind the latest bar).
5. Check the gap at the LATEST bar vs the gap at the signal bar — if they have opposite signs, the signal direction is wrong.

## Verification Query

```python
import sqlite3
from datetime import datetime, timezone

# Get recent signals
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()
c.execute("""SELECT token, direction, price, created_at FROM signals
             WHERE signal_type = 'accel_300_long'
             AND created_at > '2026-06-23 20:00:00' ORDER BY id DESC LIMIT 5""")
signals = c.fetchall()
conn.close()

# For each, check current price vs EMA at signal time
for token, direction, recorded_price, created_at in signals:
    sig_ts = int(datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp())
    conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
    c = conn.cursor()
    c.execute("SELECT timestamp, price FROM price_history WHERE token = ? AND timestamp <= ? ORDER BY timestamp DESC LIMIT 700",
              (token.upper(), sig_ts))
    rows = list(reversed(c.fetchall()))
    conn.close()
    closes = [r[1] for r in rows]
    k = 2.0/301
    ema = [None]*299 + [sum(closes[:300])/300]
    for j in range(300, len(closes)):
        ema.append(closes[j]*k + ema[-1]*(1-k))
    latest_gap = (closes[-1]-ema[-1])/ema[-1]*100
    consistent = (direction == 'LONG' and latest_gap > 0) or (direction == 'SHORT' and latest_gap < 0)
    print(f"{token} {direction} @ {created_at}: latest_gap={latest_gap:+.4f}%  consistent={consistent}")
```

If `consistent=False` for >10% of recent signals, this bug pattern is active.

## Fix

Change the loop direction:

```python
# WRONG — forward scan + break returns OLDEST bar
for i in range(PERIOD + LOOKBACK, len(closes) - 1):
    ...
    if qualifies:
        signal_bar = {...}
        break  # ← returns OLDEST

# CORRECT — backward scan + break returns MOST RECENT bar
for i in range(len(closes) - 2, PERIOD + LOOKBACK - 1, -1):
    ...
    if qualifies:
        signal_bar = {...}
        break  # ← returns MOST RECENT
```

Both loops visit the SAME set of indices. The only difference is iteration order, which is exactly what determines whether `break` returns the oldest or newest match.

## Why The Other Gates Don't Catch This

- `bars_from_latest = len(closes) - 1 - i` is meant to limit staleness, but with `ACCEL_300_STALE_LOOKBACK = 400` (≈6.7 hours), it allows signals from any bar in the last 6.7 hours.
- `bars_since_cross` is computed correctly for whatever bar the loop picks, but it doesn't help if the loop picked a stale bar.
- The `stale gap decay` check (`newest_idx > i and gap_pcts[newest_idx] is not None`) becomes a no-op once you fix the scan direction (the picked bar IS the newest).

## What Else to Audit After This Fix

Once you switch to backward scan, re-audit:
- `stale gap decay` check becomes a no-op — confirm this is acceptable (it is: most-recent bar can't have decayed)
- Comments referring to "scanning forward" become stale — fix them
- All other gates (chop filter, regime slope, marginal accel) operate on bar `i` relative values — independent of scan direction, no changes needed

## Related Class-Level Patterns

- **Pattern 40 — Subagent flags `abs()` as unguarded** (read scope carefully before flagging)
- **Pattern 41 — Subagent flags `>` inequality as inverted** (sign-blind analysis false positive)
- **Pattern 47 — Stale branches reference variables before definition** (always check what's in scope at the flagged line)

The ai-engineer delegation discipline (focused 8-item checklist, no general sweep) confirmed this is a real pattern — both the subagent and main-session verification matched. Full audit details in `/root/.hermes/skills/autonomous-ai-agents/ai-engineer/references/accel-300-stale-bar-fix-2026-06-23.md`.
