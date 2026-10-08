#!/usr/bin/env python3
"""
ai_trader_precheck.py — Pre-check a coin before the AI trader picks it.
Tests the actual RR engine calculation so the watchdog knows if a pick will pass.

Usage:
    python3 ai_trader_precheck.py COIN DIRECTION
    python3 ai_trader_precheck.py W SHORT
    python3 ai_trader_precheck.py AVAX LONG
"""
import sys, os, json, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import *


def _get_candles_db():
    """Open candles.db connection. Caller must close in finally."""
    import sqlite3
    return sqlite3.connect(os.path.join(HERMES_DATA, 'candles.db'), timeout=5)


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

    token = coin.upper()

    # 1. ATR check — use volatility_gate.get_atr_pct() (same source as RR engine)
    try:
        from volatility_gate import get_atr_pct
        atr_pct = get_atr_pct(token) or 0
        # Import thresholds from constants
        import hermes_constants as hc
        atr_floor = getattr(hc, 'ATR_FLOOR_CHECK_PCT', 0.3)
        check(f'ATR > {atr_floor}%', atr_pct > atr_floor, f'ATR={atr_pct:.2f}%')
    except ImportError:
        # Fallback: 5m avg range (less accurate)
        conn = None
        try:
            conn = _get_candles_db()
            cur = conn.cursor()
            cur.execute('''
                SELECT AVG((high - low) / close * 100) as atr_pct
                FROM candles_5m 
                WHERE token = ? AND ts > strftime('%s', 'now') - 3600
            ''', (token,))
            row = cur.fetchone()
            atr_pct = row[0] if row and row[0] else 0
            check('ATR > 0.3% (fallback)', atr_pct > 0.3, f'ATR={atr_pct:.2f}% (5m avg)')
        except Exception as e:
            check('ATR', False, f'error: {e}')
        finally:
            if conn:
                conn.close()
    except Exception as e:
        check('ATR', False, f'error: {e}')

    # 2. RR engine test — call it directly
    try:
        # Get current price from CLOSED candles (match compactor behavior)
        conn = None
        try:
            conn = _get_candles_db()
            cur = conn.cursor()
            cur.execute('''
                SELECT close FROM candles_5m 
                WHERE token = ? AND is_closed = 1
                ORDER BY ts DESC LIMIT 1
            ''', (token,))
            price_row = cur.fetchone()
            current_price = price_row[0] if price_row else None
        finally:
            if conn:
                conn.close()

        if current_price:
            from risk_reward_engine import rr_confidence_multiplier
            rr_result = rr_confidence_multiplier(token, direction, current_price, signal_type='ai-trader')
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
        check('RR engine', False, 'RR engine not importable — cannot verify')
    except Exception as e:
        check('RR engine', False, f'error: {e}')

    # 3. RSI check — import bands from constants
    try:
        import hermes_constants as hc
        rsi_long_min = getattr(hc, 'LONG_RSI_FLOOR', 20)
        rsi_long_max = getattr(hc, 'SIGNAL_FILTER_RSI_MAX', 72)
        rsi_short_min = getattr(hc, 'SHORT_RSI_HARD_FLOOR', 45)
        rsi_short_max = getattr(hc, 'SHORT_RSI_CEILING', 65)

        conn = None
        try:
            conn = _get_candles_db()
            cur = conn.cursor()
            # Use CLOSED candles only (match rsi_utils behavior)
            cur.execute('''
                SELECT close FROM candles_5m 
                WHERE token = ? AND is_closed = 1
                ORDER BY ts DESC LIMIT 16
            ''', (token,))
            closes = [r[0] for r in cur.fetchall()][::-1]  # ASC: oldest->newest
        finally:
            if conn:
                conn.close()

        if len(closes) >= 15:
            # Simple RSI calculation on closed candles
            gains, losses = [], []
            for i in range(1, len(closes)):
                diff = closes[i] - closes[i-1]
                gains.append(max(0, diff))
                losses.append(max(0, -diff))
            # Use last 14 diffs (need 15 closes for 14 diffs)
            avg_gain = sum(gains[-14:]) / 14
            avg_loss = sum(losses[-14:]) / 14
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            rsi = 100 - (100 / (1 + rs))
            rsi_valid = True
        else:
            rsi = None
            rsi_valid = False
    except Exception as e:
        rsi = None
        rsi_valid = False
        check('RSI', False, f'error: {e}')

    if rsi_valid and rsi is not None:
        if direction == 'LONG':
            passed = rsi_long_min <= rsi <= rsi_long_max
            check(f'RSI {rsi_long_min}-{rsi_long_max}', passed, f'RSI={rsi:.1f}')
        else:
            passed = rsi_short_min <= rsi <= rsi_short_max
            check(f'RSI {rsi_short_min}-{rsi_short_max}', passed, f'RSI={rsi:.1f}')
    elif rsi is None and 'RSI' not in [c['name'] for c in results['checks']]:
        check('RSI', False, 'insufficient closed candle data')

    # 3b. HALL-SHAME check — 30d direction winrate must be >= 55%
    try:
        lb_file = os.path.join(HERMES_DATA, 'favorites_leaderboard.json')
        with open(lb_file) as f:
            lb_data = json.load(f)
        # Find coin in leaderboard
        coin_lb = None
        for t in lb_data.get('leaderboard', []):
            if t.get('token', '').upper() == token:
                coin_lb = t
                break
        if coin_lb and coin_lb.get('trades', 0) >= 15:
            dir_stats = coin_lb.get('direction_stats', {})
            if direction in dir_stats:
                dir_wr = dir_stats[direction].get('winrate', 50)
            else:
                dir_wr = coin_lb.get('wr', 50)
            check(f'30d WR >= 55%', dir_wr >= 55, f'30d {direction} WR={dir_wr:.1f}% ({coin_lb.get("trades",0)} trades)')
        else:
            check('30d WR', True, f'insufficient trades ({coin_lb.get("trades",0) if coin_lb else 0}) — skip check')
    except FileNotFoundError:
        check('30d WR', True, 'leaderboard not found — skip check')
    except Exception as e:
        check('30d WR', True, f'error: {e} — skip check')

    # 3c. LOSERS/PENALTY check
    try:
        from hermes_constants import LOSERS, LOSERS_LONG, LOSERS_SHORT, PENALTY_TOKENS
        in_losers = token in LOSERS or token in LOSERS_LONG or token in LOSERS_SHORT
        in_penalty = token in PENALTY_TOKENS
        if in_losers or in_penalty:
            reasons = []
            if token in LOSERS: reasons.append('LOSERS')
            if token in LOSERS_LONG and direction == 'LONG': reasons.append('LOSERS_LONG')
            if token in LOSERS_SHORT and direction == 'SHORT': reasons.append('LOSERS_SHORT')
            if in_penalty: reasons.append('PENALTY')
            check('Not in losers/penalty', False, f'blocked by {", ".join(reasons)}')
        else:
            check('Not in losers/penalty', True, 'clean')
    except ImportError:
        check('Not in losers/penalty', True, 'constants not importable')
    except Exception as e:
        check('Not in losers/penalty', True, f'error: {e}')

    # 4. BTC trend check for LONG
    if direction == 'LONG':
        try:
            with open(os.path.join(WWW_DATA, 'continuum_data.json')) as f:
                cont = json.load(f)
            ema_pos = cont.get('current', {}).get('ema300_position', 'UNKNOWN')
            check('BTC not bearish for LONG', ema_pos != 'BELOW', f'BTC ema300={ema_pos}')
        except Exception as e:
            check('BTC trend', False, f'cannot read continuum: {e}')

    # 5. Price data check — use ANY candle (including developing) for freshness
    # The collector updates the developing candle every 30s; closed candles lag by one period
    try:
        conn = None
        try:
            conn = _get_candles_db()
            cur = conn.cursor()
            cur.execute('''
                SELECT close, ts, is_closed FROM candles_5m 
                WHERE token = ?
                ORDER BY ts DESC LIMIT 1
            ''', (token,))
            row = cur.fetchone()
        finally:
            if conn:
                conn.close()

        if row:
            age_min = (time.time() - row[1]) / 60 if row[1] else 999
            candle_type = 'closed' if row[2] else 'developing'
            # 10min threshold: developing candle updated every 30s, closed lags by 5min
            check('Price fresh (<10min)', age_min < 10, f'age={age_min:.0f}min ({candle_type})')
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

    result = precheck(coin, direction)

    print(f"\n=== AI Trader Pre-check: {coin} {direction} ===")
    for c in result['checks']:
        icon = '✅' if c['passed'] else '❌'
        print(f"  {icon} {c['name']}: {c['detail']}")
    print(f"\n{'✅ PASS — safe to pick' if result['pass'] else '❌ FAIL — will likely be blocked'}")
