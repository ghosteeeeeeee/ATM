#!/usr/bin/env python3
"""temporal_confluence_shadow.py — Counterfactual tracking for temporal confluence.

Standalone: parses pipeline.log (zero code in trading path, freeze-safe).
Records every shadow-blocked signal, closes 24h later with would-be outcome.

Modes:
  --record   parse new log lines since last offset -> events
  --close    close events >24h old via forward-return join
  --report   aggregate per-gate shadow WR (feeds CEO decision)

Output DB: brain/temporal_confluence_shadow.db (SQLite, own file).

Usage: python3 scripts/temporal_confluence_shadow.py [--record] [--close] [--report] [--since-hours 6]

Spec: plans/temporal-confluence-spec.md
Pattern: automatic-implementation (shadow→enforce rollout)
"""
import sys, os, re, sqlite3, argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

# ── Paths ──────────────────────────────────────────────────────────────────
SHADOW_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'temporal_confluence_shadow.db')
PIPELINE_LOG = os.path.join(os.path.dirname(HERMES_DATA), 'logs', 'pipeline.log')
OFFSET_FILE = os.path.join(HERMES_DATA, 'temporal_confluence_shadow_offset.txt')
CLOSE_AFTER_HOURS = 24

# ── Log parsing ────────────────────────────────────────────────────────────
# Match the shadow log line from signal_compactor.py
# Format: 📊 [TEMPORAL-CONFLUENCE-SHADOW] {token} {direction} — would bypass ({count} fires in {window}min), flag ON, shadow mode
BLOCK_RE = re.compile(
    r'TEMPORAL-CONFLUENCE-SHADOW\]\s+(\w+)\s+(LONG|SHORT)\s+—\s+would bypass\s+\((\d+) fires in (\d+)min\)',
)


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [tc_shadow] {msg}', flush=True)


def get_db():
    os.makedirs(os.path.dirname(SHADOW_DB), exist_ok=True)
    conn = sqlite3.connect(SHADOW_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT, direction TEXT, fire_count INTEGER, window_min INTEGER,
            blocked_at TEXT, dedup_key TEXT UNIQUE,
            closed INTEGER DEFAULT 0,
            would_trade INTEGER, would_win INTEGER, would_pnl REAL,
            closed_at TEXT)
    """)
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
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
    """Parse pipeline.log shadow lines into events."""
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
            file_size = f.seek(0, 2)
            # LOG ROTATION CHECK
            if offset > file_size:
                log(f'log rotation detected (offset={offset} > size={file_size}) — resetting')
                offset = 0
            if offset:
                f.seek(offset)
            else:
                f.seek(max(0, file_size - 20_000_000))
            for line in f:
                m = BLOCK_RE.search(line)
                if not m:
                    continue
                token, direction, fire_count, window_min = (
                    m.group(1).upper(), m.group(2).upper(),
                    int(m.group(3)), int(m.group(4)))
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
                # DEDUP: same token+direction within 10-min bucket
                bucket = b_dt.strftime('%Y%m%d%H%M')[:-1]
                dedup = f'tc|{token}|{direction}|{bucket}'
                try:
                    cur.execute(
                        "INSERT INTO events (token, direction, fire_count, window_min, blocked_at, dedup_key) "
                        "VALUES (?,?,?,?,?,?)",
                        (token, direction, fire_count, window_min, blocked_at, dedup))
                    n_new += 1
                except sqlite3.IntegrityError:
                    pass  # dedup hit
            new_offset = f.tell()
        conn.commit()
        _write_offset(new_offset)
        total = cur.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        log(f'record: +{n_new} events, total={total}, offset={new_offset}')
        return n_new
    finally:
        conn.close()


def close_events():
    """Close events >24h old: find would-be outcome via forward returns from candles."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=CLOSE_AFTER_HOURS)).strftime(
            '%Y-%m-%d %H:%M:%S') + '+00:00'
        pending = cur.execute(
            "SELECT id, token, direction, blocked_at FROM events "
            "WHERE closed=0 AND blocked_at < ?", (cutoff,)).fetchall()
        if not pending:
            log('close: 0 pending events')
            return 0

        # Load candle DB for forward returns
        from paths import CANDLES_DB
        n_closed = 0
        for eid, token, direction, blocked_at in pending:
            try:
                # Parse blocked_at to epoch
                b_dt = datetime.fromisoformat(blocked_at)
                entry_ts = int(b_dt.timestamp())
                # Get price at block time and 30min later
                cconn = sqlite3.connect(CANDLES_DB, timeout=5)
                try:
                    ccur = cconn.cursor()
                    # Price at block time (nearest 1m candle)
                    ccur.execute(
                        "SELECT close FROM candles_1m WHERE token=? AND ts<=? ORDER BY ts DESC LIMIT 1",
                        (token, entry_ts))
                    entry_row = ccur.fetchone()
                    # Price 30min later
                    ccur.execute(
                        "SELECT close FROM candles_1m WHERE token=? AND ts>? ORDER BY ts ASC LIMIT 1",
                        (token, entry_ts + 1800))
                    exit_row = ccur.fetchone()
                finally:
                    cconn.close()

                if entry_row and exit_row:
                    entry_price = entry_row[0]
                    exit_price = exit_row[0]
                    if entry_price and entry_price > 0 and exit_price:
                        if direction == 'LONG':
                            pnl_pct = (exit_price - entry_price) / entry_price * 100
                        else:
                            pnl_pct = (entry_price - exit_price) / entry_price * 100
                        would_win = 1 if pnl_pct > 0 else 0
                        cur.execute(
                            "UPDATE events SET closed=1, would_trade=1, would_win=?, "
                            "would_pnl=?, closed_at=? WHERE id=?",
                            (would_win, round(pnl_pct, 4),
                             datetime.now(timezone.utc).isoformat(), eid))
                        n_closed += 1
                    else:
                        cur.execute(
                            "UPDATE events SET closed=1, closed_at=? WHERE id=?",
                            (datetime.now(timezone.utc).isoformat(), eid))
                        n_closed += 1
                else:
                    # No candle data — close without outcome
                    cur.execute(
                        "UPDATE events SET closed=1, closed_at=? WHERE id=?",
                        (datetime.now(timezone.utc).isoformat(), eid))
                    n_closed += 1
            except Exception as e:
                log(f'close error for event {eid} ({token} {direction}): {e}')
        conn.commit()
        log(f'close: {n_closed}/{len(pending)} events closed')
        return n_closed
    finally:
        conn.close()


