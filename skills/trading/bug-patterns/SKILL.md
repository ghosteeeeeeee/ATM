# Common Bug Patterns in Hermes Codebase

Date: 2026-08-05
Source: Bug hunter systematic codebase analysis

## Top 10 Recurring Bug Patterns

### 1. Bare `except:` with Silent Failure (CRITICAL)
**80+ instances** — errors vanish without trace, making debugging impossible.
**Fix:** Linter rule `bare-except`, replace with `except Exception as e: log(...)`.

### 2. Connection Leaks — No `finally` Block (HIGH)
SQLite connections opened but only closed in happy path.
**Fix:** Create `_db_cursor()` context manager in `signal_schema.py`.

### 3. Non-Atomic JSON Writes (HIGH)
`open(path, 'w')` truncates before writing. Crash = corrupted file.
**Fix:** Add `atomic_json_write()` to `hermes_file_lock.py`.

### 4. Duplicated `ema()/rsi()/macd()` Functions (MEDIUM)
Same indicator functions re-implemented in 15+ files.
**Fix:** Extract to `indicators.py`, import from there.

### 5. Hardcoded Database Credentials (MEDIUM SECURITY)
93 files with `password=` in source.
**Fix:** Replace with `from _secrets import BRAIN_DB_DICT`, add CI check.

### 6. `token` vs `coin` Naming Inconsistency (MEDIUM)
Mixes Hyperliquid's `coin` with DB's `token`.
**Fix:** Standardize on `coin` for HL, `token` for DB, explicit mapping at boundary.

### 7. Stale/Dead Code Left in Place (MEDIUM)
`ai_decider.py` (3200+ lines), `.bak` files, legacy paths.
**Fix:** Delete if unused 30 days, move `.bak` to `archive/`.

### 8. Missing `finally` in Cursor Cleanup (HIGH)
`cur.close(); conn.close()` without `finally`.
**Fix:** Same as #2 — use `_db_cursor()` context manager.

### 9. Configuration Drift — Hardcoded Constants (LOW-MEDIUM)
Magic numbers scattered across files.
**Fix:** Any value used in 2+ files → `hermes_constants.py`.

### 10. Non-Atomic File Writes Under Concurrent Access (HIGH)
Multiple processes write same JSON without locking.
**Fix:** Move `_atomic_write` to shared utility, enforce usage.

## Top 5 Systemic Fixes

| Priority | Fix | Impact |
|----------|-----|--------|
| 1 | `_db_cursor()` context manager | Eliminates ~50+ leak sites |
| 2 | `atomic_json_write()` utility | Eliminates ~30+ corruption sites |
| 3 | Lint rule: ban bare `except:` | Eliminates ~80+ silent failures |
| 4 | Extract indicators to `indicators.py` | Eliminates 15+ duplicated functions |
| 5 | CI check for hardcoded passwords | Eliminates ~10+ security leaks |

## Key Insight

> "The `except: pass` is the fastest way to 'fix' a crash — it works until you need to debug why something silently stopped working."

Most bugs stem from **missing shared utilities** (DB context manager, atomic write, indicator functions). Each file reimplements the wheel with slightly different edge cases.
