"""
Session Writer — Write Path for Session End

Stores patterns, observations, and decisions made during a session.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
import json

from .graph_db import KnowledgeGraph
from .pattern_lib import PatternLibrary


class SessionWriter:
    """
    Writes session data to the memory graph at session end.
    
    Write path:
    1. Extract key decisions made during session
    2. Store observations about code patterns found
    3. Update relationships between code entities
    4. Index new patterns into pattern library
    """
    
    def __init__(
        self,
        session_id: str,
        repo_path: str,
        db_path: Optional[str] = None,
        patterns_dir: Optional[Path] = None
    ):
        """
        Initialize the session writer.
        
        Args:
            session_id: ID of the current session
            repo_path: Path to the repository
            db_path: Optional custom path for the knowledge graph DB
            patterns_dir: Optional custom path for patterns directory
        """
        self.session_id = session_id
        self.repo_path = Path(repo_path).resolve()
        self.kg = KnowledgeGraph(db_path)
        self.pl = PatternLibrary(patterns_dir)
        
        self.pending_nodes: List[Dict[str, Any]] = []
        self.pending_edges: List[Dict[str, Any]] = []
        self.pending_observations: List[Dict[str, Any]] = []
        self.pending_patterns: List[Dict[str, Any]] = []
    
    def add_file_node(
        self,
        file_path: str,
        language: Optional[str] = None
    ) -> str:
        """
        Record a file that was encountered or modified.
        
        Args:
            file_path: Path to the file
            language: Programming language (auto-detected if not provided)
            
        Returns:
            Node ID
        """
        node_id = self.kg.add_node(
            node_type="file",
            name=Path(file_path).name,
            path=str(Path(file_path).resolve()),
            language=language or self._detect_language(file_path)
        )
        
        self.pending_nodes.append({
            "id": node_id,
            "type": "file",
            "path": file_path
        })
        
        return node_id
    
    def add_function_node(
        self,
        name: str,
        file_path: str,
        signature: str,
        language: Optional[str] = None
    ) -> str:
        """
        Record a function that was discovered or created.
        
        Args:
            name: Function name
            file_path: Path to the file containing the function
            signature: Function signature
            language: Programming language
            
        Returns:
            Node ID
        """
        node_id = self.kg.add_node(
            node_type="function",
            name=name,
            path=str(Path(file_path).resolve()),
            signature=signature,
            language=language or self._detect_language(file_path)
        )
        
        self.pending_nodes.append({
            "id": node_id,
            "type": "function",
            "name": name,
            "file": file_path
        })
        
        # Also add file node if not already tracked
        self.add_file_node(file_path, language)
        
        return node_id
    
    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        weight: float = 1.0
    ) -> None:
        """
        Record a relationship between two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            relationship: Relationship type (imports, calls, tests, etc.)
            weight: Relationship weight (0.0 to 1.0)
        """
        self.kg.add_edge(source_id, target_id, relationship, weight)
        
        self.pending_edges.append({
            "source": source_id,
            "target": target_id,
            "relationship": relationship
        })
    
    def add_observation(
        self,
        node_id: str,
        observation_type: str,
        content: str,
        confidence: float = 1.0,
        tags: Optional[List[str]] = None
    ) -> None:
        """
        Add an observation about a node.
        
        Args:
            node_id: Node being observed
            observation_type: Type (pattern, convention, bug, note, etc.)
            content: Observation content
            confidence: Confidence level (0.0 to 1.0)
            tags: Optional tags
        """
        self.kg.add_observation(
            node_id=node_id,
            observation_type=observation_type,
            content=content,
            confidence=confidence,
            tags=tags
        )
        
        self.pending_observations.append({
            "node_id": node_id,
            "type": observation_type,
            "content": content
        })
    
    def store_pattern(
        self,
        language: str,
        pattern_name: str,
        code: str,
        description: str,
        tags: Optional[List[str]] = None
    ) -> None:
        """
        Store a successful code pattern.
        
        Args:
            language: Programming language
            pattern_name: Unique name for the pattern
            code: The code pattern
            description: What this pattern does
            tags: Categorization tags
        """
        self.pl.store_pattern(
            language=language,
            pattern_name=pattern_name,
            code=code,
            description=description,
            tags=tags
        )
        
        self.pending_patterns.append({
            "language": language,
            "name": pattern_name
        })
    
    def log_decision(
        self,
        decision: str,
        context: str,
        rationale: str,
        alternatives: Optional[List[str]] = None
    ) -> None:
        """
        Log a significant decision made during the session.
        
        Args:
            decision: What was decided
            context: Situation that required the decision
            rationale: Why this was the right choice
            alternatives: What alternatives were considered
        """
        self.pl.log_decision(
            decision=decision,
            context=context,
            rationale=rationale,
            alternatives=alternatives
        )
    
    def finalize(
        self,
        tasks_completed: int,
        key_decisions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Finalize the session and write all pending data.
        
        Args:
            tasks_completed: Number of tasks completed
            key_decisions: List of key decision summaries
            
        Returns:
            Session summary
        """
        with self.kg:
            # End the session
            self.kg.end_session(
                session_id=self.session_id,
                tasks_completed=tasks_completed,
                key_decisions=key_decisions
            )
        
        summary = {
            "session_id": self.session_id,
            "repo_path": str(self.repo_path),
            "nodes_added": len(self.pending_nodes),
            "edges_added": len(self.pending_edges),
            "observations_added": len(self.pending_observations),
            "patterns_stored": len(self.pending_patterns),
            "tasks_completed": tasks_completed
        }
        
        return summary
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
        }
        
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext)
    
    def close(self) -> None:
        """Close connections."""
        self.kg.close()
    
    # === Integration helpers for ReAct loop ===
    
    def record_search_result(
        self,
        query: str,
        files_found: List[str],
        pattern_detected: Optional[str] = None
    ) -> None:
        """
        Record results from a code search.
        
        Args:
            query: Search query
            files_found: List of file paths found
            pattern_detected: Optional pattern name detected
        """
        for file_path in files_found:
            file_node = self.add_file_node(file_path)
            
            if pattern_detected:
                self.add_observation(
                    node_id=file_node,
                    observation_type="pattern",
                    content=f"File matches pattern '{pattern_detected}' for query '{query}'",
                    confidence=0.8,
                    tags=["search", pattern_detected]
                )
    
    def record_command_success(
        self,
        command: str,
        working_dir: str,
        output_summary: str
    ) -> None:
        """
        Record a successful command execution.
        
        Args:
            command: Command that was executed
            working_dir: Working directory
            output_summary: Summary of command output
        """
        self.add_observation(
            node_id="session",
            observation_type="note",
            content=f"Successfully executed: {command} in {working_dir}. Output: {output_summary[:200]}",
            confidence=0.9,
            tags=["command", "success"]
        )
    
    def record_file_edit(
        self,
        file_path: str,
        edit_type: str,
        description: str
    ) -> None:
        """
        Record a file edit.
        
        Args:
            file_path: Path to the file
            edit_type: Type of edit (create, modify, delete)
            description: Description of the change
        """
        file_node = self.add_file_node(file_path)
        
        self.add_observation(
            node_id=file_node,
            observation_type="note",
            content=f"File {edit_type}: {description}",
            confidence=1.0,
            tags=["edit", edit_type]
        )
