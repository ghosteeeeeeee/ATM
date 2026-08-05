#!/usr/bin/env python3
"""Analyze big winners vs small-loss trades — what separates them?

Usage: python3 analyze_winners.py

Outputs:
- Group breakdown (big wins vs small wins vs small losses vs big loss)
- Co-signal fingerprints for each group
- Big winner details (what makes them win)
"""
import json

data = json.load(open('/var/www/hermes/data/trades.json'))
closed = data.get('closed', [])
print(f'Total closed: {len(closed)}')

big_wins   = [t for t in closed if t['pnl_pct'] > 1.0]
big_loss   = [t for t in closed if t['pnl_pct'] < -1.0]
small_win  = [t for t in closed if 0 < t['pnl_pct'] <= 1.0]
small_loss = [t for t in closed if -1.0 <= t['pnl_pct'] <= 0]

print(f'Big wins (>1%):   {len(big_wins)}')
print(f'Small wins (0-1%): {len(small_win)}')
print(f'Small loss (-1-0%): {len(small_loss)}')
print(f'Big loss (<-1%):   {len(big_loss)}')
print()

def summarize(label, trades):
    if not trades:
        print(f'{label}: n=0\n'); return
    dirs = {}
    confs = []; levs = []; pnls = []; src_parts = {}
    for t in trades:
        dirs[t['direction']] = dirs.get(t['direction'], 0) + 1
        confs.append(t['confidence']); levs.append(t['leverage']); pnls.append(t['pnl_pct'])
        for p in t['signal'].split(','):
            src_parts[p] = src_parts.get(p, 0) + 1
    wr = sum(1 for p in pnls if p > 0) / len(pnls) * 100
    avg = sum(pnls) / len(pnls)
    print(f'{label}: n={len(trades)} avg={avg:+.3f}% conf={sum(confs)/len(confs):.1f} lev={sum(levs)/len(levs):.1f}x LONG={dirs.get("LONG",0)} SHORT={dirs.get("SHORT",0)}')
    top = sorted(src_parts.items(), key=lambda x: -x[1])[:5]
    print(f'  signals: {", ".join(f"{s}({c})" for s,c in top)}')
    print(f'  tokens: {", ".join(t["coin"] for t in trades[:6])}')
    print()

summarize('Big wins (>1%)', big_wins)
summarize('Big loss (<-1%)', big_loss)
summarize('Small wins (0-1%)', small_win)
summarize('Small loss (-1-0%)', small_loss)

print('=== Big winner details ===')
for t in sorted(big_wins, key=lambda x: -x['pnl_pct']):
    print(f"  {t['coin']:<10} pnl={t['pnl_pct']:+.2f}%  signal={t['signal']:<55}  conf={t['confidence']}  lev={t['leverage']}")

print()
print('=== Small loss breakdown (SL vs other close) ===')
sl_losses = [t for t in small_loss if t.get('close_reason') == 'atr_sl_hit']
other = [t for t in small_loss if t.get('close_reason') != 'atr_sl_hit']
print(f'  SL hits: {len(sl_losses)}, Other: {len(other)}')
for t in sorted(sl_losses, key=lambda x: x['pnl_pct'])[:6]:
    print(f"  {t['coin']:<10} pnl={t['pnl_pct']:.3f}%  signal={t['signal']:<55}  conf={t['confidence']}")