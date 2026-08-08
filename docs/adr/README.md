# Architecture Decision Records (ADRs)

ADRs document key architectural decisions made in the Hermes trading system. They capture the context, decision, and consequences of each choice.

## When to Create an ADR

- New signal design pattern
- Database schema change
- New integration (exchange, API)
- Policy change (kill switches, confluence rules)
- Infrastructure change (systemd, timers)

## Format

Each ADR is a numbered file: `NNN-short-title.md`

```markdown
# ADR-NNN: Title

**Date**: YYYY-MM-DD
**Status**: Accepted/Superseded/Deprecated
**Deciders**: [who]

## Context
What situation forced this decision?

## Decision
What did we decide?

## Consequences
What are the trade-offs?

## Alternatives Considered
What else was evaluated?
```

## Index

| ADR | Title | Date |
|-----|-------|------|
| 001 | PostgreSQL for brain DB | 2026-07-19 |
| 002 | ATR-based SL/TP | 2026-07-19 |
| 003 | Signal confluence required | 2026-08-06 |
| 004 | Confluence kill-switches | 2026-08-06 |
| 005 | Guardian owns HL reconciliation | 2026-07-19 |
| 006 | Position manager owns ATR SL/TP | 2026-07-19 |
| 007 | NEVER_REENABLE_FLAGS policy | 2026-08-05 |
| 008 | Pipeline lock prevents overlaps | 2026-07-19 |
