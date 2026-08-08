# ADR-003: Signal Confluence Required

**Date**: 2026-08-06
**Status**: Accepted
**Deciders**: T (permanent directive)

## Context
Single signals have low WR. Confluence (2+ signal types agreeing) dramatically improves WR.

## Decision
- `CONFLUENCE_REQUIRED = True` (permanent, CEO cannot toggle)
- Requires 2+ unique signal types to pass compactor
- Signals must be different types (not just different instances of same signal)

## Consequences
- Fewer trades but higher quality
- Signals need time to find co-signals (PENDING expiry = 10min)
- Some good single signals blocked, but net positive

## Alternatives Considered
- Confidence-only gate: too many low-quality entries
- Regime-only gate: doesn't capture signal agreement
