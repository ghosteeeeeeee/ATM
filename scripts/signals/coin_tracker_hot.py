#!/usr/bin/env python3
"""
coin_tracker_hot — Signal when coin_tracker detects a hot setup.

Thesis: coin_tracker's multi-factor analysis (Wyckoff, Elliott Wave, trend,
clustering, recency) identifies high-probability setups before they move.
When setup_score crosses threshold and health is hot/ready, fire a signal.

Entry: setup_score > threshold + health in (hot, ready) + clustering alignment
Exit: Standard trailing stop from position_manager
"""
import sys, os, sqlite3, time, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes
from paths import HERMES_DATA
from coin_tracker_schema import COIN_TRACKER_DB, _table_name

from hermes_constants import (
    COIN_TRACKER_HOT_ENABLED,
    COIN_TRACKER_HOT_PLUS_ENABLED,
    COIN_TRACKER_HOT_MINUS_ENABLED,
    COIN_TRACKER_HOT_CLUSTER_MIN,
    COIN_TRACKER_HOT_RECENCY_MIN,
    COIN_TRACKER_HOT_CONF_BASE,
    COIN_TRACKER_HOT_CONF_CAP,
    COIN_TRACKER_HOT_COOLDOWN_HOURS,
    COIN_TRACKER_HOT_MIN_COMPOSITE,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG  = 'coin_tracker_hot_long'
SIGNAL_TYPE_SHORT = 'coin_tracker_hot_short'
SOURCE_LONG       = 'ct-hot+'
SOURCE_SHORT      = 'ct-hot-'


def _read_tracker_data():
    """Read latest analysis from coin_tracker.db agg_scores."""
    conn = None
    try:
        conn = sqlite3.connect(COIN_TRACKER_DB, timeout=10)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT symbol, health, composite, setup_score, setup_type, setup_details,
                   clustering_bullish, clustering_bearish, recency,
                   wyckoff_phase, ewave_count, ewave_direction,
                   trend_quality, trend_direction
            FROM agg_scores
            WHERE setup_score IS NOT NULL
        """).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_price(token):
    """Get current price from coin_tracker.db latest event."""
    from coin_tracker_schema import _table_name
    table = _table_name(token)
    conn = None
    try:
        conn = sqlite3.connect(COIN_TRACKER_DB, timeout=10)
        row = conn.execute(
            f"SELECT price FROM {table} WHERE price IS NOT NULL ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def detect(token, data):
    """Detect hot setup from coin_tracker analysis.

    Returns {direction, confidence, value, price} or None.
    """
    setup_score = data.get('setup_score') or 0
    health = data.get('health') or 'unknown'
    composite = data.get('composite') or 0
    clustering_bull = data.get('clustering_bullish') or 0
    clustering_bear = data.get('clustering_bearish') or 0
    recency = data.get('recency') or 0.5
    setup_type = data.get('setup_type') or 'NEUTRAL'
    trend_dir = data.get('trend_direction') or 'NEUTRAL'
    wyckoff = data.get('wyckoff_phase') or 'none'

    # Primary trigger: health must be hot or ready
    if health not in ('hot', 'ready'):
        return None

    # Must meet minimum composite threshold
    if composite < COIN_TRACKER_HOT_MIN_COMPOSITE:
        return None

    # Must have real structure signal (wyckoff or ewave — trend alone is not enough)
    has_structure = (
        (wyckoff and wyckoff != 'none') or
        (data.get('ewave_count') is not None)
    )
    if not has_structure:
        return None

    # Must have sufficient recency (data freshness)
    if recency < COIN_TRACKER_HOT_RECENCY_MIN:
        return None

    # Must have some directional signal
    has_direction = False
    if clustering_bull > clustering_bear and clustering_bull >= COIN_TRACKER_HOT_CLUSTER_MIN:
        has_direction = True
    elif clustering_bear > clustering_bull and clustering_bear >= COIN_TRACKER_HOT_CLUSTER_MIN:
        has_direction = True
    elif setup_type in ('LONG', 'SHORT'):
        has_direction = True
    elif trend_dir in ('BULL', 'BEAR'):
        has_direction = True

    if not has_direction:
        return None

    # Determine direction from strongest signal
    if clustering_bull > clustering_bear:
        direction = 'LONG'
    elif clustering_bear > clustering_bull:
        direction = 'SHORT'
    elif setup_type == 'LONG':
        direction = 'LONG'
    elif setup_type == 'SHORT':
        direction = 'SHORT'
    elif trend_dir == 'BULL':
        direction = 'LONG'
    elif trend_dir == 'BEAR':
        direction = 'SHORT'
    else:
        return None

    # Compute confidence from composite + bonuses
    conf = COIN_TRACKER_HOT_CONF_BASE
    conf += min(10, composite * 0.1)         # composite score bonus
    conf += min(5, setup_score * 0.1)        # setup score bonus
    conf += min(5, recency * 5)              # recency bonus
    conf += min(5, max(clustering_bull, clustering_bear) * 2)  # clustering bonus
    conf = min(conf, COIN_TRACKER_HOT_CONF_CAP)

    price = _get_price(token)
    if not price or price <= 0:
        return None

    return {
        'direction': direction,
        'confidence': conf,
        'value': setup_score,
        'price': price,
    }


def scan_signals():
    """Scan all coins for hot setups."""
    added = 0
    tracker_data = _read_tracker_data()

    for data in tracker_data:
        token = data.get('symbol')
        if not token:
            continue

        # Guards
        if price_age_minutes(token) > 10:
            continue

        sig = detect(token, data)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not COIN_TRACKER_HOT_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not COIN_TRACKER_HOT_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token, direction=direction):
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        # Build reason string
        details = []
        if data.get('wyckoff_phase') and data['wyckoff_phase'] != 'none':
            details.append(f"wyckoff={data['wyckoff_phase']}")
        if data.get('ewave_count'):
            details.append(f"ewave={data['ewave_count']}")
        if data.get('trend_direction') and data['trend_direction'] != 'NEUTRAL':
            details.append(f"trend={data['trend_direction']}")
        reason = ','.join(details) if details else 'setup_score'

        sid = add_signal(
            token=token.upper(),
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=sig['confidence'],
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
        )
        if sid:
            added += 1
            set_cooldown(token, direction, hours=COIN_TRACKER_HOT_COOLDOWN_HOURS)

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    result = run()
    print(f"coin_tracker_hot: {result} signals")
