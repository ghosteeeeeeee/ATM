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
                   -- FIX 2026-10-04 (gap-hunt GAP A): trades.regime is a DIFFERENT
                   -- concept (roughly 96 pct NEUTRAL — market-bias scanner vocabulary)
                   -- while the live classifier + t5 lookups use volatility_regime
                   -- (EXTREME/HIGH/NORMAL/FLAT). Old COALESCE(regime, volatility_regime)
                   -- lumped 285/513 cells into a fake NEUTRAL bucket (36/54 admitted),
                   -- making the primary store regime-blind. Prefer volatility_regime;
                   -- NULLIF strips empty strings. (No bare percent signs in SQL comments
                   -- — psycopg2 parses them as parameter placeholders.)
                   COALESCE(NULLIF(volatility_regime, ''), NULLIF(regime, ''), 'UNKNOWN') AS regime,
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


def fetch_signal_outcomes(days):
    """signal_type-keyed outcomes from runtime SQLite — covers live families
    (support_resistance, hmacd_mtf, ichimoku, ...) that trades.signal source-form
    keys miss. Percent units (pnl_pct)."""
    from paths import RUNTIME_DB
    if not os.path.exists(RUNTIME_DB):
        return []
    conn = sqlite3.connect(RUNTIME_DB)
    try:
        rows = conn.execute("""
            SELECT signal_type, direction, COALESCE(regime, 'UNKNOWN'),
                   is_win, pnl_pct
            FROM signal_outcomes
            WHERE closed_at > datetime('now', ?)
              AND signal_type IS NOT NULL
        """, (f'-{days} days',)).fetchall()
        return rows
    finally:
        conn.close()


def compute_outcome_cells(rows):
    """Signal_type-keyed cells from signal_outcomes (percent units, same backoff)."""
    K = CELL_STATS_SHRINK_K
    MIN_N = CELL_STATS_MIN_N_CELL
    cells, signals = {}, {}
    glob = {'n': 0, 'wins': 0, 'pnl': 0.0}
    for stype, direction, regime, is_win, pnl_pct in rows:
        stype = (stype or 'UNKNOWN').strip()
        direction = (direction or 'UNKNOWN').strip().upper()
        regime = (regime or 'UNKNOWN').strip().upper()
        win = int(is_win or 0)
        pnl = float(pnl_pct or 0)
        for store, key in ((cells, (stype, direction, regime)),
                           (signals, (stype, direction)),
                           (glob, None)):
            agg = store if key is None else store.setdefault(
                key, {'n': 0, 'wins': 0, 'pnl': 0.0})
            agg['n'] += 1
            agg['wins'] += win
            agg['pnl'] += pnl
    glob_wr = (glob['wins'] / glob['n']) if glob['n'] else 0.0
    glob_avg = (glob['pnl'] / glob['n']) if glob['n'] else 0.0
    sig_f = {k: {'n': v['n'], 'wr': (v['wins'] / v['n']) if v['n'] else 0.0,
                 'avg': (v['pnl'] / v['n']) if v['n'] else 0.0}
             for k, v in signals.items()}
    out = []
    for (stype, direction, regime), agg in cells.items():
        n = agg['n']
        wr = (agg['wins'] / n) if n else 0.0
        avg = (agg['pnl'] / n) if n else 0.0
        sig = sig_f.get((stype, direction))
        if n >= MIN_N:
            admission, wr_b, avg_b = 'cell', wr, avg
        elif sig and sig['n'] >= 5:
            wr_b = (n * wr + K * sig['wr']) / (n + K)
            avg_b = (n * avg + K * sig['avg']) / (n + K)
            admission = 'blend' if n >= 10 else 'signal'
            if n < 10:
                wr_b, avg_b = sig['wr'], sig['avg']
        else:
            wr_b = (n * wr + K * glob_wr) / (n + K) if n else glob_wr
            avg_b = (n * avg + K * glob_avg) / (n + K) if n else glob_avg
            admission = 'global'
        out.append({'signal': stype, 'direction': direction, 'regime': regime,
                    'n': n, 'wins': agg['wins'], 'wr_raw': round(wr, 4),
                    'wr_blended': round(wr_b, 4), 'avg_pnl_pct': round(avg_b, 4),
                    'total_pnl_pct': round(agg['pnl'], 2), 'admission': admission,
                    'tradeable': bool(n >= MIN_N and wr_b >= 0.60)})
    return out


