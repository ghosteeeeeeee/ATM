#!/usr/bin/env python3
"""
analyze_24h_closed_trades.py — Recipe for diagnosing TPSL bugs from closed trades.

Pulls the last 24h of closed trades from PostgreSQL, joins with 1m price_history
from signals_hermes.db, computes MFE/MAE per trade, and prints winner vs loser
profiles, per-token blacklist candidates, leverage breakdown, and time-of-day
analysis.

Usage:
    python3 analyze_24h_closed_trades.py
    python3 analyze_24h_closed_trades.py --hours 48
    python3 analyze_24h_closed_trades.py --token MERL

Companion to: /root/.hermes/brain/plans/tpsl-profit-capture-2026-06-25.md
See also: atr-trailing-debug/references/24h-trade-audit-recipe-2026-06-25.md
"""
import argparse
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime

import psycopg2
from _secrets import BRAIN_HOST, BRAIN_PASSWORD  # noqa: PLC0415


# ── DB connections ──────────────────────────────────────────────────────────
def pg_connect():
    return psycopg2.connect(
        host=BRAIN_HOST, dbname='brain', user='postgres',
        password=BRAIN_PASSWORD, connect_timeout=10,
    )


def price_connect():
    # 1m price data lives in signals_hermes.db (NOT signals_hermes_runtime.db)
    # The runtime DB has the signals table, NOT price history.
    return sqlite3.connect('/root/.hermes/data/signals_hermes.db')


# ── Pull trades ─────────────────────────────────────────────────────────────
def fetch_trades(hours=24, token=None):
    """Pull closed trades from PostgreSQL within the last N hours."""
    conn = pg_connect()
    cur = conn.cursor()
    q = """
        SELECT id, token, direction, entry_price, exit_price, pnl_usdt, pnl_pct,
               exit_reason, open_time, close_time, signal, confidence, leverage,
               stop_loss, target, highest_price, lowest_price
        FROM trades
        WHERE status='closed' AND close_time > NOW() - INTERVAL '%s hours'
    """
    params = [hours]
    if token:
        q += " AND token=%s"
        params.append(token.upper())
    q += " ORDER BY open_time ASC"
    cur.execute(q, params)
    rows = cur.fetchall()
    conn.close()
    cols = ['id', 'token', 'dir', 'entry', 'exit', 'pnl', 'pnl_pct',
            'exit_reason', 'open_time', 'close_time', 'signal', 'confidence',
            'leverage', 'sl', 'target', 'highest', 'lowest']
    return [dict(zip(cols, r)) for r in rows]


# ── Price path lookup ───────────────────────────────────────────────────────
def get_price_path(token, open_unix, close_unix):
    """Get 1m prices during a trade. Returns list of (unix_ts, price) tuples."""
    db = price_connect()
    cur = db.cursor()
    cur.execute("""
        SELECT timestamp, price FROM price_history
        WHERE token=? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp
    """, (token, open_unix, close_unix))
    rows = cur.fetchall()
    db.close()
    return rows


def compute_mfe_mae(t, prices):
    """Max favorable / adverse excursion as % from entry."""
    if not prices:
        return 0.0, 0.0
    arr = [p[1] for p in prices]
    if t['dir'] == 'LONG':
        mfe = (max(arr) - float(t['entry'])) / float(t['entry']) * 100
        mae = (float(t['entry']) - min(arr)) / float(t['entry']) * 100
    else:
        mfe = (float(t['entry']) - min(arr)) / float(t['entry']) * 100
        mae = (max(arr) - float(t['entry'])) / float(t['entry']) * 100
    return mfe, mae


# ── Report sections ─────────────────────────────────────────────────────────
def print_headline(trades):
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]
    be = [t for t in trades if t['pnl'] == 0]
    if not trades:
        print("No trades in window.")
        return
    pf = sum(t['pnl'] for t in wins) / max(abs(sum(t['pnl'] for t in losses)), 0.01)
    print(f"Trades: {len(trades)} ({len(wins)}W / {len(losses)}L / {len(be)} BE)")
    print(f"WR: {len(wins)/len(trades)*100:.1f}%  Net: ${sum(t['pnl'] for t in trades):+.2f}  "
          f"PF: {pf:.2f}")
    print(f"Avg win: {sum(t['pnl_pct'] for t in wins)/max(len(wins),1):+.2f}%  "
          f"Avg loss: {sum(t['pnl_pct'] for t in losses)/max(len(losses),1):+.2f}%")


def print_per_trade(trades):
    """One-line summary per trade with MFE/MAE."""
    print("\n" + "=" * 80)
    print("PER-TRADE MFE/MAE (1m price data)")
    print("=" * 80)
    for t in trades:
        o, c = int(t['open_time'].timestamp()), int(t['close_time'].timestamp())
        prices = get_price_path(t['token'], o, c)
        mfe, mae = compute_mfe_mae(t, prices)
        marker = "W" if t['pnl'] > 0 else ("L" if t['pnl'] < 0 else "-")
        flag = ""
        if mfe > 0.5 and t['pnl'] < 0:
            flag = "  *MISSED*"
        print(f"  {marker} #{t['id']:5d} {t['token']:6s} {t['dir']:5s} "
              f"pnl=${t['pnl']:+.2f} ({t['pnl_pct']:+.2f}%) | "
              f"MFE={mfe:5.2f}% MAE={mae:5.2f}% | exit={t['exit_reason']:15s}{flag}")


