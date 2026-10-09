#!/usr/bin/env python3
"""
pump_chain_v6_calibration.py — MANDATORY pre-enable calibration (spec rev1 §4 G4 / §9.2)

Recomputes momentum_state from 1-minute price_history bars at the historical pump-chain
signal times (signal_time = open_time - staleness_minutes) and measures agreement with
the stored _signal_metadata momentum_state labels the v6 gates were validated against.

GATE: agreement >= 75% required (auditor measured 77.1%). Below 75% -> HALT, re-audit.
Anchor set: hyphen-sample trades with non-NULL staleness (175 of 260); the 44 underscore
trades have NULL staleness and cannot be anchors (re-audit note #6).
"""
import json
import sys
import sqlite3
import time

import psycopg2

sys.path.insert(0, '/root/.hermes/scripts')

AGREEMENT_FLOOR = 0.75


def load_anchors():
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""
        SELECT token, direction, open_time,
               (_signal_metadata->>'staleness_minutes')::numeric AS staleness,
               _signal_metadata->>'momentum_state' AS label
        FROM trades
        WHERE status='closed' AND signal LIKE '%%pump-chain%%'
          AND open_time > now() - interval '60 days'
          AND _signal_metadata IS NOT NULL
          AND (_signal_metadata->>'staleness_minutes') IS NOT NULL
          AND _signal_metadata->>'momentum_state' IS NOT NULL
        ORDER BY open_time;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def momentum_at(token, ts_epoch):
    """Exact historical formula: 5-bar velocity over 1-minute price_history bars
    ending at ts_epoch. Mirrors signal_schema._enrich_indicators lines 494-497."""
    db = '/root/.hermes/data/signals_hermes.db'
    conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=10)
    try:
        cur = conn.cursor()
        # Last 6 one-minute bars up to (and including) the signal time
        cur.execute("""
            SELECT price FROM price_history
            WHERE token = ? AND timestamp > ? AND timestamp <= ?
            ORDER BY timestamp DESC LIMIT 6
        """, (token.upper(), ts_epoch - 3600, ts_epoch))
        prices = [r[0] for r in reversed(cur.fetchall())]
        cur.close()
        if len(prices) >= 6 and prices[-6]:
            vel = (prices[-1] - prices[-6]) / prices[-6] * 100
            return 'rising' if vel > 0.1 else 'falling' if vel < -0.1 else 'flat'
    except Exception as e:
        print(f'  [WARN] {token}@{ts_epoch}: {type(e).__name__}: {e}')
    finally:
        conn.close()
    return None


def main():
    anchors = load_anchors()
    print(f'Anchors (hyphen trades with non-NULL staleness + momentum label): {len(anchors)}')

    agree = disagree = no_data = 0
    flips = []          # trades where the flat-block decision would differ
    disagreements = []

    for (token, direction, open_time, staleness, label) in anchors:
        ts_epoch = int((open_time.timestamp() - float(staleness) * 60))
        computed = momentum_at(token, ts_epoch)
        if computed is None:
            no_data += 1
            continue
        if computed == label:
            agree += 1
        else:
            disagree += 1
            disagreements.append((token, direction, open_time, label, computed))
        # flat-block gate decision comparison
        if (label == 'flat') != (computed == 'flat'):
            flips.append((token, direction, open_time, label, computed))

    total = agree + disagree
    print(f'With data: {total}  |  no 1m data: {no_data}')
    if total == 0:
        print('HALT — no anchors could be recomputed')
        sys.exit(2)

    rate = agree / total
    print(f'\nAgreement: {agree}/{total} = {rate:.1%}  (floor: {AGREEMENT_FLOOR:.0%})')
    print(f'Flat-block decision flips: {len(flips)}/{total} = {len(flips)/total:.1%} '
          f'(auditor measured 47/175 = 26.9% for the WRONG 5m formula; the correct 1m '
          'formula was validated WITH these flips as dilution)')

    if disagreements:
        print('\nFirst 15 disagreements:')
        for (tok, d, ot, lab, comp) in disagreements[:15]:
            print(f'  {tok:8s} {d:5s} {ot} label={lab:8s} computed={comp}')

    if rate >= AGREEMENT_FLOOR:
        print(f'\nPASS — calibration {rate:.1%} >= {AGREEMENT_FLOOR:.0%}. V6 may stay enabled.')
        sys.exit(0)
    else:
        print(f'\nHALT — calibration {rate:.1%} < {AGREEMENT_FLOOR:.0%}. '
              'Disable PUMP_CHAIN_V6_ENABLED and re-audit (spec §9.2).')
        sys.exit(1)


if __name__ == '__main__':
    main()
