#!/usr/bin/env python3
"""
t5_shadow.py — Trade Learning System P4: T5 decision-time trainer, SHADOW MODE.

For every new signal, looks up its context cell (source/signal_type x direction x
current vol regime) in the T2 cell store, applies the selection rule, and logs
what the learned layer WOULD do — without blocking anything. After closes, joins
would-be outcomes from the brain DB so the 7d shadow-WR vs live-WR comparison
(the P4 gate for P5) can be published.

Decision rule v1 (execution plan T5, simplified for shadow):
  admitted cell (n>=15) & wr_blended >= 0.60  -> WOULD_TRADE  (positive edge)
  admitted cell & wr_blended < 0.50           -> WOULD_SKIP   (negative edge)
  otherwise                                  -> UNCERTAIN    (backoff; logged, not counted)

Regime for the lookup: current token ATR classified via volatility_gate_v2
(read-only candle queries — freeze-safe, zero code in the trading path).

Output DB: brain/t5_shadow.db (SQLite, own file).

Usage: python3 scripts/t5_shadow.py [--decide] [--close] [--report] [--since-min 70]
"""
import sys
import os
import json
import sqlite3
import argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

SHADOW_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 't5_shadow.db')
RUNTIME_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
CELL_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'cell_stats.db')
OFFSET_FILE = os.path.join(HERMES_DATA, 't5_shadow_offset.txt')

TRADE_WINDOW_MIN = 60   # would-be trade join window after signal creation


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [t5_shadow] {msg}', flush=True)


def get_db():
    os.makedirs(os.path.dirname(SHADOW_DB), exist_ok=True)
    conn = sqlite3.connect(SHADOW_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_rowid INTEGER UNIQUE, token TEXT, direction TEXT,
            source TEXT, signal_type TEXT, regime TEXT,
            lookup_key TEXT, cell_n INTEGER, cell_wr REAL, cell_admission TEXT,
            shadow_decision TEXT, shadow_reason TEXT,
            live_decision TEXT, live_executed INTEGER,
            created_at TEXT, closed INTEGER DEFAULT 0,
            would_win INTEGER, would_pnl REAL, closed_at TEXT)
    """)
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
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


def _current_regime(token):
    """Classify token's current vol regime (read-only)."""
    try:
        from volatility_gate_v2 import get_atr_pct, classify_volatility
        atr = get_atr_pct(token)
        if atr is None:
            return 'UNKNOWN'
        return classify_volatility(atr)
    except Exception:
        return 'UNKNOWN'


def _lookup_cell(cell_cur, key_signal, direction, regime):
    """Cell lookup with fallbacks (shadow mode wants signal, not perfection).
    Tries: exact (signal x dir x regime) -> substring combo match (brain DB keys
    are combo strings like 'accel-300-,rs-r79', source is a component) ->
    any row for signal x dir (regime-agnostic, uses signal-level stats).
    Regime alias: live gate vocabulary FLAT ~ store NEUTRAL (brain DB regime col).
    Returns (row_tuple, which_key) or (None, None)."""
    if not key_signal:
        return None, None
    regimes = [regime]
    if regime == 'FLAT':
        regimes.append('NEUTRAL')
    elif regime == 'NEUTRAL':
        regimes.append('FLAT')
    # 1. exact match, preferred regime then alias
    for reg in regimes:
        row = cell_cur.execute(
            "SELECT n, wr_blended, admission FROM cells "
            "WHERE signal=? AND direction=? AND regime=?",
            (key_signal, direction, reg)).fetchone()
        if row:
            return row, f'exact:{key_signal}|{reg}'
    # 2. substring: store key contains source as component (combo keys)
    for reg in regimes:
        row = cell_cur.execute(
            "SELECT n, wr_blended, admission, signal FROM cells "
            "WHERE direction=? AND regime=? AND (? = '' OR instr(signal, ?) > 0) "
            "ORDER BY n DESC LIMIT 1",
            (direction, reg, key_signal, key_signal)).fetchone()
        if row:
            return row[:3], f'substr:{row[3][:40]}|{reg}'
    # 3. signal_type-keyed outcome cells (cells_st — covers live families like
    #    support_resistance/hmacd_mtf that trades.signal source-form keys miss)
    for reg in regimes:
        row = cell_cur.execute(
            "SELECT n, wr_blended, admission FROM cells_st "
            "WHERE signal=? AND direction=? AND regime=?",
            (key_signal, direction, reg)).fetchone()
        if row:
            return row, f'cells_st:{key_signal}|{reg}'
    row = cell_cur.execute(
        "SELECT n, wr_blended, admission FROM cells_st "
        "WHERE direction=? AND instr(signal, ?) > 0 ORDER BY n DESC LIMIT 1",
        (direction, key_signal)).fetchone()
    if row:
        return row, f'cells_st_sub:{key_signal}'
    # 4. regime-agnostic signal-level fallback (uses stored signal_n/signal_wr)
    row = cell_cur.execute(
        "SELECT signal_n, signal_wr, 'signal' FROM cells "
        "WHERE direction=? AND (? = '' OR instr(signal, ?) > 0) "
        "AND signal_n >= 10 ORDER BY signal_n DESC LIMIT 1",
        (direction, key_signal, key_signal)).fetchone()
    if row:
        return row, f'siglevel:{key_signal}'
    return None, None


