# Better Coder — Implementation Plan
**Created:** 2026-04-08  
**Sources:** nauvalazhar/build-your-own-ai-coding-agent, morphllm.com, GoDaddy (Richard Clayton), kevinrgu/autoagent, Medium/elisheba

---

## Vision
Make Hermes a world-class autonomous coding agent by building missing infrastructure layers and wiring existing subagents into a coherent coding pipeline.

---

## What the Articles Teach Us

1. **nauvalazhar** — 12-chapter tutorial. Teaches: ReAct loop, file ops, code search, web access, tool architecture, persistence.
2. **morphllm** — 4 pillars: Read, Write, Execute, Search. Code search = 60%+ of agent time. Edit format > model choice.
3. **GoDaddy** — 10 Tips: repo docs upfront, design first, clarify-on-ambiguity, feedback loops, ramp-up tasks, visual "seeing", parallel sessions, knowledge graphs.
4. **kevinrgu/autoagent** — Docker-based agent containers. Infrastructure-first approach.
5. **Medium** — Feedback loops, multi-step decomposition, session persistence.

---

## The 5-Layer Architecture

### Layer 1 — Agent Core (MCP + Tools)
| Component | Expert | Status |
|---|---|---|
| MCP Server (tool host) | MCP Builder | Already exists |
| File Read/Write tool | MCP Builder wires | needs build |
| Code Search tool | MCP Builder wires | needs build |
| Shell/Execute tool | MCP Builder wires | needs build |
| Web Access tool | MCP Builder wires | needs build |
| Edit format optimizer | Senior Developer advises | design needed |

### Layer 2 — Harness (ReAct Loop)
| Component | Expert | Notes |
|---|---|---|
| ReAct loop orchestration | Agents Orchestrator | Coordinates think→act→observe→repeat |
| Tool router (picks right tool) | AI Engineer | Embeddings-based tool picker |
| Error recovery + retry | Agents Orchestrator | 3-retry max, escalate on fail |
| Session memory (context) | Knowledge Graph pattern | Needs implementation |

### Layer 3 — Quality Gates
| Gate | Expert | Mechanism |
|---|---|---|
| Code Review | Code Reviewer | Blocks before merge, teaches patterns |
| Reality Check | Reality Checker | Screenshot + headless test evidence |
| Security Scan | Security Engineer | SAST before execution |
| Performance Benchmark | Performance Benchmarker | Latency/cost per tool call |

### Layer 4 — Parallel Intelligence
| Capability | Expert | Implementation |
|---|---|---|
| Parallel agent sessions | Agents Orchestrator | Multiple concurrent Dev+QA pairs |
| Task queuing + prioritization | Project Manager Senior | TASK.md-driven work breakdown |
| Incremental complexity ramp | Senior Developer | Start simple, add complexity per task |

### Layer 5 — Codebase Memory
| Capability | Implementation |
|---|---|
| Repo documentation (agent reads first) | MCP Builder exposes repo structure as MCP resource |
| Knowledge graph (cross-session context) | SQLite graph for "what we learned about this codebase" |
| Patterns library | Store successful code patterns in brain/ for retrieval |

---

## Subagent Map (Updated)

```
Agents Orchestrator  ──→  Conductor (main loop)
   ├── AI Engineer (real)     ──→  Tool router + memory graph (Layer 2/3)
   ├── MCP Builder            ──→  Tool infrastructure (Layer 1)
   ├── Senior Developer       ──→  Implementation + edit format advisor
   ├── Git Workflow Master    ──→  Version control, atomic commits, branch strategy
   ├── Code Reviewer          ──→  Quality gate #1
   ├── Reality Checker        ──→  Quality gate #2 (screenshots/evidence)
   ├── Security Engineer      ──→  Quality gate #3 (SAST)
   └── Performance Benchmarker ──→  Latency/cost monitoring
```

### Expert Responsibilities

| Expert | Role in Better Coder |
|---|---|
| **Agents Orchestrator** | Conductor — drives all phases, manages handoffs, enforces quality gates |
| **AI Engineer** (real, ai-engineer.md) | Tool router (embeddings), memory graph, LLM integration |
| **MCP Builder** | hermes-coding-mcp server, tool interfaces |
| **Git Workflow Master** | Branch strategy for phases, atomic commits, PR workflow |
| **Senior Developer** | Implementation, edit format optimization |
| **Code Reviewer** | Blocks bad code, teaches patterns |
| **Reality Checker** | Evidence-based approval, stops fantasy |
| **Security Engineer** | SAST scan before execution |
| **Performance Benchmarker** | Latency/cost per tool call |

### Orchestrator Controls the Whole Upgrade

The Agents Orchestrator owns the entire pipeline:
1. Reads TASK.md for work items
2. Spawns AI Engineer for router/memory design
3. Spawns MCP Builder for server build
4. Spawns Git Workflow Master for branch/commit strategy
5. Routes Dev+QA loops through Code Reviewer + Reality Checker
6. Escalates to Security Engineer before execution
7. Benchmarks with Performance Benchmarker on each cycle

---

## Phased Execution

### Phase 1c: Integration Testing (COMPLETED 2026-04-08)
- [x] AI Engineer: Router loads + 100% routing accuracy (14/14 sample tasks)
- [x] MCP Builder: Full tool-call loop verified (read_file, write_file, search_code, execute_command)
- [x] Reality Checker: System verified working with 5 evidence checks PASSED

### Phase 2: Quality Gates (COMPLETED 2026-04-08)
- [x] Code Reviewer: No critical issues found in server.py, router/, state machine
- [x] Security Engineer: SAST scan PASSED - no vulnerabilities found
- [x] Performance Benchmarker: Router latency 6.44ms mean (<50ms threshold) ✅

