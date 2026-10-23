#!/usr/bin/env python3
"""Loser gate-coverage census (brain_auditor #98, 2026-10-23).

WATCHDOG CLAIM UNDER TEST: "4/6 losers violated existing gates — gates exist
and were bypassed or late."

METHOD: for every closed trade, look for a gate BLOCK line (dropped char)
in logs/signal-compactor.log with the SAME token + SAME direction inside
+-60s of open_time (one approval cycle). If one exists, a gate wanted this
token/direction blocked at the moment we opened it.

CONTROL: same token+direction lookup at open_time + 6h (gates fire all day
on active tokens, so raw coverage means nothing without a base rate).

HONEST LIMITS (read before citing):
  * gate lines carry no signal name -> a match may be a block of a different
    signal on the same tape. It proves gate intent on that token/direction,
    not that OUR executed signal was bypassed.
  * blocks are dense for hot tokens; only coverage >> control is informative.

Usage:
  python3 loser_gate_coverage_2026-10-23.py            # 14d
  python3 loser_gate_coverage_2026-10-23.py --selfcheck
"""
import os
import re
import sys
import bisect
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'scripts'))
from paths import *  # noqa

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'logs', 'signal-compactor.log')
LINE = re.compile(r'🚫 \[([^\]]+)\] ([A-Za-z0-9]+)[\s:+]+(LONG|SHORT)\b')
TS = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
TOKDIR = re.compile(r'([A-Za-z0-9]+)[\s:+]+(LONG|SHORT)\b')


def parse_log(path=LOG):
    """(token, direction) -> sorted list of (ts_str, gate)."""
    idx = defaultdict(list)
    with open(path, errors='replace') as f:
        for line in f:
            if '🚫' not in line:
                continue
            m = LINE.search(line)
            if not m:
                continue
            t = TS.match(line)
            if not t:
                continue
            idx[(m.group(2).upper(), m.group(3))].append((t.group(1), m.group(1)))
    for k in idx:
        idx[k].sort()
    return idx


def hits(idx, token, direction, ts_str, window=61):
    """gates whose block falls within +-window seconds of ts_str (zero-padded
    'YYYY-MM-DD HH:MM:SS' compares chronologically as a string)."""
    import datetime as dt
    base = dt.datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
    lo = (base - dt.timedelta(seconds=window)).strftime('%Y-%m-%d %H:%M:%S')
    hi = (base + dt.timedelta(seconds=window)).strftime('%Y-%m-%d %H:%M:%S')
    rows = idx.get((token.upper(), direction), [])
    keys = [r[0] for r in rows]
    i = bisect.bisect_left(keys, lo)
    out = []
    while i < len(rows) and rows[i][0] <= hi:
        out.append(rows[i][1])
        i += 1
    return out


