#!/usr/bin/env python3
"""
cell_stats.py — Trade Learning System P1: nightly hierarchical cell store.

Computes per-cell (signal x direction x regime) performance from the PostgreSQL
brain DB with Bayesian backoff, writes:
  - brain/cell_stats.db   (SQLite: cells table + meta table — the T2 store)
  - data/cell_stats_latest.json (snapshot for dashboards/brain_auditor)

Backoff policy (CEO 2026-10-04: cell admission n>=15, hierarchical shrinkage):
  n >= 15            -> cell stats trusted (admission='cell')
  10 <= n < 15       -> blend cell toward signal-level (admission='blend')
  5  <= n < 10       -> signal-level stats (admission='signal')
  n < 5              -> global stats (admission='global')
Blend = empirical-Bayes shrinkage: (n*cell + K*prior) / (n + K), K=10.

Freeze-safe: reads data only, changes no trading behavior. Tunables live here
with import-override from hermes_constants.py (add constants post-freeze).

Usage: python3 scripts/cell_stats.py [--days 90] [--quiet]
"""
import sys
import os
import json
import sqlite3
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

# ── Tunables (override via hermes_constants.py when added post-freeze) ────────
try:
    from hermes_constants import (
        CELL_STATS_WINDOW_DAYS,
        CELL_STATS_MIN_N_CELL,
        CELL_STATS_SHRINK_K,
    )
except ImportError:
    CELL_STATS_WINDOW_DAYS = 90     # lookback window
    CELL_STATS_MIN_N_CELL = 15      # CEO: cell admission threshold
    CELL_STATS_SHRINK_K = 10        # shrinkage strength toward prior level

CELL_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'cell_stats.db')
LATEST_JSON = os.path.join(HERMES_DATA, 'cell_stats_latest.json')


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [cell_stats] {msg}', flush=True)


def _pct(values, q):
    """q-th percentile (0-100) of a list; None if empty."""
    if not values:
        return None
    s = sorted(values)
    idx = min(len(s) - 1, max(0, int(round(q / 100.0 * (len(s) - 1)))))
    return round(s[idx], 4)


