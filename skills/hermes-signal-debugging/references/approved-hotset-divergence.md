# APPROVED vs hot-set Token Divergence (2026-05-11)

## The Phenomenon

User observes: hot-set and `get_approved_signals()` have **completely different token sets**.

Example (2026-05-11 ~06:30):
- **hotset.json**: EIGEN, AVNT, CAKE, XMR, TAO, ADA, ATOM, DASH, 0G, AVAX (LONG, 71-88%)
- **APPROVED (DB)**: PEOPLE, LINEA, NIL, COMP, BLUR, LTC, MERL, GRIFFAIN (LONG, 72-88%)

Not a subset — disjoint sets.

## Root Cause: Timing + Independence

```
signals_runner (background, ~every 5 min)
  → writes signals to signals_hermes_runtime.db
  ↓
signal_compactor.py (every 1 min, SYNCHRONOUS)
  → reads DB, applies confluence gate (2+ sources)
  → scores, ranks TOP-10
  → writes hotset.json
  ↓
decider_run.py (every 1 min, SYNCHRONOUS)
  → reads hotset.json → _hot_tokens set
  → calls get_approved_signals() from DB
  → iterates APPROVED signals
  → ONLY executes if token is in _hot_tokens (hotset.json)
```

**Key insight**: `get_approved_signals()` returns ALL DB entries passing confluence gate.
`hotset.json` is the scored/ranked TOP-10 subset.

A token can be APPROVED in the DB but not in hotset.json if:
1. It arrived AFTER the last signal_compactor run (DB write → compaction window miss)
2. It ranks #11-16 in scoring (not in top-10)
3. It was blocked by a safety filter in signal_compactor but still marked APPROVED

## Decider_run Execution Gate

```python
# decider_run.py ~line 1474
for sig in scored_approved:
    token = sig['token'].upper()
    # Only executes if token is in current hotset.json
    if token not in _hot_tokens:
        continue  # NEVER executes — not in hot-set
```

An APPROVED token NOT in hotset.json is silently skipped every cycle.

## Why They Have Different Tokens (specific example)

| Signal | Time | Source | In hotset? | In APPROVED? | Reason |
|--------|------|--------|------------|--------------|--------|
| EIGEN | ~06:20 | accel-300+,rs-s108 | YES | YES (if same cycle) | Arrived before compaction |
| AVNT | ~06:22 | accel-300+,rs-s296 | YES | YES | Arrived before compaction |
| PEOPLE | 06:15 | accel-300+,rs-s472 | NO | YES | Arrived after compaction cutoff |
| LINEA | 06:13 | accel-300+,rs-s76 | NO | YES | Arrived after compaction cutoff |
| COMP | 06:10 | accel-300+ (single!) | NO | YES | Single-source — confluence gate FAIL |

COMP has source=`accel-300+` only (no RS co-signal). It was NOT merged. How is it APPROVED?

**Theory**: COMP's accel-300+ signal arrived within a 5-min window where signal_gen wrote it to DB as its own row. GROUP BY token+direction merges multiple rows — if another signal (e.g., a second accel-300 from a different cycle) had same token+direction within the window, GROUP BY would merge them. But source=`accel-300+` only = single source.

Wait — the user showed COMP source as `accel-300+` (no comma = no merge). But it's APPROVED. This means the confluence gate in signal_compactor may allow single-source through in some path, OR the grouping query is picking it up differently.

**Actual check needed**:
```bash
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, source, COUNT(*) FROM signals \
   WHERE token='COMP' AND direction='LONG' \
   GROUP BY token, source ORDER BY created_at DESC LIMIT 5;"
```

## Confluence Gate in signal_compactor

signal_compactor.py lines ~495-510:
```python
# Must have 2+ distinct signal types for the same token+direction
unique_signal_types = set()
for source_tag in source.split(','):
    base_type = source_tag.split('-')[0]  # 'accel' from 'accel-300+'
    unique_signal_types.add(base_type)

if unique_signal_types >= 2:
    pass_gate = True  # APPROVED / hot-set candidate
```

