"""
Parallel Dispatcher — Concurrent Pipeline Management

Manages a pool of PipelineWorkers with semaphore-based concurrency control.
Handles task distribution, conflict detection, and result aggregation.
"""

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from collections import defaultdict

from .worker import PipelineWorker, PipelineResult, ToolCall


@dataclass
class Conflict:
    """Represents a file write conflict between pipelines."""
    file_path: str
    pipelines: List[int]  # Pipeline IDs that wrote to this file
    resolution: str = 'last_write_wins'
    backup_path: Optional[str] = None


@dataclass
class DispatcherResult:
    """Aggregated result from all pipelines."""
    pipeline_count: int
    total_tasks: int
    completed: int
    escalated: int
    failed: int
    all_tool_calls: List[ToolCall]
    conflicts: List[Conflict]
    total_duration_seconds: float
    pipeline_results: List[PipelineResult] = field(default_factory=list)


class ParallelDispatcher:
    """
    Manages concurrent pipeline execution with semaphore-based concurrency.
    
    Features:
    - 2-3 concurrent pipeline workers
    - Semaphore-based concurrency control
    - File write conflict detection
    - Result aggregation
    """
    
    MAX_CONCURRENT = 3
    
    def __init__(
        self,
        tasks: List[str],
        tool_executor: Optional[callable] = None,
        max_concurrent: Optional[int] = None
    ):
        """
        Initialize the dispatcher.
        
        Args:
            tasks: List of task descriptions to execute
            tool_executor: Optional async function to execute tools
            max_concurrent: Maximum concurrent pipelines (default: 3)
        """
        self.tasks = tasks
        self.tool_executor = tool_executor
        self._max_concurrent = max_concurrent or self.MAX_CONCURRENT
        
        self.semaphore = asyncio.Semaphore(self._max_concurrent)
        
        self.workers: List[PipelineWorker] = []
        self.results: List[PipelineResult] = []
        self.conflicts: List[Conflict] = []
    
    async def run(self) -> DispatcherResult:
        """
        Run all tasks through concurrent pipelines.
        
        Returns:
            DispatcherResult with aggregated results
        """
        start_time = datetime.now()
        
        # Create all pipeline tasks
        async def run_with_semaphore(pipeline_id: int, task: str) -> PipelineResult:
            async with self.semaphore:
                worker = PipelineWorker(
                    pipeline_id=pipeline_id,
                    task=task,
                    tool_executor=self.tool_executor
                )
                self.workers.append(worker)
                return await worker.run()
        
        # Run all tasks concurrently (semaphore limits actual concurrency)
        coroutines = [
            run_with_semaphore(i, task) 
            for i, task in enumerate(self.tasks)
        ]
        
        # Wait for all to complete
        self.results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(self.results):
            if isinstance(result, Exception):
                # Create a failed result for exceptions
                processed_results.append(PipelineResult(
                    pipeline_id=i,
                    task=self.tasks[i],
                    status='failed',
                    errors=[str(result)]
                ))
            else:
                processed_results.append(result)
        
        self.results = processed_results
        
        total_duration = (datetime.now() - start_time).total_seconds()
        
        # Detect and resolve conflicts
        self.conflicts = self._detect_conflicts()
        self._resolve_conflicts()
        
        return self._aggregate_results(total_duration)
    
    def _detect_conflicts(self) -> List[Conflict]:
        """Detect file write conflicts between pipelines."""
        file_writes = defaultdict(list)
        
        for result in self.results:
            if isinstance(result, PipelineResult):
                for file_path in result.file_modifications:
                    file_writes[file_path].append(result.pipeline_id)
        
        conflicts = []
        
        for file_path, pipelines in file_writes.items():
            # A conflict exists if multiple pipelines wrote to the same file
            if len(pipelines) > 1:
                conflicts.append(Conflict(
                    file_path=file_path,
                    pipelines=pipelines,
                    resolution='last_write_wins'
                ))
        
        return conflicts
    
    def _resolve_conflicts(self) -> None:
        """Resolve detected conflicts with last-write-wins + backup."""
        for conflict in self.conflicts:
            if conflict.resolution == 'last_write_wins':
                # In a real implementation, we would:
                # 1. Read the file content from each pipeline's result
                # 2. Keep the last one's content
                # 3. Create .orig backup of previous versions
                conflict.backup_path = f"{conflict.file_path}.orig"
    
    def _aggregate_results(self, total_duration: float) -> DispatcherResult:
        """Aggregate results from all pipelines."""
        completed = sum(1 for r in self.results if isinstance(r, PipelineResult) and r.status == 'completed')
        escalated = sum(1 for r in self.results if isinstance(r, PipelineResult) and r.status == 'escalated')
        failed = sum(1 for r in self.results if isinstance(r, PipelineResult) and r.status == 'failed')
        
        all_tool_calls = []
        for result in self.results:
            if isinstance(result, PipelineResult):
                all_tool_calls.extend(result.tool_calls)
        
        return DispatcherResult(
            pipeline_count=len(self.results),
            total_tasks=len(self.tasks),
            completed=completed,
            escalated=escalated,
            failed=failed,
            all_tool_calls=all_tool_calls,
            conflicts=self.conflicts,
            total_duration_seconds=total_duration,
            pipeline_results=[r for r in self.results if isinstance(r, PipelineResult)]
        )
    
    def get_conflict_report(self) -> str:
        """Generate a human-readable conflict report."""
        if not self.conflicts:
            return "No file conflicts detected."
        
        lines = [f"Detected {len(self.conflicts)} file conflicts:"]
        
        for i, conflict in enumerate(self.conflicts):
            lines.append(
                f"  {i+1}. {conflict.file_path}: "
                f"pipelines {conflict.pipelines} "
                f"(resolution: {conflict.resolution})"
            )
        
        return "\n".join(lines)


async def run_parallel_tasks(
    tasks: List[str],
    tool_executor: Optional[callable] = None,
    max_concurrent: int = 3
) -> DispatcherResult:
    """
    Convenience function to run tasks in parallel.
    
    Args:
        tasks: List of task descriptions
        tool_executor: Optional async function to execute tools
        max_concurrent: Maximum concurrent pipelines
        
    Returns:
        DispatcherResult with aggregated results
    """
    dispatcher = ParallelDispatcher(
        tasks=tasks,
        tool_executor=tool_executor,
        max_concurrent=max_concurrent
    )
    
    return await dispatcher.run()
