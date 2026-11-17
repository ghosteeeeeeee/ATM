#!/usr/bin/env python3
"""Deadline reads for the 2026-11-17 shadow_disposition batch.

Covers entries with NO pre-built join in scripts/shadow_tag_join.py:
  1. btc-standalone-deny-shadow   [BTC-CHOP-STANDALONE-SHADOW] member-filter tok-day join
  2. setup-recall-shadow          [SETUP-RECALL-SHADOW] tok-day join
  3. short-regime-exempt-shadow   tape-split amendment on top of shadow_tag_join events
  4. long-bypass-regime-shadow    blocked-cohort fwd4h (bar: 14d net > 0 -> back to shadow)
  5. jup-cluster-gate / jup-anti-chase / jup-pro-selection  trades-metadata counterfactuals

LOG/ANALYTICS ONLY. Reads pipeline logs + PG + candles.db, prints verdicts.
Self-check: --selfcheck
"""
import glob
import gzip
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, '/root/.hermes/scripts')
sys.path.insert(0, '/root/.hermes/brain/analysis')

HERMES = '/root/.hermes'
NOTIONAL = 13.44
RT_FEE = 0.0009

# reuse the standard engine
from shadow_tag_join import (  # noqa: E402
    load_candles, fwd_4h, entry_ts_of, log_sources, open_log_text,
)

# module filename has dashes -> importlib
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location(
    'flip1_mod', os.path.join(HERMES, 'brain/analysis/flip1_bear_override_reshadow_2026-11-14.py'))
flip1_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(flip1_mod)
tape_of = flip1_mod.tape_of

import sqlite3  # noqa: E402

TS_RE = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
CONT = os.path.join(HERMES, 'data/continuum.db')


def iter_lines():
    for src in log_sources():
        try:
            with open_log_text(src) as f:
                for ln in f:
                    yield ln
        except Exception:
            continue


def parse_ts(ln):
    m = TS_RE.match(ln)
    return m.group(1) if m else None


def join_and_bar(events, notional=NOTIONAL):
    """events: [{ts, token, direction, source}] -> joined rows + day nets."""
    joined = []
    skipped = defaultdict(int)
    cache = {}
    for e in events:
        tok = (e['token'] or '').upper()
        if not tok:
            skipped['no_token'] += 1
            continue
        if tok not in cache:
            cache[tok] = load_candles(tok)
        rows = cache[tok]
        try:
            datetime.strptime(e['ts'], '%Y-%m-%d %H:%M:%S')
        except Exception:
            skipped['bad_ts'] += 1
            continue
        entry_ts = entry_ts_of(e['ts'])
        sgn = 1 if e['direction'].upper() == 'LONG' else -1
        fwd = fwd_4h(rows, entry_ts, sgn)
        if fwd is None:
            skipped['horizon_immature'] += 1
            continue
        joined.append({**e, 'fwd': fwd, 'day': e['ts'][:10]})
    if not joined:
        return joined, skipped
    return joined, skipped


def bar_stats(joined, notional=NOTIONAL):
    if not joined:
        return None
    n = len(joined)
    wins = sum(1 for r in joined if r['fwd'] > 0)
    fwd_sum = sum(r['fwd'] for r in joined)
    gross = fwd_sum / 100.0 * notional
    fee = n * notional * RT_FEE
    day_net = defaultdict(float)
    for r in joined:
        day_net[r['day']] += r['fwd'] / 100.0 * notional - notional * RT_FEE
    days_pos = sum(1 for v in day_net.values() if v > 0)
    return {
        'n': n, 'wr': 100.0 * wins / n, 'avg_fwd': fwd_sum / n,
        'gross': gross, 'fee': fee, 'net': gross - fee,
        'days_total': len(day_net), 'days_pos': days_pos,
        'day_net': dict(sorted(day_net.items())),
        'pos_ratio': days_pos / len(day_net) if day_net else 0,
    }


# ── 1. BTC-CHOP-STANDALONE ───────────────────────────────────────────────────
def standalone_events():
    from hermes_constants import STANDALONE_BYPASS_SIGNALS
    members = set()
    for s in STANDALONE_BYPASS_SIGNALS:
        members.add(s)
        members.add(re.sub(r'\d+$', '', s.rstrip('+-')))
    pat = re.compile(
        r'\[BTC-CHOP-STANDALONE-SHADOW\] (\w+) (LONG|SHORT) ([^:]+): WOULD-PASS')
    raw = 0
    evs = []
    seen = set()
    for ln in iter_lines():
        if '[BTC-CHOP-STANDALONE-SHADOW]' not in ln:
            continue
        raw += 1
        ts = parse_ts(ln)
        m = pat.search(ln)
        if not ts or not m:
            continue
        token, direction, source = m.group(1), m.group(2), m.group(3).strip()
        bare = re.sub(r'\d+$', '', source.rstrip('+-'))
        is_member = (bare in members) or (source.rstrip('+-') in members)
        if not is_member:
            continue  # bar counts MEMBER would-passes only
        key = (token.upper(), direction, ts[:10])
        if key in seen:
            continue
        seen.add(key)
        evs.append({'ts': ts, 'token': token, 'direction': direction, 'source': source})
    return evs, raw


