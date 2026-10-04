#!/usr/bin/env python3
"""
gate_shadow.py — Trade Learning System P3: gate shadow outcomes.

Records every gate block from pipeline.log (standalone log-parsing — zero code
in the live trading path, freeze-safe by construction), then closes each block
24h+ later with the would-be outcome: did a trade on that token+direction
actually fire and close afterwards? What would the result have been?

Modes (default runs all three in sequence):
  --record   parse new pipeline.log lines since last offset -> gate_shadow events
  --close    close events older than 24h via signal_outcomes counterfactual join
  --report   aggregate per-gate shadow WR (feeds brain_auditor kanban proposal)

Output DB: brain/gate_shadow.db (SQLite, own file — never touches runtime DB).
Weekly report target: per gate, shadow WR by band -> relax >=55% (n>=15),
keep/tightle <=35% (CEO gate-tuner rule from execution plan Part 3/T4).

Usage: python3 scripts/gate_shadow.py [--record] [--close] [--report] [--since-hours 6]
"""
import sys
import os
import re
import json
import sqlite3
import argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, HERMES_LOG_DIR

SHADOW_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'gate_shadow.db')
PIPELINE_LOG = os.path.join(HERMES_LOG_DIR, 'pipeline.log')
OFFSET_FILE = os.path.join(HERMES_DATA, 'gate_shadow_offset.txt')
CLOSE_AFTER_HOURS = 24

# Block-line patterns seen in pipeline.log (2026-10-04 verified):
#   🚫 [GATE-NAME] TOKEN DIRECTION blocked — reason
#   🔒 [CONFLUENCE-GATE-BLOCK] TOKEN DIRECTION: reason
#   🚧 [BTC-CHOP-GATE] TOKEN DIRECTION ... BLOCKED — reason
BLOCK_RE = re.compile(
    r'(?:🚫|🔒|🚧|🌊)\s+\[([A-Za-z0-9_-]+)\]\s+([A-Za-z0-9]+)\s+(LONG|SHORT)\b'
    r'.*?(?:blocked|BLOCKED)',
    re.IGNORECASE,
)


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [gate_shadow] {msg}', flush=True)


