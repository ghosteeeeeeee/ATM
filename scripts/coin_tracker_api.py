#!/usr/bin/env python3
"""
coin_tracker_api.py — Export coin_tracker.db data as JSON for dashboard.

Writes to /var/www/html/:
  - coin_tracker_data.json      — all coins with scores, registry info
  - coin_tracker_coins/{SYM}.json — per-coin candle history + events

Run after coin_tracker.py collects data.
"""
import sys, os, json, time, sqlite3
sys.path.insert(0, os.path.dirname(__file__))

from paths import HERMES_DATA
from coin_tracker_schema import COIN_TRACKER_DB, _table_name

WWW_HTML = '/var/www/html'
WWW_COINS = os.path.join(WWW_HTML, 'coin_tracker_coins')

def _conn():
    conn = sqlite3.connect(COIN_TRACKER_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def export_all():
    """Export all coins with scores to JSON."""
    os.makedirs(WWW_HTML, exist_ok=True)
    os.makedirs(WWW_COINS, exist_ok=True)

    conn = _conn()
    try:
        # ── Registry + scores joined ──
        rows = conn.execute("""
            SELECT r.symbol, r.name, r.health, r.health_score, r.status,
                   r.signal_count_24h, r.win_rate, r.total_trades,
                   r.avg_spread_bps, r.max_leverage, r.decimals,
                   s.momentum, s.volume, s.volatility, s.spread, s.signals, s.regime, s.composite, s.ts,
                   s.wyckoff_phase, s.ewave_count, s.ewave_degree, s.ewave_direction,
                   s.trend_quality, s.trend_direction, s.sr_levels, s.vol_profile,
                   s.setup_score, s.setup_type, s.setup_details,
                   s.clustering_bullish, s.clustering_bearish, s.recency
            FROM _coin_registry r
            LEFT JOIN agg_scores s ON r.symbol = s.symbol
            WHERE r.status = 'active'
            ORDER BY s.composite DESC
        """).fetchall()

        coins = []
        for row in rows:
            d = dict(row)
            # Get latest event for price
            table = _table_name(d['symbol'])
            try:
                latest = conn.execute(
                    f"SELECT price, vol_1h, vol_24h, spread_bps, rsi_14, macd_hist, "
                    f"ema_9, ema_20, ema_50, atr_14, signal_type, signal_confidence, regime, "
                    f"wyckoff_phase, ewave_count, ewave_degree, ewave_direction, "
                    f"trend_quality, trend_direction, sr_levels, vol_profile, "
                    f"setup_score, setup_type, setup_details, clustering_bullish, clustering_bearish, recency "
                    f"FROM {table} ORDER BY ts DESC LIMIT 1"
                ).fetchone()
                if latest:
                    d.update(dict(latest))
            except Exception:
                pass

            coins.append(d)

        # ── Summary stats ──
        total = len(coins)
        by_health = {}
        for c in coins:
            h = c.get('health', 'unknown')
            by_health[h] = by_health.get(h, 0) + 1

        avg_score = sum(c.get('composite', 0) or 0 for c in coins) / max(1, total)

        output = {
            'generated': int(time.time()),
            'generated_iso': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'total': total,
            'by_health': by_health,
            'avg_score': round(avg_score, 1),
            'coins': coins,
        }

        # Write atomically
        tmp = os.path.join(WWW_HTML, 'coin_tracker_data.json.tmp')
        with open(tmp, 'w') as f:
            json.dump(output, f)
        os.replace(tmp, os.path.join(WWW_HTML, 'coin_tracker_data.json'))

        print(f'[coin_tracker_api] Exported {total} coins to coin_tracker_data.json')

        # ── Per-coin history (all coins for sparklines) ──
        exported = 0
        for coin in coins:
            sym = coin['symbol']
            table = _table_name(sym)
            try:
                events = conn.execute(
                    f"SELECT ts, price, vol_1h, health, health_score, signal_type, signal_confidence, "
                    f"wyckoff_phase, ewave_count, ewave_degree, trend_quality, trend_direction "
                    f"FROM {table} WHERE price IS NOT NULL ORDER BY ts DESC LIMIT 1440"
                ).fetchall()
                if events:
                    coin_out = {
                        'symbol': sym,
                        'name': coin.get('name', sym),
                        'health': coin.get('health'),
                        'composite': coin.get('composite'),
                        'wyckoff_phase': coin.get('wyckoff_phase'),
                        'ewave_count': coin.get('ewave_count'),
                        'ewave_degree': coin.get('ewave_degree'),
                        'ewave_direction': coin.get('ewave_direction'),
                        'trend_quality': coin.get('trend_quality'),
                        'trend_direction': coin.get('trend_direction'),
                        'sr_levels': coin.get('sr_levels'),
                        'vol_profile': coin.get('vol_profile'),
                        'events': [dict(e) for e in events],
                    }
                    path = os.path.join(WWW_COINS, f'{sym}.json')
                    tmp = path + '.tmp'
                    with open(tmp, 'w') as f:
                        json.dump(coin_out, f)
                    os.replace(tmp, path)
                    exported += 1
            except Exception:
                pass

        print(f'[coin_tracker_api] Exported {exported} per-coin histories')
    finally:
        conn.close()

if __name__ == '__main__':
    export_all()
