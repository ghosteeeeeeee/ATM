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
    AI_TRADER_RSI_DRIFT_MAX,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

STATE_FILE = os.path.join(HERMES_DATA, 'ai_trader_state.json')
# ponytail: watchdog agents sometimes write here instead (2026-10-20 SAND pick
# landed in www while signal read HERMES_DATA — pick starved in limbo).
# Dual-path load; collapse to single path once agent prompts are fixed.
STATE_FILE_ALT = '/var/www/hermes/data/ai_trader_state.json'
_active_state_path = STATE_FILE
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


def _read_state_file(path):
    """Read one state file. Returns dict or None."""
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if not state or not isinstance(state, dict) or not state.get('timestamp'):
        return None
    return state


def _load_state():
    """Load freshest AI trader state. Checks HERMES_DATA and www fallback path.

    Returns dict or None if stale/missing. Sets _active_state_path so
    reject/fired_at writes land on the file that was actually read.
    """
    global _active_state_path
    best = None
    for path in (STATE_FILE, STATE_FILE_ALT):
        state = _read_state_file(path)
        if state and (best is None or str(state.get('timestamp', '')) > str(best.get('timestamp', ''))):
            best = state
            _active_state_path = path
    state = best
    if not state:
        return None

    # Skip rejected picks — watchdog should pick a different coin
    if state.get('rejected_at'):
        return None

    # Check freshness — state older than TTL is stale
    try:
        ts_dt = datetime.fromisoformat(state['timestamp'].replace('Z', '+00:00'))
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)
        age_min = (datetime.now(timezone.utc) - ts_dt).total_seconds() / 60
        if age_min > AI_TRADER_STATE_TTL_MINUTES:
            return None
    except (ValueError, AttributeError, KeyError):
        return None

    return state


def _mark_rejected(state, reason):
    """Mark state as rejected so watchdog picks a different coin next cycle."""
    state['rejected_at'] = datetime.now(timezone.utc).isoformat()
    state['reject_reason'] = reason
    try:
        tmp_path = _active_state_path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, _active_state_path)
    except Exception:
        pass


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
        _mark_rejected(state, f'cooldown active for {token} {direction}')
        return None

    # Price freshness (BUG 7: use constant, handle 999 = no data)
    if token:
        age = price_age_minutes(token)
        if age is not None and age >= 999:
            _log(f"  [AI-TRADER] {token} {direction} rejected: no price data")
            _mark_rejected(state, f'no price data for {token}')
            return None
        if age is not None and age > AI_TRADER_PRICE_MAX_AGE_MINUTES:
            _log(f"  [AI-TRADER] {token} {direction} rejected: price {age:.0f} min old")
            _mark_rejected(state, f'price {age:.0f} min old for {token}')
            return None

    # RSI drift guard (brain_auditor 2026-10-17): pick RSI can collapse before fill.
    # APT pick 57.1 → fill 33.7 (Δ23.4) → hard_max_loss. Require |fire_rsi - pick_rsi|
    # <= AI_TRADER_RSI_DRIFT_MAX. Fail-open if either RSI unavailable (old state format).
    fire_rsi = None
    try:
        from rsi_utils import compute_rsi_1m
        fire_rsi = compute_rsi_1m(token)
    except Exception:
        fire_rsi = None
    pick_rsi = state.get('rsi_at_pick')
    try:
        pick_rsi = float(pick_rsi) if pick_rsi is not None else None
    except (TypeError, ValueError):
        pick_rsi = None
    if fire_rsi is not None and pick_rsi is not None:
        drift = abs(fire_rsi - pick_rsi)
        if drift > AI_TRADER_RSI_DRIFT_MAX:
            _log(
                f"  [AI-TRADER] {token} {direction} rejected: RSI drift "
                f"pick={pick_rsi:.1f} fire={fire_rsi:.1f} Δ={drift:.1f} "
                f"> {AI_TRADER_RSI_DRIFT_MAX}"
            )
            _mark_rejected(state, f'RSI drift {pick_rsi:.1f}→{fire_rsi:.1f} Δ={drift:.1f}')
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
            'ai_pick_rsi': pick_rsi,
            'ai_fire_rsi': fire_rsi,
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
            tmp_path = _active_state_path + '.tmp'
            with open(tmp_path, 'w') as f:
                json.dump(state, f, indent=2)
            os.replace(tmp_path, _active_state_path)
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
