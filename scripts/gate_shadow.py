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
  --report   aggregate per-gate follow-on trade outcomes (DISTINCT-trade basis)

Output DB: brain/gate_shadow.db (SQLite, own file — never touches runtime DB).
Semantics (2026-10-26 #156): an event resolves to the first REAL Hermes trade on
the same token+direction within 24h after the block. Those trades are already in
the live book, so the PnL column is an indicator of how the blocked token
subsequently traded — NOT avoided or foregone money. Each trade is counted at
most once per gate (pre-fix: 4,182 events -> 380 trades, 11x multi-count, 23x
PnL inflation, per-gate sign flips; the auto "PROPOSE RELAX" line was an
artifact of that). Gate changes still need CEO criteria (n>=50, OOS same-sign).

Usage: python3 scripts/gate_shadow.py [--record] [--close] [--report] [--since-hours 6]
       --since-hours limits --record only; --report is all-time by design.
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
#   🚫 [GATE-NAME] TOKEN: SHORT blocked at approval — reason   (compactor form,
#     colon after token — FIX code-review b6d1b071 2026-10-22: the optional `:?`
#     makes approval-layer kills recordable; previously ZERO compactor block lines
#     matched, so the highest-volume gates never reached gate_shadow.db)
BLOCK_RE = re.compile(
    r'(?:🚫|🔒|🚧|🌊)\s+\[([A-Za-z0-9_-]+)\]\s+([A-Za-z0-9]+):?\s+(LONG|SHORT)\b'
    r'.*?(?:blocked|BLOCKED)',
    re.IGNORECASE,
)
# FIX 2026-10-04 (bug-hunter F1 HIGH): CONFLUENCE-GATE-BLOCK lines have NO
# 'blocked' word — reason follows a colon or is empty ('🔒 [CONFLUENCE-GATE-BLOCK]
# APT LONG:'). Confluence is the highest-frequency gate (~473 blocks/6h) — without
# this alternative the shadow analysis was blind to the majority of all blocks.
CONF_RE = re.compile(
    r'🔒\s+\[CONFLUENCE-GATE-BLOCK\]\s+([A-Za-z0-9]+)\s+(LONG|SHORT)\b',
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
    # FIX 2026-10-26 (brain_auditor #156): would_pnl was attributed to a
    # follow-on LIVE trade but no trade id was stored, so one real trade could
    # back many events (measured 4,182 events -> 380 trades = 11.0x) and report()
    # summed the same dollars repeatedly (23x inflation, sign flips per gate).
    try:
        conn.execute("ALTER TABLE events ADD COLUMN trade_id INTEGER")
    except sqlite3.OperationalError:
        pass  # column exists
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
            # LOG ROTATION CHECK: if offset > file size, file was rotated
            f.seek(0, 2)
            file_size = f.tell()
            if offset > file_size:
                log(f'log rotation detected (offset={offset} > size={file_size}) — resetting')
                offset = 0
            if offset:
                f.seek(offset)
            else:
                # first run: scan only the trailing window, not the whole file
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 20_000_000))
            for line in f:
                m = BLOCK_RE.search(line)
                if m:
                    gate, token, direction = m.group(1), m.group(2).upper(), m.group(3).upper()
                else:
                    # FIX 2026-10-04 (bug-hunter F1): confluence lines lack the
                    # 'blocked' word — try the dedicated alternative.
                    mc = CONF_RE.search(line)
                    if not mc:
                        continue
                    gate, token, direction = 'CONFLUENCE-GATE-BLOCK', mc.group(1).upper(), mc.group(2).upper()
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
        # BACKFILL (2026-10-26 #156): resolve trade ids for rows closed before
        # trade_id existed, otherwise report() silently drops the whole history.
        # One-shot (meta flag) so each run does not rescan unresolved history.
        cur.execute("SELECT value FROM meta WHERE key='trade_id_backfilled'")
        if cur.fetchone() is None:
            cur.execute("SELECT id, token, direction, blocked_at FROM events "
                        "WHERE closed=1 AND would_trade=1 AND trade_id IS NULL")
            for eid, token, direction, blocked_at in cur.fetchall():
                pg_cur.execute("""
                    SELECT id FROM trades
                    WHERE token = %s AND direction = %s AND status='closed'
                      AND open_time >= %s::timestamptz
                      AND open_time < (%s::timestamptz + interval '24 hours')
                      AND pnl_usdt IS NOT NULL
                    ORDER BY open_time LIMIT 1
                """, (token, direction, blocked_at, blocked_at))
                _r = pg_cur.fetchone()
                if _r:
                    cur.execute("UPDATE events SET trade_id=? WHERE id=?", (_r[0], eid))
            cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                        ('trade_id_backfilled', datetime.now(timezone.utc).isoformat()))
            conn.commit()
        for eid, token, direction, blocked_at in pending:
            # would-be outcome: first closed trade on token+direction opening
            # within 24h AFTER the block. trade_id stored so report() can count
            # each real trade once (2026-10-26 #156 — was 11x multi-counted).
            pg_cur.execute("""
                SELECT id, signal, pnl_usdt FROM trades
                WHERE token = %s AND direction = %s AND status='closed'
                  AND open_time >= %s::timestamptz
                  AND open_time < (%s::timestamptz + interval '24 hours')
                  AND pnl_usdt IS NOT NULL
                ORDER BY open_time LIMIT 1
            """, (token, direction, blocked_at, blocked_at))
            row = pg_cur.fetchone()
            if row:
                tid, sig, pnl = row
                cur.execute(
                    "UPDATE events SET closed=1, would_trade=1, would_win=?, "
                    "would_pnl=?, outcome_signal=?, closed_at=?, trade_id=? WHERE id=?",
                    (1 if (pnl or 0) > 0 else 0, float(pnl or 0), sig,
                     datetime.now(timezone.utc).isoformat(), tid, eid))
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
    """Per-gate aggregation — DISTINCT-trade basis (fix 2026-10-26, #156).

    Semantics: an event resolves to the first REAL Hermes trade on the same
    token+direction opening within 24h after the block. That trade is already in
    the live book, so its PnL here is NEITHER avoided NOR foregone money — it is
    an indicator of how the blocked token subsequently traded. Before this fix
    the report summed one event per block, so a single real trade could be added
    many times (measured 4,182 events -> 380 trades = 11.0x, 23x PnL inflation,
    per-gate sign flips). Every number below counts each referenced trade at
    most once per gate.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT gate, closed, would_trade, would_win, would_pnl, trade_id "
            "FROM events").fetchall()
        if not rows:
            log('report: no events yet')
            return
        agg, orphan = {}, 0
        for gate, closed, wt, win, pnl, tid in rows:
            a = agg.setdefault(gate, {'blocks': 0, 'closed': 0, 'trades': {}})
            a['blocks'] += 1
            a['closed'] += 1 if closed else 0
            if wt:
                if tid:
                    a['trades'][tid] = (1 if win else 0, float(pnl or 0))
                else:
                    orphan += 1
        log('─── GATE SHADOW REPORT (follow-on trade outcomes of blocked tokens) ───')
        log('  NOTE: follow-on trades are LIVE trades already in the book — PnL below is')
        log('        NOT avoided/foregone money; distinct-trade basis (each trade once).')
        if orphan:
            log(f'  {orphan} resolved events have no trade_id (excluded — run --close to backfill)')
        log(f'{"gate":28} {"blocks":>6} {"closed":>6} {"trades":>6} {"wins":>5} {"wr":>6} {"pnl":>8}')
        proposals = []
        for gate, a in sorted(agg.items(), key=lambda kv: -kv[1]['blocks']):
            trades = a['trades']
            n = len(trades)
            wins = sum(w for w, _ in trades.values())
            pnl = round(sum(p for _, p in trades.values()), 2)
            wr = (wins / n * 100) if n else None
            wr_s = f'{wr:5.1f}%' if wr is not None else '  n/a '
            flag = ''
            if n >= 15:
                # token-state watch only: blocked tokens' NEXT real trade won
                # >=55% and netted positive. Not a counterfactual — CEO gate
                # criteria (n>=50, OOS same-sign) still apply before any change.
                if wr is not None and wr >= 55 and pnl > 0:
                    flag = ' ← WATCH-RELAX (follow-on WR>=55, distinct n>=15)'
                    proposals.append((gate, wr, n))
                elif pnl < 0:
                    flag = ' ← blocked tokens went on to LOSE'
                elif wr is not None and wr <= 35:
                    flag = ' ← blocked tokens went on to LOSE (WR<=35)'
            log(f'{gate:28} {a["blocks"]:6d} {a["closed"]:6d} {n:6d} {wins:5d} {wr_s} {pnl:+8.2f}{flag}')
        if proposals:
            log('KANBAN WATCH (not a proposal — see semantics above): '
                + '; '.join(f'{g} follow-on wr={w:.0f}%,n={n}' for g, w, n in proposals))
        else:
            log('no WATCH-RELAX candidates this run (need distinct n>=15 follow-on trades per gate)')
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
