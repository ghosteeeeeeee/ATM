# Memory Graph Design — Cross-Session Context for Better Coder

## Overview

Design for a knowledge graph that preserves "what we learned about this codebase" across agent sessions.

---

## Problem Statement

Current system has no memory between sessions:
- Every new session starts from scratch
- Agent re-discovers the same patterns, file locations, and conventions
- No awareness of previous successful implementations

---

## Solution: Dual-Layer Memory Graph

### Layer 1: Repository Knowledge Graph (SQLite)

Stores structured knowledge about the codebase being worked on.

```sql
-- Node: Files, Functions, Classes, Configs
CREATE TABLE nodes (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL, -- 'file', 'function', 'class', 'config', 'test'
    name TEXT NOT NULL,
    path TEXT,
    signature TEXT, -- for functions/classes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Edges: Relationships between nodes
CREATE TABLE edges (
    id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES nodes(id),
    target_id TEXT REFERENCES nodes(id),
    relationship TEXT NOT NULL, -- 'imports', 'calls', 'tests', 'configures'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Observations: What we learned about nodes
CREATE TABLE observations (
    id TEXT PRIMARY KEY,
    node_id TEXT REFERENCES nodes(id),
    observation_type TEXT NOT NULL, -- 'pattern', 'convention', 'bug', 'note'
    content TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Layer 2: Pattern Library (File-based)

Stores successful code patterns for reuse.

```
brain/patterns/
├── python/
│   ├── async-handler.py      # Successful async pattern
│   ├── context-manager.py    # Context manager pattern
│   └── error-handling.py     # Error handling pattern
├── javascript/
│   └── promise-pattern.js
└── markdown/
    └── decision-log.md      # Why we made certain decisions
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Storage | SQLite + Files | SQLite for relationships, files for code patterns |
| Schema | Node-Edge-Observation | Flexible triple-store model |
| Query | SPARQL-lite | Simple graph traversal for common patterns |
| Sync | Lazy updates | Update graph on significant actions, not every keystroke |
| Context | Retrieval at session start | Load relevant context before first task |

---

## Operations

### Write Path (Session End)
1. Extract key decisions made during session
2. Store observations about code patterns found
3. Update relationships between code entities
4. Index new patterns into pattern library

### Read Path (Session Start)
1. Load repo context from SQLite graph
2. Retrieve recent observations about project
3. Load relevant patterns from pattern library
4. Inject into system prompt as context

---

## Integration Points

### ReAct Loop Integration
- After `search_code`: Store discovered patterns
- After `execute_command` success: Record successful commands
- On task completion: Store key decisions made

### Router Integration  
- Before routing: Check if similar task was seen before
- If same task pattern exists: Suggest previous approach

---

## Next Steps

1. Create SQLite schema and initialization
2. Build context loader that injects memory into prompts  
3. Implement pattern storage on task completion
4. Design retrieval queries for session startup

---

**Status**: Design Complete - Ready for Implementation
