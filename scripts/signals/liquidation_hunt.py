#!/usr/bin/env python3
"""
liquidation_hunt — Contrarian signal from Hyperliquid liquidation clusters.

Thesis: When price approaches a cluster of liquidation levels (forced stops),
a cascade is imminent. We front-run the cascade by entering CONTRARIAN to the
hunt direction. If longs are about to get liquidated (price dropping toward
their liq levels), we go LONG just above the cluster — the cascade of forced
selling provides our liquidity, and the snap-back after cascade is our profit.

Data source: liquidation_clusters.json (built by liquidation_map.py every 5min)
"""
import sys, os, json, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, get_cooldown, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    LIQUIDATION_HUNT_PLUS_ENABLED,
    LIQUIDATION_HUNT_MINUS_ENABLED,
    LIQUIDATION_HUNT_COOLDOWN_HOURS,
    LIQUIDATION_HUNT_MIN_CLUSTER_USD,
    LIQUIDATION_HUNT_MIN_SCORE,
    LIQUIDATION_HUNT_CONF_BASE,
    LIQUIDATION_HUNT_CONF_CAP,
    LIQUIDATION_HUNT_STALE_SECONDS,
    STOP_HUNT_DISTANCE_PCT,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG  = 'liquidation_hunt_long'
SIGNAL_TYPE_SHORT = 'liquidation_hunt_short'
SOURCE_LONG       = 'liq-hunt+'
SOURCE_SHORT      = 'liq-hunt-'

_LIQ_CLUSTERS_FILE = os.path.join(HERMES_DATA, 'liquidation_clusters.json')


def _load_liquidation_data():
    """Load latest liquidation cluster data. Returns dict or empty dict."""
    try:
        with open(_LIQ_CLUSTERS_FILE) as f:
            data = json.load(f)
        # Check freshness — data older than threshold is stale
        age = time.time() - data.get('timestamp', 0)
        if age > LIQUIDATION_HUNT_STALE_SECONDS:
            print(f'[liq_hunt] Data stale ({age/60:.0f}min old), skipping')
            return {}
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def detect(token, data):
    """
    Check if token has a liquidation hunt opportunity.

    Returns {direction, confidence, value, price, notes} or None.
    """
    token_upper = token.upper()

    # Check stop hunt signals
    stop_hunts = data.get('stop_hunt_signals', [])
    hunt = None
    for sh in stop_hunts:
        if sh['coin'] == token_upper:
            hunt = sh
            break

    if not hunt:
        return None

    # Filter by thresholds
    if hunt['score'] < LIQUIDATION_HUNT_MIN_SCORE:
        return None
    if hunt['cluster_size_usd'] < LIQUIDATION_HUNT_MIN_CLUSTER_USD:
        return None
    if abs(hunt['distance_pct']) > STOP_HUNT_DISTANCE_PCT:
        return None

    # Determine direction — CONTRARIAN to hunt
    # If hunt is DOWN (longs getting liquidated) → go LONG (front-run cascade)
    # If hunt is UP (shorts getting liquidated) → go SHORT
    if hunt['hunt_direction'] == 'DOWN':
        direction = 'LONG'
        entry_zone = hunt['cluster_price'] * 1.002
        stop_loss = hunt['cluster_price'] * 0.985
        take_profit = hunt['current_price'] * 1.015
    elif hunt['hunt_direction'] == 'UP':
        direction = 'SHORT'
        entry_zone = hunt['cluster_price'] * 0.998
        stop_loss = hunt['cluster_price'] * 1.015
        take_profit = hunt['current_price'] * 0.985
    else:
        return None

    # Compute confidence (uses hermes_constants for base/cap)
    base_conf = min(LIQUIDATION_HUNT_CONF_CAP - 3, LIQUIDATION_HUNT_CONF_BASE + hunt['score'] * 0.4)
    book_bonus = 5 if hunt.get('book_thin') else 0
    cluster_bonus = min(10, hunt['cluster_size_usd'] / 100000)
    confidence = round(min(LIQUIDATION_HUNT_CONF_CAP, base_conf + book_bonus + cluster_bonus))

    # Risk/reward
    rr = round(abs(take_profit - entry_zone) / max(abs(entry_zone - stop_loss), 0.001), 2)

    notes = (
        f"Stop hunt {hunt['signal']}: {hunt['hunt_direction']} "
        f"cluster ${hunt['cluster_price']:.4f} ({hunt['distance_pct']:+.2f}%) "
        f"size=${hunt['cluster_size_usd']:,.0f} "
        f"({hunt['position_count']} positions, max {hunt['max_leverage']}x) "
        f"book_thin={hunt.get('book_thin', False)} RR={rr}"
    )

    return {
        'direction': direction,
        'confidence': confidence,
        'value': hunt['score'],
        'price': hunt['current_price'],
        'notes': notes,
        'metadata': {
            'cluster_price': hunt['cluster_price'],
            'distance_pct': hunt['distance_pct'],
            'cluster_size_usd': hunt['cluster_size_usd'],
            'position_count': hunt['position_count'],
            'max_leverage': hunt['max_leverage'],
            'hunt_direction': hunt['hunt_direction'],
            'book_thin': hunt.get('book_thin', False),
            'imbalance_ratio': hunt.get('imbalance_ratio', 1.0),
            'entry_zone': entry_zone,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward': rr,
        },
    }


def scan_signals():
    """Scan all tradeable tokens for liquidation hunt opportunities."""
    data = _load_liquidation_data()
    if not data:
        return 0

    # Import token list
    from tokens import get_all_tradeable_tokens
    tokens = get_all_tradeable_tokens()

    added = 0
    for token in tokens:
        token_upper = token.upper()

        sig = detect(token, data)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not LIQUIDATION_HUNT_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not LIQUIDATION_HUNT_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token_upper in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token_upper in SHORT_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token_upper, direction=direction):
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        sid = add_signal(
            token=token_upper,
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=sig['confidence'],
            value=sig.get('value'),
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='15m',
            z_score=None,
        )
        if sid:
            added += 1
            set_cooldown(token_upper, direction, hours=LIQUIDATION_HUNT_COOLDOWN_HOURS)
            print(f'[liq_hunt] {token_upper} {direction} conf={sig["confidence"]} '
                  f'cluster=${sig["metadata"]["cluster_price"]:.4f} '
                  f'({sig["metadata"]["distance_pct"]:+.2f}%) '
                  f'RR={sig["metadata"]["risk_reward"]}')

    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


# ─── Standalone Test ─────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Liquidation Hunt Signal')
    parser.add_argument('--query', help='Query a specific token')
    args = parser.parse_args()

    if args.query:
        data = _load_liquidation_data()
        if not data:
            print('No liquidation data. Run liquidation_map.py first.')
            sys.exit(1)

        sig = detect(args.query, data)
        if sig:
            m = sig['metadata']
            print(f'{sig["direction"]} {args.query.upper()} conf={sig["confidence"]}')
            print(f'  cluster=${m["cluster_price"]:.4f} ({m["distance_pct"]:+.2f}%)')
            print(f'  entry=${m["entry_zone"]:.4f} SL=${m["stop_loss"]:.4f} TP=${m["take_profit"]:.4f}')
            print(f'  RR={m["risk_reward"]} score={sig["value"]}')
            print(f'  {sig["notes"]}')
        else:
            print(f'No signal for {args.query.upper()}')
    else:
        count = scan_signals()
        print(f'\n[liq_hunt] Added {count} signals')
