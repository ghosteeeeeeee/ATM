---
name: signal-source-renaming
description: Rename a signal source in Hermes to add directional +/- suffix — updates source constant, scoring table, clears cache. One rename at a time, user-directed.
tags: [signals, hermes, renaming]
author: Hermes Agent
created: 2026-04-23
---

# Signal Source Renaming Workflow

## When to Use
User asks to rename a signal source (e.g., `gap-300-short` → `gap-300-`). Done one-by-one, user-directed.

## Context
The confluence gate (`signal_compactor.py:295`) requires ≥2 comma-separated source components. The directional conflict detector (`signal_compactor.py:289`) strips trailing `-short`/`-long` and checks `+/-` polarity. Renaming sources with proper `+`/`-` suffixes helps both mechanisms work correctly.

## Step-by-Step

### 1. Find the source in all files
```bash
grep -rn "gap-300-short\|gap.short\|gap_short" /root/.hermes/scripts/ 2>/dev/null | grep -v ".pyc"
```
Also check the compactor log to see how it's being blocked:
```bash
tail -50 /root/.hermes/logs/signal-compactor.log | grep "CONFLUENCE-GATE"
```

### 2. Find where SOURCE/SOURCE_TAG is defined
```bash
grep -rn "SOURCE_SHORT\|SOURCE_TAG\|SOURCE_LONG" /root/.hermes/scripts/<file>.py 2>/dev/null
```
The generator file has the constant, e.g.:
```python
SOURCE_SHORT = 'gap-300-short'
SOURCE_LONG  = 'gap-300-long'
```

### 3. Check if there's a scoring entry in signal_compactor.py
```bash
grep -n "gap-300" /root/.hermes/scripts/signal_compactor.py 2>/dev/null
```
If yes, update the source name there too. If no, add one (optional but recommended).

### 4. Make the rename — 3 parts

**Part A: Update the source constant in the generator file**
```python
SOURCE_SHORT = 'gap-300-'
SOURCE_LONG  = 'gap-300+'
```

**Part B: Update scoring table in signal_compactor.py**
Find `SIGNAL_SOURCE_WEIGHTS` dict. Add or update entry:
```python
('ema_sma_gap_300_short', 'gap-300-'):  1.3,
('ema_sma_gap_300_long',  'gap-300+'):  1.3,
```

**Part C: Clear .pyc cache**
```bash
find /root/.hermes/scripts -name "*.pyc" -delete 2>/dev/null
find /root/.hermes/scripts/__pycache__ -name "*.pyc" -delete 2>/dev/null
```

### 5. Report back to user with the exact old→new names

## Key Rules
- **One rename at a time** — user directs each rename
- **Signal_TYPE stays the same** — only SOURCE values change (e.g., `ema_sma_gap_300_short` signal_type is fine, the source string changes)
- **Use +/- suffixes** — sources ending in `-short`/`-long` get misread by the directional conflict detector; `+` (LONG) and `-` (SHORT) are the correct suffixes
- **Scoring table must match** — if there's an existing entry in `SIGNAL_SOURCE_WEIGHTS`, update it; otherwise the renamed source gets `DEFAULT_SOURCE_WEIGHT = 1.0`
- **Compound sources** (comma-separated) pass the confluence gate only if they have 2+ parts — renaming alone doesn't bypass the gate for true single-source signals

## Files Involved
- `/root/.hermes/scripts/gap300_signals.py` — SOURCE_LONG/SHORT constants
- `/root/.hermes/scripts/zscore_momentum.py` — SOURCE_TAG_LONG/SHORT constants
- `/root/.hermes/scripts/signal_gen.py` — `source=` in add_signal calls (phase-accel)
- `/root/.hermes/scripts/ma_cross_5m.py` — SOURCE_LONG/SHORT constants
- `/root/.hermes/scripts/oc_signal_importer.py` — source= in add_signal calls, conditional logic per oc_source type
- `/root/.hermes/scripts/signal_compactor.py` — `SIGNAL_SOURCE_WEIGHTS` dict (~line 140)
- `/root/.hermes/scripts/hermes_constants.py` — `SIGNAL_SOURCE_BLACKLIST` set

