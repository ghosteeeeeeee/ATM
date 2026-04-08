"""
Tool Router - Embeddings-based routing with name and pattern boosts.

Routes task descriptions to the most appropriate tool using:
1. Cosine similarity between task embedding and tool embeddings
2. Name boost (+0.2) if task contains tool name
3. Pattern boost (+0.1 per matching pattern)
4. Fallback to 'search_code' when confidence < 0.3
"""

import re
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .embeddings import ToolEmbeddingCache, ToolDescription


@dataclass
class RoutingResult:
    """Result of a routing decision."""
    tool_name: str
    confidence: float
    scores: dict[str, float]


class Router:
    """
    Embeddings-based tool router.
    
    Pre-caches tool embeddings at startup for fast routing.
    Uses cosine similarity + heuristics (name/pattern boost).
    """
    
    # Confidence threshold below which we fall back to search_code
    CONFIDENCE_THRESHOLD = 0.3
    
    # Boost values
    NAME_BOOST = 0.2
    PATTERN_BOOST = 0.1
    
    def __init__(self) -> None:
        self._cache = ToolEmbeddingCache()
        self._tools = self._cache.TOOLS
        # Pre-cache embeddings at startup
        self._cache.embed_tools()
    
    def route_task(self, task_description: str) -> str:
        """
        Route a task description to the most appropriate tool.
        
        Args:
            task_description: Natural language description of what to do
            
        Returns:
            Tool name string: 'read_file', 'write_file', 'search_code', or 'execute_command'
        """
        result = self._route_with_scores(task_description)
        return result.tool_name
    
    def get_scores(self, task_description: str) -> dict[str, float]:
        """Get routing scores for all tools (no fallback applied)."""
        result = self._route_with_scores(task_description)
        return result.scores
    
    def _route_with_scores(self, task_description: str) -> RoutingResult:
        """
        Compute routing scores and return best tool with confidence.
        
        Algorithm:
        1. Embed task description
        2. Compute cosine similarity with each tool's embedding
        3. Apply name boost if task contains tool name
        4. Apply pattern boost for matching usage patterns
        5. Return best tool if above threshold, else search_code
        """
        task_lower = task_description.lower()
        
        # Embed the task
        task_embedding = self._cache.embed(task_description)
        
        scores: dict[str, float] = {}
        
        for tool_name, tool_desc in self._tools.items():
            # Cosine similarity
            similarity = self._cache.cosine_similarity(task_embedding, tool_desc.embedding)
            
            # Name boost
            name_boost = self.NAME_BOOST if self._contains_tool_name(task_lower, tool_name) else 0.0
            
            # Pattern boost
            pattern_boost = self._compute_pattern_boost(task_lower, tool_desc)
            
            total_score = similarity + name_boost + pattern_boost
            scores[tool_name] = total_score
        
        # Find best tool
        best_tool = max(scores, key=scores.get)  # type: ignore
        best_score = scores[best_tool]
        
        # Fallback if below threshold
        if best_score < self.CONFIDENCE_THRESHOLD:
            return RoutingResult(
                tool_name="search_code",
                confidence=best_score,
                scores=scores
            )
        
        return RoutingResult(
            tool_name=best_tool,
            confidence=best_score,
            scores=scores
        )
    
    def _contains_tool_name(self, text: str, tool_name: str) -> bool:
        """Check if text contains the tool name or common aliases."""
        # Direct name match
        if tool_name in text:
            return True
        
        # Common aliases
        aliases: dict[str, list[str]] = {
            "read_file": ["read", "view", "show", "cat", "display", "inspect", "look at"],
            "write_file": ["write", "create", "make", "save", "generate"],
            "search_code": ["search", "find", "grep", "lookup", "locate"],
            "execute_command": ["run", "execute", "build", "test", "install", "compile"],
        }
        
        for alias in aliases.get(tool_name, []):
            if alias in text:
                return True
        
        return False
    
    def _compute_pattern_boost(self, text: str, tool_desc: ToolDescription) -> float:
        """Compute pattern boost based on matching usage patterns."""
        boost = 0.0
        for pattern in tool_desc.usage_patterns:
            # Use word boundary matching for better precision
            if re.search(r'\b' + re.escape(pattern) + r'\b', text):
                boost += self.PATTERN_BOOST
        return boost
    
    def get_tool_info(self) -> dict:
        """Get metadata for all tools."""
        return {
            name: {
                "name": desc.name,
                "description": desc.description,
                "usage_patterns": desc.usage_patterns,
            }
            for name, desc in self._tools.items()
        }
