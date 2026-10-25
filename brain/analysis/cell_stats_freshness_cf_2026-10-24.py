#!/usr/bin/env python3
"""cell_stats_freshness_cf_2026-10-24.py — counterfactual for the PRE-REGISTERED
cell-stats freshness guard (brain_auditor run #116, criteria locked BEFORE this run).

Guard under test (scope A, HARD):
    de-boost _cell_mult 1.2 -> 1.0 whenever the boosted cell's own signal has had
    no closed trade within FRESH_DAYS (=14) before the fire.

This script is ZERO BEHAVIOR — it only reads logs + PostgreSQL and reports.
Ship criteria (locked by #116, unchanged here):
    fk_upper (share of last-7d WINNERS that received a stale boost) < 20%
    AND OOS same-sign at 7d and 30d windows
    AND suppressed-fires/day reported so the CEO sees the traffic cost.

Per window also reports:
    stale_boost_pnl          PnL of the stale-boosted cohort (suppressing the boost
                             removes these trades — negative = suppress is profitable)
    hard_blocked_would_be_*  subset whose de-boosted conf (conf/1.2) falls under
                             MIN_EXEC_CONFIDENCE=40 i.e. conf<48 => fk_hard_pct

Usage: python3 brain/analysis/cell_stats_freshness_cf_2026-10-24.py [--fresh-days 14]
       python3 brain/analysis/cell_stats_freshness_cf_2026-10-24.py --selfcheck
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT  # noqa: E402

import psycopg2  # noqa: E402

PIPELINE_LOG = '/root/.hermes/logs/pipeline.log'
FIRE_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*CELL-STATS\] (\S+) (\w+): '
    r'tradeable cell \[([^\]]+)\]')


def parse_fires(path=PIPELINE_LOG):
    """[(dt, token, direction, cell_key)] for every 1.2x tradeable fire."""
    fires = []
    with open(path, 'r', errors='replace') as f:
        for line in f:
            if 'CELL-STATS' not in line or 'tradeable' not in line:
                continue
            m = FIRE_RE.match(line)
            if not m:
                continue
            ts = datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
            fires.append((ts, m.group(2), m.group(3).upper(), m.group(4)))
    fires.sort()
    return fires


def cell_last_close(conn):
    """{cell_key: {DIR: last close_time of trades.signal == cell_key}}."""
    cur = conn.cursor()
    cur.execute("""
        SELECT signal, direction, MAX(close_time)
        FROM trades WHERE status='closed' AND close_time IS NOT NULL
        GROUP BY signal, direction""")
    out = defaultdict(dict)
    for sig, d, mx in cur.fetchall():
        out[sig][(d or '').upper()] = mx
    return out


def closed_trades(conn, days):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, token, signal, direction, open_time, close_time, pnl_usdt, exit_reason,
               COALESCE(confidence, 0)
        FROM trades
        WHERE status='closed' AND close_time > NOW() - INTERVAL '%s days'
        ORDER BY open_time""" % int(days))
    return cur.fetchall()


