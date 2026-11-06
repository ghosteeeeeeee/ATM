#!/usr/bin/env python3
"""
linreg_both_sides_regime_test.py — evaluate the CEO proposal: "don't longs
and shorts fire for the signal? can we try and follow the trend?"

The system already has trend gates built for exactly this:
  - SHORT blocked while BTC bullish: score>60 sustained >=30min AND
    zscore_tier != 'STRONG_NEG' (SHORT-CONTINUUM), unless bearish structure
  - LONG blocked while BTC bearish structure (CONTINUUM-BLOCK), unless coin
    rising (omitted here — approximation noted below)

This script re-runs the fade event backtest (both sides, fixed 8h, V8 exits)
and filters events through those REAL gates, reconstructed from the system's
own continuum.db BTC state history (2026-08-12 -> now, 30s resolution).

Cohorts compared:
  A. current ship : SHORT only, no gate        (LINREG_FADE_MINUS only)
  B. both sides   : LONG+SHORT, no gate        (what the CEO asks about)
  C. both sides   : + system trend gates       (the proposal)

Approximations (documented, both directions): token-level momentum/oversold
overrides omitted (conservative for SHORT); LONG-side LONG-NEUTRAL token
regime gate omitted (optimistic for LONG); hysteresis approximated by
requiring score>60 both now and 30min ago.

Usage: python3 scripts/analysis/linreg_both_sides_regime_test.py [--tf 15m|1m]
"""
import os
import sys
import sqlite3
import datetime

import numpy as np

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS_DIR)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA  # noqa: E402
import linreg_fade_backtest as B  # noqa: E402

CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')

BEARISH_PHASES = ('DECLINING', 'CALM', 'RECOVERY')
BEARISH_LINREG = ('LEAN_BEAR', 'BEAR')
BEARISH_EMA = ('BELOW', 'AT')
BULL_LINREG = ('LEAN_BULL', 'BULL')
BULL_EMA = ('ABOVE', 'AT')


def load_btc_states():
    """BTC continuum state timeline: arrays sorted by ts."""
    conn = sqlite3.connect(CONTINUUM_DB, timeout=15)
    try:
        rows = conn.execute("""
            SELECT ts, state_score, zscore_tier, market_phase,
                   linreg_direction, ema300_position
            FROM continuum_states WHERE token='BTC' ORDER BY ts""").fetchall()
    finally:
        conn.close()
    if not rows:
        raise SystemExit('no BTC continuum states — cannot gate')
    ts = np.array([r[0] for r in rows], dtype=np.int64)
    score = np.array([r[1] if r[1] is not None else 50.0 for r in rows])
    z = [r[2] or 'NEUTRAL' for r in rows]
    phase = [r[3] or '' for r in rows]
    linreg = [r[4] or '' for r in rows]
    ema = [r[5] or '' for r in rows]
    return dict(ts=ts, score=score, z=z, phase=phase, linreg=linreg, ema=ema)


def state_at(s, t):
    """Latest BTC state at-or-before t (int ts). None if before history."""
    i = int(np.searchsorted(s['ts'], t, side='right')) - 1
    if i < 0:
        return None
    return i


def gate_short(s, i, t):
    """True = SHORT allowed by the system's rules at state i / time t."""
    if i is None:
        return None
    bearish = (s['phase'][i] in BEARISH_PHASES
               and s['linreg'][i] in BEARISH_LINREG
               and s['ema'][i] in BEARISH_EMA)
    if bearish:
        return True                       # CONTINUUM-OVERRIDE allows SHORT
    score = s['score'][i]
    if s['z'][i] == 'STRONG_NEG':
        return True                       # ALLOW_Z
    # hysteresis: score>60 now AND >=30min ago
    i30 = state_at(s, t - 30 * 60)
    sustained = score > 60 and (i30 is not None and s['score'][i30] > 60)
    return not sustained                   # blocked only when sustained >60


