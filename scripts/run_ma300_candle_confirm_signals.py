#!/usr/bin/env python3
"""
run_ma300_candle_confirm_signals.py — Standalone runner for MA300 + 2-conf signal.

Run manually:  python3 scripts/run_ma300_candle_confirm_signals.py
Or via cron/systemd timer.

Integrates with signal_gen.py via:
    from ma300_candle_confirm_signals import scan_ma300_candle_signals
"""

import sys, os, sqlite3, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ma300_candle_confirm_signals import (
    scan_ma300_candle_signals,
    LOOKBACK_CANDLES,
    COOLDOWN_MINUTES,
    SIGNAL_TYPE,
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
        print(f"[ma300c] candles.db price fetch error: {e}")
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
    except Exception as e:
        print(f"[ma300c] positions table error: {e}")
    return positions


# ── Blacklists ────────────────────────────────────────────────────────────────

_KNOWN_SHORT_BLACKLIST = {
    'TRUMP', 'MELANIA', 'BOME', 'MOG', 'CHAMP', 'ZERERO', 'SNIONI',
    'SLERF', 'PONKE', 'BONK', 'FUDCO', 'SMERF',
    'SCUM', 'LAYER', 'CHMP', 'NUB', 'SAGA', 'DOGINT', 'RANKER',
    'OPEN_WORLD', 'CATSEI', 'PINU', 'GOU', 'SUSHI', 'KAMA', 'ALCH',
    'PAJAMA', 'MEDUSA',
}


def is_blacklisted(token: str) -> bool:
    return token.upper() in _KNOWN_SHORT_BLACKLIST


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"[ma300c] Starting MA300+2conf scan at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Get live prices
    prices = get_latest_prices_from_candles()
    print(f"[ma300c] Found {len(prices)} tokens with price data")

    # 2. Get open positions (skip if already open)
    open_pos = get_open_positions()
    if open_pos:
        print(f"[ma300c] {len(open_pos)} open positions: {open_pos}")

    # 3. Filter blacklisted tokens
    filtered = {
        token: data for token, data in prices.items()
        if not is_blacklisted(token)
    }
    skipped = len(prices) - len(filtered)
    if skipped:
        print(f"[ma300c] Skipped {skipped} blacklisted tokens")

    # 4. Remove open positions
    for token in list(filtered.keys()):
        if token in open_pos:
            del filtered[token]

    # 5. Remove cooldown tokens
    from signal_schema import is_cooldown_active
    removed_cooldown = 0
    for token in list(filtered.keys()):
        if is_cooldown_active(token, 'LONG') or is_cooldown_active(token, 'SHORT'):
            del filtered[token]
            removed_cooldown += 1
    if removed_cooldown:
        print(f"[ma300c] Skipped {removed_cooldown} cooldown tokens")

    print(f"[ma300c] Scanning {len(filtered)} tokens for MA300+2conf signals...")

    # 6. Run scanner
    from signal_schema import init_db, record_cooldown_start
    init_db()

    n, fired_tokens = scan_ma300_candle_signals(filtered)

    # 7. Write cooldowns for tokens that actually fired signals (not all scanned)
    # fired_tokens is a list of signal dicts — extract unique token names
    if n > 0:
        from signal_schema import record_cooldown_start
        signaled_tokens = list({sig['token'] for sig in fired_tokens})
        for token in signaled_tokens:
            record_cooldown_start(token.upper(), 'LONG', COOLDOWN_MINUTES)
            record_cooldown_start(token.upper(), 'SHORT', COOLDOWN_MINUTES)
        print(f"[ma300c] Cooldowns written: {len(signaled_tokens)} tokens × {COOLDOWN_MINUTES}min × 2 dirs")

    print(f"[ma300c] Done. {n} signals emitted.")


if __name__ == '__main__':
    main()
