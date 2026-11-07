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
Gate changes still need CEO criteria (tok_n>=50 distinct token|direction pairs,
OOS same-sign).

STATISTICS WARNING (brain_auditor #160 class, mirrored from expiry_shadow.py) —
one row per block EVENT, and events repeat over the same tokens: the 10-min
dedupe still yields OVERLAPPING 4h fwd windows that the raw basis counts as
independent evidence (measured 2026-10-31: 53,421 fwd rows across only ~200
distinct token|direction pairs — BTC LONG alone x1,605). Event/per-row figures
are therefore PSEUDO-REPLICATED and overstated; the independent unit is
token|direction (tok_n), not the row. --report prints tok_n beside every fwd_n,
only flags COSTLY/protective at tok_n>=50 (row-n alone never flags), and prints
a deduped non-overlapping-window NET next to the raw NET. Use
brain/analysis/cluster_t.py `cluster_t(values, clusters)` (selfcheck PASS) for
any significance claim off this DB; naive per-row averages are point estimates
only.

Usage: python3 scripts/gate_shadow.py [--record] [--close] [--fwd] [--report] [--since-hours 6]
       python3 scripts/gate_shadow.py --backfill-rr 24        # option TAKES a value
       --since-hours limits --record only; --report/--fwd are all-time by design.
       --backfill-rr HOURS = one-shot, idempotent RR-ENGINE recovery for lines the
       forward offset already consumed before RR_BLOCK_RE existed (see backfill_rr).
       Alone it runs ONLY the backfill; combined with the other flags it runs them too.
"""
import sys
import os
import re
import json
import gzip
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
# 4h fwd horizon expressed once: 48 x 5m candles (the same 48-candle rule as
# expiry_shadow._fwd_metrics) and its wall-clock size in seconds. Used both by
# the fwd engine and by close_fwd's "has the horizon matured yet?" test and by
# report()'s non-overlapping-window dedupe.
FWD_HORIZON_CANDLES = 48
FWD_HORIZON_SECS = FWD_HORIZON_CANDLES * 300  # 300s = 5m candle interval
# Generous upper bound on pipeline.log growth per hour, used ONLY to bound
# backfill_rr's scan window (bug_hunter F3). The real rate is tens of MB/day,
# so this never under-scans a requested `hours` window.
BACKFILL_BYTES_PER_HOUR = 70_000_000

# ── rotated-log discovery ─────────────────────────────────────────────────────
# log_rotate_pipeline renames pipeline.log daily (~00:10) into
# logs/archive/pipeline.log.<YYYYMMDDhhmmss>.gz. Reading ONLY the live file
# silently drops every older line — code-review H1: the mandated 11-10 join
# re-run read n=0 for all 5 shadow tags, and gate_shadow_health's log-dedup
# denominator collapsed until the live log regrew (its --selfcheck then
# asserted `db > log-dedup`). Every consumer of pipeline.log must go through
# archive_paths()/open_log_text() to stay correct across the rotation.
ARCHIVE_NAME_RE = re.compile(r'^pipeline\.log\.(\d{14})\.gz$')


def archive_paths(log_path=PIPELINE_LOG, since=None):
    """Rotated .gz logs, oldest-first. `since` (datetime) drops archives stamped
    at or before it: an archive stamped T holds data ENDING at T, so T <= since
    means every line it carries is older than the window."""
    out = []
    adir = os.path.join(os.path.dirname(log_path), 'archive')
    if not os.path.isdir(adir):
        return out
    # Archive stamps are UTC wall-clock; normalise BOTH sides so a naive caller
    # and an aware `datetime.now(timezone.utc)` cutoff compare cleanly
    # (TypeError: can't compare offset-naive and offset-aware datetimes).
    if since is not None and since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    for name in sorted(os.listdir(adir)):
        m = ARCHIVE_NAME_RE.match(name)
        if not m:
            continue
        if since is not None:
            try:
                rot = datetime.strptime(m.group(1), '%Y%m%d%H%M%S'
                                        ).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if rot <= since:
                continue
        out.append(os.path.join(adir, name))
    return out


def open_log_text(path):
    """Text handle for a live or rotated log (caller closes it)."""
    if path.endswith('.gz'):
        return gzip.open(path, 'rt', errors='replace')
    return open(path, 'r', errors='replace')


def log_sources(log_path=PIPELINE_LOG, since=None):
    """Every file that can hold lines in the window: rotated archives first,
    live log last (its content is the newest)."""
    return archive_paths(log_path, since=since) + (
        [log_path] if os.path.exists(log_path) else [])


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
# SCOPE+ (registry gate-shadow-capture-coverage-fix, CEO mover-census verdict
# 20261106T215910Z): rr-engine hard blocks fire as `🎯 [RR-ENGINE] TOKEN DIR:
# RR HARD BLOCKED: ...` and were captured at 0% because BLOCK_RE only accepts
# the 🚫/🔒/🚧/🌊 block emojis — the 🎯 target emoji was never in its class.
# HARD BLOCKED only: the sibling `RR PENALTY ... mult=0.70` lines are a
# multiplier, not a kill, and must stay out of the counterfactual.
# TELEMETRY ONLY — nothing in the trading path changed; this is the same
# log-parse capture every other gate in this DB uses.
RR_BLOCK_RE = re.compile(
    r'🎯\s+\[RR-ENGINE\]\s+([A-Za-z0-9]+):?\s+(LONG|SHORT)\b'
    r'.*?RR HARD BLOCKED',
    re.IGNORECASE,
)


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [gate_shadow] {msg}', flush=True)


def _pin_pg_utc(pg, where):
    """FIX 2026-10-31 (code-review #5): PG trades.open_time is `timestamp
    without time zone`, so every `open_time >= %s::timestamptz` window edge in
    this script resolved the timestamptz through the SESSION TimeZone — the
    same block could fall inside or outside the window depending on where the
    session ran. Pin the session (transaction-local, no DDL) to UTC and PROVE
    it with SHOW timezone on both sides of the SET, so the log records what the
    window edges were actually measured against.

    Note: `SET LOCAL TimeZone 'UTC'` is a SYNTAX ERROR in PostgreSQL ('TimeZone'
    parses as a generic var_name, which needs TO/=); the accepted form is
    `SET LOCAL TIME ZONE 'UTC'` (verified against PG 16.15). A failed SET also
    aborts the surrounding transaction, so any failure is followed by a
    rollback before the caller's own queries run.
    """
    cur = pg.cursor()
    try:
        cur.execute("SHOW timezone")
        before = cur.fetchone()[0]
        cur.execute("SET LOCAL TIME ZONE 'UTC'")  # holds for this txn (psycopg2 default)
        cur.execute("SHOW timezone")
        after = cur.fetchone()[0]
        log(f'pg timezone [{where}]: {before} -> {after} (SET LOCAL TIME ZONE UTC)')
    except Exception as e:
        try:
            pg.rollback()  # clear the aborted transaction a bad SET leaves behind
        except Exception:
            pass
        log(f'pg timezone [{where}] NOT pinned ({e}) — open_time window edges may drift')


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
    # FIX 2026-10-31 (code-review #12): two literal ALTERs instead of one f-string
    # over a hardcoded tuple — same shape as the trade_id ALTER above.
    try:
        conn.execute("ALTER TABLE events ADD COLUMN fwd_4h REAL")
    except sqlite3.OperationalError:
        pass  # column exists
    try:
        conn.execute("ALTER TABLE events ADD COLUMN fwd_done INTEGER")
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
                    # SCOPE+ (registry gate-shadow-capture-coverage-fix): rr-engine
                    # hard blocks — same match order, same 10-min dedup bucket, same
                    # INSERT as every other gate here.  Fail-silent by construction:
                    # an unparsable line just `continue`s, so a block can never be
                    # affected by this telemetry.
                    mr = RR_BLOCK_RE.search(line)
                    if mr:
                        gate, token, direction = 'RR-ENGINE', mr.group(1).upper(), mr.group(2).upper()
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


def backfill_rr(hours=24):
    """One-shot RR-ENGINE recovery (registry gate-shadow-capture-coverage-fix
    SCOPE+, CEO mover-census 20261106T215910Z).

    record() only ever scans FORWARD from the offset, so every
    `🎯 [RR-ENGINE] ... RR HARD BLOCKED` line written before RR_BLOCK_RE
    existed was consumed and dropped — those rows are unrecoverable through the
    normal path and would leave RR-ENGINE pinned at ~0% capture in
    gate_shadow_health --per-gate for a full window.  This re-reads the log for
    the trailing `hours` and inserts with the IDENTICAL gate|token|direction|
    10-min dedup key, so it is idempotent (UNIQUE dedup_key) and can never
    double-count a row record() already wrote.  RR-ENGINE only — other gates
    are untouched, and this is telemetry: nothing in the trading path runs it.
    """
    if not os.path.exists(PIPELINE_LOG):
        log(f'pipeline.log missing: {PIPELINE_LOG}')
        return 0
    conn = get_db()
    try:
        cur = conn.cursor()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        n_new = n_dup = n_since_commit = 0
        # Scan every source that can hold lines in the window: rotated archives
        # (bounded by `since`) plus the live log.  The live log is tail-seeked
        # (bug_hunter F3) so a 210MB file is never read from byte 0; 70MB/hour
        # is a deliberately generous upper bound (the log runs tens of MB/day)
        # and the discarded head is dropped at a line boundary so no line is
        # half-read.  `continue` (not `break`) on pre-cutoff lines mirrors
        # record(): cheap, and does not assume the file is perfectly sorted.
        live_start = 0
        if os.path.exists(PIPELINE_LOG):
            live_start = max(0, os.path.getsize(PIPELINE_LOG)
                             - hours * BACKFILL_BYTES_PER_HOUR)
        for path in log_sources(PIPELINE_LOG, since=cutoff):
            try:
                with open_log_text(path) as f:
                    if path == PIPELINE_LOG and live_start:
                        f.seek(live_start)
                        f.readline()  # discard the partial line under `start`
                    for line in f:
                        # L3: RR_BLOCK_RE is IGNORECASE, so the prefilter must
                        # be too — a case-variant line would otherwise be
                        # reachable by record() but skipped here.
                        if 'rr hard blocked' not in line.lower():
                            continue
                        mr = RR_BLOCK_RE.search(line)
                        if not mr:
                            continue
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
                        token, direction = mr.group(1).upper(), mr.group(2).upper()
                        bucket = b_dt.strftime('%Y%m%d%H%M')[:-1]  # 10-min bucket
                        dedup = f'RR-ENGINE|{token}|{direction}|{bucket}'
                        try:
                            cur.execute(
                                "INSERT INTO events (gate, token, direction, blocked_at, dedup_key) "
                                "VALUES (?,?,?,?,?)",
                                ('RR-ENGINE', token, direction, blocked_at, dedup))
                            n_new += 1
                        except sqlite3.IntegrityError:
                            n_dup += 1  # already recorded by record() — idempotent
                        n_since_commit += 1
                        # L2: do not hold one write transaction open across the
                        # whole scan — the hourly record()/watchdog read must
                        # never see "database is locked" for seconds.
                        if n_since_commit >= 500:
                            conn.commit()
                            n_since_commit = 0
            except (OSError, EOFError, gzip.BadGzipFile, UnicodeDecodeError) as e:
                log(f'backfill-rr: skipping unreadable {path}: {e}')
                continue
        conn.commit()
        total = cur.execute(
            "SELECT COUNT(*) FROM events WHERE gate='RR-ENGINE'").fetchone()[0]
        log(f'backfill-rr: +{n_new} new RR-ENGINE rows over {hours}h'
            f' ({n_dup} already present), RR-ENGINE total={total}')
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
        _pin_pg_utc(pg, 'close')  # open_time (timestamp w/o tz) window edges
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
            # open_time is `timestamp without time zone`, so the ::timestamptz
            # edges below resolve in the SESSION zone — pinned to UTC by
            # _pin_pg_utc above (FIX 2026-10-31 code-review #5).
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
    # FIX 2026-10-31 (code-review #8): key the cache by the SAME normalized form
    # the query uses (token.upper()), or 'btc' and 'BTC' cached separate series.
    token = token.upper()
    if token in _fwd_cache:
        return _fwd_cache[token]
    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    try:
        rows = conn.execute(
            "SELECT ts, open, close FROM candles_5m"
            " WHERE token=? AND is_closed=1 ORDER BY ts", (token,)).fetchall()
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
    if i + FWD_HORIZON_CANDLES >= len(rows):
        return None
    o = rows[i][1]
    if not o:
        # FIX 2026-10-31 (code-review #7): zero/absurd open cannot form a
        # return — guard the rows[i+48][2] / o division instead of raising.
        return None
    sgn = 1 if direction == 'LONG' else -1
    return sgn * (rows[i + FWD_HORIZON_CANDLES][2] / o - 1.0) * 100.0


def close_fwd():
    """Backfill fwd_4h (expiry-style fwd-return join) for events >4.5h old.

    This is the PRIMARY outcome join (registry gate-shadow KEEP-with-switch):
    covers ~100% of events vs the trade-join's ~13%. fwd_done=1 marks a
    SETTLED attempt: either fwd_4h was computed, or the token has no candle
    history at all (zero rows), or blocked_at is unparsable (can never mature).
    FIX 2026-10-31 (code-review #2 HIGH): rows whose +4h horizon has NOT
    matured yet (candle series ends before entry_ts + FWD_HORIZON_SECS) are no
    longer stamped done — they stay pending so the next hourly run computes
    them. The old unconditional stamp lost 37 done-NULL rows (12 of them
    computable a few hours later, ~-11.4pp of NET).
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
        n_ok = n_nodata = n_retry = n_badparse = 0
        n_since_commit = 0  # FIX 2026-10-31 (code-review #3 NIT): commit in-flight
        for eid, token, direction, blocked_at in pending:
            try:
                b_dt = datetime.fromisoformat(blocked_at)
                entry_ts = calendar.timegm(b_dt.utctimetuple())
            except (ValueError, TypeError):
                # FIX 2026-10-31 (code-review #9 NIT): count+log instead of a
                # silent stamp — an unparsable blocked_at can never mature, so
                # it IS settled, but the loss must be visible in the log.
                n_badparse += 1
                cur.execute("UPDATE events SET fwd_done=1 WHERE id=?", (eid,))
                n_since_commit += 1
                continue
            rows = _load_fwd_candles(token)
            fm = _fwd_4h(rows, entry_ts, direction) if rows else None
            if fm is not None:
                cur.execute("UPDATE events SET fwd_4h=?, fwd_done=1 WHERE id=?",
                            (fm, eid))
                n_ok += 1
            elif not rows:
                # zero candle rows = the token has no history at all: settle it
                # so it is not rescanned every hour.
                n_nodata += 1
                cur.execute("UPDATE events SET fwd_done=1 WHERE id=?", (eid,))
            else:
                # FIX 2026-10-31 (code-review #2 HIGH): candle rows exist but the
                # series ends before the +4h horizon — the horizon has not
                # matured (candles still arriving; gaps may still be backfilled).
                # Leave PENDING for the next hourly retry; stamping here is what
                # permanently lost the 12 computable done-NULL rows.
                n_retry += 1
                continue
            n_since_commit += 1
            if n_since_commit >= 500:
                conn.commit()
                n_since_commit = 0
        conn.commit()
        tot, done, ok = cur.execute(
            "SELECT COUNT(*), SUM(CASE WHEN fwd_done=1 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN fwd_4h IS NOT NULL THEN 1 ELSE 0 END) FROM events"
        ).fetchone()
        still = cur.execute(
            "SELECT COUNT(*) FROM events WHERE fwd_done IS NOT 1").fetchone()[0]
        log(f'fwd: {len(pending)} eligible, {n_ok} with fwd_4h'
            f' ({n_nodata} no-history settled, {n_retry} horizon-not-matured left'
            f' pending for retry, {n_badparse} unparsable blocked_at settled);'
            f' coverage {ok or 0}/{tot} events'
            f' ({(ok or 0)/tot*100 if tot else 0:.1f}%, attempted {done or 0},'
            f' pending {still})')
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
            # open_time is `timestamp without time zone`; `open_time >= now() -
            # make_interval(...)` resolves now() through the SESSION zone, so a
            # non-UTC session shifts the 30d window edge. Pin to UTC
            # (FIX 2026-10-31 code-review #5) before measuring.
            _pin_pg_utc(pg, 'notional')
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
    The FWD numbers are a PER-BLOCK OVERLAPPING-WINDOW basis (one row per block
    EVENT over repeated tokens — module docstring STATISTICS WARNING, #160
    class): tok_n (distinct token|direction) is the independent unit, COSTLY /
    protective flags require tok_n>=50 rather than row-n, every gate in the DB
    is listed (zero-coverage gates print a hole row), and a deduped
    non-overlapping-window NET is printed beside the raw NET.

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
            "SELECT gate, token, direction, blocked_at, fwd_4h FROM events"
            " WHERE fwd_4h IS NOT NULL"
        ).fetchall()
        if not fwd_rows:
            log('  no fwd_4h rows yet — run --fwd to backfill the forward-return join')
        else:
            notional = _avg_notional()
            # FIX 2026-10-31 (code-review #4 LOW): seed every gate that has ANY
            # block, so a gate with zero fwd coverage prints an explicit hole
            # row instead of silently vanishing from this table.
            blocks_by_gate = dict(cur.execute(
                "SELECT gate, COUNT(*) FROM events GROUP BY 1").fetchall())
            gagg = {g: {'n': 0, 'nL': 0, 'nS': 0, 'toks': set(),
                        'pp': 0.0, 'ppL': 0.0, 'ppS': 0.0}
                    for g in blocks_by_gate}
            n_cov = len(fwd_rows)
            n_other_dir = 0  # FIX 2026-10-31 (code-review #6 NIT): no silent else
            for gate, tok, d, blocked_at, f4 in fwd_rows:
                a = gagg.setdefault(gate, {'n': 0, 'nL': 0, 'nS': 0, 'toks': set(),
                                           'pp': 0.0, 'ppL': 0.0, 'ppS': 0.0})
                a['n'] += 1
                a['pp'] += f4
                # independent unit = token|direction, NOT the row (#160 class)
                a['toks'].add(f'{tok}|{d}')
                if d == 'LONG':
                    a['nL'] += 1
                    a['ppL'] += f4
                elif d == 'SHORT':
                    a['nS'] += 1
                    a['ppS'] += f4
                else:
                    n_other_dir += 1
            net_pp = sum(a['pp'] for a in gagg.values())
            n_pairs = len({t for a in gagg.values() for t in a['toks']})
            nL = sum(a['nL'] for a in gagg.values())
            ppL = sum(a['ppL'] for a in gagg.values())
            nS = sum(a['nS'] for a in gagg.values())
            ppS = sum(a['ppS'] for a in gagg.values())
            log('  fwd_4h = direction-signed fwd 4h return (candles_5m; entry = OPEN of the')
            log('    first closed 5m candle at/after block; sgn=+1 LONG / -1 SHORT blocked dir):')
            log('    NEGATIVE = blocked direction would have LOST = gate protective.')
            log(f'  coverage: {n_cov}/{tot} events ({n_cov / tot * 100:.1f}%)')
            # FIX 2026-10-31 (code-review #1c): pseudo-replication warning —
            # same class and wording as expiry_shadow.py's brain_auditor #160
            # STATISTICS WARNING (one row per EVENT over repeated tokens).
            log('  ⚠ PSEUDO-REPLICATED (brain_auditor run #160 class, same warning as'
                ' expiry_shadow): one row per block EVENT, and events repeat over the'
                f' same {n_pairs} token|direction pairs — overlapping 4h windows from the'
                ' 10-min dedupe are counted as independent evidence, so every per-row /'
                ' per-gate figure below is PSEUDO-REPLICATED and overstated.')
            log('    The independent unit is token|direction (the tok_n column), not the'
                ' row; flags below require tok_n>=50 distinct pairs. Use'
                ' brain/analysis/cluster_t.py cluster_t(values, clusters) (selfcheck PASS)'
                ' for any significance claim off this DB; naive per-row averages are point'
                ' estimates only.')
            eq_s = (f'  ${net_pp / 100 * notional:+,.2f}-eq @ ${notional:.2f} live avg notional'
                    if notional is not None else '')
            # FIX 2026-10-31 (code-review #1d): label the raw NET for what it is
            # (per-block, overlapping windows), then print the deduped
            # non-overlapping-window NET right beside it (per token|direction, only
            # the first block of each >=4h-spaced window — greedy, blocked_at order).
            log(f'  NET (per-block overlapping-window basis): {net_pp:+,.1f}pp total,'
                f' avg {net_pp / n_cov:+.3f}%/event{eq_s}')
            seen_last, dd_n, dd_pp = {}, 0, 0.0
            for _gate, _tok, _d, _ba, _f4 in sorted(fwd_rows, key=lambda r: r[3]):
                try:
                    _et = datetime.fromisoformat(_ba).timestamp()
                except (ValueError, TypeError):
                    continue
                _key = f'{_tok}|{_d}'
                if _key in seen_last and _et - seen_last[_key] < FWD_HORIZON_SECS:
                    continue  # overlaps the window already taken for this pair
                seen_last[_key] = _et
                dd_n += 1
                dd_pp += _f4
            dd_eq = f'  ${dd_pp / 100 * notional:+,.2f}-eq' if notional is not None else ''
            log(f'  DEDUPED (non-overlapping >=4h windows, 1st block per'
                f' token|direction): n={dd_n:6d} NET: {dd_pp:+,.1f}pp,'
                f' avg {(dd_pp / dd_n if dd_n else 0.0):+.3f}%/event{dd_eq}')
            if nL:
                eql = f'  ${ppL / 100 * notional:+,.2f}-eq' if notional is not None else ''
                log(f'    LONG  blocks n={nL:6d} avg {ppL / nL:+.3f}%'
                    f' {"(protective)" if ppL < 0 else "(costly)" if ppL > 0 else "(neutral)"}{eql}')
            if nS:
                eqs = f'  ${ppS / 100 * notional:+,.2f}-eq' if notional is not None else ''
                log(f'    SHORT blocks n={nS:6d} avg {ppS / nS:+.3f}%'
                    f' {"(protective)" if ppS < 0 else "(costly)" if ppS > 0 else "(neutral)"}{eqs}')
            if n_other_dir:
                # FIX 2026-10-31 (code-review #6 NIT): the split used to swallow
                # anything non-LONG into the SHORT bucket — count what is left.
                log(f'  ⚠ {n_other_dir} fwd rows had a direction outside LONG/SHORT'
                    ' (excluded from the split above)')
            hdr = (f'{"gate":28} {"blocks":>6} {"fwd_n":>6} {"tok_n":>6} {"avg%":>8}'
                   f' {"net_pp":>10}')
            if notional is not None:
                hdr += f' {"net_$-eq":>9}'
            log(hdr)
            # zero-fwd-coverage gates sort last (nothing to rank pp on)
            for gate, a in sorted(gagg.items(),
                                  key=lambda kv: (kv[1]['n'] == 0, -kv[1]['pp'])):
                if a['n'] == 0:
                    # FIX 2026-10-31 (code-review #4 LOW): coverage holes are
                    # printed, not hidden.
                    hole = (f'{gate:28} {blocks_by_gate.get(gate, 0):6d} {0:6d}'
                            f' {0:6d} {"n/a":>8} {"n/a":>10}')
                    if notional is not None:
                        hole += f' {"n/a":>9}'
                    log(hole + ' ← NO FWD COVERAGE (zero fwd_4h rows)')
                    continue
                avg = a['pp'] / a['n']
                tok_n = len(a['toks'])
                flag = ''
                # FIX 2026-10-31 (code-review #1b): the COSTLY/protective flag is
                # gated on DISTINCT token|direction pairs (tok_n>=50), never on
                # raw row-n — row-n is pseudo-replicated (one BTC LONG block
                # window can contribute 1,605 overlapping rows).
                if tok_n >= 50:
                    # FIX 2026-10-31 (code-review #10 NIT): avg exactly 0.0 used
                    # to fall into the protective branch — test avg<0 instead.
                    if avg > 0:
                        flag = ' ← COSTLY (blocked dir would have won, tok_n>=50)'
                    elif avg < 0:
                        flag = ' ← protective'
                    else:
                        flag = ' ← neutral (avg exactly 0)'
                line = (f'{gate:28} {blocks_by_gate.get(gate, a["n"]):6d} {a["n"]:6d}'
                        f' {tok_n:6d} {avg:+8.3f} {a["pp"]:+10.1f}')
                if notional is not None:
                    line += f' {a["pp"] / 100 * notional:+9.2f}'
                log(line + flag)
            log('  (per-gate sorted by net_pp desc = costliest blocks first; each row is'
                ' a per-block overlapping-window sum — tok_n is the distinct'
                ' token|direction count behind it and flags need tok_n>=50, not raw'
                ' fwd_n; CEO criteria tok_n>=50 + OOS same-sign apply to any gate change)')
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
    ap.add_argument('--since-hours', type=int, default=None,
                    help='hours for --record (default 6); supplying it alone keeps the '
                         'historic behaviour of running all four modes')
    ap.add_argument('--backfill-rr', type=int, default=0, metavar='HOURS',
                    help='one-shot: recover RR-ENGINE hard-block lines the forward '
                         'offset already consumed before RR_BLOCK_RE existed '
                         '(0 = off, idempotent)')
    args = ap.parse_args()
    since_given = args.since_hours is not None
    since_hours = 6 if args.since_hours is None else args.since_hours
    # L1: `--backfill-rr H` ALONE runs only the backfill, but with any mode flag
    # or an explicit --since-hours it is additive — `--backfill-rr 24
    # --since-hours 6` must still run record+close+fwd+report instead of
    # silently dropping them (the docstring promised "combined ... it runs them").
    run_all = not (args.record or args.close or args.fwd or args.report
                   or (args.backfill_rr and not since_given))
    if args.backfill_rr:
        backfill_rr(args.backfill_rr)
    if run_all or args.record:
        record(since_hours)
    if run_all or args.close:
        close_events()
    if run_all or args.fwd:
        close_fwd()
    if run_all or args.report:
        report()
    return 0


if __name__ == '__main__':
    sys.exit(main())
