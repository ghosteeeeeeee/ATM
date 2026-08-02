# Plan: Trading System Bug Fixes (Verified 2026-07-19)

## Status: ALL 11 BUGS FIXED ✓ — VERIFIED BY AI-ENGINEER SUBAGENT

| Bug | Severity | File | Status |
|-----|----------|------|--------|
| 6 | Critical | `decider_run.py` | **FIXED + VERIFIED** — `_skip_signal` flag + `break` + outer `continue` |
| 2 | High | `position_manager.py` | **FIXED + VERIFIED** — SHORT SL uses `effective_sl_pct` with `max()` floor |
| 5 | High | `decider_run.py` | **FIXED + VERIFIED** — Reset count/last after cooldown expires |
| 8 | High | `breakout_engine.py` | **FIXED + VERIFIED** — No sort/top-10, all entries preserved |
| 9/11 | High | `hl-sync-guardian.py` | **FIXED + VERIFIED** — Dict used directly |
| 1/12 | Medium | `decider_run.py` | **FIXED + VERIFIED** — `>= EPSILON` exploit 80% |
| 7 | Medium | `decider_run.py` | **FIXED + VERIFIED** — FileLock added |
| 10 | Medium | `signal_compactor.py` | **FIXED + VERIFIED** — isinstance type guard |
| 14 | Medium | `rs.py` | **FIXED + VERIFIED** — datetime string format |
| 15 | Medium | `decider_run.py` | **FIXED + VERIFIED** — Reset persisted to disk |
| 19 | Medium | `signal_compactor.py` | **FIXED + VERIFIED** — FileLock added |

No regressions detected.

## Goal

Fix 11 verified bugs in the Hermes trading system, prioritized by severity.

## Context

- Previous session (2026-07-19 ~04:37 UTC) identified 19 potential bugs via subagent audit
- Re-verified all 19 bugs against current codebase — 11 confirmed, 1 false positive, 7 were duplicates or already fixed
- All bugs exist in production scripts under `/root/.hermes/scripts/`

## Verified Bug List

### Critical (1)

| # | File:Line | Bug | Impact |
|---|-----------|-----|--------|
| 6 | `decider_run.py:1641-1692` | Layer 3 kill-switch `continue` only skips inner `_comp` loop, not outer `sig` loop. Comment at line 1697 incorrectly claims it skips outer loop. | Blocked signal components still execute trades |

### High (4)

| # | File:Line | Bug | Impact |
|---|-----------|-----|--------|
| 2 | `position_manager.py:1519-1523` | SHORT SL computes `effective_sl_pct` from ATR (lines 1506-1511) but ignores it at line 1523, always uses `ATR_SL_MIN` (0.7%). LONG path correctly uses `effective_sl_pct`. | SHORT stops too tight, hit on normal volatility |
| 5 | `decider_run.py:1287-1296` | `_record_hotset_failure` increments count, never resets. After 2 failures, count stays ≥2 forever. Each new failure within hour extends cooldown; each failure after hour immediately re-triggers. | Tokens permanently blocked after 2 failures |
| 8 | `breakout_engine.py:468-533` | `write_to_hotset` dedupes, sorts by score, keeps top 10. Breakout signals score 100+ (line 500: `100 + vol_ratio`), always rank above normal signals. | Breakout engine evicts all signal_compactor signals from hotset |
| 9/11 | `hl-sync-guardian.py:70-71` | `get_open_hype_positions_curl()` returns `dict` (line 492: `out = {}`), but `{p.get('coin'): p for p in fresh}` iterates dict keys (strings), not values. `p.get('coin')` on string → AttributeError. | Guardian fails to get HL positions when hype_cache is cold |

### Medium (6)