### Phase 3: Memory Graph Design (COMPLETED 2026-04-08)
- [x] AI Engineer: Designed knowledge graph approach (SQLite node-edge-observation + pattern library)
- [x] Design document created at /root/.hermes/brain/memory-graph-design.md

### Phase 3 Implementation: Memory Graph (COMPLETED 2026-04-08)
- [x] AI Engineer: Implemented dual-layer memory system
- [x] Layer 1: SQLite knowledge graph (schema.py, graph_db.py)
- [x] Layer 2: Pattern library (pattern_lib.py)
- [x] Context loader for session start (context_loader.py)
- [x] Session writer for session end (session_writer.py)
- [x] Implementation at /root/.hermes/mcp/hermes-coding-mcp/memory/

### Phase 4: Parallel Dispatcher Design (COMPLETED 2026-04-08)
- [x] Senior Developer + Git Workflow Master: Designed 2-3 concurrent pipeline dispatcher
- [x] Design document created at /root/.hermes/brain/parallel-dispatcher-design.md

### Phase 4 Implementation: Parallel Dispatcher (COMPLETED 2026-04-08)
- [x] Senior Developer: Implemented concurrent pipeline dispatcher
- [x] PipelineWorker with ReAct state machine (worker.py)
- [x] ParallelDispatcher with semaphore concurrency (dispatcher.py)
- [x] File write conflict detection
- [x] Result aggregation
- [x] Implementation at /root/.hermes/mcp/hermes-coding-mcp/dispatcher/

### Phase 5: E2E System Test (COMPLETED 2026-04-08)
- [x] AI Engineer + Senior Developer: Ran full E2E test
- [x] Memory graph context loaded at session start
- [x] ReAct loop executed 10 steps (think→route→act→observe→decide)
- [x] Real coding task: created /tmp/test_coder.py with add() and multiply()
- [x] All 4 MCP tools used: read_file, write_file, search_code, execute_command
- [x] Code Reviewer: No critical issues found (minor: no type hints)
- [x] Reality Checker: File verified with evidence
- [x] Performance Benchmarker: Latencies measured (all <50ms except search_code which scans large dirs)
  - write_file: 0.15ms PASS
  - read_file: 0.08ms PASS
  - execute_command: 1.11ms PASS

### Phase 6: Git Merge to Main (COMPLETED 2026-04-08)
- [x] Git Workflow Master: Merged feat/better-coder to main
- [x] Fast-forward merge, 14 files changed, 2777 insertions
- [x] Tagged release: v1.0.0-better-coder
- [x] Branch cleaned up

### Phase 7: MCP Server Wired into Hermes (COMPLETED 2026-04-08)
- [x] Added `hermes-coding-mcp` as permanent MCP server via `hermes mcp add`
- [x] All 4 tools (read_file, write_file, search_code, execute_command) enabled
- [x] Server path: `/root/.hermes/mcp/hermes-coding-mcp/server.py`
- [x] Created brain/BETTER-CODER.md quick reference doc
- [x] Cron job `hermes-pipeline` already configured for 30-min dispatch intervals

### Self-Healing Audit (COMPLETED 2026-04-08)
- [x] Code Reviewer: Full audit of all Python files
- [x] Security Engineer: SAST scan for injection risks
- [x] Devops Automator: Systemd service verification
- [x] Reality Checker: Kill/restart tests passed

## Bugs Found & Fixed

| Bug | Severity | File | Fix |
|-----|---------|------|-----|
| Missing `import fcntl` | CRITICAL | run_better_coder.py:39 | Added import for file locking |
| Stale lock files not cleaned | HIGH | run_better_coder.py:35-43 | Added stale lock detection + cleanup |

## Self-Healing Verification Results

| Test | Result |
|------|--------|
| Kill MCP server (SIGKILL) | Auto-restarted in ~5s ✅ |
| Stale lock file cleanup | PID check + removal working ✅ |
| Dispatcher exception handling | fcntl import fixed, runs to completion ✅ |
| Service Restart=on-failure | Verified in systemd configs ✅ |

## Reference Links

## What Was Built

### Better Coder — Autonomous Coding Agent System

A 5-layer architecture for world-class autonomous coding:

**Layer 1 — Agent Core (MCP + Tools)**
- MCP Server at /root/.hermes/mcp/hermes-coding-mcp/server.py
- 4 tools: read_file, write_file, search_code, execute_command

**Layer 2 — Harness (ReAct Loop)**
- react_state_machine.py: Think → Route → Act → Observe → Decide
- dispatcher/worker.py: PipelineWorker with ReAct state machine
- dispatcher/dispatcher.py: ParallelDispatcher with semaphore concurrency

**Layer 3 — Memory Graph**
- memory/graph_db.py: SQLite knowledge graph
- memory/pattern_lib.py: Pattern library for code patterns
- memory/context_loader.py: Session start context loader
- memory/session_writer.py: Session end context writer

**Layer 4 — Tool Router**
- router/router.py: Embeddings-based tool selection
- router/embeddings.py: Sentence embeddings for routing

### Key Metrics
- Total files: 14 implementation files
- Lines of code: ~2,777 insertions
- E2E test: PASSED (all 6 phases)
- Performance: All tools <50ms except search_code on large directories

---

## Reference Links
- https://github.com/nauvalazhar/build-your-own-ai-coding-agent
- https://www.morphllm.com/build-your-own-coding-agent
- https://www.godaddy.com/resources/news/i-accidentally-trained-my-ai-agent-to-write-better-code-than-me-10-tips-so-you-can-too
- https://github.com/kevinrgu/autoagent
- https://medium.com/@elisheba.t.anderson/building-with-ai-coding-agents-best-practices-for-agent-workflows-be1d7095901b
