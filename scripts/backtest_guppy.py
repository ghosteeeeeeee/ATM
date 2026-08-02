"""
backtest_guppy.py — Guppy MMA Historical Backtester
==================================================
Walks through candles.db historical data to evaluate guppy signal performance.
No HL API calls — pure local SQLite + stdlib.

Usage:
  python3 backtest_guppy.py <TOKEN> [interval=1m] [start_ts=0] [end_ts=now]
  python3 backtest_guppy.py --scan-all [max_tokens=50]

Exit logic: reverse guppy signal (fast group flips = exit, opposite signal = entry in opposite direction)
No fixed TP/SL — pure signal-driven exits.

Output:
  CSV of all trades with: token, direction, entry_time, exit_time, entry_price, exit_price, pnl_pct, squeeze_at_entry, sep_at_entry, conf_at_entry, exit_reason
  Plus summary stats at the end.
"""

import sys
import os
import sqlite3
import csv
import math
from datetime import datetime
from typing import Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CANDLES_DB  = "/root/.hermes/data/candles.db"

# Append script dir so we can import guppy_signals
sys.path.insert(0, SCRIPT_DIR)
import guppy_signals as gs


# ── Data Fetching ─────────────────────────────────────────────────────────────

def fetch_candles_for_backtest(token: str, interval: str = "1m",
                                start_ts: int = 0,
                                end_ts: int = None) -> list:
    """Fetch all candles for a token in a time range, ordered oldest→newest."""
    table = {
        '1m': 'candles_1m', '5m': 'candles_5m',
        '15m': 'candles_15m', '1h': 'candles_1h', '4h': 'candles_4h'
    }.get(interval, 'candles_1m')

    end_ts = end_ts or int(datetime.now().timestamp())

    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=30)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT token, ts, open, high, low, close, volume, is_closed
            FROM {table}
            WHERE token = ? AND ts >= ? AND ts <= ?
            ORDER BY ts ASC
        """, (token.upper(), start_ts, end_ts))
        rows = [tuple(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except sqlite3.Error as e:
        print(f"DB error for {token}: {e}")
        return []


# ── Rolling Window Walk ──────────────────────────────────────────────────────

def backtest_token(token: str, interval: str = "1m",
                   start_ts: int = 0, end_ts: int = None,
                   lookback: int = 120,
                   min_confidence: float = 0.60,
                   tp_pct: float = 0.0,
                   sl_pct: float = 0.0) -> list:
    """
    Walk through historical candles for a single token using a rolling window.
    At each bar, look back `lookback` bars and check for guppy signal.

    Exit logic (in priority order):
      1. SL hit: price moves against entry by sl_pct
      2. TP hit: price moves in favor of entry by tp_pct
      3. Reverse signal: opposite guppy signal fires → close + reverse
      4. end_of_data

    tp_pct / sl_pct: 0.0 = disabled. e.g. tp_pct=1.5 means TP at +1.5% from entry.

    Returns: list of trade dicts
    """
    rows = fetch_candles_for_backtest(token, interval, start_ts, end_ts)
    if len(rows) < lookback + 1:
        return []

    trades = []
    position = None

    for i in range(lookback, len(rows)):
        window = rows[i - lookback: i + 1]
        curr_row = rows[i]
        curr_ts = curr_row[1]
        curr_close = curr_row[4]

        sig = gs.detect_guppy_signal(window)
        if sig is None or sig['confidence'] < min_confidence:
            continue

        direction = sig['direction']

        if position is None:
            position = {
                'direction':    direction,
                'entry_price':  curr_close,
                'entry_ts':     curr_ts,
                'entry_sig':    sig,
                'tp_hit':       False,
                'sl_hit':       False,
            }
        else:
            entry = position['entry_price']
            pnl_raw = (curr_close - entry) / entry * 100.0
            if position['direction'] == 'SHORT':
                pnl_raw = -pnl_raw

            exited = False
            reason = None

            if sl_pct > 0 and pnl_raw <= -sl_pct:
                exited = True
                reason = 'sl'
                position['tp_hit'] = False
                position['sl_hit'] = True
            elif tp_pct > 0 and pnl_raw >= tp_pct:
                exited = True
                reason = 'tp'
                position['tp_hit'] = True
                position['sl_hit'] = False
            elif direction != position['direction']:
                exited = True
                reason = 'guppy_fast_flip'
                position['tp_hit'] = False
                position['sl_hit'] = False

            if exited:
                pnl_pct = _calc_pnl(position['direction'], position['entry_price'], curr_close)
                trades.append({
                    'token':          token,
                    'direction':      position['direction'],
                    'entry_ts':       position['entry_ts'],
                    'exit_ts':        curr_ts,
                    'entry_price':    position['entry_price'],
                    'exit_price':     curr_close,
                    'pnl_pct':        round(pnl_pct, 4),
                    'exit_reason':    reason,
                    'squeeze_at_entry': position['entry_sig'].get('squeeze', False),
                    'sep_at_entry':   round(position['entry_sig'].get('separation', 0), 3),
                    'conf_at_entry':  round(position['entry_sig'].get('confidence', 0), 2),
                    'bars_held':      (curr_ts - position['entry_ts']) // 60 if interval == '1m' else (curr_ts - position['entry_ts']) // 300,
                    'tp_hit':         position.get('tp_hit', False),
                    'sl_hit':         position.get('sl_hit', False),
                })
                position = {
                    'direction':    direction,
                    'entry_price':  curr_close,
                    'entry_ts':     curr_ts,
                    'entry_sig':    sig,
                    'tp_hit':       False,
                    'sl_hit':       False,
                }

    if position is not None:
        last_row = rows[-1]
        last_close = last_row[4]
        last_ts = last_row[1]
        pnl_pct = _calc_pnl(position['direction'], position['entry_price'], last_close)
        trades.append({
            'token':          token,
            'direction':      position['direction'],
            'entry_ts':       position['entry_ts'],
            'exit_ts':        last_ts,
            'entry_price':    position['entry_price'],
            'exit_price':     last_close,
            'pnl_pct':        round(pnl_pct, 4),
            'exit_reason':    'end_of_data',
            'squeeze_at_entry': position['entry_sig'].get('squeeze', False),
            'sep_at_entry':   round(position['entry_sig'].get('separation', 0), 3),
            'conf_at_entry':  round(position['entry_sig'].get('confidence', 0), 2),
            'bars_held':      (last_ts - position['entry_ts']) // 60 if interval == '1m' else (last_ts - position['entry_ts']) // 300,
            'tp_hit':         position.get('tp_hit', False),
            'sl_hit':         position.get('sl_hit', False),
        })

    return trades


def _calc_pnl(direction: str, entry: float, exit: float) -> float:
    if direction == 'LONG':
        return (exit - entry) / entry * 100.0
    else:  # SHORT
        return (entry - exit) / entry * 100.0


# ── Stats ────────────────────────────────────────────────────────────────────

def compute_stats(trades: list) -> dict:
    if not trades:
        return {}

    pnls = [t['pnl_pct'] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    return {
        'total_trades':    len(trades),
        'wins':            len(wins),
        'losses':          len(losses),
        'win_rate':        round(len(wins) / len(trades) * 100, 2) if trades else 0,
        'avg_pnl':         round(sum(pnls) / len(pnls), 4),
        'best_trade':      round(max(pnls), 4),
        'worst_trade':     round(min(pnls), 4),
        'max_drawdown':    round(min(pnls), 4),
        'avg_bars_held':   round(sum(t.get('bars_held', 0) for t in trades) / len(trades), 1),
        'squeeze_rate':    round(sum(1 for t in trades if t.get('squeeze_at_entry')) / len(trades) * 100, 1),
    }


def print_stats(token: str, stats: dict, trades: list):
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"BACKTEST RESULTS: {token}")
    print(f"{sep}")
    if not stats:
        print("  No trades generated.")
        return

    print(f"  Total trades:    {stats['total_trades']}")
    print(f"  Win rate:        {stats['win_rate']}%")
    print(f"  Wins / Losses:  {stats['wins']} / {stats['losses']}")
    print(f"  Avg PnL:         {stats['avg_pnl']:+.4f}%")
    print(f"  Best trade:     {stats['best_trade']:+.4f}%")
    print(f"  Worst trade:    {stats['worst_trade']:+.4f}%")
    print(f"  Max drawdown:   {stats['max_drawdown']:+.4f}%")
    print(f"  Avg bars held:  {stats['avg_bars_held']}")
    print(f"  Squeeze rate:   {stats['squeeze_rate']}%")

    print(f"\n  Last 10 trades:")
    print(f"  {'Dir':<6} {'Entry':>10} {'Exit':>10} {'PnL%':>8} {'Exit Reason':<20} {'Conf':>5}")
    for t in trades[-10:]:
        print(f"  {t['direction']:<6} {t['entry_price']:>10.6f} {t['exit_price']:>10.6f} {t['pnl_pct']:>+8.4f}% {t['exit_reason']:<20} {t['conf_at_entry']:>5.2f}")


# ── CSV Output ───────────────────────────────────────────────────────────────

CSV_FILE = "/root/.hermes/data/guppy_backtest_results.csv"


def write_csv(trades: list, append: bool = False):
    mode = 'a' if append else 'w'
    with open(CSV_FILE, mode, newline='') as f:
        if not trades:
            return
        fieldnames = ['token', 'direction', 'entry_ts', 'exit_ts',
                      'entry_price', 'exit_price', 'pnl_pct',
                      'exit_reason', 'squeeze_at_entry', 'sep_at_entry',
                      'conf_at_entry', 'bars_held']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not append:
            writer.writeheader()
        for t in trades:
            writer.writerow({k: t[k] for k in fieldnames})
    print(f"CSV written to {CSV_FILE} ({len(trades)} trades)")


# ── Scan All Tokens ──────────────────────────────────────────────────────────

def scan_all_tokens(max_tokens: int = 50, interval: str = "1m",
                    start_ts: int = 0, end_ts: int = None) -> list:
    """Backtest top tokens by data availability."""
    tokens = gs.get_available_tokens(interval=interval)
    print(f"Found {len(tokens)} tokens. Backtesting first {max_tokens}...")
    all_trades = []

    for token in tokens[:max_tokens]:
        trades = backtest_token(token, interval=interval,
                                start_ts=start_ts, end_ts=end_ts,
                                tp_pct=0.0, sl_pct=0.0)
        if trades:
            all_trades.extend(trades)
            stats = compute_stats(trades)
            print(f"  {token}: {stats.get('total_trades', 0)} trades, "
                  f"win_rate={stats.get('win_rate', 0)}%, avg_pnl={stats.get('avg_pnl', 0):+.3f}%")

    return all_trades


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Guppy MMA backtester")
    parser.add_argument('token', nargs='?', default=None,
                        help="Token to backtest (e.g. HYPE). Use --scan-all for all.")
    parser.add_argument('--interval', '-i', default='1m',
                        help="Candle interval: 1m, 5m, 15m, 1h, 4h (default: 1m)")
    parser.add_argument('--start', '-s', type=int, default=0,
                        help="Start Unix timestamp (default: 0 = all data)")
    parser.add_argument('--end', '-e', type=int, default=None,
                        help="End Unix timestamp (default: now)")
    parser.add_argument('--lookback', '-l', type=int, default=120,
                        help="Lookback bars for EMA computation (default: 120)")
    parser.add_argument('--conf', '-c', type=float, default=0.60,
                        help="Min confidence threshold (default: 0.60)")
    parser.add_argument('--tp', type=float, default=0.0,
                        help="Take profit % (e.g. 1.0 = TP at +1.0%% from entry, default: 0 = disabled)")
    parser.add_argument('--sl', type=float, default=0.0,
                        help="Stop loss %% (e.g. 0.75 = SL at -0.75%% from entry, default: 0 = disabled)")
    parser.add_argument('--scan-all', action='store_true',
                        help="Scan all available tokens")
    parser.add_argument('--max-tokens', type=int, default=50,
                        help="Max tokens to scan with --scan-all (default: 50)")
    parser.add_argument('--no-csv', action='store_true',
                        help="Don't write CSV output")
    args = parser.parse_args()

    end_ts = args.end or int(datetime.now().timestamp())

    if args.scan_all or args.token is None:
        print(f"=== GUPPY BACKTEST: SCAN ALL (interval={args.interval}) ===")
        all_trades = scan_all_tokens(
            max_tokens=args.max_tokens,
            interval=args.interval,
            start_ts=args.start,
            end_ts=end_ts,
        )
        if all_trades:
            overall_stats = compute_stats(all_trades)
            print_stats("ALL TOKENS", overall_stats, all_trades)
            if not args.no_csv:
                write_csv(all_trades)
    else:
        token = args.token.upper()
        print(f"=== GUPPY BACKTEST: {token} (interval={args.interval}) ===")
        print(f"  Period: {datetime.fromtimestamp(args.start)} → {datetime.fromtimestamp(end_ts)}")
        print(f"  Lookback: {args.lookback} bars | Min confidence: {args.conf}")
        trades = backtest_token(
            token,
            interval=args.interval,
            start_ts=args.start,
            end_ts=end_ts,
            lookback=args.lookback,
            min_confidence=args.conf,
            tp_pct=args.tp,
            sl_pct=args.sl,
        )
        stats = compute_stats(trades)
        print_stats(token, stats, trades)
        if trades and not args.no_csv:
            write_csv(trades, append=False)