def report():
    """Per-gate shadow aggregation for CEO decision."""
    conn = get_db()
    try:
        cur = conn.cursor()
        rows = cur.execute("""
            SELECT COUNT(*) as blocks,
                   SUM(CASE WHEN closed=1 THEN 1 ELSE 0 END) as closed_n,
                   SUM(CASE WHEN would_trade=1 THEN 1 ELSE 0 END) as traded_n,
                   SUM(CASE WHEN would_trade=1 AND would_win=1 THEN 1 ELSE 0 END) as wins,
                   ROUND(SUM(CASE WHEN would_trade=1 THEN COALESCE(would_pnl,0) ELSE 0 END), 4) as pnl,
                   ROUND(AVG(CASE WHEN would_trade=1 THEN would_pnl END), 4) as avg_pnl
            FROM events
        """).fetchone()
        blocks, closed_n, traded_n, wins, pnl, avg_pnl = rows
        log('─── TEMPORAL CONFLUENCE SHADOW REPORT ───')
        log(f'blocks={blocks} closed={closed_n} traded={traded_n}')
        if traded_n:
            wr = wins / traded_n * 100
            log(f'wins={wins} wr={wr:.1f}% pnl={pnl:+.4f}% avg={avg_pnl:+.4f}%')
            if traded_n >= 15:
                if wr >= 55 and pnl > 0:
                    log(f'← PROPOSE ENFORCE (WR>=55, n>=15, net positive)')
                elif pnl < 0:
                    log(f'← GATE WORKING (bypassed trades net negative — keep shadow)')
                elif wr <= 35:
                    log(f'← GATE WORKING (shadow WR<=35)')
                else:
                    log(f'← MONITOR (inconclusive, extend shadow)')
            else:
                log(f'← INSUFFICIENT DATA (n={traded_n} < 15)')
        else:
            log('no would-be trades recorded yet')

        # Per-direction breakdown
        for d in ['LONG', 'SHORT']:
            r = cur.execute("""
                SELECT COUNT(*), SUM(CASE WHEN would_win=1 THEN 1 ELSE 0 END),
                       ROUND(SUM(COALESCE(would_pnl,0)),4)
                FROM events WHERE direction=? AND would_trade=1
            """, (d,)).fetchone()
            if r[0]:
                dwr = (r[1] or 0) / r[0] * 100
                log(f'  {d}: {r[0]} trades, wr={dwr:.0f}%, pnl={r[2]:+.4f}%')
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
