#!/usr/bin/env python3
"""continuum_alignment_2026-10-23 — brain_auditor creative idea #1 (run #105).

QUESTION: the standing readiness prose says "LONGs only on sustained reclaim
WITH volume, SHORTs only under EMA300" — is trading WITH the BTC 1m EMA300
continuum actually better than trading against it?

Method: join every closed trade's open_time to the BTC 1m continuum_states row
in effect at that moment (latest ts <= open_time, staleness <= 600s), then
split the book into:
  ALIGNED  = LONG while ABOVE, SHORT while BELOW
  COUNTER  = LONG while BELOW, SHORT while ABOVE
  NEUTRAL  = ema300_position == 'AT' (the band itself)

Bars applied (mandate Step 5c/6): n>=20, Fisher exact p<0.05, same sign across
7d/14d/30d, winner-kill < 20%.

VERDICT (shipped with data): REJECTED. Counter-trend trades are the BETTER
cohort (30d 99T 49.5% '+0.91' vs aligned 353T 38.0% '-7.44'), but the block
is not significant at any window (p=0.41/0.71/0.15) and the save sign-flips
('-0.12' 7d / '-0.26' 14d / '+0.91' 30d). Also: the aligned cohort carries the
entire 30d bleed, so the readiness "aligned only" line is a risk convention,
NOT a measured edge — do not cite it as one.

Self-check: python3 brain/analysis/continuum_alignment_2026-10-23.py --selfcheck
"""
import sys, os, json, sqlite3, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
CONTINUUM_DB = '/root/.hermes/data/continuum.db'
STALE_S = 600

sys.path.insert(0, '/root/.hermes/scripts')


def classify(direction, position):
    """ALIGNED / COUNTER / NEUTRAL for one trade at one continuum state."""
    if position not in ('ABOVE', 'BELOW'):
        return 'NEUTRAL'
    if (direction == 'LONG' and position == 'ABOVE') or \
       (direction == 'SHORT' and position == 'BELOW'):
        return 'ALIGNED'
    return 'COUNTER'


def load_states(path=CONTINUUM_DB):
    conn = sqlite3.connect(path)
    rows = conn.execute(
        "SELECT ts, ema300_position, COALESCE(ema300_duration,0) "
        "FROM continuum_states WHERE token='BTC' ORDER BY ts").fetchall()
    conn.close()
    if not rows:
        raise SystemExit(f"no BTC continuum rows in {path}")
    return rows


def state_at(rows, ts_list, t, stale=STALE_S):
    import bisect
    i = bisect.bisect_right(ts_list, t) - 1
    if i < 0 or t - ts_list[i] > stale:
        return None
    return rows[i]


def fetch_trades(days):
    import psycopg2
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute(
        "SELECT id, direction, pnl_usdt, open_time FROM trades "
        "WHERE status='closed' AND close_time > NOW() - INTERVAL '%s days' "
        "ORDER BY open_time" % days)
    out = cur.fetchall()
    conn.close()
    return out


def split(trades, rows, ts_list, min_duration=0):
    buckets = {'ALIGNED': [], 'COUNTER': [], 'NEUTRAL': [], 'NOSTATE': 0}
    for _tid, direction, pnl, ot in trades:
        st = state_at(rows, ts_list, int(ot.timestamp()))
        if st is None:
            buckets['NOSTATE'] += 1
            continue
        pos, dur = st[1], st[2] or 0
        if min_duration and dur < min_duration:
            buckets['NEUTRAL'].append((direction, float(pnl)))
            continue
        buckets[classify(direction, pos)].append((direction, float(pnl)))
    return buckets


def agg(pairs):
    n = len(pairs)
    w = sum(1 for _, p in pairs if p > 0)
    return {"n": n, "wins": w, "wr": round(100.0 * w / n, 1) if n else 0.0,
            "pnl": round(sum(p for _, p in pairs), 2)}


def fisher(counter, all_trades):
    from scipy.stats import fisher_exact
    cw = sum(1 for _, p in counter if p > 0)
    w_all = sum(1 for r in all_trades if r[2] > 0)
    n_all = len(all_trades)
    a = [[cw, len(counter) - cw],
         [w_all - cw, (n_all - len(counter)) - (w_all - cw)]]
    return cw, w_all, float(fisher_exact(a)[1])


def report(min_duration=0):
    rows = load_states()
    ts_list = [r[0] for r in rows]
    out = {}
    for days in (7, 14, 30):
        trades = fetch_trades(days)
        b = split(trades, rows, ts_list, min_duration)
        cw, w_all, p = fisher(b['COUNTER'], trades)
        out[str(days)] = {
            "aligned": agg(b['ALIGNED']),
            "counter": agg(b['COUNTER']),
            "neutral": agg(b['NEUTRAL']),
            "nostate": b['NOSTATE'],
            "block_counter": {
                "fk_pct": round(100.0 * cw / max(w_all, 1), 1),
                "winners_blocked": cw, "winners_total": w_all,
                "fisher_p": round(p, 4),
                "save": agg(b['COUNTER'])['pnl'],
            },
        }
    return out


def selfcheck():
    # classifier truth table
    assert classify('LONG', 'ABOVE') == 'ALIGNED'
    assert classify('SHORT', 'BELOW') == 'ALIGNED'
    assert classify('LONG', 'BELOW') == 'COUNTER'
    assert classify('SHORT', 'ABOVE') == 'COUNTER'
    assert classify('LONG', 'AT') == 'NEUTRAL'
    assert classify('SHORT', 'AT') == 'NEUTRAL'
    # staleness: a state 601s old must be rejected
    rows = [(1000, 'ABOVE', 10), (2000, 'BELOW', 5)]
    assert state_at(rows, [1000, 2000], 2000) is not None
    assert state_at(rows, [1000, 2000], 2601) is None
    # live data: 30d split must cover the whole book (no NOSTATE)
    res = report(min_duration=0)
    d30 = res['30']
    covered = d30['aligned']['n'] + d30['counter']['n'] + d30['neutral']['n'] + d30['nostate']
    assert covered > 0 and d30['nostate'] == 0, d30
    # VERDICT LOCK: if a future window ever makes the counter-block significant
    # AND same-sign at all three windows, this check fails loudly so nobody
    # misses that the rejection has to be re-argued.
    ps = [res[w]['block_counter']['fisher_p'] for w in ('7', '14', '30')]
    saves = [res[w]['block_counter']['save'] for w in ('7', '14', '30')]
    if all(p < 0.05 for p in ps) and all(s > 0 for s in saves):
        raise SystemExit("SELF-CHECK FAIL: counter-block now passes all bars — re-argue the rejection")
    print("continuum_alignment --selfcheck PASS "
          "(classifier 6/6, staleness, coverage nostate=0, verdict lock p=%s save=%s)" % (ps, saves))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selfcheck', action='store_true')
    ap.add_argument('--min-duration', type=int, default=0)
    a = ap.parse_args()
    if a.selfcheck:
        selfcheck()
        return
    res = report(min_duration=a.min_duration)
    print("BTC 1m continuum vs trade direction  (block-counter = trade AGAINST the tape)")
    for w in ('7', '14', '30'):
        d = res[w]
        print(f"  {w:>2}d aligned={d['aligned']} counter={d['counter']} neutral={d['neutral']} nostate={d['nostate']}")
        bc = d['block_counter']
        print(f"      block-counter: fk {bc['winners_blocked']}/{bc['winners_total']} = {bc['fk_pct']}%  "
              f"p={bc['fisher_p']}  save={bc['save']}")


if __name__ == '__main__':
    main()
