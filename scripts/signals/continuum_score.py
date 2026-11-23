#!/usr/bin/env python3
"""
continuum_score.py — Fire signals on continuum score STATE TRANSITIONS.

Two transition signals (T directive 2026-11-23):

1. LONG: score stayed BELOW 50 for an extended period (30+ min),
   then hits 90+ FOR THE FIRST TIME. (Bear exhaustion → first bullish breakout)

2. SHORT: after a recent 90+ peak (within 4 hours), score drops
   back to 0. (Bull exhaustion → full reversal)

Cooldown: 5 minutes between signals per direction.
"""
import sys, os, sqlite3, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from signal_schema import add_signal, get_cooldown, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    CONTINUUM_SCORE_ENABLED,
    CONTINUUM_SCORE_LONG_ENABLED,
    CONTINUUM_SCORE_SHORT_ENABLED,
    CONTINUUM_SCORE_COOLDOWN_MIN,
    CONTINUUM_SCORE_STALENESS_MIN,
    CONTINUUM_SCORE_BELOW_THRESHOLD,
    CONTINUUM_SCORE_BELOW_MINUTES,
    CONTINUUM_SCORE_LONG_TRIGGER,
    CONTINUUM_SCORE_SHORT_TRIGGER,
    CONTINUUM_SCORE_SHORT_TOLERANCE,
    CONTINUUM_SCORE_SHORT_PEAK_WINDOW,
    CONTINUUM_SCORE_TRANSITION_CONF,
)

SIGNAL_TYPE_LONG = 'continuum_score_long'
SIGNAL_TYPE_SHORT = 'continuum_score_short'
SOURCE_LONG = 'continuum+'
SOURCE_SHORT = 'continuum-'

CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')


def _get_recent_scores(token: str = 'BTC', minutes: int = None, limit: int = 500):
    """Get recent scores from DB as [(score, price, ts), ...] oldest-first.

    If minutes given, only rows within that window (from now).
    """
    conn = None
    try:
        conn = sqlite3.connect(CONTINUUM_DB, timeout=10)
        if minutes is not None:
            cutoff = int(time.time()) - minutes * 60
            cur = conn.execute(
                "SELECT state_score, price, ts FROM continuum_states "
                "WHERE token = ? AND ts >= ? ORDER BY ts ASC LIMIT ?",
                (token.upper(), cutoff, limit)
            )
        else:
            cur = conn.execute(
                "SELECT state_score, price, ts FROM continuum_states "
                "WHERE token = ? ORDER BY ts DESC LIMIT ?",
                (token.upper(), limit)
            )
            rows = cur.fetchall()
            rows.reverse()  # oldest-first
            return [(r[0], r[1], r[2]) for r in rows if r[0] is not None]
        rows = cur.fetchall()
        return [(r[0], r[1], r[2]) for r in rows if r[0] is not None]
    except Exception as e:
        print(f"[continuum-score] Error reading DB: {e}")
        return []
    finally:
        if conn:
            conn.close()


