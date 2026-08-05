---
name: audit-an-existing-plan
title: Plan-vs-Reality Audit
description: "Read-only audit of an existing implementation plan against current source code. Verify every citation (file paths, line numbers, statistics, arithmetic), check internal consistency between sections, catch stale code/data after audits, identify missed fixes, and produce a structured readiness verdict — without modifying the plan or any source files."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [audit, plan-review, verification, preflight, citations, internal-consistency, hermes, code-quality]
    related_skills: [writing-plans, multi-file-refactoring, requesting-code-review]
---

# Plan-vs-Reality Audit

Read-only verification of an existing implementation plan against the actual codebase and live data. The user wrote a plan (or someone else did); you check whether every claim in it still holds before anyone starts implementing.

**Core principle:** A plan is stale the moment it's written. Code moves, audits get applied to one section but not others, statistics get superseded, arithmetic drifts. Treat the plan as a hypothesis to test, not a source of truth.

**This skill vs others:**
- `writing-plans` — for **writing** new plans
- `multi-file-refactoring` Section 3 — about delegating audits and applying fixes (write-then-fix loop)
- `requesting-code-review` — for **reviewing code diffs** before commit
- This skill — for **auditing a plan that already exists** (read-only, no fixes)

## When to Use

- User says "audit this plan", "check this plan for errors", "verify the plan before we implement", "preflight review"
- User hands you an existing plan and asks for inconsistencies, missed fixes, contradictions
- User wants a confidence rating per item, with which-section-line to update
- T's directive style: "Audit only — do NOT modify the plan or any source files"

**Skip for:**
- Plans still being drafted (use `writing-plans`)
- Code review of a diff (use `requesting-code-review`)
- Trading-system-specific debugging (use the trading-category skills)

## Step 1 — Establish Audit Scope

Before reading anything, capture:

1. **Pre-flight verified facts** — what the user says is already known true (constants applied, backups made, files migrated). DO NOT re-verify these. List them up front so you don't waste tokens.
2. **Audit checklist** — what the user wants checked (per-item verdicts? arithmetic? line numbers? consistency?).
3. **Constraint** — read-only. No edits to plan or source. Run scripts but don't patch code.

If the user provides a numbered checklist (e.g. "verify items 1-10"), copy it verbatim into your todo and execute in order.

## Step 2 — Read the Plan in 200-Line Chunks

Plans grow. A 1000-line plan read in two pages will miss late-section contradictions. Chunk:

```python
read_file(path=plan_path, offset=1, limit=200)
read_file(path=plan_path, offset=201, limit=200)
# ... until EOF (verify with wc -l)
```

For each chunk, note:
- **Section headers** (`## SECTION X`) — cross-check naming later
- **Tables and column claims** — Implementation Status tables drift frequently
- **Code blocks** — these need verification against source, line-by-line
- **Statistics with numerators/denominators** — these go stale; track window labels (24h vs 7d vs all-time)

## Step 3 — Verify Citations Against Source

For every "FIX #N: file X, lines A-B" or "constant Y = value Z" claim, run the actual check. The user's reaction to finding a bad citation is worse than the cost of one grep.

### 3a. Line-Range Citations

```python
read_file(path=<cited_file>, offset=<cited_line>, limit=<range>)
```

Match exactly. Note when the plan says "line ~N" vs "exact line N" — only the latter is a hard claim.

### 3b. Constant Values

```bash
grep -n "^CONSTANT_NAME\s*=" /root/.hermes/scripts/hermes_constants.py
```

Confirm plan's stated value matches file's actual value. Especially check after audits claim "9 constants applied" — verify all 9, not just the first 3.

### 3c. Cross-File Usage of a Constant About to Change

**Critical.** Before claiming "safe to change X", grep ALL files that reference it:

```bash
grep -rn "X\b" /root/.hermes/scripts/ --include="*.py" | grep -v "^.*#"
```

If only one file uses it → safe. If multiple files use it → each call site needs verification, and changing the value has multi-file impact.

### 3d. Code-Block Citations

When the plan shows a code block purporting to be the current state ("CURRENT (BROKEN):"), find that block in source. If it doesn't exist, the plan is citing a hallucinated version. Check git log if needed.

