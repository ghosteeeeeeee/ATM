#!/usr/bin/env python3
"""
Backfill trade indicator data for all closed trades.

Reads token + open_time from PostgreSQL, computes indicators from
price_history at that timestamp, updates the trades row.

Usage:
    python3 scripts/backfill_trade_indicators.py                # full backfill
    python3 scripts/backfill_trade_indicators.py --dry          # dry run, no writes
    python3 scripts/backfill_trade_indicators.py --limit 100    # test on 100
    python3 scripts/backfill_trade_indicators.py --token BTC    # single token
"""
import sys, os, time, json, sqlite3, argparse, psycopg2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _secrets import BRAIN_DB_DICT
from paths import STATIC_DB, CANDLES_DB

def get_prices_at(token, ts, n=60):
    """Get n 1m close prices ending at timestamp ts from price_history."""
    try:
        with sqlite3.connect(STATIC_DB, timeout=5) as conn:
            rows = conn.execute(
                'SELECT price FROM price_history WHERE token=? AND timestamp<=? ORDER BY timestamp DESC LIMIT ?',
                (token.upper(), ts, n)
            ).fetchall()
        return [r[0] for r in reversed(rows)] if rows else []
    except Exception:
        return []

def get_atr_at(token, ts, period=14):
    """Compute ATR(period) from 5m candles at timestamp ts."""
    try:
        with sqlite3.connect(CANDLES_DB, timeout=5) as conn:
            rows = conn.execute(
                'SELECT high, low, close FROM candles_5m WHERE token=? AND ts<=? AND is_closed=1 ORDER BY ts DESC LIMIT ?',
                (token.upper(), ts, period + 1)
            ).fetchall()
        if len(rows) < 2:
            return None
        trs = []
        for i in range(1, len(rows)):
            h, l, c = rows[i-1]
            prev_c = rows[i][2]
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            trs.append(tr)
        return sum(trs[:period]) / min(len(trs), period) if trs else None
    except Exception:
        return None

def compute_indicators(prices):
    """Compute z_score, RSI, MACD, BB, momentum from close prices. Returns dict."""
    if len(prices) < 26:
        return {}
    last = prices[-1]
    result = {}
    w = prices[-20:]
    mean = sum(w) / len(w)
    var = sum((p - mean) ** 2 for p in w) / len(w)
    std = var ** 0.5
    if std > 0:
        z = (last - mean) / std
        result['signal_z_score'] = round(z, 4)
        result['signal_z_score_tier'] = (
            'extreme_high' if z > 2 else 'high' if z > 1 else
            'extreme_low' if z < -2 else 'low' if z < -1 else 'neutral'
        )
        result['entry_bb_position'] = round((last - (mean - 2 * std)) / (4 * std), 4)
    if len(prices) >= 15:
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [c for c in changes[-14:] if c > 0]
        losses = [-c for c in changes[-14:] if c < 0]
        ag = sum(gains) / 14 if gains else 0
        al = sum(losses) / 14 if losses else 0
        rsi = 100.0 if al == 0 else round(100 - 100 / (1 + ag / al), 2)
        result['signal_rsi_14'] = rsi
        result['entry_rsi_14'] = rsi

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
            result['signal_macd_value'] = round(ml, 8)
            result['signal_macd_signal'] = round(sig, 8)
            result['signal_macd_hist'] = round(ml - sig, 8)
            result['entry_macd_hist'] = round(ml - sig, 8)

    if len(prices) >= 6 and prices[-6]:
        vel = (prices[-1] - prices[-6]) / prices[-6] * 100
        result['signal_momentum_state'] = 'rising' if vel > 0.1 else 'falling' if vel < -0.1 else 'flat'

    if len(prices) >= 60:
        recent = prices[-60:]
        n = len(recent)
        sx = sum(range(n))
        sy = sum(recent)
        sxy = sum(i * recent[i] for i in range(n))
        sxx = sum(i * i for i in range(n))
        denom = n * sxx - sx * sx
        if denom != 0 and recent[0]:
            slope = (n * sxy - sx * sy) / denom
            pct = slope / recent[0] * 100
            result['entry_trend'] = 'up' if pct > 0.05 else 'down' if pct < -0.05 else 'flat'
    return result

def main():
    parser = argparse.ArgumentParser(description="Backfill trade indicator data")
    parser.add_argument("--dry", action="store_true", help="Dry run, no writes")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of trades")
    parser.add_argument("--token", type=str, default=None, help="Single token")
    args = parser.parse_args()

    conn = psycopg2.connect(**BRAIN_DB_DICT)
    c = conn.cursor()

    query = "SELECT id, token, open_time, signal, direction FROM trades WHERE close_time IS NOT NULL"
    params = []
    if args.token:
        query += " AND token=%s"
        params.append(args.token.upper())
    query += " ORDER BY open_time ASC"
    if args.limit:
        query += f" LIMIT {args.limit}"

    c.execute(query, params)
    trades = c.fetchall()
    total = len(trades)
    print(f"Backfilling {total} trades{' (DRY RUN)' if args.dry else ''}...")

    done = 0
    skipped = 0
    for trade_id, token, open_time, signal, direction in trades:
        ts = int(open_time.replace(tzinfo=None).timestamp())
        prices = get_prices_at(token, ts)
        if len(prices) < 26:
            skipped += 1
            continue

        indicators = compute_indicators(prices)
        atr = get_atr_at(token, ts)
        if atr:
            indicators['entry_atr_14'] = round(atr, 8)

        metadata = json.dumps(indicators, default=str)
        if not indicators:
            skipped += 1
            continue

        if not args.dry:
            set_cols = []
            set_vals = []
            for k, v in indicators.items():
                set_cols.append(f"{k}=%s")
                set_vals.append(v)
            set_cols.append("_signal_metadata=%s")
            set_vals.append(metadata)
            set_vals.append(trade_id)
            c.execute(f"UPDATE trades SET {', '.join(set_cols)} WHERE id=%s", set_vals)

        done += 1
        if done % 200 == 0:
            print(f"  ...{done}/{total} processed ({skipped} skipped)")

    if not args.dry:
        conn.commit()
    conn.close()
    print(f"Done: {done} backfilled, {skipped} skipped (insufficient price data), {total} total")

if __name__ == "__main__":
    main()