# ADR-008: Pipeline Lock Prevents Overlapping Runs

**Date**: 2026-07-19
**Status**: Accepted
**Deciders**: T

## Context
Pipeline runs can overlap if the previous run hasn't finished. This causes duplicate trades, race conditions on DB writes, and position_manager crashes.

## Decision
- `/tmp/hermes-pipeline.lock` file used as mutex
- `run_pipeline.py` acquires lock at start, releases on exit
- If lock exists and is recent (<5min), skip this run
- Lock auto-releases on process exit (even crash)

## Consequences
- Pipeline runs are serialized
- No duplicate trades from overlapping runs
- Lock file can get stuck if process killed harshly (manual cleanup needed)

## Alternatives Considered
- Systemd timer with `RemainAfterExit`: doesn't prevent overlap
- Database-level locking: too heavy for pipeline coordination
