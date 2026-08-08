# Transcript Mining Report

**Source**: Ex-NASA dev reveals his Agentic Engineering Workflow.md
**Date**: 2026-08-08

## TL;DR
- **Program design before coding** — spend 20min upfront on product/architecture to avoid hours of rework
- **Vertical slices** — build end-to-end first, then add logic (models build horizontally by default)
- **Measurable outputs** — give agents quantifiable goals and they optimize for them
- **Stay in the loop** — have agents quiz you on codebase; stop reading = eventual crisis
- **Benchmarks lie** — SweBench doesn't penalize slop, only test pass/fail

## Ideas

### 1. Program Design Session (Context-Light)
- **What**: Make architecture decisions in a lightweight session (43k tokens) before deep coding
- **Why Hermes**: Signal architecture decisions (which indicators, how to combine, entry/exit logic) should be designed before coding
- **Where**: Signal development workflow, AGENTS.md
- **Effort**: small
- **Priority**: quick win

### 2. Vertical Slices for Signals
- **What**: Build signal end-to-end first (detection → signal → trade → exit), then add complexity
- **Why Hermes**: Currently signals are built horizontally (all detection logic, then all integration). Should build one signal complete end-to-end first.
- **Where**: Signal development pattern
- **Effort**: medium
- **Priority**: worth it

### 3. Measurable Signal Goals
- **What**: Define measurable output for each signal (WR > X%, profit factor > Y)
- **Why Hermes**: Currently signals are added without clear success metrics. Each signal should have a measurable goal.
- **Where**: hermes_constants.py, signal_schema.py
- **Effort**: small
- **Priority**: quick win

### 4. Agent-Quiz for Codebase Knowledge
- **What**: Have agents quiz you on codebase to keep you in the loop
- **Why Hermes**: Prevents losing touch with codebase when agents do most of the work
- **Where**: Could add to post-change skill
- **Effort**: small
- **Priority**: future

### 5. Incident-to-PR Pipeline
- **What**: Route incidents straight to agent, get PR back instead of alert
- **Why Hermes**: Pipeline failures, trade errors could auto-generate fix PRs
- **Where**: systemd timers, pipeline monitoring
- **Effort**: large
- **Priority**: future

### 6. LLM Quality Judge for Signals
- **What**: Use LLM to judge signal quality against rules (not just test pass)
- **Why Hermes**: Current smoke_test only checks if signal fires, not if it's good quality
- **Where**: smoke_test.py, signal quality evaluation
- **Effort**: medium
- **Priority**: worth it

## Quick Wins (do today)
- Add measurable goals to each signal type in hermes_constants.py
- Document vertical slice pattern for new signals in AGENTS.md

## Worth Discussing
- Program design sessions for major features
- LLM quality judge for signal evaluation
- Agent-quiz mechanism for codebase knowledge

## Skip
- PostHog integration (overkill for trading system)
- Full software factory (we're not a SaaS)
