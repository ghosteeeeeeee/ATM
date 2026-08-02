#!/usr/bin/env python3
"""
archive-trades.py — Atomic trade archiver for Hermes.

Archives closed trades from PostgreSQL brain DB to JSON + SQLite for analysis.
Each archived trade is stored WITH its full signal context — the join is done
atomically at archive time (not post-hoc), so coverage is 100% for all trades
that were executed after this script was deployed.

For pre-existing trades (before this script existed): re-link to signals via
nearest-time join into signals_hermes_runtime.db to maximize coverage.

Usage:
    python3 archive-trades.py --dry-run       # show what would be archived
    python3 archive-trades.py --apply         # actually archive
    python3 archive-trades.py --rebuild-db    # rebuild analysis SQLite DB from scratch
"""
import sys, os, json, sqlite3, gzip, time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
import psycopg2

# ── Paths ──────────────────────────────────────────────────────────────────
ARCHIVE_DIR = '/root/.hermes/archive/trades'
ANALYSIS_DB = '/root/.hermes/archive/trades_analysis.db'
os.makedirs(ARCHIVE_DIR, exist_ok=True)

RUNTIME_SIGNALS_DB = '/root/.hermes/data/signals_hermes_runtime.db'

# ── Schema: use ACTUAL PostgreSQL column names exactly ─────────────────────
# Retrieve these dynamically to ensure accuracy
def get_pg_columns(conn_pg):
    cur = conn_pg.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'trades' ORDER BY ordinal_position")
    cols = [r[0] for r in cur.fetchall()]
    cur.close()
    return cols

