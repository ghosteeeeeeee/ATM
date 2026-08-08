# Transcript Mining Report

**Source**: Top 10 GitHub Repos of the Week - Andrew Ng.md
**Date**: 2026-08-08

## TL;DR
- **Agent memory sharing** — Tencent DB Agent Memory solves team context loss when developers join
- **Book-to-skill** — Turn reference books into agent skills for consistent decision-making
- **Concise agent output** — Rules for agents to lead with actions, not context
- **Diff-based code review** — Terminal-based review tools for agentic workflows
- **Local-first AI OS** — Desktop apps combining chat, agents, coding, and memory

## Ideas

### 1. Agent Memory Sharing (Tencent DB Agent Memory)
- **What**: Shared memory store for agents so team context persists across sessions and developers
- **Why Hermes**: Currently each session starts fresh. Shared memory would let pipeline, signals, and guardian share learnings without re-discovering
- **Where**: OpenMemory integration, brain.py, signal_compactor.py
- **Effort**: large
- **Priority**: future

### 2. Book-to-Skill Conversion
- **What**: Turn reference books into agent skills that can be queried and applied consistently
- **Why Hermes**: Could encode trading books (Technical Analysis of Financial Markets, etc.) into skills that guide signal design and risk management
- **Where**: New skill type, /book-skill command
- **Effort**: medium
- **Priority**: worth it

### 3. Concise Agent Output Rules
- **What**: Rules that force agents to lead with actions, not context (first line = what reader can do)
- **Why Hermes**: Agent responses are often verbose. Could improve CEO reports, pipeline alerts, and signal summaries
- **Where**: AGENTS.md, CEO skill, pipeline logging
- **Effort**: small
- **Priority**: quick win

### 4. Diff-Based Code Review
- **What**: Terminal-based tools for reviewing agent-written code changes via diffs
- **Why Hermes**: After major changes, we use bug_hunter subagent. Could add diff-review step to post-change workflow
- **Where**: post-change skill, bug-hunter skill
- **Effort**: small
- **Priority**: quick win

### 5. Local-First AI Operating System
- **What**: Desktop app combining chat, agents, coding, creative, and memory in one interface
- **Why Hermes**: Our system is already close to this (opencode + OpenMemory + pipeline). Could formalize the "orchestrator" pattern
- **Where**: Architecture documentation, AGENTS.md
- **Effort**: large
- **Priority**: skip (we already have this)

### 6. Tool Router Pattern
- **What**: Agent that routes tasks to the right tool based on input type
- **Why Hermes**: Signal compactor already does this somewhat. Could formalize routing for different trade types (momentum vs mean-reversion vs breakout)
- **Where**: signal_compactor.py, signals_runner.py
- **Effort**: medium
- **Priority**: worth it

## Quick Wins (do today)
- Add "lead with action" rule to AGENTS.md for agent output
- Add diff-review step to post-change skill

## Worth Discussing
- Book-to-skill for trading knowledge
- Tool router for signal types
- Agent memory sharing across sessions

## Skip
- Local-first AI OS (we already have this architecture)
- Terminal code review (we use subagents, not terminal)
