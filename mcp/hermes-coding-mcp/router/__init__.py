"""
Tool Router - Embeddings-based routing for the Better Coder agent.

Exposes:
    - router: the main Router instance (pre-cached embeddings)
    - route_task(task_description: str) -> str: returns tool name
    - get_tool_info() -> dict: returns tool metadata and scores
"""

from .embeddings import ToolEmbeddingCache
from .router import Router

# Global router instance (lazily initialized and cached)
_router: Router | None = None


def _get_router() -> Router:
    """Get or create the global router instance."""
    global _router
    if _router is None:
        _router = Router()
    return _router


def route_task(task_description: str) -> str:
    """
    Route a task description to the most appropriate tool.
    
    Uses embeddings-based similarity with name boost and pattern boost.
    Falls back to 'search_code' when confidence < 0.3.
    
    Args:
        task_description: Natural language description of the task
        
    Returns:
        Tool name string: 'read_file', 'write_file', 'search_code', or 'execute_command'
    """
    return _get_router().route_task(task_description)


def get_tool_scores(task_description: str) -> dict:
    """Get routing scores for all tools (useful for debugging)."""
    return _get_router().get_scores(task_description)


def get_tool_info() -> dict:
    """Get tool metadata (names, descriptions, usage patterns)."""
    return _get_router().get_tool_info()