| # | File:Line | Bug | Impact |
|---|-----------|-----|--------|
| 1/12 | `decider_run.py:360` | `random.random() < EPSILON` triggers exploit 20% of time. Standard epsilon-greedy: exploit = `random.random() >= EPSILON` (80%). | A/B testing explores too much, under-utilizes winners |
| 7 | `decider_run.py:167-176` | `_is_guardian_closing` reads `guardian-closing-markers.json` without FileLock. Writer (`hl-sync-guardian.py:377`) uses lock. | TOCTOU race — may miss closing markers, allow duplicate positions |
| 10 | `signal_compactor.py:833-837` | `prev_entry.get('entry_origin_ts')` could be string from old hotset.json. `time.time() - string` → TypeError crash. | Potential crash on compaction |
| 14 | `rs.py:896-904` | Cooldown cutoff in milliseconds (`* 1000`), but `signal_history.created_at` may store seconds. Query compares wrong units. | Cooldown may not work — signals fire too frequently |
| 15 | `decider_run.py:812-824` | `_get_hotset_approval_rate` returns `(0, now)` in-memory on window expiry but never writes to disk. Next read gets stale count. | Rate limit may not reset, allowing >3 approvals/min |
| 19 | `signal_compactor.py:106-108` | `_get_open_tokens` reads guardian closing markers without FileLock. Same issue as Bug 7. | May miss closing markers during concurrent guardian close |

### Not a Bug (1)

| # | File | Reported As | Verdict |
|---|------|-------------|---------|
| 4 | `decider_run.py:846-858` | `_save_hotset_failures` loses concurrent writes | FileLock serializes access. Re-read-under-lock is correct pattern. |

## Approach

Fix bugs in severity order (Critical → High → Medium). Each fix is a small, targeted edit.

### Fix 1: Bug 6 — Layer 3 kill-switch outer loop skip (Critical)

**File:** `decider_run.py:1694-1697`

The `continue` inside `for _comp in _components` only skips to the next component. Need to add a flag and check after the inner loop to skip the outer signal loop.

**Current (lines 1640-1698):**
```python
            _components = source.split(',')
            for _comp in _components:
                if _comp == 'pct-hermes+' and not PCT_HERMES_PLUS_ENABLED:
                    log(f'  SKIP {token} {direction}: PCT_HERMES_PLUS_ENABLED=False')
                    skipped += 1; continue
                # ... many more conditions ...
        except ImportError:
            pass  # hermes_constants not available — skip gate

        # Check skip flag before proceeding (set by Layer 3 gate above)
        # The continue above sets a 'continue' but we need to check after the try/except
        # Re-check: if the loop hit a continue, we need to break to next signal
        # Actually the 'continue' above already skips to next iteration of the for loop
        price = sig.get('price') or get_current_price(token)
```

**Fix:** Add `_skip_signal = False` before inner loop, set it on skip, check after try/except.

```python
            _skip_signal = False
            _components = source.split(',')
            for _comp in _components:
                if _comp == 'pct-hermes+' and not PCT_HERMES_PLUS_ENABLED:
                    log(f'  SKIP {token} {direction}: PCT_HERMES_PLUS_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                # ... update all `continue` to `break` ...
            if _skip_signal:
                continue  # skip to next signal in outer loop
        except ImportError:
            pass  # hermes_constants not available — skip gate

        price = sig.get('price') or get_current_price(token)
```

### Fix 2: Bug 2 — SHORT SL ignores ATR distance (High)

**File:** `position_manager.py:1519-1523`

**Current:**
```python
    else:
        # SHORT: SL trails ABOVE current price as it falls (locks in profit)
        # SL = current_price + ATR_SL_MIN buffer — tight trailing for acceleration phase
        # The buffer is relative to current price, so as price falls, SL falls too
        result = current_price * (1 + ATR_SL_MIN)
```

**Fix:** Use `effective_sl_pct` like LONG does:
```python
    else:
        # SHORT: SL = current + k·ATR, never below current price (catches rallies)
        sl = entry_price * (1 + effective_sl_pct)
        result = max(sl, current_price * (1 + ATR_SL_MIN))
```

### Fix 3: Bug 5 — Failure count never resets (High)

**File:** `decider_run.py:1287-1296`

**Current:**
```python
def _record_hotset_failure(token: str, direction: str, failures: dict):
    """Record a failed trade for back-to-back failure cooldown."""
    import time
    now = time.time()
    if token not in failures:
        failures[token] = {'LONG': {'count': 0, 'last': 0}, 'SHORT': {'count': 0, 'last': 0}}
    dir_data = failures[token].setdefault(direction, {'count': 0, 'last': 0})
    dir_data['count'] = dir_data.get('count', 0) + 1
    dir_data['last'] = now
    _save_hotset_failures(failures)
```

