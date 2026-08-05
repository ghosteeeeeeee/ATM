---
name: ai-engineer
description: Expert AI/ML engineer persona for AI engineering subagent tasks — ML model development, production deployment, MLOps, and intelligent system integration. Uses context from brain + trading.md + signals DB to make data-driven decisions about the Hermes trading system.
color: blue
emoji: 🤖
category: autonomous-ai-agents
author: T
created: 2026-04-01
---

# AI Engineer Agent

All persona definition and methodology is sourced exclusively from:

**`.hermes/subagents/engineering/ai-engineer.md`**

Do not use any other definition for the AI Engineer persona. All capabilities, rules, workflows, and communication patterns come from that file only.

## When to Use This Skill vs `trading-system-audit`

Use `ai-engineer` to DELEGATE a full Hermes pipeline audit — it is the correct persona to invoke for cross-layer trading system investigations. The `ai-engineer` subagent definition lives in `.hermes/subagents/engineering/ai-engineer.md` and is the execution vehicle; `trading-system-audit` (autonomous-ai-agents) is the methodology reference that should be loaded as context for the delegation.
## Critical Audit Rule (learned 2026-05-08)

**Always check `hermes_constants.py` FIRST in the main session before delegating anything.**
The highest-value bug found in the 2026-05-08 audit (`SIGNAL_SOURCE_BLACKLIST = {}` — all blacklist
entries commented out, empty dict) was missed by 3 prior audit cycles because subagents kept
timing out before reaching it. Run this before ANY delegation:

```bash
grep -n "SIGNAL_SOURCE_BLACKLIST\|CONFLUENCE_REQUIRED\|LONG_BLACKLIST\|SHORT_BLACKLIST" /root/.hermes/scripts/hermes_constants.py
```

If the blacklist is empty or commented, that's a P0 — stop and fix it before continuing.

**RESOLVED 2026-05-13.**

## Subagent Timeout Discipline (learned 2026-05-08, updated 2026-05-18)

**Rule: Single file ≤500 lines → main session always.** Subagent overhead (process spawn,
context serialization, tool translation) dominates for small fast tasks. A 450-line audit
that takes the main session minutes will time out a subagent at 600-900s because the
subagent's startup/context-transfer cost alone eats most of the budget before any real
work starts. Verified: zscore_pump.py (450 lines) audit completed in main session with
no timeout; same audit delegated to subagent with 15-min timeout → timed out at 600s.

**Rule: Multi-file or cross-layer audits → delegate.** When the task requires traversing
10+ files, cross-referencing DB schemas, or checking multiple layers (signal → compactor
→ decider → guardian), subagent parallelism pays off.

For subagent workers:
- Max 8-10 signal scripts per worker
- Constants audit: always in main session
- If a worker times out, do NOT re-delegate — run the remaining checks directly in main session
- When giving subagent a timeout, round up to a known-safe value (e.g., 20 min for a
  complex multi-file audit), but only after confirming the task is too large for main session

The 2026-05-08 signals_runner audit (2 files only) timed out after 447s because the worker
was doing excessive file reads. The fix: main session handles lightweight multi-file
consistency checks (import verification, flag resolution, dead code); subagent gets only
deep-logic review of pre-verified files.

## Patch-Audit Workflow (confirmed 2026-05-11, updated 2026-06-08)

When auditing recently patched files, apply this 2-phase approach:

**Phase 1 — Main session (lightweight, fast):**
```
# 1. Always check constants first (P0 check)
grep -n "SIGNAL_SOURCE_BLACKLIST\|CONFLUENCE_REQUIRED\|LONG_BLACKLIST\|SHORT_BLACKLIST" /root/.hermes/scripts/hermes_constants.py

# 2. Syntax check all patched files
python3 -m py_compile /path/to/patched/file.py

# 3. Read only the patched sections — verify:
#    - All branches handled (no unreachable code)
#    - Values match the spec (e.g., reg_mult = 1.5 not 1.15)
#    - No variable name collisions with existing code
```

**Phase 2 — Implement fixes with constant-first discipline (added 2026-06-08):**

When adding a new gate or filter to a signal script, identify ALL magic numbers (window sizes,
lookback values, thresholds) BEFORE writing any patch. For each magic number:
1. Check if a matching constant already exists in hermes_constants.py
2. If not, add it to hermes_constants.py FIRST with a descriptive name
3. Then import it in the signal script and use it — never hardcode it in the patch

Common culprits: `window = 20`, `lookback = 50`, `ema_lookback = N` — these are always
tunable and must live in hermes_constants.py. Found the hard way: a 20-bar slope window and
50-bar EMA lookback were both hardcoded in the initial patch and had to be extracted post-hoc.

**Phase 3 — Subagent (deep logic review of patched files only):**
- Give subagent ONLY the patched files to audit
- Focus checklist on: error handling completeness, confidence bounds, interaction with downstream multipliers
- Include the stale-comment bug pattern in the checklist: "docstring says X but code does Y"

**Session 2026-06-03 confirmed clean:** rs.py patches (broken-level reclassification) passed subagent audit — no new bugs. Subagent correctly verified `bounce` field has no downstream consumers, `broken` is not carried in signal dict, and equality edge cases handled correctly. Subagent timed out at 155s (well under 450s budget).

**Recurring stale-comment pattern (2 bugs found 2026-05-11):**
- `signal_compactor.py:200` — docstring said +15%/-30%, code did +50%/-50%
- `rs.py:496-501` — comment said "25% penalty", actual haircut was 20%
Fix: always cross-reference comments against actual computed values, not just the spec.

## Subagent False-Positive Pattern (learned 2026-05-12)

**Pattern 1 — "Not found" false positives:** Subagent reports "MA_CROSS_PLUS_ENABLED not in hermes_constants" as P1. Main session verifies — flag IS present at line 419.

**Root cause:** Subagent's grep/search tools returned empty results due to tool errors (MCP coding tool read_file failures), not because the flags are absent. The subagent drew the wrong conclusion from empty output.

**Rule:** When a subagent reports a "missing flag" or "not found" bug, verify it in the main session before accepting it as real. Run:
```bash
grep -n "MA_CROSS_PLUS\|MA_CROSS_MINUS\|GAP_300_PLUS\|GAP_300_MINUS" /root/.hermes/scripts/hermes_constants.py
```
If the flag exists, the subagent's tools malfunctioned — the bug report is a false positive. Do NOT relay unverified subagent conclusions to the user. Always do a direct verification pass in the main session before reporting subagent findings as fact.

**Pattern 9 — Subagent confirms some bugs but misses the primary P0 bug (found 2026-05-29):**
Subagent was delegated to audit `zscore_rising.py` (3 known bugs to verify). It confirmed Bug 1 (kill-switch gates unused) and Bug 4 (dead code) but completely missed Bug 3 — the fundamental `scan_zscore_rising_signals()` logic error: single full-array z-score instead of per-bar iteration. The subagent never flagged this because the backtest data it was given showed fires per-bar (correct) but the scan function itself was broken (wrong). The subagent trusted the backtest result and didn't audit the scan function's actual logic.

This is a **reasoning-depth failure**: the subagent verified surface-level bugs (import, dead code, guard flags) but never questioned the core algorithm. The backtests appeared to validate the signal correctly, masking the fact that the scan function was broken.

**Rule:** When delegating bug-verification of a new signal, always separately verify the core algorithm BEFORE accepting the subagent's audit as complete. Do a quick Python simulation of the core loop logic against known data to confirm it works as expected. Surface-level checks (import, syntax, flag guards) are not sufficient for new signal logic.

**Guardian restart rule (found 2026-05-20):** Python constants are imported at module load time. If the guardian was started when `LIVE_TRADING_ENABLED=False`, flipping the constant in hermes_constants.py does NOT propagate to the running guardian process — the old value stays baked in. After ANY change to hermes_constants.py that affects guardian behavior (kill switch, trade size, min notional), the guardian MUST be restarted. Always check guardian process status after hermes_constants.py changes and restart if needed.

**Pattern 62 — Subagent "surface pattern ≠ root cause" — same-name function ≠ same role (found 2026-06-24):**
Subagent audit reported `hebbian_learner.py` as a "parallel pollution source" because it had its own `infer_label()` (line 37) and `extract_concepts()` (line 52) — same function names as `hebbian_entity_extractor.py`'s broken versions. Subagent's conclusion: "delete it, or apply Fix 1's filter, otherwise it keeps polluting the DB."