def read_btc_standalone():
    evs, raw = standalone_events()
    joined, skipped = join_and_bar(evs)
    st = bar_stats(joined)
    print('=== btc-standalone-deny-shadow ===')
    print(f'  raw={raw} member_tokday={len(evs)} joinable={len(joined)} skipped={dict(skipped)}')
    if not st:
        print('  NO DATA -> bar not met (default: keep flat-deny)')
        return {'bar_met': False, 'reason': 'no data'}
    print(f"  n={st['n']} WR={st['wr']:.1f}% avg={st['avg_fwd']:+.4f}% net=${st['net']:+.3f} "
          f"days+={st['days_pos']}/{st['days_total']} ({st['pos_ratio']:.2f})")
    limbs = {
        'n>=30': st['n'] >= 30,
        'net>=1.50': st['net'] >= 1.50,
        'days 2/3': st['pos_ratio'] >= 2 / 3,
    }
    for k, v in limbs.items():
        print(f"  {'PASS' if v else 'FAIL'} {k}")
    return {'bar_met': all(limbs.values()), 'limbs': limbs, **st}


# ── 2. SETUP-RECALL ──────────────────────────────────────────────────────────
def read_setup_recall():
    pat = re.compile(r'\[SETUP-RECALL-SHADOW\] (\w+) (LONG|SHORT) ([^:]+): WOULD-ALLOW')
    evs, seen, raw = [], set(), 0
    for ln in iter_lines():
        if '[SETUP-RECALL-SHADOW]' not in ln:
            continue
        raw += 1
        ts = parse_ts(ln)
        m = pat.search(ln)
        if not ts or not m:
            continue
        token, direction, source = m.group(1), m.group(2), m.group(3).strip()
        key = (token.upper(), direction, ts[:10])
        if key in seen:
            continue
        seen.add(key)
        evs.append({'ts': ts, 'token': token, 'direction': direction, 'source': source})
    joined, skipped = join_and_bar(evs)
    st = bar_stats(joined)
    print('=== setup-recall-shadow ===')
    print(f'  raw={raw} tokday={len(evs)} joinable={len(joined)} skipped={dict(skipped)}')
    if not st:
        print('  NO DATA -> bar not met')
        return {'bar_met': False}
    print(f"  n={st['n']} WR={st['wr']:.1f}% avg={st['avg_fwd']:+.4f}% net=${st['net']:+.3f} "
          f"days+={st['days_pos']}/{st['days_total']} ({st['pos_ratio']:.2f})")
    limbs = {'n>=30': st['n'] >= 30, 'net>=1.50': st['net'] >= 1.50,
             'days 2/3': st['pos_ratio'] >= 2 / 3}
    for k, v in limbs.items():
        print(f"  {'PASS' if v else 'FAIL'} {k}")
    return {'bar_met': all(limbs.values()), 'limbs': limbs, **st}


