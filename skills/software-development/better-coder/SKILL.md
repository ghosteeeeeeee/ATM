---
name: better-coder
description: Better Coder — autonomous coding agent system for Hermes. 5-layer architecture: MCP tools, ReAct loop, memory graph, embeddings router, quality gates. Reads TASKS.md and executes parallel agent workflows.
color: purple
emoji: 🦸
category: software-development
author: T
created: 2026-04-08
---

# Better Coder

The Better Coder is a fully-implemented autonomous coding agent system for Hermes.

## Source of Truth

All implementation and methodology comes exclusively from:

**`/root/.hermes/brain/better-coder-plan.md`**

This plan document contains the complete architecture, phase history, and reference links.

## System Location

```
/root/.hermes/mcp/hermes-coding-mcp/
├── server.py              # MCP server (Layer 1 - Core Tools)
├── react_state_machine.py # ReAct loop orchestration
├── dispatcher/            # Parallel dispatcher (Layer 2)
│   ├── dispatcher.py      # ParallelDispatcher (semaphore concurrency)
│   └── worker.py          # PipelineWorker with ReAct state machine
├── router/                # Embeddings-based tool router (Layer 4)
│   ├── router.py
│   └── embeddings.py
├── memory/                 # Memory graph (Layer 3)
│   ├── graph_db.py        # SQLite knowledge graph
│   ├── pattern_lib.py     # Pattern library
│   ├── context_loader.py  # Session start loader
│   └── session_writer.py  # Session end writer
└── e2e_test.py
```

## Entry Point

```bash
python /root/.hermes/scripts/run_better_coder.py
```

## 5-Layer Architecture

| Layer | Component | Status |
|-------|-----------|--------|
| 1 | MCP Server (read_file, write_file, search_code, execute_command) | ✅ Active |
| 2 | ReAct Loop + Parallel Dispatcher | ✅ Active |
| 3 | Memory Graph (SQLite nodes + pattern library) | ✅ Active |
| 4 | Embeddings-based Tool Router | ✅ Active |
| 5 | Quality Gates (Code Reviewer, Reality Checker, Security Engineer) | ✅ Active |

## Usage

When asked to perform a coding task, delegate it to the Better Coder system by spawning subagents or invoking `run_better_coder.py` directly.

For complex multi-step tasks, use the Parallel Dispatcher to run concurrent agent pairs (Dev + QA).

## Key Files

- **Plan/Architecture**: `/root/.hermes/brain/better-coder-plan.md`
- **Entry script**: `/root/.hermes/scripts/run_better_coder.py`
- **Memory graph design**: `/root/.hermes/brain/memory-graph-design.md`
- **Parallel dispatcher design**: `/root/.hermes/brain/parallel-dispatcher-design.md`
- **Quick reference**: `/root/.hermes/brain/BETTER-CODER.md`
