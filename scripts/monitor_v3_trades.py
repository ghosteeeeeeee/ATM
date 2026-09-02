#!/usr/bin/env python3
"""Monitor open v3 trades — live tuning session."""
import sys, os, sqlite3, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import STATIC_DB, RUNTIME_DB
from signal_schema import get_all_latest_prices

LOG_FILE = '/root/.hermes/logs/v3_trade_monitor.log'

# All open trades to track
TRADES = [
    {'token': 'CASHCAT', 'entry': 0.2197, 'sl': 0.217932, 'tp': 0.2239, 'source': 'accel-300-v3-long+', 'opened': '23:40', 'size': 11.1, 'leverage': 3},
    {'token': 'ACE',     'entry': 0.2127, 'sl': 0.210998, 'tp': 0.2155, 'source': 'accel-300-v3-long+', 'opened': '23:59', 'size': 11.1, 'leverage': 3},
    {'token': 'FIL',     'entry': 0.7782, 'sl': 0.771964, 'tp': 0.7854, 'source': 'accel-300-v3-long+', 'opened': '23:52', 'size': 19.9, 'leverage': 5},
    {'token': 'ZRO',     'entry': 1.0273, 'sl': 1.019082, 'tp': 1.0358, 'source': 'accel-300-v3-long+', 'opened': '23:59', 'size': 11.1, 'leverage': 5},
    {'token': 'SUSHI',   'entry': 0.2005, 'sl': 0.198876, 'tp': 0.2024, 'source': 'accel-300-v3-long+', 'opened': '23:54', 'size': 11.1, 'leverage': 3},
]

INTERVAL = 180  # 3 min
ROUNDS = 10     # 30 min

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f'{ts} {msg}'
    print(line, flush=True)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except: pass

def get_prices():
    """Get current prices for all tracked tokens."""
    prices = get_all_latest_prices()
    result = {}
    for t in TRADES:
        token = t['token']
        if token in prices:
            result[token] = prices[token]['price']
        else:
            # Fallback: read from DB
            try:
                conn = sqlite3.connect(STATIC_DB, timeout=5)
                cur = conn.cursor()
                cur.execute("SELECT price FROM price_history WHERE token=? ORDER BY timestamp DESC LIMIT 1", (token,))
                row = cur.fetchone()
                result[token] = row[0] if row else None
                conn.close()
            except:
                result[token] = None
    return result

def check_new_signals():
    """Check for any new v3 signals since last check."""
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT token, price, confidence, created_at
            FROM signals
            WHERE source = 'accel-300-v3-long+'
            ORDER BY created_at DESC LIMIT 10
        """)
        return cur.fetchall()
    except:
        return []
    finally:
        if conn: conn.close()

log(f'=== V3 Trade Monitor — {len(TRADES)} trades, {ROUNDS} rounds, {INTERVAL}s interval ===')
log(f'Trades: {", ".join(t["token"] for t in TRADES)}')

for round_num in range(1, ROUNDS + 1):
    log(f'\n--- Round {round_num}/{ROUNDS} ({datetime.now().strftime("%H:%M:%S")}) ---')

    prices = get_prices()

    for t in TRADES:
        token = t['token']
        price = prices.get(token)
        if price is None:
            log(f'  {token}: NO PRICE DATA')
            continue

        entry = t['entry']
        sl = t['sl']
        tp = t['tp']
        pnl_pct = (price - entry) / entry * 100
        pnl_usdt = pnl_pct / 100 * t['size'] * t['leverage']

        # Distance to SL and TP
        sl_dist = (price - sl) / price * 100
        tp_dist = (tp - price) / price * 100

        # Status
        if price <= sl:
            status = '🔴 SL HIT'
        elif price >= tp:
            status = '🟢 TP HIT'
        elif pnl_pct > 0:
            status = '✅ GREEN'
        else:
            status = '⚠️ RED'

        # R:R ratio
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = reward / risk if risk > 0 else 0

        # How long held
        log(f'  {token:8s} {status} entry=${entry:.4f} now=${price:.4f} pnl={pnl_pct:+.2f}% ${pnl_usdt:+.2f} | SL {sl_dist:.2f}% away | TP {tp_dist:.2f}% away | R:R {rr:.1f}:1')

    # Check for new signals
    signals = check_recent_signals()
    new_tokens = [s[0] for s in signals if s[0] not in [t['token'] for t in TRADES]]
    if new_tokens:
        log(f'  📡 New v3 signals: {", ".join(new_tokens)}')

    if round_num < ROUNDS:
        log(f'  zzz {INTERVAL}s...')
        time.sleep(INTERVAL)

log(f'\n=== Monitor Complete ===')
