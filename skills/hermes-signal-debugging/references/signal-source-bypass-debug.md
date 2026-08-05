---
name: signal-source-bypass-debug
description: Debug when standalone signal emitters (zscore_momentum, pump_hunter) bypass the hot-set pipeline and execute as single-source trades. Trace the execution path, identify the bypass and apply fixes to decider_run.py or hermes_constants.py. Also covers the phantom-EXECUTED bug where decider_run marks blocked signals as EXECUTED instead of SKIPPED, corrupting signal_outcomes and triggering false loss cooldowns.
tags: [hermes, signal-pipeline, bypass, single-source, standalone-emitter]
created: 2026-04-28
updated: 2026-04-28
trigger: single-source signals executing despite hot-set having multi-source signals; trades with sources like zscore-momentum- appearing in trades.json but not hotset.json; "where did these trades come from?"; standalone timer signal scripts bypassing approval gates; phantom EXECUTED marks with no corresponding HL position; loss cooldown firing after winning trades; signal_outcomes showing opposite-sign PnL pairs for the same trade
---

# Signal Source Bypass + Phantom EXECUTED Debug — Hermes Trading System

## Bug 1 (Primary): Phantom EXECUTED Marks — decider_run Uses `mark_signal_executed` for Blocked Signals

**Symptom:** Signals show `decision=EXECUTED` in DB but have NO corresponding trade on Hyperliquid and NO entry in trades.json. These phantom marks corrupt `signal_outcomes` (fake win/loss classification) and trigger **false loss cooldowns** — a trade with positive PnL gets classified as a loss because `signal_quality` reads from corrupted `signal_outcomes`.

**Root cause:** `decider_run.py` calls `mark_signal_executed()` for EVERY blocked signal — stale token, bad price, already open, single-source, speed=0%, etc. This marks them `decision=EXECUTED` so they never retry. But `EXECUTED` should mean "actually traded on Hyperliquid." Blocked signals should be marked `SKIPPED` or `BLOCKED`.

**Evidence (DYM gap300-5m+ at 03:17:10):**
- DB: `decision=EXECUTED`, `executed=1`, `created_at=2026-04-28 03:17:10`
- Pipeline log at 03:21:55: `🚫 [EXEC-BLOCK] DYM LONG blocked: speed=0% (stale token)` — never reached HL
- trades.json: DYM NOT present
- Hyperliquid: no DYM position existed
- signal_outcomes: phantom entry added with fake PnL

**Evidence (MEME zscore-momentum- at 02:39:52):** Same pattern — blocked by signal_compactor confluence gate but marked EXECUTED anyway.

**Downstream corruption:**
1. Phantom EXECUTED → written to `signal_outcomes` as if real trade
2. `signal_quality()` reads wrong source at close time → classifies winning trade as losing
3. Loss cooldown fires for winning trade → blocks valid re-entries
4. signal_outcomes shows duplicate entries with ±pnl for same trade (corrupted data)