This was wrong. `hebbian_learner.py` is a **brain-md seeder** (scans `brain/*.md` for co-occurrences to seed the network from T's documented knowledge) — a *complementary data source*, not a competing extractor. It has zero live callers because it was never wired to a timer. Deleting it would have destroyed the highest-signal data source in the system. T pushed back directly: "I'm not following, it is what we are trying to improve isn't it?"

**Root cause:** Subagent applied structural pattern matching (same function name + no live callers = dead/redundant) without reading the file's purpose (docstring + main() + the data flow it produces). It treated `infer_label` as the *identity* of the file rather than a *tool the file uses*.

**Rule:** When a subagent flags a file as "redundant / parallel / pollution source" purely on the basis of structural similarity (same function name, same imports, no live callers), DO NOT accept the framing without:
1. Read the file's docstring (lines 1-10)
2. Read its `main()` to see what data it processes and writes
3. Grep for any external use of the *output* (not just the file): `grep -rn "output_table\|output_path\|output.json\|writes to"` — the file may produce data that other components consume even if no code imports it
4. Check git log for the file's evolution — was it ever wired up? Was it intentionally archived?

If the file produces a unique, currently-needed data source (like seeding from human-written brain docs), the right fix is **integrate it** (refactor to share code with the sibling, add a timer to run it), not delete it.

**Adjacent lesson:** absence of live callers is **ambiguous evidence**. It could mean (a) dead code, (b) never wired up, (c) replaced by a newer tool, (d) run only manually. Subagents can't disambiguate from structure alone. The asymmetry: deleting wrong is permanent; integrating wrong is reversible.

**Pattern 63 — `process list` and `ps auxf` do NOT track subagent delegations (found 2026-06-24):**
See `references/audit-surface-pattern-vs-purpose-2026-06-24.md` for the full reproducer
on Pattern 62 (the surface-pattern-vs-purpose lesson that triggered the docstring/main()/git-log
verification discipline).

**Pattern 63 — `process list` and `ps auxf` do NOT track subagent delegations (found 2026-06-24):**
After `delegate_task`, checking `process(action='list')` returns empty, and `ps auxf | grep deleg` returns nothing. Both look like "subagent failed to launch" but actually mean nothing — subagents run in isolated contexts the main session's process tracker doesn't see.

When the user asks "did the subagent finish?", do NOT check `process list` or `ps`. Instead:
- Trust the dispatch contract: `"status": "dispatched"` means the runtime accepted it
- The result will arrive as a new conversation message — either an `[ASYNC DELEGATION BATCH COMPLETE]` block (batch) or a direct tool result (single)
- If you genuinely need mid-task verification, check `/tmp/hermes-results/` (subagent results directory) for the delegation_id-named file
- The instruction "do not wait or poll" in the dispatch tool's response is real — there is no live polling API for subagents

**Rule:** When the user asks "is the subagent running?" after a dispatch, the honest answer is "I can't directly observe subagents, but the dispatch returned successfully and the result will appear as a new turn when it finishes." Do NOT report "I can't confirm" without offering the corrective framing — that phrasing makes it sound like a failure when it's normal Hermes architecture.

**Pattern 2 — Logic inversion false positives (learned 2026-05-13):** Subagent reports `delta_last >= delta_prev` as inverted for LONG and `delta_last <= delta_prev` as inverted for SHORT. On full trace, the SHORT branch is actually correct — the sign of `delta_last` is negative for SHORT positions, so `<=` correctly skips decelerating SHORT momentum. The LONG branch IS inverted.

**Root cause:** Subagent did not account for the sign of the gap_pct value itself. For LONG, gap_pct > 0, so `>=` comparison is inverted. For SHORT, gap_pct < 0, so the inequality direction flips.

**Fix:** When a subagent reports an inverted `>=`/`<=` inequality in a directional signal, always trace through both directions with concrete sign values. Do not accept "X is inverted" without verifying the sign context of the variable in each branch.

**Pattern 3 — Loop bounds false positives (learned 2026-05-13):** Subagent reports `range(PERIOD + LOOKBACK, len(closes) - 1)` as an off-by-one that "misses the last bar." The `-1` was actually intentional OOB protection — the loop body contains a `cross_bar` search that accesses `closes[j]` where `j` can equal `i` at the upper bound of `range(i-LOOKBACK, i+1)`. Without the `-1`, the final iteration would OOB.

**Fix:** Before flagging a loop bound as an off-by-one bug, trace all array accesses within the loop body that use `i` or ranges derived from `i`. If any access could reach `len(closes)`, the `-1` is intentional protection. Verify with a Python one-liner:
```python
python3 -c "n=700; print('OOB at', n, 'but len=', n-1, '— len-1 is intentional')
```

**Pattern 6 — Final-verify checks wrong index (found 2026-05-14):**
...
**Pattern 7 — Confidence bonus threshold misaligned from signal threshold (found 2026-05-14):**
A common audit finding: code computes a signal at loop index `i`, then verifies it against
`len(closes) - 2` (the newest bar), not against `i` (the bar where the signal was detected).
This causes valid signals to be blocked by post-detection price reversals.

Example from accel_300.py lines 319-336:
```python
current_bar_idx = len(closes) - 2   # ← ALWAYS the newest bar
if current_bar_idx != i:
    if direction == 'LONG' and not (closes[current_bar_idx] > ema300[current_bar_idx]):
        continue   # ← blocks signal at i because bar n-2 reversed
```

Signal detected at i=695 (gap growing 0.30→0.33), but bar 698 (n-2) gap=-0.02 → blocked.

**Fix:** Always verify against the bar where the signal was detected (`i`), not the newest bar.
If the intent is to check for staleness, do it explicitly with a `bars_since_cross > N` check
before the final return, not by re-checking a different bar's gap.
**Pattern 7 — Confidence bonus threshold misaligned from signal threshold (found 2026-05-14):**
A signal fires when `value >= CONSTANT_A` (e.g., `MIN_GAP_GROWTH = 0.03%`), but the confidence
formula uses `bonus = max(0, value - 0.05) * multiplier` — with a DIFFERENT hardcoded threshold
(0.05%) for the bonus. Signals that clear CONSTANT_A but fall below the bonus threshold get no
bonus, making confidence under-represent the signal's actual strength.

Example from accel_300.py line 426:
```python
gap_bonus = max(0, sig['gap_growth'] - 0.05) * 200  # bonus threshold = 0.05
# but MIN_GAP_GROWTH = 0.03  ← signal fires at 0.03, bonus kicks in at 0.05
```

**Fix:** Always use the same named constant in both the signal gate and the confidence formula.
Never hardcode a numeric threshold in the confidence formula when a named constant governs the
signal itself. If you need a higher threshold for the bonus than for the signal, define a
separate `BONUS_THRESHOLD` constant and document why it's higher.

**Pattern 8 — Per-run dedup missing in decider_run hotset loop (found 2026-05-15):**
`execute_all()` in `decider_run.py` iterates `hotset_sorted` (line 967). For each entry,
it calls `execute_trade()` which checks PostgreSQL for open trades (lines 694-702). BUT:
two signals for the same token+direction in the same hotset iterate before the first
INSERT commits. The second iteration's PostgreSQL check reads state as it was BEFORE the
first INSERT — so both pass the duplicate check.

**Fix:** Add `_processed_tokens_this_run = set()` before the loop. Inside the loop, before
`execute_trade()`, skip if `token in _processed_tokens_this_run`. Add token after skip check.

**Verified by subagent (2026-05-15):**
- No existing per-run dedup mechanism exists
- Hotset CAN have duplicate token+direction via signal_compactor merges
- Fix placement inside `for hot_sig in hotset_sorted:` loop, before `execute_trade()`, is correct
- Token-only dedup (not token+direction) over-blocks opposite direction but is safe — capital already deployed makes opposite-direction entry questionable

**Pattern 14 — Gate threshold uses wrong lookback, never fires (found 2026-05-18):**
A new gate is added to `detect_zscore_pump()` with a bar-minimum check. The condition uses
`lookback * 2 + BARS + 2` (e.g., 205 bars for lookback=100, BARS=3) but the caller in
`scan_zscore_pump_signals()` only fetches `lookback + 50 = 150 bars`. The gate is dead code
— it can never activate regardless of how extreme the divergence is.

This is a **systematic off-by-magnitude error**: the gate minimum should be based on the
short lookback used internally (spot_lookback), not the signal's long lookback.

```python
# WRONG — needs 205 bars but only 150 available
if ZSCORE_PUMP_DIVERGENCE_ENABLED and len(prices) >= lookback * 2 + ZSCORE_PUMP_DIVERGENCE_BARS + 2:
    if _check_divergence(prices, lookback):
        return None

# FIXED — needs 25 bars, always satisfied by lookback+50 fetch
if ZSCORE_PUMP_DIVERGENCE_ENABLED and len(prices) >= ZSCORE_PUMP_DIVERGENCE_LOOKBACK + ZSCORE_PUMP_DIVERGENCE_BARS + 2:
    if _check_divergence(prices, lookback):
        return None
```

**Rule:** When adding a new gate, always derive its minimum bar requirement from the
shortest lookback used inside the gate function, not the caller's total fetch size.
Verify: the gate condition's RHS must be ≤ `lookback + 50` (the caller's fetch).

**Pattern 19 — Stale time-unit comment (found 2026-05-18):**
A comment says "~10 minutes" for a 5-bar cooldown on 1m data. The actual behavior is
`COOLDOWN_BARS / 60.0 = 5/60 ≈ 0.083h ≈ 5 minutes`. The comment overestimates by 2x.

```python
# WRONG — comment says "10 minutes" but 5 bars = 5 minutes on 1m
set_cooldown(token, direction, hours=ZSCORE_PUMP_COOLDOWN_BARS / 60.0)  # 5/60 = 0.083h
# Set cooldown: don't re-fire for COOLDOWN_BARS bars (~10 minutes)       ← stale

# CORRECT — match comment to actual value, or use a computed constant
COOLDOWN_MINUTES = ZSCORE_PUMP_COOLDOWN_BARS  # 5
# Set cooldown: don't re-fire for COOLDOWN_BARS bars (~5 minutes on 1m)
```

**Rule:** When a comment describes a time duration derived from a numeric constant,
always verify with the actual value. Better: compute the time at常数 definition
and document it in the comment with the actual computed value, not an estimate.

**Pattern 15 — `.index()` finds first occurrence not last (found 2026-05-18):**
When searching for the peak in a z-score or momentum series, `.index(peak_value)` returns
the first occurrence. If the peak occurred multiple times, this underestimates
`bars_since_peak`, making the divergence check fire too early or not at all.

```python
# WRONG — first occurrence
peak_idx = recent_zs.index(peak_z)

# CORRECT — last occurrence (most recent peak)
peak_idx = max(idx for idx, z in enumerate(recent_zs) if z == peak_z)
```

**Rule:** When finding a peak in a time series, always use `max(idx for ... if val == peak_val)`
to get the most recent occurrence. Only use `.index()` when you explicitly want the first.

**Pattern 16 — Off-by-one: rolling window loop misses most recent bar (found 2026-05-18):**
A rolling z-score computed as `for i in range(spot_lookback, len(closes))` evaluates the chunk
`closes[i-spot_lookback:i]` — which at the last iteration (`i = len(closes)-1`) excludes
`closes[-1]`. The most recent price is never scored; the entire z-series is shifted left
by one bar.

```python
# WRONG — last iteration misses closes[-1]
for i in range(spot_lookback, len(closes)):
    chunk = closes[i - spot_lookback:i]

# CORRECT — extends to len(closes)+1 so closes[-1] is scored
for i in range(spot_lookback, len(closes) + 1):
    chunk = closes[i - spot_lookback:i]
```

**Rule:** For rolling window iterations over a `closes` list where the chunk is
`closes[i-window:i]` and the intent is to score every bar from `window` to the last bar,
the range must be `range(window, len(closes) + 1)`. The `+1` compensates for Python's
half-open interval `[i-window, i)`.

**Pattern 17 — Confidence formula unconditionally overwrites tuner value (found 2026-05-18):**
When a signal uses both a tuner (win-rate based confidence) and a z-bonus, the z-bonus
line completely replaces the tuner's carefully-derived value:

```python
# Line 354: tuner path sets confidence = 85 (based on win_rate)
confidence = min(95.0, max(80.0, wr))

# Line 387: z-bonus OVERWRITES — tuner value discarded
confidence = int(min(95, confidence + conf_bonus))  # replaces 85 with 82
```

The tuner's WR-based confidence and the z-bonus are independent signals of quality.
The final confidence should be the max of both, not the sum.

```python
# CORRECT — preserves whichever is higher
confidence = int(min(95, max(confidence, confidence + conf_bonus)))
```

**Rule:** When two independent confidence estimators coexist (tuner + bonus),
use `max()` not replacement. The base (tuner, win_rate, regime_conf) should be a
floor, not a starting point that gets overwritten.

**Pattern 18 — Trailing gate `pass` leaves `needs_X=None` (falsy), blocking ALL updates (found 2026-05-18):**
A trailing gate checks if a value should be tightened/updated. The tighten branch uses `pass`
leaving the result dict's `needs_sl` or `needs_tp` as `None` (falsy). Downstream code
uses `if needs_sl or needs_tp or ...` — since `None` is falsy, the update is blocked
even though the new value is correct.

```python
# WRONG — needs_sl stays None (falsy), downstream gate blocks update
if new_sl < current_sl:  # tightening — correct direction
    pass                  # BUG: needs_sl was initialized to None at top of function

# CORRECT — explicitly set the flag
if new_sl < current_sl:
    result['needs_sl'] = True  # tighten allowed
```

This happened in `tpsl_utils.py` lines 416 (LONG) and 434 (SHORT) in the trailing SL gate.
Both had `pass` in the tighten branch, silently blocking all SL updates for established trades.

**Rule:** When a branch is a "do nothing / allow through" case, ALWAYS explicitly set the
result dict key, never use bare `pass`. Initialize all result keys to a safe default at the
top, but branches that allow an action must set `True` explicitly.

**Subagent pointed at wrong files (archive copies) — always verify file path (found 2026-05-18):**
A subagent auditing `position_manager.py` found that `_collect_atr_updates` and
`_persist_atr_levels` "do not exist." The subagent was reading archive copies at
`/root/.hermes/archive/hermes-archive-*/position_manager.py` (875 lines each) instead of the
live file at `/root/.hermes/scripts/position_manager.py` (3111 lines). The live file has
both functions at the correct lines.

**Rule:** Before delegating to a subagent, always confirm the canonical path of the file
being audited. Archive copies multiply over time and become stale. The live code lives at
`/root/.hermes/scripts/`. When giving subagents file paths, give the specific line ranges
AND verify those ranges exist in the file they will actually read.

**Pattern 21 — PostgreSQL column type coercion for arithmetic (found 2026-05-19):**
A subagent reported "UPDATE has 8 placeholders but 9 params — mismatch!" — false positive.
The UPDATE was:
```sql
UPDATE trades SET
    status='closed',         -- hardcoded literal, NOT a placeholder
    close_reason=%s,        -- placeholder 1
    ...
WHERE id=%s                 -- placeholder 8
```
8 `%s` placeholders, 8 params — MATCH. The subagent counted `status='closed'` as a
placeholder when it is a hardcoded string value.

**Fix:** Always distinguish hardcoded literal values from `%s` placeholders when counting.
A SQL string with `status='closed'` (no `%s`) has one fewer placeholder than columns.
Similarly, `guardian_closed=TRUE` is a hardcoded boolean, not a placeholder.

**Rule:** When a subagent reports a param/placeholder mismatch, verify by running the
actual query string through `.count('%s')` in Python and comparing against `len(params)`.
Do not accept the subagent's count without this verification.

