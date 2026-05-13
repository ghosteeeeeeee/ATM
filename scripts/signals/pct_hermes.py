#!/usr/bin/env python3
"""
pct_hermes.py — Standalone percentile-rank Hermes signal generator.

Fires when price is at a historical extreme (pct_long or pct_short >= PCT_RANK_THRESH).
  pct_long  >= 72 → LONG  (price suppressed/at bottom → expect bounce up)
  pct_short >= 72 → SHORT (price elevated/at top   → expect drop down)

Extracted from signal_gen.py lines ~1674-1708 (pct-hermes block).
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Configuration ───────────────────────────────────────────────────────────────
PCT_HERMES_ENABLED    = True   # master kill-switch for this signal type
PCT_HERMES_PLUS_ENABLED  = True   # fire pct-hermes+ (LONG) signals
PCT_HERMES_MINUS_ENABLED = True   # fire pct-hermes- (SHORT) signals
PCT_RANK_THRESH        = 95    # raised from 88 on 2026-05-07 — pct-hermes fires on top/bottom 5% only
                                 # pct=88 fires too early (conf=70) — price hasn't accelerated yet, catches knives
                                 # pct=95+ fires when momentum is already accelerating — price has room to continue
                                 # Historical data: winners fired at p90=~99, p50=96.5. Only pct=95+ has momentum.

# ── Imports ────────────────────────────────────────────────────────────────────
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


# ── Helpers ────────────────────────────────────────────────────────────────────
def _get_open_pos_dict():
    """Return {token: direction} for all open positions."""
    return {p['token']: p['direction'] for p in _get_open_pos()}


# ── Main ───────────────────────────────────────────────────────────────────────
def run() -> int:
    """
    Scan all tokens and emit pct-hermes signals for price extremes.

    Returns:
        Number of signals successfully written to DB.

    NOTE: PCT_HERMES_ENABLED guard is in signal_gen.py (inline version).
    This registry version is called by signals_runner.py and fires regardless
    of the *_ENABLED flag — Layer 2 add_signal() guard handles filtering.
    """
    # Layer 1 guard removed — Layer 2 (add_signal) handles per-source kill-switch

    init_db()

    # ── Live-trading guard ─────────────────────────────────────────────────────
    try:
        if not is_live_trading_enabled():
            print('[pct_hermes] SKIPPED — live_trading=OFF')
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
        if not _sg.is_reasonable_price(token, price):
            continue

        # Skip if already in an open position in this direction
        if token.upper() in open_pos:
            continue

        # ── Momentum / percentile stats ────────────────────────────────────────
        mom = _sg.get_momentum_stats(token)
        if not mom:
            continue

        pct_long  = mom.get('percentile_long', 50)
        pct_short = mom.get('percentile_short', 50)
        avg_z     = mom.get('avg_z', 0)
        z_dir     = mom.get('z_direction', 'neutral')

        # ── Direction selection ────────────────────────────────────────────────
        pct_signal_dir = None
        if pct_long >= PCT_RANK_THRESH:
            if not PCT_HERMES_PLUS_ENABLED:
                continue
            pct_signal_dir = 'LONG'
            pct_val = pct_long
        elif pct_short >= PCT_RANK_THRESH:
            if not PCT_HERMES_MINUS_ENABLED:
                continue
            pct_signal_dir = 'SHORT'
            pct_val = pct_short
        else:
            continue

        # ── Confidence (FIX 2026-05-07) ────────────────────────────────────────────
        # Old formula (PCT_RANK_THRESH=72): (pct_val - 72) * 1.25 + 50, capped at 60.
        # At PCT_RANK_THRESH=95: pct_val is always 95-100. Old formula gives 60 (capped).
        # pct=95 → conf=70, pct=100 → conf=95. Range: 70-95.
        pct_conf = min(95, max(70, 70 + (pct_val - PCT_RANK_THRESH) * 5))

        pct_dir_char = '+' if pct_signal_dir == 'LONG' else '-'

        sid = add_signal(
            token       = token,
            direction   = pct_signal_dir,
            signal_type = 'percentile_rank',
            source      = f'pct-hermes{pct_dir_char}',
            confidence  = round(pct_conf, 1),
            value       = pct_val,
            price       = price,
            exchange    = 'hyperliquid',
            timeframe   = '4h',
            z_score     = avg_z,
            z_score_tier = z_dir,
        )
        if sid:
            added += 1

    return added


if __name__ == '__main__':
    print(f'[pct_hermes] start — PCT_RANK_THRESH={PCT_RANK_THRESH}')
    count = run()
    print(f'[pct_hermes] done — {count} signals written')
