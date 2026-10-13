#!/usr/bin/env python3
"""
mom_filter_shadow.py — Counterfactual tracking for momentum S/R filter.

Records every MOMENTUM SR-FILTER activation from pipeline.log (standalone
log-parsing — zero code in the live trading path), then closes each event
24h+ later with the would-be outcome: did a trade on that token+direction
actually fire and close? What would the result have been?

Modes (default runs all three in sequence):
  --record   parse new pipeline.log lines since last offset -> events
  --close    close events older than 24h via signal_outcomes counterfactual join
  --report   aggregate shadow WR (feeds CEO decision)

Output DB: brain/mom_filter_shadow.db (SQLite, own file).

Usage: python3 scripts/mom_filter_shadow.py [--record] [--close] [--report]
"""
import sys
import os
import re
import sqlite3
import argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, HERMES_LOG_DIR, RUNTIME_DB

SHADOW_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'mom_filter_shadow.db')
PIPELINE_LOG = os.path.join(HERMES_LOG_DIR, 'pipeline.log')
OFFSET_FILE = os.path.join(HERMES_DATA, 'mom_filter_shadow_offset.txt')
CLOSE_AFTER_HOURS = 24

# Shadow log line format from risk_reward_engine.py:
#   MOMENTUM SR-FILTER TOKEN DIRECTION: skipped N nearby levels (vel=X.XXXX%/candle, skip_dist=X.XX%)
MOM_FILTER_RE = re.compile(
    r'MOMENTUM SR-FILTER\s+(\S+)\s+(LONG|SHORT):\s+skipped\s+(\d+)\s+nearby\s+levels'
    r'.*?vel=([-\d.]+)%/candle.*?skip_dist=([\d.]+)%',
)

# Also capture RR engine shadow blocks (context for what the filter changes):
#   [rr-engine] SHADOW BLOCK TOKEN DIRECTION $PRICE: R:R X.XX < Y.Y minimum for REGIME regime
RR_SHADOW_RE = re.compile(
    r'\[rr-engine\]\s+SHADOW BLOCK\s+(\S+)\s+(LONG|SHORT)\s+\$([\d.]+):\s+R:R\s+([\d.]+)\s+<\s+([\d.]+)\s+minimum\s+for\s+(\w+)',
)


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [mom_filter_shadow] {msg}', flush=True)


def init_db():
    os.makedirs(os.path.dirname(SHADOW_DB), exist_ok=True)
    conn = sqlite3.connect(SHADOW_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL,
        direction TEXT NOT NULL,
        skipped_levels INTEGER,
        velocity_pct REAL,
        skip_dist_pct REAL,
        rr_engine_rr REAL,
        rr_engine_regime TEXT,
        event_ts TEXT NOT NULL,
        closed INTEGER DEFAULT 0,
        closed_ts TEXT,
        would_trade INTEGER,
        pnl_usdt REAL,
        wr_outcome TEXT,
        notes TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS offsets (
        key TEXT PRIMARY KEY,
        offset INTEGER NOT NULL
    )''')
    conn.commit()
    return conn


def get_offset(conn, key='pipeline_log'):
    c = conn.cursor()
    c.execute('SELECT offset FROM offsets WHERE key=?', (key,))
    row = c.fetchone()
    return row[0] if row else 0


def set_offset(conn, key, offset):
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO offsets (key, offset) VALUES (?, ?)', (key, offset))
    conn.commit()


def record(conn):
    """Parse new pipeline.log lines since last offset -> events."""
    if not os.path.exists(PIPELINE_LOG):
        log(f'pipeline.log not found at {PIPELINE_LOG}')
        return 0

    file_size = os.path.getsize(PIPELINE_LOG)
    offset = get_offset(conn)

    # Handle log rotation: if file shrank, reset offset
    if offset > file_size:
        log(f'Log rotation detected (offset {offset} > size {file_size}), resetting')
        offset = 0

    if offset >= file_size:
        return 0

    with open(PIPELINE_LOG, 'r', errors='replace') as f:
        f.seek(offset)
        new_lines = f.readlines()
        new_offset = f.tell()

    set_offset(conn, 'pipeline_log', new_offset)

    # Parse MOMENTUM SR-FILTER lines
    mom_events = []
    rr_blocks = {}  # (token, direction) -> most recent RR block info

    for line in new_lines:
        m = MOM_FILTER_RE.search(line)
        if m:
            token, direction, skipped, vel, skip_dist = m.groups()
            ts_str = line[:19]  # "YYYY-MM-DD HH:MM:SS"
            mom_events.append({
                'token': token.upper(),
                'direction': direction,
                'skipped': int(skipped),
                'velocity': float(vel),
                'skip_dist': float(skip_dist),
                'ts': ts_str,
            })

        # Capture RR shadow blocks for context
        rm = RR_SHADOW_RE.search(line)
        if rm:
            token, direction, price, rr, min_rr, regime = rm.groups()
            rr_blocks[(token.upper(), direction)] = {
                'rr': float(rr),
                'min_rr': float(min_rr),
                'regime': regime,
            }

    # Insert events with dedup (10-min bucket per token+direction)
    c = conn.cursor()
    inserted = 0
    for ev in mom_events:
        # Check for recent duplicate
        c.execute('''SELECT COUNT(*) FROM events
                     WHERE token=? AND direction=?
                     AND event_ts > datetime(?, '-10 minutes')''',
                  (ev['token'], ev['direction'], ev['ts']))
        if c.fetchone()[0] > 0:
            continue

        # Attach RR context if available
        rr_info = rr_blocks.get((ev['token'], ev['direction']), {})
        c.execute('''INSERT INTO events
                     (token, direction, skipped_levels, velocity_pct, skip_dist_pct,
                      rr_engine_rr, rr_engine_regime, event_ts)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (ev['token'], ev['direction'], ev['skipped'], ev['velocity'],
                   ev['skip_dist'], rr_info.get('rr'), rr_info.get('regime'), ev['ts']))
        inserted += 1

    conn.commit()
    if inserted:
        log(f'Recorded {inserted} new events ({len(mom_events)} parsed, {len(rr_blocks)} RR blocks seen)')
    return inserted


