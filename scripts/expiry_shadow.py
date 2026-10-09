#!/usr/bin/env python3
"""expiry_shadow.py — D3 confluence-expiry counterfactual (CEO GO 2026-10-09 00:45).

The confluence-by-expiry is the single largest filter in the system: 25,204
signals per 6d EXPIRED waiting <5min for a co-signal, averaging 80.5 conf —
with ZERO counterfactual instrumentation. This records every expired/skipped
signal before the hourly purge deletes it (<2h rows), then closes each with
direction-aware forward returns from candles.db.

Standalone observability — zero code in the live trading path (freeze-safe,
same pattern as gate_shadow.py). Does NOT touch CONFLUENCE_REQUIRED.

Modes (default runs all in sequence):
  --record   snapshot EXPIRED/SKIPPED rows from signals_hermes_runtime.db
             (newer than last recorded id; purge removes them after 2h)
  --close    close events >4.5h old: fwd +30m/+1h/+4h, MFE/MAE(4h),
             market-neutral excess (direction-signed, same method as
             gate_counterfactual_audit_2026-10-08)
  --report   aggregate by confidence band / source / signal_type — the
             money question: do conf>=80 single-source signals have
             positive forward edge?

Output DB: brain/expiry_shadow.db (own file — never touches runtime DB).
"""
import sys
import os
import sqlite3
import argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

SHADOW_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'expiry_shadow.db')
RUNTIME_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
CLOSE_AFTER_HOURS = 4.5  # need 4h forward + slack


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [expiry_shadow] {msg}', flush=True)


