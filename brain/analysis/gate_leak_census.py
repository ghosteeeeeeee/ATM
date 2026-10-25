#!/usr/bin/env python3
"""Gate-leak census — did the SHORT RSI gates actually hold?

Scope is deliberately narrow: only rules whose gate input IS `_signal_metadata.rsi_14`
(meta = signal-time RSI, what brain.py / the approval floor / the midband block read).
SHORT ceiling and every LONG RSI rule are EXEC-time (`compute_rsi` at gate evaluation),
so the DB cannot adjudicate them — they are counted OUT-OF-SCOPE, never LEAK.

Verified by hand 2026-10-25 run #140 (this script reproduces that verdict):
  * pipeline.log ✅/🚫 lines, not the DB, are authoritative for exec-time gates
  * `_signal_metadata.rsi_exec` is stamped at PERSIST time, not gate time
    (PUMP #16361: gate live=43.4, stamped exec=33.39) — never usable as gate input
  * ai-trader-pending is a separate execution path (CEO conditional orders); the
    approval floor correctly blocks the pipeline path while pending orders open

  python3 brain/analysis/gate_leak_census.py [--days 14] [--selfcheck]
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from paths import *  # noqa

import psycopg2
from hermes_constants import (  # noqa
    SHORT_RSI_HARD_FLOOR, OVERSOLD_SHORT_RSI_MAX,
    SHORT_MIDBAND_RSI_MIN, SHORT_MIDBAND_RSI_MAX,
)

MIDBAND_LIVE = '2026-10-16 00:00:00'          # SHORT_MIDBAND block shipped
# SHORT_RSI_HARD_FLOOR history (git -S on hermes_constants.py):
#   <2026-10-07 04:38:49 -> 25 | ->2026-10-13 04:19:37 -> 45
#   ->2026-10-18 14:40:11 -> 35 (CEO recalibration) | after -> 45 (revert)
FLOOR_45_FROM_EARLY = '2026-10-07 04:38:49'   # 25 -> 45, "NO bearish override"
FLOOR_35_FROM = '2026-10-13 04:19:37'
FLOOR_45_FROM = '2026-10-18 14:40:11'          # commit f635705c
WAIVER_LIVE = '2026-10-22 00:00:00'            # first unclog grant
PATH_EXEMPT = ('ai-trader',)                   # CEO conditional-order path


def _waiver_active(open_time):
    """unclog_waiver window from vacation_mode.json.

    Only trusted from the first grant forward — the file carries only the CURRENT
    `expires`, so an older open_time would otherwise compare as in-window.
    """
    ts = str(open_time)[:19]
    if ts < WAIVER_LIVE:
        return False
    try:
        with open(os.path.join(HERMES_DATA, 'vacation_mode.json')) as f:
            w = json.load(f).get('rules', {}).get('unclog_waiver')
        return bool(w) and w.get('expires', '0000') > ts
    except Exception:
        return False


def _floor_at(ts):
    if ts < FLOOR_45_FROM_EARLY:
        return 25
    if ts < FLOOR_35_FROM:
        return 45
    if ts < FLOOR_45_FROM:
        return 35
    return SHORT_RSI_HARD_FLOOR


def _band(rsi, source, waived, open_time='2099-01-01 00:00:00'):
    """(verdict, reason) for a SHORT. verdict in ALLOW / WAIVER / LEAK."""
    ts = str(open_time)[:19]
    if ts < FLOOR_45_FROM:
        # Rule history before the 2026-10-18 revert is not modelled here (floor
        # was 25 then 45 then 35, and the approval/knife enforcement shipped in
        # stages) — caller routes these to PRE-RULE instead of adjudicating.
        return 'ALLOW', 'pre-rule era'
    src = source or ''
    if rsi < OVERSOLD_SHORT_RSI_MAX:
        return 'LEAK', f'knife {rsi:.1f} < {OVERSOLD_SHORT_RSI_MAX} (never waivable)'
    floor = _floor_at(ts)
    if rsi < floor:
        if waived:
            return 'WAIVER', f'{rsi:.1f} < {floor} — unclog bear-band active'
        return 'LEAK', f'{rsi:.1f} < {floor} — rule live, no waiver'
    if ts >= MIDBAND_LIVE:
        if 'pump-chain' in src:
            if SHORT_MIDBAND_RSI_MIN <= rsi <= SHORT_MIDBAND_RSI_MAX:
                return 'WAIVER', f'pump-chain exempt from midband {rsi:.1f}'
        elif SHORT_MIDBAND_RSI_MIN <= rsi <= SHORT_MIDBAND_RSI_MAX:
            return 'LEAK', f'midband {rsi:.1f} — non-pump-chain block must hold'
    return 'ALLOW', 'in band'


def census(days=14):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, signal, open_time, pnl_usdt,
                   _signal_metadata->>'rsi_14', _signal_metadata->>'rsi_exec'
            FROM trades
            WHERE status='closed' AND close_time > NOW() - INTERVAL %s
              AND direction = 'SHORT' AND _signal_metadata IS NOT NULL
        """, (f'{days} days',))
        rows = cur.fetchall()
    finally:
        conn.close()

    tally = {'ALLOW': 0, 'WAIVER': 0, 'LEAK': 0, 'NO_RSI': 0, 'PRE-RULE': 0}
    leaks, exempt = [], []
    drift = 0
    for tid, token, signal, open_time, pnl, meta, ex in rows:
        src = signal or ''
        if any(p in src for p in PATH_EXEMPT):
            exempt.append((tid, token, src, str(open_time)[:19]))
            continue
        if str(open_time)[:19] < FLOOR_45_FROM:
            tally['PRE-RULE'] += 1
            continue
        try:
            rsi = float(meta)
        except (TypeError, ValueError):
            tally['NO_RSI'] += 1
            continue
        try:
            if abs(float(ex) - rsi) > 10:
                drift += 1
        except (TypeError, ValueError):
            pass
        verdict, reason = _band(rsi, src, _waiver_active(open_time), open_time)
        if verdict == 'LEAK':
            leaks.append((tid, token, src, str(open_time)[:19], round(rsi, 1), reason,
                          float(pnl or 0)))
        tally[verdict] += 1
    return tally, leaks, drift, len(exempt)


