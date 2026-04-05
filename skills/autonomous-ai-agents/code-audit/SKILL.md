---
name: code-audit
description: Full codebase audit of the Hermes trading system — syntax, imports, calculations, API consistency, DB safety, error handling, and security.
category: autonomous-ai-agents
author: T
created: 2026-04-02
---

# Code Audit

Run a full health check and code quality audit of the Hermes trading system.

## When to Use
After any significant code change (weights, signal flow, API calls, DB schema). Covers:
1. Python syntax — py_compile each key script
2. Import integrity — all imports resolve, no circular dependencies
3. Calculation logic — sign flips, None handling, zero-division guards
4. API call consistency — hype_cache usage vs direct requests.post for Hyperliquid
5. Database consistency — SQL injection risks, connection leaks, NULL handling
6. Signal flow — source weights in ONE place only
7. Error handling — bare excepts, silent failures, missing fallbacks
8. Security — hardcoded secrets, exposed ports, credential leaks
9. Concurrency — lock file handling, race conditions
10. Completeness — dead code paths, unfinished TODOs, `***` placeholder corruption

## Key Files

```
/root/.hermes/scripts/
  decider-run.py          — hot-set approval logic
  ai-decider.py           — signal scoring + source weights (SINGLE SOURCE)
  ai_decider.py           — symlink to ai-decider.py (DO NOT DELETE)
  signal_gen.py           — confluence signal generation
  unified_scanner.py      — regime + price scanning
  position_manager.py     — trade execution + position tracking
  hyperliquid_exchange.py — HL API wrapper
  hype_cache.py           — centralized HL API cache (THE canonical source)
  hl-sync-guardian.py    — DB/HL reconciliation
  wasp.py                 — anomaly detection
  brain.py                — PostgreSQL brain
  run_pipeline.py         — pipeline orchestrator
  hermes-trades-api.py    — JSON output for web dashboard
```

## Critical Bugs Found (2026-04-02)

| # | File | Line | Severity | Issue | Status |
|---|------|------|----------|-------|--------|
| 1 | `ai-decider.py` | 313 | HIGH | `clear_ab_cache()` refs undefined `token` (should be `coin`) | FIXED |
| 2 | `unified_scanner.py` | 30, 179 | MEDIUM | Direct `requests.post` to HL `/info` bypasses shared hype_cache | FIXED |
| 3 | `hyperliquid_exchange.py` | 875 | MEDIUM | `mirror_open()` returns undefined `mid_price` (should be `live_price`) | FIXED |
| 4 | `signal_gen.py` | ~1570 | HIGH | 10x `token=***` placeholder bugs in confluence loop | FIXED |
| 5 | `ai-decider.py` | multiple | HIGH | 10x SQL `WHERE token=***` placeholder bugs | FIXED |

## Audit Checklist

### Syntax Check
```bash
cd /root/.hermes
python3 -m py_compile scripts/decider-run.py scripts/ai-decider.py scripts/signal_gen.py \
  scripts/unified_scanner.py scripts/position_manager.py scripts/hyperliquid_exchange.py \
  scripts/hype_cache.py scripts/hl-sync-guardian.py scripts/wasp.py scripts/brain.py
```

### HL API Consistency
Direct `requests.post` to Hyperliquid is ONLY allowed in:
- `hype_cache.py` (canonical cache writer)
- `price_collector.py` (cache feeder)
- `hyperliquid_exchange.py` (SDK-level calls)
- `hyperliquid-trader.py` (separate trader)

All other scripts MUST use `hype_cache.get_meta()`, `hype_cache.get_allMids()`, or `hype_cache.get_user_context()`.

Search for violations:
```bash
grep -n "requests\.post.*hyperliquid\|requests\.post.*allMids\|requests\.post.*meta" \
  scripts/decider-run.py scripts/ai-decider.py scripts/unified_scanner.py \
  scripts/hl-sync-guardian.py scripts/wasp.py 2>/dev/null
```
Should return nothing (except in hype_cache.py, price_collector.py, hyperliquid_exchange.py).

### `***` Placeholder Corruption Check
The git diff sanitization tool corrupts `token=?` → `token=***`. Check:
```bash
grep -c 'token=\\*\\*\\*' scripts/signal_gen.py scripts/ai-decider.py scripts/unified_scanner.py
```
Expected: 0 in all files.

### SQL Parameter Check
```bash
grep -c 'WHERE token=\\*\\*\\*' scripts/*.py  # should be 0
```

### Import Check
```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
import ai_decider, hype_cache, signal_gen, position_manager, hyperliquid_exchange
```

### Source Weights Check
Source weights must ONLY be in `ai-decider.py`:
```bash
grep -rn "SOURCE_WEIGHT\|source_weight\|source_mult\|SOURCE_MULT" scripts/ \
  --include=*.py | grep -v ai-decider.py
```
Should be empty.

### DB Sync Check
```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hype_cache import get_allMids
from hyperliquid_exchange import get_open_hype_positions_curl
import psycopg2

mids = get_allMids()
hl = get_open_hype_positions_curl()
conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
cur = conn.cursor()
cur.execute("SELECT token, status FROM trades WHERE status='open'")
db_tokens = set(r[0] for r in cur.fetchall())
cur.close(); conn.close()
hl_tokens = set(k for k,v in hl.items() if v.get('size',0)!=0)
diff = db_tokens ^ hl_tokens
print(f"hype_cache mids: {len(mids)} | HL: {len(hl_tokens)} | DB: {len(db_tokens)}")
print(f"Sync: {'OK' if not diff else 'MISMATCH: '+str(diff)}")
```

### Error Handling Check
```bash
grep -rn "except:$" scripts/ai-decider.py scripts/decider-run.py
```
Count bare excepts — should be minimal and have logging.

### Security Check
```bash
grep -rn "password.*=" scripts/brain.py  # should use _secrets.py fallback
grep -rn "Bearer \|api_key\|secret.*=" scripts/*.py | grep -v "#\|_\|password"
```

## Pitfalls Found So Far

- **`***` WIP placeholders** in decider-run.py SQL — always verify all SQL is complete
- **Phantom DB entries** from hl-sync-guardian not closing deleted HL positions
- **Symlink `ai_decider.py → ai-decider.py`** required for underscore import — do NOT remove
- **CloudFront blocks `/exchange` endpoint** for clearinghouseState — use `/info` endpoint
- **Symlinks break `git archive`** — allow `ai_decider.py` in update-git.py symlink check
- **GitHub releases become immutable** after any asset upload attempt — use draft → upload → publish flow
- **mirror_open `mid_price` NameError** — always use `live_price` in that scope
- **`clear_ab_cache(coin=...)` referenced undefined `token`** — parameter was renamed, body wasn't
- **unified_scanner.py direct HL API calls** bypassing hype_cache — now fixed to use `get_meta()`