# ── 3. SHORT-REGIME tape-split ──────────────────────────────────────────────
def read_short_regime_tape():
    pat = re.compile(r'\[SHORT-REGIME-EXEMPT-SHADOW\] (\w+) (LONG|SHORT)')
    evs, seen = [], set()
    for ln in iter_lines():
        if '[SHORT-REGIME-EXEMPT-SHADOW]' not in ln:
            continue
        ts = parse_ts(ln)
        m = pat.search(ln)
        if not ts or not m:
            continue
        token, direction = m.group(1), m.group(2)
        if direction.upper() != 'SHORT':
            continue
        key = (token.upper(), ts[:10])
        if key in seen:
            continue
        seen.add(key)
        evs.append({'ts': ts, 'token': token, 'direction': direction, 'source': 'sr'})
    joined, skipped = join_and_bar(evs)
    conn = sqlite3.connect(CONT, timeout=5)
    for r in joined:
        r['tape'] = tape_of(r['ts'], conn)
    conn.close()
    print('=== short-regime-exempt tape-split (CEO amendment) ===')
    print(f'  tokday={len(evs)} joinable={len(joined)} skipped={dict(skipped)}')
    for tape in ('trend', 'chop'):
        sub = [r for r in joined if r['tape'] == tape]
        st = bar_stats(sub)
        if st:
            print(f"  {tape:6s} n={st['n']} WR={st['wr']:.1f}% net=${st['net']:+.3f} "
                  f"days+={st['days_pos']}/{st['days_total']} avg={st['avg_fwd']:+.4f}%")
        else:
            print(f'  {tape:6s} n=0')
    st_all = bar_stats(joined)
    if st_all:
        print(f"  ALL n={st_all['n']} net=${st_all['net']:+.3f} days+={st_all['days_pos']}/{st_all['days_total']}")
        limbs = {'n>=15': st_all['n'] >= 15, 'net>=0.50': st_all['net'] >= 0.50,
                 'days 2/3': st_all['pos_ratio'] >= 2 / 3}
        for k, v in limbs.items():
            print(f"  {'PASS' if v else 'FAIL'} {k}")
        return {'bar_met': all(limbs.values()), 'limbs': limbs, **st_all}
    return {'bar_met': False}


# ── 4. LONG-BYPASS blocked cohort ───────────────────────────────────────────
def read_long_bypass():
    pat = re.compile(r'\[LONG-BYPASS-SHORT-BIAS-BLOCK\] (\w+) LONG BLOCKED')
    evs, seen, raw = [], set(), 0
    for ln in iter_lines():
        if '[LONG-BYPASS-SHORT-BIAS-BLOCK]' not in ln or 'BLOCKED' not in ln:
            continue
        raw += 1
        ts = parse_ts(ln)
        m = pat.search(ln)
        if not ts or not m:
            continue
        token = m.group(1)
        if token.upper() == 'TST':
            continue  # selfcheck stubs
        key = (token.upper(), ts[:10])
        if key in seen:
            continue
        seen.add(key)
        evs.append({'ts': ts, 'token': token, 'direction': 'LONG', 'source': 'bypass'})
    # window: last 14d only
    cut = (datetime.now(timezone.utc) - __import__('datetime').timedelta(days=14))
    cut_s = cut.strftime('%Y-%m-%d %H:%M:%S')
    evs = [e for e in evs if e['ts'] >= cut_s]
    joined, skipped = join_and_bar(evs)
    st = bar_stats(joined)
    print('=== long-bypass-regime blocked cohort (bar: 14d net > 0 -> back to shadow) ===')
    print(f'  raw={raw} tokday_14d={len(evs)} joinable={len(joined)} skipped={dict(skipped)}')
    if not st:
        print('  NO DATA -> keep LIVE block (default)')
        return {'bar_met': False, 'reason': 'no data'}
    print(f"  n={st['n']} WR={st['wr']:.1f}% avg={st['avg_fwd']:+.4f}% net=${st['net']:+.3f} "
          f"days+={st['days_pos']}/{st['days_total']}")
    bar = st['net'] > 0
    print(f"  {'PASS -> convert back to shadow' if bar else 'FAIL -> stay LIVE'} (net>0 = {bar})")
    return {'bar_met': bar, **st}


