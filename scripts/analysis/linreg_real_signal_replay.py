#!/usr/bin/env python3
"""
linreg_real_signal_replay.py — replay the REAL fired linreg_fade signals
through the shipped V8 exit structure (wide 6% SL, NO trailing, 8h close,
0.09% round-trip fees) to answer: "the 78 signals already fired — how did
they fare, with simulated exit data?"

Complements shadow_trades (which simulates the OLD production engines):
this replay answers "what would our SHIPPED structure have done".

Usage: python3 scripts/analysis/linreg_real_signal_replay.py
"""
import os
import sys
import json
import sqlite3
import datetime

import numpy as np

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS_DIR)
from paths import HERMES_DATA  # noqa: E402

CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
SHADOW_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'shadow_trades.db')
SIGNALS_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')

FEE_RT = 0.09
SL_PCT = 0.06
TP_PCT = 0.06          # wide TP (rarely hit, mirrors decider branch)
HOLD_BARS = 480        # 8h of 1m candles


def parse_ts(s):
    return datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S').replace(
        tzinfo=datetime.timezone.utc).timestamp()


def load_signal_rows():
    conn = sqlite3.connect(SIGNALS_DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, token, direction, confidence, created_at
        FROM signals WHERE signal_type LIKE 'linreg%'
        ORDER BY id""").fetchall()
    conn.close()
    return rows


def load_shadow_map():
    """shadow_trades recorded outcome + engine sims, keyed by signal_id."""
    out = {}
    if not os.path.exists(SHADOW_DB):
        return out
    conn = sqlite3.connect(SHADOW_DB)
    conn.row_factory = sqlite3.Row
    for r in conn.execute("""
        SELECT signal_id, net_pnl_pct, first_exit_reason, first_exit_pnl_pct,
               exit_atr_json, exit_hard_max_json, exit_universal_hold_json
        FROM shadow_trades WHERE signal_type LIKE 'linreg%'"""):
        out[r['signal_id']] = dict(r)
    conn.close()
    return out


def get_bars(token, start_ts, need=HOLD_BARS + 2):
    conn = sqlite3.connect(CANDLES_DB, timeout=15)
    try:
        rows = conn.execute(
            "SELECT ts, open, high, low, close FROM candles_1m "
            "WHERE token=? AND is_closed=1 AND ts >= ? ORDER BY ts LIMIT ?",
            (token.upper(), int(start_ts), need)).fetchall()
        return rows
    finally:
        conn.close()


def simulate(side, bars):
    """V8: wide 6% SL/TP, no trailing, time exit at 8h. Returns dict or None."""
    if not bars or len(bars) < 2:
        return None
    entry = bars[0][1]  # open of first bar at/after signal time
    if not entry or entry <= 0:
        return None
    if side == 'LONG':
        sl = entry * (1 - SL_PCT)
        tp = entry * (1 + TP_PCT)
    else:
        sl = entry * (1 + SL_PCT)
        tp = entry * (1 - TP_PCT)
    for i, (ts, o, hi, lo, c) in enumerate(bars[1:], start=1):
        if side == 'LONG':
            if lo <= sl:
                exit_px, kind = sl, 'SL'
                break
            if hi >= tp:
                exit_px, kind = tp, 'TP'
                break
        else:
            if hi >= sl:
                exit_px, kind = sl, 'SL'
                break
            if lo <= tp:
                exit_px, kind = tp, 'TP'
                break
        if i >= HOLD_BARS:
            exit_px, kind = c, 'TIME'
            break
    else:
        exit_px, kind = bars[-1][4], 'TIME_TRUNC'
    gross = ((exit_px - entry) if side == 'LONG' else (entry - exit_px)) / entry * 100
    hold_min = (bars[min(i, len(bars) - 1)][0] - bars[0][0]) / 60
    return dict(entry=entry, exit_px=exit_px, kind=kind, gross=gross,
                net=gross - FEE_RT, hold_min=hold_min,
                end_ts=bars[min(i, len(bars) - 1)][0])


def main():
    rows = load_signal_rows()
    shadow = load_shadow_map()
    print(f'signals: {len(rows)}  shadow rows: {len(shadow)}')

    results = []
    for r in rows:
        sig_ts = parse_ts(r['created_at'])
        bars = get_bars(r['token'], sig_ts + 60)  # first bar starting after signal
        sim = simulate(r['direction'], bars)
        if sim is None:
            continue
        sim.update(id=r['id'], token=r['token'], direction=r['direction'],
                   confidence=r['confidence'], created=r['created_at'])
        results.append(sim)

    n = len(results)
    if not n:
        print('no replayable signals'); return
    nets = [x['net'] for x in results]
    wins = sum(1 for x in nets if x > 0)
    print(f"\n=== V8 SHIPPED STRUCTURE (wide 6% SL/TP, no trail, 8h hold) — "
          f"{n} real signals ===")
    print(f"WR={100*wins/n:.1f}%  avg_net={np.mean(nets):+.4f}%  "
          f"median={np.median(nets):+.4f}%  sum={sum(nets):+.2f}%")
    from collections import Counter
    print('exits:', dict(Counter(x['kind'] for x in results)))
    holds = [x['hold_min'] for x in results]
    print(f"hold: median={np.median(holds):.0f}min mean={np.mean(holds):.0f}min")
    trunc = sum(1 for x in results if x['kind'] == 'TIME_TRUNC')
    print(f"(TIME_TRUNC = signal younger than 8h, exit at last candle: {trunc})")

    for side in ['LONG', 'SHORT']:
        g = [x for x in results if x['direction'] == side]
        if not g:
            print(f'{side}: none'); continue
        gn = [x['net'] for x in g]
        gw = sum(1 for x in gn if x > 0)
        print(f"  {side}: n={len(g)} WR={100*gw/len(g):.1f}% "
              f"avg={np.mean(gn):+.4f}% sum={sum(gn):+.2f}%")

    # confidence buckets
    for lo, hi in [(0, 70), (70, 75), (75, 100)]:
        g = [x for x in results if lo <= x['confidence'] < hi]
        if len(g) >= 5:
            gn = [x['net'] for x in g]
            gw = sum(1 for x in gn if x > 0)
            print(f"  conf[{lo},{hi}): n={len(g)} WR={100*gw/len(g):.1f}% "
                  f"avg={np.mean(gn):+.4f}%")

    # monthly-ish split by created date
    by_day = {}
    for x in results:
        d = x['created'][:10]
        by_day.setdefault(d, []).append(x['net'])
    print('\nby day:')
    for d in sorted(by_day):
        v = by_day[d]
        w = sum(1 for x in v if x > 0)
        print(f"  {d}: n={len(v):<3} WR={100*w/len(v):5.1f}% avg={np.mean(v):+.4f}%")

    # compare with shadow's recorded (old-engine) outcome on same signals
    common = [(x, shadow[x['id']]) for x in results
              if x['id'] in shadow and shadow[x['id']]['net_pnl_pct'] is not None]
    if common:
        a = [x['net'] for x, _ in common]
        b = [s['net_pnl_pct'] for _, s in common]
        print(f"\nvs shadow recorded (old engines): same n={len(common)}")
        print(f"  V8 shipped: WR={100*sum(1 for v in a if v>0)/len(a):.1f}% avg={np.mean(a):+.4f}%")
        print(f"  shadow old: WR={100*sum(1 for v in b if v>0)/len(b):.1f}% avg={np.mean(b):+.4f}%")

    # save detail
    out = os.path.join(SCRIPTS_DIR, 'analysis', '_linreg_real_replay.json')
    with open(out, 'w') as f:
        json.dump(results, f, indent=1, default=str)
    print(f'\ndetail written: {out}')


if __name__ == '__main__':
    main()