def main():
    if '--selfcheck' in sys.argv:
        assert SHORT_RSI_HARD_FLOOR == 45, 'floor moved — update expectations'
        assert _floor_at('2026-10-05 00:00:00') == 25, 'pre-Oct-7 floor 25'
        assert _floor_at('2026-10-15 00:00:00') == 35, 'CEO recalibration window'
        assert _floor_at('2026-10-18 10:00:00') == 35, 'pre-revert (commit 14:40:11)'
        assert _floor_at('2026-10-18 15:00:00') == 45, 'post-revert'
        assert _band(30.0, 'x', True)[0] == 'LEAK', 'knife never waivable'
        assert _band(40.0, 'x', True)[0] == 'WAIVER', 'waiver band + waiver active'
        assert _band(40.0, 'x', False)[0] == 'LEAK', 'no waiver -> leak'
        assert _band(40.0, 'x', False, '2026-10-15 00:00:00') == ('ALLOW', 'pre-rule era'), \
            'pre-2026-10-18 rows are PRE-RULE, not adjudicated'
        assert _band(40.0, 'x', False, '2026-10-20 00:00:00')[0] == 'LEAK', \
            'floor 45 live, no waiver (Oct 18..22)'
        assert _band(50.0, 'pump-chain-', True)[0] == 'WAIVER', 'pump-chain midband exempt'
        assert _band(50.0, 'volume-buildup-', True)[0] == 'LEAK', 'non-pump midband holds'
        assert _band(56.0, 'x', True)[0] == 'ALLOW', 'above floor, outside midband'
        print('SELFCHECK PASS')
        return 0

    days = 14
    if '--days' in sys.argv:
        days = int(sys.argv[sys.argv.index('--days') + 1])
    tally, leaks, drift, exempt = census(days)
    print(f'GATE-LEAK CENSUS — last {days}d (SHORT knife / hard-floor / midband on meta rsi_14)')
    print(f'  ALLOW {tally["ALLOW"]} | WAIVER {tally["WAIVER"]} | NO_RSI {tally["NO_RSI"]} '
          f'| PATH-EXEMPT {exempt} | PRE-RULE {tally["PRE-RULE"]} | LEAK {tally["LEAK"]}')
    print(f'  adjudicated from {FLOOR_45_FROM} (2026-10-18 revert) — earlier rows are '
          f'PRE-RULE (floor was 25/45/35, enforcement shipped in stages)')
    print(f'  drift: {drift} trades with |rsi_exec - rsi_14| > 10 '
          f'(info — stamped rsi_exec is persist-time, not gate-time)')
    print('  OUT-OF-SCOPE (exec-time gate input, not adjudicable from DB): '
          'SHORT ceiling 65/75, all LONG RSI rules')
    for l in leaks:
        print(f'  LEAK  #{l[0]} {l[1]} {l[2]} {l[3]} rsi={l[4]} -> {l[5]} pnl={l[6]:+.2f}')
    print('  VERDICT: ' + ('GAPS FOUND — verify each in pipeline.log' if leaks else
                           'all executed SHORTs explainable — gates holding'))
    return 1 if leaks else 0


if __name__ == '__main__':
    sys.exit(main())
