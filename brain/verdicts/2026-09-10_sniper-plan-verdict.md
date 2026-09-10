# Independent Auditor Verdict — Sniper Exit Strategy Plan

**Date:** 2026-09-10
**Auditor:** Independent (fresh eyes, no prior context)
**Plan file:** `/root/.hermes/plans/sniper-exit-strategy.md`
**Verdict:** **PARTIAL — Concept is sound, but implementation has multiple critical bugs**

---

## Verdict Summary

| Area | Verdict | Severity |
|------|---------|----------|
| Core concept (directional selectivity) | AGREE | — |
| Shift detection algorithm | DISAGREE | CRITICAL — 3 bugs that will crash |
| `check_btc_crash()` API usage | DISAGREE | CRITICAL — wrong function name, wrong access pattern |
| `multi_alt_divergence` field access | DISAGREE | CRITICAL — field does not exist |
| Helper functions (`get_btc_wave_phase`, etc.) | DISAGREE | CRITICAL — none exist |
| `close_position()` call | DISAGREE | CRITICAL — no such function with this signature |
| Trail state type matching | DISAGREE | BUG — int vs str key mismatch |
| Direction voting logic | AGREE | Sound |
| Timing/spacing pattern | AGREE | Compatible with existing systems |
| Momentum cache freshness | DISAGREE | CRITICAL — BTC data is 14 days stale |
| Race conditions with PM/CL | DISAGREE | HIGH — no mutual exclusion guards |
| LIFO sorting on `open_time` | PARTIAL | MEDIUM — fragile string comparison |
| Existing infrastructure integration | PARTIAL | Data stores exist but no accessor functions |

**Overall: 7 CRITICAL bugs, 2 HIGH issues, 1 MEDIUM issue. Concept approved, implementation NOT ready to deploy.**

---

## Detailed Findings

---

### VERDICT 1: `check_btc_crash()` function name

**Claim:** Plan imports and calls `check_btc_crash()` from `btc_crash_filter`

**Verdict: DISAGREE**

**Evidence:**
```
$ grep -n "def check" btc_crash_filter.py
Line 403: def check_crash() -> CrashSignal:
Line 620: def check_position_protection(positions: list) -> List[PositionProtection]:

$ grep -rn "check_btc_crash" scripts/
(no matches found)
```

The function is `check_crash()`, not `check_btc_crash()`. The plan's import statement `from btc_crash_filter import check_btc_crash` will raise `ImportError`. The function does not exist anywhere in the codebase.

**Fix:** Change all references from `check_btc_crash()` to `check_crash()`.

**Confidence: HIGH**

---

### VERDICT 2: CrashSignal dict access pattern

**Claim:** Plan uses `crash_result['blocked']`, `crash_result.get('severity')`, `crash_result.get('multi_alt_divergence')`

**Verdict: DISAGREE**

**Evidence:**
```python
# Live test output:
$ python3 -c "from scripts.btc_crash_filter import check_crash; r = check_crash(); print(r['blocked'])"
TypeError: 'CrashSignal' object is not subscriptable

# CrashSignal is a dataclass:
class CrashSignal:
    blocked: bool = False
    reason: str = ''
    severity: str = ''
    ...
```

`check_crash()` returns a `CrashSignal` dataclass, NOT a dict. Dict-style access `crash_result['blocked']` will raise `TypeError`. The correct access is `crash_result.blocked` (attribute access). The `result.get()` calls will also fail with `AttributeError`.

**Fix:** Change all dict access to attribute access: `result.blocked`, `result.severity`, etc.

**Confidence: HIGH**

---

### VERDICT 3: `multi_alt_divergence` field does not exist

**Claim:** Plan accesses `crash_result.get('multi_alt_divergence')`

**Verdict: DISAGREE**

**Evidence:**
```
# CrashSignal fields (from live test):
['blocked', 'reason', 'severity', 'layer', 'blocked_direction',
 'price_chg_5m', 'price_chg_1m', 'volume_spike', 'eth_divergence',
 'btc_atr_pct', 'dynamic_threshold', 'block_duration_sec', 'block_until', 'raw']

# No 'multi_alt_divergence' field exists.

# Multi-alt divergence data is stored in:
signal.raw['weak_alt_count']  # int — number of weak alts
signal.raw['weak_alts']       # list — which alts are weak
# But ONLY when multi_alt_blocked is True.

# Live test confirms:
result.raw.get('multi_alt_divergence', 'NOT IN RAW')  # → 'NOT IN RAW'
```

