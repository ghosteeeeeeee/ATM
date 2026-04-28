---
name: mtf-macd-signal-debug
description: Debug why MTF-MACD signals (hmacd+/hmacd-) are generated but never appear in the hot-set or lead to trades. Found and fixed 2026-04-18.
category: trading
---

# MTF-MACD Signal Debug Skill

## Symptom

MTF-MACD signals are being generated (visible in pipeline logs: "RSI/MACD/Momentum: 0 RSI + 0 MACD + 90+ MTF-MACD") but:
1. No `hmacd+`/`hmacd-` signals appear in `/var/www/hermes/data/hotset.json`
2. No trades fire based on MTF-MACD confluence
3. Logs show "X signals approved" but all blocked by "Max positions reached" (red herring)

## Root Cause: SIGNAL_SOURCE_BLACKLIST

`hmacd++` and `hmacd--` (bare MTF-MACD without confluence) were in `SIGNAL_SOURCE_BLACKLIST` in `hermes_constants.py`. This silently filters signals BEFORE the confluence check.

**Location:** `/root/.hermes/scripts/hermes_constants.py` lines ~129-132

```python
# WRONG (blocked):
'hmacd++',    # non-confluence: bare hmacd++ without accompanying hmacd--
'hmacd--',    # non-confluence: bare hmacd-- without accompanying hmacd--

# CORRECT (unblocked):
# hmacd++ and hmacd-- are valid signal sources when paired with other indicators
```

Note: `hmacd+-` and `hmacd-+` (MTF disagreement variants / merge artifacts) SHOULD remain blocked.

## Why This Is Hard to Debug

1. **Silent filtering** — The blacklist check in `signal_compactor.py` (line ~448) silently drops signals before they reach the hot-set. No error, no obvious log entry.
2. **Pipeline log misleads** — Pipeline log shows "MTF-MACD: 90 added" — looks like signals are working. But they're filtered 2 steps later in ai_decider's hot-set gate.
3. **"hot-set gate BLOCKED" is stale** — Old log entries from 2026-04-07 say "hot-set gate BLOCKED — hot_cycle_count=0 < 1" — these are stale, not the current issue.
4. **Max positions is a red herring** — When positions are full, approved signals pile up behind the block. The real question is why MTF-MACD signals never accumulate enough hot-set rounds to auto-approve.

## How to Diagnose

```bash
# Step 1: Check what's in the hot-set source distribution
cat /var/www/hermes/data/hotset.json | python3 -c "
import json,sys
d = json.load(sys.stdin)
from collections import Counter
sources = Counter()
for s in d['hotset']:
    for p in s.get('source','').split(','):
        p = p.strip()
        if p: sources[p] += 1
for src, cnt in sources.most_common():
    print(f'  {src}: {cnt}')
"

# Step 2: Check blacklist in hermes_constants.py
grep -n "hmacd" /root/.hermes/scripts/hermes_constants.py

# Step 3: Check pipeline log for MTF-MACD generation
cat /root/.hermes/logs/pipeline.log | strings | grep -E "MTF-MACD|hmacd" | tail -10

# Step 4: Count MTF-MACD signals per cycle vs hot-set entries
cat /root/.hermes/logs/pipeline.log | strings | grep "RSI/MACD/Momentum" | tail -5
```

## Two-Layer Signal Filtering

MTF-MACD signals pass through TWO filter layers:

**Layer 1 — SIGNAL_SOURCE_BLACKLIST (signal_compactor.py):**
- Any source component in `SIGNAL_SOURCE_BLACKLIST` → signal dropped, stays PENDING
- Check: `any(p in SIGNAL_SOURCE_BLACKLIST for p in source_parts)`

**Layer 2 — Confluence filter (signal_compactor.py):**
- Single-source signals (only one comma-separated component) → blocked from hot-set
- Must have ≥2 distinct source components to enter hot-set
- Example: `hmacd+,hzscore` passes; `hmacd+` alone fails

MTF-MACD signal generation creates sources like:
- `hmacd+` (bare, single source) — will fail confluence filter
- `hmacd+,hzscore,pct-hermes` (3 sources) — passes confluence filter BUT only if hmacd++/-- not blacklisted

## The Fix

```python
# File: /root/.hermes/scripts/hermes_constants.py
# REMOVE these two lines from SIGNAL_SOURCE_BLACKLIST:
'hmacd++',    # non-confluence: bare hmacd++ without accompanying hmacd--
'hmacd--',    # non-confluence: bare hmacd-- without accompanying hmacd--

# KEEP these (merge artifact — should remain blocked):
'hmacd+-',    # MTF disagreement — both + and - present
'hmacd-+',    # MTF disagreement — both - and + present
```

## Counter-Signal Injection (Related Enhancement)

After wave_turn exits, position_manager injects counter-signals into the signal DB so the pipeline can catch reversals immediately. These use source=`wave_turn,momentum` (2 sources = passes confluence filter).

Key lesson: **always use 2+ source components** when injecting signals programmatically, otherwise they'll be blocked by the confluence filter and stay PENDING forever.

## Verification

```bash
# After fix, check hot-set for hmacd sources
sleep 120  # wait for next compaction cycle
cat /var/www/hermes/data/hotset.json | python3 -c "
import json,sys
d = json.load(sys.stdin)
hmacd = [(s['token'],s['source']) for s in d['hotset'] if 'hmacd' in s.get('source','')]
print(f'hmacd in hot-set: {len(hmacd)}')
for t,s in hmacd[:5]: print(f'  {t}: {s}')
"
```

## Related Files

- `/root/.hermes/scripts/hermes_constants.py` — SIGNAL_SOURCE_BLACKLIST
- `/root/.hermes/scripts/signal_compactor.py` — confluence filter (line ~254-259) and blacklist check (line ~448)
- `/root/.hermes/scripts/signal_gen.py` — MTF-MACD signal generation (line ~1909: `mtf_source = f'hmacd+{"+" if mtf_macd_direction == "LONG" else "-"}'`)
- `/root/.hermes/scripts/backtest_mtf_1h15m1m.py` — backtest script with validated params
- `/root/.hermes/skills/trading/mtf-macd-backtest-findings/` — latest backtest findings

## MTF-MACD Parameters Updated (2026-04-18)

**Old params:** Fast=12, Slow=26, Sig=9, z_1h > 0.5 blocking LONGs, crossover-based entry
**New params (backtest-validated):** Fast=10, Slow=20, Sig=7, z_1h > 3.0, histogram-agreement entry

See `mtf-macd-backtest-findings` skill for full findings and counterintuitive discoveries.