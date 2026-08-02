#!/usr/bin/env python3
"""Trace one abandoned trade through the full pipeline.

Pulls:
  - trade row (entry, exit, SL, PnL, duration)
  - signal row from signals_hermes_runtime.db
  - audit log entries around open_time
  - price_history at entry
  - hl_sync_guardian log entries

Reveals: where the trade came from, what SL was set, what price moved during the trade.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras


def fetch_trade(trade_id: int) -> dict:
    pg = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
    cur = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM trades WHERE id = %s", (trade_id,))
    trade = cur.fetchone()
    pg.close()
    return trade


def fetch_signal(signal_id, runtime_db: str) -> list[dict]:
    if not os.path.exists(runtime_db):
        return []
    con = sqlite3.connect(runtime_db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM signals WHERE id = ?", (signal_id,))
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows


def fetch_audit_lines(trade: dict, audit_log: str, around_seconds: int = 60) -> list[str]:
    """Return audit-log lines that mention the trade's id within +/- around_seconds of open_time."""
    if not os.path.exists(audit_log):
        return []
    open_ts = int(trade['open_time'].replace(tzinfo=timezone.utc).timestamp())
    needle = str(trade['id'])
    pattern = re.compile(r'\b' + needle + r'\b')
    hits = []
    with open(audit_log, 'rb') as f:
        for line in f:
            try:
                text = line.decode('utf-8', errors='replace')
            except Exception:
                continue
            if not pattern.search(text):
                continue
            m = re.search(r'\[?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', text)
            if m:
                try:
                    line_ts = int(
                        datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
                        .replace(tzinfo=timezone.utc).timestamp()
                    )
                except ValueError:
                    hits.append(text)
                    continue
                if abs(line_ts - open_ts) > around_seconds * 6:  # wide window to catch lag
                    continue
            hits.append(text)
    return hits


def fetch_price_around(token: str, when_ts: int, price_db: str, around_seconds: int = 600) -> list[dict]:
    if not os.path.exists(price_db):
        return []
    con = sqlite3.connect(price_db)
    cur = con.cursor()
    cur.execute(
        """
        SELECT timestamp, price FROM price_history
        WHERE token = ? AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
        """,
        (token.upper(), when_ts - around_seconds, when_ts + around_seconds),
    )
    rows = [{'ts': ts, 'price': price, 'tstr': datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}
            for ts, price in cur.fetchall()]
    con.close()
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trade_id', type=int)
    parser.add_argument('--signal-id', type=int, default=None,
                        help='Override signal lookup (if not stored in trade row)')
    parser.add_argument('--audit-log', default='/root/.hermes/data/audit.log')
    parser.add_argument('--runtime-db', default='/root/.hermes/data/signals_hermes_runtime.db')
    parser.add_argument('--price-db', default='/root/.hermes/data/signals_hermes.db')
    args = parser.parse_args()

    trade = fetch_trade(args.trade_id)
    if not trade:
        print(f'No trade #{args.trade_id}')
        return

    print(f"== Trade #{trade['id']} ==")
    for k, v in trade.items():
        if isinstance(v, datetime):
            v = v.isoformat()
        print(f'  {k:20s} = {v}')

    open_ts = int(trade['open_time'].replace(tzinfo=timezone.utc).timestamp())
    close_ts = int(trade['close_time'].replace(tzinfo=timezone.utc).timestamp())
    print(f'\n  open_ts  = {open_ts}  ({datetime.fromtimestamp(open_ts, tz=timezone.utc).isoformat()})')
    print(f'  close_ts = {close_ts}  ({datetime.fromtimestamp(close_ts, tz=timezone.utc).isoformat()})')
    print(f'  duration = {close_ts - open_ts}s')

    if trade['stop_loss']:
        entry = float(trade['entry_price'])
        sl = float(trade['stop_loss'])
        if trade['direction'] == 'LONG':
            sl_dist = (entry - sl) / entry * 100
        else:
            sl_dist = (sl - entry) / entry * 100
        print(f'  SL distance from entry = {sl_dist:+.3f}%  (entry={entry}, sl={sl})')

    if trade['exit_price']:
        ep = float(trade['exit_price'])
        e = float(trade['entry_price'])
        if trade['direction'] == 'LONG':
            move = (ep - e) / e * 100
        else:
            move = (e - ep) / e * 100
        print(f'  Price move entry->exit = {move:+.3f}%')

    # Signals table lookup
    if args.signal_id:
        signals = fetch_signal(args.signal_id, args.runtime_db)
        print(f'\n-- signals row {args.signal_id} ({len(signals)} found) --')
        for s in signals:
            print(' ', s)

    # Audit log
    audit_lines = fetch_audit_lines(trade, args.audit_log)
    print(f'\n-- audit.log mentions of trade #{trade["id"]} ({len(audit_lines)} lines) --')
    for line in audit_lines[-30:]:
        print(' ', line.rstrip())

    # Price around open
    prices = fetch_price_around(trade['token'], open_ts, args.price_db)
    print(f'\n-- price_history around open ({len(prices)} rows) --')
    for row in prices[-30:]:
        marker = 'OPEN' if abs(row['ts'] - open_ts) < 60 else '    '
        print(f"  [{row['tstr']}] {row['price']:>12.8g}  {marker}")


if __name__ == '__main__':
    main()
