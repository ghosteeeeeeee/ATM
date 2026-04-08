"""
ReAct State Machine for Better Coder.

Implements the Think -> Route -> Act -> Observe -> Decide loop
for autonomous coding agent orchestration.

Based on: nauvalazhar/build-your-own-ai-coding-agent
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class ReActAction(Enum):
    """Actions the state machine can take."""
    THINK = "think"
    ROUTE = "route"
    ACT = "act"
    OBSERVE = "observe"
    DECIDE = "decide"
    RETRY = "retry"
    ESCALATE = "escalate"
    DONE = "done"


class StepStatus(Enum):
    """Status after each step."""
    SUCCESS = "success"
    ERROR_RECOVERABLE = "error_recoverable"
    ERROR_FATAL = "error_fatal"
    TASK_COMPLETE = "task_complete"
    NEEDS_MORE_STEPS = "needs_more_steps"


@dataclass
class ToolCall:
    """Record of a tool invocation."""
    tool_name: str
    parameters: dict
    timestamp: datetime = field(default_factory=datetime.now)
    result: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass
class ReActState:
    """
    ReAct state machine for agent orchestration.

    Attributes:
        task: Current task description from user
        history: All tool calls made so far
        current_thought: Current reasoning/thinking
        current_action: Current action being considered
        current_tool: Tool selected for execution
        current_params: Parameters for current tool
        retries: Current retry count for failed tool
        max_retries: Maximum retries before escalation (default: 3)
        step_count: Number of ReAct steps taken
    """
    task: str
    history: list[ToolCall] = field(default_factory=list)
    current_thought: Optional[str] = None
    current_action: ReActAction = ReActAction.THINK
    current_tool: Optional[str] = None
    current_params: dict = field(default_factory=dict)
    retries: int = 0
    max_retries: int = 3
    step_count: int = 0
    error_message: Optional[str] = None

    # Maximum history size to prevent unbounded memory growth
    MAX_HISTORY_SIZE: int = 1000
    
    def step(self, tool_result: Optional[dict] = None) -> tuple[ReActAction, Optional[dict]]:
        """
        Execute one step of the ReAct loop.
        
        Args:
            tool_result: Result from the previous tool call (if any)
            
        Returns:
            Tuple of (next_action, response_data)
        """
        self.step_count += 1
        
        if self.current_action == ReActAction.THINK:
            self.current_thought = self._analyze_task()
            self.current_action = ReActAction.ROUTE
            return ReActAction.ROUTE, {"thought": self.current_thought}
        
        elif self.current_action == ReActAction.ROUTE:
            # Tool routing handled externally by the router module
            self.current_action = ReActAction.ACT
            return ReActAction.ACT, {"tool": self.current_tool, "params": self.current_params}
        
        elif self.current_action == ReActAction.ACT:
            if tool_result is None:
                # Need to actually call the tool
                return ReActAction.ACT, {"call_tool": True}
            
            # Record the result
            if self.history:
                self.history[-1].result = tool_result
            
            self.current_action = ReActAction.OBSERVE
            return ReActAction.OBSERVE, tool_result
        
        elif self.current_action == ReActAction.OBSERVE:
            status = self._evaluate_result(tool_result)
            
            if status == StepStatus.TASK_COMPLETE:
                self.current_action = ReActAction.DONE
                return ReActAction.DONE, tool_result
            
            elif status == StepStatus.ERROR_RECOVERABLE:
                if self.retries < self.max_retries:
                    self.retries += 1
                    self.current_action = ReActAction.RETRY
                    return ReActAction.RETRY, {"retry": self.retries, "max": self.max_retries}
                else:
                    self.current_action = ReActAction.ESCALATE
                    return ReActAction.ESCALATE, {"reason": "max_retries_exceeded"}
            
            elif status == StepStatus.ERROR_FATAL:
                self.current_action = ReActAction.ESCALATE
                return ReActAction.ESCALATE, {"reason": "fatal_error", "error": self.error_message}
            
            else:
                self.retries = 0
                self.current_action = ReActAction.THINK
                return ReActAction.THINK, {"continue": True}
        
        elif self.current_action == ReActAction.RETRY:
            self.current_action = ReActAction.ACT
            return ReActAction.ACT, {"call_tool": True}
        
        else:
            return self.current_action, {}
    
    def _analyze_task(self) -> str:
        """Analyze the current task and determine what needs to be done."""
        # This is a placeholder - in practice, this would use an LLM
        # to generate reasoning about the task
        return f"Analyzing task: {self.task}"
    
    def _evaluate_result(self, result: dict) -> StepStatus:
        """
        Evaluate the result of a tool call.
        
        Returns:
            StepStatus indicating what happened and what to do next
        """
        if result is None:
            return StepStatus.NEEDS_MORE_STEPS
        
        # Check for errors
        if isinstance(result, dict) and result.get("isError"):
            error = result.get("error", "unknown")
            self.error_message = result.get("message", error)
            
            # Recoverable errors that can be retried
            recoverable = {"timeout", "transient_failure", "rate_limit"}
            if error in recoverable or result.get("recoverable"):
                return StepStatus.ERROR_RECOVERABLE
            else:
                return StepStatus.ERROR_FATAL
        
        # Check if task appears complete
        # This is a simple heuristic - in practice would use LLM evaluation
        if self._check_task_complete(result):
            return StepStatus.TASK_COMPLETE
        
        return StepStatus.NEEDS_MORE_STEPS
    
    def _check_task_complete(self, result: dict) -> bool:
        """Heuristic check if task appears complete."""
        # Simple checks - in practice, use LLM to evaluate
        if not result:
            return False
        
        # If we got meaningful data back, consider it progress
        # A more sophisticated check would look at the specific task
        return False  # Conservative - let the orchestrator decide
    
    def record_tool_call(self, tool_name: str, parameters: dict,
                         duration_ms: Optional[float] = None) -> None:
        """Record a tool call in history."""
        call = ToolCall(
            tool_name=tool_name,
            parameters=parameters,
            duration_ms=duration_ms
        )
        self.history.append(call)

        # Truncate history if it exceeds max size to prevent unbounded growth
        if len(self.history) > self.MAX_HISTORY_SIZE:
            # Keep the most recent entries
            self.history = self.history[-self.MAX_HISTORY_SIZE:]
    
    def get_history_summary(self) -> dict:
        """Get a summary of all tool calls made."""
        return {
            "task": self.task,
            "step_count": self.step_count,
            "tool_calls": [
                {
                    "tool": call.tool_name,
                    "params": call.parameters,
                    "error": call.error,
                    "duration_ms": call.duration_ms
                }
                for call in self.history
            ]
        }
