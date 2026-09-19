#!/usr/bin/env python3
"""
continuum_ma.py — MA-smoothed continuum score crossover detection.

When the raw continuum score crosses above its Moving Average, momentum is
building. When it crosses below, momentum is fading. The MA slope confirms
direction. This is a "derivative of a derivative" — smoother than raw score,
faster than waiting for phase transitions.

Signal types:
  - continuum_ma_long : LONG when score crosses above MA
  - continuum_ma_short : SHORT when score crosses below MA

Data source: continuum.db → continuum_states (state_score field)
"""
import sys, os, sqlite3, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from signal_schema import add_signal, get_cooldown, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    CONTINUUM_MA_ENABLED,
    CONTINUUM_MA_LONG_ENABLED,
    CONTINUUM_MA_SHORT_ENABLED,
    CONTINUUM_MA_PERIOD,
    CONTINUUM_MA_SCORE_THRESHOLD,
    CONTINUUM_MA_MIN_SLOPE,
    CONTINUUM_MA_COOLDOWN_RECORDS,
    CONTINUUM_MA_STALENESS_MIN,
    CONTINUUM_MA_CONF_BASE,
    CONTINUUM_MA_CONF_SPREAD_MULT,
    CONTINUUM_MA_CONF_SLOPE_MULT,
    CONTINUUM_MA_CONF_ZONE_BONUS,
    CONTINUUM_MA_CONF_CAP,
)

SIGNAL_TYPE_LONG = 'continuum_ma_long'
SIGNAL_TYPE_SHORT = 'continuum_ma_short'
SOURCE_LONG = 'continuum-ma+'
SOURCE_SHORT = 'continuum-ma-'

CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')


def _get_recent_scores(token='BTC', limit=30):
    """Get recent state_score values. Returns list of (score, ema300_pos, ts) oldest-first."""
    conn = None
    try:
        conn = sqlite3.connect(CONTINUUM_DB, timeout=10)
        cur = conn.execute(
            "SELECT state_score, ema300_position, ts FROM continuum_states "
            "WHERE token = ? ORDER BY ts DESC LIMIT ?",
            (token.upper(), limit)
        )
        rows = cur.fetchall()
        return [(r[0], r[1], r[2]) for r in reversed(rows)] if rows else []
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _compute_ma(values, period):
    """Simple moving average. Returns list same length as values (NaN-padded)."""
    ma = []
    for i in range(len(values)):
        if i < period - 1:
            ma.append(None)
        else:
            ma.append(sum(values[i - period + 1:i + 1]) / period)
    return ma


def _compute_slope(ma_values, window=3):
    """Compute slope of MA over last `window` non-None values. Returns float."""
    valid = [v for v in ma_values[-window:] if v is not None]
    if len(valid) < 2:
        return 0.0
    return (valid[-1] - valid[0]) / len(valid)


