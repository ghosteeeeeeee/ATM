---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior. 4-phase root cause investigation — NO fixes without understanding the problem first.
version: 1.1.0
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
for s in statuses:
    if s.get('status') == 'err':
        ...

# After (safe):
result = req.json()
if not isinstance(result, dict):
    return {"success": False, "error": f"Non-dict response: {result}"}
if result.get("status") == "err":
    err_msg = result.get("response", "")
    return {"success": False, "error": err_msg}
statuses = result.get('response', {}).get('data', {}).get('statuses', [])
```

**Prevention:** When wrapping external API responses, validate the top-level structure before accessing nested keys. Use `isinstance(result, dict)` first. If the API uses a `status: err` pattern, handle it at the outermost level before any chained `.get()` calls. Document the error response structure in the code comments.

## Real-World Impact

From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common

**No shortcuts. No guessing. Systematic always wins.**
