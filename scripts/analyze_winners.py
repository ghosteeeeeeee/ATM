#!/usr/bin/env python3
"""Analyze big winners vs small-loss trades to find what separates them."""
import json, sys

data = json.load(open('/var/www/hermes/data/trades.json'))
closed = data.get('closed', [])

big_wins = [t for t in closed if t['pnl_pct'] > 1.0]
small_loss = [t for t in closed if -1.0 <= t['pnl_pct'] <= 0]
big_loss = [t for t in closed if t['pnl_pct'] < -1.0]
small_win = [t for t in closed if 0 < t['pnl_pct'] <= 1.0]

print(f'Big wins (>1%):  {len(big_wins)}')
print(f'Small wins (0-1%): {len(small_win)}')
print(f'Small loss (-1-0%): {len(small_loss)}')
print(f'Big loss (<-1%): {len(big_loss)}')
print()

def analyze_group(label, trades):
    if not trades:
        print(f'{label}: n=0'); return
    src_parts = {}
    dirs = {'LONG':0,'SHORT':0}
    confs = []; levs = []; pnls = []
    for t in trades:
        dirs[t['direction']] = dirs.get(t['direction'],0) + 1
        confs.append(t['confidence'])
        levs.append(t['leverage'])
        pnls.append(t['pnl_pct'])
        for p in t['signal'].split(','):
            src_parts[p] = src_parts.get(p,0) + 1
    avg_pnl = sum(pnls)/len(pnls)
    print(f'{label}: n={len(trades)} avg_pnl={avg_pnl:+.3f}% conf={sum(confs)/len(confs):.1f} lev={sum(levs)/len(levs):.1f}x LONG={dirs.get("LONG",0)} SHORT={dirs.get("SHORT",0)}')
    # Top co-signals
    top = sorted(src_parts.items(), key=lambda x: -x[1])[:5]
    print(f'  signals: {", ".join(f"{s}({c})" for s,c in top)}')
    print(f'  tokens: {", ".join(t["coin"] for t in trades[:6])}')
    print()

analyze_group('Big wins (>1%)', big_wins)
analyze_group('Big loss (<-1%)', big_loss)
analyze_group('Small wins (0-1%)', small_win)
analyze_group('Small loss (-1-0%)', small_loss)

print('=== What do the 8 big winners have in common? ===')
for t in sorted(big_wins, key=lambda x: -x['pnl_pct']):
    print(f'  {t["coin"]:<10} pnl={t["pnl_pct"]:+.2f}% signal={t["signal"]:<50} conf={t["confidence"]} lev={t["leverage"]}')

print()
print('=== Small loss details (28 trades, -0.1 to -0% each) ===')
sl_losses = [t for t in small_loss if t.get('close_reason') == 'atr_sl_hit']
non_sl = [t for t in small_loss if t.get('close_reason') != 'atr_sl_hit']
print(f'  SL hits: {len(sl_losses)}, Other close reason: {len(non_sl)}')
for t in sorted(sl_losses, key=lambda x: x['pnl_pct'])[:8]:
    print(f'  {t["coin"]:<10} pnl={t["pnl_pct"]:.3f}% signal={t["signal"]:<50} conf={t["confidence"]}')