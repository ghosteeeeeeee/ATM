# Plan: Fix Hot-Set Wild Fluctuation (5 ↔ 20 signals)

## Goal
Fix the hot-set size wildly fluctuating between 5 and 20 signals every cycle.

---

## Root Causes Found

### BUG 1 (CRITICAL): `HOTSET_FILE` undefined in `get_pending_signals()`
**File:** `/root/.hermes/scripts/ai_decider.py`
**Line:** ~1898

```python
def get_pending_signals():
    try:
        conn = sqlite3.connect(SIGNALS_DB)
        c = conn.cursor()
        _do_compaction_llm()  # ← calls this
        ...
```

`_do_compaction_llm()` uses `HOTSET_FILE` at lines 1198, 1647, 1721, 1722, 1773, 1774, 1870 — but `HOTSET_FILE` is **never actually imported** into ai_decider.py's namespace.

**Why it appears to work when you test it directly:**
- `import paths` (line 19) runs fine — it's a separate module
- `import paths  # noqa: F401` suppresses linting only; it does NOT make `from paths import *` bring in lowercase attrs
- `from paths import *` (line 19) brings in nothing from paths because: (a) paths.py has no `__all__`, and (b) `from X import *` only imports uppercase names by convention when `__all__` is absent
- So `HOTSET_FILE` is **never defined** in ai_decider.py's global scope
- `_do_compaction_llm()` → `get_pending_signals()` crashes with `NameError: name 'HOTSET_FILE' is not defined`

**Pipeline log proves it:**
```
[2026-04-16 04:20:31] [ERROR] [ai-decider] get_pending_signals DB read error: name 'HOTSET_FILE' is not defined
(repeats every ~1 minute through 04:44)
```

**Effect:** Every pipeline cycle hits the exception handler in `get_pending_signals()`, which returns `[]`. The outer `compact_signals()` loop then processes 0 pending signals → hot-set preservation logic fires → sometimes 5 survivors carry forward, sometimes 20 depending on signal_gen output.

### BUG 2 (RELATED): `_load_hot_rounds()` reads stale hotset.json
**File:** `/root/.hermes/scripts/ai_decider.py`
**Lines:** 1721-1722, 1773-1774

Even when `_do_compaction_llm()` somehow succeeds (earlier cycles), `_load_hot_rounds()` also uses `HOTSET_FILE` directly. Both functions need `paths.HOTSET_FILE` (qualified).

### BUG 3: 10-minute compaction window too narrow for signal_gen cadence
**File:** `/root/.hermes/scripts/ai_decider.py` line ~1159

```python
AND created_at > datetime('now', '-10 minutes')
```

`signal_gen` fires every 1 minute (pipeline). But compaction runs every 10 minutes. When it fires, it queries only the last 10 minutes of signals. If signal_gen was skipped in a prior cycle (e.g., if signal_gen timed out), the window has 0-5 signals → LLM gets a tiny pool → hot-set collapses.

**Fix:** Expand window to 20 minutes (2x the 10-min compaction cycle), enough to span missed cycles.

---

## Proposed Fix (3 patches)

### Fix 1: Add `HOTSET_FILE` to `__all__` in paths.py
**File:** `/root/.hermes/scripts/paths.py`

Add `__all__` near the top of paths.py after the imports, listing all public symbols:

```python
__all__ = [
    'HERMES_DATA', 'WWW_DATA', 'RUNTIME_DB', 'STATIC_DB',
    'SIGNALS_DB', 'LEGACY_SIGNALS_DB', 'HOTSET_FILE', 'HOTSET_META_FILE',
    'HOTSET_FAILURES_FILE', 'HOTSET_APPROVAL_FILE', 'HOTSET_FAIL_FILE',
    'TRADES_JSON', 'SIGNALS_JSON', 'LIVESWITCH_FILE', 'HL_CACHE_FILE',
    ...
]
```

**Effect:** `from paths import *` then brings HOTSET_FILE into ai_decider.py namespace. All 8 uses of HOTSET_FILE (lines 1198, 1444, 1647, 1721, 1722, 1773, 1774, 1870) will resolve.

