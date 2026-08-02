#!/usr/bin/env python3
"""
backtest_macd_accel.py — Backtest MACD(8,50,12) Crossover + Acceleration Signal.

Tests on local candles.db across all tokens with sufficient 1m history.
Reports per-token and aggregate: win rate, avg PnL%, total PnL, signal count.

Run: python3 backtest_macd_accel.py [--tokens BTC,ETH,SOL] [--bars 3000]
"""

import sys, os, sqlite3, argparse, statistics
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from macd_accel_signals import (
    detect_macd_accel, FAST, SLOW, SIGNAL, MIN_BARS,
    SIGNAL_TYPE_LONG, SIGNAL_TYPE_SHORT,
)

DB_CANDLES = '/root/.hermes/data/candles.db'


# ── Candle fetch ──────────────────────────────────────────────────────────────

def get_1m_closes(token, lookback=2000):
    """Fetch 1m closes from candles.db."""
    try:
        conn = sqlite3.connect(DB_CANDLES, timeout=15)
        c = conn.cursor()
        c.execute(
            "SELECT close FROM candles_1m WHERE token=? "
            "ORDER BY ts ASC LIMIT ?",
            (token.upper(), lookback)
        )
        rows = c.fetchall()
        conn.close()
        if not rows:
            return None
        return [r[0] for r in rows]
    except Exception as e:
        print(f"  [{token}] DB error: {e}")
        return None


# ── Simulate signal + trade ──────────────────────────────────────────────────

def backtest_token(token, lookback=2000, hold=10, min_signals=3):
    """
    Backtest macd_accel on one token.
    Entry: bar where crossover+accel fires
    Exit:  hold bars later OR reverse signal

    Returns dict with per-direction stats.
    """
    closes = get_1m_closes(token, lookback)
    if closes is None or len(closes) < MIN_BARS + hold + 2:
        return None

    long_pnls = []
    short_pnls = []

    # Iterate every bar, detect entry signals
    for i in range(MIN_BARS + 2, len(closes) - hold - 1):
        window = closes[:i+1]
        result = detect_macd_accel(window)
        if result is None:
            continue

        direction, _ = result
        entry_price = closes[i]
        exit_price = closes[i + hold]
        pnl_pct = (exit_price - entry_price) / entry_price * 100

        if direction == 'LONG':
            long_pnls.append(pnl_pct)
        else:
            short_pnls.append(pnl_pct)

    total_signals = len(long_pnls) + len(short_pnls)
    if total_signals < min_signals:
        return None

    def stats(pnls):
        if not pnls:
            return 0, 0, 0
        wr = sum(1 for p in pnls if p > 0) / len(pnls) * 100
        avg = statistics.mean(pnls)
        return wr, avg, len(pnls)

    long_wr,  long_avg,  long_n  = stats(long_pnls)
    short_wr, short_avg, short_n = stats(short_pnls)

    return {
        'token': token,
        'long_wr': long_wr,  'long_avg': long_avg,  'long_n': long_n,
        'short_wr': short_wr, 'short_avg': short_avg, 'short_n': short_n,
        'long_pnls': long_pnls, 'short_pnls': short_pnls,
    }


# ── Aggregate ────────────────────────────────────────────────────────────────

def aggregate(all_results):
    """Aggregate stats by pooling all per-token PnL lists."""
    long_pnls  = []
    short_pnls = []
    for r in all_results:
        long_pnls.extend(r.get('long_pnls',  []))
        short_pnls.extend(r.get('short_pnls', []))

    def stats(pnls):
        if not pnls:
            return 0, 0, 0
        wr = sum(1 for p in pnls if p > 0) / len(pnls) * 100
        avg = statistics.mean(pnls)
        return wr, avg, len(pnls)

    long_wr,  long_avg,  long_n  = stats(long_pnls)
    short_wr, short_avg, short_n = stats(short_pnls)
    total_n = long_n + short_n

    return {
        'long_wr': long_wr, 'long_avg': long_avg, 'long_n': long_n,
        'short_wr': short_wr, 'short_avg': short_avg, 'short_n': short_n,
        'total_n': total_n,
    }


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Backtest MACD(8,50,12) Acceleration Signal')
    parser.add_argument('--tokens', default='ALL',
                        help='Comma-separated tokens or ALL (default: ALL)')
    parser.add_argument('--bars', type=int, default=3000,
                        help='Lookback bars (default: 3000)')
    parser.add_argument('--hold', type=int, default=10,
                        help='Hold bars (default: 10)')
    parser.add_argument('--min', type=int, default=3,
                        help='Minimum signals to report token (default: 3)')
    args = parser.parse_args()

    if args.tokens == 'ALL':
        try:
            conn = sqlite3.connect(DB_CANDLES, timeout=10)
            c = conn.cursor()
            c.execute("SELECT DISTINCT token FROM candles_1m ORDER BY token LIMIT 40")
            tokens = [r[0] for r in c.fetchall()]
            conn.close()
        except Exception as e:
            print(f"Failed to get tokens: {e}")
            tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'AVAX', 'LINK', 'DOGE', 'DOT', 'MATIC']
    else:
        tokens = [t.strip().upper() for t in args.tokens.split(',')]

    print(f"Backtest MACD(8,50,12) Accel — {len(tokens)} tokens, {args.bars} bars, hold={args.hold}")
    print("=" * 80)

    results = []
    for token in tokens:
        r = backtest_token(token, lookback=args.bars, hold=args.hold, min_signals=args.min)
        if r:
            results.append(r)
            print(
                f"  {token:8s}  LONG: {r['long_n']:3d}s WR={r['long_wr']:5.1f}% avg={r['long_avg']:+.3f}%  "
                f"SHORT: {r['short_n']:3d}s WR={r['short_wr']:5.1f}% avg={r['short_avg']:+.3f}%"
            )

    if not results:
        print("No results — try more bars or check token names.")
        return

    agg = aggregate(results)
    print("=" * 80)
    print(
        f"  AGGREGATE  LONG: {agg['long_n']:3d}s WR={agg['long_wr']:5.1f}% avg={agg['long_avg']:+.3f}%  "
        f"SHORT: {agg['short_n']:3d}s WR={agg['short_wr']:5.1f}% avg={agg['short_avg']:+.3f}%"
    )
    total_pnl_long   = agg['long_n']  * agg['long_avg']
    total_pnl_short  = agg['short_n'] * agg['short_avg']
    print(
        f"  TOTAL PNL  LONG: {total_pnl_long:+.2f}%  SHORT: {total_pnl_short:+.2f}%  "
        f"COMBINED: {total_pnl_long + total_pnl_short:+.2f}%"
    )

    # Per-token breakdown sorted by combined PnL
    print("\n--- Per-token ranked by combined PnL ---")
    ranked = sorted(results, key=lambda r: (r['long_n'] * r['long_avg'] + r['short_n'] * r['short_avg']), reverse=True)
    for r in ranked:
        combined_pnl = r['long_n'] * r['long_avg'] + r['short_n'] * r['short_avg']
        total = r['long_n'] + r['short_n']
        print(f"  {r['token']:8s}  {total:3d}s  combined_pnl={combined_pnl:+.3f}%  "
              f"L:({r['long_n']}s,{r['long_wr']:.0f}%,{r['long_avg']:+.3f}%)  "
              f"S:({r['short_n']}s,{r['short_wr']:.0f}%,{r['short_avg']:+.3f}%)")


if __name__ == '__main__':
    main()