def get_db():
    os.makedirs(os.path.dirname(SHADOW_DB), exist_ok=True)
    conn = sqlite3.connect(SHADOW_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER UNIQUE,
            token TEXT, direction TEXT, signal_type TEXT, source TEXT,
            confidence REAL, decision TEXT, decision_reason TEXT,
            created_at TEXT, recorded_at TEXT,
            closed INTEGER DEFAULT 0,
            fwd_30m REAL, fwd_1h REAL, fwd_4h REAL,
            excess_30m REAL, excess_1h REAL, excess_4h REAL,
            mfe_4h REAL, mae_4h REAL, closed_at TEXT)
    """)
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    return conn


def record():
    """Snapshot EXPIRED/SKIPPED signals not yet recorded. Purge deletes rows
    older than 2h hourly — this timer runs every 30min, so nothing is lost."""
    conn = get_db()
    try:
        cur = conn.cursor()
        last = cur.execute("SELECT MAX(signal_id) FROM events").fetchone()[0] or 0
        rt = sqlite3.connect(RUNTIME_DB, timeout=10)
        try:
            rows = rt.execute("""
                SELECT id, token, direction, signal_type, source, confidence,
                       decision, COALESCE(decision_reason,''), created_at
                FROM signals
                WHERE id > ? AND decision IN ('EXPIRED','SKIPPED')
                ORDER BY id
            """, (last,)).fetchall()
        finally:
            rt.close()
        n = 0
        now = datetime.now(timezone.utc).isoformat()
        for sid, tok, d, st, src, conf, dec, reason, created in rows:
            try:
                cur.execute(
                    "INSERT INTO events (signal_id, token, direction, signal_type, source,"
                    " confidence, decision, decision_reason, created_at, recorded_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (sid, tok, d, st, src, conf, dec, reason, created, now))
                n += 1
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        log(f'record: +{n} expired/skipped signals (last_id={last})')
        return n
    finally:
        conn.close()


# ── forward-return engine (same rules as gate_counterfactual_audit) ──────────
_candles_cache = {}


def _load_candles(token):
    if token in _candles_cache:
        return _candles_cache[token]
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    try:
        rows = conn.execute(
            "SELECT ts, open, close, high, low FROM candles_5m"
            " WHERE token=? AND is_closed=1 ORDER BY ts", (token.upper(),)).fetchall()
    finally:
        conn.close()
    _candles_cache[token] = rows
    return rows


def _market_rows_all():
    """Cross-sectional close series for baseline — lazily all tokens."""
    if '_all' in _candles_cache:
        return _candles_cache['_all']
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    try:
        rows = conn.execute(
            "SELECT token, ts, open, close FROM candles_5m WHERE is_closed=1"
            " ORDER BY ts").fetchall()
    finally:
        conn.close()
    by_tok = {}
    for tok, ts, o, c in rows:
        by_tok.setdefault(tok, []).append((ts, o, c))
    _candles_cache['_all'] = by_tok
    return by_tok


def _fwd_metrics(rows, entry_ts, direction):
    """Entry = OPEN of first 5m candle with ts >= entry_ts (no lookahead)."""
    lo, hi = 0, len(rows)
    while lo < hi:
        mid = (lo + hi) // 2
        if rows[mid][0] < entry_ts:
            lo = mid + 1
        else:
            hi = mid
    i = lo
    if i + 48 >= len(rows):
        return None
    _, o, c, h, l = rows[i]
    sgn = 1 if direction == 'LONG' else -1
    res = {
        'fwd_30m': sgn * (rows[i + 6][2] / o - 1.0) * 100.0,
        'fwd_1h': sgn * (rows[i + 12][2] / o - 1.0) * 100.0,
        'fwd_4h': sgn * (rows[i + 48][2] / o - 1.0) * 100.0,
    }
    highs = [r[3] for r in rows[i:i + 49]]
    lows = [r[4] for r in rows[i:i + 49]]
    if direction == 'LONG':
        res['mfe_4h'] = (max(highs) / o - 1.0) * 100.0
        res['mae_4h'] = (min(lows) / o - 1.0) * 100.0
    else:
        res['mfe_4h'] = (1.0 - min(lows) / o) * 100.0
        res['mae_4h'] = (1.0 - max(highs) / o) * 100.0
    return res


def _market_mean(entry_ts, horizon_n):
    """Cross-sectional mean UNSIGNED fwd return at entry candle (baseline)."""
    bucket = (int(entry_ts) + 299) // 300 * 300
    rets = []
    for tok, trows in _market_rows_all().items():
        lo, hi = 0, len(trows)
        while lo < hi:
            mid = (lo + hi) // 2
            if trows[mid][0] < bucket:
                lo = mid + 1
            else:
                hi = mid
        i = lo
        if i + horizon_n >= len(trows):
            continue
        rets.append((trows[i + horizon_n][2] / trows[i][1] - 1.0) * 100.0)
    if len(rets) < 20:
        return None
    return sum(rets) / len(rets)


def close_events():
    conn = get_db()
    try:
        cur = conn.cursor()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=CLOSE_AFTER_HOURS))
        pending = cur.execute(
            "SELECT id, token, direction, created_at FROM events"
            " WHERE closed=0 AND created_at < ?", (cutoff.strftime('%Y-%m-%d %H:%M:%S'),)
        ).fetchall()
        if not pending:
            log('close: 0 pending')
            return 0
        n_ok = 0
        for eid, tok, d, created in pending:
            try:
                import calendar
                entry_ts = calendar.timegm(datetime.strptime(created, '%Y-%m-%d %H:%M:%S').timetuple())
            except (ValueError, TypeError):
                continue
            rows = _load_candles(tok)
            if not rows:
                # no candles for token — close as unclosed-with-note (not a loss)
                cur.execute("UPDATE events SET closed=1, closed_at=? WHERE id=?",
                            (datetime.now(timezone.utc).isoformat(), eid))
                continue
            fm = _fwd_metrics(rows, entry_ts, d)
            if fm is None:
                cur.execute("UPDATE events SET closed=1, closed_at=? WHERE id=?",
                            (datetime.now(timezone.utc).isoformat(), eid))
                continue
            mb30 = _market_mean(entry_ts, 6)
            mb1 = _market_mean(entry_ts, 12)
            mb4 = _market_mean(entry_ts, 48)
            sgn = 1 if d == 'LONG' else -1
            cur.execute(
                "UPDATE events SET closed=1, fwd_30m=?, fwd_1h=?, fwd_4h=?,"
                " excess_30m=?, excess_1h=?, excess_4h=?, mfe_4h=?, mae_4h=?, closed_at=?"
                " WHERE id=?",
                (fm['fwd_30m'], fm['fwd_1h'], fm['fwd_4h'],
                 (fm['fwd_30m'] - (mb30 if d == 'LONG' else -mb30)) if mb30 is not None else None,
                 (fm['fwd_1h'] - (mb1 if d == 'LONG' else -mb1)) if mb1 is not None else None,
                 (fm['fwd_4h'] - (mb4 if d == 'LONG' else -mb4)) if mb4 is not None else None,
                 fm['mfe_4h'], fm['mae_4h'],
                 datetime.now(timezone.utc).isoformat(), eid))
            n_ok += 1
        conn.commit()
        log(f'close: {len(pending)} pending, {n_ok} with forward data')
        return n_ok
    finally:
        conn.close()


def report():
    conn = get_db()
    try:
        cur = conn.cursor()
        log('─── EXPIRY SHADOW REPORT (counterfactual of confluence-expired signals) ───')
        rows = cur.execute("""
            SELECT CASE WHEN confidence < 60 THEN 'a <60'
                        WHEN confidence < 70 THEN 'b 60-69'
                        WHEN confidence < 80 THEN 'c 70-79'
                        WHEN confidence < 90 THEN 'd 80-89'
                        ELSE 'e 90+' END band,
                   COUNT(*),
                   SUM(CASE WHEN closed=1 AND fwd_4h IS NOT NULL THEN 1 ELSE 0 END),
                   ROUND(AVG(excess_4h), 3),
                   SUM(CASE WHEN excess_4h > 0 THEN 1 ELSE 0 END),
                   ROUND(AVG(mfe_4h), 2)
            FROM events GROUP BY 1 ORDER BY 1
        """).fetchall()
        log(f'{"conf band":10} {"n":>6} {"closed":>6} {"ex4h":>8} {"wr":>6} {"mfe":>6}')
        for band, n, cl, ex4h, wins, mfe in rows:
            wr = f'{wins/cl*100:.0f}%' if cl else ' n/a'
            log(f'{band:10} {n:6} {cl:6} {ex4h if ex4h is not None else "n/a":>8} {wr:>6} {mfe if mfe else "n/a":>6}')
        rows2 = cur.execute("""
            SELECT decision_reason, COUNT(*),
                   ROUND(AVG(excess_4h),3),
                   SUM(CASE WHEN closed=1 AND fwd_4h IS NOT NULL THEN 1 ELSE 0 END)
            FROM events GROUP BY 1 ORDER BY 2 DESC
        """).fetchall()
        log('─── by reason ───')
        for reason, n, ex4h, cl in rows2:
            log(f'  {reason or "(none/staleness=0)":32} n={n:5} closed={cl:5} ex4h={ex4h if ex4h is not None else "n/a"}')
        tot = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        pend = cur.execute("SELECT COUNT(*) FROM events WHERE closed=0").fetchone()[0]
        log(f'total events={tot} pending={pend}')
        log('NOTE: excess = direction-signed fwd − market mean (same engine as gate audit).')
        log('The money question: conf>=80 bands with positive ex4h = confluence is costing edge.')
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--record', action='store_true')
    ap.add_argument('--close', action='store_true')
    ap.add_argument('--report', action='store_true')
    args = ap.parse_args()
    run_all = not (args.record or args.close or args.report)
    if run_all or args.record:
        record()
    if run_all or args.close:
        close_events()
    if run_all or args.report:
        report()
    return 0


if __name__ == '__main__':
    sys.exit(main())
