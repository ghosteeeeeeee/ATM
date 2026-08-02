# Plan: Trading System Bug Fixes — Round 2 (Verified 2026-07-19)

## Goal

Fix 10 verified bugs in the Hermes trading system (second pass), prioritized by severity.

## Status: All fixes applied ✅

| # | File | Bug | Status |
|---|------|-----|--------|
| 4 | signal_compactor.py | RS gate blocks accel-300 standalone | ✅ Fixed |
| 5 | hl-sync-guardian.py | Missing FileLock + swallowed re-raise | ✅ Fixed |
| 7 | breakout_engine.py | Hardcoded paths | ✅ Fixed |
| 1 | hzscore.py | Stale comment | ✅ Fixed |
| 3 | rs.py | Legacy path touch counting | ✅ Fixed |
| 6 | position_manager.py | Python 3.10+ syntax | ✅ Fixed |
| 8 | zscore_pump.py | DRY_RUN import-time | ✅ Fixed |
| 9 | brain.py | Validation mismatch | ✅ Fixed |
| 2 | exhaustion.py | Asymmetric gap (intentional) | ⏭️ Skip |
| 10 | decider_run.py | Lambda aliasing (safe) | ⏭️ Skip |

## Context

- First pass fixed 11 bugs (see `2026-07-19_trading-bugs-verified.md`)
- Second pass found 10 new bugs via code audit
- All bugs exist in production scripts under `/root/.hermes/scripts/`

## Verified Bug List

### High (1)

| # | File:Line | Bug | Impact |
|---|-----------|-----|--------|
| 4 | `signal_compactor.py:689-694` | RS required gate (`if not has_rs: continue`) runs AFTER accel-300 standalone bypass at lines 586-591, silently dropping all standalone accel-300 signals. `ACCEL_300_STANDALONE_BYPASS_ENABLED` flag is dead code. | Standalone accel-300 bypass never fires |

### Medium (3)

| # | File:Line | Bug | Impact |
|---|-----------|-----|--------|
| 2 | `exhaustion.py:35-36` | `MIN_GAP_PCT_SHORT = 0.00` vs `MIN_GAP_PCT_LONG = 0.20` — SHORT fires on any cross, LONG requires 0.20% gap | SHORT exhaustion fires more frequently, lower quality |
| 5 | `hl-sync-guardian.py:210-261` | `_save_cooldowns` missing FileLock, `_record_loss_cooldown` catches re-raise with `pass` | Loss cooldowns can be silently dropped or corrupted |
| 7 | `breakout_engine.py:39-44` | Hardcoded paths instead of importing from `paths.py` | Breakout engine reads wrong DBs if directory changes |

### Low (6)

| # | File:Line | Bug | Impact |
|---|-----------|-----|--------|
| 1 | `hzscore.py:14` | Docstring says `MIN_Z_VALUE = 0.6`, actual value is `0.4` | Stale comment, no runtime impact |
| 3 | `rs.py:431-436` | Legacy path only checks `low` for touches, misses `high` (resistance undercount) | Legacy path rarely used |
| 6 | `position_manager.py:1577` | `float | None` syntax requires Python 3.10+, rest of codebase uses `Optional[float]` | Style inconsistency |
| 8 | `zscore_pump.py:70` | `DRY_RUN = '--dry' in sys.argv` evaluated at import time, not at run time | Wrong when imported by signals_runner |
| 9 | `brain.py:92-126` | `call_ollama` validates for `DECISION:`/`CONFIDENCE:` but prompt asks for JSON with `people/topics/sentiment/etc` | Metadata extraction always returns empty |
| 10 | `decider_run.py:60` | `detect_incomplete_run` and `checkpoint_read_last` aliased to same lambda object | Cosmetic, no runtime impact |

## Approach

Fix bugs in severity order (High → Medium → Low). Each fix is a small, targeted edit.

### Fix 1: Bug 4 — RS gate blocks accel-300 standalone bypass (High)

**File:** `signal_compactor.py:689-694`

**Flow:**
1. Lines 586-591: accel-300 standalone bypass sets `pass_gate = True`, signal appended to `signals` at line 602
2. Lines 689-694: RS required gate runs on ALL signals in list, drops any without RS component