# ── 5. jup metadata counterfactuals ─────────────────────────────────────────
def jup_meta():
    import psycopg2
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""
        SELECT signal, direction, pnl_usdt, status,
               _signal_metadata->>'jup_cluster_size',
               _signal_metadata->>'rsi_14', _signal_metadata->>'z_score',
               _signal_metadata->>'jup_win_rate', _signal_metadata->>'jup_trades',
               _signal_metadata->>'jup_margin_usd'
        FROM trades
        WHERE status='closed' AND signal LIKE 'jup_yolo%'
          AND close_time > NOW() - INTERVAL '30 days'
    """)
    rows = cur.fetchall()
    conn.close()
    print(f'=== jup metadata counterfactuals (30d closed n={len(rows)}) ===')

    def net(sub):
        return round(sum(r[2] for r in sub), 2)

    def wr(sub):
        return round(100.0 * sum(1 for r in sub if r[2] > 0) / len(sub), 1) if sub else 0

    # cluster
    def clu(r):
        try:
            return int(r[4]) if r[4] is not None else None
        except Exception:
            return None
    have = [r for r in rows if clu(r) is not None]
    for label, pred in [('clu>=2', lambda c: c >= 2), ('clu>=4', lambda c: c >= 4)]:
        kept = [r for r in have if pred(clu(r))]
        blocked = [r for r in have if not pred(clu(r))]
        delta = net(kept) - net(have) if have else 0  # vs keep-all = -blocked contribution
        # net delta of applying gate = -net(blocked) (we lose blocked PnL, keep kept)
        gate_delta = -net(blocked)
        print(f'  cluster {label}: kept n={len(kept)} net=${net(kept):+.2f} WR={wr(kept)} | '
              f'blocked n={len(blocked)} net=${net(blocked):+.2f} WR={wr(blocked)} | '
              f'gate_delta=${gate_delta:+.2f} (bar +0.50)')

    # anti-chase: rsi>=55
    def rsi(r):
        try:
            return float(r[5]) if r[5] is not None else None
        except Exception:
            return None
    have_r = [r for r in rows if rsi(r) is not None]
    blocked_r = [r for r in have_r if rsi(r) >= 55]
    kept_r = [r for r in have_r if rsi(r) < 55]
    gate_delta = -net(blocked_r)
    print(f'  anti-chase rsi>=55: blocked n={len(blocked_r)} net=${net(blocked_r):+.2f} WR={wr(blocked_r)} | '
          f'kept n={len(kept_r)} net=${net(kept_r):+.2f} WR={wr(kept_r)} | gate_delta=${gate_delta:+.2f}')

    # z>=1.5
    def z(r):
        try:
            return float(r[6]) if r[6] is not None else None
        except Exception:
            return None
    have_z = [r for r in rows if z(r) is not None]
    blocked_z = [r for r in have_z if z(r) >= 1.5]
    kept_z = [r for r in have_z if z(r) < 1.5]
    print(f'  anti-chase z>=1.5: blocked n={len(blocked_z)} net=${net(blocked_z):+.2f} WR={wr(blocked_z)} | '
          f'kept n={len(kept_z)} net=${net(kept_z):+.2f} | gate_delta=${-net(blocked_z):+.2f}')

    # pro-selection: jwr cap 0.55
    def jwr(r):
        try:
            return float(r[7]) if r[7] is not None else None
        except Exception:
            return None
    have_j = [r for r in rows if jwr(r) is not None]
    blocked_j = [r for r in have_j if jwr(r) >= 0.55]
    kept_j = [r for r in have_j if jwr(r) < 0.55]
    print(f'  pro jwr>=0.55: blocked n={len(blocked_j)} net=${net(blocked_j):+.2f} WR={wr(blocked_j)} | '
          f'kept n={len(kept_j)} net=${net(kept_j):+.2f} | gate_delta=${-net(blocked_j):+.2f}')
    # experience floor >=100
    def exp(r):
        try:
            return int(r[8]) if r[8] is not None else None
        except Exception:
            return None
    have_e = [r for r in rows if exp(r) is not None]
    blocked_e = [r for r in have_e if exp(r) < 100]
    kept_e = [r for r in have_e if exp(r) >= 100]
    print(f'  exp<100 block: blocked n={len(blocked_e)} net=${net(blocked_e):+.2f} | '
          f'kept n={len(kept_e)} net=${net(kept_e):+.2f} | gate_delta=${-net(blocked_e):+.2f}')


def selfcheck():
    assert callable(join_and_bar) and callable(bar_stats)
    # bar_stats sanity
    rows = [{'fwd': 1.0, 'day': '2026-11-01'}, {'fwd': -0.5, 'day': '2026-11-01'},
            {'fwd': 2.0, 'day': '2026-11-02'}]
    st = bar_stats(rows, notional=100)
    assert st['n'] == 3 and st['days_total'] == 2 and st['days_pos'] == 2, st
    # member filter sanity
    from hermes_constants import STANDALONE_BYPASS_SIGNALS
    members = set()
    for s in STANDALONE_BYPASS_SIGNALS:
        members.add(s)
        members.add(re.sub(r'\d+$', '', s.rstrip('+-')))
    assert 'pump-chain' in members
    assert re.sub(r'\d+$', '', 'pump-chain+'.rstrip('+-')) in members
    print('SELFCHECK PASS')
    return 0


def main():
    if '--selfcheck' in sys.argv:
        return selfcheck()
    out = {}
    out['btc_standalone'] = read_btc_standalone()
    out['setup_recall'] = read_setup_recall()
    out['short_regime_tape'] = read_short_regime_tape()
    out['long_bypass'] = read_long_bypass()
    jup_meta()
    path = os.path.join(HERMES, 'data/disposition_deadline_2026-11-17.json')
    with open(path + '.tmp', 'w') as f:
        json.dump(out, f, indent=2, default=str)
    os.replace(path + '.tmp', path)
    print(f'wrote {path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
