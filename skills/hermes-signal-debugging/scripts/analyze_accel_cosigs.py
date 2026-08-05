#!/usr/bin/env python3
"""Analyze co-signal patterns vs PnL in closed trades.json.

Usage: python3 analyze_accel_cosigs.py

Key metrics:
- Which co-signals improve accel-300+ WR
- RS touch count vs PnL correlation
- Big winners vs small loss breakdown
"""
import json, re

data = json.load(open('/var/www/hermes/data/trades.json'))
closed = data.get('closed', [])
print(f'Total closed trades: {len(closed)}')

# ── Accel-300+ co-signal breakdown ──────────────────────────────────────────
print('\n=== accel-300+ with/without RS co-signal ===')
groups = {}
for t in closed:
    src = t.get('signal', '')   # NOT 'source'
    pnl = t.get('pnl_pct', 0)   # NOT 'pnl'
    is_accel = 'accel-300' in src
    has_rs = bool(re.search(r'rs-[sr]\d+', src))
    key = 'accel+rs' if (is_accel and has_rs) else ('accel alone' if is_accel else 'other')
    if key not in groups:
        groups[key] = {'count':0,'wins':0,'pnl':0.0,'tokens':[]}
    groups[key]['count'] += 1
    groups[key]['wins'] += 1 if pnl > 0 else 0
    groups[key]['pnl'] += pnl
    groups[key]['tokens'].append((t.get('coin'), pnl))

for k, v in sorted(groups.items(), key=lambda x: -x[1]['count']):
    wr = v['wins']/v['count']*100 if v['count'] > 0 else 0
    avg = v['pnl']/v['count'] if v['count'] > 0 else 0
    print(f'{k:15s} n={v["count"]:2d}  WR={wr:5.1f}%  avg={avg:+.3f}%')

# ── RS touch count vs PnL ──────────────────────────────────────────────────
print('\n=== RS touch count vs PnL ===')
rs_buckets = {'1-20': [], '21-50': [], '51-100': [], '100+': []}
accel_only_pnls = []

for t in closed:
    src = t.get('signal', '')
    pnl = t.get('pnl_pct', 0)
    if 'accel-300' not in src:
        continue
    m = re.search(r'rs-([sr])(\d+)', src)
    if m:
        touches = int(m.group(2))
        if touches <= 20:   rs_buckets['1-20'].append(pnl)
        elif touches <= 50: rs_buckets['21-50'].append(pnl)
        elif touches <= 100: rs_buckets['51-100'].append(pnl)
        else:               rs_buckets['100+'].append(pnl)
    else:
        accel_only_pnls.append(pnl)

if accel_only_pnls:
    print(f'Accel alone (no RS): {len(accel_only_pnls)} trades, avg={sum(accel_only_pnls)/len(accel_only_pnls):.3f}%')

for range_k, pnls in rs_buckets.items():
    if not pnls: continue
    wr = sum(1 for p in pnls if p > 0) / len(pnls) * 100
    avg = sum(pnls) / len(pnls)
    print(f'  RS {range_k} touches: n={len(pnls)} WR={wr:.0f}% avg={avg:+.3f}%')

# ── Big winners vs small losses ─────────────────────────────────────────────
print('\n=== Big winners (pnl > 1%) ===')
for t in sorted(closed, key=lambda x: -x['pnl_pct']):
    if t['pnl_pct'] > 1.0:
        print(f"  {t['coin']:<10} pnl={t['pnl_pct']:+.2f}%  signal={t['signal']:<55}  conf={t['confidence']}")

print('\n=== Small losses (-1-0% with SL hit) ===')
sl_losses = [t for t in closed if -1.0 <= t['pnl_pct'] <= 0 and t.get('close_reason') == 'atr_sl_hit']
for t in sorted(sl_losses, key=lambda x: x['pnl_pct'])[:8]:
    print(f"  {t['coin']:<10} pnl={t['pnl_pct']:.3f}%  signal={t['signal']:<55}  conf={t['confidence']}")