**Current:**
```python
            # ── rs required (replaces accel-300, 2026-05-15) ──────────────────────────
            has_rs = any(p.startswith('rs') for p in source_parts)
            if not has_rs:
                if verbose:
                    log(f"  SKIP {token} {direction}: no rs signal")
                continue
```

**Fix:** Skip RS gate if source starts with 'accel-300' (standalone bypass):
```python
            # ── rs required (replaces accel-300, 2026-05-15) ──────────────────────────
            # Accel-300 standalone bypass: skip RS gate for accel-300 signals
            is_accel300_standalone = source.startswith('accel-300')
            has_rs = any(p.startswith('rs') for p in source_parts)
            if not has_rs and not is_accel300_standalone:
                if verbose:
                    log(f"  SKIP {token} {direction}: no rs signal")
                continue
```

### Fix 2: Bug 2 — Asymmetric exhaustion gap (Medium)

**File:** `exhaustion.py:35-36`

This is intentional per comments ("SHORT: any cross after long grind fires — gap is secondary"). The question is whether this is a design choice or a bug. The subagent flagged it as creating "lower quality SHORT entries."

**Recommendation:** This appears to be an intentional design choice. Leave as-is unless T wants to change the threshold. Document in plan but skip fix.

### Fix 3: Bug 5 — Missing FileLock on cooldown writes (Medium)

**File:** `hl-sync-guardian.py:210-216`

**Current:**
```python
def _save_cooldowns(data: dict) -> None:
    try:
        with open(LOSS_COOLDOWN_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log(f'[_save_cooldowns] FAILED to write {LOSS_COOLDOWN_FILE}: {e}', 'FAIL')
        raise  # Re-raise so caller knows the save failed
```

**Fix:** Add FileLock:
```python
def _save_cooldowns(data: dict) -> None:
    from hermes_file_lock import FileLock
    try:
        with FileLock('loss_cooldown'):
            with open(LOSS_COOLDOWN_FILE, 'w') as f:
                json.dump(data, f, indent=2)
    except Exception as e:
        log(f'[_save_cooldowns] FAILED to write {LOSS_COOLDOWN_FILE}: {e}', 'FAIL')
        raise
```

Also fix the exception swallowing in `_record_loss_cooldown` at line 260-261:
```python
    except Exception:
        pass  # Error already logged and re-raised by _save_cooldowns
```

The comment says "already logged and re-raised" but the `pass` swallows the re-raise. Should be:
```python
    except Exception:
        log(f'  [Guardian] LOSS COOLDOWN FAILED for {token} {direction}', 'FAIL')
```

### Fix 4: Bug 7 — Hardcoded paths in breakout_engine (Medium)

**File:** `breakout_engine.py:39-44`

**Current:**
```python
HERMES_DATA  = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'data')
CANDLES_DB   = os.path.join(HERMES_DATA, 'candles.db')
RUNTIME_DB   = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
OC_PENDING   = '/var/www/hermes/data/oc_pending_signals.json'
HOTSET_PATH  = '/var/www/hermes/data/hotset.json'
WWW_DATA     = '/var/www/hermes/data'
LOG_FILE     = '/var/www/hermes/logs/breakout_engine.log'
```

**paths.py defines:** `HERMES_DATA`, `WWW_DATA`, `RUNTIME_DB`, `CANDLES_DB`, `HOTSET_FILE`

**Usage in breakout_engine:** Uses `HOTSET_PATH` at lines 487, 489, 541

**Fix:** Import from paths.py, alias HOTSET_FILE as HOTSET_PATH:
```python
from paths import HERMES_DATA, WWW_DATA, CANDLES_DB, RUNTIME_DB, HOTSET_FILE as HOTSET_PATH
OC_PENDING   = '/var/www/hermes/data/oc_pending_signals.json'
LOG_FILE     = '/var/www/hermes/logs/breakout_engine.log'
```

Remove lines 39-44 (the hardcoded definitions).

### Fix 5: Bug 1 — Stale comment in hzscore.py (Low)

**File:** `hzscore.py:14`

**Current:**
```python
FIX (2026-05-07): Added MIN_Z_VALUE = 0.6.
  - Historical data: winners had avg_z ~2.0, losers ~0.72. Marginal z-scores
    in chop zone produce 35% WR vs 47%+ WR at extreme readings.
  - Only fire when |avg_z| >= 0.6 — excludes marginal readings in the noise zone.
```

