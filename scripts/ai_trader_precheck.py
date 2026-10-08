#!/usr/bin/env python3
"""
ai_trader_precheck.py — Pre-check a coin before the AI trader picks it.
Tests the actual RR engine calculation so the watchdog knows if a pick will pass.

Usage:
    python3 ai_trader_precheck.py COIN DIRECTION
    python3 ai_trader_precheck.py W SHORT
    python3 ai_trader_precheck.py AVAX LONG
"""
import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import *


def precheck(coin, direction):
    """Check if a coin+direction would pass the RR engine and other gates."""
    results = {
        'coin': coin,
        'direction': direction,
        'checks': [],
        'pass': True
    }

    def check(name, passed, detail):
        results['checks'].append({'name': name, 'passed': passed, 'detail': detail})
        if not passed:
            results['pass'] = False

    # 1. ATR check
    try:
        import sqlite3
        conn = sqlite3.connect(os.path.join(HERMES_DATA, 'candles.db'), timeout=5)
        cur = conn.cursor()
        cur.execute('''
            SELECT AVG((high - low) / close * 100) as atr_pct
            FROM candles_5m 
            WHERE token = ? AND ts > strftime('%s', 'now') - 3600
        ''', (coin.upper(),))
        row = cur.fetchone()
        conn.close()
        atr_pct = row[0] if row and row[0] else 0
    except Exception:
        atr_pct = 0

    check('ATR > 0.3%', atr_pct > 0.3, f'ATR={atr_pct:.2f}%')

    # 2. RR engine test — call it directly
    try:
        # Get current price
        import sqlite3
        conn = sqlite3.connect(os.path.join(HERMES_DATA, 'candles.db'), timeout=5)
        cur = conn.cursor()
        cur.execute('SELECT close FROM candles_5m WHERE token = ? ORDER BY ts DESC LIMIT 1', (coin.upper(),))
        price_row = cur.fetchone()
        conn.close()
        current_price = price_row[0] if price_row else None

        if current_price:
            from risk_reward_engine import rr_confidence_multiplier
            rr_result = rr_confidence_multiplier(coin.upper(), direction, current_price, signal_type='ai-trader')
            if rr_result is not None:
                # rr_confidence_multiplier returns (mult, reason) tuple
                if isinstance(rr_result, tuple):
                    rr_mult = float(rr_result[0])
                    rr_reason = rr_result[1] if len(rr_result) > 1 else ''
                else:
                    rr_mult = float(rr_result)
                    rr_reason = ''
                blocked = rr_mult == 0
                detail = f'multiplier={rr_mult:.2f}'
                if rr_reason:
                    detail += f' ({rr_reason[:60]})'
                check('RR engine', not blocked, detail + (' — BLOCKED' if blocked else ''))
            else:
                check('RR engine', False, 'returned None')
        else:
            check('RR engine', False, 'no price data')
    except ImportError:
        # Fallback: estimate R:R from ATR
        import hermes_constants as hc
        atr_min = getattr(hc, 'ATR_SL_MIN', 0.013)
        tp_min = getattr(hc, 'RR_ENGINE_TP_MIN_PCT', 0.005)
        est_rr = tp_min / atr_min if atr_min > 0 else 0
        check('RR estimate', est_rr >= 0.70, f'estimated R:R={est_rr:.2f} (RR engine not importable)')
    except Exception as e:
        check('RR engine', False, f'error: {e}')

    # 3. RSI check
    try:
        import sqlite3
        conn = sqlite3.connect(os.path.join(HERMES_DATA, 'candles.db'), timeout=5)
        cur = conn.cursor()
        cur.execute('''
            SELECT close FROM candles_5m 
            WHERE token = ? ORDER BY ts DESC LIMIT 15
        ''', (coin.upper(),))
        closes = [r[0] for r in cur.fetchall()][::-1]  # ASC: oldest->newest (query returns DESC)
        conn.close()
        if len(closes) >= 14:
            # Simple RSI calculation
            gains, losses = [], []
            for i in range(1, len(closes)):
                diff = closes[i] - closes[i-1]
                gains.append(max(0, diff))
                losses.append(max(0, -diff))
            avg_gain = sum(gains[-14:]) / 14
            avg_loss = sum(losses[-14:]) / 14
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50
    except Exception:
        rsi = 50

    if direction == 'LONG':
        check('RSI 40-65', 40 <= rsi <= 65, f'RSI={rsi:.1f}')
    else:
        check('RSI 40-60', 40 <= rsi <= 60, f'RSI={rsi:.1f}')

    # 4. BTC trend check for LONG
    if direction == 'LONG':
        try:
            with open(os.path.join(WWW_DATA, 'continuum_data.json')) as f:
                cont = json.load(f)
            ema_pos = cont.get('current', {}).get('ema300_position', 'UNKNOWN')
            check('BTC not bearish for LONG', ema_pos != 'BELOW', f'BTC ema300={ema_pos}')
        except Exception:
            pass

    # 5. Price data check
    try:
        import sqlite3
        conn = sqlite3.connect(os.path.join(HERMES_DATA, 'candles.db'), timeout=5)
        cur = conn.cursor()
        cur.execute('''
            SELECT close, ts FROM candles_5m 
            WHERE token = ? ORDER BY ts DESC LIMIT 1
        ''', (coin.upper(),))
        row = cur.fetchone()
        conn.close()
        if row:
            age_min = (time.time() - row[1]) / 60 if row[1] else 999
            check('Price fresh (<5min)', age_min < 5, f'age={age_min:.0f}min')
        else:
            check('Price data', False, 'no candle data')
    except Exception as e:
        check('Price data', False, str(e))

    return results


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 ai_trader_precheck.py COIN DIRECTION")
        print("Example: python3 ai_trader_precheck.py W SHORT")
        sys.exit(1)

    coin = sys.argv[1]
    direction = sys.argv[2].upper()

    import time
    result = precheck(coin, direction)

    print(f"\n=== AI Trader Pre-check: {coin} {direction} ===")
    for c in result['checks']:
        icon = '✅' if c['passed'] else '❌'
        print(f"  {icon} {c['name']}: {c['detail']}")
    print(f"\n{'✅ PASS — safe to pick' if result['pass'] else '❌ FAIL — will likely be blocked'}")