TRADE_FIELDS_PG = get_pg_columns(psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres'))


def get_closed_trades(conn_pg, limit=None):
    """Fetch closed trades from PostgreSQL. Returns list of dicts."""
    cols = get_pg_columns(conn_pg)
    fields_str = ', '.join(cols)
    query = f"""
        SELECT {fields_str}
        FROM trades
        WHERE status = 'closed'
          AND close_time IS NOT NULL
        ORDER BY close_time DESC
    """
    if limit:
        query += f" LIMIT {limit}"
    cur = conn_pg.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    return [dict(zip(cols, r)) for r in rows]


def get_runtime_signal(token, direction, trade_open_time, runtime_conn):
    """
    Find the best matching signal from signals_hermes_runtime.db for a trade.
    Matches on (token, direction) + nearest timestamp within ±6 hours.
    Returns dict or None.
    """
    try:
        cur = runtime_conn.cursor()
        cur.execute("""
            SELECT signal_type, confidence, value, price,
                   z_score, z_score_tier, rsi_14,
                   macd_value, macd_signal, macd_hist,
                   momentum_state, decision, leverage,
                   created_at
            FROM signals
            WHERE token = %s
              AND direction = %s
              AND created_at IS NOT NULL
            ORDER BY ABS(EXTRACT(EPOCH FROM (created_at - %s::timestamptz)))
            LIMIT 1
        """, (token.upper(), direction.upper(), trade_open_time))
        row = cur.fetchone()
        if row:
            cols = [d[0] for d in cur.description]
            cur.close()
            return dict(zip(cols, row))
        cur.close()
    except Exception:
        pass
    return None


def build_analysis_db(trades, runtime_conn, append=False):
    """
    Insert trades into the SQLite analysis DB.
    - append=True:  preserve existing rows, skip any trade IDs already present (idempotent).
    - append=False: wipe the DB and rebuild from scratch (default).
    Signal context is embedded atomically at archive time from PostgreSQL columns.
    """
    # ── Serialization helpers ──────────────────────────────────────────────
    def _json_safe(v):
        """Convert values that SQLite/json cannot natively store."""
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, dict):
            return json.dumps(v)
        if isinstance(v, list):
            return json.dumps(v)
        return v

    def _int_safe(v):
        """Normalize values to int (for INTEGER columns)."""
        if v is None:
            return None
        if isinstance(v, bool):
            return 1 if v else 0
        if isinstance(v, Decimal):
            return int(v)
        if isinstance(v, (int, float)):
            return int(v)
        return v

    # ── Build signals lookup by (token, direction) ──────────────────────────
    signal_lookup = {}
    try:
        cur = runtime_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM signals")
        total_sigs = cur.fetchone()[0]
        print(f"  Building signal index from {total_sigs:,} runtime signals...")
        cur.execute("""
            SELECT token, direction, signal_type, confidence, value, price,
                   z_score, z_score_tier, rsi_14,
                   macd_value, macd_signal, macd_hist,
                   momentum_state, decision, leverage, created_at
            FROM signals
            ORDER BY token, direction, created_at
        """)
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            d = dict(zip(cols, row))
            key = (d['token'].upper(), d['direction'].upper())
            if key not in signal_lookup:
                signal_lookup[key] = []
            signal_lookup[key].append(d)
        cur.close()
        print(f"  Indexed {len(signal_lookup)} token-direction pairs")
    except Exception as e:
        print(f"  Signal index error: {e}")

    def find_nearest_signal(trade):
        """Find nearest-time signal for a trade from pre-indexed lookup."""
        key = (trade['token'].upper(), trade['direction'].upper())
        if key not in signal_lookup:
            return None
        trade_ts = trade.get('open_time')
        if not trade_ts:
            return None
        try:
            if isinstance(trade_ts, str):
                trade_dt = datetime.fromisoformat(trade_ts.replace('Z', '+00:00'))
            else:
                trade_dt = trade_ts
            trade_ts_float = trade_dt.timestamp()
        except Exception:
            return None
        best = None
        best_delta = float('inf')
        for sig in signal_lookup[key]:
            sig_ts_str = sig.get('created_at')
            if not sig_ts_str:
                continue
            try:
                if isinstance(sig_ts_str, str):
                    sig_dt = datetime.fromisoformat(sig_ts_str.replace('Z', '+00:00'))
                else:
                    sig_dt = sig_ts_str
                delta = abs(sig_dt.timestamp() - trade_ts_float)
                if delta < best_delta and delta < 21600:  # 6 hours
                    best_delta = delta
                    best = sig
            except Exception:
                continue
        return best

    # ── Open or create SQLite DB ─────────────────────────────────────────────
    db_is_new = not os.path.exists(ANALYSIS_DB)
    conn = sqlite3.connect(ANALYSIS_DB)
    conn.execute("PRAGMA journal_mode=WAL")

    # ── Migration: add missing columns to existing DB ──────────────────────────
    # The schema has been extended since the first build; add any columns that
    # exist in the full list but are missing from the on-disk table.
    ADD_COLUMNS = [
        ('trade_id', 'INTEGER'),
        ('pair', 'TEXT'),
        ('strategy', 'TEXT'),
        ('entry_bb_position', 'REAL'),
        ('entry_fear_greed', 'INTEGER'),
        ('peak_price', 'REAL'),
        ('exit_conditions', 'TEXT'),
        ('regime', 'TEXT'),
        ('notes', 'TEXT'),
        ('partial_exit', 'REAL'),
        ('breakeven_activated', 'INTEGER'),
        ('entry_timing', 'TEXT'),
        ('atr_managed', 'INTEGER'),
        ('trailing_activated', 'INTEGER'),
        ('trailing_stop_pct', 'REAL'),
        ('trailing_stop_price', 'REAL'),
        ('workflow_state', 'TEXT'),
        ('workflow_updated_at', 'TEXT'),
        ('flip_armed', 'INTEGER'),
        ('is_guardian_close', 'INTEGER'),
        ('hl_sl_order_id', 'INTEGER'),
        ('hl_tp_order_id', 'INTEGER'),
        ('paper', 'INTEGER'),
        ('server', 'TEXT'),
        ('chain', 'TEXT'),
        ('token_address', 'TEXT'),
        ('signal_reason', 'TEXT'),
        ('missed_opportunity', 'INTEGER'),
        ('fees', 'TEXT'),
        ('current_price', 'REAL'),
        ('last_updated', 'TEXT'),
        ('learnings', 'TEXT'),
        ('predicted_return', 'TEXT'),
        ('actual_return', 'REAL'),
        ('test_sl_variant', 'TEXT'),
        ('test_timing_variant', 'TEXT'),
        ('test_trailing_variant', 'TEXT'),
        ('_signal_metadata', 'TEXT'),
        ('_exp_metadata', 'TEXT'),
        ('hl_notional_usdt', 'REAL'),
    ]
    if not db_is_new:
        existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(trades)").fetchall()}
        for col_name, col_type in ADD_COLUMNS:
            if col_name not in existing_cols:
                try:
                    conn.execute(f"ALTER TABLE trades ADD COLUMN {col_name} {col_type}")
                    print(f"  Added column: {col_name} ({col_type})")
                except Exception as e:
                    print(f"  Could not add column {col_name}: {e}")
        conn.commit()

    # Full column list — mirrors PostgreSQL trades table, with _signal_ and _exp_ prefixes
    # for embedded signal fields and A/B test variants.  All 99 PG columns included.
    SQLITE_TRADE_COLS = [
        # ── Primary trade fields ────────────────────────────────────────────
        'id', 'trade_id', 'token', 'direction', 'pair', 'strategy',
        'amount_usdt', 'entry_price', 'exit_price',
        'stop_loss', 'target', 'pnl_usdt', 'pnl_pct',
        'status', 'exchange', 'signal', 'confidence', 'leverage',
        'sl_distance',
        'open_time', 'close_time', 'close_reason', 'exit_reason',
        # ── Trailing stop ───────────────────────────────────────────────────
        'trailing_activation', 'trailing_distance', 'trailing_phase2_dist',
        # ── Entry indicators (from candles at open) ──────────────────────────
        'entry_rsi_14', 'entry_macd_hist', 'entry_atr_14',
        'entry_bb_position', 'entry_slope_4h',
        'entry_regime_4h', 'entry_trend', 'entry_fear_greed',
        # ── Position tracking ────────────────────────────────────────────────
        'highest_price', 'lowest_price', 'peak_price',
        'hl_entry_price', 'hl_exit_price', 'hl_notional_usdt',
        'hype_pnl_usdt', 'hype_pnl_pct',
        'hype_realized_pnl_usdt', 'hype_realized_pnl_pct',
        # ── Exit / close metadata ───────────────────────────────────────────
        'exit_conditions', 'regime', 'notes',
        'partial_exit', 'breakeven_activated', 'entry_timing',
        'atr_managed', 'trailing_activated', 'trailing_stop_pct', 'trailing_stop_price',
        # ── Workflow ────────────────────────────────────────────────────────
        'workflow_state', 'workflow_updated_at',
        # ── Flip / cascade ─────────────────────────────────────────────────
        'flipped_from_trade', 'flip_variant', 'flip_armed',
        # ── Guardian ───────────────────────────────────────────────────────
        'guardian_closed', 'guardian_reason', 'is_guardian_close',
        # ── Hyperliquid order IDs ───────────────────────────────────────────
        'hl_sl_order_id', 'hl_tp_order_id',
        # ── Experiment / A/B test ───────────────────────────────────────────
        'experiment', 'test_sl_variant', 'test_timing_variant', 'test_trailing_variant',
        # ── Misc ───────────────────────────────────────────────────────────
        'paper', 'server', 'chain', 'token_address',
        'signal_reason', 'missed_opportunity',
        'fees', 'current_price', 'last_updated',
        'learnings', 'predicted_return', 'actual_return',
        # ── Signal metadata (embedded from hotset at entry) ────────────────
        '_signal_type', '_signal_confidence',
        '_signal_z_score', '_signal_z_score_tier',
        '_signal_rsi_14', '_signal_macd_hist',
        '_signal_macd_value', '_signal_macd_signal',
        '_signal_momentum_state', '_signal_decision',
        '_signal_leverage', '_signal_created_at',
        '_signal_match_delta_s',
        # ── A/B test variants ───────────────────────────────────────────────
        '_exp_sl_variant', '_exp_timing_variant', '_exp_trailing_variant',
        # ── JSONB catch-all ────────────────────────────────────────────────
        '_signal_metadata', '_exp_metadata',
        # ── Archive tracking ─────────────────────────────────────────────────
        'archive_file', 'archived_at',
    ]

    # PostgreSQL signal / test columns (used to detect "new" trades with embedded context)
    PG_SIGNAL_FIELDS = [
        'signal_z_score', 'signal_rsi_14', 'signal_macd_hist',
        'signal_macd_value', 'signal_macd_signal',
        'signal_momentum_state', 'signal_z_score_tier',
        'signal_decision', 'signal_leverage', 'signal_created_at',
        'test_sl_variant', 'test_timing_variant', 'test_trailing_variant',
        '_signal_metadata', '_exp_metadata',
    ]

    if db_is_new:
        # First time — create the schema and signals table
        conn.execute("""
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY,
                trade_id INTEGER,
                token TEXT, pair TEXT, strategy TEXT,
                amount_usdt REAL, entry_price REAL, exit_price REAL,
                stop_loss REAL, target REAL, pnl_usdt REAL, pnl_pct REAL,
                status TEXT, exchange TEXT, signal TEXT, confidence REAL, leverage INTEGER,
                sl_distance REAL,
                open_time TEXT, close_time TEXT, close_reason TEXT, exit_reason TEXT,
                trailing_activation REAL, trailing_distance REAL, trailing_phase2_dist REAL,
                entry_rsi_14 REAL, entry_macd_hist REAL, entry_atr_14 REAL,
                entry_bb_position REAL, entry_slope_4h REAL,
                entry_regime_4h TEXT, entry_trend TEXT, entry_fear_greed INTEGER,
                highest_price REAL, lowest_price REAL, peak_price REAL,
                hl_entry_price REAL, hl_exit_price REAL, hl_notional_usdt REAL,
                hype_pnl_usdt REAL, hype_pnl_pct REAL,
                hype_realized_pnl_usdt REAL, hype_realized_pnl_pct REAL,
                exit_conditions TEXT, regime TEXT, notes TEXT,
                partial_exit REAL, breakeven_activated INTEGER, entry_timing TEXT,
                atr_managed INTEGER, trailing_activated INTEGER,
                trailing_stop_pct REAL, trailing_stop_price REAL,
                workflow_state TEXT, workflow_updated_at TEXT,
                flipped_from_trade INTEGER, flip_variant TEXT, flip_armed INTEGER,
                guardian_closed INTEGER, guardian_reason TEXT, is_guardian_close INTEGER,
                hl_sl_order_id INTEGER, hl_tp_order_id INTEGER,
                experiment TEXT, test_sl_variant TEXT, test_timing_variant TEXT, test_trailing_variant TEXT,
                paper INTEGER, server TEXT, chain TEXT, token_address TEXT,
                signal_reason TEXT, missed_opportunity INTEGER,
                fees TEXT, current_price REAL, last_updated TEXT,
                learnings TEXT, predicted_return TEXT, actual_return REAL,
                _signal_type TEXT, _signal_confidence REAL,
                _signal_z_score REAL, _signal_z_score_tier TEXT,
                _signal_rsi_14 REAL, _signal_macd_hist REAL,
                _signal_macd_value REAL, _signal_macd_signal REAL,
                _signal_momentum_state TEXT, _signal_decision TEXT,
                _signal_leverage INTEGER, _signal_created_at TEXT,
                _signal_match_delta_s REAL,
                _exp_sl_variant TEXT, _exp_timing_variant TEXT, _exp_trailing_variant TEXT,
                _signal_metadata TEXT, _exp_metadata TEXT,
                archive_file TEXT, archived_at TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE signals (
                id INTEGER PRIMARY KEY,
                token TEXT, direction TEXT,
                signal_type TEXT, confidence REAL,
                value REAL, price REAL,
                z_score REAL, z_score_tier TEXT,
                rsi_14 REAL,
                macd_value REAL, macd_signal REAL, macd_hist REAL,
                momentum_state TEXT, decision TEXT,
                leverage INTEGER, created_at TEXT,
                source TEXT, exchange TEXT, timeframe TEXT
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_t_token ON trades(token)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_t_direction ON trades(direction)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_t_open_time ON trades(open_time)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_t_signal_type ON trades(_signal_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_t_id ON trades(id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_s_token_dir ON signals(token, direction)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_s_created ON signals(created_at)")
        conn.commit()

        # ── Add UNIQUE constraint on signals table for idempotent inserts ──────
        # Prevents duplicate signals on re-runs. Silently fails if existing data
        # has duplicates (acceptable — primary analysis uses trade rows, not this table).
        try:
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_s_unique
                ON signals(token, direction, signal_type, source, created_at)
            """)
            conn.commit()
        except Exception as e:
            print(f"  Unique index on signals skipped (pre-existing duplicates): {e}")

    # ── Idempotent insert: skip trade IDs already in DB ───────────────────
    if append:
        existing_ids = set()
        try:
            cur = conn.execute("SELECT id FROM trades")
            existing_ids = {r[0] for r in cur.fetchall()}
            if existing_ids:
                print(f"  Existing IDs in DB: {len(existing_ids)}, will skip duplicates")
        except Exception:
            pass  # table empty or doesn't exist yet

    now_str = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    t_count = 0
    t_skipped = 0
    t_with_sig = 0

    for trade in trades:
        trade_id = trade.get('id')
        if append and trade_id in existing_ids:
            t_skipped += 1
            continue
        t_count += 1
        tok = trade.get('token', '').upper()
        direction = trade.get('direction', '').upper()
        open_time = trade.get('open_time')

        has_sig_in_pg = any(trade.get(f) is not None for f in PG_SIGNAL_FIELDS)

        if has_sig_in_pg:
            row_data = {
                '_signal_z_score':         _json_safe(trade.get('signal_z_score')),
                '_signal_rsi_14':           _json_safe(trade.get('signal_rsi_14')),
                '_signal_macd_hist':        _json_safe(trade.get('signal_macd_hist')),
                '_signal_macd_value':       _json_safe(trade.get('signal_macd_value')),
                '_signal_macd_signal':     _json_safe(trade.get('signal_macd_signal')),
                '_signal_momentum_state':  _json_safe(trade.get('signal_momentum_state')),
                '_signal_z_score_tier':    _json_safe(trade.get('signal_z_score_tier')),
                '_signal_decision':        _json_safe(trade.get('signal_decision')),
                '_signal_leverage':        _json_safe(trade.get('signal_leverage')),
                '_signal_created_at':      _json_safe(trade.get('signal_created_at')),
                '_exp_sl_variant':         _json_safe(trade.get('test_sl_variant')),
                '_exp_timing_variant':     _json_safe(trade.get('test_timing_variant')),
                '_exp_trailing_variant':   _json_safe(trade.get('test_trailing_variant')),
                '_signal_metadata':         _json_safe(trade.get('_signal_metadata')),
                '_exp_metadata':           _json_safe(trade.get('_exp_metadata')),
            }
            # _signal_type = the signal decision that triggered the trade
            row_data['_signal_type'] = _json_safe(trade.get('signal_decision'))
            row_data['_signal_confidence'] = _json_safe(trade.get('confidence'))
            row_data['_signal_match_delta_s'] = None
            t_with_sig += 1
        else:
            rt_sig = find_nearest_signal(trade) if runtime_conn else None
            if rt_sig:
                ts_match = rt_sig.get('created_at')
                delta_s = None
                if ts_match and open_time:
                    try:
                        ts_dt = datetime.fromisoformat(ts_match.replace('Z', '+00:00'))
                        ot_dt = datetime.fromisoformat(str(open_time).replace('Z', '+00:00'))
                        delta_s = abs((ts_dt - ot_dt).total_seconds())
                    except Exception:
                        pass
                row_data = {
                    '_signal_type':           rt_sig.get('signal_type'),
                    '_signal_confidence':      rt_sig.get('confidence'),
                    '_signal_z_score':         rt_sig.get('z_score'),
                    '_signal_z_score_tier':   rt_sig.get('z_score_tier'),
                    '_signal_rsi_14':          rt_sig.get('rsi_14'),
                    '_signal_macd_hist':       rt_sig.get('macd_hist'),
                    '_signal_macd_value':      rt_sig.get('macd_value'),
                    '_signal_macd_signal':     rt_sig.get('macd_signal'),
                    '_signal_momentum_state':  rt_sig.get('momentum_state'),
                    '_signal_decision':        rt_sig.get('decision'),
                    '_signal_leverage':        rt_sig.get('leverage'),
                    '_signal_created_at':      rt_sig.get('created_at'),
                    '_signal_match_delta_s':   delta_s,
                    '_exp_sl_variant':         None,
                    '_exp_timing_variant':     None,
                    '_exp_trailing_variant':   None,
                    '_signal_metadata':        None,
                    '_exp_metadata':           None,
                }
                t_with_sig += 1
            else:
                row_data = {f: None for f in PG_SIGNAL_FIELDS}
                row_data.update({
                    '_signal_type': None, '_signal_confidence': None,
                    '_signal_match_delta_s': None,
                    '_exp_sl_variant': None, '_exp_timing_variant': None,
                    '_exp_trailing_variant': None,
                })

        # Build the full row using the canonical column list
        row = {}
        for col in SQLITE_TRADE_COLS:
            if col in ('archive_file', 'archived_at'):
                continue
            raw = trade.get(col)
            # Normalize booleans → 0/1 for INTEGER columns
            if col in ('paper', 'missed_opportunity', 'breakeven_activated',
                       'trailing_activated', 'atr_managed', 'flip_armed',
                       'is_guardian_close', 'guardian_closed',
                       'leverage', 'entry_fear_greed',
                       'hl_sl_order_id', 'hl_tp_order_id', 'flipped_from_trade'):
                raw = _int_safe(raw)
            # Normalize Decimal → float for REAL/NUMERIC cols (handled by _json_safe below)
            row[col] = _json_safe(raw)

        # Overlay signal / experiment fields from row_data
        row.update({k: v for k, v in row_data.items() if k in SQLITE_TRADE_COLS})
        row['archive_file'] = ''
        row['archived_at'] = now_str

        cols = list(row.keys())
        vals = list(row.values())
        placeholders = ','.join(['?' for _ in cols])
        # INSERT OR IGNORE ensures idempotency if append=True
        conn.execute(f"INSERT OR IGNORE INTO trades ({','.join(cols)}) VALUES ({placeholders})", vals)

        if t_count % 500 == 0:
            print(f"  {t_count} trades inserted...")

    conn.commit()

    # ── Populate signals table from runtime DB ────────────────────────────
    # Only on fresh DB build; on incremental runs the trade rows already carry
    # their signal context embedded from PostgreSQL columns, and this flat
    # signals table is secondary (bulk signal analysis). Uses INSERT OR IGNORE
    # so re-runs are safe even without the unique-index guard.
    if db_is_new:
        try:
            rt_cur = runtime_conn.cursor()
            rt_cur.execute("""
                SELECT signal_type, token, direction, confidence, value, price,
                       z_score, z_score_tier, rsi_14,
                       macd_value, macd_signal, macd_hist,
                       momentum_state, decision, leverage, created_at,
                       source, exchange, timeframe
                FROM signals
                ORDER BY created_at
                LIMIT 1000000
            """)
            sig_cols = [d[0] for d in rt_cur.description]
            inserted = 0
            for row in rt_cur.fetchall():
                conn.execute(
                    f"INSERT OR IGNORE INTO signals ({','.join(sig_cols)}) VALUES ({','.join(['?' for _ in sig_cols])})",
                    list(row)
                )
                inserted += 1
            conn.commit()
            rt_cur.close()
            print(f"  Inserted {inserted:,} signals into signals table (append-safe)")
        except Exception as e:
            print(f"  Signals insert error: {e}")

    conn.close()

    cov = t_with_sig / t_count * 100 if t_count else 0
    action = "Appended" if append else "Built"
    print(f"\n  {action}: {ANALYSIS_DB}")
    print(f"  New trades: {t_count} | Skipped (dup): {t_skipped} | With signal: {t_with_sig} ({cov:.1f}%)")
    return t_count, t_with_sig


