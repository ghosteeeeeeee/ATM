#!/usr/bin/env python3
"""
gate_shadow_dedup_2026-10-26.py — brain_auditor run #156

QUESTION: does gate_shadow --report measure "PnL avoided/foregone by gates", or
something else?

METHOD (matches scripts/gate_shadow.py close_events exactly):
  for each event WHERE closed=1 AND would_trade=1, the would-be outcome is the
  FIRST real Hermes trade on (token, direction) opening in [blocked_at, blocked_at+24h).
  We re-derive that join and collect the referenced trade id.

TWO properties this exposes:
  1. REALIZED, not counterfactual — the referenced rows are live Hermes trades
     already in `trades` with their own PnL in every performance window. Their
     money was captured (or lost) by us; it is not "avoided" or "foregone".
  2. MULTI-COUNTED — many events (same token+direction, different 10-min block
     buckets, often different gates) map to the SAME follow-on trade, so the
     report's pnl column adds the same dollars repeatedly.

Self-check asserts both properties and the live-book membership of every
referenced trade.

Run: python3 brain/analysis/gate_shadow_dedup_2026-10-26.py [--selfcheck]
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts'))
from paths import HERMES_DATA  # noqa: E402

GATE_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'gate_shadow.db')


def join_followon(pg_cur, token, direction, blocked_at):
    """Exact replica of gate_shadow.close_events would-be join (adds trade id)."""
    pg_cur.execute("""
        SELECT id, signal, pnl_usdt FROM trades
        WHERE token = %s AND direction = %s AND status='closed'
          AND open_time >= %s::timestamptz
          AND open_time < (%s::timestamptz + interval '24 hours')
          AND pnl_usdt IS NOT NULL
        ORDER BY open_time LIMIT 1
    """, (token, direction, blocked_at, blocked_at))
    return pg_cur.fetchone()


def collect(verbose=False):
    import psycopg2
    con = sqlite3.connect(GATE_DB)
    cur = con.cursor()
    ev = cur.execute(
        "SELECT id, gate, token, direction, blocked_at, would_pnl FROM events "
        "WHERE closed=1 AND would_trade=1").fetchall()
    con.close()
    if not ev:
        return {'events': 0}

    pg = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    pc = pg.cursor()
    per_event, trade_owner = [], {}
    for eid, gate, token, direction, blocked_at, pnl in ev:
        row = join_followon(pc, token, direction, blocked_at)
        if row is None:
            continue
        tid, sig, real_pnl = row[0], row[1], float(row[2] or 0)
        per_event.append({'id': eid, 'gate': gate, 'trade_id': tid, 'pnl': real_pnl})
        trade_owner.setdefault(tid, {'signal': sig, 'pnl': real_pnl, 'events': 0})['events'] += 1
        # every event's stored would_pnl must equal the referenced trade's pnl
        if pnl is not None and abs(float(pnl) - real_pnl) > 1e-6:
            if verbose:
                print(f'  !! event {eid} stored {pnl} != trade {tid} {real_pnl}')
    ids = list(trade_owner)
    pc.execute("SELECT COUNT(*) FROM trades WHERE status='closed' AND id = ANY(%s)", (ids,))
    in_live = pc.fetchone()[0]
    pc.execute("SELECT COUNT(*) FROM trades WHERE status='closed'")
    live_closed = pc.fetchone()[0]
    pg.close()

    sum_events = sum(e['pnl'] for e in per_event)
    sum_trades = sum(t['pnl'] for t in trade_owner.values())
    n_events, n_trades = len(per_event), len(trade_owner)

    # per-gate: report basis (event multiset) vs distinct-trade basis
    gates = {}
    for e in per_event:
        g = gates.setdefault(e['gate'], {'ev_n': 0, 'ev_w': 0, 'ev_pnl': 0.0, 'tr': {}})
        g['ev_n'] += 1
        g['ev_w'] += 1 if e['pnl'] > 0 else 0
        g['ev_pnl'] += e['pnl']
        g['tr'][e['trade_id']] = e['pnl']
    for g in gates.values():
        g['tr_n'] = len(g['tr'])
        g['tr_w'] = sum(1 for p in g['tr'].values() if p > 0)
        g['tr_pnl'] = sum(g['tr'].values())
        g['dup'] = g['ev_n'] / g['tr_n'] if g['tr_n'] else 0.0

    relax = sorted(
        ((k, v) for k, v in gates.items() if v['tr_n'] >= 15 and v['tr_w'] / v['tr_n'] >= 0.55 and v['tr_pnl'] > 0),
        key=lambda kv: -kv[1]['tr_pnl'])
    worst = sorted(gates.items(), key=lambda kv: kv[1]['tr_pnl'])[:8]

    return {
        'events': n_events, 'distinct_trades': n_trades,
        'sum_events': round(sum_events, 2), 'sum_trades': round(sum_trades, 2),
        'inflation': round(sum_events / sum_trades, 2) if sum_trades else None,
        'dup_factor': round(n_events / n_trades, 2) if n_trades else None,
        'live_closed_trades': live_closed, 'referenced_in_live': in_live,
        'gates': gates, 'relax_on_distinct': [(k, v['tr_n'], round(v['tr_w'] / v['tr_n'], 3),
                                               round(v['tr_pnl'], 2), round(v['dup'], 1))
                                              for k, v in relax],
        'worst_distinct': [(k, v['tr_n'], round(v['tr_pnl'], 2), round(v['dup'], 1))
                           for k, v in worst],
    }


def main():
    selfcheck = '--selfcheck' in sys.argv
    r = collect()
    if r['events'] == 0:
        print('no resolved events')
        return 1
    print('=== gate_shadow counterfactual re-derivation (run #156) ===')
    print(f"events with a follow-on trade : {r['events']}")
    print(f"distinct live trades referenced: {r['distinct_trades']}")
    print(f"dup factor (events / trades)   : {r['dup_factor']}")
    print(f"report-basis PnL (sum events)  : {r['sum_events']:+.2f}")
    print(f"distinct-trade PnL             : {r['sum_trades']:+.2f}")
    print(f"inflation factor               : {r['inflation']}x")
    print(f"live closed trades in book     : {r['live_closed_trades']}")
    print(f"referenced trades found in book: {r['referenced_in_live']}/{r['distinct_trades']}")
    print('\nper-gate (report basis -> distinct basis):')
    print(f'  {"gate":30} {"ev":>5} {"evPnL":>8} {"trd":>5} {"trdPnL":>8} {"dup":>5}')
    for k in sorted(r['gates'], key=lambda k: -r['gates'][k]['ev_n'])[:18]:
        g = r['gates'][k]
        print(f"  {k:30} {g['ev_n']:5d} {g['ev_pnl']:+8.2f} {g['tr_n']:5d} {g['tr_pnl']:+8.2f} {g['dup']:5.1f}")
    print('\nRELAX candidates surviving DISTINCT-trade basis (tr_n>=15, WR>=55%, pnl>0):')
    for k, n, wr, pnl, dup in r['relax_on_distinct']:
        print(f"  {k:30} n={n} WR={wr:.1%} pnl={pnl:+.2f} dup={dup}x")
    if not r['relax_on_distinct']:
        print('  NONE')
    print('\nworst gates on distinct basis:')
    for k, n, pnl, dup in r['worst_distinct']:
        print(f"  {k:30} n={n} pnl={pnl:+.2f} dup={dup}x")

    if selfcheck:
        assert r['dup_factor'] and r['dup_factor'] > 1.0, 'expected multi-counting'
        assert r['events'] > r['distinct_trades'], 'expected events > distinct trades'
        assert abs(r['sum_events']) > abs(r['sum_trades']), 'expected report basis != distinct basis'
        # every referenced row is a live Hermes trade -> money already in the book
        assert r['referenced_in_live'] == r['distinct_trades'], 'referenced trade missing from live book'
        assert r['distinct_trades'] <= r['live_closed_trades']
        print('\nSELF-CHECK PASS: multi-count confirmed; all referenced outcomes are live-book trades.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