The field `multi_alt_divergence` does not exist on CrashSignal and is not in the `raw` dict. The multi-alt divergence information is at `result.raw['weak_alt_count']` and `result.raw['weak_alts']`, but only populated when Layer 6 triggers.

**Fix:** Access `result.raw.get('weak_alt_count', 0)` instead. Also check if `result.layer` contains 'MULTI_ALT'.

**Confidence: HIGH**

---

### VERDICT 4: Helper functions don't exist

**Claim:** Plan calls `get_btc_wave_phase()`, `get_btc_velocity()`, `get_btc_momentum_state()`, `volatility_regime_changed()`, `get_btc_slope_15m()`

**Verdict: DISAGREE**

**Evidence:**
```
$ grep -rn "def get_btc_wave_phase\|def get_btc_velocity\|def get_btc_momentum_state\|def volatility_regime_changed\|def get_btc_slope_15m" scripts/
(no matches found)
```

None of these 5 functions exist anywhere in the codebase. The plan treats them as if they're available from existing infrastructure. They are NOT — they would all need to be implemented.

The underlying DATA exists:
- `wave_phase` is in `token_speeds` table (signals_hermes_runtime.db)
- `velocity` and `momentum_state` are in `momentum_cache` table (same DB)
- Volatility regime data exists in `volatility_gate` signals

But no accessor functions exist to read them cleanly.

**Fix:** Implement these 5 functions before building the shift detection algorithm. Each should query the correct SQLite table from `signals_hermes_runtime.db`.

**Confidence: HIGH**

---

### VERDICT 5: `close_position()` function signature mismatch

**Claim:** Plan calls `close_position(pos, reason=reason)` in the execution loop

**Verdict: DISAGREE**

**Evidence:**
```
Existing close functions:
  profit_monster.close_position(trade_id, token, direction, pnl_pct, current_price, dry_run, tier)
  cut_loser.close_position(trade_id, token, direction, pnl_pct, current_price, dry_run, tier)
  position_manager.close_paper_position(trade_id, reason)
  hyperliquid_exchange.close_position(name, slippage=0.02)

No function matches: close_position(pos, reason=reason)
```

The plan's pseudocode `close_position(pos, reason=reason)` does not match ANY existing function signature. The sniper script would need to implement its own close function or adapt to use `position_manager.close_paper_position(trade_id, reason)` — but that only handles paper trades, not HL execution.

For live trading, the sniper would need to:
1. Close on Hyperliquid via `hyperliquid_exchange.close_position()`
2. Update DB via `brain.py close_trade()` or similar
3. Handle fill price, slippage, error recovery

This is non-trivial and the plan glosses over it entirely.

**Fix:** Design an explicit `sniper_close_position()` that handles HL close + DB update, similar to what profit_monster does.

**Confidence: HIGH**

---

### VERDICT 6: Trail state type mismatch (int vs string keys)

**Claim:** Plan checks `p['id'] not in trail_state` to identify positions without trailing active

**Verdict: DISAGREE**

**Evidence:**
```
# profit_monster_trail_state.json keys:
["13366", "13480", "13654", ...]  ← strings

# get_open_positions() returns dict with 'id' from PostgreSQL:
# id is INTEGER in the trades table

# Python comparison:
13366 not in {"13366": ...}  → True (always!)
# int 13366 never equals str "13366" in dict lookup
```

The trail state JSON has string keys (`"13366"`), but position IDs from PostgreSQL are integers. The check `p['id'] not in trail_state` will ALWAYS return True because `int != str`. This means ALL positions would be classified as "no trailing" — Tier 1 and Tier 3 categorization would be completely broken.

**Fix:** Convert position ID to string before checking: `str(p['id']) not in trail_state`

**Confidence: HIGH**

---

### VERDICT 7: momentum_cache BTC data is 14 days stale

**Claim:** Plan reads momentum_state and velocity from momentum_cache for shift detection

**Verdict: DISAGREE**

**Evidence:**
```
$ python3 -c "
import sqlite3, time
conn = sqlite3.connect('data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute('SELECT token, momentum_state, velocity, updated_at FROM momentum_cache WHERE token=\"BTC\"')
row = cur.fetchone()
age = time.time() - float(row[3])
print(f'BTC momentum_state: {row[1]}')
print(f'BTC velocity: {row[2]}')
print(f'Last update: {age/60:.0f} minutes ago ({age/86400:.1f} days)')
"
BTC momentum_state: neutral
BTC velocity: 0.0256
Last update: 20303 minutes ago (14.1 days)
```