def decide(since_min):
    """Process new signals -> shadow decisions."""
    if not os.path.exists(RUNTIME_DB):
        log(f'runtime DB missing: {RUNTIME_DB}')
        return 0
    if not os.path.exists(CELL_DB):
        log(f'cell store missing: {CELL_DB} — run cell_stats.py first')
        return 0
    conn = get_db()
    sig_conn = sqlite3.connect(RUNTIME_DB)
    cell_conn = sqlite3.connect(CELL_DB)
    try:
        cur = conn.cursor()
        sig_cur = sig_conn.cursor()
        cell_cur = cell_conn.cursor()
        # NOTE: signals.created_at is 'YYYY-MM-DD HH:MM:SS' (space, no tz) — cutoff
        # must match that format or string comparison silently returns 0 rows.
        since = (datetime.now(timezone.utc) - timedelta(minutes=since_min)).strftime('%Y-%m-%d %H:%M:%S')
        rows = sig_cur.execute("""
            SELECT rowid, token, direction, source, signal_type, confidence,
                   rsi_14, decision, executed, created_at
            FROM signals WHERE created_at > ?
        """, (since,)).fetchall()
        n_new = 0
        for (rowid, token, direction, source, signal_type, conf, rsi,
             live_decision, live_executed, created_at) in rows:
            direction = (direction or '').upper()
            regime = _current_regime(token)
            cell_row, lookup_key = _lookup_cell(cell_cur, source, direction, regime)
            if cell_row is None and signal_type:
                cell_row, lookup_key = _lookup_cell(cell_cur, signal_type, direction, regime)
            if cell_row:
                n, wr_b, admission = cell_row
                if admission == 'cell' and wr_b >= 0.60:
                    decision, reason = 'WOULD_TRADE', f'admitted cell wr_blended={wr_b:.2f} n={n}'
                elif admission == 'cell' and wr_b < 0.50:
                    decision, reason = 'WOULD_SKIP', f'admitted cell negative edge wr_blended={wr_b:.2f} n={n}'
                else:
                    decision, reason = 'UNCERTAIN', f'admission={admission} n={n} wr_b={wr_b:.2f}'
            else:
                n, wr_b, admission = 0, None, 'no_cell'
                decision, reason = 'UNCERTAIN', 'no cell in store (signal unseen in 90d window)'
            try:
                cur.execute("""
                    INSERT INTO decisions (signal_rowid, token, direction, source, signal_type,
                        regime, lookup_key, cell_n, cell_wr, cell_admission, shadow_decision,
                        shadow_reason, live_decision, live_executed, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (rowid, token, direction, source, signal_type, regime, lookup_key,
                      n, wr_b, admission, decision, reason, live_decision,
                      int(live_executed or 0), created_at))
                n_new += 1
            except sqlite3.IntegrityError:
                pass  # already processed
        conn.commit()
        total = cur.execute('SELECT COUNT(*) FROM decisions').fetchone()[0]
        dist = cur.execute(
            "SELECT shadow_decision, COUNT(*) FROM decisions GROUP BY 1").fetchall()
        log(f'decide: +{n_new} signals processed, total={total}, dist={dict(dist)}')
        return n_new
    finally:
        conn.close()
        sig_conn.close()
        cell_conn.close()


def close_events():
    """Join closed trades to shadow decisions (token+direction, within window)."""
    import psycopg2
    from _secrets import BRAIN_DB_DICT
    conn = get_db()
    pg = None
    try:
        cur = conn.cursor()
        pending = cur.execute(
            "SELECT id, token, direction, created_at FROM decisions WHERE closed=0 "
            "AND created_at < ?",
            # FIX 2026-10-04 (bug-hunter HIGH): decisions.created_at is SPACE-format
            # ('YYYY-MM-DD HH:MM:SS', from signals.created_at) — isoformat 'T' cutoff
            # compares space(0x20) < 'T'(0x54) so EVERY same-day row matched: the
            # 65-min age gate was bypassed and all decisions closed premature with
            # NULL outcomes, destroying the P4 gate metric. Same class as the
            # decide-mode fix; mirror its strftime format exactly.
            ((datetime.now(timezone.utc) - timedelta(minutes=TRADE_WINDOW_MIN + 5)).strftime('%Y-%m-%d %H:%M:%S'),)
        ).fetchall()
        if not pending:
            log('close: 0 pending decisions')
            return 0
        pg = psycopg2.connect(**BRAIN_DB_DICT)
        pg_cur = pg.cursor()
        n_closed = n_trade = 0
        for did, token, direction, created_at in pending:
            pg_cur.execute("""
                SELECT pnl_usdt FROM trades
                WHERE token=%s AND direction=%s AND status='closed'
                  AND open_time >= %s::timestamptz
                  AND open_time < (%s::timestamptz + interval '%s minutes')
                  AND pnl_usdt IS NOT NULL
                ORDER BY open_time LIMIT 1
            """, (token, direction, created_at, created_at, TRADE_WINDOW_MIN))
            row = pg_cur.fetchone()
            if row:
                pnl = float(row[0] or 0)
                cur.execute(
                    "UPDATE decisions SET closed=1, would_win=?, would_pnl=?, closed_at=? WHERE id=?",
                    (1 if pnl > 0 else 0, pnl, datetime.now(timezone.utc).isoformat(), did))
                n_trade += 1
            else:
                cur.execute(
                    "UPDATE decisions SET closed=1, closed_at=? WHERE id=?",
                    (datetime.now(timezone.utc).isoformat(), did))
            n_closed += 1
        conn.commit()
        log(f'close: {n_closed}/{len(pending)} decisions closed, {n_trade} had follow-on trades')
        return n_closed
    finally:
        conn.close()
        if pg:
            pg.close()


def report():
    """Shadow WR vs live-executed WR (the P4 gate metric)."""
    conn = get_db()
    try:
        cur = conn.cursor()
        rows = cur.execute("""
            SELECT shadow_decision,
                   COUNT(*) as n,
                   SUM(CASE WHEN closed=1 THEN 1 ELSE 0 END) as closed_n,
                   SUM(CASE WHEN would_win=1 THEN 1 ELSE 0 END) as wins,
                   ROUND(SUM(COALESCE(would_pnl,0)), 2) as pnl,
                   SUM(live_executed) as live_taken
            FROM decisions GROUP BY 1 ORDER BY n DESC
        """).fetchall()
        if not rows:
            log('report: no decisions yet')
            return
        log('─── T5 SHADOW REPORT (would-trade vs live) ───')
        log(f'{"decision":14} {"n":>6} {"closed":>6} {"wins":>5} {"wr":>6} {"pnl":>8} {"live_taken":>10}')
        for dec, n, closed_n, wins, pnl, live_taken in rows:
            wr = (wins / closed_n * 100) if closed_n else 0.0
            log(f'{dec:14} {n:6} {closed_n:6} {wins:5} {wr:5.1f}% {pnl:+8.2f} {live_taken:10}')
        # the gate metric: WOULD_TRADE cohort outcome
        wt = cur.execute("""
            SELECT COUNT(*), SUM(CASE WHEN closed=1 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN would_win=1 THEN 1 ELSE 0 END), ROUND(SUM(COALESCE(would_pnl,0)),2)
            FROM decisions WHERE shadow_decision='WOULD_TRADE'
        """).fetchone()
        if wt and wt[1] and wt[1] >= 5:
            log(f"P4 GATE: WOULD_TRADE cohort closed={wt[1]} wr={wt[2]/wt[1]*100:.1f}% pnl={wt[3]:+.2f} "
                f"(P5 requires 7d of this comparison + freeze lift)")
        else:
            log(f'P4 GATE: WOULD_TRADE cohort closed={wt[1] if wt else 0} — accumulating (need 7d series)')
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--decide', action='store_true')
    ap.add_argument('--close', action='store_true')
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--since-min', type=int, default=70)
    args = ap.parse_args()
    run_all = not (args.decide or args.close or args.report)
    if run_all or args.decide:
        decide(args.since_min)
    if run_all or args.close:
        close_events()
    if run_all or args.report:
        report()
    return 0


if __name__ == '__main__':
    sys.exit(main())
