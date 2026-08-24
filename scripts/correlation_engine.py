#!/usr/bin/env python3
"""
correlation_engine.py — Statistical correlation engine for Hermes Trading System.

Builds real token pump chains, signal effectiveness matrices, and cadence patterns
from actual trade outcomes. NOT text mining — pure statistical associations.

Usage:
    # Bootstrap (first time — processes all trades)
    from correlation_engine import CorrelationEngine
    engine = CorrelationEngine()
    engine.ingest_all()
    print(engine.stats())

    # Query
    results = engine.next_tokens("DOGE")      # what tokens follow DOGE?
    rec = engine.should_trade("BLUR", "bb_bounce+")  # should I take this trade?

    # CLI
    python3 correlation_engine.py ingest        # bootstrap/re-ingest
    python3 correlation_engine.py decay         # daily decay pass
    python3 correlation_engine.py stats         # show engine health
    python3 correlation_engine.py query DOGE    # what follows DOGE?
    python3 correlation_engine.py signal SOL hl_copy_trader  # signal effectiveness
"""

import sqlite3
import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from collections import defaultdict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BRAIN_DIR = Path("/root/.hermes/brain")
CORRELATIONS_DB = BRAIN_DIR / "correlations.db"
TRADE_LOG_DB = BRAIN_DIR / "associative_memory.db"  # source of trade data

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_WINDOW_SECS = 1800       # 30 minutes
DECAY_RATE = 0.95                # per-day decay multiplier
PRIOR_WEIGHT = 10                # Bayesian prior weight
PRIOR_WIN_RATE = 0.50            # Bayesian prior: 50% base rate
MIN_CO_FIRES = 3                 # minimum co-fires to report a chain
MIN_CONFIDENCE_FOR_TRADE = 0.60
MIN_LIFT_FOR_SUGGEST = 1.3
MAX_AGE_DAYS = 60