The BTC momentum_cache entry is **14 days old**. Any velocity or momentum_state reads from this would be completely stale. The plan assumes this data is refreshed regularly (every ~15 min based on the scan intervals), but the last update was September 26 — not today.

This means:
- `get_btc_momentum_state()` would return 'neutral' regardless of current conditions
- `get_btc_velocity()` would return 0.0256 regardless of current conditions
- The entire shift detection algorithm would be operating on stale data

**Root cause:** The 15m regime scanner or whatever writes to momentum_cache appears to not be running or not updating BTC.

**Fix:** Ensure momentum_cache is being updated. Check if the 15m regime scanner is active. Add a staleness check to sniper: if `updated_at` is older than 30 min, don't use momentum signals.

**Confidence: HIGH**

---

### VERDICT 8: Race conditions with profit_monster / cut_loser

**Claim:** Plan does not mention race condition mitigation

**Verdict: DISAGREE (with existing system)**

**Evidence:**
```
# cut_loser.close_position checks:
  1. is_token_being_closed_by_guardian(token)  ← checks guardian markers
  2. is_token_being_closed_by_profit_monster(token)  ← checks trail_state JSON
  3. is_position_on_hl(token)

# profit_monster.close_position checks:
  1. is_token_being_closed_by_guardian(token)  ← checks guardian markers
  2. is_position_on_hl(token)
  # Does NOT check cut_loser!

# Neither checks for sniper!
```

If sniper fires at the same time as profit_monster or cut_loser:
1. **Sniper + profit_monster:** Both could try to close the same position on HL. HL might reject the second close (position already gone), but the DB update could still happen, creating phantom trades.
2. **Sniper + cut_loser:** Same issue. cut_loser checks profit_monster but not sniper.
3. **cut_loser + profit_monster:** Already has a partial guard (CL checks PM), but PM doesn't check CL. This is an existing issue, not introduced by sniper.

The plan has NO mutual exclusion mechanism. The 3-minute timer approach means sniper runs independently from PM's 5-10 min windows.

**Fix:** 
1. Add a `is_token_being_closed_by_sniper()` check in profit_monster and cut_loser
2. Have sniper write a closing marker (like guardian does) before executing
3. Or use a shared lock file per-token

**Confidence: HIGH**

---

### VERDICT 9: Direction voting logic

**Claim:** "All signals must agree on direction. If signals disagree (some bullish, some bearish), no shift is declared."

**Verdict: PARTIAL**

**Evidence:**
The plan's pseudocode uses majority voting, not strict agreement:
```python
if bearish > bullish:
    direction = 'BEARISH'
elif bullish > bearish:
    direction = 'BULLISH'
else:
    return None  # Tied — uncertain, don't act
```

This is NOT "all signals must agree" — it's "majority must agree." Example:
- 2 bearish signals + 1 bullish signal = BEARISH (2 vs 1)
- The plan text says "all signals must agree" but the code does majority voting

The majority approach is actually BETTER than strict agreement (which would fail on 2-1 splits). But the text is misleading.

Also, CRITICAL severity crash adds 2 to bearish votes (not 1). So 1 CRITICAL + 1 bullish = 2 bearish vs 1 bullish → BEARISH wins at Level 2. This is reasonable but undocumented in the text.

**Fix:** Update plan text to say "majority must agree" instead of "all signals must agree." Document that CRITICAL counts as 2 votes.

**Confidence: HIGH**

---

### VERDICT 10: LIFO sorting on open_time

**Claim:** Plan sorts losing positions by `open_time` in reverse (LIFO — most recent first)

**Verdict: PARTIAL**

**Evidence:**
```python
tier2 = sorted(
    [p for p in wrong_side if p['pnl_pct'] < -SNIPER_MIN_LOSS_THRESHOLD],
    key=lambda p: p['open_time'],
    reverse=True  # LIFO
)
```

The `open_time` comes from PostgreSQL as a datetime/timestamp. When returned by psycopg2 with `RealDictCursor`, it's a Python `datetime` object. Sorting datetime objects works correctly with `sorted()` — `reverse=True` puts the most recent first. This is CORRECT for LIFO.

