#!/usr/bin/env python3
"""
gate_shadow.py — Trade Learning System P3: gate shadow outcomes.

Records every gate block from pipeline.log (standalone log-parsing — zero code
in the live trading path, freeze-safe by construction), then closes each block
24h+ later with the would-be outcome: did a trade on that token+direction
actually fire and close afterwards? What would the result have been?

Modes (default runs all four in sequence):
  --record   parse new pipeline.log lines since last offset -> gate_shadow events
  --close    close events older than 24h via signal_outcomes counterfactual join
  --fwd      backfill expiry-style fwd-return join (fwd_4h) from candles_5m
  --report   fwd-basis report FIRST (net pp + $-eq + per-gate), trade-join second

Output DB: brain/gate_shadow.db (SQLite, own file — never touches runtime DB).

FWD JOIN (deep-dive KEEP-label 2026-10-31, registry gate-shadow): the trade-join
above joins only 13-14% of events (few blocked tokens fire a real trade), so
--report now LEADS with an expiry-style forward-return join (same engine/rules
as expiry_shadow._fwd_metrics): entry = OPEN of the first closed 5m candle with
ts >= block time, outcome = fwd 4h return SIGNED IN THE BLOCKED DIRECTION's
would-be direction (sgn=+1 LONG, -1 SHORT) — negative fwd = the blocked
direction would have LOST = gate protective. Coverage ~100% of events with a
+4h candle horizon. $-eq converts pp at the LIVE 30d avg PG notional
(amount_usdt, read at runtime — never hardcoded). The trade-join columns stay
for continuity but are SECONDARY: those trades are already in the live book, so
their PnL is an indicator of how the blocked token subsequently traded — NOT
avoided or foregone money. Each trade counted at most once per gate (#156:
pre-fix 4,182 events -> 380 trades, 11x multi-count, 23x PnL inflation).
Gate changes still need CEO criteria (n>=50, OOS same-sign).

Usage: python3 scripts/gate_shadow.py [--record] [--close] [--fwd] [--report] [--since-hours 6]
       --since-hours limits --record only; --report/--fwd are all-time by design.
"""
import sys
import os
import re
import json
import calendar
import sqlite3
import argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, HERMES_LOG_DIR

SHADOW_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'gate_shadow.db')
CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
PIPELINE_LOG = os.path.join(HERMES_LOG_DIR, 'pipeline.log')
OFFSET_FILE = os.path.join(HERMES_DATA, 'gate_shadow_offset.txt')
CLOSE_AFTER_HOURS = 24
FWD_AFTER_HOURS = 4.5  # need +4h forward horizon + slack (same as expiry_shadow)
NOTIONAL_WINDOW_DAYS = 30  # trailing window for the live avg-notional $-eq basis

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
    # FWD JOIN (2026-10-31 deep-dive KEEP-label): fwd_4h = expiry-style
    # direction-signed fwd return (see close_fwd); fwd_done marks the attempt so
    # tokens without candle history are skipped instead of rescanned hourly.
    for col in ('fwd_4h REAL', 'fwd_done INTEGER'):
        try:
            conn.execute(f"ALTER TABLE events ADD COLUMN {col}")
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


# ── forward-return engine (same rules as expiry_shadow._fwd_metrics) ─────────
_fwd_cache = {}


def _load_fwd_candles(token):
    if token in _fwd_cache:
        return _fwd_cache[token]
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    try:
        rows = conn.execute(
            "SELECT ts, open, close FROM candles_5m"
            " WHERE token=? AND is_closed=1 ORDER BY ts", (token.upper(),)).fetchall()
    finally:
        conn.close()
    _fwd_cache[token] = rows
    return rows


def _fwd_4h(rows, entry_ts, direction):
    """fwd 4h return — mirrors expiry_shadow._fwd_metrics exactly (entry = OPEN
    of first closed 5m candle with ts >= entry_ts, no lookahead; needs the +48th
    candle; sgn = the blocked direction's would-be direction: +1 LONG, -1 SHORT).
    Returns None when the +4h horizon is not yet in the candle data."""
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
    o = rows[i][1]
    sgn = 1 if direction == 'LONG' else -1
    return sgn * (rows[i + 48][2] / o - 1.0) * 100.0