**Subagent param-count false positive (2026-05-20):** Subagent reported brain.py _params
had 43 items for 44 placeholders. The "proof" showed a count of comma-separated items
visible in the source — but ternary expressions spanning multiple lines (`json.dumps(X)
if X else 'Y'`) occupy ONE tuple slot, not two. Main session verified: actual tuple
evaluated to 43 items (after duplicate removal), the missing slot was `_exp_metadata`
(col 44), fixed by pre-building `_exp_metadata_str`. Subagent's visual counting method
failed to account for expression evaluation semantics.

**replace_all=True PATCH CORRUPTION (found 2026-05-20):**
Using `replace_all=True` on hl-sync-guardian.py (1600+ lines) via the patch tool created
DUPLICATE CODE BLOCKS at lines 1261 and 3733 — file became syntactically invalid.

**Fix:** Never use `replace_all=True` on files >500 lines. Always do targeted single-location
patches. If corruption occurs, revert with `git checkout -- scripts/<file>.py` and re-apply
as separate targeted patches. This is especially critical for hl-sync-guardian.py, brain.py,
and position_manager.py which are all 1000+ lines.

---

**Pattern 21 — PostgreSQL column type coercion for arithmetic (found 2026-05-19):**
PostgreSQL `real` columns return Python `float` or `None`; `numeric` columns return
Python `Decimal`. Doing arithmetic directly — `realized_pnl / calc_notional` — fails
with TypeError if `calc_notional` is `Decimal` or `None`, or ZeroDivisionError if it's 0.

**Pattern 64 — `delegate_task` "lost dispatch" false failure (found 2026-06-24):**
A `delegate_task` call returned `"status": "dispatched"` cleanly with a delegation_id, then `process list` returned empty, `ps auxf | grep deleg` showed nothing, and no result file appeared anywhere. The main session declared "can't confirm running" to the user and offered to re-dispatch — but ~4 minutes later the original delegation's `[ASYNC DELEGATION BATCH COMPLETE]` message arrived carrying the full result. **The delegation worked the entire time; the main session's tools just couldn't observe it.**

Root cause: subagent processes run in an isolated context that doesn't appear in `process list` or `ps`. The result is delivered via a new message turn, not a file or process signal.

**Rule for main session when delegating an audit / task:**
1. A clean `"status": "dispatched"` response IS confirmation the subagent is running. Don't poll `process list`.
2. If the user asks "is the subagent running?" within a few minutes of dispatch, say: "dispatched successfully — result will arrive as a new message when it finishes, typically 200-500s for focused tasks."
3. Only re-dispatch if the result has not arrived AND the user explicitly says "give up on it, try a different approach." Burning a second dispatch "to be safe" wastes budget — the original result will still arrive and contaminate the conversation with stale data.
4. Verify subagent findings with main-session grep regardless of how the result arrives. The async delivery mechanism doesn't change the verification rule.

**Pattern 65 — Prompt-injection / secret-leak risk in session dump backfills (found 2026-06-24):**
`request_dump_*.json` files (under `/root/.hermes/sessions/`) contain raw HTTP request bodies including `Authorization: Bearer ***` API keys in headers, plus `sk-` keys (OpenRouter, OpenAI) embedded in body messages. Verified directly:
```python
# From /root/.hermes/sessions/request_dump_*.json
"headers": {"Authorization": "Bearer ***", "Content-Type": "application/json"}
# sk- count in body: 2
```
Any script that truncates the request body to a fixed character count for a `summary` field risks landing API key fragments in the database. **For any session-distill / backfill script that produces text to be stored or shown:**
1. Explicitly strip `Bearer ...` patterns from any text field before INSERT.
2. Explicitly strip `sk-...` patterns (regex: `sk-[a-zA-Z0-9-]{20,}`).
3. Don't include raw HTTP headers in any extracted text — only `request.body.messages[*].content` is safe.
4. The `session_*.json` `system_prompt` field (38,830 chars of full SOUL.md) MUST be skipped during entity extraction — otherwise 4,007× duplicate co-occurrences of every concept in SOUL.md pollute the graph.

**Rule:** When auditing any code that reads `request_dump_*.json`, `session_*.json`, or similar dump files, treat their contents as untrusted input — even though they originate from your own system. Strip credentials before persistence.

**Pattern 66 — Sibling extractor files missed by audits (found 2026-06-24):**
The Hebbian entity extraction audit verified `hebbian_entity_extractor.py` and proposed a fix for its unfiltered ALL_CAPS regex. But `/root/.hermes/scripts/hebbian_learner.py` (182 lines) ALSO had its own `infer_label()` at line 37, `extract_concepts()` at line 52, `normalize_concept()` at line 95, and `seed_from_file()` at line 103 — all unfiltered. The plan and prior auditor missed it because they grepped for function calls, not function definitions across the whole module.

**Rule when auditing entity extraction / NLP / parsing pipelines:**
1. After fixing the primary file, run `grep -n "def \(extract\|parse\|infer_label\|normalize\|tokenize\)" <module_dir>/` — look for SIBLING files with the same function names.
2. Also run `grep -rn "from .* import.*\(extract\|parse\|infer\|normalize\)" <module_dir>/` — find alternative import paths.
3. The pattern generalizes: any time a function is "the canonical one" in a module, check if sibling modules have parallel implementations. Vocabularies duplicated across files (already a known pattern) are a sibling symptom.
4. Always grep the broader module directory: `grep -rn "<function_name>" <module_dir>/` not just `grep -rn "<function_name>" <specific_file>.py`.

**Pattern 67 — `mcp_hermes_coding_mcp_search_code` regex parser fails on alternation (confirmed 2026-06-24):**
`mcp_hermes_coding_mcp_search_code` with a regex like `seed_decisions_log|learn_from_decisions_log` fails with "unterminated character set at position 11" — the parser doesn't handle `|` alternation correctly. Workaround: use `grep -rn` via terminal, which handles alternation natively and is the authoritative tool for code search anyway.

**Rule:** For multi-pattern code search, always prefer `grep -rn` via terminal over `search_code` MCP tool. Reserve `search_code` for single-pattern queries where its integration with the read tool saves a step.