### Fix 2: Expand signal query window from 10 → 20 minutes
**File:** `/root/.hermes/scripts/ai_decider.py`
**Line:** ~1159

```python
# BEFORE
AND created_at > datetime('now', '-10 minutes')

# AFTER
AND created_at > datetime('now', '-20 minutes')
```

**Effect:** Compaction always has at least one full compaction cycle of signals to rank. Won't collapse when signal_gen misses a beat.

### Fix 3: Validate HOTSET_FILE is importable (defensive)
**File:** `/root/.hermes/scripts/ai_decider.py`
**Line:** ~19 (after `import paths`)

```python
import paths  # noqa: F401 — makes paths.* available via paths.py exports
from paths import *  # noqa: F403, F401

# Defensive: verify HOTSET_FILE is resolvable (crash early if paths is broken)
assert 'HOTSET_FILE' in dir(), f"HOTSET_FILE not in namespace after 'from paths import *' — check paths.py __all__"
```

---

## Files to Change

| File | Change |
|------|--------|
| `/root/.hermes/scripts/paths.py` | Add `__all__` list including `HOTSET_FILE` and all other public symbols |
| `/root/.hermes/scripts/ai_decider.py` | Line ~1159: `'-10 minutes'` → `'-20 minutes'`; add defensive assertion after imports |

---

## Verification Steps

1. **Verify fix loads without error:**
   ```bash
   cd /root/.hermes/scripts && python3 -c "from ai_decider import get_pending_signals; print('HOTSET_FILE OK')"
   ```

2. **Verify paths __all__ works:**
   ```bash
   python3 -c "import sys; sys.path.insert(0, '/root/.hermes/scripts'); from paths import *; print('HOTSET_FILE:', HOTSET_FILE)"
   ```

3. **Check pipeline log for errors (should be clean after next run):**
   ```bash
   grep -E "HOTSET_FILE|NameError|get_pending_signals DB read error" /root/.hermes/logs/pipeline.log | tail -10
   ```

4. **Watch hot-set size stabilize (should stay ~20, not fluctuate 5↔20):**
   ```bash
   watch -n5 'cat /var/www/hermes/data/hotset.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"hotset size: {len(d[\\\"hotset\\\"])}, age: {__import__(\\\"time\\\").time()-d[\\\"timestamp\\\"]:.0f}s\")"'
   ```

---

## Risks & Tradeoffs

- **Fix 1 (paths __all__):** Safe and correct. Adding `__all__` to paths.py is the right way to make `from paths import *` work predictably. No behavioral change, just explicit exports.
- **Fix 2 (10→20 min window):** Larger prompt to LLM (worst case ~272 signals instead of ~136). The LLM already handles 68 signals well per logs. With a 20-min window, worst case ~120-150 signals — still within the 150 LIMIT cap on line 1170. Safe.
- **Fix 3 (assertion):** Defensive. If paths.py is broken, the pipeline crashes immediately instead of silently producing wrong results. This is the desired behavior.

---

## Open Questions

1. **Why did this suddenly break?** The HOTSET_FILE error first appeared at `04:20:31` on 04-16. Was paths.py or ai_decider.py recently changed? A previous fix may have removed HOTSET_FILE from an import path without adding it to paths.py's `__all__`.
2. **Were there other NameErrors before this?** Yes — earlier logs show `name 'top20' is not defined` (20:00, 20:10 on 04-15) and `'token'` errors (19:10-19:50). The HOTSET_FILE bug may be the latest manifestation of a broader import/namespace issue.
3. **Should we do a broader audit of ai_decider.py imports?** Yes — the pattern of multiple NameErrors in recent days suggests the module may need a careful import audit.

---

## Timeline of Related Errors (from pipeline.log)

```
04-15 19:10-19:50  get_pending_signals DB read error: 'token'
04-15 20:00-20:10  get_pending_signals DB read error: name 'top20' is not defined
04-16 03:32       get_pending_signals DB read error: tuple index out of range
04-16 04:06       ERROR ai_decider: timed out
04-16 04:20-04:44 get_pending_signals DB read error: name 'HOTSET_FILE' is not defined
                  (every ~1 min — compaction completely broken)
```
