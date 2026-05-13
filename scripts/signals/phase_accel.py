#!/usr/bin/env python3
"""
Phase Acceleration Signal — rewritten to catch LAYER-type moves.

Fires when a token's momentum enters an UPWARD phase transition:
  - building → accelerating   (classic acceleration start)
  - building → exhaustion     (fast move that skips accelerating)
  - accelerating → exhaustion (momentum building, still valid entry)
  - exhaustion → extreme     (continued momentum, still valid entry)
  - extreme → extreme        (only if avg_z < -0.3 AND velocity > 0: suppressed-price
                              bounce at extreme = LAYER pattern, still valid LONG)

Direction logic:
  - avg_z < -0.3  → suppressed price = LONG (price likely to mean-revert up)
  - avg_z >  0.3  → elevated price  = SHORT (price likely to mean-revert down)
  - avg_z neutral  → fallback to momentum_state

Key fix from original:
  - Original: only fires in 'accelerating' phase, momentum_state can't be neutral
  - New: fires on TRANSITION into accelerating/exhaustion/extreme, uses avg_z for direction
  - Original: prev_phase read from DB (stale, wrong)
  - New: prev_phase tracked IN-MEMORY per token (correct, no DB round-trip)
  - New: extreme→extreme handled via avg_z check (LAYER pattern: extreme all day but
         avg_z < 0 means suppressed price = mean-reversion bounce still valid)

Requires PHASE_ACCEL_PLUS_ENABLED / PHASE_ACCEL_MINUS_ENABLED.
PHASE_ACCEL_ENABLED controls the inline version in signal_gen.py (not used here).
"""
import sys, os, sqlite3, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, price_age_minutes


_RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'

# In-memory prev_phase tracker — updated each cycle, no DB latency
# Key: token (str), Value: prev_phase (str) from last run
_PHASE_TRACKER = {}  # token -> prev_phase string
_SEEDED = False


def _seed_tracker_from_db():
    """
    Seed _PHASE_TRACKER from momentum_cache on first run.
    Uses phase from DB as prev_phase so first cycle detects any
    transition FROM the current state (not from empty/None).
    """
    global _SEEDED
    if _SEEDED:
        return
    try:
        conn = sqlite3.connect(_RUNTIME_DB, timeout=5)
        c = conn.cursor()
        c.execute('SELECT token, phase FROM momentum_cache')
        for token, phase in c.fetchall():
            if token not in _PHASE_TRACKER:
                _PHASE_TRACKER[token] = phase  # current phase = prev_phase for first cycle
        conn.close()
        _SEEDED = True
    except Exception:
        pass  # non-fatal, tracker stays empty and works normally


def _detect_phase(percentile, velocity):
    """Classify current phase. Mirrors signal_gen.py detect_phase()."""
    PHASE_BUILDING     = 60
    PHASE_ACCELERATING = 75
    PHASE_EXHAUSTION   = 88
    PHASE_EXTREME      = 95

    if percentile < PHASE_BUILDING and abs(velocity) < 0.05:
        return 'quiet'
    if percentile >= PHASE_EXTREME:
        return 'extreme'
    if percentile >= PHASE_EXHAUSTION:
        return 'exhaustion'
    if percentile >= PHASE_ACCELERATING:
        return 'accelerating'
    if percentile >= PHASE_BUILDING:
        return 'building'
    return 'quiet'


def _get_direction(mom):
    """
    Determine direction from momentum metrics.
    Uses avg_z (mean reversion signal) as primary, with momentum_state fallback.

    avg_z < -0.2  → price suppressed  → LONG (threshold aligned with extreme→extreme check)
    avg_z >  0.2  → price elevated   → SHORT
    avg_z neutral → momentum_state   → bullish/bearish/neutral
    """
    avg_z = mom.get('avg_z', 0)
    momentum_state = mom.get('momentum_state', 'neutral')

    if avg_z < -0.2:
        return 'LONG', 'bullish'
    if avg_z > 0.2:
        return 'SHORT', 'bearish'
    if momentum_state == 'bullish':
        return 'LONG', 'bullish'
    if momentum_state == 'bearish':
        return 'SHORT', 'bearish'
    return None, 'neutral'  # skip neutral


def _is_upward_transition(prev_phase, curr_phase, velocity, avg_z):
    """
    Returns True if this is an upward (bullish) phase transition.

    Valid upward transitions (bullish momentum STARTING or BUILDING):
      - building → accelerating   (classic acceleration start) ← LAYER entry here at 04:45
      - building → exhaustion   (fast move, skipped accelerating)
      - accelerating → exhaustion (momentum still building)
      - exhaustion → extreme     (continued momentum, still valid for LONG)

    Invalid (reversal or noise):
      - quiet → building        (too early, A/B zone only)
      - quiet → accelerating     (skip building is too aggressive)
      - Any transition where velocity < 0.01
      - extreme → anything       (extreme is terminal, next move is reversal)
        EXCEPT: extreme→extreme if avg_z < -0.3 AND velocity > 0 (LAYER pattern)
    """
    if prev_phase is None:
        return False
    if velocity < 0.01:
        return False
    if prev_phase == 'extreme' and curr_phase == 'extreme':
        # Still extreme — allow signal only if avg_z < -0.2 (suppressed price at
        # extreme = mean-reversion bounce setting up, valid LONG entry) and velocity > 0.
        # LAYER: avg_z=-0.299, velocity=+0.0347 — suppressed price at extreme, still bullish.
        # Requires avg_z and positive velocity — not a reversal, still bullish.
        if avg_z < -0.2 and velocity > 0.01:
            return True
        return False  # extreme is terminal unless suppressed-price bounce
    if prev_phase == 'quiet':
        return False  # too early, not an entry zone
    if prev_phase == 'building' and curr_phase == 'accelerating':
        return True
    if prev_phase == 'building' and curr_phase in ('exhaustion', 'extreme'):
        return True
    if prev_phase == 'accelerating' and curr_phase in ('exhaustion', 'extreme'):
        return True
    if prev_phase == 'exhaustion' and curr_phase == 'extreme':
        return True
    return False


