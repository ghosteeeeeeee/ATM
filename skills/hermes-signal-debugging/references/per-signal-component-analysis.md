# Per-Signal-Component PnL Analysis — Method and Findings (2026-05-05)

## The Method

When evaluating a hot-set signal, don't just look at the combo — decompose it and check each component against actual trade history:

```python
import json
from collections import defaultdict

with open('/var/www/hermes/data/trades.json') as f:
    d = json.load(f)
closed = d['closed']
open_trades = d['open']

def by_component(trades):
    comp_stats = defaultdict(list)
    for t in trades:
        src = t.get('signal', '')
        if not src:
            continue
        pnl = t.get('pnl_pct', 0)
        for part in src.split(','):
            part = part.strip()
            if part:
                comp_stats[part].append({'pnl': pnl, 'src': src, 'token': t.get('coin', t.get('token'))})
    return comp_stats

# Analyze LONG signals
long_closed = [t for t in closed if t.get('direction') == 'LONG']
ls = by_component(long_closed)
for comp, trades in sorted(ls.items(), key=lambda x: -len(x[1])):
    pnls = [t['pnl'] for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    avg = sum(pnls)/len(pnls) if pnls else 0
    print(f'{comp}: n={len(trades)} WR={wins/len(trades)*100:.0f}% avg={avg:.2f}%')
```

**Critical**: Check each comma-separated component individually, not the combo as a whole. A combo can appear to pass because one good component dominates the score, but weaker components may drag it below threshold.

## Current Signal Quality Table (200 closed trades)

### LONG Components
| Component | Trades | WR | Avg PnL | Status |
|-----------|--------|-----|---------|--------|
| accel-300+ | 45 | 42% | +0.55% | BEST — in open trades |
| macd-accel+ | 3 | 33% | +1.05% | Small n, strong |
| em2050+ | 5 | 40% | +0.94% | Small n, strong |
| pct-hermes+ | 36 | 33% | +0.18% | Unblocked 2026-05-05 |
| hzscore- | 26 | 35% | +0.10% | Ranging-market problem |
| trend_purity+ | 15 | 27% | +0.22% | Mediocre |
| ma-cross-5m+ | 3 | 0% | -0.35% | Bad — not in hot-set |
| vel-hermes+ | 4 | 25% | -0.18% | Blocked via SENTINEL_BASES |

### SHORT Components
| Component | Trades | WR | Avg PnL | Status |
|-----------|--------|-----|---------|--------|
| vel-hermes- | 12 | 33% | +0.32% | Blocked via SENTINEL_BASES |
| pct-hermes- | 76 | 28% | +0.15% | BLOCKED — catches knives |
| hzscore+ | 67 | 33% | +0.21% | Range market problem, not blocked |
| gap-300- | 5 | 20% | -0.16% | BLOCKED — worst active loser |

## Case Study: PURR LONG — Why OPP Penalty Was Right to Block It

Hot-set signal: `hzscore-,pct-hermes+,rs-s77`

| Component | WR | Avg PnL | Verdict |
|-----------|-----|---------|---------|
| hzscore- | 35% | +0.10% | Mediocre |
| pct-hermes+ | 33% | +0.18% | Unblocked but mediocre |
| rs-s77 | 0 trades | N/A | Too new |

**Conclusion**: OPP penalty was correctly suppressing a weak signal. Raising floor to 65% allows good signals through, but PURR's components are individually below average — it would still score low even without OPP penalty.

## Reference Good Signal: XMR LONG (currently +1.98%)

Source: `hzscore-,rs-s146,rs-s147,rs-s492`

| Component | WR | Avg PnL | Verdict |
|-----------|-----|---------|---------|
| hzscore- | 35% | +0.10% | Weak but present |
| rs-s492 | 50% | +1.09% | Strong support |
| rs-s146 | small n | strong | Stacked support |
| rs-s147 | small n | strong | Stacked support |

**Why it works**: Stacked support levels (rs-s146 + rs-s147 + rs-s492) give structural validity. The hzscore- is weak but the RS levels are doing the real work. Confidence=99.0.

## Key Lesson

The OPP penalty is a quality filter. When it blocks a signal, check the components — if they're genuinely weak, the OPP was right. If they're strong (like accel-300+ combos), the OPP floor needs adjustment.

**Never diagnose an OPP block without decomposing the signal first.**
