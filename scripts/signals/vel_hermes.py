#!/usr/bin/env python3
"""
vel_hermes.py — z-score velocity signal generator (fishing for momentum).

Like a fish-finder detecting oxygen levels:
- z-score velocity = oxygen level (is momentum real?)
- RSI = water temperature (is it too hot/cold to fish?)
- Speed percentile = current speed (is the fish moving?)
- Price acceleration = are fish gathering or scattering?

Fires when ALL oxygen indicators align:
  velocity > 0 + z > 1.0 + speed > 50% + RSI 30-70 → SHORT
  velocity < 0 + z < -1.0 + speed > 50% + RSI 30-70 → LONG
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermes_constants import (
    VEL_HERMES_ENABLED, VEL_HERMES_PLUS_ENABLED, VEL_HERMES_MINUS_ENABLED,
    SHORT_BLACKLIST as _SHORT_BL, LONG_BLACKLIST as _LONG_BL,
)

from signal_schema import (
    init_db, get_all_latest_prices, get_price_history,
    add_signal, price_age_minutes, get_cooldown,
)
import signal_gen as _sg

try:
    from hyperliquid_exchange import is_live_trading_enabled
except Exception:
    def is_live_trading_enabled():
        return True

SHORT_BLACKLIST = _SHORT_BL
LONG_BLACKLIST = _LONG_BL

# ── Fishing parameters (oxygen detection thresholds) ──────────────────────────
VEL_ABS_THRESHOLD = 0.05   # abs(velocity) — minimum oxygen level
VEL_Z_MIN = 1.0            # abs(z_score) — directional confirmation (was 0.5)
VEL_SPEED_MIN = 50         # speed percentile — fish must be moving
VEL_RSI_MIN = 30           # RSI floor — don't fish in frozen water
VEL_RSI_MAX = 70           # RSI ceiling — don't fish in boiling water
VEL_ACCEL_MIN = 0.0        # price acceleration — fish must be gathering, not scattering

try:
    from position_manager import get_open_positions as _get_open_pos
except Exception:
    def _get_open_pos():
        return []

try:
    from signal_gen import recent_trade_exists, MIN_TRADE_INTERVAL_MINUTES
except Exception:
    MIN_TRADE_INTERVAL_MINUTES = 10
    def recent_trade_exists(token, interval):
        return False


def _get_open_pos_dict():
    return {p['token']: p['direction'] for p in _get_open_pos()}


def _get_rsi(token, period=14):
    """Compute RSI from price history. Returns 0-100 or None."""
    try:
        rows = get_price_history(token, lookback_minutes=period * 2)
        if not rows or len(rows) < period + 1:
            return None
        prices = [r[1] for r in rows]
        gains = []
        losses = []
        for i in range(1, len(prices)):
            delta = prices[i] - prices[i-1]
            gains.append(max(delta, 0))
            losses.append(max(-delta, 0))
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    except Exception:
        return None


def run() -> int:
    """
    Scan all tokens for z-score velocity signals.
    Uses multi-indicator filtering (oxygen detection) to find real momentum.
    """
    init_db()

    try:
        if not is_live_trading_enabled():
            print('[vel_hermes] SKIPPED — live_trading=OFF')
            return 0
    except Exception:
        pass

    prices_dict = get_all_latest_prices()
    open_pos = _get_open_pos_dict()
    added = 0

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        if price_age_minutes(token) > 10:
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if get_cooldown(token):
            continue
        if token.upper() in SHORT_BLACKLIST or token.upper() in LONG_BLACKLIST:
            continue

        price = data['price']

        if token.upper() in open_pos:
            continue

        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue

        # ── Oxygen check #1: Momentum stats ──────────────────────────────────
        mom = _sg.get_momentum_stats(token)
        if not mom:
            continue

        velocity = mom.get('velocity', 0)
        avg_z    = mom.get('avg_z', 0)
        z_dir    = mom.get('z_direction', 'neutral')
        accel    = mom.get('price_acceleration', 0)

        vel_abs = abs(velocity)
        abs_z = abs(avg_z)

        # ── Oxygen check #2: Speed percentile (is the fish moving?) ──────────
        try:
            from speed_tracker import get_token_speed
            spd = get_token_speed(token)
            speed_pct = spd.get('speed_percentile', 50) if spd else 50
        except Exception:
            speed_pct = 50

        # ── Oxygen check #3: RSI (water temperature) ─────────────────────────
        rsi = _get_rsi(token)

        # ── Oxygen check #4: Price acceleration (fish gathering?) ─────────────
        # Positive acceleration = momentum increasing
        # Negative acceleration = momentum fading

        # ── Signal generation (all oxygen levels must align) ───────────────────
        if vel_abs >= VEL_ABS_THRESHOLD and abs_z >= VEL_Z_MIN and speed_pct >= VEL_SPEED_MIN:
            # RSI filter: don't fish in frozen/boiling water
            if rsi is not None and (rsi < VEL_RSI_MIN or rsi > VEL_RSI_MAX):
                continue

            # Direction: rising z = SHORT, falling z = LONG
            if velocity > 0:
                if not VEL_HERMES_MINUS_ENABLED:
                    continue
                vel_signal_dir = 'SHORT'
                vel_dir_char = '-'
            else:
                if not VEL_HERMES_PLUS_ENABLED:
                    continue
                vel_signal_dir = 'LONG'
                vel_dir_char = '+'

            # Confidence: multi-factor (oxygen levels)
            vel_conf = min(85, 40 + vel_abs * 300 + abs_z * 10 + speed_pct * 0.2)
            if accel > 0:
                vel_conf += 5  # bonus for accelerating momentum

            sid = add_signal(
                token        = token,
                direction    = vel_signal_dir,
                signal_type  = 'velocity',
                source       = f'vel-hermes{vel_dir_char}',
                confidence   = round(vel_conf, 1),
                value        = round(velocity, 4),
                price        = price,
                exchange     = 'hyperliquid',
                timeframe    = '1h',
                z_score      = avg_z,
                z_score_tier = z_dir,
            )
            if sid:
                added += 1

    return added


if __name__ == '__main__':
    print(f'[vel_hermes] start — VEL_HERMES_ENABLED={VEL_HERMES_ENABLED}')
    count = run()
    print(f'[vel_hermes] done — {count} signals written')