**Pattern 22 — Tuple item count differs from naive line count (found 2026-05-20):**
brain.py `_params` tuple appeared to have 43 items but `exp_metadata` appeared only once
in the source — yet the tuple evaluated to 43 items. Root cause: `json.dumps(exp_metadata)
if exp_metadata else '{}'` was a single ternary expression occupying one tuple slot, while
the bare `exp_metadata)` on the next line was a SECOND expression also consumed into the same
ternary result (parser interpreted it as `...else exp_metadata)` which is a SyntaxError
that got silently worked around by an earlier patch removing the bare `exp_metadata)`.
The second, later patch that removed the bare `exp_metadata)` left a hole — one slot that
looked filled but wasn't.

**Verification:** Always simulate the tuple in a Python interpreter to get the TRUE item
count, never count by eyeballing the source lines or grepping for commas. The count must
match `.count('%s')` on the actual SQL string at runtime. False positive generators:
- Tuple expressions split across lines with inline conditionals (ternary) look like two items
  but are one
- Empty `None` placeholders for unmapped columns shift downstream items — INSERT still works
  but values land in wrong columns (semantic bug, not crash)
- PostgreSQL accepts undersized tuples silently (no IndexError from psycopg2 itself) — INSERT
  appears to succeed but row has NULL/wrong values

**Rule:** When auditing a tuple-vs-SQL mismatch, run the actual file through Python to count
real tuple items: `python3 -c "import sys; sys.path.insert(0,'/root/.hermes/scripts'); import brain; print(len(brain._test_params()))"` or equivalent inline simulation. Do not trust visual line count or grep for commas.

**Rule:** When reading ANY column from PostgreSQL for use in arithmetic, always coerce
to the appropriate numeric type (float/int) before use.

**Subagent timeout produces false positives (found 2026-05-19):**
A subagent delegated to audit the full trading system timed out at 600s. Its "findings"
(e.g., "HL_MIN_NOTIONAL_USDT not found") were false positives — the constants ARE
deployed correctly (22+ imports found). The subagent's search_files tool returned empty
results during timeout phase, leading the subagent to incorrectly conclude constants were missing.

**Subagent false positive: Architectural desync between writer and reader (found 2026-05-21):**
A subagent reported "hotset.json has 10 entries but no trades fire" and listed multiple
possible causes (flags, blacklist, open positions). All individual checks were correct but
missed the real bug: `signal_compactor` writes to `hotset.json` directly while `decider_run`
reads from `get_approved_signals()` (DB). The two are disconnected — entries enter hotset.json
without creating APPROVED DB rows, so decider_run always gets 0 results. This is NOT a
flag/constant/logic bug — it is a cross-file architectural desync. Subagents see both files
as "working correctly" in isolation and miss the interface gap.

**Rule:** When auditing pipeline desyncs (signals enter hot-set but no trades fire), always
check what the CONSUMER reads vs what the PRODUCER writes. `decider_run` does NOT read
`hotset.json` — it queries `signals` DB table via `get_approved_signals()`. Any code path
that writes `hotset.json` without also writing an APPROVED row to the DB is a broken link.
Always trace the data flow: source → signal_compactor → [DB + JSON] → decider_run reads DB only.

**Rule:** Always verify subagent findings in main session with `grep -rn` before accepting.
If grep finds it and subagent says it doesn't exist → tool malfunction, not a real bug.
For constant-existence checks, grep via terminal is authoritative; search_files is not.

## T's Communication Style — ALL_CAPS = coin signal channel

**T uses all-caps almost exclusively for coin tickers he wants to draw attention to**
(BTC, ETH, XLM, etc.). Acronyms (API/SQL/JSON) are conventional and stay in stopword lists.

**Implication for any extraction/recall/parsing pipeline that touches ALL_CAPS words:**
1. Default to the **strict-token-only filter**: an all-caps word is treated as a coin
   ticker unless explicitly excluded. The opposite default (treat as acronym, allow
   through as concept) produces the exact pollution T was trying to avoid.
2. New acronyms get added to the stopword set explicitly (with a one-line comment
   explaining why), never the other way around.
3. For Hermes entity extraction in particular: the strict `if lt == "token"` gate on
   ALL_CAPS extraction is correct under this assumption. Document the design constraint
   in a code comment so future agents don't second-guess it.
4. This generalizes beyond Hermes. Any system where a user uses capitalization as a
   deliberate signal channel (T's case: "I want attention drawn to this coin") should
   respect that channel rather than treating it as noise.

Source: confirmed by T directly during Hebbian plan audit (2026-06-24). T said: "I rarely
use all caps, when I do it is usually a coin name that I am drawing your attention to."

**Rule for delegation:** Timeout at 600s with 35 API calls = tool instability. Do NOT
re-delegate. Run the verification checks directly in main session.

**Pattern 68 — Verify live-path wiring BEFORE auditing (learned 2026-07-13):**
**Pattern 69 — Slice-arithmetic cancellation = high-distraction bug class (learned 2026-07-13):**
**Pattern 70 — set_cooldown coverage gap across signal scanners (learned 2026-07-13):**

See `references/signal-script-audit-2026-07-13.md` for the full audit context:
- Live-path wiring table (which `*_signals.py` files actually run in the pipeline)
- `pattern_scanner.py` slice-arithmetic reproducer with concrete values
- `set_cooldown` coverage matrix across the 12 audited scripts

**Pattern 26 — Subagent claims `>=` is inverted for SHORT marginal acceleration (false positive, found 2026-05-31):**
Subagent claimed `if direction == 'SHORT' and delta_last >= delta_prev: continue` at line 310
was inverted — should be `<=`. Concrete trace with negative SHORT values proves `>=` is CORRECT:

- Accelerating SHORT: `delta_last=-0.08 >= delta_prev=-0.03` → False → PASS ✓
- Stable SHORT: `delta_last=-0.05 >= delta_prev=-0.05` → True → BLOCK ✓
- Decelerating SHORT: `delta_last=-0.02 >= delta_prev=-0.06` → True → BLOCK ✓

With `<=` (subagent's proposed fix):
- Accelerating SHORT: `delta_last=-0.08 <= delta_prev=-0.03` → True → BLOCK ✗
- Decelerating SHORT: `delta_last=-0.02 <= delta_prev=-0.06` → False → PASS ✗

The subagent applied abstract inequality reasoning without accounting for the fact that
`delta_last` and `delta_prev` are both NEGATIVE for SHORT, so `>=` correctly blocks when
the gap is not becoming MORE negative (decelerating).

Same root cause as Pattern 25: sign-blind inequality analysis. For SHORT delta comparisons:
`delta_last >= delta_prev` means "current bar gap change is >= previous bar gap change"
— with both values negative, this correctly fires only when the gap is NOT accelerating.

**Rule:** When a subagent reports an inequality is inverted for a directional signal,
ALWAYS trace with concrete sign values for that direction. For SHORT: delta values are
negative. `>=` tests "is the gap change less negative or equal" (decelerating/stabilizing).
`<=` tests "is the gap change more negative or equal" — wrong for SHORT acceleration check.

**Pattern 27 — Signal dict missing `recency_score` key crashes logging (found 2026-06-03):**
`detect_rs_signal` builds signal dicts for 4 cases: LONG broken, LONG non-broken, SHORT broken,
SHORT non-broken. All 4 dicts are logged in `scan_rs_signals` line 780 with unconditional
`sig['recency_score']` access. The SHORT non-broken path (lines 650-659) was missing
`recency_score`. Any SHORT resistance signal that wins the confidence comparison crashes
`scan_rs_signals` with KeyError on `recency_score`.

Fix: always verify ALL signal dicts in a multi-path function include every key that
downstream code accesses unconditionally. A simple audit checklist: for each dict
construction branch, enumerate all keys and cross-reference against every caller that
reads those keys.

**Pattern 28 — Clustered level lookup misses recency_by_level dict (found 2026-06-03):**
`_cluster_levels` returns `(avg_price, total_touch_count)` where `avg_price` is the mean
of multiple raw levels — a value that almost never exactly matches any raw level price.
`recency_by_level` is keyed by raw level prices (not clustered averages). When the loop
at lines 499-517 does `recency_by_level.get(level, 0)` where `level` is the clustered price,
the lookup always misses and returns 0. This affects BOTH support and resistance paths.

Fix: after clustering, map each clustered level back to the nearest raw level's recency
score via a nearest-level search, or build a separate `recency_by_clustered_level` dict
keyed by clustered prices.

**Pattern 29 — Bounce confirmation nearly impossible on close-only candles (found 2026-06-03):**
price_history synthesizes `open=high=low=close` for every candle. In `_bounce_confirmation`:
- Condition (a) `c['close'] > c['open']` is ALWAYS False (equality) — dead branch
- Condition (b) `next_close > c['close'] * 1.00025` uses 0.025% of candle close as threshold
  for recovery, which is completely different from the ATR-normalized touch threshold

For a token with ATR=1.0 (1% of price): touch threshold = 1.0 (line 220), bounce threshold =
`c['close'] * 0.00025` ≈ 0.025% of candle close. These are two completely different regimes.
A candle can touch a level at 0.8% distance but bounce confirmation requires only 0.025%
movement beyond the touch candle's close — a ~32x difference in threshold scale.

Severity: functional gap, not crash. Bounce confirmation on close-only candles is
nearly impossible to satisfy when ATR is meaningful. Consider comparing `next_close` to
`level` (not `c['close']`) or normalizing the bounce threshold by ATR like the touch
threshold is.

**Pattern 30 — Docstring says "weighted by touch count" but code does simple average (found 2026-06-03):**
`_cluster_levels` docstring says "Each cluster is replaced by its average price weighted by
touch count." The code at lines 170 and 181 computes `sum(p for p, _ in cluster) / len(cluster)`
— a simple unweighted mean. Touch counts are summed at line 182 (`total_count`) but never
used in the price averaging. This is a docstring/code mismatch, not a logic error (simple
average clustering is a valid approach), but the docstring misleads future readers.

**Rule:** When updating a function's implementation, update its docstring immediately.
A stale docstring is a liability — it causes future developers to make wrong assumptions
about what the code is supposed to do.

**Pattern 24 — Benchmark vs actual runtime discrepancy: 3-bottleneck model (found 2026-05-28):**
valid crosses.** False positive — `max(310, ...)` floors at 310 but EMA period starts at
299, so any cross before index 310 is mathematically impossible (no valid EMA there yet).
No bug.

**Rule:** Before delegating, confirm the canonical file path — `search_files` can miss files
that exist. Always verify with `ls` or `wc` in terminal before claiming a file doesn't exist.

**Pattern 25 — Subagent sign-blind inequality claims (found 2026-05-31):**
Subagent claimed `if gap_now > gap_at_cross - MIN_GAP_EXPANSION` was inverted for SHORT
(should be `<`), calling it a HIGH severity bug. Main session trace with concrete values
proved `>` is correct — subagent never traced through negative gap values.

For SHORT, `gap_at_cross` is NEGATIVE (e.g., -0.20), `MIN_GAP_EXPANSION` is POSITIVE (0.10).
`threshold = -0.20 - 0.10 = -0.30`.

With `>` (original code — correct):
- `gap_now=-0.25 > -0.30` → True → block (only 0.05% expansion, insufficient) ✓
- `gap_now=-0.35 > -0.30` → False → pass (0.15% expansion, sufficient) ✓

With `<` (subagent's proposed fix — wrong):
- `gap_now=-0.25 < -0.30` → False → pass (weak expansion allowed, wrong) ✗
- `gap_now=-0.35 < -0.30` → True → block (strong expansion blocked, wrong) ✗

**Root cause:** The subagent evaluated inequality direction abstractly, without substituting
the actual negative sign values that apply to SHORT gaps.

**Rule:** When a subagent reports an inverted inequality in a directional signal,
ALWAYS trace through with concrete sign values for that direction. For SHORT: gap_pct < 0,
so comparisons like `gap_now > -min_gap` (where `min_gap > 0`) mean `-0.25 > -0.20` —
correctly testing "is gap less negative than threshold" (passes) vs "more negative" (blocks).
Always verify with concrete sign traces, not abstract operator reasoning.

This is related to Pattern 2 but different: Pattern 2 = subagent correctly catching an
inverted inequality. Pattern 25 = subagent incorrectly claiming an inequality is inverted
when the signs actually make it correct. Verify with concrete sign traces.

**Pattern 26 — Subagent claims `>=` is inverted for SHORT marginal acceleration (false positive, found 2026-05-31):**
A microbenchmark shows fast execution (8.3s) but actual runs hang for 2+ minutes. The
benchmark only tested the initial GROUP BY queries — it misses the full execution chain.

3 distinct bottlenecks that compound:
1. **Double write**: `save_prices()` called twice in same run — second call is redundant
   (prices unchanged between calls) but still hits the DB
2. **API blocking**: `_seed_universe_candles` makes N Binance API calls with 10s timeout each
   — if Binance is slow, N×10s adds up fast
3. **Timer conflict**: overlapping systemd timers competing for the same DB files —
   one holds WAL lock while another times out waiting

**Rule:** When diagnosing timeout discrepancies, always trace the FULL execution flow
from main() entry to exit. Identify every function that touches the DB or makes external
calls. Microbenchmarks are only valid for the specific code path they measure — they don't
capture the interaction between sequential phases. The missing time is usually in the
phases the benchmark didn't test:
- Per-token loop overhead after GROUP BY
- Double-writes (same function called twice)
- External API calls with long timeouts
- Lock contention from concurrent processes

**Debugging approach:** Run with timing split across phases, instrument each phase:
```python
t0 = time.time(); fetch_all_prices(); print(f'fetch: {time.time()-t0:.1f}s')
t0 = time.time(); save_prices();       print(f'save1: {time.time()-t0:.1f}s')
t0 = time.time(); _aggregate_tf(...);   print(f'agg:  {time.time()-t0:.1f}s')
t0 = time.time(); save_prices();       print(f'save2: {time.time()-t0:.1f}s')  # should be ~0
t0 = time.time(); _seed_universe();    print(f'seed:  {time.time()-t0:.1f}s')  # often the culprit
```

See: `references/rs-py-audit-2026-06-03.md`

**Pattern 30 — Docstring says "weighted by touch count" but code does simple average (found 2026-06-03):**
`_cluster_levels` docstring says "Each cluster is replaced by its average price weighted by
touch count." The code at lines 170 and 181 computes `sum(p for p, _ in cluster) / len(cluster)`
— a simple unweighted mean. Touch counts are summed at line 182 (`total_count`) but never
used in the price averaging. This is a docstring/code mismatch, not a logic error (simple
average clustering is a valid approach), but the docstring misleads future readers.

**Rule:** When updating a function's implementation, update its docstring immediately.
A stale docstring is a liability — it causes future developers to make wrong assumptions
about what the code is supposed to do.

See: `references/price-collector-timeout-2026-05-28.md`
A subagent reported "hotset.json has entries but no trades fire" and listed multiple
possible causes (flags, blacklist, open positions). The investigation traced through signal_compactor,
found PRESERVE-APPROVED-UPSERT path WAS creating APPROVED rows, decider_run WAS firing trades.
The real bug: `brain.py` rejects at `HL_MIN_NOTIONAL_USDT` gate (amount_usdt=3.5 < HL_MIN=11.0).
The DB and pipeline were fully working — the block was at the Hyperliquid API minimum notional
gate, not the Hermes signal layer.

**"use `replace_all=True` on large files corrupts them"** — should be added as a hard rule since it already exists for hl-sync-guardian/brain/position_manager but wasn't documented for accel_300

**Rule:** Never use `replace_all=True` on files >500 lines. Always do targeted single-location patches. If corruption occurs, revert with `git checkout -- scripts/<file>.py` and re-apply as separate targeted patches. This is especially critical for hl-sync-guardian.py, brain.py, position_manager.py, and accel_300.py which are all 300+ lines. This rule was already documented for some large files but not consistently — add it to the general patching discipline.

**Pattern 42 — Self-fixing: first patch used wrong inequality for LONG, had to correct (found 2026-06-08):**
When implementing the gap expansion gate for both directions, the first patch used `>` for both LONG and SHORT. A Python trace with concrete values revealed LONG was inverted:
```
LONG (wrong): gap_now > gap_at_cross - EXPANSION
  gap_now=0.15 > 0.19 → False → pass  ← SHOULD block (contracting)
LONG (correct): gap_now < gap_at_cross - EXPANSION
  gap_now=0.15 < 0.19 → True → block ✓
```
The initial implementation blindly copied the SHORT inequality operator to LONG without tracing signs.

**Rule:** When implementing a gate for both LONG and SHORT, always write Python one-liners to verify BOTH directions with concrete positive AND negative values before applying the patch. Do the trace BEFORE patching, not after.

**Pattern 43 — Chop filter EMA angle check silently skipped when EMA value is None (found 2026-06-08):**
The chop filter's EMA angle sub-check uses hardcoded `ema_lookback = 50`. The outer guard is `cross_bar >= 50`, which should ensure `ema300[cross_bar - 50]` is non-None (EMA300 warmup is 300 bars). But if `ema300[cross_bar - 50]` is `None` (data gap), the angle check is silently skipped — the signal proceeds without EMA angle validation.

**Rule:** When a guard condition has an exception clause that skips rather than blocks, ask: what does "skip" mean? Prefer explicit `continue` in the exception branch rather than letting the signal proceed by default. A data gap should block the signal, not bypass the filter.

**Pattern 40 — Subagent flags `abs()` as unguarded, but it's inside a `None` check block (found 2026-06-07):**
Subagent reported HIGH severity: `abs(gap_pcts[newest_idx])` at lines 374-377 could TypeError crash if the value is `None`. The subagent read these lines in isolation and concluded they were unguarded.

Main session trace: lines 374-377 are INSIDE the block `if gap_pcts[newest_idx] is not None:` which starts at line 361. The subagent misread the scope — it saw the None check at the top of the stale gate section but didn't trace that it also covers the `abs()` call.

```python
# Subagent's view (incorrect — flags lines 374-377 as unguarded):
abs(gap_pcts[newest_idx])   # ← flagged as potentially None

# Actual code structure:
if gap_pcts[newest_idx] is not None:   # line 361
    ...
    if newest_gap < signal_gap * THRESHOLD:   # line 374
        abs(gap_pcts[newest_idx])              # INSIDE the guard, safe
```

**Rule:** When a subagent reports an unguarded access, verify the full scope of all conditional branches that guard it. The bug may be real (access outside the guard) or the subagent may have misread which `if` block contains the access. Read the full function around the flagged line to confirm the actual control flow.

**Pattern 41 — Subagent flags SHORT `>` inequality as inverted (false positive, found 2026-06-07):**
Subagent reported the SHORT gap expansion gate: `if gap_now > gap_at_cross + MIN_GAP_EXPANSION: continue` — claimed it should be `<` (inequality inverted).

Main session concrete trace with actual negative SHORT values:
```
gap_at_cross = -0.20  (cross was below EMA — negative)
MIN_GAP_EXPANSION = 0.00
threshold = -0.20 + 0.00 = -0.20

gap_now = -0.25:  -0.25 > -0.20 → False → pass ✓  (0.05% expansion, correct)
gap_now = -0.15:  -0.15 > -0.20 → True  → block ✓ (gap contracting toward EMA, wrong)
```

The `>` operator with negative values tests "is the gap less negative than the threshold" — correctly blocking when the gap is contracting toward EMA. The subagent applied abstract `>/<` reasoning without substituting the actual negative sign values.

**Rule:** When a subagent reports an inequality is inverted for a directional signal, ALWAYS trace through with concrete sign values for that direction. For SHORT: gap_pct < 0. `>` means "gap is less negative" (contracting → block). `<` means "gap is more negative" (expanding → pass). Verify with concrete negative values, not abstract operator logic.

**Pattern 45 — Parameter initialized inside function shadows passed-in value (found 2026-06-12):**
`_close_orphan_paper_trade_by_id(lev=1)` at line 2676 initialized `lev = 1` as a local variable INSIDE the function. When `amount_usdt_override` was provided (orphan path), the `elif conn_lookup:` branch was skipped — `lev` stayed at 1 instead of using the passed-in `int(lev)` value from `hl_pos`. The parameter was shadowed and lost.

```python
# WRONG — lev=1 shadows the function parameter
def _close_orphan_paper_trade_by_id(..., lev, ...):
    ...
    lev = 1  # ← BUG: shadows passed-in lev when amount_usdt_override is not None
    if amount_usdt_override is not None:
        amount_usdt = float(amount_usdt_override)
    elif conn_lookup:
        ...  # lev read from DB here — but elif is SKIPPED when override provided
        lev = float(row[1] or 1)
```

Fix: remove `lev = 1`. The parameter's passed-in value is correct for the orphan path (int from `hl_pos`); DB lookup only needed when `amount_usdt_override` is None.

**Pattern 46 — `'pos_data' in dir()` is the wrong idiom for checking local scope (found 2026-06-12):**
Subagent flagged `'pos_data' in dir()` at line 1282 as a potential issue. `dir()` returns local variable **names**, not a dict of values. `'pos_data' in dir()` happens to work because Python creates a local binding on assignment, but it's fragile. `hasattr()` or direct reference is better.

More importantly: `pos_data` is the for-loop variable from `for coin, pos_data in hl_pos.items():` — it's provably always in scope at line 1282. The safest fix is to just use `pos_data.get('size', 0)` directly with no guard.

```python
# WRONG — dir() check is fragile and unnecessary
_sz = float(pos_data.get('size', 0)) if 'pos_data' in dir() else 0

# CORRECT — pos_data is the loop variable, always in scope
_sz = float(pos_data.get('size', 0))
```

**Pattern 47 — Stale self-close branch referenced variables before definition (found 2026-06-12):**
When refactoring `if entry_delta > 0.001 or direction_changed:` into two explicit branches, `_upsert_self_close(coin, direction, sz, entry_px, new_sl, new_tp)` was called with `new_sl`/`new_tp` — but these were defined INSIDE the original `if` block (after the stale check). The branches need to use `record['sl_price']` directly, not `new_sl`/`new_tp`.

```python
# WRONG — new_sl/new_tp defined after the stale check branches
if entry_delta > 0.001:
    _upsert_self_close(coin, direction, sz, entry_px, new_sl, new_tp)  # ← undefined
    continue

# CORRECT — use values already loaded from record at line 3062
if entry_delta > 0.001:
    _upsert_self_close(coin, direction, sz, entry_px, record['sl_price'], record['tp_price'])
    continue
```

Also confirmed: the dead code block (ATR computation) after the `continue` at the stale check was unreachable — that was the original code's structure and it was intentional (the `continue` was there to skip the ATR recompute). The refactor preserved this correctly.

**Pattern 48 — Unreachable dead code after `continue` in hl-sync-guardian (found 2026-06-12):**
Lines 3101-3116 in hl-sync-guardian.py: after `if direction_changed: ... continue` at line 3100, a full ATR/SL/TP recompute block was unreachable (would never execute). `real_atr` referenced there was defined in the `else` branch below. The fix: delete the unreachable block entirely. Always check for dead code that follows a `continue` statement inside an `if` block.

**Pattern 49 — Function return tuple not unpacked at call site (found 2026-06-12):**
`_poll_hl_fills_for_close()` returns `(wavg_exit_px, realized_pnl)` — a 2-tuple. At line 4198 (pending retry path), the call was:
```python
hl_exit = _poll_hl_fills_for_close(token, close_start_ms)  # returns tuple!
_close_orphan_paper_trade_by_id(..., hl_exit, ...)        # passes tuple as scalar
log(f'... HL exit={hl_exit:.6f}')                        # format error on tuple
```
Python raises `TypeError` on `tuple.__format__`. The call site must unpack:
```python
hl_exit_px, realized_pnl = _poll_hl_fills_for_close(token, close_start_ms)
```
Rule: always verify that multi-return functions are correctly unpacked at every call site. A function that returns a tuple and is used as a scalar will fail at the `.format()` call or the first arithmetic operation.

**Pattern 50 — Duplicate guard SELECT missing `direction` filter (found 2026-06-12):**
hl-sync-guardian.py lines 1176-1177: the PostgreSQL duplicate guard queried:
```sql
SELECT id, signal FROM trades WHERE token=%s AND status='open' AND signal NOT IN ('pump_hunter')
```
No `direction` filter. The UPDATE at line 1197 then used the orphan HL coin's `direction` — which may differ from the existing paper trade's direction. If guardian sees a LONG HL position but a SHORT paper trade exists, the guard fires and corrupts the SHORT record with LONG direction.

Fix: SELECT the direction from the matched trade and use it:
```sql
SELECT id, signal, direction FROM trades WHERE token=%s AND status='open' AND signal NOT IN ('pump_hunter')
```
**Pattern 51 — `f.get('dir')` not defensive against `None` in fill-polling (found 2026-06-12):**
All 5 fill-polling list comprehensions in hl-sync-guardian.py used `str(f.get('dir', ''))`.
If `dir` key exists but value is `None`, `str(None)` → `'None'` and `'Open' in 'None'` is False
(safe but implicit). Defensive fix:
```python
'Open' in str(f.get('dir') or '')   # explicit None-coercion
'Close' in str(f.get('dir') or '')
```
Occurrences: lines 519, 893, 914, 2600 (all in hl-sync-guardian.py).

**Pattern 52 — Subagent times out on hl-sync-guardian despite batch split (found 2026-06-13):**
Subagent with 1200s timeout and 9 API calls timed out on hl-sync-guardian audit.
Prior 2026-06-12 rule said "split into 2 batches" — followed, still timed out.
Subagent context serialization overhead makes it unsuitable for files >1500 lines regardless
of batch splitting. Lesson: once a file consistently times out subagents, stop delegating it.
Rule: audit hl-sync-guardian.py entirely in the main session. Use subagent only for
smaller files (<1000 lines) that don't change often.

**Pattern 53 — Crash site never visible without traceback logging (found 2026-06-13):**
`sync_pnl_from_hype` logged "unsupported operand type(s) for -: 'float' and 'str'" for
~10 hours across dozens of cycles. The except handler only logged the exception message,
not the traceback — the crash site was never visible. Multiple wrong guesses were made
about where the `float - str` error occurred (unrealizedPnl, entryPrice, compute_live_pnl).
Fix: add `import traceback; tb = traceback.format_exc()` to every except handler that
logs a generic error message. The traceback showed the real crash site in <5 minutes.
```python
except Exception as e:
    import traceback
    tb = traceback.format_exc()
    log(f'  sync_pnl_from_hype failed: {e}', 'FAIL')
    log(f'  Traceback: {tb}', 'FAIL')  # ← this shows exactly where
```
Rule: always add traceback logging to outer exception handlers for functions that
process external API data. The crash message alone is never sufficient to localize
the error site.

**Pattern 55 — Intermediate variable undefined after early-exit path (found 2026-06-14):**
`cand_signal` in rs.py lines 691-754 (resistance path). The variable was only defined inside
the `else: bounces` block (lines 695-751) but used at line 753 OUTSIDE that block. Two early-exit
paths reached line 753 with `cand_signal` undefined:
1. `touch_count > RS_TOUCH_HARD_CAP` → `nearest_resistance = None` (line 694)
2. `bounces == False` → `nearest_resistance = None` (line 701)

Fix: initialize `cand_signal = None` before the bounces gate so it's always in scope.
```python
# WRONG — cand_signal only defined inside else: bounces block
if not bounces:
    nearest_resistance = None
else:
    cand_signal = { ... }   # defined here only
# Line 753 uses cand_signal — undefined if bounces was False
if cand_signal is not None and ...:  # NameError if bounces=False

# CORRECT — always initialize before the conditional
cand_signal = None  # always in scope
if not bounces:
    nearest_resistance = None
else:
    cand_signal = { ... }
if cand_signal is not None and ...:  # safe — None if bounces was False
```

**Rule:** When a variable is used after a conditional block, always initialize it before the
condition so all paths (early-exit and normal) have it in scope.

**Pattern 56 — Bounce follow-through compared to candle close instead of level (found 2026-06-14, extended 2026-06-17):**
`_bounce_confirmation` in rs.py lines 286 and 295. The follow-through check was:
```python
# WRONG — compares to candle close, not the level
if next_close > c['close'] * 1.00025:   # LONG
if next_close < c['close'] * 0.99975:   # SHORT
```
With `touch_thresh = 0.2 * ATR = 0.2%` for ATR=1.0, a candle can be 0.2% away from the
level and still confirm bounce with only a 0.025% move above ITSELF — an 8:1 scale mismatch.
The next candle could stay 0.175% away from the actual level yet still satisfy the test.

Fix: compare to the level itself:
```python
# CORRECT — compares to level, not candle close
if next_close > level * 1.00025:   # LONG
if next_close < level * 0.99975:   # SHORT
```
Now the next candle must move 0.025% beyond the LEVEL to confirm. Both the touch
(`touch_thresh`) and the follow-through (`level * 1.00025`) are expressed relative to the
same anchor (the level), so they're properly calibrated.

**Rule:** When a bounce confirmation has a "touch" threshold and a "follow-through" threshold,
both must be expressed relative to the same anchor (the level). If comparing to the candle's
close, the scale is likely wrong. Always express both relative to the structural level.

**Pattern 57 — Forward lookahead array construction makes swing-high check self-comparison (found 2026-06-17):**
`_find_swing_highs_lows` in rs.py used:
```python
forward_high = np.append(roll_high[window:], np.full(window, np.nan))
```
This makes `forward_high[i] = roll_high[i]` for all valid i, so the swing-high condition
`highs[i] >= forward_high[i]` reduces to `highs[i] >= roll_high[i]` — a self-comparison
identical to the already-satisfied left side of the `and`. The forward lookahead constraint
("no higher price in the window ahead") is completely bypassed.

Fix: `forward_high[i]` should be `max(highs[i+1:i+window+1]) = roll_high[i+window]`:
```python
forward_high = np.concatenate([roll_high[window:], np.full(window, np.nan)])
```
Now `forward_high[i] = roll_high[i+window]` — correctly looks ahead by `window` positions.

**Rule:** When implementing rolling window forward lookahead with NumPy, verify the array
index algebra with a concrete small example (window=3) before committing. The off-by-one
is easy to get wrong and the self-comparison bug produces no error — swing highs are just
silently less accurate.

**Pattern 58 — Recency score inflation when candle count < RS_RECENCY_WINDOW (found 2026-06-17):**
`_build_level_touches` in rs.py: when `n < RS_RECENCY_WINDOW`, the else branch set
`recency_touches = total` and `ancient_touches = 0`, giving `recency_score = total * K`.
A level with 20 touches in 50 candles scored 60 instead of 20. All touches were treated
as recent and multiplied by K when there weren't enough candles to define a recency window.

Fix:
```python
if n >= recent_cutoff:
    recency_touches = int(touch_mask[-recent_cutoff:].sum())
    ancient_touches = total - recency_touches
else:
    # Not enough candles to define an "ancient" window — all touches are recent
    recency_touches = total
    ancient_touches = 0
```

**Pattern 59 — Resistance bounce SHORT blocked by broken-LONG killswitch (found 2026-06-17):**
When `RS_BROKEN_RESISTANCE_LONG_ENABLED=False`, the broken-path killswitch zeroed
`nearest_resistance`. The bounce SHORT path then saw `nearest_resistance is None` and
silently discarded the correctly-constructed bounce SHORT signal. The killswitch was for
*broken-resistance LONG* (counter-trend trap), but it also suppressed the *bounce SHORT*
path — a valid mean-reversion entry.

Fix: remove the `RS_BROKEN_RESISTANCE_LONG_ENABLED` check from the bounce SHORT path
entirely. The bounce SHORT is a valid standalone signal independent of whether the
broken-resistance LONG path is enabled.

**Rule:** When a killswitch is shared between a "broken level" path and a "bounce" path,
verify the killswitch doesn't accidentally gate the bounce path. A bounce confirmation
from a structural level is a valid signal independent of whether broken-level paths are
enabled.

**Pattern 60 — Recency bonus formula uses (K-1) instead of K numerator (found 2026-06-17):**
`_compute_confidence` in rs.py used:
```python
recent_fraction = min(1.0, (recency_score - touch_count) / (recency_score + 1e-9))
```
With K=3, this equals `recent×(K-1)/recent×K = 2/3` even for 100%-recent levels.
Recency bonus capped at ~5 instead of the intended ~8.

Fix: derive recent_touches from recency_score first, then compute the fraction:
```python
_k = RS_RECENCY_BOOST_K
recent_touches = (recency_score - touch_count) / max(1e-9, _k - 1)
recent_fraction = min(1.0, recent_touches * _k / (recency_score + 1e-9))
```

**Rule:** When a composite score encodes multiple weighted components (recent×K + ancient),
derive the underlying component counts before computing ratios. Using the composite score
directly in a ratio produces the wrong denominator effect.

**Pattern 61 — Support reclassification sets bounces=True without re-confirmation (found 2026-06-17):**
After detecting a broken support that has since recovered (`broken and price > level`), the
code set `bounces = True` without calling `_bounce_confirmation`. Resistance reclassification
correctly called `_bounce_confirmation` again. Support was inconsistent.

Fix: after reclassification, re-call `_bounce_confirmation` to verify:
```python
if broken and price > level:
    broken = False
    bounces = _bounce_confirmation(candles, level, 'LONG', atr_value=atr)
```

**Rule:** When reclassifying a broken level as a bounce, always re-confirm the bounce
rather than assuming it. The level's broken state was detected under different price
conditions — recovery above the level doesn't guarantee the next candle confirmed the bounce.

**Subagent batch dispatch: 600s timeout insufficient for single-file audits (found 2026-06-17):**
6 subagents dispatched in parallel to audit rs.py (~950 lines) in batches of ~150 lines each.
2 of 6 batches timed out at 600s despite well-scoped checklists. Root cause: subagent
context serialization + file-read overhead for even moderate complexity can exceed 600s.
Re-dispatch with tighter focus (explicit line ranges, fewer cross-references, shorter checklist)
completed successfully in 70-500s per batch.

Updated dispatch rule: for single-file audits, give subagent explicit `offset/limit` line
ranges for each read_file call AND cap the checklist at 5-6 specific items. For files
>500 lines with complex cross-references, always do the audit in the main session directly.

**Subagent 70s completion on 938-line file — scope focus matters more than line count (found 2026-06-14):**
rs.py (938 lines) was fully audited by subagent in 70s — did NOT time out. The key
difference from prior timeouts: the subagent was given a focused checklist of 8 specific
items (bounce thresholds, cand_signal scope, recency_by_level, broken level logic, signal dict
completeness) instead of a vague "audit this file for bugs." The subagent's context was
tightly bounded to what it needed to verify.

Rule: For single-file focused audits, give the subagent a numbered checklist of specific
things to verify rather than "audit for all bugs." The checklist limits context scope
and prevents the subagent from wandering into excessive file reads. Target: < 500 lines
of output instructions, 8-10 specific check items maximum.

**Pattern 54 — HL fill list comprehensions need float coercion on sz/px/closed_pnl (found 2026-06-13):**
`_poll_open_fills_once` and `_poll_close_fills_once` compute wavg using `f['sz']` and
`f['px']` directly in arithmetic. HL API returns these as strings in some error cases.
The existing `str(f.get('dir'))` fix addressed `dir` but not `sz`/`px`/`closed_pnl`.
```python
# WRONG — crashes if HL returns string sz or px
total_sz = sum(f['sz'] for f in token_opens)
wavg_open = sum(f['px'] * f['sz'] for f in token_opens) / total_sz

# CORRECT — always coerce before arithmetic
total_sz = sum(float(f['sz']) for f in token_opens)
wavg_open = sum(float(f['px']) * float(f['sz']) for f in token_opens) / total_sz
```
Same for `closed_pnl` in close fills: `float(f.get('closed_pnl', 0) or 0)`.
Occurrences: `_poll_open_fills_once` lines 893-894, `_poll_close_fills_once` lines 914-916.

**hl-sync-guardian.py NEVER delegate to subagent (found 2026-06-13):**
Despite the 2026-06-12 rule splitting hl-sync-guardian.py into 2 batches, the subagent
timed out again at 600s on a simple 9-API-call audit. Root cause: the subagent's
context-serialization + file-read overhead scales super-linearly with file size (4250 lines).
The file is too large and too frequently patched for subagent delegation to work reliably.
Rule: audit hl-sync-guardian.py entirely in the main session. Use subagent only for
smaller files (<1000 lines) that don't change often. For the guardian specifically:
- Main session: read sections directly with offset/limit pagination
- Syntax check: always `python3 -m py_compile` before restart
- Bug pattern search: grep/terminal is faster than subagent for this file
- Restart: kill all processes, clear log, start fresh, verify 2 clean cycles

**Pattern 52 — Subagent times out on hl-sync-guardian despite batch split (found 2026-06-13):**
Subagent with 1200s timeout and 9 API calls timed out on hl-sync-guardian audit.
Prior 2026-06-12 rule said "split into 2 batches" — followed, still timed out.
Subagent context serialization overhead makes it unsuitable for files >1500 lines regardless
of batch splitting. Lesson: once a file consistently times out subagents, stop delegating it.

**Bug B false positive (2026-06-12):** Subagent reported `_sweep_blocklist_trades` missing `_save_closed_set()`. Main session verified: `_save_closed_set()` IS called at line 2893. Subagent misread the code. Always grep/verify before accepting.

**brain.py and signal_compactor.py clean (verified 2026-06-12):** Subagent audit confirmed:
- `add_trade()` correctly uses actual HL fill price (`result.get("hl_entry_price")`) for both `entry_price` and `hl_entry_price` — not signal_price
- Confluence gate at lines 571-589 requires 2+ types — correct
- Accel-300 standalone bypass at 585-590 is intentional (not a bug)
- `breakout` source exempt at 1572-1573 is intentional

**position_manager.py clean (verified 2026-06-12):** The `_in_profit` bug existed only in `_compute_dynamic_sl` (dead code, zero callers). The live ATR path via `tpsl_utils.compute_atr_sl_tp` is clean. `_persist_atr_levels` correctly writes both `stop_loss` and `target` to DB.

- `references/ai-engineer-delegation-2026-06-11.md` — successful 96s delegation; exact line ranges + prior fixes + trade timeline + DB schema = no timeout; good delegation hygiene rules
- `references/audit-surface-pattern-vs-purpose-2026-06-24.md` — full Pattern 62 reproducer: hebbian_learner.py false positive, docstring/main()/git-log verification discipline, code-review trap (not just subagent)
- `references/ai-engineer-hebbian-audit-2026-06-24.md` — full session log: dual subagent audit, main-session verification discipline (grep/sqlite3/python), T's ALL_CAPS = coin signal channel design constraint, plan evolution v1→v2→v3 (1 architectural pivot: "delete" → refactor-and-integrate)
- `references/ai-engineer-session-2026-06-12.md` — hl-sync-guardian.py 11 fixes verified; 4 bugs found; Bug B false positive confirmed; brain.py/signal_compactor.py/position_manager.py all clean
- `references/signal-pipeline-audit-2026-07-13.md` — 12-script cron audit, zero bugs found; P0 blacklists intact; recent-fix baseline re-verified; canonical patterns documented
- `references/rs-py-audit-2026-06-17.md` — rs.py full audit: 10 bugs (4 HIGH), forward lookahead self-comparison, recency inflation, broken-LONG killswitch blocking bounce SHORT, CLI tuple unpacking, etc.
- `references/rs-py-audit-2026-06-14.md` — rs.py: cand_signal NameError fix, bounce detection scale fix, subagent 70s completion on 938 lines
- `references/hl-sync-guardian-june-2026-fixes.md` — 6 bugs fixed in one session: SELF-CLOSE stale TP/SL restructure, undefined trigger_reason, speed_data['updated_at'] float coercion, unrealizedPnl NaN guard, compute_live_pnl crash, HL fill arithmetic not coerced. Key lesson: audit hl-sync-guardian.py in main session only — subagent times out every time.
- `references/accel-300-june-2026-fixes.md`

**Pattern 44 — Confluence gate starves the pipeline: 2+ types required, no bypass (found 2026-06-08):**
signal_compactor.py lines 571-589 require `unique_signal_types >= 2` — no exceptions, no bypass. Pure single-source signals (accel-300+, rs-r136, etc.) always blocked at compaction.

Investigation: 6,597 `accel-300+` signals written to DB in 24h (confidence 70-88%) — detection is fine. Every cycle: "Approved signals: 0", hot-set empty. Gap is at the compactor, not detection.

Root cause chain:
1. signal_schema.py add_signal() has 5-min merge window — signals from different scripts (accel_300 vs rs) running 6+ min apart never combine
2. _signal_type_key() collapses rs-r136 and rs-r50 to `rs` — RS+RS counts as 1 unique type at confluence gate
3. Result: signals write to DB but never survive compaction → hot-set empty → no trades

Fix paths:
- Option A (surgical): Add accel-300 to a standalone-ok bypass list in signal_compactor.py — bypass 2-type requirement for this signal
- Option B (correct but bigger): Widen the 5-min merge window OR tighten the script run cycle so signals combine

**Rule:** When "signals write to DB but hot-set stays empty," problem is NEVER detection params — it's always at compactor or below. Check order: (1) Are signals written to DB? (2) Is compactor verbose showing "only 1 unique type — need 2+" blocks? (3) Is merge window too narrow for cross-script combining? (4) Is _signal_type_key() collapsing distinct types? Never chase detection params when compactor is blocking everything.

**Pattern 42 — Self-fixing: first patch used wrong inequality for LONG, had to correct (found 2026-06-08):**

---

**Pattern 31 — Regime slope hardcoded in accel_300.py (found 2026-06-06):**
`ACCEL_300_REGIME_SLOPE_PCT` was hardcoded at lines 410/413 as `0.015` (both LONG and SHORT).
This constant MUST be in `hermes_constants.py` so it can be tuned without code changes.
Fix: add `ACCEL_300_REGIME_SLOPE_PCT` to hermes_constants (line ~477), import it in
accel_300.py, replace both `0.015` literals with the constant reference.

**Pattern 32 — Always scan ALL tokens for regime, not just top-10 (found 2026-06-06):**
Analysis of just ETH/AVAX showed slopes 0.008-0.011%/bar (below 0.015 threshold) → assumed
market was flat. Scanning all 87 fresh tokens revealed 81 have meaningful slopes (>0.008).
ETH/AVAX are flat; the market is actually heavily SHORT-biased (-0.04 to -0.08%/bar).
Top-coins analysis gave a false picture. Always scan the full universe before concluding
"market is choppy."

**Pattern 33 — accel_300+ LONG is fundamentally broken by RS confirmation (found 2026-06-06):**
96h trade analysis: accel-300+ LONG = 45 trades, 22.2% WR, avg -0.41%.
All 45 required RS-confirmed levels. 0 trades on rs-broken levels.
RS-confirmed signals for accel-300+ are catastrophic.
RS-confirmed signals for accel-300- SHORT are also bad (37.5% WR, -0.00%).
RS-broken signals for accel-300- SHORT are the best (53.2% WR, +0.20%).
Root cause: confirmed RS levels = range-bound consolidation zones = weak momentum = bad for
accel model. Broken RS levels = support/resistance invalidation = strong momentum = ideal
for accel. The RS confirmation filter is selecting against the best signals.

**Pattern 34 — accel_300 data format: dicts not tuples (found 2026-06-06):**
`_get_1m_prices()` returns `list[dict]` with keys `{'timestamp', 'price'}` — NOT
`list[tuple]`. Every debug/trace script that treats prices as `[p for (ts, p) in prices]`
or `prices[i][1]` will silently get wrong values or crash. Always use
`prices[i]['price']` and `prices[i]['timestamp']`.

**Pattern 35 — Stale gate inequality `>= 0` vs `> 0` (found 2026-06-07):**
Stale gate checks newest bar gap against 0 with the wrong operator:
```python
# WRONG — equality (gap == 0) allowed through for LONG
if direction == 'LONG' and gap_pcts[newest_idx] >= 0: continue

# CORRECT — strictly positive required
if direction == 'LONG' and gap_pcts[newest_idx] <= 0: continue
```
A gap of exactly 0 at the newest bar would incorrectly pass the stale gate for LONG.
Always use `< 0` (not `<=`) for the "must be above EMA" check on the newest bar.

**Pattern 36 — Gap decay check prevents stale pullback signals (found 2026-06-07):**
With gap_growth and marginal_accel removed as blocking gates, stale signals on fading
trends can fire if the newest bar only barely clears MIN_GAP. Add a decay check:
```python
STALE_GAP_DECAY_THRESHOLD = 0.50  # newest gap must be >= 50% of signal bar gap
signal_gap = abs(gap_pcts[i]) if gap_pcts[i] is not None else 0
newest_gap = abs(gap_pcts[newest_idx])
if signal_gap > 0 and newest_gap < signal_gap * STALE_GAP_DECAY_THRESHOLD:
    continue  # gap collapsed 50%+, stale pullback — block
```
This catches cases where gap went from 3% (signal bar) to 0.1% (newest bar) while
still technically above MIN_GAP.

**Pattern 37 — Shortcut gate asymmetry: SHORT bypasses gap expansion (found 2026-06-07):**
Subagent flagged that accel_300 had different gates for LONG vs SHORT. The gap
expansion gate was present for LONG but absent for SHORT. The asymmetry was
pre-existing but now documented:
```python
# SHORT: gap must be expanding (more negative), not contracting toward EMA
# gap_at_cross is negative (cross was below EMA).
# If gap_now > gap_at_cross + MIN_GAP_EXPANSION, the gap is contracting (less bearish).
if direction == 'SHORT':
    if gap_now > gap_at_cross + MIN_GAP_EXPANSION: continue
```
Both directions need the same gate logic. The SHORT gate was missing entirely.

**Pattern 38 — Cross bar fallback range too narrow (found 2026-06-07):**
The cross bar fallback searched `range(i-1, PERIOD, -1)` where PERIOD=300.
With 600-bar fetches (lookback=600), crosses can occur at index 378 or higher —
outside the 300-bar PERIOD limit. The fallback missed valid crosses.

Fix: search the full available window:
```python
# WRONG — stopped at index 300, missed crosses at 378+
for j in range(i - 1, PERIOD, -1):
    if gap_pcts[j] <= 0: cross_bar = j; break

# CORRECT — searches full window from signal bar back to 0
for j in range(i - 1, -1, -1):
    if gap_pcts[j] is not None and gap_pcts[j] <= 0: cross_bar = j; break
```
Note: The cross bar fallback finds crosses that occurred BEFORE the signal bar
in array order (older in time). Crosses that are NEWER than the signal bar
(bar 378 is newer than bar 242 in array order) are correctly excluded —
the fallback is a backward search, not a forward search.

**Pattern 39 — Loop start < 0 normalizes to 0 in Python range() (found 2026-06-07):**
The signal loop is: `for i in range(n - LOOKBACK_1M, n - 1):`
With LOOKBACK_1M=700 and n=600: `range(-100, 599)` → Python's range()
silently normalizes the negative start to 0. The loop processes bars 0..598
(the entire array), not just the intended last 700 bars.
This means with a 600-bar fetch, the loop iterates the full dataset.
This is NOT a bug — it's how Python's range() works — but it means the
intended lookback constraint is only effective when n > LOOKBACK_1M.

**Rule:** When updating a function's implementation, update its docstring immediately.
brain.py's HL-level rejection gates (amount_usdt, min notional, leverage limits) BEFORE
auditing the DB signal flow. The signal layer can be fully functional while the trade fails
at the exchange integration layer. Always read the actual rejection message from pipeline.log
before assuming the bug is in the signal/approval path.

See: `references/hl-min-rejection-pipeline-desync-2026-05-21.md`

**Updated rule (2026-05-20):** Focused 3-4 bug fix tasks (20 API calls, targeted scope)
can complete successfully in ~400s. The 600s timeout is a floor, not a guarantee of failure.
When giving a subagent a focused fix task (not a full pipeline audit), allow 400-450s
and monitor for completion. Only re-delegate if the subagent explicitly times out —
do not assume timeout will happen from prior experience with DIFFERENT task types.

```python
# WRONG — crashes on Decimal, None, or 0
calc_notional = hl_notional if hl_notional else amount_usdt
computed_pnl_pct = realized_pnl / calc_notional * 100

# CORRECT — explicit float coercion with safe fallback
hl_notional_raw = db_trade.get('hl_notional_usdt')
amount_usdt_raw = db_trade.get('amount_usdt', 50.0)
try:
    hl_notional = float(hl_notional_raw) if hl_notional_raw is not None else None
except (ValueError, TypeError):
    hl_notional = None
try:
    amount_usdt = float(amount_usdt_raw) if amount_usdt_raw is not None else 50.0
except (ValueError, TypeError):
    amount_usdt = 50.0
calc_notional = hl_notional if hl_notional else amount_usdt
if not calc_notional:  # None or 0
    calc_notional = 50.0  # hard fallback — never divide by zero
```

**Rule:** When reading ANY column from PostgreSQL for use in arithmetic, always coerce
to the appropriate numeric type (float/int) before use. Never assume a DB column will
be the Python type you expect — check with a test query:
```python
cur.execute("SELECT column_name, data_type FROM information_schema.columns
             WHERE table_name='trades' AND column_name='...'")
```

**Pattern 12 — Sentinel only ALERTs but doesn't ACT (found 2026-05-17):**
Subagent correctly identified that the sentinel in `close_paper_position()` alerts when
`hype_realized_pnl_usdt < 0` and `is_loss=False`, but the code only printed an ALERT and
did NOT call `set_loss_cooldown()`. The cooldown was still missed despite the detection.
Fix: sentinel must call `set_loss_cooldown(token, direction)` as fallback when it detects
the missed cooldown — alerting without acting is a half-measure.

**Pattern 13 — `_load_closing_markers()` silently accepts wrong type (found 2026-05-17):**
If `guardian-closing-markers.json` was ever written as a raw list `[]` instead of
`{"tokens": {...}}`, `json.load()` returns a list. `data.get('tokens', {})` on a list
raises `AttributeError` (caught, returns `{}`) — silently resetting all closing markers.
The guardian log showed repeated `'list' object has no attribute 'get'` failures.
Fix: validate `isinstance(data, dict)` and `isinstance(tokens, dict)` before returning.

| **ATOM phantom re-entry (2026-05-17) — correct root cause:** | User pushed back on initial analysis. His HL history showed position open for hours — the system must account for that. Correct timeline: (1) Pipeline opened ATOM SHORT 07:36:07 (id=10077, entry=2.1051). (2) Held 2.5h. (3) ATR SL closed at 10:07:05, pnl_usdt=-0.03, hype_realized=-0.1725 (combined HL loss). (4) Guardian detected separate brief position at 10:05:24 (sub-60s window, not in any guardian sync). (5) Spurious LIVE-MISS re-entry at 10:05:26. Key lesson: HL history is ground truth. Never tell T his data is wrong without exhausting every explanation first. | `references/atom-phantom-reentry-2026-05-17.md` |

The bug: `_collect_atr_updates()` had `if is_new_trade or _in_profit` forcing `_entry` as the
SHORT SL anchor whenever the position was in profit. This placed SL ABOVE entry — completely
backwards for a SHORT in profit (SL should be below entry to protect the profit).

Example: DASH SHORT entry=0.017526, price fell to 0.01709 (2.5% profit), `pnl_pct > 0` →
the buggy condition forced `_entry` anchor → `new_sl = 0.017526 × 1.007 = 0.017649` = ABOVE
entry. A 0.8% bounce from current hits SL and closes with tiny profit.

**The fix (VERIFIED correct):** Remove `is_new_trade or _in_profit` condition entirely.
Always use `ref_price` (which equals `_peak_low` for established/profitable SHORTs):

```python
# BEFORE (BUGGY):
if is_new_trade or _in_profit:
    new_sl = round(_entry * (1 + effective_sl_pct), 8)   # WRONG — above entry
else:
    new_sl = round(ref_price * (1 + effective_sl_pct), 8)

# AFTER (CORRECT — always ref_price for SHORT):
new_sl = round(ref_price * (1 + effective_sl_pct), 8)
```

Why `ref_price` is correct for ALL SHORT states:
- **New SHORT** (no peak yet): `ref_price = current_price` (fallback) → `SL = current × (1+sl%)` = above current = protective
- **In-profit SHORT** (price fell): `ref_price = _peak_low` (lowest seen) → `SL = lowest × (1+sl%)` = below lowest = locks in profit correctly
- **Underwater SHORT** (price rose): `ref_price = current_price` → `SL = current × (1+sl%)` = above both entry and current

The `ref_price = _peak_low if _peak_low > 0 else current_price else _entry` fallback chain at
line 1613 handles all three cases correctly without any `_in_profit` gating.

**IMPORTANT:** Do NOT apply `_entry` anchor for in-profit SHORTs — that WAS the bug.
Always use `ref_price`. The trailing-tighten gate (`new_sl < current_sl`) further ensures
only meaningful tighten moves are accepted.

**Verification:** Next cycle's `[ATR]` debug line shows `SL_entry_dist=X.XX%`. For in-profit
SHORTs this should be negative (SL below entry). `anchor=ref_price(_peak_low)` confirms
the correct anchor is being used.

**Note:** `new_tp` for SHORT is correct as-is — TP anchored to `_peak_low` (lowest = best TP
anchor for SHORT) does NOT need the `_in_profit` treatment. Only SL had the bug.

**Audit findings (2026-05-15):** Full trace of all 3 SHORT cases confirmed fix is correct.
Subagent audit of `_compute_dynamic_sl`/`_compute_dynamic_tp` confirmed these are dead code
(zero callers) — SHORT formula bugs in those functions have no live impact.

**Pattern 4 — Stale-comment confidence formula (found 2026-05-13):**
Subagent reports confidence formula comment as stale or wrong. In accel_300.py line 390, comment
said MIN_GAP_PCT=0.10 but actual constant was 0.20. The formula was correct — only the comment
was wrong. This is a recurring bug class: parameter values change but comments don't track them.

Fix: When a subagent reports a wrong formula or stale constant bug, verify the actual constant
value with grep in the main session before accepting. If the code is correct but the comment is
wrong, flag as a stale-comment bug (low severity) with the specific line numbers.

**Pattern 5 — Stale signals persist through regime reversal (verified 2026-05-13):**
Another agent claimed: "Old signals from hours earlier still execute after price regime has completely reversed."

Investigation found the claim is PARTIALLY correct — signals can't persist for hours (5-min staleness cap), but the architectural bug is real:

- `signal_compactor.py` lines 253-266: `reg_mult` is a SCORE MULTIPLIER (0.5x for counter-regime), NOT an exit filter. Counter-regime signals survive preservation passes.
- `_filter_safe_prev_hotset()` lines 1396-1411: Only staleness + confluence + WR are checked. NO regime check.
- `decider_run.py`: Max 30pt penalty for counter-regime, NOT a hard block. High-confidence signals (base conf 85, penalty 30 → 55) can still execute.

The failure scenario: LONG signal enters during LONG_BIAS. Regime flips to SHORT_BIAS 2 min later. Signal is counter-regime but survives staleness. decider_run applies 30pt penalty → signal still clears execution threshold → executes LONG into SHORT_BIAS.

**Live validation (2026-05-13 18:35:** IMX SHORT was open against LONG_BIAS regime (IMX regime=LONG_BIAS conf=17 per candles.db 1m regression). The trade executed at 18:29 with a 2-source combo (accel-300-,rs-r688) despite regime being LONG_BIAS the entire time.

**Fix direction:** `_filter_safe_prev_hotset()` needs a regime alignment filter: if `regime_conf > 60` and direction is counter to current regime, `continue` (don't preserve).

**No HOTSET_TTL constant exists** — staleness at `max(0.0, 1.0 - age_m * 0.2)` (5 min to 0) is the only timer.

**Pattern 11 — Flag guards function entry but NOT internal HL order calls (found 2026-05-17):**
`PUMP_HUNTER_ENABLED=False` blocks `scan_and_fire()` but NOT `_open_pump_position()` — the `place_tp`/`place_sl` calls at lines 671-677 fire whenever the function is called directly, regardless of the flag. Same for cascade_flip: `CASCADE_FLIP_ENABLED=False` at function entry, but `hl_place_sl`/`hl_place_tp` at lines 414-415 are unguarded inside the function body.

**Fix**: Always wrap the actual `place_sl`/`place_tp` calls with `if FLAG and condition: pass` + commented code. The flag at function entry is not sufficient — the internal calls must be individually guarded. This is the root cause of the GALA TP/SL bug (May 2026-05-17).

`_get_1m_prices()` in `ema_angle.py` used `WHERE token=? AND is_closed=1`. PURR had 17,340 rows ALL `is_closed=0` (never closed). 42 tokens had only open (unclosed) candles. These tokens were completely invisible to the signal despite having recent price data.

**Fix:** Remove `is_closed=1` from the query. This is consistent with how most signal scripts use candles.db (rs.py, ma_cross.py, guppy.py all read all rows). The token scan query in the same file was also inconsistent — it used `is_closed=1` while `_get_1m_prices()` did not.

**Also found:** `ABS_ANGLE_FLOOR = 0.003°` universal floor on LONG only (SHORT has no equivalent). PURR's p75=0.002° < 0.003° floor — all LONG signals blocked regardless of legitimacy. Fix: remove floor, use per-token p75 only.

**Pattern 9 — Per-run dedup missing in decider_run hotset loop (found 2026-05-15):**
`execute_all()` in `decider_run.py` iterates `hotset_sorted` (line 967). For each entry,
it calls `execute_trade()` which checks PostgreSQL for open trades (lines 694-702). BUT:
two signals for the same token+direction in the same hotset iterate before the first
INSERT commits. The second iteration's PostgreSQL check reads state as it was BEFORE the
first INSERT — so both pass the duplicate check.

**Fix:** Add `_processed_tokens_this_run = set()` before the loop. Inside the loop, before
`execute_trade()`, skip if `token in _processed_tokens_this_run`. Add token after skip check.

**Verified by subagent (2026-05-15):**
- No existing per-run dedup mechanism exists
- Hotset CAN have duplicate token+direction via signal_compactor merges
- Fix placement inside `for hot_sig in hotset_sorted:` loop, before `execute_trade()`, is correct
- Token-only dedup (not token+direction) over-blocks opposite direction but is safe — capital already deployed makes opposite-direction entry questionable

**DB navigation for this bug:**
- `references/accel-300-audit-2026-05-14.md` — full accel_300.py audit with line-level bugs

**DB navigation for this bug:** PostgreSQL `brain.trades` has live open trades (token, direction, entry_price, created_at, regime=None for recent trades). `signals_hermes_runtime.db` has signal metadata (decision, combo_key, hot_cycle_count, survival_rounds). `signals_hermes.db` is a different DB with candle data (no signals table) — do NOT confuse the two. `candles.db` has 1m candle data for `get_regime_1m()` regression.

- **references/price-collector-timeout-2026-05-28.md** — price_collector 120s+ timeout root cause: double save_prices(), Binance API blocking in _seed_universe_candles, and timer conflict with 1m-candle.timer. Fixed: removed 2nd save_prices, disabled _seed_universe_candles, disabled competing timers. Runtime went from 120s+ to ~80s.

---

## Signal Pipeline Audit Methodology (cron-driven ai-engineer task, confirmed 2026-07-13)

Cron jobs invoke the ai-engineer skill with a flat file list and a checklist. When this fires, the audit is *confirmation*, not exploration — apply this exact playbook to avoid wasted calls.

### Pattern 68 — Signal scripts live in TWO places (found 2026-07-13)

There are TWO parallel sets of signal-generation scripts in Hermes:

1. **Legacy top-level**: `/root/.hermes/scripts/{gap300,ma_cross,ma_fast,zscore_momentum,rs,r2_trend,macd_1m,volume_1m,ma300_candle_confirm,macd_rules,ma_cross_5m,pattern_scanner}_signals.py`
2. **New package**: `/root/.hermes/scripts/signals/*.py` (`ma_cross.py`, `gap_300.py`, `accel_300.py`, `rs.py`, etc.)

The legacy top-level scripts are wired into `signal_gen.py` (the cron entry point) and are the LIVE production code path. The `signals/` package is the refactor target but is not what cron actually runs.

**Rule:** Before auditing a signal script by name, confirm the canonical file path with:
```bash
grep -nE "^from .* import|<signal_name>" /root/.hermes/scripts/signal_gen.py | head -20
```
The file `signal_gen.py` (NOT `signal_runner.py` — that doesn't exist) is the import surface that determines which scripts run. Auditing the wrong file is silent wasted work.

### Pattern 69 — Canonical price_history read pattern (confirmed 2026-07-13)

The CORRECT and CURRENT idiom for reading 1m prices from `signals_hermes.db` is:

```sql
SELECT timestamp, price FROM (
    SELECT timestamp, price
    FROM price_history
    WHERE token = ?
    ORDER BY timestamp DESC
    LIMIT ?
) sub
ORDER BY timestamp ASC
```

The double-subquery is required because the inner `ORDER BY DESC LIMIT N` gets the N most recent rows, and the outer `ORDER BY ASC` reverses them to oldest-first. **The inner SELECT must include `timestamp`** even though the outer only selects `price` and `timestamp` — the outer ORDER BY references it.

Two near-miss bugs from prior cycles:
- Omitting `timestamp` from the inner SELECT crashes with "no such column" on the outer ORDER BY.
- Using `ORDER BY timestamp ASC LIMIT N` directly gives the OLDEST N rows, not the most recent — opposite of what you want.

### Pattern 70 — Synthesize-ohlcv for close-only price_history (confirmed 2026-07-13)

`price_history` is close-only — no open/high/low/volume. Scripts that need OHLCV shapes (RS swing detection, MACD rules, pattern_scanner, ma300_candle_confirm) synthesize:

```python
return [{'open': r[1], 'high': r[1], 'low': r[1], 'close': r[1]} for r in rows]
# or with timestamp for pattern_scanner / macd_rules:
return [{'open_time': r[0], 'open': r[1], 'high': r[1],
         'low': r[1], 'close': r[1], 'volume': 0.0} for r in rows]
```

This is **intentional**, not a bug. Consequences:
- Volume-based confirmation logic is effectively disabled (volume = 0).
- Touch/bounce thresholds using ATR (relative) still work — `c['close']` is real.
- `c['close'] > c['open']` for bullish candle detection is ALWAYS False (equality) — any code branch that depends on this is dead.

When auditing a signal that synthesizes ohlcv, don't flag it as a bug. But DO check downstream callers for branches that rely on `c['open'] != c['close']` or non-zero volume — those are real dead code.

### Pattern 71 — "Missing set_cooldown" is usually a false positive (confirmed 2026-07-13)

Many legacy signal scripts (ma_cross_signals, ma_fast_signals, r2_trend_signals, rs_signals, volume_1m_signals, ma300_candle_confirm_signals, macd_rules, pattern_scanner) do NOT call `set_cooldown()` themselves. They rely on caller-level dedup in `signal_gen.py`:

```python
if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
    continue
```

`MIN_TRADE_INTERVAL_MINUTES = 10` is the token-level cooldown window enforced by `signal_gen.py` BEFORE each scanner is invoked.

**Scripts that DO call `set_cooldown` themselves** (macd_1m_signals, zscore_momentum, ma_cross_5m, gap300_signals-via-state-table) are doing per-token+direction cooldowns *in addition* to the caller-level dedup, not instead of it.

**Rule:** When auditing a signal script and you observe it doesn't call `set_cooldown`, DO NOT flag it as missing. Verify the caller in `signal_gen.py` applies `recent_trade_exists` first. If yes, the absence of `set_cooldown` in the signal script is the established pattern, not a bug.

### Pattern 72 — Signal-pipeline audit checklist (cron playbook, confirmed 2026-07-13)

When a cron job hands you a flat list of signal scripts and a checklist, run this exact sequence. Each step is cheap and eliminates a class of false positives:

```bash
# Step 1: P0 blacklists (always first)
grep -n "SIGNAL_SOURCE_BLACKLIST\|CONFLUENCE_REQUIRED\|LONG_BLACKLIST\|SHORT_BLACKLIST" \
  /root/.hermes/scripts/hermes_constants.py

# Step 2: Syntax check all listed files in parallel
for f in <file1> <file2> ...; do
  python3 -m py_compile "$f" || echo "COMPILE FAILED: $f"
done

# Step 3: DB path correctness — must use _PRICE_DB=/root/.hermes/data/signals_hermes.db
grep -nE "_PRICE_DB|_RUNTIME_DB|_CANDLES_DB" <file>

# Step 4: Price_history query pattern — must be double-subquery, ASC order
grep -n -A 6 "FROM price_history" <file>

# Step 5: set_cooldown + cooldown handling
grep -n "set_cooldown\|recent_trade_exists\|COOLDOWN_FILE\|LOSS_COOLDOWN_FILE" <file>

# Step 6: ohlcv_1m usage (must be ZERO — that table is 7+ days stale)
grep -nE "FROM ohlcv|ohlcv_1m" <file>
# Note: docstring/comment mentions of ohlcv_1m warning against it are OK;
# only actual SQL FROM ohlcv_1m is a bug.

# Step 7: Print statements in hot loops vs. error/summary paths
grep -n "print(" <file>

# Step 8: Caller wiring — confirm signal_gen.py actually imports the script
grep -nE "from <script_module> import|<script_module>\." /root/.hermes/scripts/signal_gen.py

# Step 9: Recent-fix baseline verification (compare against known-good state)
# paths.py: COOLDOWN_FILE defined
# signal_schema.set_cooldown: writes loss_cooldowns.json dict format
# zscore_momentum subquery: includes 'timestamp' in inner SELECT
```

This 9-step checklist completed a 12-script audit cleanly in ~10 minutes in the 2026-07-13 cron run with zero P0/P1 findings. Each step is bounded so a subagent can run them in parallel without timeout.

### Pattern 73 — "Auditor asked the right checklist, found nothing" is a valid outcome (confirmed 2026-07-13)

Cron audits are confirmation checks, not exploration. When the checklist passes cleanly:
- Report PASS for each item with specific line numbers proving the fix is intact
- Don't manufacture findings to justify the audit — explicit "no bugs found" is the correct deliverable
- The recent-fix baseline list (paths.py, signal_schema set_cooldown, zscore_momentum subquery, etc.) MUST be re-verified each audit cycle — fixes can silently regress

The wrong outcome is padding the report with low-severity observations dressed up as bugs ("stale comment potential", "could be cleaner") to look thorough. The user asked for bugs; if there are none, say so plainly with the evidence.
