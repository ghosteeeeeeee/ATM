# ADR-004: Confluence Kill-Switches for Low-WR Combos

**Date**: 2026-08-06
**Status**: Accepted
**Deciders**: T + CEO

## Context
Some signal combos consistently lose money. Need to block specific combos without disabling individual signals.

## Decision
- `CONFLUENCE_KILL_SWITCHES` dict in `hermes_constants.py`
- Maps combo patterns to reasons
- Compactor checks kills before approving combos
- Example: `bb_bounce+ma100-cross` blocked at 43% WR

## Consequences
- Can surgically block bad combos
- Individual signals still work in other combos
- Requires manual monitoring to add new kills

## Alternatives Considered
- Disable signals entirely: too broad, kills good combos
- Auto-disable by WR: too aggressive, needs human judgment
