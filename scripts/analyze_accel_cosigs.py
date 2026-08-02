#!/usr/bin/env python3
import json

data = json.load(open('/var/www/hermes/data/trades.json'))
closed = data.get('closed', [])
print(f'Total closed trades: {len(closed)}')

# Analyze co-signals with accel-300+
# Key question: does pct-hermes+ boost or hurt accel-300+ trades?
accel_trades = [t for t in closed if 'accel-300' in t.get('source','') or 'accel_300' in t.get('source','')]
print(f'\nAccel-300+ trades: {len(accel_trades)}')

# Accel alone vs accel + pct-hermes+
groups = {}
for t in closed:
    src = t.get('signal','')  # field is 'signal' not 'source'
    pnl = t.get('pnl_pct', 0)
    is_accel = 'accel-300' in src or 'accel_300' in src
    has_pct_plus = 'pct-hermes+' in src
    has_pct_minus = 'pct-hermes-' in src
    has_rs = 'rs-' in src or 'rs-s' in src or 'rs-r' in src
    has_vel = 'vel-hermes' in src
    has_tl = 'tl_break' in src

    if is_accel and has_pct_plus:
        key = 'accel+pct+'
    elif is_accel and has_pct_minus:
        key = 'accel+pct-'
    elif is_accel and has_rs:
        key = 'accel+rs'
    elif is_accel and not has_pct_plus and not has_pct_minus:
        key = 'accel alone'
    else:
        continue

    if key not in groups:
        groups[key] = {'count':0, 'wins':0, 'pnl':0.0, 'tokens':[]}
    groups[key]['count'] += 1
    groups[key]['wins'] += 1 if pnl > 0 else 0
    groups[key]['pnl'] += pnl
    groups[key]['tokens'].append((t.get('coin'), pnl))

for k, v in sorted(groups.items(), key=lambda x: -x[1]['count']):
    wr = v['wins']/v['count']*100 if v['count'] > 0 else 0
    avg = v['pnl']/v['count'] if v['count'] > 0 else 0
    print(f'{k:15s} n={v["count"]:2d}  WR={wr:5.1f}%  avg={avg:+.3f}%')
    for tok, p in (v['tokens'] or [])[:4]:
        print(f'  {str(tok):<10} pnl={p:+.3f}%')
    if len(v['tokens']) > 4:
        print(f'  ... +{len(v["tokens"])-4} more')
    print()

# Also check: what does RS alone look like in trades?
print('=== All trades by source type ===')
src_groups = {}
for t in closed:
    src = t.get('signal','')
    pnl = t.get('pnl_pct', 0)
    # extract primary signal type
    parts = src.split(',')
    primary = parts[0] if parts else src
    key = primary[:40]
    if key not in src_groups:
        src_groups[key] = {'count':0, 'wins':0, 'pnl':0.0, 'tokens':[]}
    src_groups[key]['count'] += 1
    src_groups[key]['wins'] += 1 if pnl > 0 else 0
    src_groups[key]['pnl'] += pnl
    src_groups[key]['tokens'].append((t.get('coin'), pnl))

for k, v in sorted(src_groups.items(), key=lambda x: -x[1]['count'])[:20]:
    wr = v['wins']/v['count']*100 if v['count'] > 0 else 0
    avg = v['pnl']/v['count'] if v['count'] > 0 else 0
    print(f'{k:<45s} n={v["count"]:2d}  WR={wr:5.1f}%  avg={avg:+.3f}%')