def fetch_trades(days):
    """Closed trades with full context from brain DB."""
    import psycopg2
    from _secrets import BRAIN_DB_DICT
    conn = None
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            SELECT signal, direction,
                   COALESCE(regime, volatility_regime, 'UNKNOWN') AS regime,
                   exit_reason, pnl_usdt, pnl_pct,
                   mfe_pct, mae_pct, entry_rsi_14, confidence
            FROM trades
            WHERE status = 'closed'
              AND close_time > NOW() - (%s || ' days')::interval
              AND pnl_usdt IS NOT NULL
        """, (str(days),))
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        if conn:
            conn.close()


def compute_cells(rows):
    """Aggregate rows into cell / signal-level / global stats with backoff."""
    K = CELL_STATS_SHRINK_K
    MIN_N = CELL_STATS_MIN_N_CELL

    cells = {}       # (signal, direction, regime) -> raw aggregates
    signals = {}     # (signal, direction) -> raw aggregates
    glob = {'n': 0, 'wins': 0, 'pnl': 0.0, 'pf_vals': [], 'mfe': [], 'mae': []}

    for signal, direction, regime, exit_reason, pnl_usdt, pnl_pct, mfe, mae, rsi, conf in rows:
        signal = (signal or 'UNKNOWN').strip()
        direction = (direction or 'UNKNOWN').strip().upper()
        regime = (regime or 'UNKNOWN').strip().upper()
        win = 1 if (pnl_usdt or 0) > 0 else 0

        for store, key in ((cells, (signal, direction, regime)),
                           (signals, (signal, direction)),
                           (glob, None)):
            agg = store if key is None else store.setdefault(
                key, {'n': 0, 'wins': 0, 'pnl': 0.0, 'pf_vals': [], 'mfe': [], 'mae': [],
                      'exits': {}})
            agg['n'] += 1
            agg['wins'] += win
            agg['pnl'] += float(pnl_usdt or 0)
            if pnl_pct is not None:
                agg['pf_vals'].append(float(pnl_pct))
            if mfe is not None:
                agg['mfe'].append(float(mfe))
            if mae is not None:
                agg['mae'].append(float(mae))
            if key is not None and exit_reason:
                er = exit_reason.split('_-_')[0][:40]  # guard long labels
                agg['exits'][er] = agg['exits'].get(er, 0) + 1

    def finish(agg):
        n = agg['n']
        wr = (agg['wins'] / n) if n else 0.0
        avg_pnl = (agg['pnl'] / n) if n else 0.0
        return {
            'n': n, 'wins': agg['wins'], 'wr': round(wr, 4),
            'total_pnl': round(agg['pnl'], 2), 'avg_pnl': round(avg_pnl, 4),
            'mfe_p25': _pct(agg['mfe'], 25), 'mfe_p50': _pct(agg['mfe'], 50),
            'mfe_p75': _pct(agg['mfe'], 75), 'mae_p25': _pct(agg['mae'], 25),
            'mae_p50': _pct(agg['mae'], 50),
            'exits': agg.get('exits', {}),
        }

    glob_f = finish(glob)
    sig_f = {k: finish(v) for k, v in signals.items()}

    out = []
    for (signal, direction, regime), agg in cells.items():
        c = finish(agg)
        sig = sig_f.get((signal, direction))
        n = c['n']
        if n >= MIN_N:
            admission, prior = 'cell', None
            wr_b, avg_b = c['wr'], c['avg_pnl']
        elif sig and sig['n'] >= 5:
            prior = sig
            wr_b = (n * c['wr'] + K * sig['wr']) / (n + K)
            avg_b = (n * c['avg_pnl'] + K * sig['avg_pnl']) / (n + K)
            admission = 'blend' if n >= 10 else 'signal'
            if n < 10:
                wr_b, avg_b = sig['wr'], sig['avg_pnl']
        else:
            prior = glob_f
            wr_b = (n * c['wr'] + K * glob_f['wr']) / (n + K) if n else glob_f['wr']
            avg_b = (n * c['avg_pnl'] + K * glob_f['avg_pnl']) / (n + K) if n else glob_f['avg_pnl']
            admission = 'global'

        out.append({
            'signal': signal, 'direction': direction, 'regime': regime,
            'n': n, 'wins': c['wins'], 'wr_raw': c['wr'],
            'wr_blended': round(wr_b, 4), 'avg_pnl_raw': c['avg_pnl'],
            'avg_pnl_blended': round(avg_b, 4), 'total_pnl': c['total_pnl'],
            'admission': admission,
            'tradeable': bool(n >= MIN_N and wr_b >= 0.60),
            'mfe_p25': c['mfe_p25'], 'mfe_p50': c['mfe_p50'], 'mfe_p75': c['mfe_p75'],
            'mae_p25': c['mae_p25'], 'mae_p50': c['mae_p50'],
            'signal_n': sig['n'] if sig else 0,
            'signal_wr': sig['wr'] if sig else None,
            'exits': c['exits'],
        })
    out.sort(key=lambda r: (-r['n'], r['signal']))
    return out, glob_f, sig_f


def write_store(cells, glob_f, days):
    """Persist to SQLite cell store + JSON snapshot."""
    os.makedirs(os.path.dirname(CELL_DB), exist_ok=True)
    conn = sqlite3.connect(CELL_DB)
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cells (
                signal TEXT, direction TEXT, regime TEXT,
                n INTEGER, wins INTEGER, wr_raw REAL, wr_blended REAL,
                avg_pnl_raw REAL, avg_pnl_blended REAL, total_pnl REAL,
                admission TEXT, tradeable INTEGER,
                mfe_p25 REAL, mfe_p50 REAL, mfe_p75 REAL,
                mae_p25 REAL, mae_p50 REAL,
                signal_n INTEGER, signal_wr REAL, exits_json TEXT,
                computed_at TEXT,
                PRIMARY KEY (signal, direction, regime))
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY, value TEXT)
        """)
        cur.execute("DELETE FROM cells")
        now = datetime.now(timezone.utc).isoformat()
        for c in cells:
            cur.execute("""
                INSERT INTO cells VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (c['signal'], c['direction'], c['regime'], c['n'], c['wins'],
                  c['wr_raw'], c['wr_blended'], c['avg_pnl_raw'], c['avg_pnl_blended'],
                  c['total_pnl'], c['admission'], int(c['tradeable']),
                  c['mfe_p25'], c['mfe_p50'], c['mfe_p75'], c['mae_p25'], c['mae_p50'],
                  c['signal_n'], c['signal_wr'], json.dumps(c['exits']), now))
        for k, v in (('computed_at', now), ('window_days', str(days)),
                     ('global_wr', str(glob_f['wr'])), ('global_n', str(glob_f['n'])),
                     ('cells_total', str(len(cells))),
                     ('cells_admitted', str(sum(1 for c in cells if c['admission'] == 'cell'))),
                     ('cells_tradeable', str(sum(1 for c in cells if c['tradeable'])))):
            cur.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (k, v))
        conn.commit()
        cur.close()
    finally:
        conn.close()

    snapshot = {
        'computed_at': now, 'window_days': days, 'global': glob_f,
        'cells_total': len(cells),
        'cells_admitted': sum(1 for c in cells if c['admission'] == 'cell'),
        'cells_tradeable': sum(1 for c in cells if c['tradeable']),
        'cells': cells,
    }
    tmp = LATEST_JSON + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(snapshot, f, indent=1)
    os.replace(tmp, LATEST_JSON)
    return snapshot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=CELL_STATS_WINDOW_DAYS)
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    log(f'fetching {args.days}d closed trades from brain DB...')
    rows = fetch_trades(args.days)
    log(f'{len(rows)} trades fetched')
    if not rows:
        log('no trades — aborting (store untouched)')
        return 1

    cells, glob_f, _sig = compute_cells(rows)
    snap = write_store(cells, glob_f, args.days)

    admitted = [c for c in cells if c['admission'] == 'cell']
    tradeable = [c for c in cells if c['tradeable']]
    log(f"cells={snap['cells_total']} admitted(n>={CELL_STATS_MIN_N_CELL})={snap['cells_admitted']} "
        f"tradeable(admitted & wr>={0.60})={snap['cells_tradeable']} "
        f"global_wr={glob_f['wr']:.3f} n={glob_f['n']}")
    if not args.quiet:
        log('top 10 admitted cells by total_pnl:')
        for c in sorted(admitted, key=lambda x: -x['total_pnl'])[:10]:
            log(f"  {c['signal'][:34]:34} {c['direction']:5} {c['regime']:8} "
                f"n={c['n']:3} wr={c['wr_raw']:.0%} pnl=${c['total_pnl']:+.2f} "
                f"wr_b={c['wr_blended']:.0%} tradeable={c['tradeable']}")
        log('top 5 bleeders among admitted:')
        for c in sorted(admitted, key=lambda x: x['total_pnl'])[:5]:
            log(f"  {c['signal'][:34]:34} {c['direction']:5} {c['regime']:8} "
                f"n={c['n']:3} wr={c['wr_raw']:.0%} pnl=${c['total_pnl']:+.2f}")
    log(f'store: {CELL_DB}')
    log(f'snapshot: {LATEST_JSON}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
