# ADR-001: PostgreSQL for Brain DB, SQLite for Runtime

**Date**: 2026-07-19
**Status**: Accepted
**Deciders**: T

## Context
Hermes needs two types of data storage:
- Trade history, positions, signals (permanent, queried across sessions)
- Runtime state, speed tracker, candle cache (ephemeral, per-pipeline-run)

## Decision
- **PostgreSQL** (`brain` database) for permanent trade/position data
- **SQLite** (various `.db` files in `data/`) for runtime state

## Consequences
- PostgreSQL requires auth + connection management
- SQLite is simpler but locks under concurrent access
- All PostgreSQL connections go through `get_db_connection()` in `position_manager.py`
- All SQLite connections must use `cursor.close()` in `finally` blocks

## Alternatives Considered
- All PostgreSQL: too heavy for ephemeral state
- All SQLite: locking issues with concurrent pipeline + guardian
