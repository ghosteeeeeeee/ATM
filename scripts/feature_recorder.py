#!/usr/bin/env python3
"""
feature_recorder.py — Standalone entry/exit feature recording.

Extracted from hl-sync-guardian.py to allow import without triggering
the guardian's module-level lock acquisition. brain.py imports this
instead of hl_sync_guardian.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _secrets import BRAIN_DB_DICT


def _get_db_connection():
    import psycopg2
    try:
        return psycopg2.connect(**BRAIN_DB_DICT)
    except Exception:
        return None


def _compute_intel_from_prices(token: str) -> dict:
    """Compute indicators from price_history and candles_5m."""
    from paths import STATIC_DB, CANDLES_DB

    result = {
        'rsi_14': None, 'macd_hist': None, 'atr_14': None,
        'bb_position': None, 'slope_4h': None, 'regime_4h': None, 'trend': None,
    }

    try:
        with sqlite3.connect(STATIC_DB, timeout=5) as db:
            rows = db.execute(
                'SELECT price FROM price_history WHERE token=? ORDER BY timestamp DESC LIMIT 60',
                (token.upper(),)
            ).fetchall()
        prices = [r[0] for r in reversed(rows)] if rows else []
    except Exception:
        prices = []

    if len(prices) < 26:
        return result

    # RSI
    if len(prices) >= 15:
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [c for c in changes[-14:] if c > 0]
        losses = [-c for c in changes[-14:] if c < 0]
        ag = sum(gains) / 14 if gains else 0
        al = sum(losses) / 14 if losses else 0
        result['rsi_14'] = round(100.0 if al == 0 else 100 - 100 / (1 + ag / al), 2)

    # MACD
    def _ema(vals, period):
        k = 2 / (period + 1)
        e = sum(vals[:period]) / period
        for v in vals[period:]:
            e = v * k + e * (1 - k)
        return e

    if len(prices) >= 35:
        ml = _ema(prices[-35:], 12) - _ema(prices[-35:], 26)
        mvs = []
        for i in range(26, len(prices) + 1):
            chunk = prices[max(0, i - 35):i]
            if len(chunk) >= 26:
                mvs.append(_ema(chunk, 12) - _ema(chunk, 26))
        if len(mvs) >= 9:
            sig = _ema(mvs, 9)
            result['macd_hist'] = round(ml - sig, 8)

    # BB position
    w = prices[-20:]
    mean = sum(w) / len(w)
    var = sum((p - mean) ** 2 for p in w) / len(w)
    std = var ** 0.5
    if std > 0:
        result['bb_position'] = round((prices[-1] - (mean - 2 * std)) / (4 * std), 4)

    # ATR from 5m candles
    try:
        with sqlite3.connect(CANDLES_DB, timeout=5) as db:
            rows = db.execute(
                'SELECT high, low, close FROM candles_5m WHERE token=? AND is_closed=1 ORDER BY ts DESC LIMIT 15',
                (token.upper(),)
            ).fetchall()
        if len(rows) >= 2:
            trs = []
            for i in range(1, len(rows)):
                h, l, c = rows[i-1]
                prev_c = rows[i][2]
                tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
                trs.append(tr)
            result['atr_14'] = round(sum(trs[:14]) / min(len(trs), 14), 8) if trs else None
    except Exception:
        pass

    return result


def get_token_intel(token: str) -> dict:
    """
    Token intel: reads from momentum_cache, falls back to computing from price_history.
    Returns dict with rsi_14, macd_hist, atr_14, bb_position, slope_4h, regime_4h, trend.
    """
    # Try momentum_cache first (may be empty)
    conn = _get_db_connection()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT rsi_14, macd_hist, atr_14, bb_position, slope_4h, regime_4h, trend
                FROM momentum_cache
                WHERE token=%s
                ORDER BY updated_at DESC LIMIT 1
            """, (token,))
            row = cur.fetchone()
            conn.close()

            if row and row[0] is not None:
                return {
                    'rsi_14': float(row[0]) if row[0] else None,
                    'macd_hist': float(row[1]) if row[1] else None,
                    'atr_14': float(row[2]) if row[2] else None,
                    'bb_position': float(row[3]) if row[3] else None,
                    'slope_4h': float(row[4]) if row[4] else None,
                    'regime_4h': row[5] if row[5] else None,
                    'trend': row[6] if row[6] else None,
                }
        except Exception:
            try:
                conn.close()
            except:
                pass

    return _compute_intel_from_prices(token)


def record_entry_features(trade_id: int, token: str):
    """Record technical indicators at trade entry."""
    intel = get_token_intel(token)
    if not intel or not any(intel.values()):
        return False

    conn = _get_db_connection()
    if conn is None:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE trades SET
                entry_rsi_14 = %s,
                entry_macd_hist = %s,
                entry_atr_14 = %s,
                entry_bb_position = %s,
                entry_slope_4h = %s,
                entry_regime_4h = %s,
                entry_trend = %s,
                features_recorded = TRUE,
                predicted_return = %s
            WHERE id = %s
        """, (
            intel.get('rsi_14'),
            intel.get('macd_hist'),
            intel.get('atr_14'),
            intel.get('bb_position'),
            intel.get('slope_4h'),
            intel.get('regime_4h'),
            intel.get('trend'),
            0.0,
            trade_id
        ))
        conn.commit()
        cur.close()
        conn.close()
        print(f'[feature_recorder] ✅ {token} trade #{trade_id} — rsi={intel.get("rsi_14")} bb={intel.get("bb_position")}')
        return True
    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        print(f'[feature_recorder] ❌ {token} trade #{trade_id} error: {e}')
        return False


def record_exit_features(trade_id: int, exit_price: float, exit_reason: str):
    """Record exit details and calculate actual vs predicted return."""
    conn = _get_db_connection()
    if conn is None:
        return

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT entry_price, direction, entry_regime_4h, leverage
            FROM trades WHERE id = %s
        """, (trade_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return

        entry_price, direction, regime, leverage = row
        if entry_price and exit_price:
            mult = 1 if direction == 'LONG' else -1
            actual_return = round((exit_price - entry_price) / entry_price * mult * 100, 4)
            cur.execute("""
                UPDATE trades SET exit_price=%s, exit_reason=%s, actual_return=%s WHERE id=%s
            """, (exit_price, exit_reason, actual_return, trade_id))
            conn.commit()

        cur.close()
        conn.close()
    except Exception:
        try:
            conn.rollback()
            conn.close()
        except:
            pass


if __name__ == '__main__':
    import psycopg2
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    cur = conn.cursor()
    cur.execute("SELECT id, token FROM trades WHERE status='open' ORDER BY open_time DESC LIMIT 5")
    for tid, tok in cur.fetchall():
        record_entry_features(tid, tok)
    conn.close()