**The Fix (Option 3 — T's request):** Require `APPROVED` status from signal_compactor. Only signals that passed through the hot-set pipeline should execute:

```python
# In decider_run.py — before executing any signal:
if sig.get('decision') != 'APPROVED':
    log(f'  🚫 [EXEC-BLOCK] {token} {direction} not APPROVED by hot-set (decision={sig.get("decision")}) — skipping')
    skipped += 1
    continue
```

**Secondary fix:** Change `mark_signal_executed()` calls for blocked signals to write `SKIPPED` or `BLOCKED` instead of `EXECUTED`. `EXECUTED` must mean "HL confirmed the position."

## Bug 2 (Root Enabler): Standalone Emitters Bypass Hot-Set Pipeline

**The Vulnerability:**

**Standalone signal emitters** (scripts with their own systemd timers like `zscore_momentum.py`, `pump_hunter.py`) write signals directly to the signals DB as `decision=PENDING`. These bypass the hot-set pipeline's approval gates:

```
signal_gen → signals DB (PENDING)
zscore_momentum.py → signals DB (PENDING)  ← standalone timer, own cycle
signal_compactor → reads PENDING, applies confluence gate, writes hotset.json
decider_run → reads APPROVED from DB, consults hotset.json, executes
```

The bypass: decider_run has a fallback path for PENDING signals, AND the single-source filter doesn't catch naming patterns like `zscore-momentum-` (ends with `-`, not `s`).

## Diagnostic Steps

### Step 1: Identify the standalone emitter

Check which signal source appeared in trade but NOT in hot-set:
```bash
grep "zscore-momentum" /var/www/hermes/data/hotset.json  # should return nothing
grep "source" /var/www/hermes/data/trades.json | grep zscore  # shows the source
```

Check if script has its own timer:
```bash
systemctl list-timers --all | grep zscore
systemctl list-timers --all | grep pump
```

### Step 2: Trace execution in journalctl

```bash
journalctl -u hermes-pipeline.service --since "YYYY-MM-DD HH:MM" | grep EXEC
```

Check signal_compactor blocking:
```bash
grep "CONFLUENCE-GATE-BLOCK" /root/.hermes/logs/signal-compactor.log | grep TOKEN
grep "APPROVED" /root/.hermes/logs/signal-compactor.log
```

### Step 3: Verify signal_compactor IS blocking

Look for `CONFLUENCE-GATE-BLOCK` entries for same token+direction before execution:
```
grep "FET SHORT\|ONDO SHORT" /root/.hermes/logs/signal-compactor.log
```
If blocker exists but trade still executed → bypass path confirmed.

### Step 4: Check single-source filter in decider_run.py

Line 1513 only catches sources ending in `s` or starting with `conf-`:
```python
if sig_src.startswith('conf-') or sig_src.endswith('s'):
    if sig_src == 'conf-1s' or sig_src.startswith('conf-1s'):
        log(f'  🚫 [EXEC-BLOCK] {token} {direction} blocked: {sig_src} (single-source, min 2 required)')
```

**MISSES:** `zscore-momentum-`, `zscore-momentum+` (end with `-`/`+`)

### Step 5: Verify signal was PENDING not APPROVED

```python
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()
c.execute("""
    SELECT id, token, direction, signal_type, source, confidence, 
           decision, executed, created_at
    FROM signals 
    WHERE token IN ('ONDO', 'FET') 
      AND source LIKE '%zscore%' 
    ORDER BY created_at DESC
    LIMIT 5
""")
```
If `decision=PENDING` and `executed=1` → bypassed the APPROVED pathway.

## Diagnostic Steps

### Step 0 (Always Start Here): Check for Phantom EXECUTED Marks

```python
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()

# Find EXECUTED signals with no corresponding HL trade
c.execute("""
    SELECT id, token, direction, source, confidence, price,
           decision, executed, pnl, realized_pnl, created_at, updated_at
    FROM signals
    WHERE decision = 'EXECUTED'
    ORDER BY created_at DESC
    LIMIT 20
""")
for r in c.fetchall():
    print(r)
```

Cross-reference against trades.json:
```python
import json
trades = json.load(open('/var/www/hermes/data/trades.json'))
executed_tokens = {t['coin'] for t in trades['open']}
executed_tokens |= {t['coin'] for t in trades['closed']}

# Check if phantom token is in trades.json
# If NOT → phantom EXECUTED mark
```

### Step 1: Identify the standalone emitter

Check which signal source appeared in trade but NOT in hot-set:
```bash
grep "zscore-momentum" /var/www/hermes/data/hotset.json  # should return nothing
grep "source" /var/www/hermes/data/trades.json | grep zscore  # shows the source
```

Check if script has its own timer:
```bash
systemctl list-timers --all | grep zscore
systemctl list-timers --all | grep pump
```

### Step 2: Trace execution in journalctl

```bash
journalctl -u hermes-pipeline.service --since "YYYY-MM-DD HH:MM" | grep EXEC
```

Check signal_compactor blocking:
```bash
grep "CONFLUENCE-GATE-BLOCK" /root/.hermes/logs/signal-compactor.log | grep TOKEN
grep "APPROVED" /root/.hermes/logs/signal-compactor.log
```

### Step 3: Verify signal_compactor IS blocking

Look for `CONFLUENCE-GATE-BLOCK` entries for same token+direction before execution:
```
grep "FET SHORT\|ONDO SHORT" /root/.hermes/logs/signal-compactor.log
```
If blocker exists but trade still executed → bypass path confirmed.

### Step 4: Check single-source filter in decider_run.py

Line 1513 only catches sources ending in `s` or starting with `conf-`:
```python
if sig_src.startswith('conf-') or sig_src.endswith('s'):
    if sig_src == 'conf-1s' or sig_src.startswith('conf-1s'):
        log(f'  🚫 [EXEC-BLOCK] {token} {direction} blocked: {sig_src} (single-source, min 2 required)')
```

**MISSES:** `zscore-momentum-`, `zscore-momentum+` (end with `-`/`+`)

### Step 5: Verify signal was PENDING not APPROVED

```python
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()
c.execute("""
    SELECT id, token, direction, signal_type, source, confidence,
           decision, executed, created_at
    FROM signals
    WHERE token IN ('ONDO', 'FET')
      AND source LIKE '%zscore%'
    ORDER BY created_at DESC
    LIMIT 5
""")
```
If `decision=PENDING` and `executed=1` → bypassed the APPROVED pathway.

### Step 6: Check signal_outcomes for corruption

```python
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()
c.execute("""
    SELECT * FROM signal_outcomes
    WHERE token = 'AAVE'
    ORDER BY closed_at DESC
    LIMIT 5
""")
# If same trade_id appears twice with ±pnl → phantom EXECUTED corrupted it
```

## Fix Applied (2026-04-28)

### signal_schema.py — `mark_signal_executed()` now accepts decision override

```python
def mark_signal_executed(token, direction, decision='EXECUTED', signal_id=None):
    """
    Mark a signal as processed (executed or skipped).

    BUG-FIX: Added optional `decision` param so blocked signals can be marked
    'SKIPPED' instead of 'EXECUTED'. 'EXECUTED' must mean "trade actually placed
    on Hyperliquid" — not "signal was considered and blocked".

    decision='EXECUTED': trade was actually placed (default)
    decision='SKIPPED':  signal was blocked/dropped, no trade placed
    """
    return update_signal_decision(token, direction, decision, signal_id=signal_id)
```

### decider_run.py — 7 blocked-signal sites now use 'SKIPPED'

All blocked-signal calls changed from:
```python
mark_signal_executed(token, direction, signal_id=sig_id)
```
to:
```python
mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
```

Sites changed (all 7 are blocked signals, NOT real executions):

| Line | Block reason |
|------|-------------|
| 1408 | Suspicious price (>5x from cached) |
| 1415 | Price out of absolute bounds |
| 1423 | Already open position |
| 1456 | Counter-trend trap |
| 1468 | Not tradeable on Hyperliquid |
| 1478 | Regime blindspot |
| 1519 | Single-source (conf-1s) |
| 1529 | Speed=0% (stale token) |

Line 1620 (actual execution) — unchanged, keeps default `'EXECUTED'`.

### Effect
- `decision='SKIPPED'` signals are NOT written to `signal_outcomes` as real trades
- Win/loss streaks no longer corrupted by phantom losses
- `decision='EXECUTED'` now reliably means "HL confirmed the position"

### Bug 2 (zscore- bypass) — NOT YET FIXED
The `zscore-momentum-` bypass of the single-source filter (line 1513: ends with `-`, not `s`) remains unfixed. See Bug 2 section above for the pending fix.

## Fix Options (Updated)

### Option 3 (Primary — T's Request): Require APPROVED Status

Block any PENDING signal that bypassed compaction — close the gap permanently for all standalone emitters:

```python
# In decider_run.py — add before all other checks:
sig_decision = sig.get('decision', '')
if sig_decision != 'APPROVED':
    log(f'  🚫 [EXEC-BLOCK] {token} {direction} not APPROVED by hot-set (decision={sig_decision}) — skipping')
    skipped += 1
    continue
```

This single fix addresses ALL THREE reported bugs:
1. **Phantom EXECUTEDs** — signals must be APPROVED by compactor
2. **zscore-momentum bypass** — its PENDING signals filtered at execution time
3. **Loss cooldown on wins** — signal_outcomes reflects only real trades

### Option 1 (Quick Fix): Blacklist the Source

In `hermes_constants.py`, add to `SIGNAL_SOURCE_BLACKLIST`:
```python
'zscore-momentum+',  # standalone timer, bypasses hot-set pipeline
'zscore-momentum-',  # standalone timer, bypasses hot-set pipeline
```

### Option 2 (Targeted Fix): Patch decider_run.py line 1513

Add after the existing single-source check:
```python
if sig_src.startswith('zscore-'):
    log(f'  🚫 [EXEC-BLOCK] {token} {direction} blocked: {sig_src} (standalone emitter)')
    if sig_id:
        mark_signal_executed(token, direction, signal_id=sig_id)  # ← should write SKIPPED not EXECUTED
    skipped += 1
    continue
```

**CRITICAL (secondary fix):** The `mark_signal_executed()` calls for blocked signals must write `SKIPPED` not `EXECUTED`. Find all such calls in decider_run.py and replace:
```python
# BEFORE:
mark_signal_executed(token, direction, signal_id=sig_id)

# AFTER:
from signal_schema import update_signal_decision
update_signal_decision(token, direction, 'SKIPPED', signal_id=sig_id)
```

## Key Files

- `/root/.hermes/scripts/decider_run.py` — line 1513 single-source filter, `mark_signal_executed` for blocks
- `/root/.hermes/scripts/signal_compactor.py` — confluence gate
- `/root/.hermes/scripts/zscore_momentum.py` — standalone emitter example
- `/root/.hermes/scripts/hermes_constants.py` — SIGNAL_SOURCE_BLACKLIST
- `/root/.hermes/scripts/signal_schema.py` — `update_signal_decision`, `mark_signal_executed`
- `/root/.hermes/data/signals_hermes_runtime.db` — signals DB
- `/root/.hermes/logs/signal-compactor.log` — confluence gate decisions
- `/root/.hermes/logs/pipeline.log` — execution log

## Verification

After fix:
1. Confirm single-source no longer executes
2. Run full pipeline cycle — hot-set populated with multi-source
3. Monitor `journalctl -u hermes-pipeline.service` for 5 minutes
4. Check trades.json — new entries should have multi-source signals only
5. Query signal_outcomes — no duplicate ±pnl entries for same token+direction

```python
# Sanity check: no phantom EXECUTEDs
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM signals WHERE decision='EXECUTED' AND executed=1")
print(f"EXECUTED signals: {c.fetchone()[0]}")
# Should be > 0 only if real HL trades exist for all of them
```

## Related Skills

- `signal-compactor-survival-bugs` — compactor internal bugs (partial overlap)
- `phantom-trade-debugging` — guardian orphan creation (complementary: DB phantom vs HL phantom)
- `zscore-momentum-signal` — implementation (separate concern)
- `systematic-signal-debug` — general signal pipeline debugging
- `cooldown-tracker-ms` — downstream cooldown corruption (symptom of phantom EXECUTED)