### 3e. New-Code Patch Claims

When the plan includes a proposed patch, verify:
- Variable names match the surrounding scope (`i`, `closes`, `ema300` etc.)
- Loop bound math: does the proposed guard (`if last_idx > i`) actually work for the iteration? Trace the actual loop range.
- Imports required by the patch are already imported in the file
- Insertion point is real (line `617` is the `signal_bar = {...}` block?)

## Step 4 — Execute Verification Scripts the Plan Cites

Many plans include their own verification scripts. Run them.

```bash
python3 /path/to/script_cited_in_plan.py
```

Compare the script's output to the statistic in the plan. If plan says "27/121" and script prints "27/121" → confirmed. If they differ → the script was updated but the plan wasn't, OR vice versa.

**Trick:** scripts often have many output rows. Pipe through `awk`/`sort`/`uniq -c` to extract the columns the plan claims. Don't trust the final summary line if you can tabulate the raw rows directly.

## Step 5 — Compute the Plan's Arithmetic

Don't trust the plan's stated math. Verify it.

```python
python3 -c "
lowest = 0.019699
old_sl = lowest * 1.012
new_sl = lowest * 1.005
print(f'OLD SL: {old_sl:.6f}')
print(f'NEW SL: {new_sl:.6f}')
"
```

Especially check:
- Round-off: did the plan show full precision or rounded? Match its claim.
- Sign: SHORT/LONG reverses expectations. For SHORT, positive % moves SL DOWN; negative % moves SL UP.
- Units: if a stat shows "27/121 (22%)", check `27/121 ≈ 0.223 ≈ 22%`. If `27/121 ≈ 22%` but plan says 18%, that's an arithmetic error.

## Step 6 — Check Plan-Internal Consistency

A plan is itself a document with cross-references. Look for:

| Pattern | What to look for | Action |
|---------|------------------|--------|
| **Stale stats** | "15/34 (24h)" in one section, "27/121 (7d)" in another | Flag the older statistic; either update or clearly label the window |
| **Multiple numbering** | Same fix called "Fix #9" here, "Fix #10" there, "D.4" elsewhere | Cosmetic but confusing — note it |
| **Stale code blocks** | Section X still shows pre-audit code despite later audit recommending different | Plan was partially updated. Flag the stale block |
| **Missing risk assessment** | Risk table covers Fix #1-10 but plan now has Fix #11, #12 | Section is stale; flag missing entries |
| **Conflicting orders** | Executive Summary says "apply Fix #12 FIRST"; Section E Phase 1 starts with Fix #1 | Two recommendations contradict |
| **Misleading labels** | Section called "Profit capture ratio" but SQL is just `AVG(pnl_pct)` | Label doesn't match content |
| **Duplicate sections** | Two `## SECTION X` headers, or two stats tables | Rare but possible from copy-paste |
| **Phantom defaults** | Plan says "X=1.0 default" but DB schema says `DEFAULT 0` | Plan paraphrased badly or source mystery; flag as MED |

For each found: record
- **WHERE** in the plan (line range)
- **WHAT** is inconsistent
- **CONFIDENCE** (HIGH = clearly wrong / MED = probably wrong / LOW = could be right, double-check)
- **SUGGESTED CORRECTION** (exact text or arithmetic)

## Step 7 — Audit Application Trace

Plans that cite multiple audits ("Audit #1 confirmed Fix A", "Audit #2 verified constants") — verify the cumulative narrative is coherent.

