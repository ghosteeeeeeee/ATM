---
name: writing-plans
title: Planning & Spikes
description: "Plan, write implementation plans, and run throwaway spikes before committing to a build. Covers plan mode, superpowers-style bite-sized plans, and the GSD decompose→research→build→verdict spike loop."
version: 2.0.0
author: Hermes Agent (writing-plans adapted from obra/superpowers; spike adapted from gsd-build/get-shit-done)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, design, implementation, workflow, documentation, spike, prototype, experiment, feasibility, throwaway, exploration, research, mvp, proof-of-concept, plan-mode]
    related_skills: [subagent-driven-development, test-driven-development, requesting-code-review]
---

# Planning & Spikes

Three related workflows for "think before you build":

1. **Plan Mode** — turn-only: write a plan, do not execute.
2. **Writing Implementation Plans** — produce a comprehensive plan a different agent/human can follow to implement.
3. **Spikes** — throwaway experiments to validate feasibility before committing.

## When to Use Each

| Workflow | Use when... | Output |
|----------|------------|--------|
| Plan mode | User says "plan this", "don't write code yet", or `/plan` | `.hermes/plans/YYYY-MM-DD_HHMMSS-<slug>.md` |
| Writing a plan | Multi-step feature, breaking down for delegation, handing to subagents | A markdown plan with bite-sized tasks, file paths, code, tests |
| Spikes | "Is this even possible?", "compare A vs B", "validate before I commit" | `spikes/NNN-<name>/` with code + README + verdict |

---

## 1. Plan Mode

Use this skill when the user wants a plan instead of execution.

### Core Behavior

For this turn, you are planning only.

- Do not implement code.
- Do not edit project files except the plan markdown file.
- Do not run mutating terminal commands, commit, push, or perform external actions.
- You may inspect the repo or other context with read-only commands/tools when needed.
- Your deliverable is a markdown plan saved inside the active workspace under `.hermes/plans/`.

### Output Requirements

Write a markdown plan that is concrete and actionable. Include, when relevant:

- Goal
- Current context / assumptions
- Proposed approach
- Step-by-step plan
- Files likely to change
- Tests / validation
- Risks, tradeoffs, and open questions

If the task is code-related, include exact file paths, likely test targets, and verification steps.

### Save Location

Save the plan with `write_file` under:
- `.hermes/plans/YYYY-MM-DD_HHMMSS-<slug>.md`

Treat that as relative to the active working directory / backend workspace. Hermes file tools are backend-aware, so using this relative path keeps the plan with the workspace on local, docker, ssh, modal, and daytona backends.

If the runtime provides a specific target path, use that exact path.
If not, create a sensible timestamped filename yourself under `.hermes/plans/`.

### Hermes-Specific: Hot-Set Routing

When the plan involves adding a new signal to Hermes, two files must be updated together:
1. `signals/__init__.py` — register the scanner (import + SIGNAL_REGISTRY entry + `name_to_module` dict)
2. `signal_compactor.py` — add `SIGNAL_SOURCE_WEIGHTS` entries for the new source tags

The pipeline owner is `signal_compactor.py` — NOT "signal_runner.py" or any "runner" variant. The compactor reads signals from the DB and writes hotset.json.

### Interaction Style

- If the request is clear enough, write the plan directly.
- If no explicit instruction accompanies `/plan`, infer the task from the current conversation context.
- After saving the plan, reply briefly with what you planned and the saved path.

---

## 2. Writing Implementation Plans

### Overview

Write comprehensive implementation plans assuming the implementer has zero context for the codebase and questionable taste. Document everything they need: which files to touch, complete code, testing commands, docs to check, how to verify. Give them bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume the implementer is a skilled developer but knows almost nothing about the toolset or problem domain. Assume they don't know good test design very well.

**Core principle:** A good plan makes implementation obvious. If someone has to guess, the plan is incomplete.

### When to Use

**Always use before:**
- Implementing multi-step features
- Breaking down complex requirements
- Delegating to subagents via `subagent-driven-development`

### Plan Structure

A complete plan has these sections, in this order:

1. **Goal** — one-paragraph statement of what success looks like
2. **Context** — current state, relevant code locations, prior decisions
3. **Approach** — high-level strategy and key design decisions
4. **Task breakdown** — numbered, bite-sized tasks
5. **Per-task detail** — exact file paths, complete code, test commands
6. **Verification** — how the implementer knows each task is done
7. **Commit strategy** — when to commit (one per task), conventional commit format
8. **Risks & open questions** — known unknowns, things to revisit

