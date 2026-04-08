"""
Memory Graph Module — Cross-Session Context for Better Coder

Dual-layer memory system:
- Layer 1: SQLite Knowledge Graph (nodes, edges, observations)
- Layer 2: Pattern Library (file-based code patterns)

Usage:
    # At session start
    from memory import ContextLoader
    
    loader = ContextLoader("/path/to/repo")
    context = loader.load_context()
    prompt_context = loader.format_for_prompt()
    
    # At session end
    from memory import SessionWriter
    
    writer = SessionWriter(session_id, "/path/to/repo")
    writer.add_observation(...)
    writer.store_pattern(...)
    writer.finalize(tasks_completed=5)
"""

from .schema import MemorySchema, create_node_id, create_edge_id
from .graph_db import KnowledgeGraph
from .pattern_lib import PatternLibrary
from .context_loader import ContextLoader
from .session_writer import SessionWriter

__all__ = [
    "MemorySchema",
    "create_node_id", 
    "create_edge_id",
    "KnowledgeGraph",
    "PatternLibrary",
    "ContextLoader",
    "SessionWriter",
]

__version__ = "1.0.0"
