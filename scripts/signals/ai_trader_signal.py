#!/usr/bin/env python3
"""
ai_trader_signal.py — AI-Driven Signal

The Trade Watchdog (opencode agent) runs every 30 minutes with full market
context: regime, coin-tracker, signal performance, open positions, recent
losses. Every hour, if slots are open, it picks ONE coin that "makes sense
right now" and writes it to ai_trader_state.json.

This signal reads that state file and emits via add_signal() so the pipeline
handles execution normally.

Architecture:
  trade-watchdog (opencode agent) → ai_trader_state.json → this signal
  → add_signal() → signals_hermes_runtime.db → signal_compactor → hotset → guardian

Signal types:
  - ai-trader+ (LONG)
  - ai-trader- (SHORT)

Pipeline: runs as a fast signal (every minute) via signals_runner.
State file is refreshed hourly by the watchdog agent.
"""

import sys, os, json, time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, price_age_minutes, get_cooldown, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    AI_TRADER_ENABLED,
    AI_TRADER_MIN_CONFIDENCE,
    AI_TRADER_STATE_TTL_MINUTES,
    AI_TRADER_COOLDOWN_HOURS,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

STATE_FILE = os.path.join(HERMES_DATA, 'ai_trader_state.json')
SIGNAL_LOG = '/var/www/hermes/logs/signals.log'

SIGNAL_TYPE = 'ai-trader'
SOURCE_LONG = 'ai-trader+'
SOURCE_SHORT = 'ai-trader-'


def _log(msg):
    print(msg)
    try:
        with open(SIGNAL_LOG, 'a') as f:
            f.write(msg + '\n')
    except Exception:
        pass


def _load_state():
    """Load AI trader state. Returns dict or None if stale/missing."""
    if not os.path.exists(STATE_FILE):
        return None

    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    if not state or not isinstance(state, dict):
        return None

    # Check freshness — state older than TTL is stale
    ts = state.get('timestamp')
    if not ts:
        return None

    try:
        ts_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)
        age_min = (datetime.now(timezone.utc) - ts_dt).total_seconds() / 60
        if age_min > AI_TRADER_STATE_TTL_MINUTES:
            return None
    except (ValueError, AttributeError):
        return None

    return state


def run():
    """Check AI trader state and emit signal if valid."""
    if not AI_TRADER_ENABLED:
        return None

    state = _load_state()
    if not state:
        return None

    token = state.get('coin', state.get('token', ''))
    direction = (state.get('direction', '') or '').upper()
    confidence = state.get('confidence', 0)
    price = state.get('price')
    reasoning = state.get('reasoning', '')

    # Validate
    if not token or direction not in ('LONG', 'SHORT'):
        return None

    if confidence < AI_TRADER_MIN_CONFIDENCE:
        _log(f"  [AI-TRADER] {token} {direction} rejected: conf {confidence} < {AI_TRADER_MIN_CONFIDENCE}")
        return None

    # Blacklist check
    blacklist = LONG_BLACKLIST if direction == 'LONG' else SHORT_BLACKLIST
    if token in blacklist:
        _log(f"  [AI-TRADER] {token} {direction} rejected: blacklisted")
        return None

    # Cooldown check
    if get_cooldown(token, direction):
        _log(f"  [AI-TRADER] {token} {direction} rejected: cooldown active")
        return None

    # Price freshness
    if token:
        age = price_age_minutes(token)
        if age is not None and age > 5:
            _log(f"  [AI-TRADER] {token} {direction} rejected: price {age:.0f} min old")
            return None

    # Determine source
    source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

    # Fire signal
    sid = add_signal(
        token=token,
        direction=direction,
        signal_type=SIGNAL_TYPE,
        source=source,
        confidence=confidence,
        value=state.get('conviction', 0),
        price=price,
        exchange='hyperliquid',
        timeframe='1h',
    )

    if sid:
        set_cooldown(token, direction, hours=AI_TRADER_COOLDOWN_HOURS)
        _log(
            f"  [AI-TRADER] {token:10s} {direction:5s} "
            f"conf={confidence:.0f}% "
            f"reasoning={reasoning[:80]}"
        )
        # Mark as fired so next hourly cycle picks a fresh pick
        state['fired_at'] = datetime.now(timezone.utc).isoformat()
        state['fired_signal_id'] = sid
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass
        return sid

    return None


if __name__ == '__main__':
    result = run()
    if result:
        print(f"AI trader signal fired: {result}")
    else:
        print("No AI trader signal (disabled, stale, or no valid pick)")