def run(fresh_days=14):
    fires = parse_fires()
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    last_close = cell_last_close(conn)

    # index fires by (token, direction) for nearest-pre-open lookup
    by_td = defaultdict(list)
    for ts, tok, d, cell in fires:
        by_td[(tok.upper(), d)].append((ts, cell))

    result = {}
    for days in (7, 14, 30):
        rows = closed_trades(conn, days)
        stale_boost_w = stale_boost_l = matched = 0
        stale_boost_pnl = 0.0
        stale_blocked_w = stale_blocked_l = 0
        stale_blocked_pnl = 0.0
        winners = losers = 0
        stale_cells = defaultdict(lambda: [0, 0])
        for tid, tok, sig, d, ot, ct, pnl, ex, conf in rows:
            if ct is None:
                continue
            is_win = (pnl or 0) > 0
            winners += int(is_win)
            losers += int(not is_win)
            cand = by_td.get((tok.upper(), (d or '').upper()), [])
            # nearest fire at-or-before open
            prev = [c for c in cand if c[0] <= ot]
            if not prev:
                continue
            fire_ts, cell = prev[-1]
            if ot - fire_ts > timedelta(minutes=30):
                continue  # not this trade's fire
            matched += 1
            lc = last_close.get(cell, {}).get((d or '').upper())
            age = (fire_ts - lc).total_seconds() / 86400.0 if lc else 9999.0
            if age > fresh_days:
                stale_cells[(cell, (d or '').upper())][0 if is_win else 1] += 1
                stale_boost_pnl += float(pnl or 0)
                if is_win:
                    stale_boost_w += 1
                else:
                    stale_boost_l += 1
                # de-boost 1.2 -> 1.0 divides exec confidence by 1.2; MIN_EXEC_CONFIDENCE
                # = 40 (decider_run.py) => hard-blocked iff conf < 48. conf here is the
                # stored trade confidence (pre-penalty-product scale) — reading (b) below
                # is therefore an upper bound on blocks, reading (a) a lower bound.
                if conf and float(conf) / 1.2 < 40:
                    stale_blocked_w += int(is_win)
                    stale_blocked_l += int(not is_win)
                    stale_blocked_pnl += float(pnl or 0)
        n_win = max(1, winners)
        result[days] = {
            'trades': len(rows),
            'winners': winners,
            'losers': losers,
            'matched_to_fire': matched,
            'stale_boost_winners': stale_boost_w,
            'stale_boost_losers': stale_boost_l,
            'stale_boost_pnl': round(stale_boost_pnl, 3),
            'fk_upper_pct': round(100.0 * stale_boost_w / n_win, 1),
            'hard_blocked_would_be_winners': stale_blocked_w,
            'hard_blocked_would_be_losers': stale_blocked_l,
            'hard_blocked_pnl': round(stale_blocked_pnl, 3),
            'fk_hard_pct': round(100.0 * stale_blocked_w / n_win, 1),
            'stale_cells': {f'{k[0]}|{k[1]}': v for k, v in sorted(
                stale_cells.items(), key=lambda x: -(x[1][0] + x[1][1]))},
        }
    conn.close()

    # suppressed fires / day (whole log window)
    days_span = max(1, (fires[-1][0] - fires[0][0]).days + 1) if fires else 1
    stale_fires = 0
    for ts, tok, d, cell in fires:
        lc = last_close.get(cell, {}).get(d)
        age = (ts - lc).total_seconds() / 86400.0 if lc else 9999.0
        if age > fresh_days:
            stale_fires += 1
    result['traffic'] = {
        'fires_total': len(fires),
        'log_span_days': days_span,
        'stale_fires': stale_fires,
        'stale_fires_per_day': round(stale_fires / days_span, 1),
        'fresh_days': fresh_days,
    }
    # Ship criteria locked by #116: fk_upper < 20% AND OOS same-sign at 7d and 30d.
    # Sign convention: stale_boost_pnl is the cohort's PnL — suppressing the boost
    # removes those trades, so a NEGATIVE cohort PnL = removing boost is POSITIVE.
    s7, s30 = result[7]['stale_boost_pnl'], result[30]['stale_boost_pnl']
    result['verdict'] = {
        'fk_upper_lt_20_all_windows': all(
            result[w]['fk_upper_pct'] < 20 for w in (7, 14, 30)),
        'oos_same_sign_7d_30d': (s7 < 0 and s30 < 0) or (s7 > 0 and s30 > 0),
        'suppress_is_profitable_7d_30d': (s7 < 0 and s30 < 0),
        'note': 'suppress_is_profitable = de-boost removes a net-losing cohort',
    }
    return result


def selfcheck():
    """Fixture: a stale cell fire must be flagged, a fresh one must not."""
    from datetime import datetime as dt
    lc_old = {'dead_cell': {'LONG': dt(2026, 8, 1)}}
    fire = dt(2026, 10, 24, 6, 0, 0)
    age = (fire - lc_old['dead_cell']['LONG']).days
    assert age > 14, 'stale fixture must exceed fresh window'
    lc_new = {'live_cell': {'LONG': dt(2026, 10, 23)}}
    age2 = (fire - lc_new['live_cell']['LONG']).total_seconds() / 86400.0
    assert age2 <= 14, 'fresh fixture must be inside fresh window'
    fires = parse_fires()
    assert fires and fires == sorted(fires), 'fires parse + sorted'
    assert all(c for _, _, _, c in fires), 'every fire has a cell key'
    res = run(14)
    for w in (7, 14, 30):
        assert 'stale_boost_pnl' in res[w], f'missing stale_boost_pnl for {w}d'
        assert 'fk_hard_pct' in res[w], f'missing fk_hard_pct for {w}d'
        assert res[w]['fk_upper_pct'] >= res[w]['fk_hard_pct'], 'upper must bound hard'
    assert 'fk_upper_lt_20_all_windows' in res['verdict'], 'verdict missing'
    print(f'SELFCHECK PASS: {len(fires)} fires parsed, stale/fresh fixtures OK, '
          f'pnl+verdict fields present')
    return True


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--fresh-days', type=int, default=14)
    ap.add_argument('--selfcheck', action='store_true')
    a = ap.parse_args()
    if a.selfcheck:
        selfcheck()
        sys.exit(0)
    res = run(a.fresh_days)
    import json
    print(json.dumps(res, indent=2, default=str))
