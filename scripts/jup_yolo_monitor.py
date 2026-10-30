#!/usr/bin/env python3
"""
Jupiter YOLO Mirror — follows top leaderboard wallets and fires Hermes signals.

The YOLO wallets are Solana-based (cannot be copied on Hyperliquid directly),
so we MIRROR their direction: when they go LONG/SHORT on a tradeable coin,
we emit a Hermes signal and execute on Hyperliquid.

Data source: https://yolo-api.jup.ag/trades (public, no auth)
Leaderboard: https://jup.ag/yolo/?market=BTC (top uPnL traders)

CEO 2026-10-09: Track the big-dog winners, mirror their conviction.
"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

YOLO_TRADES_URL = "https://yolo-api.jup.ag/trades?limit=100"
YOLO_POSITIONS_URL = "https://jup.ag/yolo/api/watch/positions"
STATE_FILE = os.path.join(HERMES_DATA, 'jup_yolo_state.json')

# Leaderboard wallets (verified prefix/suffix match 2026-10-09)
# Scores = leaderboard uPnL% at capture time — used for signal confidence
JUP_YOLO_WALLETS = {
    # rank: (wallet, label, upnl_pct)
    "9tRBvY5zotGawm9CPitxX1gsmQS9uhNJdiQeiSZG5VA6": ("9tRB", 4264),
    "S1NFULzFDRBf3bXetEq9enLjsZvKGt7qanofpdtNy4e":  ("S1NF", 1830),  # bot, ranks 2-7
    "5mgemxgXkEE9ks3zga4ZELAdhAb6RF7ngAxmBHE5kfzh": ("5mge", 2052),
    "DohjxeYVCxx3MefFrrg6rUdpVxhVEA88P4Cn4wXTTzXc": ("Dohj", 2153),
    "FhVZTEpa1BZEN4eL3EtDFSsDs7Gak2DK61aNpnwMZawd": ("FhVZ", 2092),
    "CJN3qXUuvHcuqdvpB5YJnDgHkwtEVAcTznRTDZrgsQXe": ("CJN3", 1940),
    "84Rvf598ZTkdEC2pBQtNMZcMYQgpNf12hgaENgestFCS": ("84Rv", 163),
    "6QJVgNETqdXNt8X4V31uq7fi7jeLkBKB9FArBrTTzStv": ("6QJV", 537),
    "4mYMEZhimKe1mCbnr34fSRXzzGo8fwVXXWL7B1peqU8M": ("4mYM", 2250),
    "2WYsmvyThohY9f3DgeT4dLHK2XGJrRZHikwTgjFymJmE": ("2WYs", 1807),
    "usa4YpHpKh8nUgViRtv3mnQVa5d6RZWdkZoGmRzXG3A":  ("usa4", 1257),
    "FSG4XbDyJWJKVuvmwMbyypTh4Cqnoc8xR4gTr3ViNuLc": ("FSG4", 2045),
    "AyvQ9wnZLPYEq9CKHmZAUAuNf6qQGsZyfy3MqNKE5Spd": ("AyvQ", 588),
}

# Coins we can trade on Hyperliquid (YOLO market -> HL market)
TRADEABLE_MARKETS = {'BTC', 'SOL', 'ETH', 'HYPE', 'ZEC'}


def _fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"last_cursor": 0, "seen_ids": []}


def save_state(state: dict):
    # Keep only last 500 seen ids
    state['seen_ids'] = state.get('seen_ids', [])[-500:]
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def get_hl_price(coin: str) -> float:
    """Get current price from local DB (candles_1m), fallback to HL API."""
    try:
        import sqlite3
        from paths import CANDLES_DB
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        row = conn.execute(
            "SELECT close FROM candles_1m WHERE token=? ORDER BY ts DESC LIMIT 1",
            (coin.upper(),)
        ).fetchone()
        conn.close()
        if row:
            return float(row[0])
    except Exception:
        pass
    try:
        from hyperliquid_exchange import get_price
        return float(get_price(coin))
    except Exception:
        return 0.0


def emit_signal(coin: str, direction: str, wallet: str, upnl_pct: int,
                leverage: int, margin_usd: float) -> bool:
    """Write a mirrored signal to the Hermes pipeline via add_signal()."""
    from signal_schema import add_signal

    price = get_hl_price(coin)
    if price <= 0:
        print(f"[jup_yolo] SKIP {coin} — no price available")
        return False

    # Confidence from leaderboard rank + leverage conviction
    # Higher upnl% = better track record; higher leverage = more conviction
    base_conf = 70
    upnl_bonus = min(25, upnl_pct / 100)         # up to +25 for 2500%+
    lev_bonus = min(5, leverage / 200)             # up to +5 for 1000x
    confidence = min(95, base_conf + upnl_bonus + lev_bonus)

    signal_type = 'jup_yolo_long' if direction == 'LONG' else 'jup_yolo_short'

    add_signal(
        token=coin,
        direction=direction,
        signal_type=signal_type,
        source='jup_yolo_mirrored',
        confidence=round(confidence, 1),
        price=price,
        exchange='hyperliquid',
        timeframe='5m',
        signal_metadata={
            'jup_wallet': wallet,
            'jup_wallet_short': wallet[:4],
            'jup_upnl_pct': upnl_pct,
            'jup_leverage': leverage,
            'jup_margin_usd': margin_usd,
            'jup_market': coin,
            'jup_side': direction,
            'mirror_source': 'jup_ag_yolo_leaderboard',
        },
    )
    print(f"[jup_yolo] 🪞 MIRRORED {wallet[:4]} {coin} {direction} "
          f"({leverage}x, upnl {upnl_pct}%) conf={confidence:.0f}")
    return True


def monitor_once() -> int:
    """One poll cycle. Uses POSITIONS feed (leaderboard wallets are holders, not churners).

    Detects NEW positions by position id — fires a mirrored Hermes signal.
    Returns number of signals emitted.
    """
    state = load_state()
    seen = set(state.get('seen_ids', []))

    # PRIMARY: positions feed — leaderboard wallets are high-x holders
    try:
        data = _fetch(YOLO_POSITIONS_URL)
    except Exception as e:
        print(f"[jup_yolo] positions fetch error: {e}")
        return 0

    positions = data.get('positions', [])
    new_signals = 0

    for p in positions:
        owner = p.get('owner', '')
        market = p.get('market', '')
        side = p.get('side', '')
        pid = p.get('id', '')

        if owner not in JUP_YOLO_WALLETS:
            continue
        if pid in seen:
            continue
        if market not in TRADEABLE_MARKETS:
            continue

        direction = 'LONG' if side == 'long' else 'SHORT'
        label, upnl_pct = JUP_YOLO_WALLETS[owner]
        leverage = int(p.get('leverage', 0) or 0)
        margin = float(p.get('margin', 0) or 0) / 1_000_000

        if emit_signal(market, direction, owner, upnl_pct, leverage, margin):
            new_signals += 1
        seen.add(pid)

    state['seen_ids'] = list(seen)
    save_state(state)
    return new_signals


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        print("=== Tracked JUP YOLO Leaderboard Wallets ===")
        for w, (label, upnl) in sorted(JUP_YOLO_WALLETS.items(), key=lambda x: -x[1][1]):
            print(f"  {label}… {w}  (+{upnl}%)")
        return

    print(f"[jup_yolo] Monitoring {len(JUP_YOLO_WALLETS)} leaderboard wallets...")
    sigs = monitor_once()
    print(f"[jup_yolo] Emitted {sigs} signals")


if __name__ == '__main__':
    main()
