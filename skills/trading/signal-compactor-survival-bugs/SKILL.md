---
name: signal-compactor-survival-bugs
description: Signal compaction bugs causing empty hot-set — confluence gate blocking 98% of signals (ongoing), directional conflict parser treating signal name suffixes as source polarity conflicts, and compact_rounds=5 rejection cascade. Compactor log at /root/.hermes/logs/signal-compactor.log is the primary diagnostic tool.
version: 1.5.0
author: Hermes Agent
created: 2026-04-17
updated: 2026-04-27
tags: [signals, compaction, hot-set, bug-fix, signal-compactor, confluence-gate, breakout]
description: Signal compaction bugs causing empty hot-set or incorrect signal survival — confluence gate blocking signals, staleness not recomputing on preserve, breakout single-source exemption needed, directional conflict parser treating signal name suffixes as source polarity conflicts. Compactor log at /root/.hermes/logs/signal-compactor.log is the primary diagnostic tool.
metadata:
  hermes:
    files: [/root/.hermes/scripts/signal_compactor.py]
    symptom: hotset.json empty or missing signals that should have been approved
    diagnostic_file: /root/.hermes/logs/signal-compactor.log
---

# Signal Compactor Survival Bugs (2026-04-17)

## Bug 1: Confluence Gate — 98% of Signals Blocked (ONGOING)

### Symptom
hotset.json is empty. `Decider Done: 0 entered` every cycle. Pipeline logs show:
```
🧊 [HOT-SET] hotset.json is empty — no signals survived compaction
No signals above 50% confidence — skipping execution
```

### Root Cause
`signal_compactor.py` line ~295 — the CONFLUENCE ENFORCEMENT gate requires `len(source_parts) < 2`:
```python
if len(source_parts) < 2:
    log(f"  🔒 [CONFLUENCE-GATE] {token} {direction}: single-source {{{source}}} — waiting for 2nd source")
    continue
```
AND line ~289 — directional conflict detection strips `-short`/`-long` suffixes and rejects if both `+` and `-` polarities exist in the same merged source string:
## Bug 1: Confluence Gate — 98% of Signals Blocked (PARTIALLY RESOLVED)

### Symptom
hotset.json is empty. `Decider Done: 0 entered` every cycle. Pipeline logs show:
```
🧊 [HOT-SET] hotset.json is empty — no signals survived compaction
No signals above 50% confidence — skipping execution
```

**2026-04-23 afternoon update**: After fixing `_is_loss_cooldown_active` (Pattern 8 in cooldown-tracker-ms), hot-set now correctly populates. 10 multi-source signals pass the confluence gate and score 98-169. After purging 182 signal-gen entries from `loss_cooldowns.json`, hot-set repopulated with 10 tokens (XAI, 0G, ATOM, AVAX, DOT, FIL, MEME, NIL, LINK, XRP SHORT).

**Key distinction**: Empty hot-set + `Pre-filter: 10+` = cooldown blocking (cooldown-tracker-ms Pattern 8). Empty hot-set + `Pre-filter: 0` = confluence gate blocking (Bug 1 here).

### Confluence Gate Log Evidence (2026-04-23)
```
[2026-04-23 00:38:00] [INFO] [signal-compactor] Query: 122 token+direction pairs in 10-min window
[2026-04-23 00:38:00] [INFO] [signal-compactor]   🔒 [CONFLUENCE-GATE] S SHORT: single-source {zscore-short} — waiting for 2nd source
[2026-04-23 00:38:00] [INFO] [signal-compactor]   🔒 [CONFLUENCE-GATE] FIL SHORT: single-source {oc-pending-zscore-v9} — waiting for 2nd source
[2026-04-23 00:38:00] [INFO] [signal-compactor]   🔒 [CONFLUENCE-GATE] AR LONG: single-source {phase-accel} — waiting for 2nd source
[2026-04-23 00:38:00] [INFO] [signal-compactor] Pre-filter: 17 signals passed safety filters
[2026-04-23 00:38:00] [INFO] [signal-compactor] Previous hotset: 0 entries loaded
[2026-04-23 00:38:00] [INFO] [signal-compactor] All entries filtered or no signals — preserving previous hotset
[2026-04-23 00:38:00] [INFO] [signal-compactor] STALLED 132 signals (still pending, rounds+1)
[2026-04-23 00:38:00] [INFO] [signal-compactor] REJECTED 26 signals after 5 rounds
[2026-04-23 00:38:00] [INFO] [signal-compactor] Wrote hotset.json with 0 tokens (cycle=10497)
```

### Key Diagnostic Commands
```bash
# Compactor's own log (separate from pipeline.log):
cat /root/.hermes/logs/signal-compactor.log | grep "CONFLUENCE-GATE\|Pre-filter\|STALLED\|REJECTED"

# Check PENDING signals with compact_rounds approaching 5:
cd /root/.hermes/scripts && python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute(\"\"\"
    SELECT token, direction, confidence, source, compact_rounds, created_at
    FROM signals
    WHERE decision IN ('PENDING','WAIT') AND executed=0 AND compact_rounds >= 4
    ORDER BY compact_rounds DESC LIMIT 20
\"\"\")
for r in cur.fetchall(): print(f'  {r[0]:10} {r[1]:5} conf={r[2]:5} cr={r[4]} src={r[3]}')
cur.close()
conn.close()
"

# Check what's actually in the hot-set:
cat /var/www/hermes/data/hotset.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Hot-set: {len(d[\"hotset\"])} entries')"
```

### The 5-Round Rejection Cascade
After a signal reaches `compact_rounds >= 5` (was APPROVED→EXECUTED or just aged out), it gets REJECTED:
```python
elif cr >= 5:
    rejected_ids.append(sid)
```
This means every cycle, ~26 signals permanently drop out, and new ones slowly accumulate rounds. The net result: hot-set stays near-empty because nothing can gather enough rounds to survive.

### Fix Options
1. **Lower the gate** (line ~295): `len(source_parts) >= 1` instead of `>= 2` — allows single-source signals through
2. **Remove the gate entirely** — let scoring/ranking decide quality
3. **Fix signal generators** to produce multi-source merged signals (hardest)

### Verification
After fix, hotset.json should populate within 1 cycle. Check:
```bash
cat /var/www/hermes/data/hotset.json
# Should show entries, not: {"hotset": [], "compaction_cycle": N}

---

## Bug 2: Open-Position Ghost Signals

### Symptom
A token shows `APPROVED` in compaction logs and enters hotset, but no trade executes. The pipeline fires the trade but Hyperliquid returns no fill. The signal becomes a ghost — in hotset, never fills, clogs execution.

### Root Cause
signal_compactor.py has no check for tokens that already have an open position in PostgreSQL `paper_trades` table. A signal for a token that's already open gets approved and enters hotset, but the Guardian's regime filter (or HL itself) blocks the fill. The signal survives compaction cycles indefinitely.

### Fix Applied
Added `_get_open_tokens()` function and Step 11 filter in the compaction loop:
```python
def _get_open_tokens(self):
    """Returns set of tokens with open positions in paper_trades."""
    rows = self.db_query("""
        SELECT DISTINCT token FROM paper_trades
        WHERE exit_price IS NULL OR exit_price = 0
    """)
    return {r[0] for r in rows}

# In compaction loop, after decision scoring:
if token in self._get_open_tokens():
    decision = 'SKIPPED'
    reason = 'open_position'
    continue
```

### Verification
Tokens with open positions should now get `SKIPPED open_position` instead of `APPROVED`.

---

## Key Lesson: Display Bug Is Often A Red Herring

The `entries_count` field in hotset.json (displayed as "Entries: 1x") was showing the wrong count (1 instead of number of distinct sources). Investigation revealed the **entries_count computation was actually correct** — the real issue was no signals were reaching hotset at all due to the confluence gate.

When debugging hotset issues: **check that signals are even reaching the file first**, before fixing display logic.

---

## Bug 7: Open-Position Ghost Signals — Live PostgreSQL Filter Gap (2026-04-23)

**Symptom**: MEME (or any token) appears in hot-set.json AND a new MEME signal re-enters in the same compaction cycle. Guardian fires a trade → PostgreSQL `status='open'` → hot-set.json NOT updated until next compactor run (~1 min later) → MEME still in hot-set AND new MEME signal appears → re-entry loop. Memory note confirmed MEME had a live trade with pnl=+7.2% but was still in hot-set.

**Root cause**: Compactor's `_open_pos_cache` is updated at the START of each compactor run, but guardian fires trades DURING the run. There's a ~1-minute window where:
1. Guardian fires trade for MEME → PostgreSQL `trades.status='open'`
2. `_open_pos_cache` still shows MEME as NOT open (was cached before the trade)
3. MEME signal passes the open-position filter
4. MEME written to hot-set.json alongside new MEME signal

**Fix** (`signal_compactor.py` lines 720-726 — right before writing hot-set.json):
```python
# Remove tokens with open positions right before writing hot-set.json.
# Closes the ~1-min gap where guardian fires a trade but _open_pos_cache
# hasn't been refreshed from PostgreSQL yet.
live_open_tokens = _get_open_tokens()
if live_open_tokens:
    hotset_output = [e for e in hotset_output if e['token'].lower() not in live_open_tokens]
    removed = [e['token'] for e in hotset_output if e['token'].lower() in live_open_tokens]
    if removed:
        log(f"  🛡️  [HOTSET-FILTER] Removed {removed} traded tokens (open pos)")