**Fix:**
```python
FIX (2026-05-07): Added MIN_Z_VALUE = 0.4.
  - Historical data: winners had avg_z ~2.0, losers ~0.72. Marginal z-scores
    in chop zone produce 35% WR vs 47%+ WR at extreme readings.
  - Only fire when |avg_z| >= 0.4 — excludes marginal readings in the noise zone.
  - Was 0.6, too tight — blocked 50% of signals.
```

### Fix 6: Bug 3 — Legacy path touch counting (Low)

**File:** `rs.py:431-436`

**Current:**
```python
    count = 0
    for c in candles:
        low_touch = abs(c['low'] - level)
        if low_touch < threshold:
            count += 1
    return count
```

**Fix:**
```python
    count = 0
    for c in candles:
        low_touch = abs(c['low'] - level)
        high_touch = abs(c['high'] - level)
        if low_touch < threshold or high_touch < threshold:
            count += 1
    return count
```

### Fix 7: Bug 6 — Python 3.10+ syntax (Low)

**File:** `position_manager.py:1577`

**Current:**
```python
    tokens_seen: Dict[str, float | None] = {}
```

**Fix:**
```python
    tokens_seen: Dict[str, Optional[float]] = {}
```

### Fix 8: Bug 8 — DRY_RUN import-time evaluation (Low)

**File:** `zscore_pump.py:70`

**Current:**
```python
DRY_RUN = '--dry' in sys.argv
```

**Fix:** Move to function scope:
```python
def run():
    global DRY_RUN
    DRY_RUN = '--dry' in sys.argv
    # ... rest of function
```

Or check in `run()`:
```python
def run(dry_run=False):
    _dry = dry_run or ('--dry' in sys.argv)
    # ... use _dry throughout
```

### Fix 9: Bug 9 — brain.py validation mismatch (Low)

**File:** `brain.py:119-121`

**Current:**
```python
        if "DECISION:" not in raw_resp or "CONFIDENCE:" not in raw_resp:
            print(f"[brain.py] Ollama response validation failed — missing DECISION/CONFIDENCE")
            return {}  # safe default
```

**Fix:** Remove the validation or make it check for valid JSON instead:
```python
        # Validate response is valid JSON (no field check — prompt asks for JSON output)
        result = json.loads(raw_resp)
        if not isinstance(result, dict):
            print(f"[brain.py] Ollama response is not a dict: {type(result)}")
            return {}
        return result
```

### Fix 10: Bug 10 — Lambda aliasing (Low)

**File:** `decider_run.py:60`

**Current:**
```python
    checkpoint_read_last = detect_incomplete_run = lambda *a, **a2: None
```

**Fix:**
```python
    checkpoint_read_last = lambda *a, **k: None
    detect_incomplete_run = lambda *a, **k: None
```

## Files to Change

| File | Fixes |
|------|-------|
| `scripts/signal_compactor.py` | Bug 4 |
| `scripts/hl-sync-guardian.py` | Bug 5 |
| `scripts/breakout_engine.py` | Bug 7 |
| `scripts/signals/hzscore.py` | Bug 1 |
| `scripts/signals/rs.py` | Bug 3 |
| `scripts/position_manager.py` | Bug 6 |
| `scripts/signals/zscore_pump.py` | Bug 8 |
| `scripts/brain.py` | Bug 9 |
| `scripts/decider_run.py` | Bug 10 |

## Verification

After each fix:
1. `python3 -m py_compile <file>` — syntax check
2. For Bug 4: check that accel-300 standalone signals pass through the RS gate
3. For Bug 5: verify FileLock is used and exception is not silently swallowed
4. For Bug 7: verify paths match those in `paths.py`

## Commit Strategy

One commit per fix, conventional-commit format:
```
fix(signal-compactor): allow accel-300 standalone bypass to pass RS gate
fix(hl-sync-guardian): add FileLock to cooldown writes, don't swallow exceptions
fix(breakout-engine): import paths from paths.py instead of hardcoding
fix(hzscore): update stale comment to match actual MIN_Z_VALUE=0.4
fix(rs): legacy path checks both high and low for touch counting
fix(position-manager): use Optional[float] instead of float | None syntax
fix(zscore-pump): move DRY_RUN check to function scope
fix(brain): remove incorrect DECISION/CONFIDENCE validation from call_ollama
fix(decider-run): separate lambda aliases for checkpoint_read_last and detect_incomplete_run
```
