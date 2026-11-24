#!/usr/bin/env python3
"""bb-squeeze MODULE-RSI 65->70 reband 1m candle-walk (amplify-bbsqueeze-module-rsi-reband).

Closes step (iii) of the pre-registered bar (due 2026-11-25):
  SHIP only if net pnl_usdt>0 AND 14d/30d same sign AND fk of current 60-65
  winners=0 (admit-only) AND n>=10.

Events: [bb-squeeze] LONG BLOCKED lines in logs/pipeline.log with MODULE RSI
in [65,70] (the block line prints module RSI — never enrichment rsi_14, #236).
Dedup: one entry per token per 60m (position-open collapse).
Entry = 1m close at/just before block ts. Exit engine (live trail family):
  arm fav >= 0.40 (PM_TRAIL_ACTIVATE_PCT) -> trail at peak-0.20 (PM_TRAIL_DISTANCE_PCT)
  hard stop -0.85% price (bb-squeeze+ live avg SL dist 0.843%, 30d n=58)
  max hold 120m -> close.
pnl_usdt = price_move% * NOTIONAL / 100 (UNITS GUARD #193; never leveraged pnl_pct).
NOTIONAL = 11.10 (size floor). fk=0 by construction (admit-only: no winner touched).

Usage: python3 bbsqueeze_reband_walk_2026-11-24.py [--selfcheck]
"""
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'scripts'))
from paths import CANDLES_DB  # noqa: E402

import sqlite3  # noqa: E402

LOG = '/root/.hermes/logs/pipeline.log'
ARM = 0.40
TRAIL = 0.20
SL_PCT = 0.85
MAX_HOLD = 120
NOTIONAL = 11.10
DEDUP_S = 60 * 60
RSI_LO, RSI_HI = 65.0, 70.0


def parse_events(path=None):
    """-> [(token, epoch, module_rsi)] for 65-70 LONG BLOCKED lines, time-sorted."""
    path = path or LOG
    ev = []
    with open(path, 'rb') as f:
        for line in f:
            if b'[bb-squeeze]' not in line or b'BLOCKED' not in line:
                continue
            s = line.decode('utf-8', 'replace')
            m = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*RSI ([0-9.]+) > 65', s)
            if not m:
                continue
            r = float(m.group(2))
            if not (RSI_LO <= r <= RSI_HI):
                continue
            t = re.search(r'\[bb-squeeze\] (\S+) LONG', s)
            if not t:
                continue
            ts = datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S').replace(
                tzinfo=timezone.utc)
            ev.append((t.group(1), ts.timestamp(), r))
    ev.sort(key=lambda x: x[1])
    return ev


def dedup(events, gap_s=DEDUP_S):
    out, last = [], {}
    for tok, ep, r in events:
        if tok in last and ep - last[tok] <= gap_s:
            continue
        last[tok] = ep
        out.append((tok, ep, r))
    return out


def entry_price(token, epoch):
    conn = sqlite3.connect(CANDLES_DB, timeout=5)
    try:
        row = conn.execute(
            "SELECT close FROM candles_1m WHERE token=? AND ts<=? "
            "ORDER BY ts DESC LIMIT 1", (token.upper(), int(epoch))).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def walk_exit(token, epoch, entry):
    """-> (exit_price, reason, bars_used) using the live trail-family rules."""
    conn = sqlite3.connect(CANDLES_DB, timeout=5)
    try:
        rows = conn.execute(
            "SELECT ts, high, low, close FROM candles_1m WHERE token=? AND ts>? "
            "ORDER BY ts ASC LIMIT ?", (token.upper(), int(epoch), MAX_HOLD)).fetchall()
    finally:
        conn.close()
    if not rows:
        return None, 'no_candles', 0
    armed, peak = False, 0.0
    for i, (_ts, hi, lo, cl) in enumerate(rows, 1):
        fav = (hi / entry - 1) * 100
        if not armed:
            if fav >= ARM:
                armed = True
                peak = fav
            elif (1 - lo / entry) * 100 >= SL_PCT:
                return entry * (1 - SL_PCT / 100), 'hard_sl', i
        else:
            peak = max(peak, (hi / entry - 1) * 100)
            trail_px = entry * (1 + (peak - TRAIL) / 100)
            if lo <= trail_px:
                return trail_px, 'trail', i
    return rows[-1][3], 'timeout', len(rows)


def run(events, split_at=None):
    decided, skipped = [], 0
    for tok, ep, r in events:
        px = entry_price(tok, ep)
        if not px:
            skipped += 1
            continue
        xp, reason, bars = walk_exit(tok, ep, px)
        if xp is None:
            skipped += 1
            continue
        move = (xp / px - 1) * 100
        decided.append({
            'token': tok, 'epoch': ep, 'rsi': r, 'entry': px, 'exit': xp,
            'reason': reason, 'bars': bars, 'move_pct': move,
            'pnl_usdt': move * NOTIONAL / 100,
        })
    wins = sum(1 for d in decided if d['pnl_usdt'] > 0)
    net = sum(d['pnl_usdt'] for d in decided)
    out = {
        'n_events': len(events), 'n_decided': len(decided), 'n_skipped': skipped,
        'wins': wins, 'losses': len(decided) - wins,
        'wr': round(100.0 * wins / len(decided), 1) if decided else 0.0,
        'net_pnl_usdt': round(net, 2),
        'fk_pct': 0.0,  # admit-only: no current 60-65 winner is touched
    }
    if split_at and decided:
        a = [d for d in decided if d['epoch'] < split_at]
        b = [d for d in decided if d['epoch'] >= split_at]
        for name, half in (('h1', a), ('h2', b)):
            hn = sum(d['pnl_usdt'] for d in half)
            out[name] = {'n': len(half), 'net': round(hn, 2),
                         'sign': (hn > 0) - (hn < 0)}
        out['same_sign'] = bool(a) and bool(b) and out['h1']['sign'] == out['h2']['sign']
    return out, decided