```

**Why this fix is correct**: Uses the existing `_get_open_tokens()` function and FileLock infrastructure already present at the write step. Re-queries PostgreSQL directly instead of relying on the stale cache.

**Diagnosis**:
```bash
# Check if a traded token is still in hot-set
cat /var/www/hermes/data/hotset.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'Hot-set tokens: {[e[\"token\"] for e in d[\"hotset\"]]}')"

# Check PostgreSQL for open positions
python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute(\"SELECT token, direction, status FROM trades WHERE status='open'\")
print('Open positions:', cur.fetchall())"
```

---

## Bug 3: z_score Read from Wrong Column Index (HIGH — fixed 2026-04-22)

### Symptom
z_score was always 0 for PENDING signals in hotset.json output.

### Root Cause
signal_compactor.py ~line 461. The GROUP BY query returns columns in this order:
```
[0]=token, [1]=direction, [2]=signal_type, [3]=confidence, [4]=source,
[5]=created_at, [6]=z_score_tier, [7]=z_score, [8]=compact_rounds, [9]=hot_cycle_count
```
But the code read `row[9]` (always 0 for PENDING signals = hot_cycle_count) instead of `row[7]`.

### Fix Applied
```python
# Wrong:
'z_score': row[9] or 0,
# Correct:
'z_score': row[7] or 0,
```

---

## Bug 4: compact_rounds Inflates Survival Bonus on PENDING→APPROVED (HIGH — fixed 2026-04-22)

### Symptom
A signal that survived 3 PENDING compaction rounds, when finally APPROVED, would get `compact_rounds=4` instead of `compact_rounds=1`. Survival bonus formula: `1.0 + compact_rounds * 0.15`, so it got 1.60× instead of 1.15× — inflated bonus based on PENDING rounds, not actual hot-set survival rounds.

### Root Cause
Line ~574: `compact_rounds = COALESCE(compact_rounds, 0) + 1` on PENDING→APPROVED transition kept incrementing.

### Fix Applied
```python
# Wrong (increment):
compact_rounds = COALESCE(compact_rounds, 0) + 1,
# Correct (reset to 1):
compact_rounds = 1,
```
Survival bonus now starts fresh from round 1 when a signal enters the hot-set.

---

## Bug 5: Zero-Score Signals Enter Hotset (MED — fixed 2026-04-22)

### Symptom
A 5+ hour old PENDING signal gets `staleness_mult=0.0` → `score=0.0`, but was still appended to scored list and could enter top-10 hotset with score=0, displacing legitimate signals.

### Fix Applied
Added skip in scoring loop (after `_score_signal()` call):
```python
if score <= 0:
    if verbose:
        log(f"  SCORE-ZERO skip {token} {direction}: age_h={age_h:.2f}")
    continue
```

---

## Bug 6: get_regime_15m Dead Code → Wired to Scoring (MED — fixed 2026-04-22)

### Symptom
`get_regime(coin)` existed and queried PostgreSQL for regime but was **never called**. The scoring loop used `regime_cache.get(token.upper(), ('NEUTRAL', 0))` which always returned NEUTRAL (the JSON file didn't exist). Regime multiplier (+15% aligned / -30% counter) was completely non-functional.

### Fix Applied
- Renamed `get_regime` → `get_regime_15m`, rewired into scoring loop at line ~362
- Primary source: `/var/www/hermes/data/regime_15m.json` (schema: `{"regimes": {"BTC": {"regime": "LONG_BIAS", "confidence": 75}}}`)
- Fallback: `momentum_cache.regime_15m` column in PostgreSQL
- Confidence: 75 if <15min old, 40 if stale
- Also fixed tzinfo bug: was comparing naive `now` against tz-aware `updated_at`

---

## Scope Gotcha When Patching Python

When patching code that references variables from inner scopes (e.g., `staleness_mult` computed inside `_score_signal()`), note that patching in a new `continue` block at a higher level creates a scope mismatch. Use variables already in scope (e.g., `age_h`) for any diagnostic log messages inside the new block.

---

## Python Patch Pitfalls (signal_gen.py patch session, 2026-04-22)

### Indentation Nesting When Patching `except:`

When replacing `except:` with `except Exception:` in deeply-nested code, always read the full surrounding context first. A bare `except:` inside a nested `try:` block will have a different indentation than the `except:` at the function level. If you patch with the wrong indentation, you can create or break nesting.

**Always read 10+ lines around the target before patching.**

### Example Fix Pattern

```python
# BEFORE (broken nesting — except at wrong indent level):
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
        except Exception:   # ← was indented under `with`, not `try`
            pass

# AFTER (correct):
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:        # ← at same indent as `try`
        pass
```

### Scope Reference Rule

When adding a new `continue/break/pass` block in a `for` or `while` loop via patch, use only variables already bound in that loop scope. Don't reference variables computed inside helper functions called in that same iteration.

---

**Files**: `/var/www/hermes/scripts/signal_compactor.py` (open-position filter), `/var/www/hermes/scripts/hl-sync-guardian.py` (never writes hot-set.json — compactor owns it).

---

## Bug 8: Cooldown Flood — Every Trade Close Writing Cooldowns, Blocking All Signals (2026-04-23)

**Symptom**: Hot-set stays empty for ~1 hour. `signal-compactor.log` shows `Pre-filter: 17 signals passed` but then `COOLDOWN skip` for EVERY signal. 0 tokens written to hot-set.json for consecutive cycles. `approved_list` in `hermes-trades-api.py` shows 0 entries.

**Root cause**: `decider_run.py` line 672 was calling `set_cooldown()` on **every closed trade**, not just losses:
```python
# WRONG — wrote 1-hour cooldown on EVERY close (win or loss):
if trade_dir:
    set_cooldown(token.upper(), trade_dir.upper(), hours=1)

# FIXED — only on LOSS closes:
if trade_dir and 'loss' in reason.lower():
    set_cooldown(token.upper(), trade_dir.upper(), hours=1)
```

**Effect**: PostgreSQL `signal_cooldowns` table accumulated 217+ active `reason='signal'` entries. `signal_compactor.py`'s `get_cooldown()` checks PostgreSQL first → every signal hit `COOLDOWN skip` → hot-set empty for ~1 hour.

**Why `decider_run.py` was the culprit**: The `reason` parameter at line 672 comes from `guardian.close_trade()` and contains the loss description (e.g., "stop_loss", "regime_exit"). For winning trades, `reason` is typically "take_profit" — adding `'loss' in reason.lower()` guard prevents cooldowns on wins while preserving them for losses.

**Note**: `position_manager.py` line 712 also writes cooldowns on losses — it already has an `if is_win == 0` guard, so it's correct.

**Diagnosis**:
```bash
# Check active cooldown count in PostgreSQL
cd /root/.hermes && python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM signal_cooldowns WHERE expires_at > NOW()\")
print(f'Active cooldowns: {cur.fetchone()[0]}')
cur.execute(\"SELECT reason, COUNT(*) FROM signal_cooldowns WHERE expires_at > NOW() GROUP BY reason\")
print('By reason:', cur.fetchall())
"

# Check signal-compactor.log for COOLDOWN skip pattern
grep "COOLDOWN skip" /root/.hermes/logs/signal-compactor.log | tail -5

# Check why decider_run is writing so many cooldowns
grep -n "set_cooldown" /root/.hermes/scripts/decider_run.py | head -10
```

**Fix**: Add `'loss' in reason.lower()` guard in `decider_run.py` line ~672. Clear stale cooldowns:
```bash
python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute(\"DELETE FROM signal_cooldowns\")
conn.commit()
print('Cleared all cooldowns')
"
```

**Key lesson**: When EVERY signal is blocked by cooldown despite no obvious loss events, check `signal_cooldowns` table directly. The cooldown flood is the most likely cause. Cooldowns should only rebuild naturally from actual losing trades.

---

## Bug 9: Loss Cooldown Read/Write Mismatch — All Hot-Set Signals Blocked (2026-04-23)

**Symptom**: 16 approved signals in hot-set but 0 entering trades every cycle. Logs show:
```
SKIP: DOT SHORT in loss cooldown
SKIP: TIA LONG in loss cooldown
SKIP: ATOM SHORT in loss cooldown
... (16 skipped, 0 entered)
```

**Root Cause**: `decider_run.py` line 1521 called `is_loss_cooldown_active()` from `position_manager.py`, which checks BOTH `loss_cooldowns.json` AND PostgreSQL `signal_cooldowns` table. The PostgreSQL table had accumulated **188 rows** of stale cooldowns from signal generators (gap300, ma_cross_5m, etc.) — signal-generator cooldowns, NOT actual losing trade cooldowns. Every cycle, all 16 hot-set signals hit the PostgreSQL check and got blocked.

**Key distinction from Bug 8**: Bug 8 was about `set_cooldown()` writing on EVERY trade. This bug is about `is_loss_cooldown_active()` reading from PostgreSQL — a read-side mismatch.

**Why it passed signal_compactor**: `signal_compactor.py` was already fixed (2026-04-23) to use `signal_schema._is_loss_cooldown_active()` (JSON-only). So hot-set was being populated correctly, but `decider_run.py` was blocking them all at execution time.

**Fix Applied** (`decider_run.py` line 1521):
```python
# Before:
from position_manager import (..., is_loss_cooldown_active, set_loss_cooldown, ...)
...
if is_loss_cooldown_active(token, direction):

# After:
from position_manager import (..., set_loss_cooldown, ...)
from signal_schema import _is_loss_cooldown_active
...
if _is_loss_cooldown_active(token, direction):
```

**Diagnosis**:
```bash
# Check PostgreSQL cooldown count
cd /root/.hermes && python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM signal_cooldowns WHERE expires_at > NOW()')
print(f'Active cooldowns: {cur.fetchone()[0]}')
cur.execute('SELECT COUNT(*) FROM signal_cooldowns')
print(f'Total rows: {cur.fetchone()[0]}')
"

# Check which cooldowns are active vs expired
python3 -c "
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute('''
    SELECT token, direction, reason, expires_at > NOW() as is_active
    FROM signal_cooldowns
    ORDER BY is_active DESC
''')
for r in cur.fetchall(): print(f'  {r[0]:10} {r[1]:5} {r[2]:20} active={r[3]}')
"

# Verify decider_run uses JSON-only check
grep -n 'is_loss_cooldown_active\|_is_loss_cooldown_active' /root/.hermes/scripts/decider_run.py
grep -n 'is_loss_cooldown_active\|_is_loss_cooldown_active' /root/.hermes/scripts/signal_compactor.py
```

**Key lesson**: When fixing cooldown bugs, fix BOTH the read side AND write side. `signal_compactor` and `decider_run` must use the same cooldown checking function — JSON-only vs PostgreSQL+JSON mismatch causes one to pass signals the other blocks.

---

## Bug 12: import os Inside Function — UnboundLocalError Crash (2026-04-26)

**Symptom**: signal_compactor.py crashes with `UnboundLocalError: cannot access local variable 'os' where it is not associated with a value` on line 352 (`os.path.exists()`), but only in the normal (non-dry) execution path.

**Root Cause**: `import os` appeared inside the `if not dry:` block at line 785:
```python
if not dry:
    import tempfile, os  # ← 'os' assigned here
    ...
    # Line 352 runs BEFORE this block, referencing 'os':
    if os.path.exists(SPEED_CACHE_FILE):  # ← UnboundLocalError!
```

Python treats any assignment (including `import`) of a name inside a function as making that name local throughout the entire function. When line 352 runs, `os` is marked as a local but hasn't been assigned yet — `UnboundLocalError`.

**Fix**: Remove `os` from the local import (it's already globally imported at line 18):
```python
# Before:
import tempfile, os
# After:
import tempfile
```

**Key lesson**: The `import os` shadowing pattern is subtly different from the classic "nested function assigns outer scope variable" gotcha. Here, `import` itself creates an assignment to the module name in the local namespace. Search for `import os` inside function bodies as a separate bug class from nested function scoping.

**Diagnosis**:
```bash
python3 /root/.hermes/scripts/signal_compactor.py --dry  # Would succeed (skips the crash path)
python3 /root/.hermes/scripts/signal_compactor.py         # Would crash
```

Search pattern for this bug:
```bash
grep -n "^    import os\|^        import os\|import os," /root/.hermes/scripts/*.py
```

**Prevention**: Never import modules inside function bodies unless you need a module that's not available at module load time. Prefer module-level imports.

---

## Bug 13: age_h Staleness — 5 Hours Instead of 5 Minutes (2026-04-26)

**Symptom**: Signals were accumulating rounds and surviving far too long. A signal could stay in the hot-set for hours despite the intended 5-minute staleness penalty.

**Root Cause**: Staleness formula used hours instead of minutes:
```python
# Before (WRONG):
age_h = (datetime.now() - created_t).total_seconds() / 3600  # hours
staleness_mult = max(0.0, 1.0 - (age_h * 0.2))  # -20%/hour
survival_bonus condition: age_h < 1.0  # 1 hour threshold
```

Changed to minutes:
```python
# After (CORRECT):
age_m = (datetime.now() - created_t).total_seconds() / 60  # minutes
staleness_mult = max(0.0, 1.0 - (age_m * 0.2))  # -20%/minute → 0 at 5min
survival_bonus condition: age_m < 5.0  # 5 minute threshold
```

**Impact**: At `age_h=1.0` (old code), staleness_mult=0.8 (only 20% penalty after 1 hour!). At `age_m=5.0` (new code), staleness_mult=0.0 (signal is dead). Signals that should have died at 5 minutes were surviving for hours.

**Files changed**: `/root/.hermes/scripts/signal_compactor.py` — lines 185, 199, 431, 435, 445, 453, 459, 482, 559 (parameter rename + formula unit change).

---

## Bug 14: GROUP BY Query Only Sees Latest PENDING Row — APPROVED Signals Invisible (2026-04-26)

**Symptom**: Dashboard shows LINEA SHORT and UMA SHORT as "PENDING" with conf=58% and single source. Investigation shows they already have APPROVED signals with conf=88% and 2-source confluence (`gap-300-,zscore-momentum-`). User suspects signals aren't advancing to hot-set.

**Root Cause**: The GROUP BY query at line 270-293 filters `WHERE decision = 'PENDING'`. When a signal is APPROVED, it disappears from this query. The newest PENDING row for the same token+direction is a different, newer signal with lower confidence and single source.

```python
# The query only sees PENDING rows:
WHERE decision = "PENDING"  # APPROVED rows are invisible to this query
```

The actual signal state (from `signals_hermes_runtime.db`):
```
LINEA SHORT: decision=APPROVED conf=88.0 source="gap-300-,zscore-momentum-" cr=2 (from 19:34)
LINEA SHORT: decision=PENDING  conf=58.0 source="gap-300-"                  cr=0 (from 19:37) ← latest PENDING
```

The GROUP BY returns only the latest row — the older APPROVED signal is invisible. The dashboard PENDING view is misleading because it shows the low-confidence single-source row while the high-quality signal is already APPROVED and in the hot-set.

**Important**: This is NOT a bug — it's working as designed. Signals move PENDING→APPROVED correctly. The confusion arises from:
1. Dashboard showing PENDING view (latest PENDING signal) rather than "best signal per token"
2. Multiple decision states can coexist for the same token+direction (older APPROVED + newer PENDING)

**Key diagnostic** — always query the DB directly to see full signal history:
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()
c.execute('''
    SELECT token, direction, decision, executed, source, confidence,
           compact_rounds, hot_cycle_count, created_at, updated_at
    FROM signals
    WHERE token=? AND decision IN (\"PENDING\",\"APPROVED\")
    ORDER BY created_at DESC LIMIT 5
''', ('LINEA',))
for r in c.fetchall():
    print(f'  decision={r[2]} conf={r[5]} cr={r[6]} created={r[8]} src={r[4]}')
"
```

---

## Bug 15: compact_rounds Tracks Failure Count, Not Survival Rounds (2026-04-26)

**Symptom**: `survival_round` values in hot-set.json (e.g., BCH cr=11, BRETT cr=6) don't match actual hot-set cycle counts. User expects rounds = how many consecutive cycles the SAME source combination fired together.

**Root Cause — compact_rounds is conflating two different concepts**:

The column `compact_rounds` in the DB tracks two completely different things depending on decision state:

1. **PENDING signals**: failure count — how many compaction cycles a PENDING signal tried to enter top-10 and failed. At each cycle not in top-10: `compact_rounds += 1` (line 690). At cr >= 5: REJECTED.

2. **APPROVED signals**: hot-set survival count — bumped +1 each cycle the signal stays in hot-set (line 717).

These are unrelated. A PENDING signal can reach cr=11 by failing 11 times and getting REJECTED. An APPROVED signal gets cr=1 on PENDING→APPROVED transition (line 673), then increments each cycle.

**The MAX() aggregation problem**: The GROUP BY query at line 272-293 uses `MAX(compact_rounds)` across ALL PENDING signals for a token+direction. When merging sources (e.g., `fast-momentum+,gap-300+`), if ANY source had a high cr (from prior APPROVED state or failure count), the merged result inherits that cr. This is wrong — rounds should reflect how many times THIS specific source combination fired together.

**Staleness uses MAX(created_at) per token+direction, not per source combination**: When DYDX has `fast-momentum+,gap-300+` (created 19:45) merged with a newer `zscore-momentum-` (created 19:55), `MAX(created_at)` = 19:55. But the hot-set entry's sources are `fast-momentum+,gap-300+`, not `zscore-momentum-`. The staleness age is from a source not in the entry.

**Evidence from live data**:
```
BCH: APPROVED cr=11 — but BCH has only ~2 hot-set cycles in history
CAKE: fast-momentum+,gap-300+ APPROVED cr=6
DYDX: fast-momentum+,gap-300+ APPROVED cr=2 (from 19:45)
DYDX: gap-300+ PENDING cr=0 (from 19:49)
```

BCH's cr=11 came from PENDING signals that failed to reach top-10 eleven times before being REJECTED. Not 11 survival rounds.

**What "rounds" should mean** (user's intent):
- A signal generator fires every minute independently
- `gap-300+` fires at T=0 → single source → blocked at confluence gate (single-source)
- `fast-momentum+` fires at T=0 → single source → blocked
- Both fire at T=0 → merged → enters hot-set, rounds=1
- Next minute same combo fires → rounds=2
- If one fires alone → blocked at confluence gate

**Staleness uses wrong timestamp**: The GROUP BY uses `MAX(created_at)` across ALL PENDING signals for token+direction. For DYDX: `fast-momentum+,gap-300+` APPROVED signal created at 19:45 (5.2 min ago), but a newer `zscore-momentum-` PENDING signal at 19:55 (1.3 min ago) makes `MAX(created_at)` = 19:55. The hot-set entry is for `fast-momentum+,gap-300+` LONG, but staleness is computed from a different source (zscore-momentum-) that isn't even in the entry.

**Fix requires**:
1. Track source combination identity: `(token, direction, sorted(source_parts))` as the round-tracking key
2. Rounds increment only when ALL sources in the combination fire together in the same cycle
3. Staleness = `created_at` of the MOST RECENT signal among the ACTUAL sources in the hot-set entry (not MAX across all PENDING signals for that token+direction)

**Diagnosis**:
```bash
python3 - << 'EOF'
import sqlite3
db = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
# Check cr distribution for APPROVED signals
cur = db.execute("""
  SELECT token, direction, source, confidence, compact_rounds, created_at
  FROM signals WHERE decision='APPROVED' AND executed=0
  ORDER BY compact_rounds DESC LIMIT 10
""")
print("APPROVED signals by cr (highest first):")
for r in cur.fetchall():
    print(f"  cr={r[4]:<3} {r[0]:<8} {r[1]:<5} src={r[2][:40]} created={r[5]}")
EOF
```

**Key lesson**: When a single integer column tracks two different concepts (PENDING failure count vs APPROVED survival count), the MAX() aggregation will pick up the wrong concept at the wrong time. Separate columns or a composite key for round tracking are needed.

---

## Bug 16: Merge-vs-Replace — Previous Hot-Set Discarded When DB Has Signals (2026-04-27)

**Symptom**: Breakout-engine entries appear in hot-set.json one cycle, then vanish the next. Hot-set token count fluctuates wildly. A token with a high-scoring DB signal drives out breakout entries entirely.

**Root Cause**: Step 12 in `signal_compactor.py` had an early return pattern:
```python
# If DB rebuild produced any signals:
if hotset_final:
    # ... build hotset_final ...
    log(f"  Compaction: {len(hotset_final)} DB signals pass all filters")
    hotset = hotset_final  # Use DB rebuild ONLY
    return  # ← EXITS HERE, prev_hotset entries never merged
```

When `hotset_final` was non-empty (DB had signals), the function returned immediately with `hotset_final`. The `prev_hotset` (previous cycle's entries, including breakout-engine entries that wrote directly) was **discarded entirely**.

**The broken logic**:
- Cycle 1: DB empty → `prev_hotset` preserved (correct)
- Cycle 2: DB has 5 signals → only those 5 written, `prev_hotset` entries lost
- Breakout entries (not in DB) vanish whenever DB rebuild produces anything

**Fix Applied** (2026-04-27): Removed the early return. `prev_hotset` entries are now always filtered through `_filter_safe_prev_hotset` and merged with DB entries in Step 12:
```python
# Always merge prev_hotset with DB rebuild, keeping higher score per token:direction
filtered_prev = _filter_safe_prev_hotset(prev_hotset, now_ts, verbose=False)
for entry in filtered_prev:
    key = f"{entry['token']}:{entry['direction']}"
    if key not in scored_map or entry['confidence'] > scored_map[key]['confidence']:
        scored_map[key] = entry
        log(f"  ↪ Preserved {entry['token']} {entry['direction']} from prev_hotset")
```

**Key change**: `prev_hotset` merge runs AFTER DB rebuild, not instead of it. Higher-confidence entry per token:direction wins.

**Diagnosis**:
```bash
# Run compactor in dry mode and look for "Preserved" lines:
python3 /root/.hermes/scripts/signal_compactor.py --dry 2>&1 | grep -E "Preserved|Merged|DB signals"

# Check hot-set.json token count over consecutive cycles:
for i in 1 2 3; do
  cat /var/www/hermes/data/hotset.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Cycle {i}: {len(d[\"hotset\"])} tokens')"
  sleep 65
done
```

**Key lesson**: Any "use X or Y" pattern (DB rebuild OR prev_hotset) creates a flicker/vanishing problem. The correct pattern is "merge X AND Y, keep best per identity" — both sets of entries should compete.

---

## Bug 17: Staleness Static on Preserve — Fixed (2026-04-27)

**Symptom**: Breakout entries survive indefinitely in `prev_hotset` across compaction cycles. Staleness stays at 1.0 even after many cycles. `entry_origin_ts` missing or not being used for staleness recomputation.

**Root Cause**: `_filter_safe_prev_hotset` refreshed `entry['timestamp']` but never recomputed `staleness` from `entry_origin_ts`.

**Fix Applied** (2026-04-27):
```python
# entry_origin_ts: set once when combo first enters hot-set, carried forward on preserve
entry_origin_ts = entry.get('entry_origin_ts')
current_ts = time.time()
if entry_origin_ts is None:
    entry_origin_ts = current_ts  # First time this entry is in hot-set
    entry['entry_origin_ts'] = entry_origin_ts
entry['timestamp'] = current_ts
age_min = (current_ts - entry_origin_ts) / 60.0
entry['staleness'] = max(0.0, 1.0 - age_min * 0.2)
# Expire entries with staleness <= 0.01 (5+ minutes old)
if entry['staleness'] <= 0.01:
    continue
# NOTE: rounds and compact_rounds are NOT decremented on preserve.
# Staleness (wall-clock) is the ONLY exit mechanism.
```

`compact_rounds` is NOT decremented on preserve — it has no role in hot-set exit. Staleness reaching 0 is the only way a signal exits.

**Survival math** (staleness-only exit):
- Entry enters at `entry_origin_ts = now`
- Each 1-min cycle: staleness recomputed from `entry_origin_ts`
- At 5 min wall-clock: `1.0 - 5/5 = 0.0` → exits

**entry_origin_ts carry-forward in Step 9** (signal_compactor.py line ~606-617):
```python
# For new combos: entry_origin_ts = now
# For existing combos (found in prev_hotset_by_combo): carry forward entry_origin_ts
if prev_entry:
    prev_origin_ts = prev_entry.get('entry_origin_ts')
    entry_origin_ts = prev_origin_ts if prev_origin_ts else time.time()
else:
    entry_origin_ts = time.time()
```

---

## Bug 18: Breakout Source — Single-Source Exemption Needed (2026-04-27)

**Symptom**: Breakout entries written by `breakout_engine.py` use `source='breakout'`, which gets blocked at the confluence gate (requires 2+ sources). Even though breakout writes directly to hot-set.json, the compactor's pre-filter blocks it when merging.

**Root Cause**: Confluence gate at line ~393: `if len(source_parts) < 2: continue` — breakout is single-source by design but has no exemption.

**Fix Applied** (2026-04-27): Added `source != 'breakout'` exemption at TWO places:
1. DB query pre-filter: `if len(source_parts) < 2 and source != 'breakout': continue`
2. `_filter_safe_prev_hotset` confluence check: breakout entries pass through without 2-source requirement

breakout writes to BOTH DB (`source='breakout'`, `combo_key='TOKEN:DIRECTION:breakout'`) and hot-set.json directly. Compactor picks it up from DB on next 1-min cycle.

**Files changed**: `signal_compactor.py` lines ~393, ~1029.

---

## Bug 19: Timer Set to 1 Minute (Final — 2026-04-27)

The compactor fires every 1 minute via `hermes-signal-compactor.timer`:
```ini
OnCalendar=*:0/1:00  # Every 1 minute at :00, :01, :02, etc.
```

Each signal has its own internal `entry_origin_ts` wall-clock timer. A signal lives exactly 5 minutes wall-clock from when it first entered the hot-set, regardless of how many compaction cycles fire. Timer fires every 1 min to keep the hot-set fresh and merge breakout entries promptly.

**Timer vs Pipeline**: The compactor does NOT run inside `run_pipeline.py`. It runs ONLY via the systemd timer. The pipeline's `STEPS_EVERY_MIN` does not include `signal_compactor`. No cron jobs call it either.

---

## Bug 11: add_signal() 30-Min Merge Window — Stale Sources Propagating (2026-04-26)

**Symptom**: A signal's `source` field in the EXEC line shows multiple sources (e.g., `[gap-300+,zscore-momentum+]`) but only ONE signal was actually firing at execution time. The second source is a ghost — it fired 15-30 min earlier, got merged, expired, but its source tag was never cleared from the merged row.

**Root Cause**: `signal_schema.py` `add_signal()` merge query used a **30-minute window**:
```python
WHERE token=? AND direction=? AND executed=0 AND decision='PENDING'
  AND created_at > datetime('now', '-30 minutes')  # ← 30 min window
```
Meanwhile, `signal_compactor.py` expires PENDING signals at **5 minutes** (line 255-264):
```python
WHERE decision='PENDING' AND created_at < datetime('now', '-5 minutes')
```

This mismatch means: a signal that expired at T+5 min is no longer visible to the compactor, but is still findable by `add_signal()` up to T+30 min. When a new signal arrives at T+20, it merges with the stale expired signal's row, inheriting its source tags. The compactor never sees this merge because the stale signal is already EXPIRED.

**Fix Applied** (2026-04-26): `signal_schema.py` line 465 — merge window reduced from 30 min to 5 min:
```python
# Before:
AND created_at > datetime('now', '-30 minutes')
# After:
AND created_at > datetime('now', '-5 minutes')
```
This brings `add_signal()` in sync with the compactor's 5-min expiry lifecycle.

**Key design principle**: A signal should only merge with signals that are truly contemporaneous (±5 min). The compactor expires signals at 5 min — `add_signal()` must not have a longer merge window, or stale source tags propagate to new signals.

**Verification**:
```bash
# Check if any signals have source tags from stale/expired emissions
cd /root/.hermes/scripts && python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
# Find PENDING signals with multiple sources that may be stale
cur.execute('''
    SELECT token, direction, source, signal_types, created_at, decision
    FROM signals
    WHERE decision IN (\"PENDING\",\"APPROVED\")
    AND source LIKE '%,%'
    ORDER BY created_at DESC LIMIT 20
''')
for r in cur.fetchall():
    print(f'{r[0]:10} {r[1]:5} src={r[2][:50]:50} types={r[3][:30]} {r[4]}')
"
```

**Related bugs**: Bug 1 (confluence gate), Bug 4 (compact_rounds inflation), Bug 10 (OC signal auto-approval bypass) — all involve signals surviving incorrectly or bypassing lifecycle discipline.

**Files**: `/root/.hermes/scripts/signal_schema.py` (merge window fix), `/root/.hermes/scripts/signal_compactor.py` (5-min expiry, line 255-264)

---

## Bug 10: OC Signal Auto-Approval Bypass — oc_pending Signals Skip Hot-Set Survival (2026-04-23)

**Symptom**: BCH LONG (`source=oc-pending-mtf-rsi-oversold,pct-hermes+`) was REJECTED/EXPIRED during LLM compaction but got EXECUTED anyway via an auto-approver at 04:25 on 2026-04-23. Neither appeared in hotset.json.

**Root Cause**: The system has two approval paths:
1. **Hot-set path (tracked survival)**: `signal_compactor` → `hotset.json` → `decider_run` iterates hotset.json. Signals must survive LLM compaction rounds to enter hotset.json.
2. **Auto-approver path (bypasses survival)**: `_run_hot_set()` in decider_run.py auto-approved ANY PENDING signal from the DB with conf ≥ 55 if no open position exists — WITHOUT checking hot-set survival.

OC signals were frequently rejected by the LLM compactor during `signal_compactor` runs but got auto-approved by the auto-approver minutes later, bypassing survival tracking entirely.

**Evidence from DB**: MEW LONG (conf=76.8%) and BCH LONG (conf=88.0%) both had `source=oc-pending-mtf-rsi-oversold,pct-hermes+`. Both were REJECTED/EXPIRED in the DB during LLM compaction but got EXECUTED anyway.

**Fix Applied** (`decider_run.py` lines 1423-1433):
```python
# ── OC Signal Block (2026-04-23) ──────────────────────────────────────────
# oc_pending signals must survive signal_compactor hot-set compaction.
# They are NOT auto-approved here — they go through the same survival
# rounds check as all other signals. This prevents OC from bypassing
# the hot-set discipline by writing directly to the signal DB.
# Leave as PENDING so they continue competing in compaction cycles.
sig_type = sig.get('signal_type', '') or ''
if sig_type == 'oc_pending':
    log(f'  🚫 [EXEC-BLOCK] {token} {direction} blocked: oc_pending signal (must survive hot-set compaction)')
    skipped += 1
    continue
```

**Note**: The `_run_hot_set()` function itself was not found in the current codebase (may have been removed or renamed), but the oc_pending block at execution time achieves the same protection.

**Diagnosis**:
```bash
# Check if oc_pending signals are getting executed without appearing in hotset.json
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute('''
    SELECT token, direction, confidence, source, decision, compact_rounds, executed, created_at
    FROM signals
    WHERE source LIKE '%oc%'
    ORDER BY created_at DESC LIMIT 20
''')
for r in cur.fetchall(): print(f'  {r[0]:10} {r[1]:5} conf={r[2]:5} cr={r[5]} exec={r[6]} src={r[3]}')
"

# Check hotset.json for a specific token
cat /var/www/hermes/data/hotset.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'Hot-set tokens: {[e[\"token\"] for e in d[\"hotset\"]]}')
"

# Check trades.json for OC signal execution
cat /var/www/hermes/data/trades.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
for t in d.get('trades',[]):
    if 'oc' in t.get('source','').lower():
        print(f'  OC trade: {t[\"token\"]} {t[\"direction\"]} conf={t.get(\"confidence\")} src={t.get(\"source\")}')
"
```

**Key lesson**: When adding external signal sources (OC), ensure they go through the same survival discipline as native signals. An auto-approver that bypasses hot-set survival undermines the entire compaction mechanism. OC signals should either compete fairly in hot-set or be blocked entirely.

**Alternative fix options**:
- Raise the auto-approver threshold for `oc_pending` signals to 90+ (only allow if extremely high confidence)
- Add `oc_pending` signals to signal_compactor's survival tracking so they compete in hot-set like all other signals
- Block `oc_pending` signals entirely from auto-approval (chosen: option 1 = block at execution)

---

## Bug 20: APPROVED Signals Expire Before Decider Can Execute — Triple Fix (2026-04-27)

**Symptom**: 4+ APPROVED signals in DB, decider has an open trade slot, but 0 trades execute. `get_approved_signals()` returns empty or stale results. hot-set has valid signals.

**Root Cause — Three independent bugs** (all introduced 2026-04-26 by a prior fix attempt):

---

**Bug 20A: `compact_rounds` vs `survival_rounds` field name mismatch (HIGH)**

`signal_schema.py:1022` — `get_approved_signals()` reads `compact_rounds` for the `hot_rounds` filter:
```python
hot_rounds_max = COALESCE(MAX(compact_rounds), 0)
```
But `signal_compactor.py` line 790 writes `survival_rounds` (never `compact_rounds`):
```python
survival_rounds = new_hcc,  # written as 'survival_rounds'
```
Result: every APPROVED signal has `survival_rounds=N >= 1` but `compact_rounds=0`. Decider's `MIN_COMPACT_ROUNDS=1` always fails → 0 trades.

**Fix Applied** (`signal_schema.py:1022`):
```python
# Before:
hot_rounds_max = COALESCE(MAX(compact_rounds), 0)
# After:
hot_rounds_max = COALESCE(MAX(survival_rounds), 0)
```

---

**Bug 20B: `hcc >= 1` immediately expires freshly approved signals (HIGH)**

`signal_compactor.py:847` — Step 14 EXPIRE query runs `hot_cycle_count >= 1`:
```python
AND hot_cycle_count >= 1  -- WRONG: catches signals approved THIS cycle
```
But newly approved signals get `hot_cycle_count=1` in Step 13 of the SAME cycle. They immediately qualify for expiration in Step 14.

**Fix Applied** (`signal_compactor.py:847`):
```python
# Before:
AND hot_cycle_count >= 1
# After:
AND hot_cycle_count >= 2  -- Must survive at least one full cycle before becoming eligible
```

---

**Bug 20C: Python `TypeError` from `.format()` with empty list (MED)**

`signal_compactor.py:849` — used f-string `.format()` to build the `approved_ids` exclusion:
```python
if approved_ids:
    sql += f" AND id NOT IN ({','.join(['?']*len(approved_ids))})"
    c.execute(sql, approved_ids)
else:
    c.execute(sql)  -- approved_ids list passed as 2nd arg to sql
```
When `approved_ids=[]`: the `else` branch executes `sql` (which still contains `AND id NOT IN ()`) AND passes `approved_ids=[]` as the second `execute()` argument → Python sqlite3 `TypeError: too many arguments`.

**Fix Applied** — restructured as explicit if/else:
```python
if approved_ids:
    placeholders = ','.join(['?'] * len(approved_ids))
    expire_sql = f"UPDATE signals SET decision='EXPIRED', ... WHERE id IN ({placeholders})"
    c.execute(expire_sql, approved_ids)
else:
    pass  # No approved signals to exclude, nothing to expire
```

---

**Combined Diagnosis**:
```bash
# Check APPROVED signal field values
cd /root/.hermes/scripts && python3 -c "
import sqlite3
db = '/root/.hermes/data/signals_hermes_runtime.db'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute('''
    SELECT token, decision, survival_rounds, compact_rounds, hot_cycle_count, confidence
    FROM signals WHERE decision=\"APPROVED\" AND executed=0
    ORDER BY survival_rounds DESC LIMIT 10
''')
print('APPROVED signals (sr=survival_rounds, cr=compact_rounds, hcc=hot_cycle_count):')
for r in c.fetchall():
    print(f'  {r[0]:<10} sr={r[2]:<2} cr={r[3]:<2} hcc={r[4]:<2} conf={r[5]}')
conn.close()
"

# Check decider hot_rounds filter — should use survival_rounds not compact_rounds
grep -n 'hot_rounds\|MIN_COMPACT_ROUNDS\|compact_rounds\|survival_rounds' \
  /root/.hermes/scripts/signal_schema.py | grep -E 'hot_rounds|compact|survival'
```

**Key lesson**: A prior "fix" introduced three bugs simultaneously. The `compact_rounds` vs `survival_rounds` mismatch is a schema integrity failure — field names must match between the writer and all readers. The `hcc >= 1` logic error and Python unpacking bug are both classic "one step later in the same function" bugs — newly written values immediately feeding back into filtering logic in the same cycle.

---

## Bug 21: Field Name Mismatch — `compact_rounds` Written But `hot_rounds` Reads It (2026-04-27)

See Bug 20A above. Same root cause, captured separately for clarity.

**Key diagnostic**:
```bash
# Verify what field the compactor ACTUALLY writes
grep -n 'survival_rounds\|compact_rounds' /root/.hermes/scripts/signal_compactor.py | grep -v '^#' | head -20

# Verify what field get_approved_signals reads
grep -n 'hot_rounds\|compact_rounds\|survival_rounds' /root/.hermes/scripts/signal_schema.py | head -20
```

The compactor writes `survival_rounds` (line ~790). The decider's `get_approved_signals()` reads `compact_rounds` (line ~1022). These are different columns — one is always 0, the other increments. They must match.

---

## Bug 22: Same-Cycle Approval → Expiration — Logic Feedback Loop (2026-04-27)

See Bug 20B above. When a signal transitions PENDING→APPROVED in Step 13 (hcc=1), Step 14 runs in the same function call and sees hcc=1. The fix (`hcc >= 2`) requires the signal to survive one complete additional cycle before becoming eligible for expiration.

---

## Bug 23: Python `.format()` TypeError in Dynamic SQL Builder (2026-04-27)

See Bug 20C above. Classic: empty list `[]` is still a truthy object passed as an argument, but `.format()` consumed placeholder tokens leaving the list as a dangling extra argument.

---

## Bug 24: Single-Source gap-300- / accel-300+ Bypass — Direct mark_signal_executed() Path (2026-04-27)

**Symptom**: A token shows `decision='EXECUTED', executed=1` in `signals_hermes_runtime.db` for a single-source signal (gap-300-, accel-300+) with conf=58, but `signal-compactor.log` has NO entry for that token at that timestamp, `sync-guardian.log` has NO XAI entries, and `pipeline.log` has NO gap-300 entries. All similar signals (same source, same conf, different tokens) correctly EXPIRED.

**Observed cases (2026-04-27)**:
- XAI SHORT `gap-300-` conf=58 → **EXECUTED** at 06:20:28 and 06:47:44 (single source, should have been blocked)
- LINEA LONG `accel-300+` conf=58 → **EXECUTED** at 05:49:22 (accel-300+ IS in SIGNAL_SOURCE_BLACKLIST, should have been blocked)
- LINEA LONG `gap-300+` conf=58 → **EXPIRED** (same conf, correctly blocked)
- PEOPLE SHORT `gap-300-` conf=58 → **EXPIRED** (same source, correctly blocked)

**Root Cause Hypothesis — Direct Execution Bypass**:
`signal_schema.py:918` `mark_signal_executed()` can set `decision='EXECUTED', executed=1` directly WITHOUT going through the hot-set pipeline. If something calls `mark_signal_executed(signal_id)` or `mark_signal_executed(token=..., direction=...)` with a single-source signal, it bypasses:
1. Confluence gate (signal_compactor.py:379-388) — requires 2+ sources
2. SIGNAL_SOURCE_BLACKLIST check in compactor's Step 11 safety filter
3. Preservation filter (signal_compactor.py:1040-1063)

**Key Evidence**:
- LINEA `accel-300+` is in `SIGNAL_SOURCE_BLACKLIST` (hermes_constants.py line 102). Compactor's safety filter checks the blacklist. Yet it was EXECUTED at 05:49:22.
- Compactor log at 05:47-05:49 shows LINEA was NEVER mentioned in any merge/preserve/approval step.
- XAI's single-source `gap-300-` at 06:14:20 was correctly EXPIRED (2-source requirement working). But 06:20:28 and 06:47:44 show as EXECUTED with no compactor log trace.
- LINEA and PEOPLE with identical conf=58 single-source gap-300 patterns correctly EXPIRED — the confluence gate IS working for those tokens.

**Diagnostic**:
```bash
# Find signals marked EXECUTED directly (not APPROVED first)
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute('''
    SELECT token, direction, signal_type, source, confidence, decision, executed,
           created_at, updated_at
    FROM signals
    WHERE decision=\"EXECUTED\" AND executed=1
    ORDER BY updated_at DESC LIMIT 20
''')
print('EXECUTED signals (should be rare):')
for r in cur.fetchall():
    print(f'  {r[0]:10} {r[1]:5} src={r[3]:40} conf={r[4]} created={r[7]} updated={r[8]}')
"

# Trace the execution path for a specific signal
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute('''
    SELECT token, direction, signal_type, source, confidence, decision, executed,
           compact_rounds, hot_cycle_count, created_at, updated_at
    FROM signals
    WHERE token=\"XAI\" AND direction=\"SHORT\" AND decision=\"EXECUTED\"
    ORDER BY created_at DESC LIMIT 5
''')
print('XAI SHORT EXECUTED signals:')
for r in cur.fetchall():
    print(f'  src={r[3]} conf={r[4]} cr={r[7]} hcc={r[8]} created={r[9]} updated={r[10]}')
"

# Check signal_outcomes for execution details
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute('''
    SELECT token, direction, outcome, created_at
    FROM signal_outcomes
    WHERE token IN (\"XAI\", \"LINEA\")
    ORDER BY created_at DESC LIMIT 10
''')
print('signal_outcomes:')
for r in cur.fetchall():
    print(f'  {r[0]:10} {r[1]:5} {r[2]:20} {r[3]}')
"

# Search ALL logs for a specific execution timestamp
grep -r "06:20:28\|05:49:22" /root/.hermes/logs/ 2>/dev/null | grep -v ".gz" | head -20
```

**Fix Required**:
1. Audit ALL callers of `mark_signal_executed()` in signal_schema.py and callers across all scripts. Any call that passes a single-source signal must first verify the signal passed through the hot-set pipeline (decision=APPROVED, hot_cycle_count>=1).
2. Add enforcement in `mark_signal_executed()` itself — reject if signal has single source AND was never APPROVED:
   ```python
   # In mark_signal_executed(), before marking EXECUTED:
   if decision != 'APPROVED':
       raise ValueError(f"Cannot execute signal {signal_id}: decision={decision} (must be APPROVED)")
   ```
3. Check if `accel-300+` in SIGNAL_SOURCE_BLACKLIST is actually being checked at execution time (decider_run.py), not just at compaction time. Blacklisted sources should be rejected at BOTH pipeline stages.

**Prevention**: Any signal reaching `decision='EXECUTED'` must have first been `decision='APPROVED'` in the hot-set. If a signal goes directly PENDING→EXECUTED, that's a bypass. Add a DB constraint or a post-execution audit query:

## Bug 26: pct-hermes+ Exact-String Blacklist Gap (2026-04-27)

**Symptom**: BRETT traded with `source=gap-300+,pct-hermes+` (dual source, correctly passed confluence gate) but pct-hermes+ may not be blocked by the blacklist because the check uses exact string matching. `pct-hermes+` (with `+`) is not in `SIGNAL_SOURCE_BLACKLIST` — only `pct-hermes` (no suffix) and `pct-hermes-` (with `-`) are listed.

**Root Cause**: The blacklist check at `signal_schema.py:410` does `p in SIGNAL_SOURCE_BLACKLIST` (exact string equality). `'pct-hermes+' not in SIGNAL_SOURCE_BLACKLIST` returns True even though `'pct-hermes' in SIGNAL_SOURCE_BLACKLIST` is True. The `+` suffix makes it a different string.

**Key diagnostic command** — check if directional variants are missing from blacklist:
```bash
# List all sources with +/- suffixes currently in the signals DB
cd /root/.hermes/scripts && python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute(\"\"\"
    SELECT DISTINCT source FROM signals
    WHERE source IS NOT NULL
    ORDER BY source
\"\"\")
import re
all_srcs = {r[0] for r in cur.fetchall() if r[0]}
# Find sources with +/- suffix not in the blacklist
blacklist = {'pct-hermes','pct-hermes-','vel-hermes','vel-hermes+','vel-hermes-',
             'hzscore','hzscore+','hzscore-','rsi','rsi-hermes','hmacd+-','hmacd-+',
             'ma-cross','r2_rev','support_resistance','conf-1s',
             'oc-zscore-v9+','oc-zscore-v9-','oc-zscore-v9',
             'oc-mtf-rsi','oc-mtf-rsi+','oc-mtf-rsi-',
             'oc-mtf-macd+','oc-mtf-macd-','accel-300+'}
for src in sorted(all_srcs):
    parts = src.split(',')
    for p in parts:
        p = p.strip()
        if p.endswith('+') or p.endswith('-'):
            base = p[:-1]
            if base in blacklist and p not in blacklist:
                print(f'  MISSING from blacklist: {p} (base {base} is blocked)')
"
```

**Fix**: Add explicit directional variants to `SIGNAL_SOURCE_BLACKLIST` in `hermes_constants.py`:
```python
'pct-hermes+',   # exact-string check: pct-hermes+ != pct-hermes
'vel-hermes+',    # vel-hermes blocked, vel-hermes+ not
```

## Bug 27: Pipeline Log Gap — Compactor and Pipeline Run Separately (2026-04-27)

**Symptom**: Trades show as EXECUTED in PostgreSQL but have no corresponding entries in `/root/.hermes/logs/pipeline.log`. Pipeline.log only shows entries from April 2 and April 27 17:00+ — there is a gap from April 2 to April 27 midday.

**Root Cause**: The compactor runs via `hermes-signal-compactor.timer` (systemd, every 1 min) and logs to `/root/.hermes/logs/signal-compactor.log`. The pipeline runs via `hermes-pipeline.timer` and logs to `/root/.hermes/logs/pipeline.log`. These are independent systems. Trade EXEC lines appear in pipeline.log, not signal-compactor.log.

**Key evidence**: `signal-compactor.log` shows "Pre-filter: N signals passed" but NOT which specific tokens. To trace a specific trade, search both logs:
```bash
# Trade execution time from PostgreSQL → search BOTH logs
grep "2026-04-27 13:48" /root/.hermes/logs/signal-compactor.log
grep "2026-04-27 13:48" /root/.hermes/logs/pipeline.log
# The pipeline.log may not have entries for those timestamps if the log was rotated
```

**Pipeline.log rotation evidence**: `pipeline.log` contains entries from April 2 and April 27 17:00+ but nothing from April 3-27. The compactor log is the primary diagnostic tool for signal-level tracing (separate from trade execution).

**Key lesson**: When investigating why a specific signal executed, always check `signal-compactor.log` (signal pipeline) NOT `pipeline.log` (trade execution pipeline). The execution logs (EXEC lines) are in `pipeline.log`, but the signal approval/failure logs are in `signal-compactor.log`.

---

## Bug 25: oc-mtf-macd+ Single-Source Bypass via Counter-Flip Path (2026-04-27)

**Symptom**: ATOM and TAO both executed trades with `source='oc-mtf-macd+'` (single source) despite the confluence gate requiring 2+ sources. Both lost money. BRETT had `gap-300+,pct-hermes+` (dual source) and also lost. SNX had `gap-300+` (single source) but won.

**PostgreSQL trade evidence** (2026-04-27):
```
ATOM  LONG @ $1.9943  closed 13:48  source=oc-mtf-macd+   loss -0.59%
TAO   LONG @ $250.72  closed 13:44  source=oc-mtf-macd+   loss -0.51%
BRETT LONG @ $0.0071  closed 13:28  source=gap-300+,pct-hermes+  loss -0.72%
SNX   LONG @ $0.3120  closed 13:11  source=gap-300+        win  +0.81%
```

**Root Cause — Three issues**:

1. **`oc-mtf-macd+` not in SIGNAL_SOURCE_BLACKLIST**: `hermes_constants.py` blocks `oc-mtf-rsi+` (line 140) but NOT `oc-mtf-macd+`. The confluence gate in `signal_compactor.py` is bypassed by the counter-flip signal path which writes single-source `oc-mtf-macd+` directly to the DB.

2. **`gap-300+` not in SIGNAL_SOURCE_BLACKLIST**: Same problem — `gap-300+` fires as a single source and bypasses the confluence gate when it should require a second confirming source.

3. **Counter-flip bypass**: `oc_signal_importer.py` writes `source='oc-mtf-macd+'` signals directly to the DB. The confluence gate in `signal_compactor.py` correctly blocks single-source signals from the pre-filter, but counter-flip signals have their own execution path that doesn't go through the hot-set pipeline's confluence enforcement.

**The confluence gate IS working correctly** — the problem is the counter-flip path writing directly to DB with single sources.

**Fix Applied** (same pattern as oc-mtf-rsi):
```python
# hermes_constants.py — add to SIGNAL_SOURCE_BLACKLIST:
# 2026-04-27: BLOCK oc-mtf-macd — counter-flip bypass writes single-source
# oc-mtf-macd+ directly to DB, bypassing confluence gate. oc-mtf-rsi+
# was already blocked this same day.
'oc-mtf-macd+',
'oc-mtf-macd-',
# 2026-04-27: BLOCK gap-300+ as solo source — requires second confirming
# source to establish confluence. Dual-source combos like gap-300+,zscore-momentum+
# still pass through normally.
'gap-300+',
'gap-300-',
```

**Key DB evidence** — signals table shows oc-mtf-macd+ correctly EXECUTED despite being single-source:
```sql
-- ATOM oc-mtf-macd+ signals (all single-source, all EXECUTED):
ATOM|LONG|oc_mtf_macd|oc-mtf-macd+|65.0|2026-04-27 13:02:50|EXECUTED
ATOM|LONG|oc_mtf_macd|oc-mtf-macd+|65.0|2026-04-27 13:53:16|EXECUTED

-- TAO oc-mtf-macd+ signals (all single-source, all EXECUTED):
TAO|LONG|oc_pending|oc-mtf-macd+|88.0|2026-04-27 13:02:50|EXECUTED
TAO|LONG|oc_pending|oc-mtf-macd+|88.0|2026-04-27 13:53:17|EXECUTED

-- Compactor log at 13:02 (when first pair executed):
[OPEN-POS-FILTER] Tokens with open positions: ['brett', 'snx', 'uni']
-- ATOM and TAO were NOT in the open-positions list yet
-- Pre-filter: 5 signals passed (all dual-source combos)
-- ATOM/TAO oc-mtf-macd+ SINGLE SOURCE were correctly blocked by confluence gate
-- But the counter-flip path bypassed the gate and wrote EXECUTED directly to DB
```

**Note on BRETT's dual-source loss**: `gap-300+,pct-hermes+` is dual-source and correctly passed the confluence gate. The loss was a signal quality issue (pct-hermes+ is strong, gap-300+ alone is weak — the combo didn't have enough confirmation). This is different from the single-source bypass problem.

**Diagnosis**:
```bash
# Find single-source signals marked EXECUTED (should be 0)
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute('''
    SELECT token, direction, source, confidence, decision, executed, created_at
    FROM signals WHERE decision=\"EXECUTED\" AND executed=1 AND source NOT LIKE \"%,%\"
    ORDER BY created_at DESC LIMIT 10
''')
print('Single-source EXECUTED signals (should be 0):')
for r in cur.fetchall():
    print(f'  {r[0]:10} {r[1]:5} src={r[2]:30} conf={r[3]}')

# Check PostgreSQL trades for single-source signals
sudo -u postgres psql brain -c \"SELECT token, strategy, entry_price, pnl_pct, close_time FROM trades WHERE open_time::text LIKE '2026-04-27%' ORDER BY open_time;\" 2>&1 | grep -v "^sudo\|^Password"
```

**Prevention**: Any signal source that writes directly to the DB (counter-flip, OC signals, breakout) must be added to `SIGNAL_SOURCE_BLACKLIST` if it fires as a single source. The blacklist is the safety net when bypass paths exist. Do NOT rely on the confluence gate alone for externally-sourced signals.
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM signals WHERE decision=\"EXECUTED\" AND executed=1')
total = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM signals WHERE decision=\"EXECUTED\" AND executed=1 AND source NOT LIKE \"%,%\"')
single = cur.fetchone()[0]
print(f'EXECUTED signals: {total} total, {single} single-source')
cur.execute('''
    SELECT token, direction, source, confidence, created_at, updated_at
    FROM signals WHERE decision=\"EXECUTED\" AND executed=1 AND source NOT LIKE \"%,%\"
''')
for r in cur.fetchall():
    print(f'  SINGLE-SOURCE EXECUTED: {r[0]} {r[1]} src={r[2]} conf={r[3]}')
"
```

## Bug 28: None Source AttributeError Bypass — `_filter_safe_prev_hotset` Crash-Through (2026-04-27)

**Symptom**: Single-source signals (confirmed: GAS `[gap-300+]`, ATOM `[oc-mtf-macd+]`) execute despite confluence gate in `signal_compactor.py` line 385. No compactor log trace of the signal being APPROVED, yet trade executes.

**Root Cause**: `_filter_safe_prev_hotset()` at line ~1032:
```python
src = entry.get('source', '')  # returns None if key exists with null value
# ...
source_parts = [p.strip() for p in src.split(',')]  # AttributeError if src is None!
if any(p in SIGNAL_SOURCE_BLACKLIST for p in source_parts):  # never reached
    continue
if src == 'breakout':  # never reached
    pass
elif len(source_parts) < 2:  # never reached
    continue
```
If `entry['source']` is explicitly `None` (not missing — the key exists with null value), `src = None`, and `src.split(',')` raises `AttributeError: 'NoneType' object has no attribute 'split'`. The crash bypasses ALL subsequent checks — blacklist, breakout exemption, single-source block. The entry passes through `_filter_safe_prev_hotset` entirely.

**Fix Required**:
```python
# Line ~1032 — add explicit None guard BEFORE any .split() call:
src = entry.get('source', '')
if src is None:  # ← ADD THIS: key exists with null value
    continue
```

**Key diagnostic**:
```bash
# Find None sources in hotset.json
cat /var/www/hermes/data/hotset.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
for e in d.get('hotset',[]):
    src = e.get('source')
    if src is None:
        print(f'  None-source: {e[\"token\"]} {e[\"direction\"]}')
"
```

**Key lesson**: `dict.get(key, '')` returns the default only when the key is MISSING. If the key exists with value `None`, it returns `None`, not `''`. Always check `if value is None` explicitly when nullable fields are possible.

---

## Bug 29: ai_decider Direct-to-Hotset.json Bypass — Confluence Gate Circumvented (2026-04-27)

**Symptom**: A single-source signal appears in hotset.json and executes. Compactor log shows "Pre-filter: 0 signals passed" but a trade fires anyway. The signal was never in the compactor's approval flow.

**Root Cause**: `decider_run.py` writes directly to `hotset.json` every 1 minute via `ai_decider`. This bypasses `signal_compactor`'s confluence gate entirely. If `ai_decider` sets `decision='APPROVED'` on a single-source signal and writes it to hotset.json, `decider_run`'s execution loop sees it as approved and fires the trade.

**Key evidence**: At 15:43:00 compactor log shows "Pre-filter: 0 signals passed" but GAS was executed at 15:43:48 with single-source `[gap-300+]`. The compactor log has no GAS entry for that cycle.

**Fix Required** — add hard confluence gate in `decider_run.py` before writing to hotset.json:
```python
# Before writing a signal to hotset.json, verify 2-source confluence:
sources = [s.strip() for s in signal.get('source', '').split(',')]
if len(sources) < 2:
    log(f'  🔒 [ai_decider] {token} {direction}: single-source bypass blocked')
    continue  # Don't write to hotset.json
```
Or better: remove `ai_decider`'s direct hotset.json writes entirely — all signals should go through `signal_compactor`.

**Key diagnostic**:
```bash
# Check ai_decider's hotset writes vs signal_compactor's
grep -n "hotset.json\|write.*hotset\|json.dump" /root/.hermes/scripts/decider_run.py | head -20
# If ai_decider writes hotset.json directly, it bypasses signal_compactor's confluence gate
```

**Key lesson**: When two systems write the same output file, one will eventually bypass the other's safety checks. `signal_compactor` owns hotset.json — `ai_decider` should only read it, never write it.

---

## Bug 31: Single-Source zscore-momentum- Executed Despite Multi-Source Combos in DB (2026-04-28)

**Symptom**: FET SHORT and ONDO SHORT executed at 02:42 with `source=zscore-momentum-` (single source). Multi-source combos `ema9-sma20-,zscore-momentum-` existed in the DB as PENDING (FET hot_cycles=3, ONDO hot_cycles=3) but never transitioned to APPROVED. Guardian log shows no hot-set updates during 02:40–02:43.

**PostgreSQL evidence** (2026-04-28):
```
FET  SHORT  zscore-momentum-     EXECUTED  conf=58  hcc=0  02:42:28
ONDO SHORT  zscore-momentum-     EXECUTED  conf=58  hcc=1  02:42:28
FET  SHORT  ema9-sma20-,zscore-momentum-  PENDING   conf=88  hcc=3  (never approved)
ONDO SHORT  ema9-sma20-,zscore-momentum-  PENDING   conf=88  hcc=3  (never approved)
```

**The anomaly**: `entries_count` field in hot-set showed 2 for the single-source entries — meaning they survived 2 compaction cycles — yet multi-source combos with higher confidence and hot_cycles=3 stayed PENDING. `get_approved_signals()` was returning 0 signals.

**Root cause hypothesis**: The compactor was not running during 02:40–02:43 (guardian log gap). Multi-source PENDING signals with hot_cycles=3 should have been eligible for APPROVED transition when compactor resumed, but the single-source signals somehow bypassed the confluence gate via a direct execution path.

**The unresolved mystery**: The code has NO path where a single-source signal (zscore-momentum-) goes directly from PENDING→EXECUTED without passing through APPROVED. The confluence gate at line 385 blocks single-source signals. Yet the DB shows `decision=EXECUTED, executed=1` for these single-source rows.

**Possible bypass paths** (ordered by likelihood):
1. `mark_signal_executed()` being called directly with a single-source signal_id (Bug 24 pattern)
2. A parallel execution path (counter_flip or OC signal importer) writing EXECUTED directly
3. `entries_count=2` in hot-set means these single-source signals WERE in the hot-set and surviving compaction cycles — but the multi-source combos for the same tokens were NOT, suggesting the compactor was writing single-source entries to hot-set.json while the multi-source PENDING signals were being filtered out by a different bug

**Key diagnostic** — confirm bypass path:
```bash
# Check if zscore-momentum- single-source signals are in SIGNAL_SOURCE_BLACKLIST
grep "zscore-momentum" /root/.hermes/scripts/hermes_constants.py

# Check for any direct mark_signal_executed calls bypassing compactor
grep -rn "mark_signal_executed\|decision.*EXECUTED" /root/.hermes/scripts/*.py | grep -v ".pyc"

# Check counter_flip execution path for zscore-momentum bypass
grep -rn "zscore-momentum\|counter_flip" /root/.hermes/scripts/counter_flip_signal.py | head -20

# Query the exact signals at execution time
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute('''
    SELECT token, direction, source, signal_type, confidence, decision, executed,
           hot_cycle_count, compact_rounds, created_at, updated_at
    FROM signals
    WHERE token IN (\"FET\",\"ONDO\") AND direction=\"SHORT\"
    AND created_at > datetime(\"now\",\"-30 minutes\")
    ORDER BY created_at DESC
''')
print('FET/ONDO SHORT signals near 02:42:')
for r in cur.fetchall():
    print(f'  {r[0]:6} {r[1]:5} src={r[2]:40} conf={r[4]} dec={r[5]} exec={r[6]} hcc={r[7]} cr={r[8]}')
"
```

**Prevention**: Every execution path that sets `decision='EXECUTED'` must verify the signal first passed through the hot-set pipeline (decision=APPROVED, hot_cycle_count>=1). If a signal goes directly PENDING→EXECUTED, that's a bypass.

---

## Bug 30: SQLite PostgreSQL Execution Timestamp Mismatch — Duplicate Execution Events (2026-04-27)

**Symptom**: GAS shows `decision='EXECUTED', executed=1` in SQLite at 15:12:28 AND at 15:43:53. PostgreSQL `trades` table shows trade at 15:43:53. Pipeline log at 15:12:29 shows "SKIP: Max positions reached (3)" — GAS was blocked from executing at 15:12.

**Root Cause — Two hypotheses**:
1. **Duplicate execution events**: GAS was marked EXECUTED in SQLite at 15:12:28 (first attempt), but the actual trade failed (max positions). Then at 15:43:48 GAS was tried again and succeeded. SQLite has both records.
2. **SQLite write ordering bug**: The EXECUTED flag was set before the position limit check, so SQLite shows EXECUTED even though the trade was skipped.

**Evidence**:
- SQLite: `GAS|LONG|gap-300+|EXECUTED|58.0|2026-04-27 15:12:28` — survival_rounds=1, executed=1
- PostgreSQL: `id=7853 entry_price=$1.662950 created_at=15:43:53` — actual trade
- Pipeline log at 15:12:29: `SKIP: Max positions reached (3)` for GAS
- Pipeline log at 15:43:48: `EXEC: GAS LONG @ $1.662950 [gap-300+]` — actual execution

**Fix Required**:
1. Audit `mark_signal_executed()` — ensure EXECUTED is only set AFTER confirmed trade fill, not before position limit check
2. Add a DB constraint: `EXECUTED` signals must have a corresponding PostgreSQL trade record
3. The 15:12 SQLite EXECUTED record should be corrected to PENDING or deleted

**Key diagnostic**:
```bash
# Find all signals where SQLite says EXECUTED but PostgreSQL has no trade
python3 -c "
import sqlite3, psycopg2
# SQLite: signals marked EXECUTED
sc = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
sc.execute('SELECT token, direction, source, updated_at FROM signals WHERE decision=\"EXECUTED\" AND executed=1')
executed = {(r[0],r[1]): r for r in sc.execute('SELECT token, direction, source, updated_at FROM signals WHERE decision=\"EXECUTED\" AND executed=1')}
# PostgreSQL: actual trades
pc = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
pc.execute('SELECT token, direction, open_time FROM trades WHERE open_time::text LIKE \"2026-04-27%\"')
pg_trades = {r[0]: r for r in pc.fetchall()}
# Find mismatches
for (tok,dir), row in executed.items():
    if tok not in pg_trades:
        print(f'  SQLite EXECUTED but no PG trade: {tok} {dir} at {row[3]}')
"
```

---

## Related Bugs (Same Session)
- `ai_decider.py` line ~1143: signals older than 90 minutes excluded even with hot_cycle_count>=1 (fixed 2026-04-14 in `hot-set-survival-bug` skill)
- FileLock PID fd leak in hermes_file_lock.py (fixed 2026-04-14)
- Phantom positions in DB not closing (fixed 2026-04-14)
- Bug 25 (oc-mtf-macd+ single-source bypass): fix applied 2026-04-27 — added oc-mtf-macd+/gap-300+ to SIGNAL_SOURCE_BLACKLIST
