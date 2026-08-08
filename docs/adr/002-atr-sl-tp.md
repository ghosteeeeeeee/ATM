# ADR-002: ATR-Based SL/TP with Trailing

**Date**: 2026-07-19
**Status**: Accepted
**Deciders**: T

## Context
Fixed-percentage SL/TP doesn't adapt to market volatility. Low-vol tokens get stopped out on noise; high-vol tokens get squeezed.

## Decision
- SL/TP computed from ATR(14): `SL = k × ATR`, `TP = k × ATR × multiplier`
- k adapts to volatility tier (low/normal/high)
- Trailing: SL tightens as price moves in favor
- MIN floors prevent too-tight SL (1.0% init, 1.2% established)

## Consequences
- SL/TP recomputed every pipeline cycle by position_manager
- tpsl_utils.py is the sole authority for SL/TP computation
- Guardian reads SL/TP from DB, doesn't compute its own

## Alternatives Considered
- Fixed % SL: doesn't adapt to volatility
- ATR only (no trailing): can't lock in profits