def detect(token='BTC'):
    """
    Detect continuum MA crossover signal.

    LONG:  raw score crosses ABOVE MA + MA slope positive + score > threshold
    SHORT: raw score crosses BELOW MA + MA slope negative + score < threshold
    """
    scores_raw = _get_recent_scores(token, limit=CONTINUUM_MA_PERIOD + 10)
    if len(scores_raw) < CONTINUUM_MA_PERIOD + 2:
        return None

    # Check staleness
    latest_ts = scores_raw[-1][2]
    age_minutes = (time.time() - latest_ts) / 60
    if age_minutes > CONTINUUM_MA_STALENESS_MIN:
        return None

    # Extract scores and compute MA
    scores = [s[0] for s in scores_raw if s[0] is not None]
    if len(scores) < CONTINUUM_MA_PERIOD + 2:
        return None

    ma = _compute_ma(scores, CONTINUUM_MA_PERIOD)

    # Current and previous values
    raw_now = scores[-1]
    raw_prev = scores[-2]
    ma_now = ma[-1]
    ma_prev = ma[-2]

    if ma_now is None or ma_prev is None:
        return None

    # Detect crossover
    crossed_above = raw_prev <= ma_prev and raw_now > ma_now
    crossed_below = raw_prev >= ma_prev and raw_now < ma_now

    if not crossed_above and not crossed_below:
        return None

    # MA slope confirmation
    slope = _compute_slope(ma)

    # EMA300 position (macro trend alignment)
    ema300_pos = scores_raw[-1][1]

    if crossed_above:
        # LONG conditions
        if raw_now < CONTINUUM_MA_SCORE_THRESHOLD:
            return None  # score too low
        if slope < CONTINUUM_MA_MIN_SLOPE:
            return None  # slope not positive enough
        if ema300_pos != 'AT' and ema300_pos != 'ABOVE':
            return None  # macro trend not aligned

        # Confidence scoring
        spread = abs(raw_now - ma_now)
        spread_bonus = min(20, spread * CONTINUUM_MA_CONF_SPREAD_MULT)
        slope_bonus = min(15, abs(slope) * CONTINUUM_MA_CONF_SLOPE_MULT)
        zone_bonus = CONTINUUM_MA_CONF_ZONE_BONUS if raw_now > 80 else 0
        conf = CONTINUUM_MA_CONF_BASE + spread_bonus + slope_bonus + zone_bonus
        conf = min(CONTINUUM_MA_CONF_CAP, conf)

        return {
            'direction': 'LONG',
            'confidence': conf,
            'value': raw_now,
            'price': scores_raw[-1][0] if scores_raw[-1][0] else 0,
            'reason': f'ma_cross_up_{raw_prev:.1f}_to_{raw_now:.1f}_ma{ma_now:.1f}',
        }

    if crossed_below:
        # SHORT conditions
        if raw_now > (100 - CONTINUUM_MA_SCORE_THRESHOLD):
            return None  # score too high
        if slope > -CONTINUUM_MA_MIN_SLOPE:
            return None  # slope not negative enough
        if ema300_pos != 'AT' and ema300_pos != 'BELOW':
            return None  # macro trend not aligned

        spread = abs(raw_now - ma_now)
        spread_bonus = min(20, spread * CONTINUUM_MA_CONF_SPREAD_MULT)
        slope_bonus = min(15, abs(slope) * CONTINUUM_MA_CONF_SLOPE_MULT)
        zone_bonus = CONTINUUM_MA_CONF_ZONE_BONUS if raw_now < 20 else 0
        conf = CONTINUUM_MA_CONF_BASE + spread_bonus + slope_bonus + zone_bonus
        conf = min(CONTINUUM_MA_CONF_CAP, conf)

        return {
            'direction': 'SHORT',
            'confidence': conf,
            'value': raw_now,
            'price': scores_raw[-1][0] if scores_raw[-1][0] else 0,
            'reason': f'ma_cross_down_{raw_prev:.1f}_to_{raw_now:.1f}_ma{ma_now:.1f}',
        }

    return None


def run():
    """Entry point for signals_runner."""
    if not CONTINUUM_MA_ENABLED:
        return 0

    sig = detect('BTC')
    if not sig:
        return 0

    direction = sig['direction']

    # Per-direction kill-switch
    if direction == 'LONG' and not CONTINUUM_MA_LONG_ENABLED:
        return 0
    if direction == 'SHORT' and not CONTINUUM_MA_SHORT_ENABLED:
        return 0

    # Cooldown
    if get_cooldown('BTC', direction=direction):
        return 0

    sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
    source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

    ok = add_signal(
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

    if ok:
        set_cooldown('BTC', direction, hours=CONTINUUM_MA_COOLDOWN_RECORDS * 0.5 / 60.0)
        print(f"[continuum-ma] Signal: {direction} | Score={sig['value']:.1f} | "
              f"Conf={sig['confidence']} | reason={sig['reason']}")
        return 1

    return 0


if __name__ == '__main__':
    print("=== Continuum MA Signal — Diagnostic ===\n")

    scores_raw = _get_recent_scores('BTC', limit=CONTINUUM_MA_PERIOD + 10)
    if len(scores_raw) < CONTINUUM_MA_PERIOD + 2:
        print("Not enough data")
        exit()

    scores = [s[0] for s in scores_raw if s[0] is not None]
    ma = _compute_ma(scores, CONTINUUM_MA_PERIOD)

    print(f"Last 5 scores: {[f'{s:.1f}' for s in scores[-5:]]}")
    print(f"Last 5 MA values: {[f'{v:.1f}' if v else 'None' for v in ma[-5:]]}")
    print(f"Slope: {_compute_slope(ma):.3f}")
    print(f"EMA300 position: {scores_raw[-1][1]}")

    sig = detect('BTC')
    if sig:
        print(f"\nSignal: {sig['direction']} | Conf={sig['confidence']} | {sig['reason']}")
    else:
        print("\nNo signal")
