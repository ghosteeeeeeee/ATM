#!/usr/bin/env python3
"""r2_addendum.py — robustness addenda for the R2 audit.
Reuses r2_verify.py helpers (independent of the audited script).

1. ev-state @60/240/1440 by OOS half for headline rules (claim's 240m
   statement check)
2. state-baseline robustness: (a) unspaced state (all non-event high-ATR
   bars), (b) hourly state with 4 different grid phases
3. exclude round-1 flat-bar-contaminated coins (GMX/IMX/GALA/SAND) + PUMP
   (n=8 events)
4. equal-weighted per-coin mean diff vs pooled
5. events-per-day clustering stats
6. continuum staleness detail, excluding stale events, inverted mapping
7. ev-base diff across all 60 index-grid phases (round-1 issue 2.5)
Output: audit/r2_addendum_out.txt
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import random
import talib
import bisect
from collections import defaultdict
import r2_verify as R

OUT = []


def p(*a):
    s = ' '.join(str(x) for x in a)
    OUT.append(s)
    print(s, flush=True)


def main():
    store = defaultdict(list)
    coin_store = defaultdict(list)
    metas, rules_by_coin = {}, {}
    for ck in R.COINS:
        meta, rules = R.process_coin(ck, store, coin_store)
        metas[ck] = meta
        rules_by_coin[ck] = rules

    HZS = (60, 240, 1440)
    HEAD = ('15m+4h agree', 'ema_15m', 'ema_1h', 'macd_1h', 'slope6_1h',
            'macd_5m')

    # ── 1. halves at all horizons ───────────────────────────────────────────
    p('=' * 100)
    p('1. ev-state by half, all horizons (claim check: 240m first-half pos, '
      'second n.s.; 60m ~0)')
    p('=' * 100)
    for half in ('first', 'second'):
        for hz in HZS:
            p(f'  --- {half} half, hz={hz} ---')
            for rname in HEAD:
                ev = store.get((rname, half, 'ev', hz), [])
                st = store.get((rname, half, 'state', hz), [])
                if len(ev) < 50 or len(st) < 30:
                    continue
                evv = [v for (_, _, v) in ev]
                stv = [v for (_, _, v) in st]
                d = R.mean(evv) - R.mean(stv)
                ci = R.iid_boot_diff(evv, stv, 2000, 31)
                p(f'   {rname:>16} n={len(evv):>5} ev={R.mean(evv):+7.3f} '
                  f'st={R.mean(stv):+7.3f} diff={d:+7.3f} iid[{ci[0]:+6.3f},'
                  f'{ci[1]:+6.3f}]')

    # ── 2. state robustness ────────────────────────────────────────────────
    p()
    p('=' * 100)
    p('2. STATE-BASELINE ROBUSTNESS @1440 (grid-phase fragility check)')
    p('=' * 100)
    # rebuild state variants per coin
    state_variants = defaultdict(list)   # variant -> [(coin, day, v)]
    ev_recs = defaultdict(list)
    for ck in R.COINS:
        meta = metas[ck]
        ts, ap, days, n = meta['ts'], meta['ap'], meta['days'], meta['n']
        ev_set = set(meta['ev_all'])
        ha = [int(x) for x in meta['ha']]
        # (a) unspaced: all non-event high-ATR bars
        uns = [i for i in ha if i not in ev_set]
        # (b) hourly with 4 phases
        phases = {}
        for ph in (0, 900, 1800, 2700):
            out, last_s = [], None
            for i in ha:
                if i in ev_set:
                    continue
                if last_s is None:
                    # anchor: first candidate; phase delays first inclusion
                    if ph == 0:
                        out.append(i)
                        last_s = ts[i]
                    else:
                        last_s = ts[i] - 3600 + ph
                        if ts[i] - last_s >= 3600:
                            out.append(i)
                            last_s = ts[i]
                    continue
                if ts[i] - last_s >= 3600:
                    out.append(i)
                    last_s = ts[i]
            phases[ph] = out
        for kind, idxs in (('uns', uns), ('ph0', phases[0]),
                           ('ph900', phases[900]), ('ph1800', phases[1800]),
                           ('ph2700', phases[2700])):
            for rname in HEAD:
                d = rules_by_coin[ck][rname]
                raw = meta['raw']
                for i in idxs:
                    dv = int(d[i])
                    if dv == 0 or np.isnan(raw[1440][i]):
                        continue
                    val = float(raw[1440][i]) * dv
                    state_variants[(kind, rname)].append(
                        (ck, int(days[i]), val))
        # ev records for these rules
        for rname in HEAD:
            d = rules_by_coin[ck][rname]
            raw = meta['raw']
            for i in meta['ev_all']:
                dv = int(d[i])
                if dv == 0 or np.isnan(raw[1440][i]):
                    continue
                val = float(raw[1440][i]) * dv
                ev_recs[rname].append((ck, int(days[i]), val))

    for rname in HEAD:
        evv = [v for (_, _, v) in ev_recs[rname]]
        line = f'  {rname:>16} ev n={len(evv):>5} {R.mean(evv):+7.3f} | '
        for kind in ('ph0', 'ph900', 'ph1800', 'ph2700', 'uns'):
            sv = [v for (_, _, v) in state_variants[(kind, rname)]]
            if not sv:
                continue
            d = R.mean(evv) - R.mean(sv)
            if kind == 'uns':
                ci = R.day_cluster_diff(ev_recs[rname],
                                        state_variants[(kind, rname)],
                                        4000, 555)
                line += (f'| uns state n={len(sv)} {R.mean(sv):+7.3f} '
                         f'diff={d:+7.3f} day[{ci[0]:+6.3f},{ci[1]:+6.3f}] ')
            else:
                line += f'{kind}={d:+6.3f} '
        p(line)

    # ── 3/4. coin exclusions & equal weighting ─────────────────────────────
    p()
    p('=' * 100)
    p('3/4. coin-composition robustness @1440, rule 15m+4h agree')
    p('=' * 100)
    flagged = {'GMX', 'IMX', 'GALA', 'SAND'}     # round-1 flat-bar counts
    allc = R.COINS

    def pooled_diff(coins, rname='15m+4h agree'):
        evv = []
        stv = []
        for ck in coins:
            evv += coin_store.get((rname, 'full', 'ev', 1440, ck), [])
            stv += coin_store.get((rname, 'full', 'state', 1440, ck),
                                  [])
        return len(evv), R.mean(evv), len(stv), R.mean(stv), \
            R.mean(evv) - R.mean(stv)

    for label, coins in (
            ('all 12', allc),
            ('excl GMX/IMX/GALA/SAND', [c for c in allc if c not in flagged]),
            ('excl PUMP', [c for c in allc if c != 'PUMP']),
            ('excl flagged+PUMP', [c for c in allc
                                   if c not in flagged and c != 'PUMP']),
            ('BTC/SOL/SUI/TAO only',
             ['BTC', 'SOL', 'SUI', 'TAO'])):
        ne, me, ns, ms, d = pooled_diff(coins)
        p(f'  {label:>26}: ev n={ne:>5} {me:+7.3f} | st n={ns:>5} {ms:+7.3f}'
          f' | pooled diff {d:+7.3f}')

    # equal-weighted per-coin diffs for all 15 rules
    p('\n  equal-weighted mean of per-coin diffs (vs pooled) @1440:')
    for rname in ('15m+4h agree', 'ema_15m', 'ema_1h', 'macd_1h',
                  'slope6_1h', 'macd_5m'):
        diffs = []
        for ck in R.COINS:
            ev = coin_store.get((rname, 'full', 'ev', 1440, ck), [])
            st = coin_store.get((rname, 'full', 'state', 1440, ck), [])
            if ev and st:
                diffs.append(R.mean(ev) - R.mean(st))
        ne, me, ns, ms, dp = pooled_diff(R.COINS)
        # pooled needs rule name:
        evv, stv = [], []
        for ck in R.COINS:
            evv += coin_store.get((rname, 'full', 'ev', 1440, ck), [])
            stv += coin_store.get((rname, 'full', 'state', 1440, ck), [])
        dp = R.mean(evv) - R.mean(stv)
        p(f'    {rname:>16}: equal-wt {R.mean(diffs):+7.3f} over '
          f'{len(diffs)} coins | pooled {dp:+7.3f}')

    # ── 5. event clustering ────────────────────────────────────────────────
    p()
    p('=' * 100)
    p('5. event clustering (independence assumption check)')
    p('=' * 100)
    for ck in R.COINS:
        meta = metas[ck]
        dd = defaultdict(int)
        for i in meta['ev_all']:
            dd[int(meta['ts'][i]) // 86400] += 1
        if dd:
            vals = list(dd.values())
            p(f'  {ck:5s} ev days={len(dd):3d} max/day={max(vals):3d} '
              f'mean/day={sum(vals)/len(vals):5.2f}')
    allday = defaultdict(int)
    for ck in R.COINS:
        meta = metas[ck]
        for i in meta['ev_all']:
            allday[int(meta['ts'][i]) // 86400] += 1
    v = sorted(allday.values())
    p(f'  POOLED per-day event counts: min={v[0]} median={v[len(v)//2]} '
      f'max={v[-1]} days={len(v)}')
    # gap between consecutive events (hours), pooled per coin
    gaps = []
    for ck in R.COINS:
        ts = metas[ck]['ts']
        ev = metas[ck]['ev_all']
        for a, b in zip(ev, ev[1:]):
            gaps.append((ts[b] - ts[a]) / 3600.0)
    gaps.sort()
    p(f'  inter-event gap hours: p10={gaps[len(gaps)//10]:.2f} '
      f'median={gaps[len(gaps)//2]:.2f} p90={gaps[9*len(gaps)//10]:.2f}')

    # ── 7. ev-base across 60 grid phases ───────────────────────────────────
    p()
    p('=' * 100)
    p('7. ev-base @1440 across all 60 index-grid phases (round-1 issue 2.5)')
    p('=' * 100)
    for rname in ('15m+4h agree', 'ema_15m', 'macd_1h'):
        evv = [v for (_, _, v) in store.get((rname, 'full', 'ev', 1440), [])]
        # per-coin buckets by index phase (i % 60)
        buckets = defaultdict(list)
        for ck in R.COINS:
            meta = metas[ck]
            d = rules_by_coin[ck][rname]
            raw = meta['raw']
            for i in range(meta['n'] - 15):
                dv = int(d[i])
                if dv == 0 or np.isnan(raw[1440][i]):
                    continue
                buckets[i % 60].append(float(raw[1440][i]) * dv)
        ds = []
        for ph in range(60):
            bv = buckets[ph]
            if bv:
                ds.append(R.mean(evv) - R.mean(bv))
        p(f'  {rname:>16}: ev-base diff across 60 phases: '
          f'min={min(ds):+.3f} median={sorted(ds)[30]:+.3f} '
          f'max={max(ds):+.3f} (phase0={ds[0]:+.3f})')

    # ── 6. continuum addenda ───────────────────────────────────────────────
    p()
    p('=' * 100)
    p('6. CONTINUUM addenda (BTC $60 events)')
    p('=' * 100)
    ts, hi, lo, cl = R.load_1m('BTC')
    n = len(ts)
    atr = talib.ATR(hi, lo, cl, 14)
    ev_all = [i for i in R.find_events(atr, ts, thr=60.0) if i < n - 15]
    conn = __import__('sqlite3').connect(R.CDB, timeout=10)
    rows = conn.execute(
        "SELECT ts, state_score FROM continuum_states WHERE token='BTC' "
        "AND state_score IS NOT NULL ORDER BY ts").fetchall()
    conn.close()
    cts = np.array([r[0] for r in rows], dtype=np.int64)
    csc = np.array([r[1] for r in rows], dtype=np.float64)

    def score_at(t):
        k = bisect.bisect_right(cts, t) - 1
        return (float(csc[k]), int(cts[k])) if k >= 0 else (None, None)

    raw, _ = R.build_returns(ts, cl)
    stales, stale_flags = [], []
    for i in ev_all:
        s, sts = score_at(int(ts[i]))
        st = int(ts[i]) - sts if s is not None else 10**9
        stales.append(st)
        stale_flags.append(st > 300)
    p(f'  staleness: n={len(stales)} >60s={sum(1 for x in stales if x > 60)} '
      f'>300s={sum(1 for x in stales if x > 300)} '
      f'>1800s={sum(1 for x in stales if x > 1800)}')

    def cont50(t):
        s, _ = score_at(t)
        return 0 if s is None else (1 if s >= 50 else -1)

    for label, filt in (('all events', lambda k: True),
                        ('staleness<=300s only',
                         lambda k: not stale_flags[k])):
        evv = []
        for k, i in enumerate(ev_all):
            if not filt(k):
                continue
            d = cont50(int(ts[i]))
            if d == 0 or np.isnan(raw[1440][i]):
                continue
            evv.append(float(raw[1440][i]) * d)
        inv = [-x for x in evv]
        p(f'  cont_50 {label:>22}: n={len(evv)} WR={R.wr(evv):.1f}% '
          f'mean={R.mean(evv):+.3f} | INVERTED WR={R.wr(inv):.1f}% '
          f'mean={R.mean(inv):+.3f}')

    # score at events: distribution + forward BTC return (direction-neutral)
    fwd = []
    for i in ev_all:
        if not np.isnan(raw[1440][i]):
            fwd.append(float(raw[1440][i]))
    p(f'  direction-neutral 24h BTC fwd at $60 events: n={len(fwd)} '
      f'mean={R.mean(fwd):+.3f}% WR(>0)={R.wr(fwd):.1f}%')
    # score>=50 share by event direction outcome
    longs = shorts = 0
    for i in ev_all:
        s, _ = score_at(int(ts[i]))
        if s is None:
            continue
        if s >= 50:
            longs += 1
        else:
            shorts += 1
    p(f'  score>=50 (LONG) events={longs} score<50 (SHORT) events={shorts}')

    with open('/root/.hermes/audit/r2_addendum_out.txt', 'w') as f:
        f.write('\n'.join(OUT) + '\n')
    print('\n[written] /root/.hermes/audit/r2_addendum_out.txt')


if __name__ == '__main__':
    main()
