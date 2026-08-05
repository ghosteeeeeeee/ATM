# Signal Quality Audit — 2026-05-06 Session

## Quick Audit Script (742-trade DB)

```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
import psycopg2
from _secrets import BRAIN_DB_DICT
from collections import defaultdict
import decimal

conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()

def to_float(v):
    return float(v) if isinstance(v, decimal.Decimal) else (float(v) if v else 0.0)

dedup = defaultdict(lambda: {'wins':0,'losses':0,'pnl':0.0,'weeks':set()})
cur.execute("""
  SELECT token, direction, pnl_pct, signal, DATE_TRUNC('week', close_time) as week
  FROM trades
  WHERE close_time IS NOT NULL AND pnl_pct IS NOT NULL
    AND signal IS NOT NULL AND signal != ''
""")
for token, direction, pnl_pct, signal, week in cur.fetchall():
    pnl = to_float(pnl_pct)
    dedup[(token, direction, week, signal)]['wins'] += 1 if pnl > 0 else 0
    dedup[(token, direction, week, signal)]['losses'] += 0 if pnl > 0 else 1
    dedup[(token, direction, week, signal)]['pnl'] += pnl
    dedup[(token, direction, week, signal)]['weeks'].add(week)

combo_stats = defaultdict(lambda: {'wins':0,'losses':0,'pnl':0.0})
for (_, direction, _, signal), d in dedup.items():
    combo_stats[(direction, signal)]['wins'] += d['wins']
    combo_stats[(direction, signal)]['losses'] += d['losses']
    combo_stats[(direction, signal)]['pnl'] += d['pnl']

for (direction, combo), d in sorted(combo_stats.items(), key=lambda x: -(x[1]['wins']/(x[1]['wins']+x[1]['losses']+0.001))):
    t = d['wins'] + d['losses']
    if t < 5: continue
    wr = d['wins'] / t * 100
    avg = d['pnl'] / t
    print(f"  {direction:<8} {combo[:55]:<55} n={t:>4} WR={wr:>5.1f}% avg={avg:>+7.3f}%")
conn.close()
```

## Audited Signal Quality (742 Trades, deduplicated by token-direction-week)

| Combo | Direction | Trades | WR | Avg% | Notes |
|-------|-----------|--------|-----|------|-------|
| accel-300+,trend_purity+ | LONG | 8 | **62.5%** | +0.36% | BEST LONG — but only 2/5 weeks of data |
| gap-300- | LONG | 75 | **40.0%** | +0.22% | Most reliable standalone LONG (1 wk data) |
| accel-300+,pct-hermes+ | LONG | 8 | **50.0%** | +0.36% | 1 week data |
| accel-300+,hzscore- | LONG | 30 | 36.7% | +0.66% | Good avg%, consistent |
| accel-300+ alone | LONG | 16 | 31.2% | +0.41% | |
| ma-cross-5m+ + accel-300+ | LONG | 6 | **16.7%** | **-0.32%** | **BLOCKED** — fades momentum |
| vel-hermes+ | LONG | 13 | 30.8% | **-0.13%** | **BLOCKED** — wrong direction |
| hzscore+,pct-hermes-,vel-hermes- | SHORT | 39 | **46.2%** | +0.38% | BEST SHORT combo |
| vel-hermes- | SHORT | 5 | 40.0% | +0.33% | Decent standalone |
| hzscore+,vel-hermes- | SHORT | 15 | 20.0% | -0.06% | Weak |

## Decider WR Filter (decider_run.py line 1709)

```python
wr, wr_count = _get_direction_wr(token, direction)
if wr < 50 and wr_count >= 3:
    log(f'SKIP: {token} {direction} WR={wr:.0f}% ({wr_count} trades) — direction paused')
```

New tokens entering hotset need ≥50% recent WR. Check per-token:
```python
from decider_run import _get_direction_wr
for tok, d in [('LINK','SHORT'), ('DYM','SHORT'), ('TRB','SHORT')]:
    wr, count = _get_direction_wr(tok, d)
    print(f"{tok} {d}: WR={wr:.0f}% ({count} trades)")
```

## Hotset → Decider Blocker Diagnosis

```python
import json
from decider_run import _is_guardian_closing, _get_direction_wr
from position_manager import get_open_positions, is_loss_cooldown_active

with open('/var/www/hermes/data/hotset.json') as f:
    entries = json.load(f).get('hotset', [])
open_tokens = {p['token'] for p in get_open_positions()}

for e in entries:
    tok, d, src = e['token'], e['direction'], e.get('source', '')
    gc = _is_guardian_closing(tok)
    wr, count = _get_direction_wr(tok, d)
    blockers = []
    if gc: blockers.append("guardian_closing")
    elif tok in open_tokens: blockers.append("already_open")
    elif is_loss_cooldown_active(tok, d): blockers.append("loss_cooldown")
    elif wr < 50 and count >= 3: blockers.append(f"low_wr({wr:.0f}%)")
    print(f"  {tok:<10} {d:<6} src={src[:40]} → {blockers}")
```

## Stale Guardian-Closing Markers

`_is_guardian_closing` reads `/root/.hermes/data/guardian-closing-markers.json`. File accumulates tokens and is never cleaned up on close. Tokens permanently blocked despite no open position.

Clean stale markers:
```python
import json
from position_manager import get_open_positions
open_tokens = {p['token'] for p in get_open_positions()}
marker_file = '/root/.hermes/data/guardian-closing-markers.json'
with open(marker_file) as f:
    data = json.load(f)
tokens = data.get('tokens', {})
for tok in list(tokens.keys()):
    if tok not in open_tokens:
        del tokens[tok]
with open(marker_file, 'w') as f:
    json.dump(data, f, indent=2)
```

## Co-Signal Gate (signal_compactor.py ~line 403)

```python
ACCEL_LONG_BLOCK   = {'ma-cross-5m+'}   # poison co-signals (16.7% WR combo)
ACCEL_LONG_REQUIRE = set()              # none required (trend_purity+ too sparse)
ACCEL_SHORT_BLOCK  = set()
ACCEL_SHORT_REQUIRE = set()             # proven 3-signal combo forms naturally

if has_accel_plus:
    blocked = [s for s in source_parts if s in ACCEL_LONG_BLOCK]
    if blocked: continue  # blocks ma-cross-5m+ combo
    missing = [s for s in ACCEL_LONG_REQUIRE if s not in source_parts]
    if missing: continue  # blocks if required co-signal missing
```

## Key Finding: SHORT-Only Bias

The system fires only SHORT signals because:
1. `trend_purity+` (LONG co-signal) appeared in only 2/5 weeks of data
2. Decider blocks new entries with <50% recent WR
3. Best LONG combos (`accel-300++trend_purity+`) are rare

**Fix options:**
- Lower decider WR threshold from 50% to 40% for new tokens
- Force more LONG signals to fire (harder — signal scarcity)
- Accept SHORT-only operation until more LONG data accumulates