def gate_long(s, i):
    """True = LONG allowed: blocked only on BTC bearish structure."""
    if i is None:
        return None
    bearish = (s['phase'][i] in BEARISH_PHASES
               and s['linreg'][i] in BEARISH_LINREG
               and s['ema'][i] in BEARISH_EMA)
    return not bearish


def cohort_report(name, events, split_ts):
    print(f'\n--- {name} ---')
    for period, sel in [('IS ', lambda e: not e['oos']),
                        ('OOS', lambda e: e['oos']),
                        ('ALL', lambda e: True)]:
        sub = [e for e in events if sel(e)]
        if not sub:
            print(f'  [{period}] n=0'); continue
        for side in ['LONG', 'SHORT']:
            g = [e for e in sub if e['side'] == side]
            if not g:
                continue
            nets = [e['net'] for e in g]
            w = sum(1 for x in nets if x > 0)
            print(f"  [{period}] {side:6} n={len(g):<6} WR={100*w/len(g):5.1f}% "
                  f"avg={np.mean(nets):+.4f}% sum={sum(nets):+.1f}")
    # combined (both sides together = the book)
    for period, sel in [('IS ', lambda e: not e['oos']),
                        ('OOS', lambda e: e['oos']),
                        ('ALL', lambda e: True)]:
        sub = [e for e in events if sel(e)]
        if not sub:
            continue
        nets = [e['net'] for e in sub]
        w = sum(1 for x in nets if x > 0)
        print(f"  [{period}] BOOK  n={len(sub):<6} WR={100*w/len(sub):5.1f}% "
              f"avg={np.mean(nets):+.4f}% sum={sum(nets):+.1f}")
    print('  by month:')
    for mo in sorted(set(e['month'] for e in events)):
        g = [e for e in events if e['month'] == mo]
        nets = [e['net'] for e in g]
        w = sum(1 for x in nets if x > 0)
        sides = {}
        for e in g:
            sides.setdefault(e['side'], []).append(e['net'])
        sd = ' '.join(f"{k}:{len(v):>4}n/{np.mean(v):+.3f}%" for k, v in sorted(sides.items()))
        print(f"    {mo} n={len(g):<5} WR={100*w/len(g):5.1f}% avg={np.mean(nets):+.4f}% | {sd}")


def main():
    tf = '15m'
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == '--tf' and i + 1 < len(argv):
            tf = argv[i + 1]
    B.configure(tf)
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    import linreg_forecast_research as R
    data = B.load_token(0, now, min_bars=R.MIN_BARS)
    all_ts = np.concatenate([d['ts'] for d in data.values()])
    split_ts = all_ts.min() + (all_ts.max() - all_ts.min()) * 0.70
    print(f'tf={tf} tokens={len(data)} split='
          f'{datetime.datetime.utcfromtimestamp(split_ts)}')

    variants = [('V1 both sides fixed', 'fixed', 0.0, 0.0, 'none')]
    events, baselines, _ = B.run_events(data, split_ts, variants,
                                        gate_type='none', regime=None,
                                        regime4h=None)
    ev = events['V1 both sides fixed']
    print(f'raw both-side events: {len(ev)}')

    states = load_btc_states()
    print(f'BTC continuum states: {len(states["ts"])} '
          f'({datetime.datetime.utcfromtimestamp(states["ts"][0])} -> now)')

    gated, skipped_no_state = [], 0
    for e in ev:
        i = state_at(states, e['ts'])
        if i is None:
            skipped_no_state += 1
            continue
        if e['side'] == 'SHORT':
            ok = gate_short(states, i, e['ts'])
        else:
            ok = gate_long(states, i)
        if ok:
            gated.append(e)
    print(f'events before continuum history: {skipped_no_state} (excluded)')

    short_only = [e for e in ev if e['side'] == 'SHORT']
    both = ev
    cohort_report('A. CURRENT SHIP — SHORT only, ungated', short_only, split_ts)
    cohort_report('B. BOTH SIDES, ungated', both, split_ts)
    cohort_report('C. PROPOSAL — both sides + system trend gates', gated, split_ts)


if __name__ == '__main__':
    main()