def get_db():
    os.makedirs(os.path.dirname(SHADOW_DB), exist_ok=True)
    conn = sqlite3.connect(SHADOW_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gate TEXT, token TEXT, direction TEXT,
            blocked_at TEXT, dedup_key TEXT UNIQUE,
            closed INTEGER DEFAULT 0,
            would_trade INTEGER, would_win INTEGER, would_pnl REAL,
            outcome_signal TEXT, closed_at TEXT)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)
    """)
    return conn


def _read_offset():
    try:
        with open(OFFSET_FILE) as f:
            return int(f.read().strip() or 0)
    except (FileNotFoundError, ValueError):
        return 0


def _write_offset(pos):
    tmp = OFFSET_FILE + '.tmp'
    with open(tmp, 'w') as f:
        f.write(str(pos))
    os.replace(tmp, OFFSET_FILE)


def record(since_hours):
    """Parse pipeline.log block lines into shadow events."""
    if not os.path.exists(PIPELINE_LOG):
        log(f'pipeline.log missing: {PIPELINE_LOG}')
        return 0
    conn = get_db()
    try:
        cur = conn.cursor()
        offset = _read_offset()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        n_new = 0
        with open(PIPELINE_LOG, 'r', errors='replace') as f:
            if offset:
                f.seek(offset)
            else:
                # first run: scan only the trailing window, not the whole file
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 20_000_000))
            for line in f:
                m = BLOCK_RE.search(line)
                if not m:
                    continue
                gate, token, direction = m.group(1), m.group(2).upper(), m.group(3).upper()
                # timestamp: leading 'YYYY-MM-DD HH:MM:SS'
                ts_m = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if not ts_m:
                    continue
                blocked_at = ts_m.group(1) + '+00:00'
                try:
                    b_dt = datetime.fromisoformat(blocked_at)
                except ValueError:
                    continue
                if b_dt < cutoff:
                    continue
                # dedupe: same gate+token+direction within 10min bucket
                bucket = b_dt.strftime('%Y%m%d%H%M')[:-1]  # 10-min bucket
                dedup = f'{gate}|{token}|{direction}|{bucket}'
                try:
                    cur.execute(
                        "INSERT INTO events (gate, token, direction, blocked_at, dedup_key) "
                        "VALUES (?,?,?,?,?)", (gate, token, direction, blocked_at, dedup))
                    n_new += 1
                except sqlite3.IntegrityError:
                    pass  # dedupe hit
            new_offset = f.tell()
        conn.commit()
        _write_offset(new_offset)
        total = cur.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        log(f'record: +{n_new} events (dedup applied), total={total}, offset={new_offset}')
        return n_new
    finally:
        conn.close()


def close_events():
    """Close events >24h old: find would-be outcome via signal_outcomes join."""
    import psycopg2
    from _secrets import BRAIN_DB_DICT
    conn = get_db()
    pg = None
    try:
        cur = conn.cursor()
        # FIX 2026-10-04 (bug-hunter LOW, same class as t5_shadow HIGH): blocked_at
        # is stored 'YYYY-MM-DD HH:MM:SS+00:00' (space + tz) — isoformat 'T' cutoff
        # could close events sharing the cutoff's calendar date up to ~23h early.
        # Match blocked_at's exact format.
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=CLOSE_AFTER_HOURS)).strftime('%Y-%m-%d %H:%M:%S') + '+00:00'
        pending = cur.execute(
            "SELECT id, token, direction, blocked_at FROM events "
            "WHERE closed=0 AND blocked_at < ?", (cutoff,)).fetchall()
        if not pending:
            log('close: 0 pending events')
            return 0
        pg = psycopg2.connect(**BRAIN_DB_DICT)
        pg_cur = pg.cursor()
        n_closed = n_trade = 0
        for eid, token, direction, blocked_at in pending:
            # would-be counterfactual: first closed trade on token+direction
            # opening within 24h AFTER the block
            pg_cur.execute("""
                SELECT signal, pnl_usdt FROM trades
                WHERE token = %s AND direction = %s AND status='closed'
                  AND open_time >= %s::timestamptz
                  AND open_time < (%s::timestamptz + interval '24 hours')
                  AND pnl_usdt IS NOT NULL
                ORDER BY open_time LIMIT 1
            """, (token, direction, blocked_at, blocked_at))
            row = pg_cur.fetchone()
            if row:
                sig, pnl = row
                cur.execute(
                    "UPDATE events SET closed=1, would_trade=1, would_win=?, "
                    "would_pnl=?, outcome_signal=?, closed_at=? WHERE id=?",
                    (1 if (pnl or 0) > 0 else 0, float(pnl or 0), sig,
                     datetime.now(timezone.utc).isoformat(), eid))
                n_trade += 1
            else:
                cur.execute(
                    "UPDATE events SET closed=1, would_trade=0, closed_at=? WHERE id=?",
                    (datetime.now(timezone.utc).isoformat(), eid))
            n_closed += 1
        conn.commit()
        log(f'close: {n_closed}/{len(pending)} events closed, {n_trade} had a real follow-on trade')
        return n_closed
    finally:
        conn.close()
        if pg:
            pg.close()


def report():
    """Per-gate shadow aggregation for brain_auditor/kanban."""
    conn = get_db()
    try:
        cur = conn.cursor()
        rows = cur.execute("""
            SELECT gate,
                   COUNT(*) as blocks,
                   SUM(CASE WHEN closed=1 THEN 1 ELSE 0 END) as closed_n,
                   SUM(CASE WHEN would_trade=1 THEN 1 ELSE 0 END) as traded_n,
                   SUM(CASE WHEN would_trade=1 AND would_win=1 THEN 1 ELSE 0 END) as wins,
                   ROUND(SUM(CASE WHEN would_trade=1 THEN COALESCE(would_pnl,0) ELSE 0 END), 2) as pnl
            FROM events GROUP BY gate ORDER BY blocks DESC
        """).fetchall()
        if not rows:
            log('report: no events yet')
            return
        log('─── GATE SHADOW REPORT (would-be outcomes of blocked trades) ───')
        log(f'{"gate":28} {"blocks":>6} {"closed":>6} {"traded":>6} {"wins":>5} {"wr":>6} {"pnl":>8}')
        proposals = []
        for gate, blocks, closed_n, traded_n, wins, pnl in rows:
            wr = (wins / traded_n * 100) if traded_n else 0.0
            flag = ''
            if traded_n >= 15 and wr >= 55:
                flag = ' ← PROPOSE RELAX (shadow WR>=55, n>=15)'
                proposals.append((gate, wr, traded_n, 'relax'))
            elif traded_n >= 15 and wr <= 35:
                flag = ' ← gate working (shadow WR<=35)'
            log(f'{gate:28} {blocks:6} {closed_n:6} {traded_n:6} {wins:5} {wr:5.1f}% {pnl:+8.2f}{flag}')
        if proposals:
            log('KANBAN PROPOSALS: ' + '; '.join(f'{g} relax (wr={w:.0f}%,n={n})' for g, w, n, _ in proposals))
        else:
            log('no relax/tighten proposals this run (need n>=15 traded outcomes per gate)')
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--record', action='store_true')
    ap.add_argument('--close', action='store_true')
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--since-hours', type=int, default=6)
    args = ap.parse_args()
    run_all = not (args.record or args.close or args.report)
    if run_all or args.record:
        record(args.since_hours)
    if run_all or args.close:
        close_events()
    if run_all or args.report:
        report()
    return 0


if __name__ == '__main__':
    sys.exit(main())
