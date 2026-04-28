#!/usr/bin/env python3
"""
run_ma_fast_signals.py — Standalone 8/50 EMA Cross Signal Runner (SHORT only).

Run this script to scan all tokens for MA fast cross SHORT signals and write them
to the signals_hermes_runtime.db via signal_schema.add_signal().

Can be run manually:  python3 scripts/run_ma_fast_signals.py
Or via systemd timer for autonomous operation.

Based on backtest findings (2026-04-20):
  - 163 tokens, 3+ months of 1m data
  - SHORT only: 27% WR, net +4214%
  - LONG catastrophic: -1800% to -4000% across all pairs
  - Best pair: 8/50
"""

import sys, os, sqlite3, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ma_fast_signals import (
    scan_ma_fast_signals,
    MA_LOOKBACK_CANDLES,
    MA_COOLDOWN_MINUTES,
    MA_SIGNAL_TYPE,
)

# ── DB paths ─────────────────────────────────────────────────────────────────

_CANDLES_DB  = '/root/.hermes/data/candles.db'
_RUNTIME_DB  = '/root/.hermes/data/signals_hermes_runtime.db'

# ── Price source ──────────────────────────────────────────────────────────────

def get_latest_prices_from_candles() -> dict:
    """Get the most recent price per token from candles.db."""
    prices = {}
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT token, close
            FROM candles_1m
            WHERE (token, ts) IN (
                SELECT token, MAX(ts)
                FROM candles_1m
                GROUP BY token
            )
        """)
        for row in c.fetchall():
            prices[row[0].upper()] = {'price': row[1]}
        conn.close()
    except Exception as e:
        print(f"[ma_fast] candles.db price fetch error: {e}")
    return prices


def get_open_positions() -> dict:
    """Return token -> direction dict for currently open HL positions."""
    positions = {}
    try:
        conn = sqlite3.connect(_RUNTIME_DB, timeout=10)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT token, direction
            FROM positions
            WHERE status = 'open'
        """)
        for row in c.fetchall():
            positions[row['token'].upper()] = row['direction']
        conn.close()
    except Exception:
        # No positions table — likely a fresh DB, treat as no open positions
        pass
    return positions


# ── Blacklists ───────────────────────────────────────────────────────────────

_KNOWN_SHORT_BLACKLIST = {
    'TRUMP', 'MELANIA', 'BOME', 'MOG', 'CHAMP', 'ZERERO', 'SNIONI',
    'SLERF', 'PONKE', 'BONK', 'FUDCO', 'SMERF',
    'SCUM', 'LAYER', 'CHMP', 'NUB', 'SAGA', 'DOGINT', 'RANKER',
    'OPEN_WORLD', 'CATSEI', 'PINU', 'GOU', 'SUSHI', 'KAMA', 'ALCH',
    'PAJAMA', 'MEDUSA',
}


def is_blacklisted(token: str) -> bool:
    return token.upper() in _KNOWN_SHORT_BLACKLIST


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"[ma_fast] Starting 8/50 MA cross scan at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Get live prices
    prices = get_latest_prices_from_candles()
    print(f"[ma_fast] Found {len(prices)} tokens with price data")

    # 2. Get open positions (skip if already open)
    open_pos = get_open_positions()
    if open_pos:
        print(f"[ma_fast] {len(open_pos)} open positions: {open_pos}")

    # 3. Filter blacklisted tokens
    filtered = {
        token: data for token, data in prices.items()
        if not is_blacklisted(token)
    }
    skipped = len(prices) - len(filtered)
    if skipped:
        print(f"[ma_fast] Skipped {skipped} blacklisted tokens")

    # 4. Remove open positions
    for token in list(filtered.keys()):
        if token in open_pos:
            del filtered[token]

    # 5. Remove cooldown tokens
    from signal_schema import is_cooldown_active
    removed_cooldown = 0
    for token in list(filtered.keys()):
        if is_cooldown_active(token, 'SHORT') or is_cooldown_active(token, 'LONG'):
            del filtered[token]
            removed_cooldown += 1
    if removed_cooldown:
        print(f"[ma_fast] Skipped {removed_cooldown} cooldown tokens")

    print(f"[ma_fast] Scanning {len(filtered)} tokens for 8/50 MA cross SHORT signals...")

    # 6. Run scanner
    from signal_schema import init_db, record_cooldown_start
    init_db()

    n = scan_ma_fast_signals(filtered)

    # 7. Write cooldowns ONLY for tokens that actually fired (coin + direction)
    if n:
        cooldown_count = 0
        for sig in n:  # n is now a list of {'token': str, 'direction': str}
            record_cooldown_start(sig['token'], sig['direction'], MA_COOLDOWN_MINUTES)
            cooldown_count += 1
        print(f"[ma_fast] Cooldowns written: {cooldown_count} signals × {MA_COOLDOWN_MINUTES}min")

    print(f"[ma_fast] Done. {len(n)} signals emitted.")


if __name__ == '__main__':
    main()
