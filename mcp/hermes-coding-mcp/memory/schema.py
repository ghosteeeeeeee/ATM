"""
Memory Graph Schema — SQLite Node-Edge-Observation Model

This module initializes the SQLite database schema for the knowledge graph.
Schema: Node-Edge-Observation triple-store model for flexible knowledge representation.
"""

import sqlite3
from pathlib import Path
from typing import Optional
import uuid
from datetime import datetime


SCHEMA_SQL = """
-- Nodes: Files, Functions, Classes, Configs
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK(type IN ('file', 'function', 'class', 'config', 'test', 'module')),
    name TEXT NOT NULL,
    path TEXT,
    signature TEXT,
    language TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Edges: Relationships between nodes
CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relationship TEXT NOT NULL CHECK(relationship IN (
        'imports', 'calls', 'tests', 'configures', 
        'contains', 'implements', 'extends',
        'depends_on', 'references', 'wraps'
    )),
    weight REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, target_id, relationship)
);

-- Observations: What we learned about nodes
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY,
    node_id TEXT REFERENCES nodes(id) ON DELETE CASCADE,
    observation_type TEXT NOT NULL CHECK(observation_type IN (
        'pattern', 'convention', 'bug', 'note', 
        'performance', 'security', 'api', 'decision'
    )),
    content TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Session history for cross-session context
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    repo_path TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    tasks_completed INTEGER DEFAULT 0,
    key_decisions TEXT,
    success_metrics TEXT
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
CREATE INDEX IF NOT EXISTS idx_nodes_path ON nodes(path);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_observations_node ON observations(node_id);
CREATE INDEX IF NOT EXISTS idx_observations_type ON observations(observation_type);
CREATE INDEX IF NOT EXISTS idx_sessions_repo ON sessions(repo_path);
"""


class MemorySchema:
    """SQLite schema initializer for the knowledge graph."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the schema manager.
        
        Args:
            db_path: Path to SQLite database. Defaults to brain/memory.db
        """
        if db_path is None:
            brain_dir = Path.home() / ".hermes" / "brain"
            brain_dir.mkdir(parents=True, exist_ok=True)
            db_path = brain_dir / "memory.db"
        
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
    
    def initialize(self) -> None:
        """Create all tables if they don't exist."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()
    
    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


def create_node_id(node_type: str, name: str, path: Optional[str] = None) -> str:
    """Generate a deterministic node ID."""
    components = [node_type, name]
    if path:
        components.append(path)
    return uuid.uuid5(uuid.NAMESPACE_DNS, "|".join(components)).hex


def create_edge_id(source_id: str, target_id: str, relationship: str) -> str:
    """Generate a deterministic edge ID."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"{source_id}|{target_id}|{relationship}").hex


if __name__ == "__main__":
    # Test schema initialization
    with MemorySchema() as schema:
        print(f"Memory graph initialized at: {schema.db_path}")
        cursor = schema.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables created: {tables}")