def control_ts(ts_str, hours=6):
    import datetime as dt
    return (dt.datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
            + dt.timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')


def trades(hours=336):
    import psycopg2
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, token, direction, open_time, pnl_usdt, pnl_pct, signal, status, exit_reason
        FROM trades
        WHERE status='closed' AND close_time > NOW() - INTERVAL '%d hours'
        ORDER BY open_time""" % int(hours))
    rows = cur.fetchall()
    conn.close()
    return rows


def parse_bypass(path=LOG):
    """(token, direction) -> sorted list of ts for ALLOW/BYPASS lines whose gate
    name says chop/neutral/continuum — an a-priori semantic cohort (NOT picked
    on pnl). Boilerplate standalone-bypass lines are excluded: they fire for
    ~77% of trades and carry no gate intent."""
    FAM = ('CHOP', 'NEUTRAL', 'CONTINUUM')
    BOILER = ('HOTSET-FINAL-BYPASS', 'PENDING-APPROVE-BYPASS', 'SAFETY-FILTER-BYPASS',
              'CONFLUENCE-GATE-PASS', 'CONFLUENCE-DEBUG')
    idx = defaultdict(list)
    with open(path, errors='replace') as f:
        for line in f:
            low = line.lower()
            if 'bypass' not in low and 'allowed' not in low:
                continue
            if '🚫' in line or 'denied' in line:
                continue
            t = TS.match(line)
            g = TOKDIR.search(line)
            gr = re.search(r'\[([^\]]+)\]', line)
            if not t or not g or not gr:
                continue
            gate = gr.group(1)
            if gate in BOILER or not any(k in gate for k in FAM):
                continue
            idx[(g.group(1).upper(), g.group(2))].append(t.group(1))
    for k in idx:
        idx[k].sort()
    return idx


def fisher_two_sided(a1, a0, b1, b0):
    from math import comb
    n, r, c = a1 + a0 + b1 + b0, a1 + a0, a1 + b1
    if n == 0 or r == 0 or c == 0:
        return 1.0
    def p(k):
        if k < 0 or k > r or k > n - r:
            return 0.0
        return comb(r, k) * comb(n - r, c - k) / comb(n, c)
    obs = p(a1)
    return min(sum(p(k) for k in range(0, min(r, c) + 1) if p(k) <= obs + 1e-12), 1.0)


def summarize(rows, idx, shift_hours=0):
    n = cover = 0
    pnl_cov = pnl_unc = 0.0
    w_cov = w_unc = w_all = 0
    losers_cov = 0
    by_gate = defaultdict(lambda: [0, 0.0])
    for tid, tok, direc, ot, pnl, pct, sig, st, exr in rows:
        ts = ot.strftime('%Y-%m-%d %H:%M:%S')
        if shift_hours:
            ts = control_ts(ts, shift_hours)
        g = hits(idx, tok, direc, ts)
        n += 1
        p = float(pnl)
        if pnl > 0:
            w_all += 1
        if g:
            cover += 1
            pnl_cov += p
            if pnl > 0:
                w_cov += 1
            else:
                losers_cov += 1
            for name in set(g):
                by_gate[name][0] += 1
                by_gate[name][1] += p
        else:
            pnl_unc += p
            if pnl > 0:
                w_unc += 1
    return {
        'n': n, 'cover': cover, 'rate': 100.0 * cover / max(n, 1),
        'pnl_cov': pnl_cov, 'pnl_unc': pnl_unc,
        'wr_cov': 100.0 * w_cov / max(cover, 1),
        'wr_unc': 100.0 * w_unc / max(n - cover, 1),
        'wr_all': 100.0 * w_all / max(n, 1),
        'losers_cov': losers_cov, 'by_gate': by_gate,
        'w_cov': w_cov, 'w_unc': w_unc,
    }


def bypass_cover(idx2, tok, direc, ot, window=61):
    lo = (ot - __import__('datetime').timedelta(seconds=window)).strftime('%Y-%m-%d %H:%M:%S')
    hi = (ot + __import__('datetime').timedelta(seconds=window)).strftime('%Y-%m-%d %H:%M:%S')
    rows_ = idx2.get((tok.upper(), direc), [])
    i = bisect.bisect_left(rows_, lo)
    return i < len(rows_) and rows_[i] <= hi


def selfcheck():
    line2 = '2026-10-23 11:07:00 \U0001f6ab [SHORT-RSI-HARD-FLOOR] ZRO: SHORT blocked at approval — RSI 31.5 < 45'
    line3 = '2026-10-23 11:24:00 \U0001f6ab [PUMP-CHAIN-SHORT-HIGH] CFX SHORT blocked — EXTREME vol'
    line4 = '2026-10-23 11:00:00 \U0001f6ab [HALL-SHAME] ZRO+continuum-trend-+x: low reputation 0.0x'
    m = LINE.search(line2)
    assert m and m.group(2) == 'ZRO' and m.group(3) == 'SHORT' and m.group(1) == 'SHORT-RSI-HARD-FLOOR', m
    m = LINE.search(line3)
    assert m and m.group(2) == 'CFX' and m.group(3) == 'SHORT', m
    assert LINE.search(line4) is None, 'direction-less lines must not match'
    idx = {('ZRO', 'SHORT'): [('2026-10-23 11:07:00', 'SHORT-RSI-HARD-FLOOR')]}
    assert hits(idx, 'ZRO', 'SHORT', '2026-10-23 11:07:30') == ['SHORT-RSI-HARD-FLOOR']
    assert hits(idx, 'ZRO', 'SHORT', '2026-10-23 11:09:00') == []
    assert hits(idx, 'ZRO', 'SHORT', '2026-10-23 11:07:00') == ['SHORT-RSI-HARD-FLOOR']
    assert control_ts('2026-10-23 11:07:00', 6) == '2026-10-23 17:07:00'
    # bypass cohort: boilerplate standalone lines must be excluded, gate lines kept
    import tempfile
    tmp = tempfile.NamedTemporaryFile('w', suffix='.log', delete=False)
    tmp.write('2026-10-23 06:50:00 \u2705 [BTC-CHOP-OVERRIDE] ME LONG — BTC flat but coin has own momentum, allowed\n')
    tmp.write('2026-10-23 06:50:00 \u2705 [HOTSET-FINAL-BYPASS] ME:LONG backtested standalone allowed\n')
    tmp.write('2026-10-23 06:50:00 \u2705 [LONG-RSI-CEILING] ME: LONG bypass — RSI 74.7 > 60 but BTC bullish\n')
    tmp.write('2026-10-23 06:50:00 \u2705 [SHORT-RSI-HARD-FLOOR] ZRO: SHORT allowed at approval — RSI 38.2 < 45 but BTC bearish\n')
    tmp.write('2026-10-23 06:50:00 \u2701 [BTC-CHOP-BYPASS] LTC SHORT — bypass denied, vol gate 0.0\n')
    tmp.close()
    b = parse_bypass(tmp.name)
    os.unlink(tmp.name)
    assert b[('ME', 'LONG')] == ['2026-10-23 06:50:00'], b
    assert ('ZRO', 'SHORT') not in b, 'non-FAM gate must be excluded'
    assert ('LTC', 'SHORT') not in b, 'bypass-denied lines must be excluded'
    assert bypass_cover(b, 'ME', 'LONG', __import__('datetime').datetime(2026, 10, 23, 6, 50, 30))
    assert not bypass_cover(b, 'ME', 'LONG', __import__('datetime').datetime(2026, 10, 23, 7, 5, 0))
    assert fisher_two_sided(3, 7, 7, 3) <= 1.0 and fisher_two_sided(0, 10, 0, 10) == 1.0
    print('SELFCHECK PASS — parser, +-60s window, control shift, bypass cohort, fisher')
    return True


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        sys.exit(0 if selfcheck() else 1)
    import datetime as _dtm
    global dt_now
    dt_now = _dtm.datetime.utcnow()
    hours = 336
    for a in sys.argv[1:]:
        if a.isdigit():
            hours = int(a)
    idx = parse_log()
    idx2 = parse_bypass()
    rows = trades(hours)
    print(f'gate block lines: {sum(len(v) for v in idx.values())} across {len(idx)} token/dir keys')
    print(f'chop/neutral/continuum allow lines: {sum(len(v) for v in idx2.values())} across {len(idx2)} keys')
    print(f'trades in {hours}h: {len(rows)}')

    obs = summarize(rows, idx, 0)
    ctl = summarize(rows, idx, 6)
    print(f"\n[1] BLOCK-line census (same token+direction +-60s of open)")
    print(f"    OBSERVED n={obs['n']} covered={obs['cover']} ({obs['rate']:.1f}%) "
          f"wr_cov={obs['wr_cov']:.1f}% wr_uncov={obs['wr_unc']:.1f}% "
          f"pnl_cov={obs['pnl_cov']:+.2f} pnl_uncov={obs['pnl_unc']:+.2f} "
          f"losers_covered={obs['losers_cov']}")
    print(f"    CONTROL+6h covered={ctl['cover']} ({ctl['rate']:.1f}%) "
          f"pnl_cov={ctl['pnl_cov']:+.2f} wr_cov={ctl['wr_cov']:.1f}%")

    for shift, label in ((0, 'OBSERVED'), (6, 'CONTROL+6h')):
        cov = [r for r in rows if bypass_cover(idx2, r[1], r[2], r[3] + __import__('datetime').timedelta(hours=shift))]
        unc = [r for r in rows if r not in cov]
        cw = sum(1 for r in cov if r[4] > 0)
        uw = sum(1 for r in unc if r[4] > 0)
        cp = sum(float(r[4]) for r in cov)
        up = sum(float(r[4]) for r in unc)
        p = fisher_two_sided(cw, len(cov) - cw, uw, len(unc) - uw)
        if shift == 0:
            print(f"\n[2] CHOP/NEUTRAL/CONTINUUM-override cohort (a-priori gate-name cohort)")
        print(f"    {label:11} COHORT n={len(cov):3} W={cw:3} wr={100*cw/max(len(cov),1):5.1f}% pnl={cp:+7.2f} | "
              f"complement n={len(unc):3} W={uw:3} wr={100*uw/max(len(unc),1):5.1f}% pnl={up:+7.2f} | "
              f"fisher p={p:.3f}")

    print('\n[3] 24h losers — same-cycle gate intent:')
    for tid, tok, direc, ot, pnl, pct, sig, st, exr in rows:
        if pnl >= 0 or (dt_now - ot).total_seconds() > 86400:
            continue
        print(f"    #{tid} {tok} {direc} {sig} {float(pnl):+.2f} "
              f"blocks={hits(idx, tok, direc, ot.strftime('%Y-%m-%d %H:%M:%S'))}")

    print('\n[4] top gates on covered trades (n>=3):')
    for g, (c, p) in sorted(obs['by_gate'].items(), key=lambda kv: kv[1][1]):
        if c >= 3:
            print(f'    {g:28} n={c:3} pnl={p:+.2f}')