## Signal Naming Conventions (2026-04-23 session)
| Signal | LONG source | SHORT source |
|--------|-------------|--------------|
| gap-300 | `gap-300+` | `gap-300-` |
| phase-accel | `phase-accel+` | `phase-accel-` |
| zscore-momentum | `zscore-momentum+` | `zscore-momentum-` |
| oc-zscore-v9 | `oc-zscore-v9+` | `oc-zscore-v9-` |
| oc-mtf-macd | `oc-mtf-macd+` | `oc-mtf-macd-` |
| oc-rsi | `oc-rsi+` | `oc-rsi-` |
| ma-cross-5m | `ma-cross-5m+` | `ma-cross-5m-` |

## Renamed Sources Session Log (2026-04-23)
- `gap-300-long` → `gap-300+` | `gap-300-short` → `gap-300-`
- `phase-accel` → `phase-accel+` (LONG) / `phase-accel-` (SHORT) [made directional in add_signal call]
- `zscore-long` → `zscore-momentum+` | `zscore-short` → `zscore-momentum-`
- `zscore-v9` (OC bare) → `oc-zscore-v9+` (LONG) / `oc-zscore-v9-` (SHORT)
  - **BUG**: code was checking `oc_source == 'oc-pending-zscore-v9'` (auto-prefixed form), but OC sends bare `'zscore-v9'`
  - **FIX**: changed check to `oc_source == 'zscore-v9'` so the rename fires correctly
- `oc-pending-mtf-macd+` → `oc-mtf-macd+` | `oc-pending-mtf-macd-` → `oc-mtf-macd-`
- `oc-rsi-oversold` → `oc-rsi+` | `oc-rsi-overbought` → `oc-rsi-`
- `ma-cross-5m-long` → `ma-cross-5m+` | `ma-cross-5m-short` → `ma-cross-5m-`

## Pitfalls

### OC importer: check bare source names from JSON, not the auto-prefixed form
The OC JSON sends BARE source names (e.g. `zscore-v9`, `mtf-macd-bullish`).
The importer's else clause (line 159) auto-prefixes them to `oc-pending-zscore-v9`.
If you add a rename check for `oc-pending-zscore-v9` it will NEVER fire — you must check for `zscore-v9`.

Always verify the actual source value from the JSON first:
```python
python3 -c "
import json
d = json.load(open('/var/www/hermes/data/oc_pending_signals.json'))
from collections import Counter
ps = d.get('pending_signals', [])
print(Counter(s.get('source','') for s in ps))
"
```

### Blacklist uses exact matching
- `oc-pending-zscore-v9` ≠ `zscore`, so it wasn't blocked
- `zscore-momentum+` ≠ `zscore`, so it's also not blocked

### Directional conflict detector strips trailing `-short`/`-long`
- `zscore-short` → `zscore` (no polarity detected)
- `pct-hermes+` stays `pct-hermes+` (has `+` in the string body, not just suffix)

### Confluence gate counts comma-separated parts
Renamed sources may still be single-source and still blocked

### compact_rounds rejection
Signals with `compact_rounds >= 5` are REJECTED after 5 cycles without a 2nd source

## OC Pending Signal Sources (as of 2026-04-23)
```
zscore-v9          → oc-zscore-v9+ (LONG) / oc-zscore-v9- (SHORT)
mtf-macd-bullish   → oc-mtf-macd+
mtf-macd-bearish   → oc-mtf-macd-
mtf-rsi-oversold   → oc-mtf-rsi+
mtf-rsi-overbought → oc-mtf-rsi-
scanner-v9         → SKIPPED (redundant echo of Hermes's own signals)
```

## Debugging OC Source Rename Failures
If a rename appears correct in code but the DB still has the wrong source name:
1. Check the actual OC JSON source field: `python3 -c "import json; print([s['source'] for s in json.load(open('/var/www/hermes/data/oc_pending_signals.json'))['pending_signals']])"` — this reveals the bare source name
2. The importer's else clause auto-prefixes bare names to `oc-pending-*` — confirm which form your if/elif checks for
3. DB shows the merged source field — query: `sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT token, source FROM signals WHERE source LIKE '%zscore%' LIMIT 5;"`
4. Hotset.json (written by signal_compactor) will also show the wrong name if DB has it
5. The fix: check for the BARE OC source name (e.g. `'zscore-v9'`), not the already-prefixed form (`'oc-pending-zscore-v9'`)
