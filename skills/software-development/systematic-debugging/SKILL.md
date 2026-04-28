---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior. 4-phase root cause investigation — NO fixes without understanding the problem first.
version: 1.2.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
metadata:
  hermes:
    tags: [debugging, troubleshooting, problem-solving, root-cause, investigation]
    related_skills: [test-driven-development, writing-plans, subagent-driven-development]
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Someone wants it fixed NOW (systematic is faster than thrashing)

## The Four Phases

You MUST complete each phase before proceeding to the next.

---

## Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

### 1. Read Error Messages Carefully

- Don't skip past errors or warnings
- They often contain the exact solution
- Read stack traces completely
- Note line numbers, file paths, error codes

**Action:** Use `read_file` on the relevant source files. Use `search_files` to find the error string in the codebase.

### 2. Reproduce Consistently

- Can you trigger it reliably?
- What are the exact steps?
- Does it happen every time?
- If not reproducible → gather more data, don't guess

**Action:** Use the `terminal` tool to run the failing test or trigger the bug:

```bash
# Run specific failing test
pytest tests/test_module.py::test_name -v

# Run with verbose output
pytest tests/test_module.py -v --tb=long
```

### 3. Check Recent Changes

- What changed that could cause this?
- Git diff, recent commits
- New dependencies, config changes

**Action:**

```bash
# Recent commits
git log --oneline -10

# Uncommitted changes
git diff

# Changes in specific file
git log -p --follow src/problematic_file.py | head -100
```

## Multi-Component Systems — Data Flow Investigation Pattern

When investigating dashboards, APIs, or services that read from files:

**Step 1: Identify the serving layer**
- nginx config: `grep -r "alias\|proxy_pass" /etc/nginx/` to find which port serves which path
- Check which process owns the listening port: `ss -tlnp | grep <port>`

**Step 2: Find all copies of the data file**
```bash
find / -name "trades.json" 2>/dev/null   # find every copy
stat <each>                              # compare timestamps/sizes
```
The file with recent modification is the live one. Empty/stale files may be unused.

**Step 3: Confirm which file the consumer actually reads**
- If nginx aliases `/data/trades.json` → `/var/www/hermes/data/trades.json`
- But code reads `/root/.hermes/data/trades.json`
- These are DIFFERENT files if `/var/www/hermes` is a real directory (not a symlink)

**Step 4: Verify what writes to the live file**
- Search scripts for the output path: `grep -rn "OUT_TRADES\|OUT_SIGNALS" scripts/`
- Check systemd timers or cron for the update frequency

**Real example from trades.html investigation:**
- `/root/.hermes/data/trades.json` → 26 bytes, empty, nothing uses it
- `/var/www/hermes/data/trades.json` → 95KB, live, nginx serves it
- `/root/.hermes/web/data/trades.json` → 965 bytes, Apr 5 seed file, unused
- nginx root is `/var/www/hermes` (real directory, NOT symlinked to `/root/.hermes`)

### When to Use
- Dashboard shows empty/stale data
- File exists but nothing seems to write to it
- Multiple copies of a config/data file exist

### 5. Trace Data Flow

**WHEN error is deep in the call stack:**

- Where does the bad value originate?
- What called this function with the bad value?
- Keep tracing upstream until you find the source
- Fix at the source, not at the symptom

**Action:** Use `search_files` to trace references:

```python
# Find where the function is called
search_files("function_name(", path="src/", file_glob="*.py")

# Find where the variable is set
search_files("variable_name\\s*=", path="src/", file_glob="*.py")
```

### Phase 1 Completion Checklist

- [ ] Error messages fully read and understood
- [ ] Issue reproduced consistently
- [ ] Recent changes identified and reviewed
- [ ] Evidence gathered (logs, state, data flow)
- [ ] Problem isolated to specific component/code
- [ ] Root cause hypothesis formed

**STOP:** Do not proceed to Phase 2 until you understand WHY it's happening.

---

## Phase 2: Pattern Analysis

**Find the pattern before fixing:**

### 1. Find Working Examples

- Locate similar working code in the same codebase
- What works that's similar to what's broken?

**Action:** Use `search_files` to find comparable patterns:

```python
search_files("similar_pattern", path="src/", file_glob="*.py")
```

### 2. Compare Against References

- If implementing a pattern, read the reference implementation COMPLETELY
- Don't skim — read every line
- Understand the pattern fully before applying

### 3. Identify Differences

- What's different between working and broken?
- List every difference, however small
- Don't assume "that can't matter"

### 4. Understand Dependencies

- What other components does this need?
- What settings, config, environment?
- What assumptions does it make?

---

## Phase 3: Hypothesis and Testing

**Scientific method:**

### 1. Form a Single Hypothesis

- State clearly: "I think X is the root cause because Y"
- Write it down
- Be specific, not vague

### 2. Test Minimally

- Make the SMALLEST possible change to test the hypothesis
- One variable at a time
- Don't fix multiple things at once

### 3. Verify Before Continuing

- Did it work? → Phase 4
- Didn't work? → Form NEW hypothesis
- DON'T add more fixes on top

### 4. When You Don't Know

- Say "I don't understand X"
- Don't pretend to know
- Ask the user for help
- Research more

---

## Phase 4: Implementation

**Fix the root cause, not the symptom:**

### 1. Create Failing Test Case

- Simplest possible reproduction
- Automated test if possible
- MUST have before fixing
- Use the `test-driven-development` skill

### 2. Implement Single Fix

- Address the root cause identified
- ONE change at a time
- No "while I'm here" improvements
- No bundled refactoring

### 3. Verify Fix

```bash
# Run the specific regression test
pytest tests/test_module.py::test_regression -v

# Run full suite — no regressions
pytest tests/ -q
```

### 4. If Fix Doesn't Work — The Rule of Three

- **STOP.**
- Count: How many fixes have you tried?
- If < 3: Return to Phase 1, re-analyze with new information
- **If ≥ 3: STOP and question the architecture (step 5 below)**
- DON'T attempt Fix #4 without architectural discussion

### 5. If 3+ Fixes Failed: Question Architecture

**Pattern indicating an architectural problem:**
- Each fix reveals new shared state/coupling in a different place
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere

**STOP and question fundamentals:**
- Is this pattern fundamentally sound?
- Are we "sticking with it through sheer inertia"?
- Should we refactor the architecture vs. continue fixing symptoms?

**Discuss with the user before attempting more fixes.**

This is NOT a failed hypothesis — this is a wrong architecture.

---

## Red Flags — STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals a new problem in a different place**

**ALL of these mean: STOP. Return to Phase 1.**

**If 3+ fixes failed:** Question the architecture (Phase 4 step 5).

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern, don't fix again. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence, trace data flow | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare, identify differences | Know what's different |
| **3. Hypothesis** | Form theory, test minimally, one variable at a time | Confirmed or new hypothesis |
| **4. Implementation** | Create regression test, fix root cause, verify | Bug resolved, all tests pass |

## Hermes Agent Integration

### Investigation Tools

Use these Hermes tools during Phase 1:

- **`search_files`** — Find error strings, trace function calls, locate patterns
- **`read_file`** — Read source code with line numbers for precise analysis
- **`terminal`** — Run tests, check git history, reproduce bugs
- **`web_search`/`web_extract`** — Research error messages, library docs

### With delegate_task

For complex multi-component debugging, dispatch investigation subagents:

```python
delegate_task(
    goal="Investigate why [specific test/behavior] fails",
    context="""
    Follow systematic-debugging skill:
    1. Read the error message carefully
    2. Reproduce the issue
    3. Trace the data flow to find root cause
    4. Report findings — do NOT fix yet

    Error: [paste full error]
    File: [path to failing code]
    Test command: [exact command]
    """,
    toolsets=['terminal', 'file']
)
```

### With test-driven-development

When fixing bugs:
1. Write a test that reproduces the bug (RED)
2. Debug systematically to find root cause
3. Fix the root cause (GREEN)
4. The test proves the fix and prevents regression

## Hermes Signal Gen: Recurring Failure Patterns

When debugging signal generation (signal_gen.py returning 0 signals):

### 1. Schema-vs-Code Mismatch in momentum_cache

**Symptom:** RSI values always 85.0, velocity=0, z=0 across all tokens.

**Root cause:** Code writes `rsi_14` to `add_signal()` but `momentum_cache` table was missing the column. The `_persist_momentum_state()` function never included `rsi_14` in its INSERT statement. After computing RSI from price history, the result was stored in-memory but never persisted.

**Fix:**
```sql
ALTER TABLE momentum_cache ADD COLUMN rsi_14 REAL;
```
Then update `_persist_momentum_state()` to include `rsi_14` in INSERT/UPDATE and pass it from the call site.

**Prevention:** When a function computes a value and another function reads it, verify the column exists in the DB schema. Schema mismatches are a common silent failure mode.

### 2. avg_z vs z_1h Variable Confusion

**Symptom:** Tokens with suppressed 1H z-scores (good for LONG) are blocked by `avg_z > 0.5` filter.

**Root cause:** `avg_z` is the mean across all 6 timeframes (1m, 5m, 15m, 30m, 1h, 4h). A token with suppressed 1h/4h z but elevated 1m/5m z will have `avg_z > 0.5` and be blocked. Comment said "1H z-score" but code checked the average.

**Fix:** Always use the specific TF variable, not the average across TFs. For 1H entry filter: `zscores.get('1h', (None, None))[0]` not `mom['avg_z']`.