### Bite-Sized Task Rules

- Each task should be completable in 15-30 minutes
- Each task should produce a clean commit
- Tasks should be testable in isolation where possible
- If a task is too big, split it
- Order tasks so each builds on the previous (no forward references)

### Code in Plans

When including code in a plan:

- Include **complete** files for small ones, **complete snippets** for changes to large ones
- Show the full function signature, not just the body
- Include imports
- Use the project's existing style (indent, quotes, naming)
- Prefer showing 5-10 lines of context above/below a change over a tiny diff

### Test Plans

For each task, specify:

- What tests to add (file path, test name, what it asserts)
- How to run them (`pytest path/to/test_x.py::test_y`)
- What existing tests should still pass
- Any new fixtures or test utilities needed

### Verification Checklist

At the end of every plan, include a verification section:

- [ ] All new tests pass
- [ ] Linter clean
- [ ] No regressions in existing tests
- [ ] Manual smoke test (specific commands)
- [ ] Documentation updated (specific files)

### Anti-Patterns to Avoid

- "Implement the feature" — too vague, no test plan, no code
- Skipping file paths — the implementer shouldn't have to grep
- "Add appropriate tests" — what tests? what do they assert?
- "Refactor as needed" — when? what triggers the refactor?
- Multiple unrelated changes in one task — split them
- Forward references ("after task 5, also update X") — fold into the task that introduces X

---

## 3. Spikes

Use this skill when the user wants to **feel out an idea** before committing to a real build — validating feasibility, comparing approaches, or surfacing unknowns that no amount of research will answer. Spikes are disposable by design. Throw them away once they've paid their debt.

Load this when the user says things like "let me try this", "I want to see if X works", "spike this out", "before I commit to Y", "quick prototype of Z", "is this even possible?", or "compare A vs B".

### When NOT to Use

- The answer is knowable from docs or reading code — just do research, don't build
- The work is production path — use the plan workflow (sections 1-2) instead
- The idea is already validated — jump straight to implementation

### If the User Has the Full GSD System Installed

If `gsd-spike` shows up as a sibling skill (installed via `npx get-shit-done-cc --hermes`), prefer **`gsd-spike`** when the user wants the full GSD workflow: persistent `.planning/spikes/` state, MANIFEST tracking across sessions, Given/When/Then verdict format, and commit patterns that integrate with the rest of GSD. This skill is the lightweight standalone version for users who don't have (or don't want) the full system.

### Core Method

Regardless of scale, every spike follows this loop:

```
decompose  →  research  →  build  →  verdict
   ↑__________________________________________↓
                  iterate on findings
```

#### 1. Decompose

Break the user's idea into **2-5 independent feasibility questions**. Each question is one spike. Present them as a table with Given/When/Then framing:

| # | Spike | Validates (Given/When/Then) | Risk |
|---|-------|----------------------------|------|
| 001 | websocket-streaming | Given a WS connection, when LLM streams tokens, then client receives chunks < 100ms | High |
| 002a | pdf-parse-pdfjs | Given a multi-page PDF, when parsed with pdfjs, then structured text is extractable | Medium |
| 002b | pdf-parse-camelot | Given a multi-page PDF, when parsed with camelot, then structured text is extractable | Medium |

**Spike types:**
- **standard** — one approach answering one question
- **comparison** — same question, different approaches (shared number, letter suffix `a`/`b`/`c`)

**Good spike questions:** specific feasibility with observable output.
**Bad spike questions:** too broad, no observable output, or just "read the docs about X".

**Order by risk.** The spike most likely to kill the idea runs first. No point prototyping the easy parts if the hard part doesn't work.

**Skip decomposition** only if the user already knows exactly what they want to spike and says so. Then take their idea as a single spike.

#### 2. Align (for multi-spike ideas)

Present the spike table. Ask: "Build all in this order, or adjust?" Let the user drop, reorder, or re-frame before you write any code.

#### 3. Research (per spike, before building)

Spikes are not research-free — you research enough to pick the right approach, then you build. Per spike:

1. **Brief it.** 2-3 sentences: what this spike is, why it matters, key risk.
2. **Surface competing approaches** if there's real choice:

   | Approach | Tool/Library | Pros | Cons | Status |
   |----------|-------------|------|------|--------|
   | ... | ... | ... | ... | maintained / abandoned / beta |

3. **Pick one.** State why. If 2+ are credible, build quick variants within the spike.
4. **Skip research** for pure logic with no external dependencies.

Use Hermes tools for the research step:

- `web_search("python websocket streaming libraries 2025")` — find candidates
- `web_extract(urls=["https://websockets.readthedocs.io/..."])` — read the actual docs (returns markdown)
- `terminal("pip show websockets | grep Version")` — check what's installed in the project's venv

For libraries without docs pages, clone and read their `README.md` / `examples/` via `read_file`. Context7 MCP (if the user has it configured) is also a good source — `mcp_*_resolve-library-id` then `mcp_*_query-docs`.

#### 4. Build

One directory per spike. Keep it standalone.

```
spikes/
├── 001-websocket-streaming/
│   ├── README.md
│   └── main.py
├── 002a-pdf-parse-pdfjs/
│   ├── README.md
│   └── parse.js
└── 002b-pdf-parse-camelot/
    ├── README.md
    └── parse.py
```

**Bias toward something the user can interact with.** Spikes fail when the only output is a log line that says "it works." The user wants to *feel* the spike working. Default choices, in order of preference:

1. A runnable CLI that takes input and prints observable output
2. A minimal HTML page that demonstrates the behavior
3. A small web server with one endpoint
4. A unit test that exercises the question with recognizable assertions

**Depth over speed.** Never declare "it works" after one happy-path run. Test edge cases. Follow surprising findings. The verdict is only trustworthy when the investigation was honest.

**Avoid** unless the spike specifically requires it: complex package management, build tools/bundlers, Docker, env files, config systems. Hardcode everything — it's a spike.

**Building one spike** — a typical tool sequence:

```
terminal("mkdir -p spikes/001-websocket-streaming")
write_file("spikes/001-websocket-streaming/README.md", "# 001: websocket-streaming\n\n...")
write_file("spikes/001-websocket-streaming/main.py", "...")
terminal("cd spikes/001-websocket-streaming && python3 main.py")
# Observe output, iterate.
```

**Parallel comparison spikes (002a / 002b) — delegate.** When two approaches can run in parallel and both need real engineering (not 10-line prototypes), fan out with `delegate_task`:

```
delegate_task(tasks=[
    {"goal": "Build 002a-pdf-parse-pdfjs: ...", "toolsets": ["terminal", "file", "web"]},
    {"goal": "Build 002b-pdf-parse-camelot: ...", "toolsets": ["terminal", "file", "web"]},
])
```

Each subagent returns its own verdict; you write the head-to-head.

#### 5. Verdict

Each spike's `README.md` closes with:

```markdown
## Verdict: VALIDATED | PARTIAL | INVALIDATED

### What worked
- ...

### What didn't
- ...

### Surprises
- ...

### Recommendation for the real build
- ...
```

**VALIDATED** = the core question was answered yes, with evidence.
**PARTIAL** = it works under constraints X, Y, Z — document them.
**INVALIDATED** = doesn't work, for this reason. This is a successful spike.

### Comparison Spikes

When two approaches answer the same question (002a / 002b), build them **back to back**, then do a head-to-head comparison at the end:

```markdown
## Head-to-head: pdfjs vs camelot

| Dimension | pdfjs (002a) | camelot (002b) |
|-----------|--------------|----------------|
| Extraction quality | 9/10 structured | 7/10 table-only |
| Setup complexity | npm install, 1 line | pip + ghostscript |
| Perf on 100-page PDF | 3s | 18s |
| Handles rotated text | no | yes |

**Winner:** pdfjs for our use case. Camelot if we need table-first extraction later.
```

### Frontier Mode (picking what to spike next)

If spikes already exist and the user says "what should I spike next?", walk the existing directories and look for:

- **Integration risks** — two validated spikes that touch the same resource but were tested independently
- **Data handoffs** — spike A's output was assumed compatible with spike B's input; never proven
- **Gaps in the vision** — capabilities assumed but unproven
- **Alternative approaches** — different angles for PARTIAL or INVALIDATED spikes

Propose 2-4 candidates as Given/When/Then. Let the user pick.

### Output

- Create `spikes/` (or `.planning/spikes/` if the user is using GSD conventions) in the repo root
- One dir per spike: `NNN-descriptive-name/`
- `README.md` per spike captures question, approach, results, verdict
- Keep the code throwaway — a spike that takes 2 days to "clean up for production" was a bad spike

### Attribution

Adapted from the GSD (Get Shit Done) project's `/gsd-spike` workflow — MIT © 2025 Lex Christopherson ([gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done)). The full GSD system offers persistent spike state, MANIFEST tracking, and integration with a broader spec-driven development pipeline; install with `npx get-shit-done-cc --hermes --global`.