def detect(token: str = 'BTC'):
    """Detect state-transition signal (LONG or SHORT)."""
    # Pull history: long window for peak detection, enough rows for below-50 duration
    scores = _get_recent_scores(token, minutes=CONTINUUM_SCORE_SHORT_PEAK_WINDOW, limit=2000)
    if len(scores) < 2:
        return None

    latest_score, latest_price, latest_ts = scores[-1]

    # Staleness check
    age_minutes = (time.time() - latest_ts) / 60
    if age_minutes > CONTINUUM_SCORE_STALENESS_MIN:
        return None

    # ── SHORT: score hit 0 after a recent 90+ peak ────────────────────────────
    if latest_score <= CONTINUUM_SCORE_SHORT_TRIGGER + CONTINUUM_SCORE_SHORT_TOLERANCE:
        # Was there a 90+ peak within the window?
        peak_scores = [s for s, _, _ in scores[:-1] if s >= CONTINUUM_SCORE_LONG_TRIGGER]
        if peak_scores:
            peak = max(peak_scores)
            conf = CONTINUUM_SCORE_TRANSITION_CONF + min(10, peak / 10)
            return {
                'direction': 'SHORT',
                'confidence': min(92, conf),
                'value': latest_score,
                'price': latest_price,
                'reason': f'peak_{peak:.0f}_then_zero',
            }

    # ── LONG: prolonged below 50, then FIRST hit of 90+ ──────────────────────
    if latest_score >= CONTINUUM_SCORE_LONG_TRIGGER:
        # Find where the current "above 90" streak started
        above_90_start = len(scores) - 1
        for i in range(len(scores) - 1, -1, -1):
            if scores[i][0] >= CONTINUUM_SCORE_LONG_TRIGGER:
                above_90_start = i
            else:
                break

        # Must be the FIRST hit — previous row must be below trigger
        if above_90_start > 0 and scores[above_90_start - 1][0] < CONTINUUM_SCORE_LONG_TRIGGER:
            # Check extended period below 50 BEFORE this streak
            below_since = None
            for i in range(above_90_start - 1, -1, -1):
                if scores[i][0] < CONTINUUM_SCORE_BELOW_THRESHOLD:
                    below_since = i
                else:
                    break

            if below_since is not None:
                below_minutes = (scores[above_90_start - 1][2] - scores[below_since][2]) / 60
                if below_minutes >= CONTINUUM_SCORE_BELOW_MINUTES:
                    conf = CONTINUUM_SCORE_TRANSITION_CONF + min(10, latest_score / 10)
                    return {
                        'direction': 'LONG',
                        'confidence': min(92, conf),
                        'value': latest_score,
                        'price': latest_price,
                        'reason': f'below50_{below_minutes:.0f}m_then_{latest_score:.0f}',
                    }

    return None


def scan_signals():
    """Scan for continuum score signals."""
    if not CONTINUUM_SCORE_ENABLED:
        return 0

    sig = detect('BTC')
    if not sig:
        return 0

    direction = sig['direction']

    # Layer 1: per-direction kill-switch
    if direction == 'LONG' and not CONTINUUM_SCORE_LONG_ENABLED:
        return 0
    if direction == 'SHORT' and not CONTINUUM_SCORE_SHORT_ENABLED:
        return 0

    # Cooldown
    if get_cooldown('BTC', direction=direction):
        return 0

    sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
    source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

    sid = add_signal(
        token='BTC',
        direction=direction,
        signal_type=sig_type,
        source=source,
        confidence=sig['confidence'],
        value=sig['value'],
        price=sig['price'],
        exchange='hyperliquid',
        timeframe='1m',
    )

    if sid:
        set_cooldown('BTC', direction, hours=CONTINUUM_SCORE_COOLDOWN_MIN / 60.0)
        print(f"[continuum-score] Signal fired: {direction} | Score={sig['value']:.1f} | "
              f"Conf={sig['confidence']} | reason={sig['reason']}")

    return 1 if sid else 0


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    print("=== Continuum Score Transition Signal Test ===")
    scores = _get_recent_scores('BTC', minutes=CONTINUUM_SCORE_SHORT_PEAK_WINDOW, limit=2000)
    print(f"Rows in window: {len(scores)}")
    if scores:
        print(f"Latest score: {scores[-1][0]:.1f} @ {scores[-1][2]}")
        peak = max(s for s, _, _ in scores)
        print(f"Peak in window: {peak:.1f}")

        # LONG check
        below_50_streak = 0
        for i in range(len(scores) - 1, -1, -1):
            if scores[i][0] < CONTINUUM_SCORE_BELOW_THRESHOLD:
                below_50_streak += 1
            else:
                break
        print(f"Current streak below 50: {below_50_streak} rows")

        sig = detect()
        if sig:
            print(f"SIGNAL: {sig['direction']} | Conf={sig['confidence']} | reason={sig['reason']}")
        else:
            print("No signal")