### 3. All Prices Flatline in price_history

**Symptom:** RSI always 85.0 (or very high), all tokens show identical RSI.

**Root cause:** `signals_hermes.db` price_history table has flatline data for many tokens — the same price repeated thousands of times. RSI returns 85.0 when `avg_loss == 0` (no pullbacks at all = price only goes up). All derived indicators (velocity, z-score) become 0.

**Diagnosis:**
```python
# Check for flatlines
rows = get_price_history(token, lookback_minutes=60480)
unique = len(set(r[1] for r in rows))
print(f'{token}: {len(rows)} rows, {unique} unique prices')
```

### 4. MACD Crossover Needs Actual Cross Event

**Symptom:** `_run_mtf_macd_signals()` produces nothing despite valid momentum data.

**Root cause:** MACD crossover requires `MACD_line` to actually cross `signal_line`. If MACD is all positive and stays all positive, no crossover fires. Histogram fallback (`h > 0`) requires ALL 3 TFs (4h, 1h, 15m) to have `hist > 0` for LONG.

**Diagnosis:** Manually compute MACD values to check crossover direction.

## 5. Noisy Signal Sources Blocked in Pipeline but NOT at Trade Entry

**Symptom:** Trades appear in brain PostgreSQL DB with signal sources like `pct-hermes`, `hzscore,pct-hermes`, `vel-hermes` that should be blocklisted. These sources pass through the full pipeline: signal_gen → SQLite signals DB → ai_decider (weight-suppressed but not blocked) → hotset.json → decider_run → brain.py → brain trades DB.

**Root cause:** Two-layer blocking gap:
- `hermes_constants.SIGNAL_SOURCE_BLACKLIST` blocks at ai_decider hot-set compaction level (filters what enters hotset.json)
- `brain.py add_trade()` had a `conf-1s` block but NO signal source blacklist

**Fix:** Add sources to BOTH places:
1. `hermes_constants.SIGNAL_SOURCE_BLACKLIST` — blocks at pipeline/approval level
2. `brain.py add_trade()` — secondary safeguard at trade entry level (last line of defense)

**Example:**
```python
# hermes_constants.py
SIGNAL_SOURCE_BLACKLIST = {
    'rsi-confluence', 'rsi_confluence',
    'pct-hermes', 'hzscore,pct-hermes', 'hzscore,pct-hermes,vel-hermes', 'vel-hermes',
}

# brain.py add_trade()
NOISE_SIGNALS = {
    'pct-hermes', 'hzscore,pct-hermes', 'hzscore,pct-hermes,vel-hermes',
    'vel-hermes', 'rsi-hermes',
}
if signal in NOISE_SIGNALS:
    print(f"✗ REJECTED: {token} {side_type} — noisy signal source '{signal}' blocklisted")
    return None
```

**Diagnosis:** Query brain DB for signals that shouldn't exist:
```sql
SELECT id, token, signal, confidence FROM trades
WHERE signal IN ('pct-hermes','hzscore,pct-hermes','hzscore,pct-hermes,vel-hermes','vel-hermes')
ORDER BY open_time DESC;
```

**Prevention:** When adding a new signal source weight suppression, always ask: should it also be added to SIGNAL_SOURCE_BLACKLIST (hard block) or just given low weight (soft suppression)? Noisy/uncalibrated sources should always be blacklisted at both levels.

### 6. Import-from-Non-Existent-Module Bug

**Symptom:** Runtime `ImportError` when a function runs (not at import time).

**Root cause:** A function `foo()` imports `bar.baz()` at call time (inside the function body) — so it works during initial development when `foo()` is never called, but fails immediately in production when `foo()` executes.

**Example:** `cascade_entry_signal()` called `from candle_db import detect_cascade_direction` — the import existed only inside the function body, `detect_cascade_direction` never existed, and the function was called in the production signal pipeline. No test ever exercised that code path.

**Fix:** Implement the missing function inline, or create the missing module with the correct interface.

**Prevention:** Test every code path, not just the happy path. When adding a function call inside another function (not at module level), mark it with a `TODO_TEST` comment and create a test that exercises that exact path.

### 7. DB Mechanism Never Triggered (Silent No-Op)

**Symptom:** A column with a state machine semantics (e.g., `is_stale`) is always stuck in one value, never transitions.

**Root cause:** The INSERT path always sets the "active" state (e.g., `is_stale=0`). There's no UPDATE path that ever sets the "inactive" state (e.g., `is_stale=1`). The mechanism is a no-op by design oversight.

**Example:** `token_best_config` table has `is_stale INTEGER NOT NULL DEFAULT 0`. The sweep code used `INSERT OR REPLACE` always inserting `is_stale=0`. No code anywhere ever set `is_stale=1`. All 124 tokens permanently stuck at active.

**Diagnosis:**
```sql
SELECT is_stale, COUNT(*) FROM token_best_config GROUP BY is_stale;
-- If all rows show is_stale=0 → mechanism is broken
```

**Fix:** Replace `INSERT OR REPLACE INTO table (..., is_stale) VALUES (..., 0)` with:
```sql
UPDATE table SET is_stale=1 WHERE token=? AND is_stale=0;
INSERT INTO table (token, ..., is_stale) VALUES (?, ..., 0);
```

**Prevention:** When implementing a state machine in a DB table (active/stale/enabled flags), always write the transition logic BEFORE the insert logic. Add a DB-level CHECK constraint if possible.

### 8. Synthetic Data Bug — Aggregation Logic Inverts High/Low

**Symptom:** Backtest shows unusually high win rates (100%) and unrealistic performance metrics. Results don't match live trading.

**Root cause:** A function aggregates raw data into a higher timeframe by taking `high = open` and `low = close` — inverting the actual meaning of high/low. Indicators (MACD, RSI) computed on these synthetic candles are fundamentally wrong.

**Example:** `build_15m_candles_from_1h` bucketed 1H open/close prices into 15m buckets using `max(high, open)` for the high field — but the `high` being used was actually the 1H close price. The "15m MACD" was computed on garbage data.

**Fix:** Fetch real Binance 15m klines via paginated API instead of aggregating 1H candles.

**Diagnosis:** Check data source lineage — synthetic 15m from 1H gives ~2160 candles (90 days × 24h); real Binance 15m gives ~8640 (90 days × 96/day).

**Prevention:** When aggregating data (e.g., 1H→15m, 1m→5m), verify that OHLC semantics are preserved correctly. Prefer fetching real data at the target timeframe rather than aggregating higher-frequency data.

### 9. Exit Loop Silent Drop — Hold Expiry Beyond Data Range

**Symptom:** Backtest trade counts are lower than expected, especially for long hold times. Some trades vanish entirely.

**Root cause:** An exit loop iterates over available candles looking for a hold expiry timestamp. If `hold_end_ts > last_candle_timestamp`, the condition never fires, `exit_price` stays `None`, and the code silently calls `continue` — dropping the trade from results entirely.

**Example:** With 90 days of 15m data, a 480-minute hold can only be tested on the first ~67% of entry points. The last 33% of potential entries silently produce no trade, skewing win rate and signal count.

**Fix:** Always have a terminal exit condition:
```python
# Before (silent drop):
if exit_price is None:
    continue  # Trade lost!

# After (graceful exit):
if exit_price is None:
    exit_price = closes_15m[-1]
    exit_type = 'hold_expired'
```

**Prevention:** In backtest loops, always have a terminal exit condition. If `hold_minutes > 0` always produces a valid exit, even if it's just "expire at last candle". Never silently drop data points.

### 10. Pipeline Writes Column X, Query Filters Column Y — Silent Empty Results

**Symptom:** A filtered dataset (e.g., hot-set, warm-up candidates) returns zero rows despite the data clearly existing. Downstream effects are asymmetric — SHORTs appear but LONGs don't, or vice versa.

**Root cause:** The pipeline increments one column (e.g., `hot_cycle_count`) while the query filters on a different column (e.g., `review_count`). These are two separate columns with different semantics:
- `hot_cycle_count` — incremented by the pipeline in `signal_gen.py` when APPROVED signals don't execute within the cycle window
- `review_count` — incremented by `ai_decider.py` only when signals are SKIPPED or WAIT

Signals can have `hot_cycle_count=1` (pipeline-approved but unexecuted) while `review_count=0` (never SKIPPED/WAIT). The query returns nothing because `review_count >= 1` never matches.

**Real example:** `_load_hot_rounds()` in `ai_decider.py` queried `review_count >= 1` at line 444. But the pipeline increments `hot_cycle_count` when signals are approved but not executed. ADA/DOGE/ONDO (LONG candidates) had `hot_cycle_count=1` but `review_count=0` → invisible to the query → `_hot_rounds` empty → flip-kill protection never ran → LLM had no LONG survivors → SHORTs dominated the hot-set.

**Fix:** Use the correct column in the query — the one that the pipeline actually increments:
```sql
-- Wrong (what was used):
WHERE hot_cycle_count >= 1  -- pipeline increments this
-- Correct (what should have been used):
WHERE hot_cycle_count >= 1  -- pipeline increments this
```

And verify with a diagnostic query that shows BOTH columns:
```sql
SELECT token, direction, hot_cycle_count, review_count, decision
FROM signals
WHERE hot_cycle_count >= 1
ORDER BY hot_cycle_count DESC;
```