def bars(res):
    """Pre-registered verdict (same-sign limb uses in-window halves; the
    14d/30d limb is NOT EVALUABLE on 5d of log instrumentation)."""
    return {
        'i_n10': res['n_decided'] >= 10,
        'ii_net_positive': res['net_pnl_usdt'] > 0,
        'iii_halves_same_sign': res.get('same_sign') is True,
        'iv_fk0_admit_only': res['fk_pct'] == 0.0,
        'v_14d30d_same_sign': False,  # window 11-19..11-24 < 14d — cannot evaluate
    }


def selfcheck():
    # dedup: burst collapses to 1
    e = [('A', 1000.0, 66.0), ('A', 1300.0, 67.0), ('A', 5000.0, 68.0), ('B', 1100.0, 69.0)]
    d = dedup(e, gap_s=3600)
    assert len(d) == 3, d  # A burst->1, A at +4000s->1, B->1
    # walk: immediate arm then trail
    # fabricated: entry 100, candles push +0.5 then retrace
    import tempfile
    global LOG
    old = LOG
    try:
        with tempfile.NamedTemporaryFile('w', suffix='.log', delete=False) as f:
            f.write('2026-11-24 01:00:00 [bb-squeeze] AAA LONG BLOCKED — RSI 66.0 > 65 (x)\n')
            f.write('2026-11-24 01:05:00 [bb-squeeze] AAA LONG BLOCKED — RSI 66.5 > 65 (x)\n')
            f.write('2026-11-24 01:40:00 [bb-squeeze] AAA LONG BLOCKED — RSI 68.0 > 65 (x)\n')
            f.write('2026-11-24 01:00:00 [bb-squeeze] BBB LONG BLOCKED — RSI 69.5 > 65 (x)\n')  # in-band
            f.write('2026-11-24 01:00:00 [bb-squeeze] DDD LONG BLOCKED — RSI 71.0 > 65 (x)\n')  # >70 excluded
            f.write('2026-11-24 01:01:00 [bb-squeeze] CCC LONG BLOCKED — RSI 55.0 < 60 (x)\n')  # wrong format
            path = f.name
        LOG = path
        ev = parse_events()
        assert len(ev) == 4, ev  # DDD 71 excluded, CCC format mismatch
        dd = dedup(ev)
        assert len(dd) == 2, dd  # AAA burst -> 1, BBB -> 1
        assert all(RSI_LO <= r <= RSI_HI for _, _, r in ev)
    finally:
        LOG = old
        os.unlink(path)
    # pnl units: +1% at 11.10 = +0.111
    assert abs((1.0 * NOTIONAL / 100) - 0.111) < 1e-9
    b = bars({'n_decided': 12, 'net_pnl_usdt': 0.5, 'same_sign': True, 'fk_pct': 0.0})
    assert b['i_n10'] and b['ii_net_positive'] and b['iii_halves_same_sign'] and not b['v_14d30d_same_sign']
    print('SELFCHECK PASS')


def main():
    if '--selfcheck' in sys.argv:
        selfcheck()
        return
    raw = parse_events()
    ev = dedup(raw)
    mid = ev[len(ev) // 2][1] if ev else None
    res, decided = run(ev, split_at=mid)
    b = bars(res)
    print(f'raw_lines={len(raw)} deduped={len(ev)} span='
          f'{datetime.fromtimestamp(ev[0][1], tz=timezone.utc):%m-%d %H:%M}..'
          f'{datetime.fromtimestamp(ev[-1][1], tz=timezone.utc):%m-%d %H:%M}')
    print(res)
    print('bars:', b)
    print('verdict:', 'SHIP' if all(b.values()) else
          ('EXTEND (window <14d — same-sign limb not evaluable)' if
           b['i_n10'] and b['ii_net_positive'] and b['iii_halves_same_sign']
           and b['iv_fk0_admit_only'] else 'NO SHIP'))
    from collections import Counter
    print('exits:', Counter(d['reason'] for d in decided))
    worst = sorted(decided, key=lambda d: d['pnl_usdt'])[:5]
    best = sorted(decided, key=lambda d: -d['pnl_usdt'])[:5]
    print('worst:', [(d['token'], round(d['pnl_usdt'], 3), d['reason']) for d in worst])
    print('best:', [(d['token'], round(d['pnl_usdt'], 3), d['reason']) for d in best])


if __name__ == '__main__':
    main()