def close_fwd():
    """Backfill fwd_4h (expiry-style fwd-return join) for events >4.5h old.

    This is the PRIMARY outcome join (registry gate-shadow KEEP-with-switch):
    covers ~100% of events vs the trade-join's ~13%. fwd_done=1 marks the
    attempt; fwd_4h stays NULL only when the token has no candle history or the
    +4h horizon has not happened yet (those events are retried never — the
    horizon gap is at the corpus tail only).
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        # blocked_at is stored 'YYYY-MM-DD HH:MM:SS+00:00' (space + tz) — match
        # that exact format for the cutoff (same FIX class as close_events).
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=FWD_AFTER_HOURS)).strftime('%Y-%m-%d %H:%M:%S') + '+00:00'
        pending = cur.execute(
            "SELECT id, token, direction, blocked_at FROM events "
            "WHERE fwd_done IS NOT 1 AND blocked_at < ?", (cutoff,)).fetchall()
        n_ok = n_nodata = 0
        for eid, token, direction, blocked_at in pending:
            try:
                b_dt = datetime.fromisoformat(blocked_at)
                entry_ts = calendar.timegm(b_dt.utctimetuple())
            except (ValueError, TypeError):
                cur.execute("UPDATE events SET fwd_done=1 WHERE id=?", (eid,))
                continue
            rows = _load_fwd_candles(token)
            fm = _fwd_4h(rows, entry_ts, direction) if rows else None
            if fm is None:
                n_nodata += 1
                cur.execute("UPDATE events SET fwd_done=1 WHERE id=?", (eid,))
            else:
                cur.execute("UPDATE events SET fwd_4h=?, fwd_done=1 WHERE id=?",
                            (fm, eid))
                n_ok += 1
        conn.commit()
        tot, done, ok = cur.execute(
            "SELECT COUNT(*), SUM(CASE WHEN fwd_done=1 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN fwd_4h IS NOT NULL THEN 1 ELSE 0 END) FROM events"
        ).fetchone()
        log(f'fwd: {len(pending)} backfilled, {n_ok} with fwd_4h'
            f' ({n_nodata} lacking candle horizon); coverage {ok or 0}/{tot}'
            f' events ({(ok or 0)/tot*100 if tot else 0:.1f}%, attempted {done or 0})')
        return n_ok
    finally:
        conn.close()


def _avg_notional():
    """Live avg notional for the $-eq basis: 30d trailing avg amount_usdt over
    closed PG trades (the miner's $13.40 basis), falling back to all-time closed
    when the window is thin. None when PG is unreachable — report degrades to pp."""
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        pg = psycopg2.connect(**BRAIN_DB_DICT)
        try:
            cur = pg.cursor()
            cur.execute(
                "SELECT ROUND(AVG(amount_usdt)::numeric, 2), COUNT(*) FROM trades "
                "WHERE status='closed' AND amount_usdt IS NOT NULL "
                "AND open_time >= now() - make_interval(days => %s)",
                (NOTIONAL_WINDOW_DAYS,))
            avg_w, n_w = cur.fetchone()
            if avg_w is not None and (n_w or 0) >= 30:
                return float(avg_w)
            cur.execute(
                "SELECT ROUND(AVG(amount_usdt)::numeric, 2) FROM trades "
                "WHERE status='closed' AND amount_usdt IS NOT NULL")
            avg_all = cur.fetchone()[0]
            return float(avg_all) if avg_all is not None else None
        finally:
            pg.close()
    except Exception as e:
        log(f'$-eq basis unavailable (PG: {e}) — reporting pp only')
        return None


def report():
    """All-time aggregation. FWD-BASIS leads (registry gate-shadow join switch,
    2026-10-31): expiry-style fwd-return join over every event with a +4h candle
    horizon — direction-signed in the blocked direction's would-be direction, so
    negative fwd_4h = the blocked direction would have LOST = gate protective.
    $-eq converts pp at the LIVE avg notional (trailing 30d PG amount_usdt).

    SECONDARY — trade-join semantics (#156): an event resolves to the first REAL
    Hermes trade on the same token+direction opening within 24h after the block.
    That trade is already in the live book, so its PnL here is NEITHER avoided
    NOR foregone money — it is an indicator of how the blocked token subsequently
    traded. Before #156 the report summed one event per block, so a single real
    trade could be added many times (measured 4,182 events -> 380 trades = 11.0x,
    23x PnL inflation, per-gate sign flips). Every trade-join number below counts
    each referenced trade at most once per gate.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        tot = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        if not tot:
            log('report: no events yet')
            return
        # ── FWD BASIS (LEAD) ───────────────────────────────────────────────────
        log('─── GATE SHADOW REPORT — FWD-BASIS (LEAD): expiry-style fwd-return join ───')
        fwd_rows = cur.execute(
            "SELECT gate, direction, fwd_4h FROM events WHERE fwd_4h IS NOT NULL"
        ).fetchall()
        if not fwd_rows:
            log('  no fwd_4h rows yet — run --fwd to backfill the forward-return join')
        else:
            notional = _avg_notional()
            blocks_by_gate = dict(cur.execute(
                "SELECT gate, COUNT(*) FROM events GROUP BY 1").fetchall())
            n_cov = len(fwd_rows)
            gagg = {}
            for gate, d, f4 in fwd_rows:
                a = gagg.setdefault(gate, {'n': 0, 'nL': 0, 'nS': 0,
                                           'pp': 0.0, 'ppL': 0.0, 'ppS': 0.0})
                a['n'] += 1
                a['pp'] += f4
                if d == 'LONG':
                    a['nL'] += 1
                    a['ppL'] += f4
                else:
                    a['nS'] += 1
                    a['ppS'] += f4
            net_pp = sum(a['pp'] for a in gagg.values())
            nL = sum(a['nL'] for a in gagg.values())
            ppL = sum(a['ppL'] for a in gagg.values())
            nS = sum(a['nS'] for a in gagg.values())
            ppS = sum(a['ppS'] for a in gagg.values())
            log('  fwd_4h = direction-signed fwd 4h return (candles_5m; entry = OPEN of the')
            log('    first closed 5m candle at/after block; sgn=+1 LONG / -1 SHORT blocked dir):')
            log('    NEGATIVE = blocked direction would have LOST = gate protective.')
            log(f'  coverage: {n_cov}/{tot} events ({n_cov / tot * 100:.1f}%)')
            eq_s = (f'  ${net_pp / 100 * notional:+,.2f}-eq @ ${notional:.2f} live avg notional'
                    if notional else '')
            log(f'  NET: {net_pp:+,.1f}pp total, avg {net_pp / n_cov:+.3f}%/event{eq_s}')
            if nL:
                eql = f'  ${ppL / 100 * notional:+,.2f}-eq' if notional else ''
                log(f'    LONG  blocks n={nL:6d} avg {ppL / nL:+.3f}%'
                    f' {"(protective)" if ppL < 0 else "(costly)"}{eql}')
            if nS:
                eqs = f'  ${ppS / 100 * notional:+,.2f}-eq' if notional else ''
                log(f'    SHORT blocks n={nS:6d} avg {ppS / nS:+.3f}%'
                    f' {"(protective)" if ppS < 0 else "(costly)"}{eqs}')
            hdr = f'{"gate":28} {"blocks":>6} {"fwd_n":>6} {"avg%":>8} {"net_pp":>10}'
            if notional:
                hdr += f' {"net_$-eq":>9}'
            log(hdr)
            for gate, a in sorted(gagg.items(), key=lambda kv: -kv[1]['pp']):
                avg = a['pp'] / a['n']
                flag = ''
                if a['n'] >= 50:
                    flag = (' ← COSTLY (blocked dir would have won, n>=50)' if avg > 0
                            else ' ← protective')
                line = (f'{gate:28} {blocks_by_gate.get(gate, a["n"]):6d} {a["n"]:6d}'
                        f' {avg:+8.3f} {a["pp"]:+10.1f}')
                if notional:
                    line += f' {a["pp"] / 100 * notional:+9.2f}'
                log(line + flag)
            log('  (per-gate sorted by net_pp desc = costliest blocks first;'
                ' CEO criteria n>=50 + OOS same-sign apply to any gate change)')
        # ── TRADE-JOIN BASIS (SECONDARY, continuity) ───────────────────────────
        rows = cur.execute(
            "SELECT gate, closed, would_trade, would_win, would_pnl, trade_id "
            "FROM events").fetchall()
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
        log('─── SECONDARY: TRADE-JOIN BASIS (follow-on trade outcomes of blocked tokens) ───')
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
    ap.add_argument('--fwd', action='store_true')
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--since-hours', type=int, default=6)
    args = ap.parse_args()
    run_all = not (args.record or args.close or args.fwd or args.report)
    if run_all or args.record:
        record(args.since_hours)
    if run_all or args.close:
        close_events()
    if run_all or args.fwd:
        close_fwd()
    if run_all or args.report:
        report()
    return 0


if __name__ == '__main__':
    sys.exit(main())