def _is_downward_transition(prev_phase, curr_phase, velocity):
    """
    Returns True if this is a downward (bearish) phase transition.
    Catches reversals from elevated price levels.

    Valid downward transitions (bearish momentum STARTING):
      - extreme → exhaustion    (first sign of reversal from peak)
      - exhaustion → accelerating (reversal building, price dropping fast)
      - exhaustion → building    (reversal confirmed)
      - extreme → building       (very fast reversal, skipped exhaustion)

    Invalid:
      - quiet → anything
      - building → anything
      - Any transition where velocity > -0.01
    """
    if prev_phase is None:
        return False
    if velocity > -0.01:
        return False
    if prev_phase == 'quiet':
        return False
    if prev_phase == 'building':
        return False
    if prev_phase == 'extreme' and curr_phase in ('exhaustion', 'building'):
        return True
    if prev_phase == 'exhaustion' and curr_phase in ('accelerating', 'building', 'extreme'):
        return True
    if prev_phase == 'accelerating' and curr_phase in ('building', 'exhaustion', 'extreme'):
        return True
    return False


def run(prices_dict):
    """
    Scan tokens for phase-acceleration signals.
    Tracks prev_phase in-memory per token.
    Fires on upward transitions into accelerating/exhaustion/extreme.

    Args:
        prices_dict: token -> {'price': float, ...} from signal_gen

    Returns:
        Number of signals written to DB.
    """
    from hermes_constants import (
        PHASE_ACCEL_ENABLED,
        PHASE_ACCEL_PLUS_ENABLED,
        PHASE_ACCEL_MINUS_ENABLED,
    )

    from signal_gen import (
        get_momentum_stats,
        is_reasonable_price,
        log,
        MIN_TRADE_INTERVAL_MINUTES,
    )

    # Seed tracker from momentum_cache on first run
    _seed_tracker_from_db()

    added = 0

    for token in list(prices_dict.keys()):
        if token.startswith('@'):
            continue
        if price_age_minutes(token) > 10:
            continue
        data = prices_dict.get(token, {})
        price = data.get('price')
        if not is_reasonable_price(token, price):
            continue

        mom = get_momentum_stats(token)
        if not mom:
            continue

        percentile      = mom.get('percentile', 50)   # pct_rank (z-score percentile) — used by momentum_cache
        percentile_long  = mom.get('percentile_long', 50)
        percentile_short = mom.get('percentile_short', 50)
        velocity          = mom.get('velocity', 0)
        # Phase uses pct_rank — matches momentum_cache phase classification exactly.
        # pct_for_phase (max of pct_long/pct_short) is used for direction confidence only.
        pct_for_phase = max(percentile_long, percentile_short)
        curr_phase = _detect_phase(percentile, velocity)

        # Get in-memory prev_phase (updated last cycle)
        prev_phase = _PHASE_TRACKER.get(token, None)

        # Update tracker with current phase for next cycle
        _PHASE_TRACKER[token] = curr_phase

        # Check for upward transition (LONG signal)
        avg_z = mom.get('avg_z', 0)
        if _is_upward_transition(prev_phase, curr_phase, velocity, avg_z):
            direction, dir_state = _get_direction(mom)
            if direction is None:
                continue  # neutral, skip
            if not PHASE_ACCEL_PLUS_ENABLED:
                continue

            # Confidence: based on pct_for_phase (phase strength), boost for velocity
            confidence = min(95.0, pct_for_phase)
            # Boost confidence if velocity is very high (strong momentum)
            if velocity > 0.05:
                confidence = min(98.0, confidence + 5)

            add_signal(
                token=token,
                direction=direction,
                signal_type='phase_accel_long',
                source='phase-accel+',
                confidence=confidence,
                value=confidence,
                price=price,
                exchange='hyperliquid',
                timeframe='accel',
                z_score=mom.get('avg_z'),
                z_score_tier=mom.get('z_direction'),
            )
            log(f'SIGNAL:  {token} {direction} phase-accel+ @{price:.6f} {confidence:.1f}% '
                f'[vel={velocity:+.3f} pct={pct_for_phase:.0f} {prev_phase}→{curr_phase}]')
            added += 1

        # Check for downward transition (SHORT signal)
        elif _is_downward_transition(prev_phase, curr_phase, velocity):
            direction, dir_state = _get_direction(mom)
            if direction is None:
                continue
            if not PHASE_ACCEL_MINUS_ENABLED:
                continue

            confidence = min(95.0, pct_for_phase)
            if velocity < -0.05:
                confidence = min(98.0, confidence + 5)

            add_signal(
                token=token,
                direction=direction,
                signal_type='phase_accel_short',
                source='phase-accel-',
                confidence=confidence,
                value=confidence,
                price=price,
                exchange='hyperliquid',
                timeframe='accel',
                z_score=mom.get('avg_z'),
                z_score_tier=mom.get('z_direction'),
            )
            log(f'SIGNAL:  {token} {direction} phase-accel- @{price:.6f} {confidence:.1f}% '
                f'[vel={velocity:+.3f} pct={pct_for_phase:.0f} {prev_phase}→{curr_phase}]')
            added += 1

    return added


if __name__ == '__main__':
    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices()
    n = run(prices)
    print(f'phase_accel: {n} signals emitted')