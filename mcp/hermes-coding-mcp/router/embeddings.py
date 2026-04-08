"""
Tool Embeddings Module.

Provides embedding generation using sentence-transformers/all-MiniLM-L6-v2
and cosine similarity computation for tool routing.
"""

import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np
import torch
from sentence_transformers import SentenceTransformer


@dataclass
class ToolDescription:
    """Describes a tool for embedding and routing."""
    name: str
    description: str
    usage_patterns: list[str]
    embedding: Optional[np.ndarray] = None


class ToolEmbeddingCache:
    """
    Embedding cache for tool descriptions.
    
    Pre-caches embeddings at startup using all-MiniLM-L6-v2 model.
    Thread-safe singleton pattern.
    """
    
    _instance: Optional['ToolEmbeddingCache'] = None
    _lock = threading.Lock()
    
    # Tool definitions with descriptions and usage patterns
    TOOLS = {
        "read_file": ToolDescription(
            name="read_file",
            description=(
                "Read a file's contents with optional line range support. "
                "Use when you need to examine existing code, view file contents, "
                "inspect configurations, or read any text file."
            ),
            usage_patterns=[
                "read", "view", "show", "cat", "display", "inspect",
                "look at", "examine", "check contents", "open file",
                "read the", "view the", "show me", "cat file"
            ]
        ),
        "write_file": ToolDescription(
            name="write_file",
            description=(
                "Write or create a file with content. Use when you need to "
                "create new files, modify existing files by overwriting, "
                "save code, write configurations, or generate new source files."
            ),
            usage_patterns=[
                "write", "create", "make new", "save", "generate",
                "write to", "create file", "make file", "save as",
                "overwrite", "put content", "dump to file"
            ]
        ),
        "search_code": ToolDescription(
            name="search_code",
            description=(
                "Search code using regex patterns to find specific text, "
                "function definitions, imports, comments, or any pattern "
                "across multiple files. Returns matching lines with context."
            ),
            usage_patterns=[
                "search", "find", "grep", "lookup", "locate", "match",
                "find all", "search for", "look for", "where is",
                "search in", "find in", "grep for"
            ]
        ),
        "execute_command": ToolDescription(
            name="execute_command",
            description=(
                "Execute a shell command in a sandboxed environment. "
                "Use for running tests, builds, git commands, npm, pip, "
                "compiling, running scripts, or any command-line operations."
            ),
            usage_patterns=[
                "run", "execute", "build", "test", "install", "compile",
                "run command", "execute", "run tests", "build with",
                "install", "npm", "pip", "git", "python", "node"
            ]
        ),
    }
    
    def __new__(cls) -> 'ToolEmbeddingCache':
        """Singleton pattern with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._model: Optional[SentenceTransformer] = None
        self._embeddings: dict[str, np.ndarray] = {}
        self._initialized = True
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the embedding model."""
        if self._model is None:
            self._model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        return self._model
    
    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
    
    def embed_tools(self) -> dict[str, np.ndarray]:
        """
        Pre-compute and cache embeddings for all tools.
        Call this at startup to avoid latency on first routing decision.
        
        Returns:
            Dict mapping tool name -> embedding vector
        """
        for tool_name, tool_desc in self.TOOLS.items():
            if tool_desc.embedding is None:
                # Combine description and usage patterns for richer embedding
                combined_text = f"{tool_desc.description} {' '.join(tool_desc.usage_patterns)}"
                tool_desc.embedding = self.embed(combined_text)
                self._embeddings[tool_name] = tool_desc.embedding
        return self._embeddings
    
    def get_embedding(self, tool_name: str) -> np.ndarray:
        """Get cached embedding for a tool."""
        if tool_name not in self._embeddings:
            if tool_name in self.TOOLS:
                tool_desc = self.TOOLS[tool_name]
                combined_text = f"{tool_desc.description} {' '.join(tool_desc.usage_patterns)}"
                tool_desc.embedding = self.embed(combined_text)
                self._embeddings[tool_name] = tool_desc.embedding
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
        return self._embeddings[tool_name]
    
    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        # Normalize vectors
        a_norm = np.linalg.norm(a)
        b_norm = np.linalg.norm(b)
        if a_norm == 0 or b_norm == 0:
            return 0.0
        return float(np.dot(a, b) / (a_norm * b_norm))


def init_embeddings() -> dict[str, np.ndarray]:
    """Initialize embeddings cache at startup."""
    cache = ToolEmbeddingCache()
    return cache.embed_tools()