**Fix:** Reset count to 0 after cooldown expires (in `_check_hotset_cooldown`):
```python
def _check_hotset_cooldown(token: str, direction: str, failures: dict) -> tuple:
    import time
    token = token.upper()
    now = time.time()
    COOLDOWN_SECS = 3600
    
    token_failures = failures.get(token, {})
    dir_failures = token_failures.get(direction, {})
    opp_direction = 'SHORT' if direction == 'LONG' else 'LONG'
    opp_failures = token_failures.get(opp_direction, {})
    
    dir_count = dir_failures.get('count', 0)
    dir_last = dir_failures.get('last', 0)
    
    # Reset if cooldown expired
    if dir_count >= 2 and (now - dir_last) >= COOLDOWN_SECS:
        dir_failures['count'] = 0
        dir_failures['last'] = 0
        failures[token][direction] = dir_failures
        _save_hotset_failures(failures)
    
    if dir_count >= 2 and (now - dir_last) < COOLDOWN_SECS:
        remaining = int(COOLDOWN_SECS - (now - dir_last))
        return True, f'{direction} in cooldown ({remaining}s left, {dir_count} failures)'
    
    opp_count = opp_failures.get('count', 0)
    opp_last = opp_failures.get('last', 0)
    if opp_count >= 2 and (now - opp_last) < COOLDOWN_SECS:
        return False, f'opposite {opp_direction} in cooldown ({opp_count} failures) — allowing {direction}'
    
    return False, ''
```

### Fix 4: Bug 8 — Breakout engine overwrites hotset (High)

**File:** `breakout_engine.py:530-533`

**Current:**
```python
        # Keep only top 10, sorted by score descending
        all_entries = list(existing_by_key.values())
        all_entries.sort(key=lambda x: x.get('score', 0), reverse=True)
        top10 = all_entries[:10]
```

**Fix:** Don't evict existing signals — append breakout signals and let signal_compactor handle ranking:
```python
        # Don't evict existing signals — just add breakout signals
        # signal_compactor's next compaction cycle will handle ranking/eviction
        all_entries = list(existing_by_key.values())
        output = {
            'hotset': all_entries,
            'compaction_cycle': 9999,
            'timestamp': time.time(),
        }
```

### Fix 5: Bug 9/11 — hl-sync-guardian dict iteration (High)

**File:** `hl-sync-guardian.py:70-71`

**Current:**
```python
        fresh = get_open_hype_positions_curl()
        _hl_positions_cache = {p.get('coin'): p for p in fresh}
```

**Fix:** `get_open_hype_positions_curl()` already returns a dict `{coin: position}`. Use it directly:
```python
        fresh = get_open_hype_positions_curl()
        _hl_positions_cache = fresh  # already {coin: position_data} dict
```

### Fix 6: Bug 1/12 — Epsilon-greedy inverted (Medium)

**File:** `decider_run.py:360`

**Current:**
```python
    if random.random() < EPSILON and exploit_vid:
```

**Fix:**
```python
    if random.random() >= EPSILON and exploit_vid:
```

### Fix 7: Bug 7 — Guardian closing marker no FileLock (Medium)

**File:** `decider_run.py:167-176`

**Current:**
```python
def _is_guardian_closing(token: str) -> bool:
    try:
        if os.path.exists(_GUARDIAN_CLOSING_FILE):
            with open(_GUARDIAN_CLOSING_FILE) as f:
                data = json.load(f)
            return token.upper() in data.get('tokens', {})
    except Exception:
        pass
    return False
```

**Fix:**
```python
def _is_guardian_closing(token: str) -> bool:
    try:
        if os.path.exists(_GUARDIAN_CLOSING_FILE):
            with FileLock('guardian_closing'):
                with open(_GUARDIAN_CLOSING_FILE) as f:
                    data = json.load(f)
            return token.upper() in data.get('tokens', {})
    except Exception:
        pass
    return False
```

### Fix 8: Bug 10 — entry_origin_ts type crash (Medium)

**File:** `signal_compactor.py:833-837`

**Current:**
```python
            if prev_entry:
                prev_origin_ts = prev_entry.get('entry_origin_ts')
                entry_origin_ts = prev_origin_ts if prev_origin_ts else time.time()
            else:
                entry_origin_ts = time.time()
            age_from_entry = (time.time() - entry_origin_ts) / 60.0
```

