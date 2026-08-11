# Transcript Mining Report

**Source:** Finally FULL Portfolio Trade Automation with AI - Claude MCP Routines IT WORKS
**Date:** 2026-08-11

## TL;DR

- Our system **already does everything** this video describes — deterministic scoring, real-time execution, position management, trailing stops
- The ONE gap: **no trade summary notifications** — we have a Telegram bot token but no daily digest
- Video's approach (LLM per trade decision) is slower and more expensive than our deterministic path
- Signum MCP = their wrapper around HyperLiquid execution — we already have ccxt HyperLiquid integration

## Ideas

### 1. Daily Telegram Digest
- **What**: After each daily cycle (or on a timer), send a Telegram message summarizing: portfolio value, trades opened/closed, win rate, PnL
- **Why Hermes**: We have zero notifications. If something breaks at 3am, we don't know until we check the dashboard. The Telegram bot token already exists in `/root/.secrets/telegram-secrets.json` — we just need a chat_id and a sender script
- **Where**: New script `scripts/daily_digest.py`, systemd timer (daily)
- **Effort**: small — ~50 lines, pattern already exists in ai_decider.py lines 2276-2289
- **Priority**: Quick win — real safety improvement

### 2. Execution Summary on Trade Close
- **What**: When a trade closes (win or loss), send a one-liner to Telegram: "CLOSED BTC LONG +$0.42 (2.1%)"
- **Why Hermes**: Immediate visibility into what's happening without checking dashboard
- **Where**: `position_manager.py` — hook into the close path
- **Effort**: trivial — ~15 lines, reuse existing Telegram pattern from ai_decider.py
- **Priority**: Quick win

### 3. AI-Filtered Coin Universe
- **What**: Video's AI picks which coins to trade. We scan all ~500 tokens. Could use a simple filter (e.g., only trade tokens with >$1M daily volume or trending z-scores) to reduce noise
- **Why Hermes**: signal_gen.py already filters by data freshness and cooldown, but doesn't filter by "is this coin worth trading." Adding a volume/liquidity gate could reduce bad trades on illiquid tokens
- **Where**: `signal_gen.py` — add filter before score computation
- **Effort**: small — ~10 lines
- **Priority**: Worth discussing — may already be handled by z-score percentile logic (illiquid tokens have noisy z-scores that don't reach thresholds)

## Quick Wins (do today)
1. **Telegram daily digest** — 50 lines, systemd timer, real safety value
2. **Trade close notification** — 15 lines in position_manager.py

## Worth Discussing
1. **Volume/liquidity coin filter** — might reduce noise on illiquid tokens

## Skip
- **Claude Routines / Signum MCP** — we already have faster deterministic execution
- **Plain English strategy prompt** — our strategy is encoded in Python, which is more precise and auditable
- **Email summary** — Telegram is better for real-time alerts; email is overkill for this
- **Daily execution schedule** — our system runs every minute, which is better for scalping/mean-reversion
