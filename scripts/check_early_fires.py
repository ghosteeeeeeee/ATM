#!/usr/bin/env python3
"""Check which early-firing accel-300+ tokens have RS co-signals (confluence requirement)."""
import sys, os, sqlite3, ast
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signals.accel_300 import detect_accel_300, _get_1m_prices
from signals.rs import detect_rs_signal, _get_candles_1m
from signal_schema import get_all_latest_prices, init_db

init_db()
prices = get_all_latest_prices()

# Check which early-firing accel tokens ALSO have RS signals right now
print('Token               bars  gap_pct  gg_pct   RS_available  RS_conf')
print('-' * 80)

accel_only = []; both_signals = []
stale = []

for token, data in list(prices.items())[:60]:
    if token.startswith('@'): continue
    price = data.get('price')
    if not price or price <= 0: continue

    p = _get_1m_prices(token, 700)
    if not p or len(p) < 500: continue

    sig = detect_accel_300(token, p)
    if not sig: continue

    bars = sig['bars_since_cross']
    if bars > 10:
        stale.append((token, bars, sig['gap_pct'], sig['gap_growth']))
        continue

    # Check if RS also fires for this token
    candles = _get_candles_1m(token, lookback=4700)
    rs_sig = detect_rs_signal(token, candles, price) if candles else None

    rs_avail = 'YES' if rs_sig else 'NO'
    rs_conf = f'{rs_sig["confidence"]:.0f}' if rs_sig else '-'

    print(f'{token:<20} {bars:4d}  {sig["gap_pct"]:.3f}%  {sig["gap_growth"]:.4f}%  {rs_avail:<12} {rs_conf}')

    if rs_sig:
        both_signals.append(token)
    else:
        accel_only.append(token)

print()
print(f'Summary: {len(accel_only)} accel-only, {len(both_signals)} both signals, {len(stale)} stale')
print(f'Confluence pass rate (bars<=3): {len(both_signals)}/{len(both_signals)+len(accel_only)} = {len(both_signals)/(len(both_signals)+len(accel_only))*100:.0f}%')
if accel_only:
    print(f'ACCEL-ONLY (stuck at confluence gate, need 2nd source):')
    for t in accel_only: print(f'  {t}')
if both_signals:
    print(f'BOTH (passes confluence):')
    for t in both_signals: print(f'  {t}')