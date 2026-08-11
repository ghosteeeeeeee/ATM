# Transcript Mining Report

**Source:** Finally FULL Portfolio Trade Automation with AI - Claude MCP Routines IT WORKS
**Date:** 2026-08-11

## TL;DR

- Our system **already does everything** this video describes — deterministic scoring, real-time execution, position management, trailing stops
- Video's approach (LLM per trade decision) is slower and more expensive than our deterministic path
- Signum MCP = their wrapper around HyperLiquid execution — we already have ccxt HyperLiquid integration
- No actionable gaps found — system is ahead on all fronts

## Ideas

### 1. AI-Filtered Coin Universe
- **What**: Video's AI picks which coins to trade. We scan all ~500 tokens. Could use a simple filter (e.g., only trade tokens with >$1M daily volume or trending z-scores) to reduce noise
- **Why Hermes**: signal_gen.py already filters by data freshness and cooldown, but doesn't filter by "is this coin worth trading." Adding a volume/liquidity gate could reduce bad trades on illiquid tokens
- **Where**: `signal_gen.py` — add filter before score computation
- **Effort**: small — ~10 lines
- **Priority**: Worth discussing — may already be handled by z-score percentile logic (illiquid tokens have noisy z-scores that don't reach thresholds)

## Worth Discussing
1. **Volume/liquidity coin filter** — might reduce noise on illiquid tokens

## Skip
- **Claude Routines / Signum MCP** — we already have faster deterministic execution
- **Plain English strategy prompt** — our strategy is encoded in Python, which is more precise and auditable
- **Email/notification summary** — dashboard covers this, no need to add
- **Daily execution schedule** — our system runs every minute, which is better for scalping/mean-reversion