The merge window is ~5 min (the GROUP BY window). COMP's source shows `accel-300+` only — single type. This suggests either:
1. The example data is from `get_pending_signals()` not `get_approved_signals()` (user may have misread)
2. OR there's a code path where single-source APPROVED is possible

**DB verification required**:
```python
from signal_schema import get_approved_signals
approved = get_approved_signals()
comp_signals = [s for s in approved if s['token'] == 'COMP']
print(comp_signals[0]['source'] if comp_signals else 'NOT APPROVED')
```

## Regime as Divergence Amplifier

Before 2026-05-11: regime_5m.json showed 101/105 tokens NEUTRAL.
After switch to 1m LR: tokens show SHORT_BIAS or LONG_BIAS with varying R² confidence.

This means:
- OLD: Counter-regime blocks were rare (most tokens NEUTRAL)
- NEW: Counter-regime penalties fire more often (more tokens have directional LR slope)

1m LR with low R² (<30%) is essentially noise — slope is near-zero but rounding makes it appear directional. This creates phantom counter-regime penalties.

## Key Diagnostic Queries

```bash
# 1. What's actually in hotset.json vs DB APPROVED
python3 -c "
import sqlite3, json
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.execute(\"SELECT token, direction, decision, source, confidence FROM signals WHERE decision='APPROVED'\")
approved = {(r[0],r[1]): r for r in cur.fetchall()}
with open('/var/www/hermes/data/hotset.json') as f:
    hot = {s['token']: s['direction'] for s in json.load(f).get('hotset',[])}
in_both = set(approved.keys()) & set(hot.keys())
only_approved = set(approved.keys()) - set(hot.keys())
only_hotset = set(hot.keys()) - set(approved.keys())
print(f'In both: {len(in_both)} {in_both}')
print(f'Only APPROVED (never executes): {len(only_approved)} {only_approved}')
print(f'Only hotset: {len(only_hotset)} {only_hotset}')
"

# 2. When did APPROVED signals last get updated
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  \"SELECT token, direction, MAX(created_at), decision FROM signals \
   WHERE decision='APPROVED' GROUP BY token, direction ORDER BY MAX(created_at) DESC LIMIT 15;\"

# 3. hotset.json last write time
stat /var/www/hermes/data/hotset.json | grep Modify
```

## Counter-Regime Penalty Impact (2026-05-11 switch to 1m LR)

| Token | 1m LR Regime | R² | Direction | Penalty (regime_conf×0.15) |
|-------|-------------|-----|-----------|---------------------------|
| COMP | LONG_BIAS | 63% | LONG | 0 (aligned) |
| CAKE | SHORT_BIAS | 53% | LONG | ~8pt penalty → 63%→55% |
| LTC | SHORT_BIAS | 58% | LONG | ~9pt penalty → 66%→57% |
| DASH | SHORT_BIAS | 80% | LONG | ~12pt penalty → 71%→59% |
| 0G | SHORT_BIAS | 62% | LONG | ~9pt penalty → 88%→79% |
| XMR | SHORT_BIAS | 22% | LONG | ~3pt penalty (low conf) |
| TAO | SHORT_BIAS | 52% | LONG | ~8pt penalty → 82%→74% |

High R² SHORT_BIAS tokens (DASH 80%, CAKE 53%, TAO 52%) take meaningful confidence hits when going LONG. Low R² (<30%) tokens get minimal penalty — the LR is noisy and unreliable.

## Regime Source Comparison

| Source | Update_freq | Lookback | Method | Confidence |
|--------|------------|----------|--------|------------|
| regime_5m.json | ~5 min | 16×5m=80min | R² slope | 44-70% |
| get_regime_1m() | every decider_run | 100×1m=100min | LR R² | 0-80% |

1m LR is noisier, more responsive, less smoothed. Good for catching direction changes, bad for stable directional bias.