def print_per_token(trades):
    """Per-token win rate, candidates for SHORT_BLACKLIST."""
    print("\n" + "=" * 80)
    print("PER-TOKEN (n>=2) — blacklist candidates?")
    print("=" * 80)
    by_tok = defaultdict(list)
    for t in trades:
        by_tok[t['token']].append(t)
    for tok in sorted(by_tok):
        grp = by_tok[tok]
        if len(grp) < 2:
            continue
        net = sum(t['pnl'] for t in grp)
        wr = sum(1 for t in grp if t['pnl'] > 0) / len(grp) * 100
        avg_pct = sum(t['pnl_pct'] for t in grp) / len(grp)
        marker = "  <-- BLACKLIST?" if wr < 40 and len(grp) >= 3 else ""
        print(f"  {tok:8s} n={len(grp):2d}  wr={wr:5.0f}%  net=${net:+.2f}  "
              f"avg%={avg_pct:+.2f}%{marker}")


def print_per_leverage(trades):
    """3x vs 5x breakdown."""
    print("\n" + "=" * 80)
    print("PER-LEVERAGE — the 5x killer")
    print("=" * 80)
    by_lev = defaultdict(list)
    for t in trades:
        by_lev[t['leverage']].append(t)
    for lev in sorted(by_lev):
        grp = by_lev[lev]
        net = sum(t['pnl'] for t in grp)
        wr = sum(1 for t in grp if t['pnl'] > 0) / len(grp) * 100
        print(f"  {lev}x: n={len(grp):2d}  wr={wr:5.1f}%  net=${net:+.2f}")


def print_time_of_day(trades):
    """Hour-of-day pattern."""
    print("\n" + "=" * 80)
    print("TIME OF DAY (UTC)")
    print("=" * 80)
    by_h = defaultdict(list)
    for t in trades:
        by_h[t['open_time'].hour].append(t)
    for h in sorted(by_h):
        grp = by_h[h]
        w = sum(1 for t in grp if t['pnl'] > 0)
        l = sum(1 for t in grp if t['pnl'] < 0)
        net = sum(t['pnl'] for t in grp)
        wr = w / len(grp) * 100 if grp else 0
        print(f"  {h:02d}:00  W={w:2d} L={l:2d}  net=${net:+.2f}  wr={wr:.0f}%")


def print_db_integrity(trades):
    """Check for lowest_price=0 / highest_price=0 (broken trailing)."""
    print("\n" + "=" * 80)
    print("DB INTEGRITY — broken trailing detection")
    print("=" * 80)
    zero_low = [t for t in trades if t['dir'] == 'SHORT' and (not t['lowest'] or t['lowest'] == 0)]
    zero_high = [t for t in trades if t['dir'] == 'LONG' and (not t['highest'] or t['highest'] == 0)]
    print(f"  SHORT trades with lowest_price=0: {len(zero_low)}/{sum(1 for t in trades if t['dir']=='SHORT')} "
          f"({len(zero_low)/max(sum(1 for t in trades if t['dir']=='SHORT'),1)*100:.0f}%)")
    print(f"  LONG  trades with highest_price=0: {len(zero_high)}/{sum(1 for t in trades if t['dir']=='LONG')} "
          f"({len(zero_high)/max(sum(1 for t in trades if t['dir']=='LONG'),1)*100:.0f}%)")
    if zero_low:
        print(f"  Affected SHORT trades: {[(t['id'], t['token']) for t in zero_low]}")
    if zero_high:
        print(f"  Affected LONG trades: {[(t['id'], t['token']) for t in zero_high]}")


def print_profit_monster_clip(trades):
    """Distribution of winning pnl_pct — check for 0.7% floor clipping."""
    print("\n" + "=" * 80)
    print("PROFIT-MONSTER FLOOR CLIPPING")
    print("=" * 80)
    wins = [t for t in trades if t['pnl'] > 0]
    buckets = Counter()
    for t in wins:
        buckets[round(t['pnl_pct'], 1)] += 1
    for pct in sorted(buckets):
        bar = "█" * buckets[pct]
        print(f"  +{pct:.1f}% : {buckets[pct]:2d} {bar}")
    if wins:
        print(f"  Max winner: +{max(t['pnl_pct'] for t in wins):.2f}%")


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--hours', type=int, default=24, help='Window in hours (default 24)')
    ap.add_argument('--token', type=str, default=None, help='Filter to a single token')
    args = ap.parse_args()

    print(f"Loading closed trades from last {args.hours}h"
          f"{f' for {args.token}' if args.token else ''}...")
    trades = fetch_trades(args.hours, args.token)
    if not trades:
        print("No trades found.")
        sys.exit(0)

    print_headline(trades)
    print_per_trade(trades)
    print_per_token(trades)
    print_per_leverage(trades)
    print_time_of_day(trades)
    print_db_integrity(trades)
    print_profit_monster_clip(trades)


if __name__ == '__main__':
    main()