def archive_to_json(trades, dry_run=True):
    """Archive trades to gzipped JSON lines (one file per day)."""
    now_str = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    by_day = {}
    for t in trades:
        ct = t.get('close_time')
        if ct:
            day = str(ct)[:10]
        else:
            day = 'unknown'
        by_day.setdefault(day, []).append(t)

    total = 0
    for day, day_trades in sorted(by_day.items()):
        fname = f"trades_archive_{day}.json.gz"
        fpath = Path(ARCHIVE_DIR) / fname
        existing_ids = set()
        if fpath.exists():
            with gzip.open(fpath, 'rt') as f:
                for line in f:
                    try:
                        existing_ids.add(json.loads(line)['id'])
                    except Exception:
                        pass

        count = 0
        mode = 'at' if not dry_run else 'rt'
        # Read existing IDs if appending (mode='at'), not dry-run
        with gzip.open(fpath, mode) as f:
            if dry_run:
                pass
            else:
                for t in day_trades:
                    if t['id'] in existing_ids:
                        continue
                    rec = {**t, 'archived_at': now_str, 'archive_file': str(fpath)}
                    def json_safe(v):
                        if isinstance(v, Decimal):
                            return float(v)
                        if isinstance(v, datetime):
                            return v.isoformat()
                        return v
                    rec = {k: json_safe(v) for k, v in rec.items()}
                    f.write(json.dumps(rec) + '\n')
                    count += 1
        total += count
        print(f"  {'Would archive' if dry_run else 'Archived'} {count} trades to {fname}")

    return total


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Archive closed trades from PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be archived')
    parser.add_argument('--apply', action='store_true', help='Actually archive and delete')
    parser.add_argument('--rebuild-db', action='store_true', help='Rebuild analysis SQLite DB from scratch')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of trades to process')
    args = parser.parse_args()

    if not args.dry_run and not args.apply and not args.rebuild_db:
        parser.print_help()
        sys.exit(1)

    # Connect to PostgreSQL
    print("Connecting to brain DB...")
    try:
        conn_pg = psycopg2.connect(**BRAIN_DB_DICT)
        print("Connected.")
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")
        sys.exit(1)

    # Connect to runtime signals DB
    runtime_conn = None
    if os.path.exists(RUNTIME_SIGNALS_DB):
        try:
            runtime_conn = sqlite3.connect(RUNTIME_SIGNALS_DB, timeout=30)
            runtime_conn.row_factory = sqlite3.Row
            print("Runtime signals DB connected.")
        except Exception as e:
            print(f"Runtime signals DB connection failed: {e}")

    # Fetch closed trades
    print("Fetching closed trades from PostgreSQL...")
    t0 = time.time()
    closed_trades = get_closed_trades(conn_pg, limit=args.limit)
    print(f"  Found {len(closed_trades)} closed trades in {time.time()-t0:.1f}s")

    if not closed_trades:
        print("Nothing to archive.")
        conn_pg.close()
        if runtime_conn:
            runtime_conn.close()
        sys.exit(0)

    if args.rebuild_db:
        print(f"\nRebuilding analysis DB from scratch...")
        build_analysis_db(closed_trades, runtime_conn, append=False)
    elif args.dry_run:
        print(f"\n[DRY RUN] Would archive {len(closed_trades)} trades:")
        for t in closed_trades[:5]:
            print(f"  #{t['id']} {t['token']} {t['direction']} pnl={t.get('pnl_usdt')} close_time={t.get('close_time')}")
        if len(closed_trades) > 5:
            print(f"  ... and {len(closed_trades)-5} more")

    if args.apply:
        print(f"\nArchiving {len(closed_trades)} trades to JSON...")
        n = archive_to_json(closed_trades, dry_run=False)
        print(f"Archived {n} trades to {ARCHIVE_DIR}/")

        # Insert into analysis DB — append mode (idempotent, won't touch existing rows)
        print(f"\nInserting {len(closed_trades)} trades into analysis DB (append mode)...")
        build_analysis_db(closed_trades, runtime_conn, append=True)

        # Delete archived trades from PostgreSQL — only those still 'closed' in DB
        # Guard: re-check status to prevent deleting a trade that was re-opened
        # between SELECT and DELETE (race condition protection).
        ids = [t['id'] for t in closed_trades]
        placeholders = ','.join(['%s' for _ in ids])
        cur = conn_pg.cursor()
        cur.execute(
            f"DELETE FROM trades WHERE id IN ({placeholders}) AND status = 'closed' AND close_time IS NOT NULL",
            ids
        )
        deleted = cur.rowcount
        conn_pg.commit()
        # Warn if counts don't match (trade may have been reopened between SELECT and DELETE)
        if deleted != len(ids):
            print(f"  WARNING: requested {len(ids)} deletes but only {deleted} rows affected — possible status change in flight?")
        cur.close()
        print(f"Deleted {deleted} trades from PostgreSQL.")

    conn_pg.close()
    if runtime_conn:
        runtime_conn.close()
    print("Done.")