- Read each audit section
- Check the audit's findings are reflected in the body of the plan
- Look for findings cited but not propagated (audit says "ONLY add ASTER" but body shows "add MERL/ENS/FET/ASTER")
- Check for audit conclusions that contradict each other (Audit #1 says "Diagnosis right but framing wrong", Audit #2 ignores it)

## Step 8 — Produce the Final Report

Structure your findings as:

```
## Per-Item Verdicts
[For each user-requested item: CONFIRMED / NEEDS REVISION / FALSE POSITIVE,
 with line-specific evidence]

## Top 5 Most Important Findings (Priority Order)
[Only the highest-impact issues, with confidence rating]

## Ready-to-Implement Verdicts Per Pending Item
[CLEAR / NEEDS-MORE-REVIEW per fix in the plan]

## Confidence Summary
[HIGH / MED / LOW per finding]

## What I Did / Files Modified
[Proves the audit was real; lists files actually read]
[CRITICAL: must say "None — audit only" if read-only constraint applied]
```

### Severity Tags (Hermes Trading Convention)

When auditing trading-system plans, prefer:
- **HIGH** — actively causes wrong behavior, data loss, or safety risk
- **MED** — defined but never enforced, or stale logic
- **LOW** — cosmetic, label, or comment mismatch

## Pitfalls

### Stale Section Syndrome (the #1 finding in plan audits)

After an audit runs and modifies one part of a plan, sibling sections that referenced the OLD state are almost never updated. Examples:
- Audit adds a fix → Implementation Status table updated → body sections + risk table + decision points NOT updated
- Audit recommends "add X only" → table updated → code-block section left with the multi-X version
- Constant is applied → verification section updated → backup section still lists pre-application values

**Rule:** When an audit recommendation changes a topic, ALL places in the plan that referenced the pre-audit state are stale until updated. Track this with a checklist during audit.

### False-Positive Patterns Auditors Frequently Flag (Hermes-Specific)

Many audit subagents over-flag these as bugs when they're correct. Verify in context before reporting.

| Pattern | What subagent flags | Why it's usually a false positive |
|---------|---------------------|----------------------------------|
| 17 | `pass` in trailing gate leaves flag falsy | Verify the gate's scope; `pass` is often a no-op placeholder, not the bug |
| 21 | Hardcoded SQL literals are placeholders | They're often real filters, not placeholders |
| 25/26 | Sign-blind inequality claims | For SHORT, delta/gap values are negative by design — "growing" means MORE negative |
| 40 | `abs()` flagged as unguarded | Verify the surrounding None-check scope; `abs()` is often inside one |
| 62 | "Redundant/parallel" files | Check docstring/main purpose before concluding duplication |
| 66 | Sibling files with same function names | May be parallel implementations with different signatures — both intentional |

**Always:** When subagent flags one of these, grep the actual call sites to confirm the bug exists in context. If it doesn't → mark FALSE POSITIVE, don't pad the report.

### Reported `bars_stale=0/121` Can Be Misleading

A script may report `bars_stale=0/121` (looks like "nothing is stale") while STILL having wrong-direction trades. That's because "stale" and "wrong-direction" are independent failure modes. Always count wrong-direction trades separately, then within that subset count how many are also stale. See the empirical breakdown:

```
Of N wrong-direction trades:
- M1 have bars_stale > X (caught by STALE_LOOKBACK filter)
- M2 have bars_stale == None (never had a baseline bar — different failure mode)
- M3 have bars_stale <= X but direction reversed (only caught by NEW direction check)
```

This tells you which fix catches how many, which is critical for evaluating "is this fix sufficient?"

### "Audit confirmed = all clear" Is Not Equal to "Audit found everything"

Two separate audits can each be internally consistent and STILL miss:
- The intersection of failure modes
- Sections outside their scope
- Stale sections not in their checklist

Always verify the audit's CHECKLIST against what you were asked to check. If gaps exist, fill them yourself.

### Don't Pad the Report

A long report feels thorough but dilutes signal. Cap it:
- Per-item verdicts: terse, 1-3 lines each
- Top findings: 5 max
- Confidence: only HIGH/MED, drop LOW unless truly uncertain

## Verification Before Returning

Before submitting the report:

- [ ] All user-provided checklist items have a verdict
- [ ] Each NEEDS REVISION entry cites a specific plan line/section
- [ ] Confidence ratings are honest (HIGH only when source is unambiguous)
- [ ] "Files Modified: None — audit only" appears if read-only constraint applied
- [ ] No fabricated output (no invented line numbers, no made-up statistics)
- [ ] Where the plan's own verification scripts existed, the report cites their actual run output
- [ ] Top-5 findings are genuinely the top 5 by impact, not by recency of finding
