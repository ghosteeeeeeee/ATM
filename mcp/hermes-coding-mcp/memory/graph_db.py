"""
Knowledge Graph — Layer 1: SQLite Node-Edge-Observation Store

Provides the core graph operations for storing and retrieving
structured knowledge about codebases.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
import json

from .schema import MemorySchema, create_node_id, create_edge_id


class KnowledgeGraph:
    """
    SQLite-backed knowledge graph for code context.
    
    Stores nodes (files, functions, classes), edges (relationships),
    and observations (learned knowledge) for cross-session context.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the knowledge graph.
        
        Args:
            db_path: Path to SQLite database. Defaults to ~/.hermes/brain/memory.db
        """
        self.schema = MemorySchema(db_path)
        self.db_path = self.schema.db_path
    
    def connect(self) -> None:
        """Establish database connection."""
        self.schema.initialize()
    
    def close(self) -> None:
        """Close database connection."""
        self.schema.close()
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
    
    # === Node Operations ===
    
    def add_node(
        self,
        node_type: str,
        name: str,
        path: Optional[str] = None,
        signature: Optional[str] = None,
        language: Optional[str] = None
    ) -> str:
        """
        Add a node to the graph.
        
        Args:
            node_type: Type of node (file, function, class, config, test, module)
            name: Name of the node
            path: File path (for files/functions/classes)
            signature: Function/class signature
            language: Programming language
            
        Returns:
            Node ID
        """
        node_id = create_node_id(node_type, name, path)
        
        self.schema.conn.execute("""
            INSERT OR REPLACE INTO nodes (id, type, name, path, signature, language, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (node_id, node_type, name, path, signature, language))
        
        self.schema.conn.commit()
        return node_id
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node by ID."""
        cursor = self.schema.conn.execute("""
            SELECT id, type, name, path, signature, language, created_at, updated_at
            FROM nodes WHERE id = ?
        """, (node_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "id": row[0],
            "type": row[1],
            "name": row[2],
            "path": row[3],
            "signature": row[4],
            "language": row[5],
            "created_at": row[6],
            "updated_at": row[7]
        }
    
    def find_nodes(
        self,
        node_type: Optional[str] = None,
        path_prefix: Optional[str] = None,
        name_pattern: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find nodes matching criteria.
        
        Args:
            node_type: Filter by node type
            path_prefix: Filter by path prefix
            name_pattern: Filter by name pattern (SQL LIKE)
            
        Returns:
            List of matching nodes
        """
        query = "SELECT id, type, name, path, signature, language FROM nodes WHERE 1=1"
        params = []
        
        if node_type:
            query += " AND type = ?"
            params.append(node_type)
        
        if path_prefix:
            query += " AND path LIKE ?"
            params.append(f"{path_prefix}%")
        
        if name_pattern:
            query += " AND name LIKE ?"
            params.append(f"%{name_pattern}%")
        
        cursor = self.schema.conn.execute(query, params)
        rows = cursor.fetchall()
        
        return [
            {"id": r[0], "type": r[1], "name": r[2], "path": r[3], "signature": r[4], "language": r[5]}
            for r in rows
        ]
    
    # === Edge Operations ===
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        weight: float = 1.0
    ) -> Optional[str]:
        """
        Add an edge between two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            relationship: Relationship type (imports, calls, tests, etc.)
            weight: Edge weight (0.0 to 1.0)
            
        Returns:
            Edge ID or None if nodes don't exist
        """
        # Verify nodes exist
        source = self.get_node(source_id)
        target = self.get_node(target_id)
        
        if not source or not target:
            return None
        
        edge_id = create_edge_id(source_id, target_id, relationship)
        
        self.schema.conn.execute("""
            INSERT OR REPLACE INTO edges (id, source_id, target_id, relationship, weight)
            VALUES (?, ?, ?, ?, ?)
        """, (edge_id, source_id, target_id, relationship, weight))
        
        self.schema.conn.commit()
        return edge_id
    
    def get_outgoing_edges(self, node_id: str) -> List[Dict[str, Any]]:
        """Get all edges from a node."""
        cursor = self.schema.conn.execute("""
            SELECT e.id, e.source_id, e.target_id, e.relationship, e.weight,
                   n.name, n.type, n.path
            FROM edges e
            JOIN nodes n ON e.target_id = n.id
            WHERE e.source_id = ?
            ORDER BY e.weight DESC
        """, (node_id,))
        
        return self._edges_to_dicts(cursor.fetchall())
    
    def get_incoming_edges(self, node_id: str) -> List[Dict[str, Any]]:
        """Get all edges to a node."""
        cursor = self.schema.conn.execute("""
            SELECT e.id, e.source_id, e.target_id, e.relationship, e.weight,
                   n.name, n.type, n.path
            FROM edges e
            JOIN nodes n ON e.source_id = n.id
            WHERE e.target_id = ?
            ORDER BY e.weight DESC
        """, (node_id,))
        
        return self._edges_to_dicts(cursor.fetchall())
    
    def _edges_to_dicts(self, rows: List[Tuple]) -> List[Dict[str, Any]]:
        """Convert edge rows to dictionaries."""
        return [
            {
                "id": r[0],
                "source_id": r[1],
                "target_id": r[2],
                "relationship": r[3],
                "weight": r[4],
                "target_name": r[5],
                "target_type": r[6],
                "target_path": r[7]
            }
            for r in rows
        ]
    
    # === Observation Operations ===
    
    def add_observation(
        self,
        node_id: str,
        observation_type: str,
        content: str,
        confidence: float = 1.0,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Add an observation about a node.
        
        Args:
            node_id: Node to observe
            observation_type: Type (pattern, convention, bug, note, etc.)
            content: Observation content
            confidence: Confidence level (0.0 to 1.0)
            tags: Optional tags for categorization
            
        Returns:
            Observation ID
        """
        obs_id = create_node_id("observation", content[:50], node_id)
        
        if tags:
            tags_str = json.dumps(tags)
        else:
            tags_str = None
        
        self.schema.conn.execute("""
            INSERT INTO observations (id, node_id, observation_type, content, confidence, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (obs_id, node_id, observation_type, content, confidence, tags_str))
        
        self.schema.conn.commit()
        return obs_id
    
    def get_observations(
        self,
        node_id: Optional[str] = None,
        observation_type: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Get observations, optionally filtered.
        
        Args:
            node_id: Filter by node
            observation_type: Filter by type
            min_confidence: Minimum confidence level
            
        Returns:
            List of observations
        """
        query = """
            SELECT o.id, o.node_id, o.observation_type, o.content, o.confidence, o.tags, o.created_at,
                   n.name, n.type, n.path
            FROM observations o
            JOIN nodes n ON o.node_id = n.id
            WHERE o.confidence >= ?
        """
        params = [min_confidence]
        
        if node_id:
            query += " AND o.node_id = ?"
            params.append(node_id)
        
        if observation_type:
            query += " AND o.observation_type = ?"
            params.append(observation_type)
        
        query += " ORDER BY o.confidence DESC, o.created_at DESC"
        
        cursor = self.schema.conn.execute(query, params)
        rows = cursor.fetchall()
        
        return [
            {
                "id": r[0],
                "node_id": r[1],
                "observation_type": r[2],
                "content": r[3],
                "confidence": r[4],
                "tags": json.loads(r[5]) if r[5] else [],
                "created_at": r[6],
                "node_name": r[7],
                "node_type": r[8],
                "node_path": r[9]
            }
            for r in rows
        ]
    
    # === Graph Traversal ===
    
    def traverse_dependencies(self, node_id: str, max_depth: int = 3) -> Dict[str, Any]:
        """
        Traverse the dependency graph from a node.
        
        Args:
            node_id: Starting node
            max_depth: Maximum traversal depth
            
        Returns:
            Dict with 'nodes' and 'edges' at each depth level
        """
        visited = set()
        result = {"nodes": [], "edges": [], "depths": {}}
        
        def traverse(current_id: str, depth: int):
            if depth > max_depth or current_id in visited:
                return
            
            visited.add(current_id)
            node = self.get_node(current_id)
            
            if node:
                result["nodes"].append(node)
                result["depths"][current_id] = depth
            
            for edge in self.get_outgoing_edges(current_id):
                result["edges"].append(edge)
                traverse(edge["target_id"], depth + 1)
        
        traverse(node_id, 0)
        return result
    
    # === Session Management ===
    
    def start_session(self, repo_path: str) -> str:
        """Start a new session and return session ID."""
        session_id = create_node_id("session", repo_path, datetime.now().isoformat())
        
        self.schema.conn.execute("""
            INSERT INTO sessions (id, repo_path)
            VALUES (?, ?)
        """, (session_id, repo_path))
        
        self.schema.conn.commit()
        return session_id
    
    def end_session(
        self,
        session_id: str,
        tasks_completed: int,
        key_decisions: Optional[List[str]] = None
    ) -> None:
        """End a session and record outcomes."""
        decisions_json = json.dumps(key_decisions) if key_decisions else None
        
        self.schema.conn.execute("""
            UPDATE sessions 
            SET ended_at = CURRENT_TIMESTAMP,
                tasks_completed = ?,
                key_decisions = ?
            WHERE id = ?
        """, (tasks_completed, decisions_json, session_id))
        
        self.schema.conn.commit()
    
    def get_recent_sessions(self, repo_path: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent sessions for a repo."""
        cursor = self.schema.conn.execute("""
            SELECT id, repo_path, started_at, ended_at, tasks_completed, key_decisions
            FROM sessions
            WHERE repo_path = ?
            ORDER BY started_at DESC
            LIMIT ?
        """, (repo_path, limit))
        
        rows = cursor.fetchall()
        
        return [
            {
                "id": r[0],
                "repo_path": r[1],
                "started_at": r[2],
                "ended_at": r[3],
                "tasks_completed": r[4],
                "key_decisions": json.loads(r[5]) if r[5] else []
            }
            for r in rows
        ]
