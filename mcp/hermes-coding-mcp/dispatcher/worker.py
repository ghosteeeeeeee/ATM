"""
Pipeline Worker — Single Concurrent Pipeline Execution

Each pipeline runs independently with its own ReAct state machine,
tool router, and MCP tool calls.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from datetime import datetime


class ReActAction(Enum):
    """ReAct loop action types."""
    ROUTE = "route"
    ACT = "act"
    OBSERVE = "observe"
    DECIDE = "decide"
    DONE = "done"
    ESCALATE = "escalate"


@dataclass
class ToolCall:
    """Record of a tool invocation."""
    tool_name: str
    params: Dict[str, Any]
    result: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0
    success: bool = True


@dataclass
class PipelineResult:
    """Result from a single pipeline execution."""
    pipeline_id: int
    task: str
    status: str  # 'completed', 'escalated', 'failed'
    tool_calls: List[ToolCall] = field(default_factory=list)
    file_modifications: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0


class PipelineWorker:
    """
    Single pipeline worker that executes tasks through the ReAct loop.

    Each worker has:
    - Its own ReAct state machine
    - Independent tool execution context
    - File modification tracking for conflict detection
    """

    # Maximum tool calls to keep in history
    MAX_TOOL_CALLS = 1000

    def __init__(
        self,
        pipeline_id: int,
        task: str,
        tool_executor: Optional[Callable] = None
    ):
        """
        Initialize a pipeline worker.

        Args:
            pipeline_id: Unique identifier for this pipeline
            task: Task description to execute
            tool_executor: Optional async function to execute tools
        """
        self.pipeline_id = pipeline_id
        self.task = task
        self.tool_executor = tool_executor

        self.tool_calls: List[ToolCall] = []
        self.file_modifications: List[str] = []
        self.errors: List[str] = []
        
        self.current_action = ReActAction.ROUTE
        self.current_tool: Optional[str] = None
        self.current_result: Any = None
        
        self._start_time: Optional[datetime] = None
    
    async def run(self) -> PipelineResult:
        """
        Run the pipeline to completion.
        
        Returns:
            PipelineResult with execution details
        """
        self._start_time = datetime.now()
        status = 'completed'
        
        try:
            # Execute ReAct loop
            while self.current_action != ReActAction.DONE:
                if self.current_action == ReActAction.ESCALATE:
                    status = 'escalated'
                    break
                
                await self._execute_step()
            
        except Exception as e:
            status = 'failed'
            self.errors.append(f"Pipeline error: {str(e)}")
        
        duration = (datetime.now() - self._start_time).total_seconds()
        
        return PipelineResult(
            pipeline_id=self.pipeline_id,
            task=self.task,
            status=status,
            tool_calls=self.tool_calls,
            file_modifications=list(set(self.file_modifications)),
            errors=self.errors,
            completed_at=datetime.now(),
            duration_seconds=duration
        )
    
    async def _execute_step(self) -> None:
        """Execute one step of the ReAct loop."""
        if self.current_action == ReActAction.ROUTE:
            await self._route()
        elif self.current_action == ReActAction.ACT:
            await self._act()
        elif self.current_action == ReActAction.OBSERVE:
            self._observe()
        elif self.current_action == ReActAction.DECIDE:
            self._decide()
    
    async def _route(self) -> None:
        """Route the task to the appropriate tool."""
        # In production, this would use embeddings-based router
        # For now, use simple pattern matching
        task_lower = self.task.lower()
        
        if 'search' in task_lower or 'find' in task_lower:
            self.current_tool = 'search_code'
        elif 'read' in task_lower or 'show' in task_lower or 'what' in task_lower:
            self.current_tool = 'read_file'
        elif 'write' in task_lower or 'create' in task_lower or 'add' in task_lower:
            self.current_tool = 'write_file'
        elif 'run' in task_lower or 'execute' in task_lower or 'test' in task_lower:
            self.current_tool = 'execute_command'
        elif 'edit' in task_lower or 'modify' in task_lower:
            self.current_tool = 'edit_file'
        else:
            self.current_tool = 'search_code'
        
        self.current_action = ReActAction.ACT
    
    async def _act(self) -> None:
        """Execute the selected tool."""
        import time
        start = time.time()
        
        tool_call = ToolCall(
            tool_name=self.current_tool or 'unknown',
            params={'task': self.task}
        )
        
        try:
            if self.tool_executor:
                result = await self.tool_executor(
                    self.current_tool,
                    {'task': self.task}
                )
            else:
                # Simulate tool execution
                result = await self._simulate_tool_execution()
            
            tool_call.result = result
            tool_call.duration_ms = (time.time() - start) * 1000
            self.current_result = result
            
            # Track file modifications
            if self.current_tool == 'write_file':
                if isinstance(result, dict) and 'path' in result:
                    self.file_modifications.append(result['path'])
            
        except Exception as e:
            tool_call.success = False
            tool_call.result = str(e)
            tool_call.duration_ms = (time.time() - start) * 1000
            self.errors.append(f"Tool {self.current_tool} failed: {e}")
        
        self.tool_calls.append(tool_call)

        # Truncate history if it exceeds max size to prevent unbounded growth
        if len(self.tool_calls) > self.MAX_TOOL_CALLS:
            self.tool_calls = self.tool_calls[-self.MAX_TOOL_CALLS:]

        self.current_action = ReActAction.OBSERVE
    
    async def _simulate_tool_execution(self) -> Dict[str, Any]:
        """Simulate tool execution for testing."""
        await asyncio.sleep(0.01)  # Minimal delay
        
        tool = self.current_tool
        
        if tool == 'search_code':
            return {'files_found': ['file1.py', 'file2.py'], 'matches': 2}
        elif tool == 'read_file':
            return {'content': 'sample content', 'path': 'sample.py'}
        elif tool == 'write_file':
            path = f'/tmp/pipeline_{self.pipeline_id}_output.txt'
            return {'path': path, 'success': True}
        elif tool == 'execute_command':
            return {'output': 'Command executed', 'return_code': 0}
        elif tool == 'edit_file':
            return {'path': 'sample.py', 'changes': 'applied'}
        else:
            return {'status': 'unknown_tool'}
    
    def _observe(self) -> None:
        """Evaluate the result and decide next action."""
        # Simple success/failure evaluation
        if self.tool_calls:
            last_call = self.tool_calls[-1]
            
            if not last_call.success:
                # Retry logic would go here
                self.errors.append(f"Tool failure in pipeline {self.pipeline_id}")
        
        self.current_action = ReActAction.DECIDE
    
    def _decide(self) -> None:
        """Decide the next action based on state."""
        # Simple logic: after 3 tool calls, consider done
        if len(self.tool_calls) >= 3:
            self.current_action = ReActAction.DONE
        else:
            self.current_action = ReActAction.ROUTE
    
    def get_file_modifications(self) -> List[str]:
        """Get list of files modified by this pipeline."""
        return list(set(self.file_modifications))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline execution statistics."""
        return {
            'pipeline_id': self.pipeline_id,
            'task': self.task,
            'tool_calls': len(self.tool_calls),
            'files_modified': len(self.file_modifications),
            'errors': len(self.errors),
            'duration_seconds': (datetime.now() - self._start_time).total_seconds() if self._start_time else 0
        }
