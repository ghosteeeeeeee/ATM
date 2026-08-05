---
name: systematic-signal-debug
description: Debug missing or wrong-source signals in Hermes hot-set pipeline — when pattern_scanner dominates or hzscore/hwave/vel-hermes signals vanish.
tags: [debugging, signals, hermes]
author: Hermes Agent
created: 2026-04-18
---

# Systematic Signal Debug — Signals Missing or Wrong Source

## When to Use
When signals disappear from the hot-set, only one source remains, or the wrong signals are being generated.

## Symptoms
- Only `pattern_scanner` signals appear (or only one source type)
- Hot-set empty despite signals existing in DB
- Some signal sources missing (e.g., no `hzscore`, no `hwave`, no `vel-hermes`)

## Step-by-Step Investigation

### Step 1: Check hot-set output
```bash
cat /var/www/hermes/data/hotset.json
python3 signal_compactor.py --dry --verbose 2>&1 | head -30
```

### Step 2: Check signals in DB by source
```python
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()
c.execute("SELECT source, COUNT(*) FROM signals WHERE decision='PENDING' GROUP BY source ORDER BY COUNT(*) DESC")
print(c.fetchall())
```

### Step 3: Check decision distribution (last 4 hours)
```python
c.execute("SELECT decision, COUNT(*) FROM signals WHERE created_at > datetime('now', '-240 minutes') GROUP BY decision")
```

### Step 4: Run signal_gen directly to find crashes
```bash
cd /root/.hermes/scripts
timeout 30 python3 -c "from signal_gen import _run_mtf_macd_signals; print(_run_mtf_macd_signals())" 2>&1
```
If this crashes or returns 0, `_run_mtf_macd_signals()` itself is broken.

### Step 5: Test individual sub-functions
```bash
cd /root/.hermes/scripts
timeout 30 python3 -c "from signal_gen import _run_hzscore_signals; print(_run_hzscore_signals())" 2>&1
timeout 30 python3 -c "from signal_gen import _run_hwave_signals; print(_run_hwave_signals())" 2>&1
timeout 30 python3 -c "from signal_gen import _run_pct_hermes_signals; print(_run_pct_hermes_signals())" 2>&1
```

### Step 6: Check pipeline log for errors
```bash
tail -100 /root/.hermes/logs/pipeline.log | grep -i "error\|exception\|traceback"
```

### Step 7: Check for undefined variable bugs in signal_gen
```bash
grep -n "tf_minutes\|undefined\|NameError" /root/.hermes/scripts/signal_gen.py
```
Common pattern: a nested function uses an outer scope variable that doesn't exist (e.g., `tf_minutes` instead of `minutes` parameter).

## Common Root Causes

### 1. Confluence gate blocking single-source signals (MOST COMMON)
**Symptom:** Hot-set empty. DB has signals (e.g., `gap-300-short`, `zscore-short`, `oc-pending-zscore-v9`). Compactor log shows:
```
🔒 [CONFLUENCE-GATE] TOKEN SHORT: single-source {gap-300-short} — waiting for 2nd source
```
**Root cause:** `signal_compactor.py:295` — `if len(source_parts) < 2:` blocks all single-source signals. They stay PENDING forever, never reach APPROVED.
**Where to look:**
```bash
tail -100 /root/.hermes/logs/signal-compactor.log | grep "CONFLUENCE-GATE"
```
**Fix:** Rename sources to have directional +/- suffix AND use compound sources. The gate counts comma-separated parts — a source like `gap-300+` (1 part) still gets blocked. The rename approach:
1. Source names should end in `+` (LONG) or `-` (SHORT) so the directional conflict detector parses them correctly
2. For single-source signals, the rename alone doesn't bypass the gate — the signal must be merged with another source OR the gate threshold must be lowered
3. User-preferred approach: rename sources one-by-one (user directs each rename), updating signal source constants AND scoring table entries together

**Files to update when renaming a source:**
- Signal source constant in the generator file (e.g., `gap300_signals.py:SOURCE_SHORT`)
- Scoring table `SIGNAL_SOURCE_WEIGHTS` in `signal_compactor.py` (add or update entry)
- Clear `.pyc` cache: `find /root/.hermes/scripts -name "*.pyc" -delete`

### 2. Directional conflict detector misreading sources
**Location:** `signal_compactor.py:289`
```python
long_srcs  = [p for p in source_parts if p.endswith('+')]
short_srcs = [p for p in source_parts if p.endswith('-')]
if long_srcs and short_srcs:
    log(f"  ⚔️  [CONFLICT] ... skipping")
    continue
```
**Problem:** Source `gap-300-short` ends in `-short` — it gets stripped to `gap-300` which has no `+`/`-`, so it's not in either list. But `pct-hermes+` (which ends in `+`) IS in `long_srcs`. If another source is in `short_srcs`, conflict fires even though `pct-hermes+` is just a momentum marker.
**Also:** Sources with `-short`/`-long` suffixes get their suffix stripped before polarity check — so `zscore-short` → `zscore` (no polarity), meaning it contributes nothing to `short_srcs`. This can cause a misleading conflict report.
**Fix:** Remove trailing `-short`/`-long` from source names. Use `+`/`-` suffixes only.

### 3. Blacklist uses exact string matching — not substring matching
**Location:** `signal_compactor.py:532`
```python
if any(p in SIGNAL_SOURCE_BLACKLIST for p in source_parts):
```
**Symptom:** `oc-pending-zscore-v9` was NOT blocked by blacklist despite containing `zscore` because blacklist has `'zscore'` but the source is `oc-pending-zscore-v9` (exact string mismatch). Similarly `zscore-momentum+` is NOT blocked by `'zscore'` in blacklist.
**Fix:** If a source should be blocked, add its exact name to `SIGNAL_SOURCE_BLACKLIST` in `hermes_constants.py`. If you want substring matching, change to `any(bl in p for p in source_parts for bl in SIGNAL_SOURCE_BLACKLIST)`.

### 4. Compact_rounds rejection threshold
**Location:** `signal_compactor.py` — signals with `compact_rounds >= 5` get REJECTED after 5 cycles without a 2nd source.
```bash
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, source, compact_rounds, decision FROM signals WHERE decision='PENDING' ORDER BY compact_rounds DESC LIMIT 10"
```
**Fix:** Lower the confluence gate threshold or rename/merge signals to add 2nd source component.

### 5. Compactor window too narrow
If signals are being generated but not seen, the 180-min window may be too short. Try 240 min.

### 6. OPEN_POSITION filter blocking everything
Check: `_get_open_tokens()` returns too many tokens. Step 11 pre-filter in signal_compactor may be blocking all signals.

## Key Files
- `/root/.hermes/scripts/signal_gen.py` — signal generation (hzscore, hwave, mtf_macd, vel-hermes, pattern_scanner)
- `/root/.hermes/scripts/signal_compactor.py` — hot-set compaction
- `/root/.hermes/scripts/decider_run.py` — execution
- `/root/.hermes/scripts/signal_schema.py` — DB operations
- `/root/.hermes/data/signals_hermes_runtime.db` — signal store
- `/root/.hermes/logs/pipeline.log` — execution log

## Verification Steps After Fix
1. `python3 -c "import signal_gen; print('signal_gen OK')"`
2. `cd /root/.hermes/scripts && python3 signal_compactor.py --dry 2>&1 | grep "hotset entries"`
3. Check hot-set has more than 1 entry and includes multiple source types
4. DB query shows signals from non-pattern_scanner sources