**Fix:**
```python
            if prev_entry:
                prev_origin_ts = prev_entry.get('entry_origin_ts')
                if isinstance(prev_origin_ts, (int, float)) and prev_origin_ts > 0:
                    entry_origin_ts = prev_origin_ts
                else:
                    entry_origin_ts = time.time()
            else:
                entry_origin_ts = time.time()
            age_from_entry = (time.time() - entry_origin_ts) / 60.0
```

### Fix 9: Bug 14 — rs.py cooldown timestamp units (Medium)

**File:** `rs.py:896-904`

Check what units `signal_history.created_at` uses. If seconds, remove `* 1000`. If milliseconds, the code is correct.

```python
            cooldown_cutoff_ms = int((time.time() - RS_COOLDOWN_HOURS * 3600) * 1000)
```

Need to verify DB schema before fixing.

### Fix 10: Bug 15 — Approval rate window never resets to disk (Medium)

**File:** `decider_run.py:812-824`

**Current:**
```python
def _get_hotset_approval_rate() -> tuple:
    try:
        if os.path.exists(_HOTSET_APPROVAL_RATE_FILE):
            with open(_HOTSET_APPROVAL_RATE_FILE) as f:
                data = json.load(f)
        else:
            return 0, 0
        count = data.get('count', 0)
        window_start = data.get('window_start', 0)
        now = time.time()
        if now - window_start > 60:
            return 0, now  # new window — but never writes to disk
        return count, window_start
    except Exception:
        return 0, time.time()
```

**Fix:**
```python
def _get_hotset_approval_rate() -> tuple:
    try:
        if os.path.exists(_HOTSET_APPROVAL_RATE_FILE):
            with open(_HOTSET_APPROVAL_RATE_FILE) as f:
                data = json.load(f)
        else:
            return 0, 0
        count = data.get('count', 0)
        window_start = data.get('window_start', 0)
        now = time.time()
        if now - window_start > 60:
            _increment_hotset_approval_rate(0, now)  # reset to disk
            return 0, now
        return count, window_start
    except Exception:
        return 0, time.time()
```

### Fix 11: Bug 19 — signal_compactor guardian markers no FileLock (Medium)

**File:** `signal_compactor.py:106-108`

**Current:**
```python
        if os.path.exists(closing_file):
            with open(closing_file) as f:
                data = json.load(f)
```

**Fix:**
```python
        if os.path.exists(closing_file):
            with FileLock('guardian_closing'):
                with open(closing_file) as f:
                    data = json.load(f)
```

## Files Changed

| File | Fixes Applied |
|------|---------------|
| `scripts/decider_run.py` | Bug 6, 5, 1/12, 7, 15 |
| `scripts/position_manager.py` | Bug 2 |
| `scripts/breakout_engine.py` | Bug 8 |
| `scripts/hl-sync-guardian.py` | Bug 9/11 |
| `scripts/signal_compactor.py` | Bug 10, 19 |
| `scripts/signals/rs.py` | Bug 14 |

## Verification

After each fix:
1. `python3 -m py_compile <file>` — syntax check
2. For behavioral fixes (Bug 6, 2, 5, 8): check production logs or run pipeline once
3. For race condition fixes (Bug 7, 19): code review only — hard to test without concurrent load

## Commit Strategy

One commit per fix, conventional-commit format:
```
fix(decider-run): Layer 3 kill-switch skip outer loop on disabled component
fix(position-manager): SHORT SL uses ATR-based distance like LONG
fix(decider-run): reset hotset failure count after cooldown expires
fix(breakout-engine): don't evict signal_compactor signals from hotset
fix(hl-sync-guardian): get_open_hype_positions_curl returns dict, not list
fix(decider-run): invert epsilon-greedy exploit/explore condition
fix(decider-run): read guardian closing markers under FileLock
fix(signal-compactor): guard entry_origin_ts against string type
fix(rs): verify cooldown timestamp units (seconds vs milliseconds)
fix(decider-run): reset approval rate counter to disk on window expiry
fix(signal-compactor): read guardian closing markers under FileLock
```
