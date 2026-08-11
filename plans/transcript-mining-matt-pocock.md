# Transcript Mining Report

**Source:** Matt Pocock's Agentic Engineering Workflow (just copy him)
**Date:** 2026-08-11

## TL;DR

- Matt Pocock's core thesis: **harness > model** — optimize codebase quality, skills, and environment over chasing better LLMs
- Our system already embodies most of his philosophy: deterministic scoring, procedural skills, self-learning loops
- One idea worth stealing: **"delete everything, observe, layer back"** — a periodic context audit to prevent skill/instruction bloat
- Queue-based task management (not while-loop agents) — our systemd timers already do this

## Ideas

### 1. Context Bloat Audit
- **What**: Matt's #1 advice: "delete every skill, plugin, MCP server, CLAUDE.md, AGENTS.md — go back to blank slate. Observe what the agent does. Only layer back what you actually need."
- **Why Hermes**: We have 20+ skills, AGENTS.md, LESSONS.md, multiple config files. Some may be dead weight consuming context window. A periodic audit could keep things lean.
- **Where**: AGENTS.md, skills/, config files
- **Effort**: trivial — manual review, no code
- **Priority**: Worth doing once — then repeat quarterly

### 2. Agent Experience (AX) Optimization
- **What**: Matt distinguishes DX (developer experience) from AX (agent experience). AX = how well an agent can navigate your codebase. Good AX = good file naming, clear module boundaries, minimal circular deps.
- **Why Hermes**: Our codebase has grown organically. Some files are 2000+ lines. Improving AX (splitting large files, clearer naming) would help both human and agent maintainers.
- **Where**: Large files like signal_gen.py, ai_decider.py, position_manager.py
- **Effort**: large — refactoring
- **Priority**: Future — ongoing cleanup

### 3. Queues Not Loops
- **What**: Matt argues "agentic loops" are overhyped — what you really want is a task queue with AFK agents picking tasks off. Our systemd timers already implement this pattern (signal-decider, tokyo-decider, etc. fire on schedule, not in a while loop).
- **Why Hermes**: Already implemented. Validates our architecture.
- **Where**: N/A — already done
- **Effort**: N/A
- **Priority**: N/A — architecture validation

### 4. Skills as Procedures Not Abilities
- **What**: Matt's skills repo distinguishes "procedure skills" (how to do X) from "ability skills" (give me superpowers). Procedure skills are more reliable because they're step-by-step.
- **Why Hermes**: Our skills (add-signal, signal-lab, bug-hunter, post-change) are already procedure-based. This validates the approach.
- **Where**: Skills we already have
- **Effort**: N/A
- **Priority**: N/A — architecture validation

### 5. Self-Improving Loops
- **What**: Matt says: "build systems that are self-improving over time. We write test suites, do human reviews, refactor. A model has uncovered that we need more of that." But he says you don't need a fancy model for these insights — you can build them as procedures.
- **Why Hermes**: Our self_learner.py, Hebbian engine, and CEO automation already ARE self-improving loops. This validates the approach.
- **Where**: Already implemented
- **Effort**: N/A
- **Priority**: N/A — architecture validation

## Quick Wins (do today)
1. **Context bloat audit** — review AGENTS.md and skills/, remove anything unused. 30 min manual review.

## Worth Discussing
1. **AX-focused refactoring** — split large files (signal_gen.py, ai_decider.py) for better maintainability

## Skip
- **Sand Castle / Docker sandboxes** — we run on bare metal, not relevant
- **GitHub Actions for AFK agents** — we use systemd timers, already equivalent
- **Fable / computer use** — not applicable to trading system
- **MCP servers** — we don't use MCP, our integrations are direct API calls