However, there's a subtle issue: the plan doesn't handle the case where `open_time` is None (could happen for migrated trades). This would crash `sorted()` with a TypeError.

**Fix:** Filter out positions with None open_time, or use a fallback: `key=lambda p: p['open_time'] or datetime.min`.

**Confidence: MEDIUM**

---

### VERDICT 11: Timing/spacing compatibility

**Claim:** Plan spaces 1-2 positions every 3 minutes

**Verdict: AGREE**

**Evidence:**
- profit_monster `should_fire()`: uses 5-10 min windows with random jitter → fires every 5-10 min
- cut_loser: runs as part of pipeline or standalone timer
- sniper: 3 min intervals → fires 2-3x per PM cycle

The 3-minute spacing is compatible with PM's 5-10 minute windows. There's no timing conflict. The worst case is sniper fires while PM is also checking, but that's the race condition issue (Verdict 8), not a timing issue.

**Confidence: HIGH**

---

### VERDICT 12: SNIPER_* constants not yet in hermes_constants.py

**Claim:** Plan references SNIPER_ENABLED, SNIPER_CHECK_INTERVAL, etc.

**Verdict: EXPECTED (not yet implemented)**

**Evidence:**
```
$ grep -n "^SNIPER_" scripts/hermes_constants.py
(no matches)
```

The constants don't exist yet. This is expected since the plan is pending approval and sniper_exit.py hasn't been created. Not a bug in the plan — it's a prerequisite for implementation.

**Note:** The NEUTRAL_SNIPER_* constants exist (different system — mean-reversion for NEUTRAL regime). Don't confuse with the exit sniper.

**Confidence: HIGH**

---

## Additional Issues Found (Sideways Finds)

### Issue A: momentum_cache table missing from brain.db

```
$ python3 -c "import sqlite3; conn = sqlite3.connect('data/brain.db'); cur = conn.cursor(); cur.execute('SELECT * FROM momentum_cache'); ..."
OperationalError: no such table: momentum_cache
```

brain.db (SQLite) has no momentum_cache table. The signal_compactor.py reads from brain.db's momentum_cache, but it doesn't exist. The momentum_cache is in `signals_hermes_runtime.db` (a different SQLite DB). There may be a PostgreSQL brain DB that's currently offline.

**Severity: MEDIUM** — This affects signal_compactor's directional bias layer, not just sniper.

### Issue B: PostgreSQL is down

```
$ python3 -c "import psycopg2; conn = psycopg2.connect(...)"
Connection refused
```

position_manager depends on PostgreSQL for all trade data. If PostgreSQL is down, `get_open_positions()` returns `[]` — sniper would have nothing to close. The plan should check for this.

**Severity: LOW** — Operational issue, not a plan bug.

### Issue C: Plan references `signal.raw` dict but crash filter doesn't always populate it

The `raw` dict in CrashSignal is populated inconsistently:
- `weak_alt_count` and `weak_alts` only populated when multi_alt triggers
- `momentum_dir` only populated when MOMENTUM layer triggers
- Plan code would need to handle missing keys

**Severity: LOW** — Access with `.get()` defaults handles this.

---

## Final Score

| Metric | Count |
|--------|-------|
| CRITICAL bugs (will crash) | 5 |
| HIGH bugs (incorrect behavior) | 2 |
| MEDIUM issues | 2 |
| Sound design decisions | 4 |
| Total findings | 13 |

**Bottom line:** The CONCEPT is correct and well-designed. The DIRECTIONAL SELECTIVITY principle is sound — closing wrong-side and riding right-side is mathematically optimal during trend shifts. The TIMING/SPACING is compatible with existing systems. The VOTING LOGIC (majority, not strict agreement) is correct.

But the IMPLEMENTATION has 5 critical bugs that would prevent it from running:
1. Wrong function name (`check_btc_crash` → `check_crash`)
2. Wrong access pattern (dict → attribute)
3. Non-existent field (`multi_alt_divergence`)
4. Missing helper functions (5 functions don't exist)
5. Broken trail state type matching (int vs str)

Plus the momentum_cache data is 14 days stale, making the velocity/momentum signals useless until that's fixed.

**Recommendation:** Fix the 5 critical bugs, implement the 5 helper functions, add mutual exclusion guards, fix the momentum_cache freshness, and re-audit before deployment.

---

*End of independent audit.*
