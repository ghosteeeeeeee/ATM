# ADR-005: Guardian Owns HL Position Reconciliation

**Date**: 2026-07-19
**Status**: Accepted
**Deciders**: T

## Context
HL positions and DB trades can drift apart due to race conditions, API failures, or manual trades.

## Decision
- `hl-sync-guardian.py` runs every 60s via systemd timer
- Reconciles HL positions with DB trades
- Creates orphan paper trades for HL positions not in DB
- Closes DB trades when HL position is gone
- Never overwrites ATR SL/TP (position_manager owns that)

## Consequences
- Guardian is the source of truth for HL ↔ DB sync
- Guardian can create trades (orphan recovery)
- Guardian does NOT modify SL/TP (that's position_manager's job)

## Alternatives Considered
- Position manager does reconciliation: too coupled
- Manual reconciliation: doesn't scale
