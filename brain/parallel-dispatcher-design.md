# Parallel Dispatcher Design — 2-3 Concurrent Pipelines

## Overview

Design for running 2-3 concurrent development pipelines from the TASK.md work breakdown.

---

## Problem Statement

Current system runs tasks sequentially:
- Single task → route → execute → observe → decide
- Sequential completion of tasks in TASK.md
- No parallelization of independent tasks

---

## Solution: Concurrent Pipeline Dispatcher

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PARALLEL DISPATCHER                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │  Pipeline 1 │ │  Pipeline 2  │ │  Pipeline 3  │             │
│  │  Dev + QA    │ │  Dev + QA    │ │  Dev + QA    │             │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘             │
│         │               │               │                      │
│         ▼               ▼               ▼                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │  Task A      │ │  Task B      │ │  Task C      │           │
│  │  (independent)│ │  (independent)│ │  (independent)│          │
│  └──────────────┘ └──────────────┘ └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  RESULT AGGREGATOR   │
                    │  (merge, resolve)    │
                    └─────────────────────┘
```

### Pipeline Worker

Each pipeline runs independently with its own:
- ReAct state machine
- Tool router
- MCP tool calls
- Dev + QA loop

```python
class PipelineWorker:
    def __init__(self, pipeline_id: int, task: str):
        self.pipeline_id = pipeline_id
        self.task = task
        self.state = ReActState(task=task)
        self.router = Router()
        self.results = []
    
    async def run(self) -> PipelineResult:
        """Run one pipeline to completion."""
        while self.state.current_action != ReActAction.DONE:
            action, data = self.state.step()
            
            if action == ReActAction.ROUTE:
                tool = self.router.route_task(self.state.task)
                self.state.current_tool = tool
                
            elif action == ReActAction.ACT:
                result = await self._execute_tool(tool, params)
                self.results.append(result)
                
            elif action == ReActAction.OBSERVE:
                self._evaluate_and_decide(result)
                
            elif action == ReActAction.ESCALATE:
                return PipelineResult(
                    pipeline_id=self.pipeline_id,
                    status='escalated',
                    results=self.results
                )
        
        return PipelineResult(
            pipeline_id=self.pipeline_id,
            status='completed',
            results=self.results
        )
```

### Dispatcher

Manages worker pool, task distribution, and result aggregation.

```python
class ParallelDispatcher:
    MAX_CONCURRENT = 3
    
    def __init__(self, tasks: list[str]):
        self.tasks = tasks
        self.workers: list[PipelineWorker] = []
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
    
    async def run(self) -> DispatcherResult:
        """Run multiple pipelines concurrently."""
        # Start workers for first batch of tasks
        active_workers = []
        
        for i, task in enumerate(self.tasks[:self.MAX_CONCURRENT]):
            worker = PipelineWorker(pipeline_id=i, task=task)
            active_workers.append(asyncio.create_task(worker.run()))
        
        # Process results as workers complete
        completed = []
        for coro in asyncio.as_completed(active_workers):
            result = await coro
            completed.append(result)
            
            # Start next task if any remaining
            next_idx = len(completed) + self.MAX_CONCURRENT - 1
            if next_idx < len(self.tasks):
                worker = PipelineWorker(
                    pipeline_id=next_idx, 
                    task=self.tasks[next_idx]
                )
                active_workers.append(asyncio.create_task(worker.run()))
        
        return self._aggregate_results(completed)
    
    def _aggregate_results(self, results: list[PipelineResult]) -> DispatcherResult:
        """Merge results from all pipelines."""
        all_tool_calls = []
        total_duration = 0
        
        for result in results:
            all_tool_calls.extend(result.results)
            # Track conflicts for merge resolution
        
        return DispatcherResult(
            pipeline_count=len(results),
            all_tool_calls=all_tool_calls,
            conflicts=self._detect_conflicts(results),
            final_status=self._determine_status(results)
        )
```

---

## Conflict Resolution

When concurrent pipelines modify the same file:

1. **Detect**: Track file modifications per pipeline
2. **Warn**: Flag concurrent writes to same file as conflict
3. **Resolve**: Last-write-wins + create `.orig` backup

```python
def _detect_conflicts(self, results: list[PipelineResult]) -> list[Conflict]:
    """Detect file conflicts between pipelines."""
    file_writes = defaultdict(list)
    
    for result in results:
        for call in result.results:
            if call.tool == 'write_file':
                path = call.params['path']
                file_writes[path].append(result.pipeline_id)
    
    conflicts = []
    for path, pipelines in file_writes.items():
        if len(pipelines) > 1:
            conflicts.append(Conflict(
                file=path,
                pipelines=pipelines,
                resolution='last_write_wins'
            ))
    
    return conflicts
```

---

## Task Dependency Analysis

Before dispatching, analyze TASK.md for dependencies:

```python
def analyze_dependencies(tasks: list[Task]) -> DependencyGraph:
    """Build dependency graph from task descriptions."""
    graph = DependencyGraph()
    
    for task in tasks:
        # Check if task depends on output of another task
        if 'after' in task.description or 'depends on' in task.description:
            parent = extract_parent_reference(task)
            graph.add_edge(parent, task.id)
        else:
            graph.add_independent(task.id)
    
    return graph

def get_dispatch_order(graph: DependencyGraph) -> list[list[str]]:
    """Return batches of tasks that can run concurrently."""
    # Topological sort with level grouping
    # Level 0: All independent tasks
    # Level 1: Tasks depending on Level 0
    # etc.
```

---

## Git Integration

Each pipeline works on its own branch:

```
main ─────────────────────────────────────────
         │          │          │
    feature/p1   feature/p2   feature/p3
    (Task A)     (Task B)    (Task C)
         │          │          │
         └──────────┴──────────┘
                       │
                 merge-branch
```

**Flow:**
1. Each pipeline creates `feature/pipeline-{id}/task-{name}`
2. Pipelines run independently
3. On completion, merge into consolidation branch
4. Resolve conflicts with full context

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Concurrency | 2-3 workers | Balance throughput vs resource usage |
| Conflict handling | Detect + last-write-wins | Simple, predictable |
| Branch strategy | Per-pipeline branches | Isolation prevents interference |
| Task ordering | Dependency analysis first | Sequential for dependent tasks |
| Result merge | Centralized aggregator | Single source of truth |

---

## Next Steps

1. Implement PipelineWorker class
2. Build ParallelDispatcher with semaphore-based concurrency
3. Add dependency analysis for task ordering
4. Wire in Git branch creation per pipeline
5. Implement conflict detection and resolution

---

**Status**: Design Complete - Ready for Implementation

**Requires**: Phase 3 (Memory Graph) for cross-pipeline context sharing
