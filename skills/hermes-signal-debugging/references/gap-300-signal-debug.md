---
name: gap-300-signal-debug
description: Debug gap-300 signal — direction flip bug, collapse guard failures, momentum filter bugs, warmup data issues, and price data gap filling. (Absorbed into hermes-signal-debugging; kept here for reference.)
---

# gap-300 Signal Debug — Absorbed into hermes-signal-debugging

This reference file is retained for detailed gap-300 debugging procedures. The umbrella is `hermes-signal-debugging`. Quick reference below.

## Quick Decision Tree

```
gap-300 misfiring?
├── Check signals DB for direction mismatch
│   └── → Bug 1: Direction-Flip
├── Check price_history for data discontinuity
│   └── → Bug 2: Collapse Guard
├── Check valid bar count (need 300+ warmup)
│   └── → Warmup Bug
├── Check recent 10-bar 1m momentum vs signal direction
│   └── → Bug 4: Momentum Filter
├── Check bars_since for crossing age
│   └── → Bug 5: Staleness Cap
├── Check price_history for missing rows / 429 gaps
│   └── → Price Gap-Fill
└── Check signal survived compactor (compact_rounds > 0)
    └── → Compactor survival check
```

## Reference Files (Full Content)

| File | Covers |
|------|--------|
| `gap-300-signal-debug-ref.md` (archived) | Direction flip, collapse guard, momentum filter, staleness cap, 5m signal bugs, latency, confluence gate |
| `gap-300-warmup-debug.md` (archived) | Insufficient warmup bars causing premature firing |
| `gap-filling-price-collector.md` (archived) | Carry-forward gap-filling for 429 rate-limit gaps in price_history |

## Core Diagnostic Commands

```python
# 1. Check signal direction vs current gap
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute("""
    SELECT id, token, signal_type, direction, confidence, decision,
           compact_rounds, hot_cycle_count, created_at
    FROM signals WHERE token='TOKEN' ORDER BY created_at DESC LIMIT 5
""")
for r in cur.fetchall(): print(r)

# 2. Check valid warmup bars
from gap300_signals import _ema_series, _sma_series, PERIOD
# n = len([e for e in ema_s if e is not None])
# if n < PERIOD: warmup bug

# 3. Check price_history for gaps
cur.execute("SELECT timestamp FROM price_history WHERE token='TOKEN' ORDER BY timestamp DESC LIMIT 700")
bars = [r[0] for r in cur.fetchall()]
diffs = [bars[i-1] - bars[i] for i in range(1, len(bars))]
print(f"Max bar gap: {max(diffs)}s")  # >>60s = discontinuity

# 4. Check collapse ratio
# peak_60 = max(gap_pcts[-60:])
# latest = gap_pcts[-1]
# if latest < peak_60 * 0.70: collapse guard should have blocked
```

## Key Files
- `/root/.hermes/scripts/gap300_signals.py` — 1m gap-300 signal logic
- `/root/.hermes/scripts/gap300_5m_signals.py` — 5m gap-300 acceleration signal
- `/root/.hermes/scripts/backtest_gap300.py` — state machine backtest
- `/root/.hermes/scripts/price_collector.py` — price collection (systemd timer)
- `/root/.hermes/data/signals_hermes.db` — price_history table
- `/root/.hermes/data/signals_hermes_runtime.db` — signals/decisions tables

## Bugs Summary

| # | Bug | Fix |
|---|-----|-----|
| 1 | Direction-flip: returns first crossing, no flip check | Add `(raw_gaps[-1] > 0) != (raw_gaps[i] > 0)` guard |
| 2 | Collapse guard: widening check ignores recent peak | Compare `gap_pcts[-1]` against `max(gap_pcts[-60:]) * 0.70` |
| 3 | Warmup: fires with <300 valid bars (e.g. gap-111) | Add `MIN_WARMUP_BARS = int(PERIOD * 1.5)` guard |
| 4 | Momentum filter: fires on falling knife | Add 10-bar 1m return check vs direction |
| 5 | Staleness cap: fires hours after crossing | Add `MAX_CROSSING_AGE_BARS = 20` check |
| A | Off-by-one persistence (5m): `range(1, PERSISTENT_BARS)` | → `range(1, PERSISTENT_BARS + 1)` |
| B | Backtest vs live direction-flip discrepancy | Expected; live flips on any sign change |
| C | EMA seed uses SMA instead of first value | Low severity |
| D | Dead `cross_ts` field never used | Remove or use for max crossing age |