def backfill_mfe_mae(days=7):
    """Nightly repair: fill NULL mfe_pct/mae_pct on recently closed brain trades
    from highest_price/lowest_price (direction-aware). Brain-CLI-routed closes
    (profit_monster/cut_loser) don't compute MFE/MAE live — P0's backfill was
    one-time, so coverage decayed from 97% (RESOLV 16:33 close = NULL with all
    three prices present). One mechanism repairs every writer's gaps within 24h.
    Returns rows updated."""
    import psycopg2
    from _secrets import BRAIN_DB_DICT
    conn = None
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            UPDATE trades SET
              mfe_pct = CASE direction
                WHEN 'LONG' THEN ROUND(((highest_price - entry_price) / entry_price * 100)::numeric, 4)
                ELSE ROUND(((entry_price - lowest_price) / entry_price * 100)::numeric, 4) END,
              mae_pct = CASE direction
                WHEN 'LONG' THEN ROUND(((entry_price - lowest_price) / entry_price * 100)::numeric, 4)
                ELSE ROUND(((highest_price - entry_price) / entry_price * 100)::numeric, 4) END
            WHERE status='closed'
              AND close_time > NOW() - (%s || ' days')::interval
              AND mfe_pct IS NULL
              AND entry_price > 0
              AND ((direction='LONG' AND highest_price > 0 AND lowest_price > 0)
                OR (direction='SHORT' AND highest_price > 0 AND lowest_price > 0))
        """, (str(days),))
        n = cur.rowcount
        conn.commit()
        cur.close()
        return n
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


def write_store_st(cells_st, days):
    """Write signal_type-keyed outcome cells to cells_st table (same DB).
    Separate table: percent units (avg_pnl_pct), no MFE/MAE — never mixed
    with the USD-denominated cells table."""
    conn = sqlite3.connect(CELL_DB)
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cells_st (
                signal TEXT, direction TEXT, regime TEXT,
                n INTEGER, wins INTEGER, wr_raw REAL, wr_blended REAL,
                avg_pnl_pct REAL, total_pnl_pct REAL,
                admission TEXT, tradeable INTEGER,
                computed_at TEXT,
                PRIMARY KEY (signal, direction, regime))
        """)
        cur.execute("DELETE FROM cells_st")
        now = datetime.now(timezone.utc).isoformat()
        for c in cells_st:
            cur.execute("INSERT INTO cells_st VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (c['signal'], c['direction'], c['regime'], c['n'], c['wins'],
                         c['wr_raw'], c['wr_blended'], c['avg_pnl_pct'], c['total_pnl_pct'],
                         c['admission'], int(c['tradeable']), now))
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return len(cells_st)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=CELL_STATS_WINDOW_DAYS)
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    log(f'fetching {args.days}d closed trades from brain DB...')
    # nightly MFE/MAE repair first — cell quantiles need complete data
    n_rep = backfill_mfe_mae(days=7)
    if n_rep:
        log(f'MFE/MAE backfill: {n_rep} recent closes repaired (brain-CLI gap)')
    rows = fetch_trades(args.days)
    log(f'{len(rows)} trades fetched')
    if not rows:
        log('no trades — aborting (store untouched)')
        return 1

    cells, glob_f, _sig = compute_cells(rows)
    snap = write_store(cells, glob_f, args.days)

    # signal_type-keyed outcome cells (covers live families source-form keys miss)
    st_rows = fetch_signal_outcomes(args.days)
    if st_rows:
        cells_st = compute_outcome_cells(st_rows)
        n_st = write_store_st(cells_st, args.days)
        st_adm = sum(1 for c in cells_st if c['admission'] == 'cell')
        log(f'signal_type cells: {n_st} written ({st_adm} admitted), from {len(st_rows)} outcomes')
    else:
        log('signal_outcomes empty — cells_st not written')

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
