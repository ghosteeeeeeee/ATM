"""
Parallel Dispatcher Module — Concurrent Pipeline Execution

Provides concurrent task execution with:
- PipelineWorker: Individual pipeline with ReAct loop
- ParallelDispatcher: Manager with semaphore-based concurrency
- Conflict detection and resolution

Usage:
    from dispatcher import ParallelDispatcher, run_parallel_tasks
    
    # Option 1: Direct run
    dispatcher = ParallelDispatcher(tasks=['task1', 'task2', 'task3'])
    result = await dispatcher.run()
    
    # Option 2: Convenience function
    result = await run_parallel_tasks(['task1', 'task2', 'task3'])
    
    print(f"Completed {result.completed}/{result.total_tasks} tasks")
    print(f"Conflicts: {result.conflicts}")
"""

from .worker import PipelineWorker, PipelineResult, ToolCall, ReActAction
from .dispatcher import ParallelDispatcher, DispatcherResult, Conflict, run_parallel_tasks

__all__ = [
    "PipelineWorker",
    "PipelineResult", 
    "ToolCall",
    "ReActAction",
    "ParallelDispatcher",
    "DispatcherResult",
    "Conflict",
    "run_parallel_tasks",
]

__version__ = "1.0.0"
