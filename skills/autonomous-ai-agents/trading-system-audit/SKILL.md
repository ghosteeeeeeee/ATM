---
name: trading-system-audit
description: Full codebase audit of the Hermes trading system — syntax, imports, calculations, API consistency, DB safety, error handling, and security.
category: autonomous-ai-agents
---

# trading-system-audit

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
10. Completeness — dead code paths, unfinished TODOs

## Key Files
```
/root/.hermes/scripts/
  decider-run.py         — hot-set approval logic
  ai-decider.py          — signal scoring + source weights (SINGLE SOURCE)
  signal_gen.py          — confluence signal generation
  unified_scanner.py    — regime + price scanning
  position_manager.py    — trade execution + position tracking
  hyperliquid_exchange.py — HL API wrapper
  hype_cache.py          — centralized HL API cache
  hl-sync-guardian.py   — DB/HL reconciliation
  wasp.py                — anomaly detection
  brain.py               — PostgreSQL brain
  run_pipeline.py        — pipeline orchestrator
```

## Audit Script
Save and run from `/root/.hermes`:
```python
#!/usr/bin/env python3
"""Quick audit runner — paste into terminal."""
import subprocess, sys, os

REPO = "/root/.hermes"
SCRIPTS = f"{REPO}/scripts"

def sh(*cmd):
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    return r.stdout, r.stderr, r.returncode

KEY_FILES = [
    "decider-run.py", "ai-decider.py", "signal_gen.py",
    "unified_scanner.py", "position_manager.py", "hyperliquid_exchange.py",
    "hype_cache.py", "hl-sync-guardian.py", "wasp.py", "brain.py", "run_pipeline.py"
]

print("=== 1. SYNTAX ===")
for s in KEY_FILES:
    path = f"{SCRIPTS}/{s}"
    status = "OK" if os.path.exists(path) and sh("python3","-m","py_compile",path)[2]==0 else "FAIL"
    print(f"  {s}: {status}")

print("\n=== 2. IMPORTS ===")
for mod in ["ai_decider", "hype_cache", "signal_gen", "position_manager", "hyperliquid_exchange"]:
    out, err, rc = sh("python3","-c",f"import sys;sys.path.insert(0,'{SCRIPTS}');import {mod}")
    print(f"  {mod}: {'OK' if rc==0 else 'FAIL'}")

print("\n=== 3. SOURCE WEIGHTS — ONE PLACE ONLY ===")
out, _, _ = sh("grep","-rn","SOURCE_WEIGHT\\|source_weight\\|source_mult","--include=*.py",SCRIPTS)
for line in out.splitlines():
    fname = line.split(":")[0].replace(SCRIPTS+"/","")
    if fname not in ["ai-decider.py","decider-run.py"]:
        print(f"  !! OUTSIDE ai-decider: {line}")
    else:
        print(f"  {line}")

print("\n=== 4. DIRECT HL API (should use hype_cache) ===")
for fname in KEY_FILES:
    out, _, _ = sh("grep","-n","requests\\.post.*hyperliquid\\|requests\\.post.*allMids\\|exchange\\.info\\.all_mids",f"{SCRIPTS}/{fname}")
    tag = "!!" if out.strip() else "  "
    print(f"  {tag} {fname}: {'direct calls found' if out.strip() else 'clean'}")

print("\n=== 5. PIPELINE SYNC CHECK ===")
sys.path.insert(0, SCRIPTS)
try:
    from hype_cache import get_allMids
    from hyperliquid_exchange import get_open_hype_positions_curl
    import psycopg2
    mids = get_allMids()
    hl = get_open_hype_positions_curl()
    conn = psycopg2.connect(host='/var/run/postgresql',dbname='brain',user='postgres',password='Brain123')
    cur = conn.cursor()
    cur.execute("SELECT token,status FROM trades WHERE status='open'")
    db_tokens = set(r[0] for r in cur.fetchall())
    cur.close(); conn.close()
    hl_tokens = set(k for k,v in hl.items() if v.get('size',0)!=0)
    diff = (db_tokens ^ hl_tokens)
    print(f"  hype_cache mids: {len(mids)} | HL: {len(hl_tokens)} | DB: {len(db_tokens)}")
    print(f"  Sync: {'OK' if not diff else 'MISMATCH: '+str(diff)}")
except Exception as e:
    print(f"  !! Sync check failed: {e}")

print("\n=== 6. ERROR HANDLING ===")
out, _, _ = sh("grep","-rn","except:$","--include=ai-decider.py","--include=decider-run.py",SCRIPTS)
print(f"  Bare excepts in ai-decider+decider-run: {len(out.splitlines())}")

print("\n=== AUDIT COMPLETE ===")
```

## Pitfalls Found So Far (2026-04-02)
- **`***` WIP placeholders** in decider-run.py SQL — always verify all SQL is complete
- **Phantom DB entries** from hl-sync-guardian not closing deleted HL positions
- **Symlink `ai_decider.py → ai-decider.py`** required for underscore import — do NOT remove
- **CloudFront blocks `/exchange` endpoint** for clearinghouseState — use `/info` endpoint
- **Symlinks break `git archive`** — allow `ai_decider.py` in update-git.py symlink check
- **GitHub releases become immutable** after any asset upload attempt — use draft → upload → publish flow
