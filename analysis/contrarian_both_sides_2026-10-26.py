#!/usr/bin/env python3
"""contrarian_both_sides_2026-10-26.py — the missing control arm for the Oct-27 PROMOTE.

`analysis/contrarian_outcome_join.py` evaluates ONLY the contrarian direction on each
contrarian_shadow.jsonl event, so the standing pre-registered bar reads
"pump-chain- flip-WR 64.6% n=347". A flip decision needs the ORIGINAL direction scored
with the SAME rule on the SAME events — otherwise 64.6% is uninterpretable (it could be
64.6% vs 64.6% = no directional edge at all).

Primary table = the pre-registered scorer, untouched (the Oct-27 bar is defined on it).
A second table reports a direction-aware sensitivity for the one inherited defect in that
scorer: when a single 5m candle crosses both +/-0.40% it picks the verdict off the close
direction alone (`c >= entry_price -> WINNER`), which is wrong for a SHORT arm. Measured
on this file: that branch fires on 22/1638 arm-evals (1.3%), balanced 6W/5L per arm —
reported next to the primary number instead of changing the pre-registered instrument
days before the decision.

Rule (identical to the join, pre-registered there):
  WINNER = direction reached +0.40% favorable before -0.40% adverse (5m candles)
  LOSER  = adverse hit first, or neither inside 30 candles
  SHALLOW= never moved +/-0.40% either way inside 30 candles
Units: price-move % only (no leverage) — UNITS RULE.

Usage: python3 analysis/contrarian_both_sides_2026-10-26.py [--selfcheck]
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contrarian_outcome_join import classify  # pre-registered scorer (PRIMARY table)

SHADOW = '/root/.hermes/data/contrarian_shadow.jsonl'
OUT = '/root/.hermes/data/contrarian_both_sides.json'
ARM_PCT = 0.40
ADV_PCT = 0.40
MAX_CANDLES = 30


def classify_primary(conn, entry, direction):
    """Adapter: the pre-registered scorer's signature is classify(entry, conn)."""
    return classify(entry, conn)


def classify_fixed(conn, entry, direction):
    """Sensitivity scorer: same rule, but the both-crossed-same-candle tiebreak is
    direction-aware (a SHORT whose close is above entry did NOT win)."""
    from contrarian_outcome_join import ts_to_unix
    ts_unix = ts_to_unix(entry.get('ts', ''))
    token = (entry.get('token') or '').upper()
    ep = entry.get('entry_price')
    if not ts_unix or not token or not ep or not direction:
        return None
    ep = float(ep)
    if ep <= 0:
        return None
    cur = conn.cursor()
    cur.execute("""
        SELECT ts, open, high, low, close FROM candles_5m
        WHERE token = ? AND ts > ? AND is_closed = 1
        ORDER BY ts ASC LIMIT ?
    """, (token, ts_unix, MAX_CANDLES))
    rows = cur.fetchall()
    if not rows:
        return ('NO_DATA', 0, 0, 0)
    max_fav = 0.0
    max_adv = 0.0
    outcome = 'SHALLOW'
    for (_, o, h, l, c) in rows:
        if direction == 'LONG':
            fav = (h - ep) / ep * 100
            adv = (ep - l) / ep * 100
        else:
            fav = (ep - l) / ep * 100
            adv = (h - ep) / ep * 100
        max_fav = max(max_fav, fav)
        max_adv = max(max_adv, adv)
        if max_fav >= ARM_PCT and max_adv < ADV_PCT:
            outcome = 'WINNER'
            break
        if max_adv >= ADV_PCT and max_fav < ARM_PCT:
            outcome = 'LOSER'
            break
        if max_fav >= ARM_PCT and max_adv >= ADV_PCT:
            won = (direction == 'LONG') == (c >= ep)
            outcome = 'WINNER' if won else 'LOSER'
            break
    else:
        if max_fav >= ARM_PCT:
            outcome = 'WINNER'
        elif max_adv >= ADV_PCT:
            outcome = 'LOSER'
        else:
            outcome = 'SHALLOW'
    return (outcome, round(max_fav, 3), round(max_adv, 3), len(rows))


def score(conn, entry, direction, scorer):
    """Score one direction on one event (entry cloned so contrarian_direction = direction)."""
    if not direction:
        return None
    clone = dict(entry)
    clone['contrarian_direction'] = direction
    r = scorer(conn, clone, direction)
    if r is None or r[0] == 'NO_DATA':
        return None
    return r[0]


