# Confluence Gate Starvation — 2026-05-21

## Session Findings

**No bug introduced.** The system is working correctly but stalling due to confluence gate being too tight for current signal output.

### Current State
- hotset.json: 1 entry (DASH SHORT, conf=88%, score=128)
- HL positions: 3 open (LINK, BSV, ENS) — 2 slots FREE
- signals DB: 0 APPROVED+unexecuted, 28 PENDING
- MAX_HYPE_POSITIONS=5

### Why 2 Slots Are Empty
The confluence gate (2+ unique signal SOURCE TYPES, not just source parts) is blocking all 28 PENDING signals.

**Confluence gate rule:** `len(set(parts)) >= 2`
- `rs-r84,zscore-pump-` → 2 parts, 2 unique types (rs, zscore-pump) → **PASS**
- `rs-s104,rs-s128` → 2 parts, 1 unique type (both rs) → **BLOCKED**
- `zscore-pump-` only → 1 part → **BLOCKED**

### Why DASH Is the Only Hot-Set Entry
DASH passed confluence multiple cycles (02:15–02:21) with multi-source signals (`rs-r353,zscore-pump-`).
Each APPROVED signal was immediately EXECUTED (executed=1).
The next DASH signal (02:18:03) is single-source (`zscore-pump-` only) → blocked.
No new APPROVED signal created → decider_run finds nothing to execute.

### The Staleness Bug in Preservation
DASH's hot-set entry shows score=0.0 despite being written with score=51.33.
Root cause: preserved entries from previous cycle have `no DB entry` and `score=0`.
When merge picks the higher score, the 0 persists across many cycles if no new multi-source signal fires.
DASH's APPROVED signals were consumed (executed=1) and not refreshed because the 02:18:03 signal was single-source.

### What ASTER/GALA/APEX Were
Prior hot-set entries, rotated out. Current hot-set has DASH only.
The coins listed by T in the UI are stale — from a prior compaction cycle.

## Key Code Locations
- Confluence uniqueness check: signal_compactor.py line ~562 (`len(unique_signal_types) < 2`)
- PENDING→APPROVED confluence block: signal_compactor.py line ~1047
- Preservation merge: signal_compactor.py lines ~938-964
- Score formula: signal_compactor.py lines ~195-243

## The Real Bottleneck
Signal generators are producing single-source signals:
- `zscore-pump+` or `zscore-pump-` fires alone
- `rs-s104,rs-s128` fires (2 parts, 1 type — still blocked)

**Fix direction:** Signal generators need to produce cross-type combos more reliably.
The confluence gate itself is correct — it's the signal output that's the problem.

## Diagnostic Commands
```bash
# Current hot-set (live)
cat /var/www/hermes/data/hotset.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'hotset: {len(d[\"hotset\"])} entries')
for e in d['hotset']:
    print(f'  {e[\"token\"]} {e[\"direction\"]} conf={e.get(\"confidence\",\"?\")} src={e.get(\"source\",\"?\")[:60]} score={e.get(\"final_score\",e.get(\"score\",\"?\"))}')
"

# APPROVED+unexecuted (should be 0 right now)
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, decision, executed, source, confidence FROM signals \
   WHERE decision='APPROVED' AND executed=0 ORDER BY confidence DESC LIMIT 10"

# PENDING signals (last 5 min) — shows single-source problem
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, source, confidence, created_at FROM signals \
   WHERE decision='PENDING' AND created_at > datetime('now', '-5 minutes') \
   ORDER BY confidence DESC LIMIT 30"

# HL open positions
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_open_hype_positions_curl
positions = get_open_hype_positions_curl()
print(f'Open positions: {len(positions)}')
for p in positions:
    print(f'  {p[\"coin\"]} size={p[\"sizing\"]} pnl={p.get(\"unrealized_pnl\",0)}')
"
```

## Related
- `references/confluence-gate-starvation-2026-05-18.md` — prior confluence starvation incident
- `references/signal-quality-degradation-2026-05-21.md` — signal metadata not persisting in trades