**Diagnosis:**
```python
# Check both counters side-by-side
rows = query("""
    SELECT token, direction, hot_cycle_count, review_count, decision
    FROM signals
    WHERE hot_cycle_count >= 1
    GROUP BY token, direction
""")
for r in rows:
    if r['review_count'] == 0:
        print(f"MISMATCH: {r['token']} hot_cycle={r['hot_cycle_count']} review={r['review_count']}")
```

**Prevention:** When implementing a state-tracking column, document which component increments it. When writing a query that filters on a counter, verify the column name against the actual increment site. Use a comment in the query that references the source file and line number of the increment.

### 11. HL API `{'status': 'err'}` Without Top-Level Guard — Silent Failure or Crash

**Symptom:** SHORT trades not syncing to Hyperliquid. Trades stay paper-only. No error surfaced to logs, but HL shows no positions.

**Root cause:** Hyperliquid API returns error responses as `{'status': 'err', 'response': 'error_message_string'}` — NOT as HTTP error codes. The code called `.get('response').get('data').get('statuses')` on this structure without first checking if `status == 'err'`. This caused:
- `'str' object has no attribute 'get'` when HL returned a raw string error
- `{'success': True, 'result': {'status': 'err', ...}}` when status was 'err' but code only checked the nested `statuses` array

**Real example:** `mirror_open` for SHORT trades silently failed with rate-limit error `{'status': 'err', 'response': 'Too many cumulative requests sent (77037 > 73552)'}`. All 9 HL exchange functions in `hyperliquid_exchange.py` had this pattern.

**Fix:** Always check for error status BEFORE calling nested `.get()` chains:
```python
# Before (crashes on error):
result = req.json()
statuses = result.get('response', {}).get('data', {}).get('statuses', [])

# After (safe):
result = req.json()
if not isinstance(result, dict):
    return {"success": False, "error": f"Non-dict response: {result}"}
if result.get("status") == "err":
    err_msg = result.get("response", "")
    return {"success": False, "error": err_msg}
```

**Prevention:** When wrapping external API responses, validate the top-level structure before accessing nested keys. Use `isinstance(result, dict)` first. If the API uses a `status: err` pattern, handle it at the outermost level before any chained `.get()` calls.

## 12. Non-Blocking Subprocess for Pipeline Steps Causes Double-Fire Race

**Symptom:** A file (e.g., `hotset.json`) becomes corrupt or stale, and log analysis shows two instances of the same script running simultaneously.

**Root cause:** `run_pipeline.py` ran some step scripts via `subprocess.Popen` (non-blocking) instead of `subprocess.run` (blocking). The pipeline's systemd timer fires every 60s, but a 10-minute step (e.g., `ai_decider`) takes longer than one timer interval. By the time the first instance finishes, the second has already started — both race to write the same output file. The FileLock only serialized them after the damage was done.

**Real example:** `STEPS_EVERY_10M = ['ai_decider', 'strategy_optimizer', ...]` were called in a non-blocking loop. ai_decider takes 10+ minutes but the timer fires every 60s. Two instances raced, corrupting `hotset.json`.

**Fix:** Two-part:
1. Change to blocking `subprocess.run` so pipeline waits for each step
2. Add a process-level guard using `psutil` to skip if the step is already running:
```python
import psutil
for step in STEPS_EVERY_10M:
    if step == 'ai_decider':
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if any('ai_decider' in str(c) for c in cmdline):
                    log(f'Skipping ai_decider (PID {proc.info["pid"]} already running)')
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    run(step)  # blocking
```

**Diagnosis:**
```bash
# Find duplicate processes
ps aux | grep ai_decider | grep -v grep
# Check which step is taking too long
grep "Running ai_decider" /root/.hermes/logs/pipeline.log
# Look for overlapping timestamps
```

**Prevention:** When running step scripts from a pipeline, always use blocking subprocess calls. Add a process-level guard for long-running steps that might outlast the pipeline timer interval. Document the expected runtime of each step.

## 13. FileLock Race Window — Delete on `__exit__` Creates Gap

**Symptom:** A lock file (e.g., `ai_decider.lock`) exists but no process holds it. Subsequent runs see the lock as available but still get blocked by something else. The lock holder appears to run forever.

**Root cause:** A custom FileLock class deleted the lock file only in `__exit__`. Between `fcntl.flock(UNLOCK)` and the next process's `open()`, a third process could:
1. See no lock file (because first process deleted it in `__exit__`)
2. Open and acquire the lock
3. Begin its own work
The original process then also proceeds, both now holding the lock simultaneously.

**Fix:** Delete the lock file **before** acquiring in `__enter__`:
```python
def __enter__(self):
    # Delete any stale lock BEFORE acquiring — including orphans from killed processes
    try:
        if os.path.exists(self.lockfile):
            os.unlink(self.lockfile)
    except Exception:
        pass
    self.fd = os.open(self.lockfile, os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(self.fd, fcntl.LOCK_EX)  # blocking
    return self
```

**Diagnosis:**
```bash
# Check lock file age
stat /root/.hermes/locks/hotset_json.lock
# Check which process holds it
cat /root/.hermes/locks/hotset_json.lock  # PID
ps aux | grep <PID>
# Check for stale locks
ls -la /root/.hermes/locks/
```

**Prevention:** When implementing file-based locks, always delete stale locks proactively in `__enter__`, not in `__exit__`. The `__exit__` deletion creates a race window. Also clean locks from killed/crashed processes on every acquire.

## 14. Variable Scope Bug — LLM Branch Variable Referenced in Fallback Path

**Symptom:** `NameError: name 'top20' is not defined` crashes `_do_compaction_llm()` in `ai_decider.py`. The hot-set file stops being written. Dashboard shows stale or empty hot_set.

