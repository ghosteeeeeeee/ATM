#!/usr/bin/env python3
"""
run_rs_signals.py — Standalone Support & Resistance Signal Runner.

Run this script to scan all tokens for R&S signals and write them to the
signals_hermes_runtime.db via signal_schema.add_signal().

Can be run manually:  python3 scripts/run_rs_signals.py
Or via systemd timer for autonomous operation.

Architecture:
  - Fetches latest prices from candles.db (most recent 1m candle per token)
  - Fetches full candle history from candles.db for level detection
  - Applies trade guards (blacklists, open positions, cooldowns)
  - Writes signals via signal_schema.add_signal()
"""

import sys, os, sqlite3, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rs_signals import (
    scan_rs_signals,
    RS_LOOKBACK_CANDLES,
    RS_COOLDOWN_HOURS,
    RS_SIGNAL_TYPE,
)

# ── DB paths ─────────────────────────────────────────────────────────────────

_CANDLES_DB  = '/root/.hermes/data/candles.db'
_RUNTIME_DB  = '/root/.hermes/data/signals_hermes_runtime.db'

# ── Price source ──────────────────────────────────────────────────────────────

def get_latest_prices_from_candles() -> dict:
    """Get the most recent price per token from candles.db.

    candles.db has ~4700 candles/token going back ~3+ days.
    The most recent candle for each token gives us the live price.
    """
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
        print(f"[run_rs] candles.db price fetch error: {e}")
    return prices


def get_open_positions() -> dict:
    """Return token -> direction dict for currently open HL positions.
    
    Uses position_manager.get_open_positions() which queries the brain DB (PostgreSQL).
    Falls back to an empty dict if the DB is unavailable.
    """
    try:
        from position_manager import get_open_positions as _pm_get_open
        positions = _pm_get_open()
        return {p.get('token', '').upper(): p.get('direction', '').upper()
                for p in positions if p.get('token')}
    except Exception as e:
        print(f"[run_rs] get_open_positions error: {e}")
        return {}


# ── Blacklists ────────────────────────────────────────────────────────────────

# Tokens we never trade (no real volume, meme coins, etc.)
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
    print(f"[run_rs] Starting R&S signal scan at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Get live prices
    prices = get_latest_prices_from_candles()
    print(f"[run_rs] Found {len(prices)} tokens with price data")

    # 2. Get open positions (skip if already open)
    open_pos = get_open_positions()
    if open_pos:
        print(f"[run_rs] {len(open_pos)} open positions: {open_pos}")

    # 3. Filter blacklisted tokens
    filtered = {
        token: data for token, data in prices.items()
        if not is_blacklisted(token)
    }
    skipped = len(prices) - len(filtered)
    if skipped:
        print(f"[run_rs] Skipped {skipped} blacklisted tokens")

    # 4. Remove open positions
    for token in list(filtered.keys()):
        if token in open_pos:
            del filtered[token]

    # 5. Remove cooldown tokens (uses signal_schema which handles ms internally)
    from signal_schema import is_cooldown_active
    removed_cooldown = 0
    for token in list(filtered.keys()):
        if is_cooldown_active(token, 'LONG') or is_cooldown_active(token, 'SHORT'):
            del filtered[token]
            removed_cooldown += 1
    if removed_cooldown:
        print(f"[run_rs] Skipped {removed_cooldown} cooldown tokens")

    print(f"[run_rs] Scanning {len(filtered)} tokens for R&S signals...")

    # 6. Run R&S scanner
    from signal_schema import init_db, record_cooldown_start
    init_db()

    n, signaled_tokens = scan_rs_signals(filtered)

    # 7. Write cooldowns via signal_schema (per-direction, same direction only)
    # Only for tokens+directions that actually fired — not both directions
    if signaled_tokens:
        from signal_schema import set_cooldown
        for token, direction in signaled_tokens:
            set_cooldown(token, direction, hours=RS_COOLDOWN_HOURS)
        print(f"[run_rs] Cooldowns written: {len(signaled_tokens)} entries (token+direction specific)")

    print(f"[run_rs] Done. {n} signals emitted.")


if __name__ == '__main__':
    main()