def binom_p(k, n):
    """Two-sided exact binomial p-value against p=0.5 (no scipy: this is a selfcheck-safe path)."""
    from math import comb
    if n == 0:
        return 1.0
    pk = comb(n, k) / (2.0 ** n)
    p = 0.0
    for i in range(0, n + 1):
        pi = comb(n, i) / (2.0 ** n)
        if pi <= pk + 1e-12:
            p += pi
    return min(1.0, p)


def run_scorer(entries, conn, scorer, cut):
    by_sig = defaultdict(lambda: defaultdict(int))
    halves = defaultdict(lambda: defaultdict(int))
    pairs = defaultdict(lambda: {'both': 0, 'flip_wins_orig_loses': 0,
                                 'flip_loses_orig_wins': 0, 'same': 0,
                                 'flip_only_decided': 0, 'orig_only_decided': 0})
    n_rows = 0
    for e in entries:
        o = score(conn, e, e.get('original_direction'), scorer)
        f = score(conn, e, e.get('contrarian_direction'), scorer)
        if o is None or f is None:
            continue
        n_rows += 1
        sig = e.get('signal', '?')
        half = 'older' if e.get('ts', '') < cut else 'newer'
        by_sig[sig][f'orig_{o}'] += 1
        by_sig[sig][f'flip_{f}'] += 1
        halves[(sig, half)][f'orig_{o}'] += 1
        halves[(sig, half)][f'flip_{f}'] += 1
        p = pairs[sig]
        decided_o = o in ('WINNER', 'LOSER')
        decided_f = f in ('WINNER', 'LOSER')
        if decided_o and decided_f:
            p['both'] += 1
            if f == 'WINNER' and o == 'LOSER':
                p['flip_wins_orig_loses'] += 1
                halves[(sig, half)]['F>O'] += 1
            elif f == 'LOSER' and o == 'WINNER':
                p['flip_loses_orig_wins'] += 1
                halves[(sig, half)]['F<O'] += 1
            else:
                p['same'] += 1
        elif decided_f:
            p['flip_only_decided'] += 1
        elif decided_o:
            p['orig_only_decided'] += 1
    return by_sig, halves, pairs, n_rows


def print_table(title, by_sig, pairs, halves, cut):
    print(f'\n=== {title} ===')
    print(f'{"signal":32s} {"n":>4s} {"orig WR":>8s} {"flip WR":>8s} '
          f'{"d_pairs":>7s} {"F>O":>5s} {"F<O":>5s} {"p":>8s}')
    summary = {}
    for sig in sorted(by_sig, key=lambda s: -pairs[s]['both']):
        d = by_sig[sig]
        p = pairs[sig]
        n_sig = sum(v for k, v in d.items() if k.startswith('orig_'))
        o_dec = d['orig_WINNER'] + d['orig_LOSER']
        f_dec = d['flip_WINNER'] + d['flip_LOSER']
        o_wr = 100.0 * d['orig_WINNER'] / o_dec if o_dec else 0.0
        f_wr = 100.0 * d['flip_WINNER'] / f_dec if f_dec else 0.0
        disc = p['flip_wins_orig_loses'] + p['flip_loses_orig_wins']
        pv = binom_p(p['flip_wins_orig_loses'], disc) if disc else 1.0
        print(f'{sig:32s} {n_sig:4d} {o_wr:7.1f}% {f_wr:7.1f}% {p["both"]:7d} '
              f'{p["flip_wins_orig_loses"]:5d} {p["flip_loses_orig_wins"]:5d} {pv:8.4f}')
        summary[sig] = {
            'orig': {k.split('_', 1)[1]: v for k, v in d.items() if k.startswith('orig_')},
            'flip': {k.split('_', 1)[1]: v for k, v in d.items() if k.startswith('flip_')},
            'orig_wr': round(o_wr, 1), 'flip_wr': round(f_wr, 1),
            'paired': dict(p), 'paired_p': round(pv, 4),
        }
    print(f'\nOOS split (median event ts = {cut}), house bar = same sign both halves:')
    print(f'{"signal":32s} {"half":>6s} {"n":>4s} {"orig WR":>8s} {"flip WR":>8s} '
          f'{"F>O":>5s} {"F<O":>5s} {"p":>8s}')
    for key in sorted(halves):
        d = halves[key]
        n_sig = sum(v for k, v in d.items() if k.startswith('orig_'))
        o_dec = d['orig_WINNER'] + d['orig_LOSER']
        f_dec = d['flip_WINNER'] + d['flip_LOSER']
        o_wr = 100.0 * d['orig_WINNER'] / o_dec if o_dec else 0.0
        f_wr = 100.0 * d['flip_WINNER'] / f_dec if f_dec else 0.0
        disc = d['F>O'] + d['F<O']
        pv = binom_p(d['F>O'], disc) if disc else 1.0
        print(f'{key[0]:32s} {key[1]:>6s} {n_sig:4d} {o_wr:7.1f}% {f_wr:7.1f}% '
              f'{d["F>O"]:5d} {d["F<O"]:5d} {pv:8.4f}')
    return summary