**Root cause:** A function has an LLM branch that defines a variable (e.g., `parsed` from LLM output), and a fallback branch that computes the same variable with different logic. After the dedup step, code references `top20` (the LLM branch's variable name) in loops that should iterate over `parsed` (the universal variable that exists in both branches). The fallback path crashes with `NameError`. Similarly, `top20_keys` (built from `top20`) was referenced but never defined.

**Real example:** `ai_decider.py` `_do_compaction_llm()`:
- LLM branch: `parsed = [{'token': ...}, ...]` (from LLM response)
- Fallback branch: `parsed = [{'token': ...}, ...]` (from Python scoring)
- After dedup: lines 1655, 1660 iterated `top20` (LLM-only name) instead of `parsed`
- Line 1712 referenced `top20_keys` which was never assigned

**Fix:** Use the universal variable name (`parsed`) in shared code after the branch split:
```python
# Before (crashes in fallback):
for _tok_entry in top20:
    hotset_regime_cache[_tk] = get_regime(_tk)
hotset_entries = []
for s in top20:

# After (works in both branches):
for _tok_entry in parsed:
    hotset_regime_cache[_tk] = get_regime(_tk)
hotset_entries = []
for s in parsed:

# Also define derived variables AFTER the branch merge, not inside one branch:
top20_keys = {f"{s['token']}:{s['direction']}" for s in parsed}
```

**Prevention:** When a function has multiple branches that compute the same variable (LLM vs fallback), collect all post-branch derived computations AFTER the `if/else` block ends. Never reference a variable name that only exists in one branch. Use universal names in shared loops.

## 15. Two Writers to Same File — Stale Wins Over Fresh

**Symptom:** A file (e.g., `hotset.json`) shows old data despite the pipeline running. Dashboard shows fewer entries than expected. The "authoritative" file is being overwritten by a secondary writer with different logic or limits.

**Root cause:** Two different scripts write the same output file. The one that runs last may have different filtering, different limit values, or be reading from a stale intermediate source. The file on disk reflects the last writer, not the correct data.

**Real example:** `signals.json` `hot_set[]` was being built by `hermes-trades-api.py`'s `_build_hotset_from_db()` fallback (4 stale entries from DB) while `hotset.json` had 13 fresh entries from `ai_decider.py`. The API returned the stale DB data because `hotset.json` was 77 minutes old (> 20-min stale threshold), triggering the fallback. The fallback had fewer entries because the DB query used different filters than `ai_decider`.

**Fix:** Establish one authoritative writer. The `_get_hotset_from_file()` function correctly reads from `hotset.json` (written by `ai_decider.py`). The staleness check at 20 minutes was correct — but the 10-min step (`ai_decider`) hadn't run in 77 minutes because the pipeline's 10-min timing was broken. Fixed the `NameError` that was preventing `ai_decider` from writing.

**Diagnosis:**
```python
# Check file age
import time, json
with open('/var/www/hermes/data/hotset.json') as f:
    data = json.load(f)
age_s = time.time() - data.get('timestamp', 0)
print(f'hotset.json age: {age_s:.0f}s ({age_s/60:.1f} min), entries: {len(data.get("hotset", []))}')

# Check what the API sees
# Run: python3 hermes-trades-api.py and look for "[hotset] stale" or "[hotset] fallback" in output
```

**Prevention:** When a file has one authoritative writer, ensure the writer runs reliably on its schedule. Add a heartbeat/timestamp check in the reader that alerts when the authoritative source is stale. Document which script is the sole writer for each output file.

## 16. Guardian Has Its Own Trade Creation Path That Bypasses brain.py Safeguards

**Symptom:** Phantom trades appear in DB with `paper=False` but no HL position. Guardian closes them as `HL_CLOSED` even though brain.py's `is_live_trading_enabled()` check should have prevented them.

**Root cause:** The guardian (`hl-sync-guardian.py`) has a parallel trade creation path — `mirror_open_retry()` in Step 7b — that creates paper trades independently of brain.py. The `is_live_trading_enabled()` check and the phantom-delete logic in brain.py do NOT reach this code path. If `mirror_open()` fails in the guardian's context, a phantom `paper=False` record is left behind.

**Fix:** In the guardian's Step 7b, add the same phantom-delete logic:
```python
# Inside mirror_open_retry loop:
if not is_live_trading_enabled():
    # Delete phantom — don't leave paper=False without HL position
    conn_del = get_db_connection()
    cur_del = conn_del.cursor()
    cur_del.execute("DELETE FROM trades WHERE id=%s AND paper=false", (trade_id,))
    conn_del.commit()
    log(f'[LIVE-MISS] Deleted phantom paper trade #{trade_id} — live trading is OFF')
    continue

# After mirror_open failure:
if result and not result.get('success'):
    conn_del = get_db_connection()
    cur_del = conn_del.cursor()
    cur_del.execute("DELETE FROM trades WHERE id=%s AND paper=false", (trade_id,))
    conn_del.commit()
    log(f'[LIVE-MISS] Deleted phantom trade #{trade_id} — mirror_open failed')
```

**Prevention:** When adding phantom-close protections to `brain.py`, always check if the guardian has a parallel trade creation path that bypasses those same protections. Search for `mirror_open` in all scripts. The guardian is the most likely bypass vector.

## 17. Signal Marked Executed Before Trade Persists — Phantom Signal Bug

**Symptom:** A signal is marked `executed=1` in the signals DB but no corresponding trade exists in the PostgreSQL trades table. One or more slots in the 10-position portfolio sit permanently empty. Guardian cannot rescue the signal because there's no paper record to reconcile. The trade never reached HL.

**Root cause:** The execution order in `decider_run.py` is wrong:

```
decider_run._process_approved_signals():
  1. mark_signal_executed(token, direction, sig_id)   ← executed=1 set HERE
  2. execute_trade() → brain.py trade add
  3. brain.py add_trade():
       - Inserts trade into trades table
       - Tries mirror_open() to HL
       - IF mirror_open FAILS → DELETES trade row from trades table
  4. Signal already consumed — permanently lost
```

`mark_signal_executed()` is called at line 1606 (before brain.py runs), while `brain.py` deletes the trade at lines 455-473 if `mirror_open` fails or if `is_live_trading_enabled()` is False. The signal is consumed but the trade never existed on HL.

**Real example:** DOGE LONG with source `hzscore,pct-hermes+` — approved, marked executed, brain.py deleted the trade because `mirror_open` failed (rate limit, balance, or live_trading=OFF). DOGE is gone from pipeline but never traded.

**Fix — Post-trade verification + signal restoration:**

```python
# In decider_run.py: execute_trade() call site (~line 1627)
success, msg = execute_trade(...)
if success:
    # Parse trade_id from brain.py output (line contains "TRADE_ID: <n>")
    import re
    m = re.search(r'TRADE_ID:\s*(\d+)', msg)
    if m:
        trade_id = int(m.group(1))
        # Verify trade still exists in DB (not phantom-deleted by brain.py)
        exists = verify_trade_in_db(token, direction.upper(), trade_id)
        if not exists:
            # Trade was phantom-deleted (mirror_open failed) — restore signal
            rollback_signal_executed(token, direction.upper(), sig_id)
            log(f'  🔁 PHANTOM-DELETED: {token} {direction} — signal kept alive for retry')
            _record_hotset_failure(token, direction.upper(), failures)
            continue
    mark_signal_executed(token, direction.upper(), sig_id)
else:
    mark_signal_failed(token, direction.upper(), sig_id)
```

Add to `signal_schema.py`:
```python
def rollback_signal_executed(token, direction, signal_id=None):
    """Restore executed=0 on a signal so it can be retried next cycle."""
    conn = sqlite3.connect(SIGNALS_DB)
    cur = conn.cursor()
    if signal_id:
        cur.execute("UPDATE signals SET executed=0 WHERE id=? AND executed=1",
                    (signal_id,))
    else:
        cur.execute("""UPDATE signals SET executed=0
                       WHERE token=? AND direction=? AND executed=1
                       ORDER BY updated_at DESC LIMIT 1""",
                   (token.upper(), direction.upper()))
    conn.commit()
    rows = cur.rowcount
    cur.close(); conn.close()
    return rows
```

**Prevention:** Always verify external state (HL position, DB record) before permanently marking a signal consumed. The verification must happen AFTER the downstream call, not before. Apply this pattern to any place that calls an external system (HL API, brain.py) after updating internal state.

**Diagnosis:**
```sql
-- Find phantom signals: executed=1 but no open trade in DB
SELECT s.token, s.direction, s.signal_id, s.executed, s.decision
FROM signals s
LEFT JOIN brain.trades t ON t.token = s.token AND t.direction = s.direction AND t.status = 'open'
WHERE s.executed = 1 AND s.decision = 'APPROVED'
  AND t.id IS NULL
ORDER BY s.updated_at DESC;
```

---

## 19. Singleton Without Initialization Call — Empty In-Memory State

**Symptom:** A subsystem shows all tokens with default/fallback values (e.g., `wave_phase='neutral'`, `speed_percentile=50`, `momentum_score=50`) despite the data source clearly computing real values for hundreds of tokens. The hot-set JSON shows `wave_phase='neutral'` for every token — not because the market is neutral, but because no real data was ever fetched.

**Root cause:** Two scripts share an in-memory data source via separate singleton instances. Script A (the producer) calls `.update()` to populate in-memory state. Script B (a consumer) imports the same class, creates its own instance, but calls a read method without first calling the update/init method. The read returns the empty default state.

**Real example:** `ai_decider.py` line 1741 called `speed_tracker_ai().get_all_speeds()` without ever calling `speed_tracker_ai().update()`. Meanwhile `signal_gen.py` (which runs earlier in the pipeline) calls `speed_tracker.update()` correctly at line 2109. `ai_decider.py` has its own `_speed_tracker_ai` singleton (`_get_speed_tracker()` at line 37-41) that is independent of `signal_gen.py`'s `speed_tracker` — different Python objects with different `_speeds` dicts.

```python
# ai_decider.py — WRONG (the bug):
_speed_cache = speed_tracker_ai().get_all_speeds()   # _speeds = {} — never populated!

# signal_gen.py — RIGHT (the producer):
speed_tracker.update()           # ← must be called FIRST
speeds = speed_tracker.get_all_speeds()  # ← then this returns real data
```

**Key insight:** The singleton pattern (`_tracker = None; def _get_tracker(): global _tracker; if _tracker is None: _tracker = Class(); return _tracker`) means each **process/pipeline-run** gets its own independent instance. Within a single pipeline run, multiple scripts each get their own empty instance unless they explicitly call `.update()` first.

**Fix:**
```python
# CORRECT — always call .update() before .get_all_speeds() / .get_token_speed()
_tracker = speed_tracker_ai()
_tracker.update()   # ← FETCH and POPULATE in-memory state
_speed_cache = _tracker.get_all_speeds()
```

**Diagnosis:**
```python
# Simulate what the consumer script does — creates instance, reads without update
from speed_tracker import SpeedTracker
st = SpeedTracker()
speeds = st.get_all_speeds()
print(f'Tokens with data: {len(speeds)}')   # → 0 if bug exists

# FIXED — create instance, update, then read
st2 = SpeedTracker()
st2.update()
speeds2 = st2.get_all_speeds()
print(f'Tokens with data: {len(speeds2)}')  # → 539 if working
```

**Prevention:** When a class has an `.update()` / `.fetch()` / `.refresh()` method that populates in-memory state, and a separate `.get_*()` method that reads that state — always call the update method BEFORE the read method. Document this dependency explicitly in the class docstring:

```python
class SpeedTracker:
    def update(self) -> dict:
        """FETCH prices + COMPUTE all speed metrics. MUST be called before get_all_speeds()."""
        
    def get_all_speeds(self) -> dict:
        """RETURN cached speeds. Assumes .update() was called first — returns {} if not."""
```

When importing a singleton accessor from another script, remember it has its OWN instance — you cannot assume the producer's `.update()` call populated YOUR instance. Always update before reading.

---

## 18. Import Inside Docstring — Statement Never Executes

**Symptom:** `NameError: name 'CONSTANT' is not defined` on a constant that clearly exists in `paths.py` (verified via direct import). The error happens at module load, before any function is called. `from paths import *` appears to work when tested manually but fails when running the script directly.

**Root cause:** Python triple-quoted docstrings consume everything until the closing `"""`. If the docstring straddles what looks like an import line, that import becomes literal text inside the string — never executed.

**Real example:**
```python
#!/usr/bin/env python3
"""
Profit Monster — closes medium-profit positions (2-5%) at random intervals.
Loves profit. A/B testable fire intervals (10-15min vs 20-30min).
Never touches losing positions.
from paths import *
"""
import sys, os, json, time, random, argparse
```

`from paths import *` is **inside the docstring** (lines 3-6), never executed. `PROFIT_MONSTER_CONFIG` is undefined at line 17.

**Diagnosis — the RIGHT way:**
1. Use `read_file` with `offset=1 limit=25` on the failing script
2. Check if the import line is inside a `\"\"\"...\"\"\"` block
3. Use `ast.parse()` to confirm:
```python
import ast
with open('script.py') as f:
    tree = ast.parse(f.read())
for node in ast.walk(tree):
    if isinstance(node, ast.ImportFrom) and node.module == 'paths':
        print('VALID import found at line', node.lineno)
# If no ImportFrom for 'paths' → it's inside a docstring
```

**The WRONG approaches (don't do these):**
- `grep "from paths import \*"` — returns ZERO results even when the bug exists, because grep searches file content literally. The import line IS in the file, inside the docstring string — grep won't tell you it's buried in a string.
- wandb `paths.py` shadowing (not the issue — our `paths.py` resolves correctly)
- `__pycache__` corruption (not the issue)
- `sys.path` resolution order (not the issue — Python resolves it correctly when run interactively)
- Manually tracing import machinery (overkill — just read the top of the file)

**The right debugging approach:**
1. Read the file carefully from the top with `read_file(limit=25)`
2. Notice `\"\"\"` closes AFTER the import line
3. One-line fix: move `\"\"\"` to before `from paths import *`

**When multiple files have the same bug**, write an AST-based scanner to identify all affected files, then fix them in parallel using subagents:

```python
# Scanner to find all files with this bug
import ast, sys

for path in sys.argv[1:]:
    with open(path) as f:
        src = f.read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        print(f"SYNTAX ERROR: {path}")
        continue
    doc_node = tree.body[0] if tree.body else None
    import_node = None
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and getattr(n.module, 'id', None) == 'paths':
            import_node = n
            break
    if (doc_node and isinstance(doc_node.value, (ast.Str, ast.Constant)) and
        import_node and
        import_node.lineno >= doc_node.lineno and
        import_node.lineno <= (doc_node.end_lineno or doc_node.lineno) + 1):
        print(f"Bug: {path} (import at line {import_node.lineno}, docstring ends ~line {doc_node.end_lineno})")
    else:
        print(f"OK: {path}")
```

**Fix pattern** — always move the import to its own line AFTER the docstring:
```python
# WRONG (import inside docstring):
"""
Description.
from paths import *
"""
import sys, os

# RIGHT:
"""
Description.
"""
from paths import *
import sys, os
```

**For 20+ files with the same bug:**
1. Write AST scanner to identify all affected files (don't trust grep or manual reading for 80+ files)
2. Use `delegate_task` subagents to fix files in parallel — one subagent per group of ~10 files
3. Verify each fix with `python3 -m py_compile script.py` AND a real import test
4. Run the full pipeline end-to-end as final verification

**Fix:**
```python
"""
Profit Monster — closes medium-profit positions (2-5%) at random intervals.
Loves profit. A/B testable fire intervals (10-15min vs 20-30min).
Never touches losing positions.
"""
from paths import *
import sys, os, json, time, random, argparse
```

**Prevention:** When writing module-level docstrings, never put blank lines or code after the opening `\"\"\"` on the same line. Always close `\"\"\"` on its own line before any real code. Alternatively, put the import BEFORE the docstring. A safe pattern:
```python
#!/usr/bin/env python3
\"\"\"Short one-line description.\"\"\"
from paths import *
# rest of imports
\"\"\"Extended description of what this script does.\"\"\"
import sys, ...
```

## 20. Reversed Comparison Operators in Trailing-Lock Logic — ATR "Frozen"

**Symptom:** ATR SL/TP values appear "frozen" at stale entry-based static values (e.g., 2%/5% fixed stops) despite price moving significantly. LTC is +2% but SL still shows the original 2% below entry. The trailing-lock intended to prevent ATR from *widening* stops is instead preventing ATR from *tightening* them.

**Root cause:** The comparison operators in the trailing-lock logic are reversed — `>=` used where `>` is needed (or `<=` where `<` is needed). This inverts the lock's behavior: instead of blocking true loosening, it blocks tightening.

**Real example from LTC case (`_collect_atr_updates()` in position_manager.py):**
- LTC entry=54.915, current=56.00, ATR=0.143, pnl=+2%
- ATR-computed SL=56.03 (tightened from entry-based 53.82)
- BUT `sl_at_ref >= current_sl` → `56.03 >= 53.82` → TRUE → blocked update
- AND `tp_at_ref <= current_tp` → `56.51 <= 57.68` → TRUE → blocked update

The comparison operators were the wrong direction:
```python
# WRONG — blocks tightening instead of loosening:
if sl_at_ref >= current_sl:   # 56.03 >= 53.82 = TRUE → keeps loose stop!
if tp_at_ref <= current_tp:   # 56.51 <= 57.68 = TRUE → keeps loose TP!

# RIGHT — only blocks true loosening:
if sl_at_ref > current_sl:    # 56.03 > 53.82 = TRUE → ATR tightens, accept it
if tp_at_ref < current_tp:    # 56.51 < 57.68 = TRUE → ATR tightens, accept it
```

**The logic diagram:**
```
LONG SL:  SL should only move UP (numerically higher = tighter as price rises)
          - sl_at_ref > current_sl → ATR would RAISE SL → TIGHTEN → accept
          - sl_at_ref <= current_sl → ATR would LOWER SL → LOOSEN → block
          BUG: >= instead of > blocks the TIGHTEN case

LONG TP:  TP should only move UP (numerically higher = more profit locked)
          - tp_at_ref > current_tp → ATR would RAISE TP → TIGHTEN → accept
          - tp_at_ref <= current_tp → ATR would LOWER TP → LOOSEN → block
          BUG: <= instead of < blocks the TIGHTEN case

SHORT SL: SL should only move DOWN (numerically lower = tighter as price falls)
          - sl_at_ref < current_sl → ATR would LOWER SL → TIGHTEN → accept
          - sl_at_ref >= current_sl → ATR would RAISE SL → LOOSEN → block
          ✓ (correct — this is why SHORT side didn't have the bug)

SHORT TP: TP should only move DOWN (numerically lower = more profit locked)
          - tp_at_ref < current_tp → ATR would LOWER TP → TIGHTEN → accept
          - tp_at_ref >= current_tp → ATR would RAISE TP → LOOSEN → block
          ✓ (correct)
```

**Debug steps:**
1. Read `_collect_atr_updates()` — the trailing-lock logic around lines 1528-1586
2. Verify direction with manual math:
   ```python
   # For the affected token:
   ref_price = current_price  # or entry if current unavailable
   atr = get_atr(token)
   entry = get_entry_price(token)
   atr_pct = atr / entry
   k = 0.75  # or whatever your k is
   sl_pct = k * atr_pct
   tp_pct = 2.5 * _dr_atr(token, atr_pct) * atr_pct

   sl_at_ref = round(ref_price * (1 - sl_pct), 8)   # LONG
   tp_at_ref = round(ref_price * (1 + tp_pct), 8)    # LONG

   current_sl = float(db_trade['stop_loss'])
   current_tp = float(db_trade['target'])

   print(f"ATR wants: SL={sl_at_ref:.6f} TP={tp_at_ref:.6f}")
   print(f"Current:   SL={current_sl:.6f} TP={current_tp:.6f}")
   print(f"LONG SL: sl_at_ref > current_sl = {sl_at_ref} > {current_sl} = {sl_at_ref > current_sl}")
   print(f"LONG TP: tp_at_ref < current_tp = {tp_at_ref} < {current_tp} = {tp_at_ref < current_tp}")
   ```
3. Check if ATR is computing correctly: look for `[ATR] LTC:` in pipeline logs
4. Check DB: `SELECT stop_loss, target FROM trades WHERE token='LTC' AND status='open'`
5. Check `trades.json`: the displayed SL/TP come from the DB via pipeline

**Fix:** Swap comparison operators and swap if/else branches to match:
```python
# LONG SL fix:
if sl_at_ref > current_sl:
    new_sl = sl_at_ref     # ATR tightens — accept it
    needs_sl = True
else:
    new_sl = current_sl    # ATR loosens or same — keep current
    needs_sl = False

# LONG TP fix:
if tp_at_ref < current_tp:
    new_tp = current_tp     # ATR would loosen — keep
    needs_tp = False
else:
    new_tp = tp_at_ref      # ATR tightens (higher) — update
    needs_tp = True
```

**Prevention:** When implementing trailing-lock comparison logic, verify with a concrete example:
- Price=56, ATR=0.14, old SL=53.82, ATR-computed SL=56.03
- Question: "Does the comparison block the NEW (tightened) SL or the OLD (loose) SL?"
- If it blocks the new: comparison is correct
- If it blocks the new when you wanted to accept it: comparison is reversed

## 21. FastMCP/Pydantic `Field(default=X)` — Descriptor Object Passed Instead of Default

**Symptom:** An MCP tool with optional parameters defined as `param: Type = Field(default=default_value)` fails with `TypeError: expected <type> got FieldInfo` or SQLite binding errors when the caller omits the optional parameter.

**Root cause:** FastMCP/Pydantic passes the Pydantic `FieldInfo` descriptor object itself as the argument value when the caller doesn't explicitly provide the optional parameter — not the actual default value. This happens at the MCP transport layer, before the function body executes.

**Affected patterns:**
```python
# BROKEN — min_weight receives FieldInfo object, not 0.5
@mcp.tool()
async def hebbian_recall(
    concept: str,
    k: int = Field(default=5),
    min_weight: float = Field(default=0.5, ge=0.0),  # FieldInfo passed if omitted!
):

# ALSO BROKEN — label_type_a/b receive FieldInfo, not None
@mcp.tool()
async def hebbian_learn(
    concept_a: str,
    concept_b: str,
    label_type_a: Optional[str] = Field(default=None),  # FieldInfo passed if omitted!
):
```

**Fix pattern:** Don't use `Field(default=...)` for optional parameters that will be used directly in the function body. Instead use plain Python defaults and handle `None` inside the function:

```python
# CORRECT
@mcp.tool()
async def hebbian_recall(
    concept: str,
    k: int = Field(default=5),
    min_weight: float = None,  # No Field() wrapper
) -> str:
    try:
        engine = HebbianEngine()
        _min_weight = min_weight if min_weight is not None else 0.5
        results = engine.recall(concept, k=k, min_weight=_min_weight)
        ...

# CORRECT for Optional
@mcp.tool()
async def hebbian_learn(
    concept_a: str,
    concept_b: str,
    label_type_a: Optional[str] = None,  # No Field() wrapper
    label_type_b: Optional[str] = None,
) -> str:
    try:
        engine = HebbianEngine()
        weight = engine.learn_pair(concept_a, concept_b, label_type_a, label_type_b)
        ...
```

**Diagnosis:**
```python
# Test without the MCP transport — call the function directly with defaults
import asyncio
from server import hebbian_recall

async def test():
    # This mimics what FastMCP does when caller omits min_weight
    r = await hebbian_recall(concept="TNSR", k=3)  # omit min_weight
    print(r)

asyncio.run(test())
# If it fails with FieldInfo/descriptor error → this is the bug
```

**Prevention:** When defining MCP tools with optional parameters:
1. Use plain Python defaults (`param: Type = None`) for optional params used in function body
2. Never use `Field(default=...)` on parameters that will be passed directly to downstream functions (SQL, external libraries)
3. Test each tool by calling it directly with optional parameters OMITTED (not just with defaults provided)
4. The `Field()` wrapper is fine for description/validation metadata ONLY if the param is NOT used directly

---

## 22. MCP Server `sys.path` + Import Style Mismatch

**Symptom:** `ModuleNotFoundError: No module named 'scripts'` in an MCP server tool function, even though `sys.path.insert(0, '/root/.hermes/scripts')` is present at the top of the file.

**Root cause:** The `sys.path.insert` points to `/root/.hermes/scripts` (making `scripts/` a package prefix), but the import statement uses `from scripts.hebbian_engine import HebbianEngine`. With the path set to `/root/.hermes/scripts`, Python tries to find `/root/.hermes/scripts/scripts/hebbian_engine.py` — which doesn't exist.

**Example of broken code:**
```python
import sys
sys.path.insert(0, '/root/.hermes/scripts')  # path points to scripts dir
from scripts.hebbian_engine import HebbianEngine  # WRONG: scripts.scripts.hebbian_engine
```

**Fix — match the path to the import style:**
```python
# Option A: path = parent dir, import = package.module
sys.path.insert(0, '/root/.hermes')
from scripts.hebbian_engine import HebbianEngine  # works: /root/.hermes/scripts/hebbian_engine.py

# Option B: path = scripts dir, import = module only
sys.path.insert(0, '/root/.hermes/scripts')
from hebbian_engine import HebbianEngine  # works: /root/.hermes/scripts/hebbian_engine.py
```

**The `run_mcp_server.py` wrapper gotcha:**
The systemd service wrapper does `from paths import *` which only works because `server.py` already loaded `paths.py` via its own `sys.path.insert`. The wrapper's import is a lucky no-op that breaks if the import order changes. Not a bug that crashes startup (FastMCP catches it), but fragile.

**Prevention:** When adding an MCP tool that imports from a sibling script:
1. Test the import in isolation: `python3 -c "import sys; sys.path.insert(0, '/path/to/dir'); from module import func"`
2. Then test the tool via direct function call (bypass MCP transport)
3. The wrapper's `from paths import *` is a red flag — document that it depends on import order

---

## 23. HL Fill Data — `dir` Field Indicates Open/Close, Not `side`

**Symptom:** `get_realized_pnl()` returns `realized_pnl=0.0` for all LONG closes. PnL recorded as $0.00 in DB despite profitable exits. `mirror_get_exit_fill()` finds no fills.

**Root cause:** The Hyperliquid fill API returns `side` + `dir` together — both are needed to identify fill type:
```
LONG open:  side="B" dir="Open Long"
LONG close: side="A" dir="Close Long"
SHORT open: side="A" dir="Open Short"
SHORT close: side="B" dir="Close Short"
```
Code that used `side=="B"` to find close fills missed ALL LONG closes (side="A"). This wrong assumption was copied to 3 functions independently.

**Real example:** `get_realized_pnl()`, `mirror_get_exit_fill()`, and `mirror_get_entry_fill()` all used `f["side"] == "B"` or `f["side"] in ("A","B")` to classify fills. For LONG positions, the close fill has `side="A"` — silently filtered out → `realized_pnl=0.0`.

**Fix:** Use the `dir` field (contains "Open" or "Close"):
```python
def is_open_fill(f):
    return "Open" in f.get("dir", "")
def is_close_fill(f):
    return "Close" in f.get("dir", "")
```

**Diagnosis — always check actual API response first:**
```python
# Never assume — fetch real data and inspect
fills = get_trade_history(start_ms, end_ms)
for f in fills:
    if f["coin"].upper() == token.upper():
        print(f'  side={f["side"]} dir={f["dir"]} closed_pnl={f["closed_pnl"]}')
```
This would immediately show that LONG closes have `side="A"`, not `"B"`.

**Prevention:** When integrating with any external API, especially trading APIs with complex data models:
1. Fetch real response data first — print actual field values
2. Never assume `side` or similar fields mean what the name implies
3. Look for compound keys (`side`+`dir`) that require both fields
4. When the same wrong pattern appears in multiple functions, fix the shared assumption at the source — three functions with the same bug means the underlying API model understanding was wrong in the same way

---

## 22. Two Separate Cooldown Stores — Writer Only Writes One, Reader Never Checks It

**Symptom:** A cooldown is visibly present in the PostgreSQL database (via direct query), but `is_loss_cooldown_active()` returns False. Trades that should be blocked re-enter immediately. The cooldown "doesn't work."

**Root cause:** The system has two separate cooldown stores with different write paths:
- `loss_cooldowns.json` — written by `_record_loss_cooldown()` (guardian paper-close path)
- PostgreSQL `signal_cooldowns` — written by `_record_trade_outcome()` (HL live-close path via `_record_trade_outcome()`) and `set_cooldown()`

The reader (`is_loss_cooldown_active()`) checks ONLY `loss_cooldowns.json`. HL live closes (HL_SL_CLOSED, HL_CLOSED, atr_sl_hit) write to PostgreSQL but the reader never checks it → cooldown silently ignored.

**Real example (ETH, 2026-04-22):**
- ETH closed at 14:33 with `HL_SL_CLOSED` (loss) → `_record_trade_outcome()` called → wrote to PostgreSQL only
- `is_loss_cooldown_active('ETH', 'LONG')` checked `loss_cooldowns.json` → empty → returned False
- ETH LONG signal passed cooldown check at 14:36 → new position opened at 14:41
- PostgreSQL had `ETH:LONG` cooldown active the entire time

**Fix:** `is_loss_cooldown_active()` must check BOTH stores:

```python
def is_loss_cooldown_active(token: str, direction: str) -> bool:
    key = f"{token.upper()}:{direction.upper()}"

    # Primary: loss_cooldowns.json (guardian paper path)
    data = _clean_expired(_load_cooldowns())
    if key in data:
        return True

    # Fallback: PostgreSQL signal_cooldowns (HL live-close path)
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM signal_cooldowns WHERE token=%s AND direction=%s AND expires_at > NOW()",
            (key, direction.upper()))
        result = cur.fetchone()
        cur.close(); conn.close()
        if result:
            return True
    except Exception:
        pass
    return False
```

**Diagnosis:**

```python
# Check both stores side-by-side
import json, time, psycopg2
from _secrets import BRAIN_DB_DICT

json_path = '/root/.hermes/data/loss_cooldowns.json'
with open(json_path) as f:
    jdata = json.load(f)
print(f"JSON cooldowns: {len(jdata)} entries")
print([k for k in jdata if 'ETH' in k.upper()])

conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("SELECT token, direction, expires_at FROM signal_cooldowns WHERE expires_at > NOW()")
pg_cooldowns = [r for r in cur.fetchall() if 'ETH' in r[0].upper()]
print(f"PostgreSQL ETH cooldowns: {pg_cooldowns}")
conn.close()
```

**Prevention:** When adding a new cooldown writer (any codepath that calls `set_cooldown()` or `_record_loss_cooldown()`), immediately check which store it writes to. Then verify the reader (`is_loss_cooldown_active`, `get_cooldown`) checks that same store. Add both to the same function if needed. Document the two-store architecture explicitly at the top of the cooldown section.

---

## 24. Duplicate Function Definitions — Wrong One Called at Runtime via Shadowing

**Symptom:** A function (e.g., `_atr_multiplier`) returns wrong values. Manual math shows the expected k=2.0 but runtime uses k=1.5. The pipeline has been running stale bytecode, producing incorrect SL/TP stops across all tokens. No errors or exceptions — just silently wrong numbers.

**Root cause:** Two definitions of the same function exist in the same file — an old copy was never deleted:

```python
# position_manager.py — byte 53038 (correct)
def _atr_multiplier(atr_pct):
    if atr_pct < 0.01: k = 1.0
    elif atr_pct < 0.03: k = 2.0
    else: k = 2.5
    return k

# position_manager.py — byte 60657 (wrong, duplicate)
def _atr_multiplier(atr_pct, override_k=None):  # ← different signature!
    if override_k is not None:
        return override_k
    if atr_pct < 0.01: k = 1.0
    elif atr_pct < 0.03: k = 1.5   # ← different k values
    else: k = 2.0
    return k
```

`_compute_dynamic_sl()` calls `_atr_multiplier(atr_pct, override_k=override_k)`. The call site passes `override_k` — a parameter that **only exists in the wrong duplicate**. Python's function resolution picks the second definition (shadowing the first), and the wrong k values (1.5 instead of 2.0 for 1-3% ATR) run at all call sites.

**Why it wasn't caught earlier:**
- No errors — both functions are syntactically valid
- Both return a `k` value, so call sites don't crash
- The wrong output is close enough to look plausible (1.5 vs 2.0)
- Python bytecode (`.pyc`) caching means the file was loaded once, both definitions registered, and the second shadowed the first — `__pycache__` was never invalidated

**Debug steps:**

1. **Find duplicate definitions** — use `grep` to locate all definitions:
```bash
grep -n "^def _atr_multiplier\|^    def _atr_multiplier" position_manager.py
```
This shows ALL definitions with line numbers. If there are 3+ occurrences, you have a duplicate.

2. **Verify shadowing** — confirm the wrong one is being called by checking the call site signature:
```bash
grep -n "_atr_multiplier(" position_manager.py
```
The call passes `override_k` → the definition accepting `override_k` is the active one.

3. **Check bytecode cache** — even after fixing the source, stale `.pyc` may persist:
```bash
rm -f /root/.hermes/scripts/__pycache__/position_manager.cpython-312.pyc
```

4. **Manual k verification** — for the affected token:
```python
atr_pct = 0.012  # ZEC example, 1.2% ATR
# Wrong (k=1.5): SL distance = 1.5 × 0.012 = 1.81%
# Correct (k=2.0): SL distance = 2.0 × 0.012 = 2.41%
```

**Fix:** Delete the duplicate (wrong) definition. Keep only the correct one. Delete `.pyc` cache. Restart pipeline.

**Prevention:** When refactoring a function in-place (changing its signature), always delete the old definition first before writing the new one. A common mistake: copy-paste a new version below the old one intending to replace it, but forget to delete the original — both now exist and the second shadows the first. Use `git grep "def function_name"` to confirm only one definition before committing.

---

## 23. Guardian Hard-Stop Close Fails Twice — Paper Trade Orphaned, No Fallback Close

**Symptom:** `FATAL: could not close {token} after 2 attempts` appears in guardian logs. The paper DB still shows the trade open. HL also shows the position open (ghost position with no fills). The sync check later shows HL=8 open, paper=9 open — a mismatch. After 2-3 more guardian cycles, the fallback `HL_CLOSED` path eventually closes the paper side, but by then the HL position has been in limbo for minutes.

**Root cause:** Two separate bugs in `hl-sync-guardian.py`:

**Bug 1 — No fallback close when hard-stop fails twice:**
```python
# Lines 1572-1605: hard-stop close loop
for attempt in range(2):
    result = close_position(token)
    if result.get('success'):
        filled = _wait_for_position_closed(token, timeout=15)
        if filled:
            closed_ok = True
            break
    time.sleep(3)

if closed_ok:
    # Close DB trade ← ONLY path that closes paper side
    ...
else:
    log(f'FATAL: could not close {token} after 2 attempts', 'FAIL')
    # ← NOTHING HERE — function exits without closing paper trade
```

When `close_position()` fails twice AND `_wait_for_position_closed()` returns False both times, `closed_ok=False` and the function exits without executing ANY paper-side close. The paper trade is orphaned.

**Bug 2 — `_wait_for_position_closed` uses stale cached positions:**
```python
# Line 838: _wait_for_position_closed()
positions = _get_cached_hl_positions()  # ← could be stale
if token not in positions or float(positions.get(token, {}).get('size', 0)) == 0:
    return True  # Position "closed"
```

If the close order was rejected by HL (rate limit, below minimum, etc.) and never reached the HL state, the cached positions dict still shows the token as open. The function keeps polling the same stale cache for 15s, never detecting that the close order was never placed.

**Real example (APE trade #6730):**
```
03:59:47 [HARD-HARD_SL] APE LONG entry=0.101790 cur=0.102100 SL=0.102159 — closing
03:59:47-04:00:13 close_position() placed on HL, _wait_for_position_closed polled stale cache
04:00:13 [FILL TIMEOUT] APE still on HL after 15s — proceeding anyway
04:00:19 [FAIL] HARD-HARD_SL FATAL: could not close APE after 2 attempts
04:00:35 [LIVE-MISS] APE: max positions — cannot mirror  ← HL at 10/10
04:02:26 Step8 closing APE #6730: exit=0.10225 reason=HL_CLOSED  ← fallback fires 2.5 min later
```

**Fix 1 — Fallback paper close when hard-stop fails:**
```python
if closed_ok:
    # Close DB trade — HL confirmed
    ...
else:
    # FALLBACK: close paper side even though HL didn't confirm
    log(f'  [FALLBACK-CLOSE] HL close failed for {token} — closing paper side', 'WARN')
    conn2 = get_db_connection()
    if conn2:
        cur2 = conn2.cursor()
        cur2.execute("""
            UPDATE trades SET status='closed', guardian_closed=TRUE,
                close_reason=%s, exit_reason='guardian_hard_fallback',
                exit_price=%s, pnl_pct=%s, close_time=NOW()
            WHERE id=%s AND status='open'
        """, (hit_reason, cur_price, pnl_pct, trade_id))
        conn2.commit()
        cur2.close()
        conn2.close()
    log(f'  [FALLBACK-CLOSE] {token} closed at {cur_price:.6f}', 'PASS')
```

**Fix 2 — Fresh HL query in `_wait_for_position_closed`:**
```python
# Use a fresh API call, not cached, for the wait loop
from hyperliquid_exchange import get_open_hype_positions_curl
positions = get_open_hype_positions_curl()  # ← fresh, not cached
if token not in positions or float(positions.get(token, {}).get('size', 0)) == 0:
    return True
```

Also add the actual error from `close_position()` to the retry log:
```python
# Line 1583 — log the actual error, not just "unknown"
err = result.get('error', 'unknown') if isinstance(result, dict) else str(result)
log(f'  [HARD-STOP] Attempt {attempt+1}/2 failed: {err}', 'WARN')
```

**Prevention:** Any code path that attempts an external action (HL close, order placement) and can fail MUST have a fallback path for the paper side. Never let a `FATAL` log be the end of a code path — a `FATAL` should always trigger a defensive paper-side cleanup. The paper DB is the system of record for "what positions should exist"; if HL disagrees, paper should still be correct.

---

## 26. SHORT Trailing SL Uses current_price Instead of ref_price — Peak/Lowest Anchor Broken

**Symptom:** For SHORT positions, the trailing SL appears to use `current_price` in its formula rather than `ref_price` (the lowest price seen). This breaks the peak/lowest anchor — the trailing SL should tighten from the best price, not track the current price. As a result, the SL doesn't properly lock in profit as the price moves in the favorable direction.

**Root cause:** In `_collect_atr_updates()` in `position_manager.py`, line 1609:

```python
# CURRENT (buggy):
new_sl = round(current_price * (1 + MIN_SL_PCT_TRAILING), 8)  # SHORT

# LONG is correct (line 1604):
new_sl = round(ref_price * (1 - effective_sl_pct), 8)  # LONG — uses ref_price
```

For LONG, the trailing SL correctly uses `ref_price` (highest price seen, from `highest_price`). For SHORT, the trailing SL incorrectly uses `current_price` instead of `ref_price` (lowest price seen, from `lowest_price`). The `ref_price` variable IS computed correctly for SHORT (`lowest_price`), but it's never USED in the SHORT trailing SL formula — only in the TP formula.

The bug is masked by the trailing-lock blocking logic (`new_sl >= current_sl → block`) which prevents the SL from loosening when price moves against the position. But the root cause — using `current_price` instead of `ref_price` — means the SHORT trailing SL is not properly anchored to the profit reference.

**Fix:**
```python
# FIXED — SHORT trailing SL should use ref_price, same as LONG
new_sl = round(ref_price * (1 + effective_sl_pct), 8)
```

This ensures the SHORT trailing SL:
1. Uses `ref_price` = `lowest_price` seen (the profit anchor)
2. Uses `effective_sl_pct` = `max(k × atr_pct, 0.20%)` (ATR-based, not fixed %)

**Diagnosis:**
```python
# Check which price the SHORT trailing SL uses
# For the affected SHORT position:
# ref_price = lowest_price from DB (should be the profit anchor)
# current_price = live price (current market price)
# new_sl = current_price × 1.002  ← bug: uses current, not ref

# Verify with pipeline log:
# grep "UNI.*SHORT.*ref=" logs/pipeline.log
# If ref=3.2557 (entry) but new_sl uses current_price that drifted above entry,
# the trailing SL is NOT anchored to the lowest price.
```

**Prevention:** When implementing trailing SL/TP for a SHORT position, always mirror the LONG implementation. The LONG uses `ref_price` for SL. The SHORT should also use `ref_price` for SL. If you ever find yourself using `current_price` for one direction and `ref_price` for another, question why — they should be symmetric for the SL formula (TP already uses ref_price for both).

---

## 27. Attribution of oc-zscore-v9- Source in EXEC Log Without Corresponding Signal

**Symptom:** An EXEC log shows `oc-zscore-v9-` in the source string (e.g., `gap-300-,oc-mtf-macd-,oc-zscore-v9-`), but when querying the signals DB for that execution window, no zscore signal with `z_score_tier=v9` or direction matching the executed trade exists. The executed signal record has `types=ema_sma_gap_300_short,oc_mtf_macd,oc_pending` — no zscore.

**Root cause:** The `source` field in the signals DB is a compactor/artifacts field, not a direct signal type listing. When `signal_compactor` computes confidence via `SOURCE_WEIGHTS`, it uses pairings like `('oc_pending', 'oc-zscore-v9-'): 1.3` to boost confidence. If a signal has `oc_pending` types AND the compact round involves a zscore signal nearby, the `source` field may attribute the zscore even though no zscore signal was part of the actual execution signal.

**Real example:** UNI #7777 EXEC log showed `oc-zscore-v9-` but the executed signal 433232 had `types=ema_sma_gap_300_short,oc_mtf_macd,oc_pending` — no zscore. The zscore signals near the execution window (ids 432818/432952/433020/433231) were all LONG direction with positive z-scores, not SHORT.

**Diagnosis:**
```python
# Get the exact executed signal
cur.execute("""
    SELECT id, signal_types, source, confidence, decision
    FROM signals WHERE id=? AND decision='EXECUTED'
""", (sig_id,))
row = cur.fetchone()
# source field may include components not in signal_types
# signal_types is the authoritative list of what was actually executed

# Check all signals near execution time
cur.execute("""
    SELECT id, signal_types, direction, z_score, created_at, decision
    FROM signals WHERE token=? AND created_at BETWEEN ? AND ?
    ORDER BY created_at
""", (token, exec_time - timedelta(minutes=30), exec_time + timedelta(minutes=5)))
```

**Prevention:** When validating which signals contributed to an execution, always check the `signal_types` column of the executed signal record — not the `source` column. The `source` field may reflect upstream compact round artifacts. The `signal_types` column is the authoritative list.

---

## 25. Global MAX Checkpoint Blocks Per-Entity Fill — Aggregation Never Catches Up

**Symptom:** A computed dataset (aggregated candles, derived indicators) shows stale or permanently-orphaned entries. For one or more tokens, a time window that should be marked `is_closed=1` stays stuck at `is_closed=0` forever. Downstream consumers (regime scanners, signal generators) read stale data and mis-fire.

**Root cause:** A state-tracking query uses `SELECT MAX(timestamp) FROM table WHERE is_closed=1` — a **global MAX across ALL tokens** — as the checkpoint for a fill loop. When ANY single token has a more recent closed row, the global MAX jumps ahead and the `WHERE timestamp > last_computed` condition becomes impossible to satisfy for ALL other tokens.

**Real example from candles_15m aggregation in `price_collector.py`:**

```python
# WRONG: global MAX across all tokens
last_computed = candle_cur.execute(
    f"SELECT MAX(ts) FROM {table} WHERE is_closed=1"
).fetchone()[0]
```

The fill query uses:
```sql
WHERE timestamp > {last_computed}
  AND timestamp <= {last_closed}
```

For BTC:
- BTC's last closed 15m window = 03:30:00 (is_closed=1)
- BTC's 03:45 and 04:00 windows are is_closed=0 (developing)
- But ILV happens to have a closed candle at 04:15:00 (from backfill)
- **Global MAX(is_closed=1) = 04:15:00**
- `timestamp > 04:15:00 AND timestamp <= 04:00:00` = **empty result**
- BTC's 03:45 and 04:00 windows can NEVER be backfilled

Secondary contributing factor: the developing candle (is_closed=0) written for the current window **becomes the MAX ts row** for that token, and the global MAX picks it up as the most recent — even though it's not closed.

```python
# Developing candle write for current_window — inserts is_closed=0
INSERT OR REPLACE INTO {table} (token, ts, ..., is_closed)
VALUES (token, current_window, ..., 0)

# Next run: candles_15m MAX(ts) is now current_window (is_closed=0)
# The global MAX picks up the developing candle
# last_computed = current_window, but the FILL only covers windows <= last_closed
# last_computed > last_closed → fill loop never executes
```

**Diagnosis — verify the checkpoint is token-specific:**

```python
# Check per-token last_computed vs global
import sqlite3
from datetime import datetime

candle_db = '/root/.hermes/data/candles.db'
conn = sqlite3.connect(candle_db)
cur = conn.cursor()

# Global MAX — misleading
global_max = cur.execute('SELECT MAX(ts) FROM candles_15m WHERE is_closed=1').fetchone()[0]
print(f'Global MAX(is_closed=1): {global_max} = {datetime.fromtimestamp(global_max)}')

# Per-token MAX — the real picture
cur.execute('''
    SELECT token, MAX(ts) as last_closed_ts
    FROM candles_15m
    WHERE is_closed = 1
    GROUP BY token
    ORDER BY last_closed_ts
    LIMIT 10
''')
print('\nPer-token last_closed (oldest first):')
for r in cur.fetchall():
    print(f'  {r[0]}: {datetime.fromtimestamp(r[1])}')

# Check which token is causing the global MAX to jump
cur.execute('''
    SELECT token, ts, is_closed
    FROM candles_15m
    WHERE ts = (SELECT MAX(ts) FROM candles_15m WHERE is_closed=1)
''')
print(f'\nToken with global MAX: {cur.fetchall()}')
```

**The pattern in three lines:**

```
FILTER: WHERE timestamp > {global_max_ts}     ← global across all entities
CAUSE:  ANY token with a newer closed row     ← jumps the checkpoint
EFFECT: ALL other tokens miss fill windows   ← permanently orphaned
```

**Fix:** Track the last computed checkpoint **per-token**, not globally. Either:

Option A — Per-token MAX in the fill query:
```python
# Each token's fill starts from its own last closed window
# Use a subquery that finds the per-token last computed
rows = ph_cur.execute(f"""
    WITH token_last_computed AS (
        SELECT token, COALESCE(
            (SELECT MAX(ts) FROM {table} WHERE token=w.token AND is_closed=1),
            0
        ) AS lc
        FROM (SELECT DISTINCT token FROM price_history) w
    ),
    windowed AS (
        SELECT token, ((timestamp / {tf}) * {tf}) AS window_ts,
               price, timestamp
        FROM price_history
    )
    SELECT w.token, w.window_ts, ...
    FROM windowed w
    JOIN token_last_computed tlc ON w.token = tlc.token
    WHERE w.window_ts > tlc.lc
      AND w.window_ts <= {last_closed}
      ...
""")
```

Option B — Process tokens independently in the fill loop:
```python
# Get all tokens that have price_history data
tokens = ph_cur.execute('SELECT DISTINCT token FROM price_history').fetchall()

for (token,) in tokens:
    # Per-token last computed
    last_computed = candle_cur.execute(
        f"SELECT MAX(ts) FROM {table} WHERE token=? AND is_closed=1",
        (token,)
    ).fetchone()[0] or 0

    # Per-token fill windows
    rows = ph_cur.execute(fill_query, {'token': token, 'last_computed': last_computed, ...})
    ...
```

Option C — Change the developing candle logic:
```python
# DON'T write is_closed=0 for the current open window using INSERT OR REPLACE
# That overwrites the ts=rowid and makes the developing candle the MAX(ts)
# Instead: UPSERT only when the window ADVANCES

# Check if this is a new window before writing developing candle
last_dev = candle_cur.execute(
    f"SELECT ts FROM {table} WHERE token=? AND is_closed=0 ORDER BY ts DESC LIMIT 1",
    (token,)
).fetchone()

if last_dev is None or last_dev[0] != current_window:
    # New window — insert developing candle
    candle_cur.execute(f"INSERT INTO {table} ...", (token, current_window, ...))
else:
    # Same window — update existing developing candle
    candle_cur.execute(f"UPDATE {table} SET ... WHERE token=? AND ts=? AND is_closed=0",
                       (token, current_window, ...))
```

**Prevention:** When implementing a fill/replay/aggregate loop that uses a checkpoint:
1. Ask: "Does this checkpoint need to be per-entity or global?"
2. Any time you're aggregating per-token and storing per-token, the checkpoint must also be per-token
3. The global `MAX(ts) WHERE is_closed=1` is almost always wrong when multiple entities exist
4. The `INSERT OR REPLACE` pattern is dangerous when combined with per-entity state — it can accidentally advance the checkpoint to an uncommitted state (developing candle)

**Diagnosis checklist:**
- [ ] Check global MAX — is it from the token you expect?
- [ ] Run per-token last_closed query — how far behind are the slowest tokens?
- [ ] Can you find a token with a newer closed row that jumped the global MAX?
- [ ] Does the orphaned window exist in price_history with enough bars (> bar_count threshold)?
- [ ] Is `INSERT OR REPLACE` being used on a table with developing/uncommitted rows?

---

## Real-World Impact

From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common

**No shortcuts. No guessing. Systematic always wins.**
