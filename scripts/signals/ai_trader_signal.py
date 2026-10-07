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
    AI_TRADER_PRICE_MAX_AGE_MINUTES,
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

    # BUG 5 fix: check if already fired (file-local dedupe, PG-independent)
    if state.get('fired_at'):
        return None

    # BUG 6 fix: uppercase token for blacklist consistency
    token = (state.get('coin', state.get('token', '')) or '').upper()
    direction = (state.get('direction', '') or '').upper()

    # BUG 2 fix: validate confidence type
    confidence = state.get('confidence') or 0
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        return None

    # BUG 4 fix: validate price type
    price = state.get('price')
    if price is not None:
        try:
            price = float(price)
        except (TypeError, ValueError):
            price = None

    # BUG 3 fix: reasoning None-safe
    reasoning = state.get('reasoning') or ''

    # Validate
    if not token or direction not in ('LONG', 'SHORT'):
        return None

    if confidence < AI_TRADER_MIN_CONFIDENCE:
        _log(f"  [AI-TRADER] {token} {direction} rejected: conf {confidence} < {AI_TRADER_MIN_CONFIDENCE}")
        return None

    # Blacklist check (BUG 6: token already uppercased above)
    blacklist = LONG_BLACKLIST if direction == 'LONG' else SHORT_BLACKLIST
    if token in blacklist:
        _log(f"  [AI-TRADER] {token} {direction} rejected: blacklisted")
        return None

    # Cooldown check
    if get_cooldown(token, direction):
        _log(f"  [AI-TRADER] {token} {direction} rejected: cooldown active")
        return None

    # Price freshness (BUG 7: use constant, handle 999 = no data)
    if token:
        age = price_age_minutes(token)
        if age is not None and age >= 999:
            _log(f"  [AI-TRADER] {token} {direction} rejected: no price data")
            return None
        if age is not None and age > AI_TRADER_PRICE_MAX_AGE_MINUTES:
            _log(f"  [AI-TRADER] {token} {direction} rejected: price {age:.0f} min old")
            return None

    # Determine source
    source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

    # Fire signal — pass reasoning in metadata for post-op analysis
    sid = add_signal(
        token=token,
        direction=direction,
        signal_type=SIGNAL_TYPE,
        source=source,
        confidence=confidence,
        value=state.get('conviction') or 0,
        price=price,
        exchange='hyperliquid',
        timeframe='1h',
        signal_metadata={
            'ai_reasoning': reasoning,
            'ai_conviction': state.get('conviction') or 0,
            'ai_pick_timestamp': state.get('timestamp'),
        },
    )

    if sid:
        set_cooldown(token, direction, hours=AI_TRADER_COOLDOWN_HOURS)
        _log(
            f"  [AI-TRADER] {token:10s} {direction:5s} "
            f"conf={confidence:.0f}% "
            f"reasoning={reasoning[:80]}"
        )
        # Mark as fired so next hourly cycle picks a fresh pick
        # BUG 7 fix: atomic write to prevent corruption
        state['fired_at'] = datetime.now(timezone.utc).isoformat()
        state['fired_signal_id'] = sid
        try:
            tmp_path = STATE_FILE + '.tmp'
            with open(tmp_path, 'w') as f:
                json.dump(state, f, indent=2)
            os.replace(tmp_path, STATE_FILE)
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