class CorrelationEngine:
    """
    Statistical correlation engine that learns token pump chains and signal
    effectiveness from actual trade outcomes.
    """

    def __init__(self, db_path: str = str(CORRELATIONS_DB)):
        self.db_path = db_path
        self._init_db()

    # -----------------------------------------------------------------------
    # Schema
    # -----------------------------------------------------------------------
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS token_chains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_a TEXT NOT NULL,
                    token_b TEXT NOT NULL,
                    window_secs INTEGER DEFAULT 1800,
                    co_fires INTEGER DEFAULT 0,
                    b_total INTEGER DEFAULT 0,
                    b_wins_after_a INTEGER DEFAULT 0,
                    b_losses_after_a INTEGER DEFAULT 0,
                    b_pnl_after_a REAL DEFAULT 0.0,
                    win_rate REAL DEFAULT 0.0,
                    base_wr REAL DEFAULT 0.0,
                    lift REAL DEFAULT 0.0,
                    confidence REAL DEFAULT 0.0,
                    avg_pnl_after_a REAL DEFAULT 0.0,
                    first_seen TIMESTAMP,
                    last_seen TIMESTAMP,
                    UNIQUE(token_a, token_b, window_secs)
                );
                CREATE INDEX IF NOT EXISTS idx_chain_a ON token_chains(token_a);
                CREATE INDEX IF NOT EXISTS idx_chain_b ON token_chains(token_b);
                CREATE INDEX IF NOT EXISTS idx_chain_lift ON token_chains(lift DESC);
                CREATE INDEX IF NOT EXISTS idx_chain_conf ON token_chains(confidence DESC);

                CREATE TABLE IF NOT EXISTS signal_effectiveness (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    direction TEXT,
                    trades INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0.0,
                    win_rate REAL DEFAULT 0.0,
                    avg_pnl REAL DEFAULT 0.0,
                    confidence REAL DEFAULT 0.0,
                    last_seen TIMESTAMP,
                    UNIQUE(token, signal, direction)
                );
                CREATE INDEX IF NOT EXISTS idx_se_token ON signal_effectiveness(token);
                CREATE INDEX IF NOT EXISTS idx_se_signal ON signal_effectiveness(signal);
                CREATE INDEX IF NOT EXISTS idx_se_conf ON signal_effectiveness(confidence DESC);

                CREATE TABLE IF NOT EXISTS cadence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT UNIQUE NOT NULL,
                    hour_dist TEXT,
                    day_dist TEXT,
                    mean_hours_between REAL,
                    burstiness REAL,
                    total_trades INTEGER DEFAULT 0,
                    peak_hour_utc INTEGER,
                    peak_day TEXT,
                    last_updated TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS signal_chains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_a TEXT NOT NULL,
                    signal_b TEXT NOT NULL,
                    window_secs INTEGER DEFAULT 1800,
                    co_fires INTEGER DEFAULT 0,
                    b_total INTEGER DEFAULT 0,
                    b_wins_after_a INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0.0,
                    lift REAL DEFAULT 0.0,
                    confidence REAL DEFAULT 0.0,
                    last_seen TIMESTAMP,
                    UNIQUE(signal_a, signal_b, window_secs)
                );

                CREATE TABLE IF NOT EXISTS engine_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Add half_life_weight column if missing (migration)
            try:
                conn.execute("ALTER TABLE token_chains ADD COLUMN half_life_weight REAL DEFAULT 1.0")
            except Exception:
                pass  # column already exists

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    @staticmethod
    def _bayesian_confidence(n: int, observed_wr: float) -> float:
        if n == 0:
            return PRIOR_WIN_RATE
        return (PRIOR_WEIGHT * PRIOR_WIN_RATE + n * observed_wr) / (PRIOR_WEIGHT + n)

    @staticmethod
    def _parse_time(ts: str) -> Optional[datetime]:
        if not ts:
            return None
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.replace(tzinfo=None)  # strip tz for consistent naive comparisons
        except (ValueError, TypeError):
            pass
        try:
            return datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return None

    def _set_state(self, key: str, value: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO engine_state (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, datetime.utcnow().isoformat())
            )

    def _get_state(self, key: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT value FROM engine_state WHERE key = ?", (key,)).fetchone()
            return row[0] if row else None

    # -----------------------------------------------------------------------
    # Single Trade Ingestion (called from brain.py on trade close)
    # -----------------------------------------------------------------------
    def ingest_trade(self, token: str, signal: str, direction: str,
                     won: bool, pnl_pct: float, close_time: str):
        """
        Process a single closed trade. Updates all matrices incrementally.
        Called from brain.py close_trade(). Fail-open — never raises.
        """
        now_iso = close_time or datetime.utcnow().isoformat()
        won_int = 1 if won else 0

        try:
            conn = sqlite3.connect(self.db_path)
            try:
                # 1. Update signal effectiveness
                row = conn.execute(
                    "SELECT trades, wins, total_pnl FROM signal_effectiveness "
                    "WHERE token=? AND signal=? AND direction=?",
                    (token, signal, direction)
                ).fetchone()

                if row:
                    t, w, p = row
                    t += 1
                    w += won_int
                    p += pnl_pct
                    wr = w / t if t > 0 else 0.0
                    conf = self._bayesian_confidence(t, wr)
                    avg_pnl = p / t if t > 0 else 0.0
                    conn.execute(
                        "UPDATE signal_effectiveness SET trades=?, wins=?, losses=?, "
                        "total_pnl=?, win_rate=?, avg_pnl=?, confidence=?, last_seen=? "
                        "WHERE token=? AND signal=? AND direction=?",
                        (t, w, t - w, p, wr, avg_pnl, conf, now_iso,
                         token, signal, direction)
                    )
                else:
                    conf = self._bayesian_confidence(1, 1.0 if won else 0.0)
                    conn.execute(
                        "INSERT INTO signal_effectiveness "
                        "(token, signal, direction, trades, wins, losses, total_pnl, "
                        "win_rate, avg_pnl, confidence, last_seen) "
                        "VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)",
                        (token, signal, direction, won_int, 0 if won else 1,
                         pnl_pct, 1.0 if won else 0.0, pnl_pct, conf, now_iso)
                    )

                # 2. Find recent trades within window to update chains
                close_dt = self._parse_time(close_time)
                if close_dt:
                    window = timedelta(seconds=DEFAULT_WINDOW_SECS)
                    lookback = close_dt - window

                    # Read from SOURCE trade_log (associative_memory.db), not correlations.db
                    src_db = str(TRADE_LOG_DB)
                    if os.path.exists(src_db):
                        src_conn = sqlite3.connect(f"file:{src_db}?mode=ro", uri=True, timeout=5)
                        try:
                            # Get recent trades (excluding this token and test tokens)
                            recent = src_conn.execute(
                                "SELECT token, won, pnl_pct, close_time FROM trade_log "
                                "WHERE close_time IS NOT NULL AND close_time > ? "
                                "AND close_time <= ? AND token != ? "
                                "AND token NOT LIKE 'TEST%' AND token NOT LIKE 'HTT%'",
                                (lookback.isoformat(), close_dt.isoformat(), token)
                            ).fetchall()

                            # Get base WR for this token
                            base_row = src_conn.execute(
                                "SELECT COUNT(*), SUM(CASE WHEN won=1 THEN 1 ELSE 0 END) "
                                "FROM trade_log WHERE token=?", (token,)
                            ).fetchone()
                        finally:
                            src_conn.close()
                    else:
                        recent = []
                        base_row = None

                    base_wr = (base_row[1] or 0) / base_row[0] if base_row and base_row[0] > 0 else 0.5

                    for r in recent:
                        tok_a = r[0]  # earlier token
                        won_a = bool(r[1])
                        pnl_a = r[2]
                        dt_a_str = r[3]

                        # Build chain: tok_a → this token (tok_a fired first)
                        chain_row = conn.execute(
                            "SELECT id, co_fires, b_wins_after_a, b_pnl_after_a "
                            "FROM token_chains WHERE token_a=? AND token_b=? AND window_secs=?",
                            (tok_a, token, DEFAULT_WINDOW_SECS)
                        ).fetchone()

                        if chain_row:
                            cid, co, bw, bp = chain_row
                            co += 1
                            bw += won_int
                            bp += pnl_pct
                            wr_c = bw / co
                            lift = wr_c / base_wr if base_wr > 0 else 1.0
                            conf_c = self._bayesian_confidence(co, wr_c)
                            conn.execute(
                                "UPDATE token_chains SET co_fires=?, b_wins_after_a=?, "
                                "b_pnl_after_a=?, win_rate=?, lift=?, confidence=?, "
                                "b_total=?, last_seen=? WHERE id=?",
                                (co, bw, bp, wr_c, lift, conf_c, base_row[0] if base_row else 0,
                                 now_iso, cid)
                            )
                        else:
                            # New chain
                            conf_c = self._bayesian_confidence(1, 1.0 if won else 0.0)
                            conn.execute(
                                "INSERT INTO token_chains "
                                "(token_a, token_b, window_secs, co_fires, b_wins_after_a, "
                                "b_losses_after_a, b_pnl_after_a, b_total, win_rate, base_wr, "
                                "lift, confidence, avg_pnl_after_a, first_seen, last_seen) "
                                "VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (tok_a, token, DEFAULT_WINDOW_SECS, won_int,
                                 0 if won else 1, pnl_pct,
                                 base_row[0] if base_row else 0,
                                 1.0 if won else 0.0, base_wr,
                                 (1.0 if won else 0.0) / base_wr if base_wr > 0 else 1.0,
                                 conf_c, pnl_pct, dt_a_str, now_iso)
                            )

                # 3. Update cadence
                if close_dt:
                    hour = close_dt.hour
                    day_idx = close_dt.weekday()
                    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                                 "Friday", "Saturday", "Sunday"]

                    cad_row = conn.execute(
                        "SELECT id, hour_dist, day_dist, total_trades FROM cadence WHERE token=?",
                        (token,)
                    ).fetchone()

                    if cad_row:
                        cid, hd_json, dd_json, total = cad_row
                        total += 1
                        hd = json.loads(hd_json) if hd_json else [0.0] * 24
                        dd = json.loads(dd_json) if dd_json else [0.0] * 7
                        hd[hour] += 1
                        dd[day_idx] += 1
                        hd_sum = sum(hd) or 1
                        dd_sum = sum(dd) or 1
                        hd_norm = [x / hd_sum for x in hd]
                        dd_norm = [x / dd_sum for x in dd]
                        peak_hour = hd.index(max(hd))
                        peak_day = day_names[dd.index(max(dd))]
                        conn.execute(
                            "UPDATE cadence SET hour_dist=?, day_dist=?, total_trades=?, "
                            "peak_hour_utc=?, peak_day=?, last_updated=? WHERE id=?",
                            (json.dumps(hd_norm), json.dumps(dd_norm), total,
                             peak_hour, peak_day, now_iso, cid)
                        )
                    else:
                        hd = [0.0] * 24
                        dd = [0.0] * 7
                        hd[hour] = 1
                        dd[day_idx] = 1
                        conn.execute(
                            "INSERT INTO cadence (token, hour_dist, day_dist, total_trades, "
                            "peak_hour_utc, peak_day, last_updated) VALUES (?, ?, ?, 1, ?, ?, ?)",
                            (token, json.dumps(hd), json.dumps(dd),
                             hour,
                             day_names[day_idx], now_iso)
                        )

                conn.commit()
            finally:
                conn.close()
        except Exception:
            # Fail-open: never block trade close
            pass

    # -----------------------------------------------------------------------
    # Bulk Ingestion (efficient — loads all trades, processes in memory)
    # -----------------------------------------------------------------------
    def ingest_all(self):
        """
        Bulk ingest all trades from trade_log. Idempotent.
        Uses sliding window for O(n) chain building instead of O(n²).
        """
        last_time = self._get_state("last_ingest_time")
        print(f"[ingest] Last ingest: {last_time or 'never (first run)'}")

        source_db = str(TRADE_LOG_DB)
        if not os.path.exists(source_db):
            print(f"[ingest] ERROR: Source DB not found: {source_db}")
            return

        # Load all trades
        conn_src = sqlite3.connect(f"file:{source_db}?mode=ro", uri=True, timeout=10)
        try:
            if last_time:
                rows = conn_src.execute("""
                    SELECT token, signal, direction, won, pnl_pct, close_time
                    FROM trade_log
                    WHERE close_time > ? AND token NOT LIKE 'TEST%' AND token NOT LIKE 'HTT%'
                    ORDER BY close_time
                """, (last_time,)).fetchall()
            else:
                rows = conn_src.execute("""
                    SELECT token, signal, direction, won, pnl_pct, close_time
                    FROM trade_log
                    WHERE token NOT LIKE 'TEST%' AND token NOT LIKE 'HTT%'
                    ORDER BY close_time
                """).fetchall()
        finally:
            conn_src.close()

        if not rows:
            print("[ingest] No new trades to process.")
            return

        print(f"[ingest] Processing {len(rows)} trades...")

        # Parse and sort by time
        trades = []
        for token, signal, direction, won, pnl_pct, close_time in rows:
            dt = self._parse_time(close_time)
            if dt:
                # Make naive for comparison
                if dt.tzinfo:
                    dt = dt.replace(tzinfo=None)
                trades.append((dt, token, signal or "unknown", direction or "unknown",
                               bool(won), pnl_pct or 0.0, close_time))

        trades.sort(key=lambda x: x[0])
        print(f"[ingest] {len(trades)} trades with valid timestamps")

        if not trades:
            print("[ingest] No trades with valid timestamps after parsing.")
            self._set_state("last_ingest_time", rows[-1][5] if rows else "")
            self._set_state("total_trades_processed", "0")
            return

        # --- Build token chains using sliding window ---
        print("[ingest] Building token chains...")
        chain_counts = defaultdict(lambda: {
            'co_fires': 0, 'b_wins': 0, 'b_losses': 0, 'b_pnl': 0.0,
            'first_seen': None, 'last_seen': None
        })

        window = timedelta(seconds=DEFAULT_WINDOW_SECS)
        j_start = 0

        for i in range(len(trades)):
            dt_i, tok_i = trades[i][0], trades[i][1]

            # Advance j_start past old trades
            while j_start < i and (dt_i - trades[j_start][0]) > window:
                j_start += 1

            # Look backward: trades[j_start..i-1] are within window of i
            for j in range(j_start, i):
                dt_j, tok_j = trades[j][0], trades[j][1]
                if tok_j == tok_i:
                    continue

                won_i = trades[i][4]
                pnl_i = trades[i][5]

                # j → i (j fires first, i follows)
                key_fwd = (tok_j, tok_i)
                chain_counts[key_fwd]['co_fires'] += 1
                chain_counts[key_fwd]['b_wins'] += 1 if won_i else 0
                chain_counts[key_fwd]['b_losses'] += 0 if won_i else 1
                chain_counts[key_fwd]['b_pnl'] += pnl_i
                if not chain_counts[key_fwd]['first_seen']:
                    chain_counts[key_fwd]['first_seen'] = trades[j][6]
                chain_counts[key_fwd]['last_seen'] = trades[i][6]

        # NOTE: No forward pass needed — the backward pass above already captures
        # ALL ordered pairs (j→i where j<i in time). Each unique (A,B) pair where
        # A fires before B within the window is counted exactly once.

        print(f"[ingest] {len(chain_counts)} unique chain pairs found")

        # --- Compute base WR for each token ---
        token_stats = defaultdict(lambda: {'total': 0, 'wins': 0})
        for t in trades:
            tok = t[1]
            token_stats[tok]['total'] += 1
            token_stats[tok]['wins'] += 1 if t[4] else 0

        base_wrs = {}
        for tok, s in token_stats.items():
            base_wrs[tok] = s['wins'] / s['total'] if s['total'] > 0 else 0.5

        # --- Write chains to DB ---
        print("[ingest] Writing chains to DB...")
        conn = sqlite3.connect(self.db_path)
        try:
            for (tok_a, tok_b), d in chain_counts.items():
                co = d['co_fires']
                if co < 1:
                    continue
                wins = d['b_wins']
                pnl = d['b_pnl']
                wr = wins / co
                base = base_wrs.get(tok_b, 0.5)
                lift = wr / base if base > 0 else 1.0
                conf = self._bayesian_confidence(co, wr)
                avg_pnl = pnl / co

                # b_total for this token
                b_total = token_stats.get(tok_b, {}).get('total', 0)

                conn.execute("""
                    INSERT INTO token_chains
                        (token_a, token_b, window_secs, co_fires, b_wins_after_a,
                         b_losses_after_a, b_pnl_after_a, b_total, win_rate, base_wr,
                         lift, confidence, avg_pnl_after_a, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(token_a, token_b, window_secs) DO UPDATE SET
                        co_fires = ?, b_wins_after_a = ?, b_losses_after_a = ?,
                        b_pnl_after_a = ?, b_total = ?, win_rate = ?, base_wr = ?,
                        lift = ?, confidence = ?, avg_pnl_after_a = ?, last_seen = ?
                """, (
                    tok_a, tok_b, DEFAULT_WINDOW_SECS, co, wins, co - wins, pnl,
                    b_total, wr, base, lift, conf, avg_pnl,
                    d['first_seen'], d['last_seen'],
                    # Update values (same)
                    co, wins, co - wins, pnl, b_total, wr, base, lift, conf, avg_pnl, d['last_seen']
                ))
            conn.commit()
        finally:
            conn.close()

        # --- Build signal effectiveness ---
        print("[ingest] Building signal effectiveness...")
        sig_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0.0, 'last_time': None})
        for t in trades:
            key = (t[1], t[2], t[3])  # token, signal, direction
            sig_stats[key]['trades'] += 1
            sig_stats[key]['wins'] += 1 if t[4] else 0
            sig_stats[key]['pnl'] += t[5]
            sig_stats[key]['last_time'] = t[6]  # per-combo last trade time

        conn = sqlite3.connect(self.db_path)
        try:
            for (token, signal, direction), s in sig_stats.items():
                t, w, p = s['trades'], s['wins'], s['pnl']
                last_t = s['last_time']

                # On first ingest (no existing row): INSERT with raw values
                # On incremental (existing row): ACCUMULATE with excluded
                conn.execute("""
                    INSERT INTO signal_effectiveness
                        (token, signal, direction, trades, wins, losses, total_pnl,
                         win_rate, avg_pnl, confidence, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(token, signal, direction) DO UPDATE SET
                        trades = trades + excluded.trades,
                        wins = wins + excluded.wins,
                        losses = losses + excluded.losses,
                        total_pnl = total_pnl + excluded.total_pnl,
                        win_rate = (wins + excluded.wins) * 1.0 / (trades + excluded.trades),
                        avg_pnl = (total_pnl + excluded.total_pnl) / (trades + excluded.trades),
                        confidence = ?,
                        last_seen = CASE WHEN excluded.last_seen > last_seen
                                          THEN excluded.last_seen ELSE last_seen END
                """, (
                    token, signal, direction, t, w, t - w, p,
                    w / t if t > 0 else 0.0,        # win_rate (insert)
                    p / t if t > 0 else 0.0,        # avg_pnl (insert)
                    self._bayesian_confidence(t, w / t if t > 0 else 0.0),
                    last_t,
                    # Recalculate confidence with accumulated totals
                    # (computed after accumulate: we need old+new totals)
                    0.0  # placeholder — will fix below
                ))

                # Recompute confidence with full accumulated stats
                row = conn.execute(
                    "SELECT trades, wins, total_pnl FROM signal_effectiveness "
                    "WHERE token=? AND signal=? AND direction=?",
                    (token, signal, direction)
                ).fetchone()
                if row:
                    full_t, full_w, full_p = row
                    full_wr = full_w / full_t if full_t > 0 else 0.0
                    full_conf = self._bayesian_confidence(full_t, full_wr)
                    full_avg = full_p / full_t if full_t > 0 else 0.0
                    conn.execute(
                        "UPDATE signal_effectiveness SET confidence=?, avg_pnl=? "
                        "WHERE token=? AND signal=? AND direction=?",
                        (full_conf, full_avg, token, signal, direction)
                    )
            conn.commit()
        finally:
            conn.close()

        # --- Build cadence ---
        print("[ingest] Building cadence patterns...")
        cadence_data = defaultdict(lambda: {
            'hours': [0] * 24, 'days': [0] * 7, 'times': [], 'last_time': None
        })
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for t in trades:
            tok = t[1]
            dt = t[0]
            cadence_data[tok]['hours'][dt.hour] += 1
            cadence_data[tok]['days'][dt.weekday()] += 1
            cadence_data[tok]['times'].append(dt)
            cadence_data[tok]['last_time'] = t[6]  # per-token last trade time

        conn = sqlite3.connect(self.db_path)
        try:
            for tok, cd in cadence_data.items():
                hours = cd['hours']
                days = cd['days']
                total = sum(hours)
                if total == 0:
                    continue

                hour_norm = [h / total for h in hours]
                day_norm = [d / total for d in days]
                peak_hour = hours.index(max(hours))
                peak_day = day_names[days.index(max(days))]
                last_t = cd['last_time']

                # Burstiness: stdev/mean of inter-trade intervals
                times = sorted(cd['times'])
                mean_h = 0.0
                burst = 0.0
                if len(times) >= 2:
                    diffs = [(times[i+1] - times[i]).total_seconds() / 3600
                             for i in range(len(times) - 1)]
                    mean_h = sum(diffs) / len(diffs) if diffs else 0
                    if mean_h > 0:
                        var = sum((d - mean_h) ** 2 for d in diffs) / len(diffs)
                        burst = (var ** 0.5) / mean_h

                conn.execute("""
                    INSERT INTO cadence (token, hour_dist, day_dist, mean_hours_between,
                        burstiness, total_trades, peak_hour_utc, peak_day, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(token) DO UPDATE SET
                        hour_dist = ?, day_dist = ?, mean_hours_between = ?,
                        burstiness = ?, total_trades = ?, peak_hour_utc = ?,
                        peak_day = ?, last_updated = ?
                """, (
                    tok, json.dumps(hour_norm), json.dumps(day_norm), mean_h, burst,
                    total, peak_hour, peak_day, last_t,
                    json.dumps(hour_norm), json.dumps(day_norm), mean_h, burst,
                    total, peak_hour, peak_day, last_t
                ))
            conn.commit()
        finally:
            conn.close()

        # --- Update state ---
        self._set_state("last_ingest_time", trades[-1][6])
        self._set_state("total_trades_processed", str(len(trades)))
        self._set_state("last_ingest_run", datetime.utcnow().isoformat())

        print(f"[ingest] Done. {len(trades)} trades → {len(chain_counts)} chains, "
              f"{len(sig_stats)} signal combos, {len(cadence_data)} token cadences")

    # -----------------------------------------------------------------------
    # Queries
    # -----------------------------------------------------------------------
    def next_tokens(self, fired_token: str, k: int = 5) -> list:
        """What tokens tend to fire AFTER this one?"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT token_b, co_fires, win_rate, base_wr, lift, confidence,
                       avg_pnl_after_a, b_total, last_seen
                FROM token_chains
                WHERE token_a = ? AND co_fires >= ?
                ORDER BY confidence * lift DESC
                LIMIT ?
            """, (fired_token, MIN_CO_FIRES, k)).fetchall()
            return [dict(r) for r in rows]

    def prev_tokens(self, following_token: str, k: int = 5) -> list:
        """What tokens tend to fire BEFORE this one?"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT token_a, co_fires, win_rate, base_wr, lift, confidence,
                       avg_pnl_after_a, b_total, last_seen
                FROM token_chains
                WHERE token_b = ? AND co_fires >= ?
                ORDER BY confidence * lift DESC
                LIMIT ?
            """, (following_token, MIN_CO_FIRES, k)).fetchall()
            return [dict(r) for r in rows]

    def token_correlations(self, token: str, k: int = 10) -> list:
        """All tokens correlated with this token (both directions)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            as_follower = conn.execute("""
                SELECT token_a as other_token, 'follows' as direction,
                       co_fires, win_rate, lift, confidence, avg_pnl_after_a
                FROM token_chains WHERE token_b = ? AND co_fires >= ?
                ORDER BY confidence * lift DESC LIMIT ?
            """, (token, MIN_CO_FIRES, k)).fetchall()

            as_leader = conn.execute("""
                SELECT token_b as other_token, 'leads_to' as direction,
                       co_fires, win_rate, lift, confidence, avg_pnl_after_a
                FROM token_chains WHERE token_a = ? AND co_fires >= ?
                ORDER BY confidence * lift DESC LIMIT ?
            """, (token, MIN_CO_FIRES, k)).fetchall()

            results = [dict(r) for r in as_follower] + [dict(r) for r in as_leader]
            results.sort(key=lambda x: x['confidence'] * x['lift'], reverse=True)
            return results[:k]

    def next_signals(self, fired_signal: str, k: int = 5) -> list:
        """What signals tend to fire after this signal? (signal co-occurrence)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT signal_b, co_fires, win_rate, lift, confidence, last_seen
                FROM signal_chains
                WHERE signal_a = ? AND co_fires >= ?
                ORDER BY confidence * lift DESC
                LIMIT ?
            """, (fired_signal, MIN_CO_FIRES, k)).fetchall()
            return [dict(r) for r in rows]

    def signal_effectiveness(self, token: str = None, signal: str = None,
                             min_n: int = 3) -> list:
        """Look up signal performance."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conditions = ["trades >= ?"]
            params = [min_n]
            if token:
                conditions.append("token = ?")
                params.append(token)
            if signal:
                conditions.append("signal = ?")
                params.append(signal)

            where = " AND ".join(conditions)
            rows = conn.execute(f"""
                SELECT token, signal, direction, trades, wins, win_rate,
                       confidence, avg_pnl, last_seen
                FROM signal_effectiveness WHERE {where}
                ORDER BY confidence * win_rate DESC
            """, params).fetchall()
            return [dict(r) for r in rows]

    def best_signals_for_token(self, token: str, min_n: int = 3) -> list:
        return self.signal_effectiveness(token=token, min_n=min_n)

    def should_trade(self, token: str, signal: str = None) -> dict:
        """Main entry point: should I take this trade?"""
        result = {
            'recommendation': 'NEUTRAL',
            'confidence': 0.0,
            'reason': 'No data',
            'chain_signals': [],
            'signal_wr': None,
            'base_wr': 0.5,
        }

        # Get base WR
        if os.path.exists(TRADE_LOG_DB):
            try:
                with sqlite3.connect(f"file:{TRADE_LOG_DB}?mode=ro", uri=True, timeout=5) as conn:
                    row = conn.execute(
                        "SELECT COUNT(*), SUM(CASE WHEN won=1 THEN 1 ELSE 0 END) "
                        "FROM trade_log WHERE token=?",
                        (token,)
                    ).fetchone()
                    if row and row[0] > 0:
                        result['base_wr'] = (row[1] or 0) / row[0]
            except Exception:
                pass  # use default 0.5

        # Signal effectiveness
        if signal:
            sig_data = self.signal_effectiveness(token=token, signal=signal, min_n=1)
            if sig_data:
                s = sig_data[0]
                result['signal_wr'] = s['win_rate']
                result['confidence'] = s['confidence']

                if s['confidence'] >= MIN_CONFIDENCE_FOR_TRADE:
                    if s['win_rate'] >= 0.60:
                        result['recommendation'] = 'TRADE'
                        result['reason'] = (f"{token} × {signal}: {s['win_rate']:.0%} WR "
                                            f"(n={s['trades']}, conf={s['confidence']:.2f})")
                    elif s['win_rate'] <= 0.35:
                        result['recommendation'] = 'AVOID'
                        result['reason'] = (f"{token} × {signal}: {s['win_rate']:.0%} WR — "
                                            f"losing signal (n={s['trades']})")

        # Chain signals
        chains = self.next_tokens(token, k=3)
        result['chain_signals'] = chains

        if chains:
            best = chains[0]
            if best['lift'] > MIN_LIFT_FOR_SUGGEST and best['confidence'] > 0.55:
                note = (f" → {best['token_b']} tends to follow "
                        f"({best['win_rate']:.0%} WR, {best['lift']:.1f}x lift)")
                if result['recommendation'] == 'NEUTRAL':
                    result['recommendation'] = 'TRADE'
                    result['confidence'] = best['confidence']
                    result['reason'] = f"Chain signal: {note}"
                elif result['recommendation'] == 'TRADE':
                    result['reason'] += note

        return result

    # -----------------------------------------------------------------------
    # Maintenance
    # -----------------------------------------------------------------------
    def apply_decay(self):
        """Apply daily decay. Half-life: 14 days."""
        with sqlite3.connect(self.db_path) as conn:
            now = datetime.utcnow().replace(tzinfo=None)  # naive for comparison
            rows = conn.execute("SELECT id, last_seen, co_fires, base_wr, win_rate FROM token_chains").fetchall()
            pruned = 0
            updated = 0
            for cid, last_seen_str, co_fires, base_wr, wr in rows:
                last_seen = self._parse_time(last_seen_str)
                if not last_seen:
                    continue
                days = (now - last_seen).days
                if days <= 0:
                    continue
                decay = DECAY_RATE ** days
                effective = co_fires * decay
                if effective < 2.0:
                    conn.execute("DELETE FROM token_chains WHERE id=?", (cid,))
                    pruned += 1
                else:
                    decayed_wr = base_wr + (wr - base_wr) * decay
                    conn.execute("UPDATE token_chains SET win_rate=? WHERE id=?", (decayed_wr, cid))
                    updated += 1

            # Prune old signal effectiveness
            rows = conn.execute("SELECT id, last_seen, trades FROM signal_effectiveness").fetchall()
            sig_pruned = 0
            for sid, last_seen_str, trades in rows:
                last_seen = self._parse_time(last_seen_str)
                if not last_seen:
                    continue
                days = (now - last_seen).days
                if days > 0:
                    effective = trades * (DECAY_RATE ** days)
                    if effective < 2.0:
                        conn.execute("DELETE FROM signal_effectiveness WHERE id=?", (sid,))
                        sig_pruned += 1

            self._set_state("last_decay_run", now.isoformat())
            print(f"[decay] Updated {updated} chains, pruned {pruned} dead chains, {sig_pruned} dead signals")

    def prune(self, min_co_fires: int = MIN_CO_FIRES, max_age_days: int = MAX_AGE_DAYS):
        """Remove chains with too few observations or too old."""
        with sqlite3.connect(self.db_path) as conn:
            cutoff = (datetime.utcnow() - timedelta(days=max_age_days)).isoformat()
            r1 = conn.execute("DELETE FROM token_chains WHERE co_fires < ?", (min_co_fires,)).rowcount
            r2 = conn.execute("DELETE FROM token_chains WHERE last_seen < ?", (cutoff,)).rowcount
            r3 = conn.execute("DELETE FROM signal_effectiveness WHERE trades < ?", (min_co_fires,)).rowcount
            print(f"[prune] Removed {r1} low-count chains, {r2} old chains, {r3} low-count signals")

    def stats(self) -> dict:
        """Engine health summary."""
        with sqlite3.connect(self.db_path) as conn:
            chains = conn.execute("SELECT COUNT(*) FROM token_chains").fetchone()[0]
            signals = conn.execute("SELECT COUNT(*) FROM signal_effectiveness").fetchone()[0]
            cadences = conn.execute("SELECT COUNT(*) FROM cadence").fetchone()[0]
            covered = conn.execute(
                "SELECT COUNT(DISTINCT token_a) FROM token_chains WHERE co_fires >= 3"
            ).fetchone()[0]
            top_chains = conn.execute("""
                SELECT token_a, token_b, co_fires, win_rate, lift, confidence, avg_pnl_after_a
                FROM token_chains WHERE co_fires >= 3
                ORDER BY confidence * lift DESC LIMIT 15
            """).fetchall()
            total = self._get_state("total_trades_processed") or "0"
            last_ingest = self._get_state("last_ingest_time") or "never"

            return {
                'total_chains': chains,
                'total_signals': signals,
                'total_cadences': cadences,
                'tokens_covered': covered,
                'total_trades_processed': int(total),
                'last_ingest': last_ingest,
                'top_chains': [
                    {'a': r[0], 'b': r[1], 'n': r[2], 'wr': f"{r[3]:.0%}",
                     'lift': f"{r[4]:.2f}x", 'conf': f"{r[5]:.2f}", 'pnl': f"{r[6]:+.3f}%"}
                    for r in top_chains
                ]
            }


# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python3 correlation_engine.py <command> [args]")
        print("Commands: ingest, decay, prune, stats, query <token>, signal <token> <signal>")
        sys.exit(1)

    cmd = sys.argv[1]
    engine = CorrelationEngine()

    if cmd == "ingest":
        engine.ingest_all()
        print(json.dumps(engine.stats(), indent=2))

    elif cmd == "decay":
        engine.apply_decay()
        engine.prune()
        print(json.dumps(engine.stats(), indent=2))

    elif cmd == "prune":
        engine.prune()
        print(json.dumps(engine.stats(), indent=2))

    elif cmd == "stats":
        print(json.dumps(engine.stats(), indent=2))

    elif cmd == "query":
        token = sys.argv[2] if len(sys.argv) > 2 else "BTC"
        print(f"\n=== What follows {token}? ===")
        results = engine.next_tokens(token, k=10)
        if not results:
            print("  No chain data found.")
        for r in results:
            print(f"  {token} → {r['token_b']:10s}  "
                  f"n={r['co_fires']:3d}  wr={r['win_rate']:.0%}  "
                  f"lift={r['lift']:.2f}x  conf={r['confidence']:.2f}  "
                  f"avg_pnl={r['avg_pnl_after_a']:+.3f}%")

        print(f"\n=== What leads to {token}? ===")
        results = engine.prev_tokens(token, k=10)
        if not results:
            print("  No chain data found.")
        for r in results:
            print(f"  {r['token_a']:10s} → {token}  "
                  f"n={r['co_fires']:3d}  wr={r['win_rate']:.0%}  "
                  f"lift={r['lift']:.2f}x  conf={r['confidence']:.2f}  "
                  f"avg_pnl={r['avg_pnl_after_a']:+.3f}%")

        print(f"\n=== Best signals for {token} ===")
        sigs = engine.best_signals_for_token(token, min_n=3)
        for s in sigs[:10]:
            print(f"  {s['signal']:40s}  {s['direction']:5s}  "
                  f"n={s['trades']:3d}  wr={s['win_rate']:.0%}  "
                  f"conf={s['confidence']:.2f}  pnl={s['avg_pnl']:+.3f}%")

    elif cmd == "signal":
        if len(sys.argv) < 4:
            print("Usage: python3 correlation_engine.py signal <token> <signal>")
            sys.exit(1)
        token, signal = sys.argv[2], sys.argv[3]
        results = engine.signal_effectiveness(token=token, signal=signal)
        if not results:
            print(f"No data for {token} × {signal}")
        for r in results:
            print(f"  {r['token']} × {r['signal']} ({r['direction']}): "
                  f"n={r['trades']}  wr={r['win_rate']:.0%}  "
                  f"conf={r['confidence']:.2f}  pnl={r['avg_pnl']:+.3f}%")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
