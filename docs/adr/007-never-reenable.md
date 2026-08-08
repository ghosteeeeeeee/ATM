# ADR-007: NEVER_REENABLE_FLAGS Policy

**Date**: 2026-08-05
**Status**: Accepted
**Deciders**: T

## Context
Killed signals keep coming back. The signal rotator re-enables them, or someone accidentally sets `*_ENABLED = True`.

## Decision
- `NEVER_REENABLE_FLAGS` list in `hermes_constants.py`
- Signals in this list are blocked at the schema level
- `_DEAD_SIGNALS` blocklist in `signal_schema.py` as defense-in-depth
- CEO cannot re-enable signals in this list
- Only T can remove from NEVER_REENABLE_FLAGS

## Consequences
- Dead signals stay dead
- Rotator can't re-enable them
- Requires explicit T action to revive a signal

## Alternatives Considered
- Just use `*_ENABLED = False`: rotator can override
- Delete signal files: too drastic, might need reference
