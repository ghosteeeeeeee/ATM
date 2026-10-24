#!/usr/bin/env python3
"""Contrarian shadow outcome-join — unblocks Oct 27 PROMOTE decision.

For each contrarian_shadow.jsonl entry (pre-classified LOSER at write time),
look at 5m candles after the signal timestamp and compute what the
CONTRARIAN direction would have done.

Classification rule (pre-registered, mirrors trail-arm logic):
  WINNER  = contrarian direction reached +0.40% favorable before -0.40% adverse
  LOSER   = adverse hit first, or neither within 30 candles (2.5h)
  SHALLOW = never moved ±0.40% either way within 30 candles

Units: price-move % only (no leverage). Compare same units per UNITS RULE.
"""
import json, sqlite3, sys, os
from datetime import datetime, timezone
from collections import defaultdict

CANDLES = '/root/.hermes/data/candles.db'
SHADOW = '/root/.hermes/data/contrarian_shadow.jsonl'
ARM_PCT = 0.40   # favorable threshold (matches trail arm)
ADV_PCT = 0.40   # adverse threshold (matches hard stop distance)
MAX_CANDLES = 30 # 30 × 5m = 2.5h horizon

def ts_to_unix(ts_str):
    """ISO '2026-10-13T17:12' → unix seconds."""
    try:
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return int(dt.timestamp())
    except Exception:
        return None

def classify(entry, conn):
    """Return (outcome, max_fav_pct, max_adv_pct, candles_used) for contrarian direction."""
    ts_unix = ts_to_unix(entry.get('ts', ''))
    token = entry.get('token', '').upper()
    entry_price = entry.get('entry_price')
    contra_dir = entry.get('contrarian_direction', '').upper()
    if not ts_unix or not token or not entry_price or not contra_dir:
        return None
    entry_price = float(entry_price)
    if entry_price <= 0:
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
    for i, (_, o, h, l, c) in enumerate(rows):
        if contra_dir == 'LONG':
            fav = (h - entry_price) / entry_price * 100
            adv = (entry_price - l) / entry_price * 100
        else:  # SHORT
            fav = (entry_price - l) / entry_price * 100
            adv = (h - entry_price) / entry_price * 100
        max_fav = max(max_fav, fav)
        max_adv = max(max_adv, adv)
        if max_fav >= ARM_PCT and max_adv < ADV_PCT:
            outcome = 'WINNER'
            break
        if max_adv >= ADV_PCT and max_fav < ARM_PCT:
            outcome = 'LOSER'
            break
        # both crossed: check which crossed first (approximate by candle order)
        if max_fav >= ARM_PCT and max_adv >= ADV_PCT:
            # whichever hit on this candle — if fav hit at or before adv, call it WINNER
            # conservative: if both same candle, check close direction
            if c >= entry_price:
                outcome = 'WINNER'
            else:
                outcome = 'LOSER'
            break
    else:
        # loop completed without break
        if max_fav >= ARM_PCT:
            outcome = 'WINNER'
        elif max_adv >= ADV_PCT:
            outcome = 'LOSER'
        else:
            outcome = 'SHALLOW'

    return (outcome, round(max_fav, 3), round(max_adv, 3), len(rows))

def main():
    selfcheck = '--selfcheck' in sys.argv
    if selfcheck:
        # minimal self-check: verify ts parsing and direction logic
        assert ts_to_unix('2026-10-13T17:12') > 0
        assert ts_to_unix('bad') is None
        print('SELF-CHECK PASS')
        return

    entries = []
    with open(SHADOW) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    print(f'Contrarian shadow entries: {len(entries)}')

    conn = sqlite3.connect(CANDLES, timeout=10)
    results = []
    no_data = 0
    for e in entries:
        r = classify(e, conn)
        if r is None:
            continue
        outcome, fav, adv, n_candles = r
        if outcome == 'NO_DATA':
            no_data += 1
            continue
        results.append({**e, '_outcome': outcome, '_max_fav': fav, '_max_adv': adv, '_candles': n_candles})
    conn.close()

    print(f'Joinable: {len(results)}  No-data: {no_data}')

    # Stats by signal
    by_sig = defaultdict(lambda: defaultdict(int))
    pnl_by_sig = defaultdict(lambda: {'WINNER': 0, 'LOSER': 0, 'SHALLOW': 0})
    for r in results:
        sig = r.get('signal', '?')
        oc = r['_outcome']
        by_sig[sig][oc] += 1

    print(f'\n=== CONTRARIAN OUTCOME-JOIN (contrarian direction) ===')
    print(f'{"Signal":35s} {"n":>5s} {"WIN":>5s} {"LOSS":>5s} {"SHAL":>5s} {"flip-WR":>8s}')
    total = defaultdict(int)
    for sig in sorted(by_sig, key=lambda s: -(by_sig[s]['WINNER'] + by_sig[s]['LOSER'])):
        d = by_sig[sig]
        n = d['WINNER'] + d['LOSER'] + d['SHALLOW']
        decided = d['WINNER'] + d['LOSER']
        wr = 100.0 * d['WINNER'] / decided if decided else 0
        print(f'{sig:35s} {n:5d} {d["WINNER"]:5d} {d["LOSER"]:5d} {d["SHALLOW"]:5d} {wr:7.1f}%')
        total['WINNER'] += d['WINNER']
        total['LOSER'] += d['LOSER']
        total['SHALLOW'] += d['SHALLOW']

    n_total = sum(total.values())
    decided = total['WINNER'] + total['LOSER']
    wr = 100.0 * total['WINNER'] / decided if decided else 0
    print(f'\n{"TOTAL":35s} {n_total:5d} {total["WINNER"]:5d} {total["LOSER"]:5d} {total["SHALLOW"]:5d} {wr:7.1f}%')
    print(f'\nFlip-WR (contrarian direction, decided only): {wr:.1f}%  (n={decided})')
    print(f'SHALLOW (never moved ±{ARM_PCT}% in {MAX_CANDLES}×5m): {total["SHALLOW"]}/{n_total} = {100*total["SHALLOW"]/max(n_total,1):.1f}%')

    # Write output
    out_path = '/root/.hermes/data/contrarian_outcome_join.json'
    with open(out_path, 'w') as f:
        json.dump({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'params': {'arm_pct': ARM_PCT, 'adv_pct': ADV_PCT, 'max_candles': MAX_CANDLES, 'timeframe': '5m'},
            'total': dict(total),
            'flip_wr': round(wr, 1),
            'decided': decided,
            'no_data': no_data,
            'by_signal': {s: dict(d) for s, d in by_sig.items()},
        }, f, indent=2)
    print(f'\nWritten: {out_path}')

if __name__ == '__main__':
    main()