def close(conn):
    """Close events older than 24h via signal_outcomes counterfactual join."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=CLOSE_AFTER_HOURS)).strftime('%Y-%m-%d %H:%M:%S')
    c = conn.cursor()
    c.execute('SELECT id, token, direction, event_ts FROM events WHERE closed=0 AND event_ts < ?', (cutoff,))
    events = c.fetchall()
    if not events:
        return 0

    # Connect to runtime DB for outcome lookup
    rt_conn = sqlite3.connect(RUNTIME_DB, timeout=10)
    rt_cur = rt_conn.cursor()

    closed = 0
    for eid, token, direction, ev_ts in events:
        # Find trades on this token+direction after the event
        rt_cur.execute('''SELECT pnl_usdt FROM signal_outcomes
                          WHERE token=? AND direction=?
                          AND created_at >= ?
                          ORDER BY created_at ASC LIMIT 1''',
                       (token, direction, ev_ts))
        row = rt_cur.fetchone()

        if row:
            pnl = float(row[0]) if row[0] is not None else 0.0
            outcome = 'WIN' if pnl > 0 else 'LOSS'
            c.execute('''UPDATE events SET closed=1, closed_ts=?, would_trade=1,
                         pnl_usdt=?, wr_outcome=? WHERE id=?''',
                      (datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                       pnl, outcome, eid))
        else:
            # No trade fired — mark as "no trade"
            c.execute('''UPDATE events SET closed=1, closed_ts=?, would_trade=0,
                         notes='no trade fired in 24h' WHERE id=?''',
                      (datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), eid))
        closed += 1

    rt_cur.close()
    rt_conn.close()
    conn.commit()
    if closed:
        log(f'Closed {closed} events (>{CLOSE_AFTER_HOURS}h old)')
    return closed


def report(conn):
    """Aggregate shadow WR per filter activation."""
    c = conn.cursor()

    # Overall stats
    c.execute('SELECT COUNT(*) FROM events')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM events WHERE closed=1')
    closed = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM events WHERE closed=1 AND would_trade=1')
    traded = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM events WHERE closed=1 AND wr_outcome="WIN"')
    wins = c.fetchone()[0]
    c.execute('SELECT COALESCE(SUM(pnl_usdt), 0) FROM events WHERE closed=1 AND would_trade=1')
    total_pnl = c.fetchone()[0]

    wr = (wins / traded * 100) if traded > 0 else 0

    print(f'\n{"="*60}')
    print(f'MOMENTUM S/R FILTER SHADOW REPORT')
    print(f'{"="*60}')
    print(f'  Total events:    {total}')
    print(f'  Closed:          {closed}')
    print(f'  Would have traded: {traded}')
    print(f'  Wins:            {wins}')
    print(f'  Win rate:        {wr:.1f}%')
    print(f'  Total PnL:       ${total_pnl:.2f}')

    # Decision rule from automatic-implementation skill:
    # >=55% WR + positive PnL (n>=15) -> PROPOSE RELAX
    # <=35% WR (n>=15) -> GATE WORKING
    # 36-54% (n>=15) -> MONITOR
    # <15 trades -> INSUFFICIENT DATA
    print(f'\n  Decision:')
    if traded < 15:
        print(f'    INSUFFICIENT DATA (n={traded} < 15) — extend shadow')
    elif wr >= 55 and total_pnl > 0:
        print(f'    PROPOSE ENFORCE — WR {wr:.1f}% >= 55%, PnL +${total_pnl:.2f}')
    elif wr <= 35:
        print(f'    GATE WORKING — WR {wr:.1f}% <= 35% (filter correctly identifies losers)')
    else:
        print(f'    MONITOR — WR {wr:.1f}% inconclusive (36-54%)')

    # Per-direction breakdown
    for d in ['LONG', 'SHORT']:
        c.execute('''SELECT COUNT(*), SUM(CASE WHEN wr_outcome='WIN' THEN 1 ELSE 0 END),
                     COALESCE(SUM(pnl_usdt), 0)
                     FROM events WHERE closed=1 AND would_trade=1 AND direction=?''', (d,))
        row = c.fetchone()
        n, w, pnl = row[0], row[1] or 0, row[2]
        d_wr = (w / n * 100) if n > 0 else 0
        print(f'  {d}: n={n}, WR={d_wr:.1f}%, PnL=${pnl:.2f}')

    # Recent activations
    print(f'\n  Recent activations:')
    c.execute('''SELECT token, direction, skipped_levels, velocity_pct, event_ts
                 FROM events ORDER BY event_ts DESC LIMIT 10''')
    for row in c.fetchall():
        tok, d, sk, vel, ts = row
        print(f'    {ts} {tok} {d}: skipped {sk} levels, vel={vel:.4f}%/candle')

    print(f'{"="*60}\n')


def main():
    parser = argparse.ArgumentParser(description='Momentum S/R filter shadow tracker')
    parser.add_argument('--record', action='store_true', help='Record new events')
    parser.add_argument('--close', action='store_true', help='Close old events')
    parser.add_argument('--report', action='store_true', help='Generate report')
    args = parser.parse_args()

    # Default: run all three
    if not (args.record or args.close or args.report):
        args.record = args.close = args.report = True

    conn = init_db()
    try:
        if args.record:
            record(conn)
        if args.close:
            close(conn)
        if args.report:
            report(conn)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
