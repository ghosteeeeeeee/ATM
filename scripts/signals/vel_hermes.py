#!/usr/bin/env python3
"""
vel_hermes.py — Standalone z-score velocity Hermes signal generator.

Fires when z-score momentum is strong (abs(velocity) >= 0.03, conf >= 50):
  velocity > 0 → SHORT (vel-hermes-)  [rising z = price above mean = bearish]
  velocity < 0 → LONG  (vel-hermes+)  [falling z = price below mean = bullish]

Extracted from signal_gen.py lines ~1710-1734.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Configuration ─────────────────────────────────────────────────────────────
# vel-hermes- (SHORT) and vel-hermes+ (LONG) thresholds.
# FIX (2026-05-07): Raised from 0.03 to 0.06 — p90 of velocity values = 0.053.
# Old 0.03 threshold barely exceeded noise; 0.06 ensures only genuine velocity fires.
VEL_HERMES_ENABLED       = False  # master kill-switch — matches hermes_constants.py
VEL_HERMES_PLUS_ENABLED  = False  # BLOCKED 2026-05-06 — 31% WR, -0.127% avg, wrong direction
VEL_HERMES_MINUS_ENABLED = True   # vel-hermes- — SHORT only when z-score below mean
VEL_ABS_THRESHOLD        = 0.04   # abs(velocity) must exceed this to fire (raised from 0.03, was 0.06 too tight)

# ── Imports ───────────────────────────────────────────────────────────────────
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

try:
    from hermes_constants import SHORT_BLACKLIST
except Exception:
    SHORT_BLACKLIST = set()

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


# ── Helpers ───────────────────────────────────────────────────────────────────
def _get_open_pos_dict():
    """Return {token: direction} for all open positions."""
    return {p['token']: p['direction'] for p in _get_open_pos()}


# ── Main ─────────────────────────────────────────────────────────────────────
def run() -> int:
    """
    Scan all tokens and emit vel-hermes signals for strong z-score momentum.

    Returns:
        Number of signals successfully written to DB.
    """
    # NOTE: VEL_HERMES_ENABLED guard is in signal_gen.py (inline version).
    # Per-direction VEL_HERMES_PLUS/MINUS_ENABLED checks below remain active.
    # This registry version is called by signals_runner.py — Layer 2 add_signal()
    # guard handles final per-source filtering.

    init_db()

    # ── Live-trading guard ─────────────────────────────────────────────────────
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
        # ── Skip conditions (mirrors signal_gen.py run() loop) ─────────────────
        if token.startswith('@'):
            continue
        if price_age_minutes(token) > 10:
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if get_cooldown(token):
            continue
        if token.upper() in SHORT_BLACKLIST:
            continue

        price = data['price']

        # Skip if already in an open position in this direction
        if token.upper() in open_pos:
            continue

        # ── Per-token rate limiting ───────────────────────────────────────────
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue

        # ── Momentum stats ─────────────────────────────────────────────────────
        mom = _sg.get_momentum_stats(token)
        if not mom:
            continue

        velocity = mom.get('velocity', 0)
        avg_z    = mom.get('avg_z', 0)
        z_dir    = mom.get('z_direction', 'neutral')

        # ── Velocity signal ────────────────────────────────────────────────────
        # abs(velocity) >= 0.03 and vel_conf >= 50 → fire
        # velocity > 0 → SHORT (vel-hermes-)
        # velocity < 0 → LONG  (vel-hermes+)
        vel_abs = abs(velocity)
        vel_conf = min(65, 35 + vel_abs * 500)

        if vel_abs >= VEL_ABS_THRESHOLD and vel_conf >= 50:
            if velocity > 0:
                # Rising z-score → price above mean → bearish → SHORT
                if not VEL_HERMES_MINUS_ENABLED:
                    continue
                # avg_z < 0: only SHORT if market is below mean (catching rebound, not fading bull)
                if not (avg_z < 0):
                    continue
                vel_signal_dir = 'SHORT'
                vel_dir_char = '-'
            else:
                # Falling z-score → price below mean → bullish → LONG
                if not VEL_HERMES_PLUS_ENABLED:
                    continue
                # avg_z > 0: only LONG if market is above mean (catching dump, not fighting trend)
                if not (avg_z > 0):
                    continue
                vel_signal_dir = 'LONG'
                vel_dir_char = '+'

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