def selfcheck():
    # 1. direction swap inverts the verdict on an asymmetric candle
    class FakeCur:
        def __init__(self, rows):
            self.rows = rows

        def execute(self, *a, **k):
            pass

        def fetchall(self):
            return self.rows

    class FakeConn:
        def cursor(self):
            return FakeCur([(1000, 100.0, 103.0, 99.9, 102.0)])

    base = {'ts': '2026-10-13T17:12', 'token': 'X', 'entry_price': 100.0}
    assert classify(dict(base, contrarian_direction='LONG'), FakeConn())[0] == 'WINNER'
    assert classify(dict(base, contrarian_direction='SHORT'), FakeConn())[0] == 'LOSER'
    assert classify_fixed(FakeConn(), base, 'LONG')[0] == 'WINNER'
    assert classify_fixed(FakeConn(), base, 'SHORT')[0] == 'LOSER'
    # 2. the BOTH-CROSSED tiebreak: high 103 / low 97 / close 102 crosses both thresholds
    #    on one candle. As-shipped calls LONG WINNER (close>=entry) AND SHORT WINNER too
    #    (same test) -> direction-blind; fixed scorer calls SHORT a LOSS.
    wide = FakeConn()
    wide.cursor = lambda: FakeCur([(1000, 100.0, 103.0, 97.0, 102.0)])
    assert classify(dict(base, contrarian_direction='SHORT'), wide)[0] == 'WINNER'  # inherited defect
    assert classify_fixed(wide, base, 'SHORT')[0] == 'LOSER'
    # 3. binomial: all-same-direction 10/10 -> only the two extremes are <= P(10) -> 2/1024
    assert abs(binom_p(10, 10) - 2 / 1024) < 1e-9, binom_p(10, 10)
    assert binom_p(30, 35) < 0.05, binom_p(30, 35)
    assert binom_p(0, 0) == 1.0
    # 4. shadow row shape
    with open(SHADOW) as f:
        row = json.loads(f.readline())
    assert row.get('original_direction') and row.get('contrarian_direction')
    assert row['original_direction'] != row['contrarian_direction']
    # 5. a None direction never reaches the scorer
    assert score(FakeConn(), dict(base, original_direction=None), None, classify_primary) is None
    print('SELF-CHECK PASS (direction swap, both-crossed tiebreak, binomial 2/1024, '
          'shadow row shape, None direction)')


def main():
    if '--selfcheck' in sys.argv:
        selfcheck()
        return

    import sqlite3
    conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=10)

    entries = [json.loads(l) for l in open(SHADOW) if l.strip()]
    print(f'shadow entries: {len(entries)}')
    stamps = sorted(e.get('ts', '') for e in entries)
    cut = stamps[len(stamps) // 2] if stamps else ''

    primary = run_scorer(entries, conn, classify_primary, cut)
    sens = run_scorer(entries, conn, classify_fixed, cut)
    conn.close()

    s1 = print_table('PRIMARY — pre-registered scorer (the Oct-27 bar is defined on this)',
                     primary[0], primary[2], primary[1], cut)
    s2 = print_table('SENSITIVITY — direction-aware both-crossed tiebreak',
                     sens[0], sens[2], sens[1], cut)

    print('\nVerdict rule (stated before reading): a flip is only evidence-backed when the')
    print('paired exact binomial p<0.05 AND flip_wr > orig_wr on the same events, in BOTH tables.')
    with open(OUT, 'w') as fh:
        json.dump({'timestamp': datetime.now(timezone.utc).isoformat(),
                   'instrument': 'same-events same-rule both directions (control arm for PROMOTE)',
                   'primary': 'pre-registered classify()',
                   'sensitivity': 'direction-aware both-crossed tiebreak (inherited defect, '
                                  'measured 22/1638 arm-evals = 1.3%)',
                   'oos_cut_ts': cut,
                   'rows_scored': primary[3],
                   'by_signal': s1,
                   'by_signal_sensitivity': s2}, fh, indent=2)
    print(f'\nWritten: {OUT}')


if __name__ == '__main__':
    main()
