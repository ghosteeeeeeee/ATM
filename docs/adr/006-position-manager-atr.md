# ADR-006: Position Manager Owns ATR SL/TP Computation

**Date**: 2026-07-19
**Status**: Accepted
**Deciders**: T

## Context
SL/TP needs to be recomputed every cycle based on current ATR, price, and trailing state. Multiple components need consistent SL/TP.

## Decision
- `position_manager.py` computes SL/TP via `tpsl_utils.compute_atr_sl_tp()`
- Writes to DB every cycle (before hit detection)
- Guardian reads SL/TP from DB (never computes its own)
- Initial SL set by `decider_run.py` at trade open

## Consequences
- Single source of truth for SL/TP computation
- SL/TP always fresh (recomputed every minute)
- Guardian and position_manager don't conflict on SL/TP

## Alternatives Considered
- Guardian computes SL/TP: duplicated logic
- Static SL/TP at entry: doesn't adapt to volatility
