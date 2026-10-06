# Bug Hunter Verdict — ride_it Exit Bug Fixes (commit 1b6f8f54)

**Auditor:** bug_hunter
**Date:** 2026-10-06
**Commit:** 1b6f8f54 — "fix: ride_it exit bugs — ATR off-by-one, SL widen, overlay conflicts"
**Files audited:** `scripts/ride_it_exit.py`, `scripts/position_manager.py`, `scripts/hermes_constants.py`

---

## VERDICT: ISSUES FOUND (not a blocker — ship with follow-up)

The core fixes (ATR off-by-one, phase-1 SL widen, PROFIT_MONSTER_BYPASS) are correct and verified with live tests. Fix 4 (UNIVERSAL_MAX_HOLD exemption) is **incomplete** — its `_is_ride_it` detection misses underscore-variant and mover signals that `_match_exit_config` maps to ride_it. This gap affects signals that exist in production history (e.g., `volume_breakout_long`, `mover`). The 2 currently open `trend-ride+` positions are correctly exempted (hyphenated variant), so the gap does not affect live trades right now.

---

## Fix-by-Fix Verdicts

### Fix 1: ATR Off-by-One — **PASS** ✅

**Evidence:**

All 3 locations verified — `rows.reverse()` is correctly placed AFTER `fetchall()` and BEFORE the TR loop:

| Location | File:Line | Verified |
|----------|-----------|----------|
| `ride_it_exit.py` `_get_atr()` | line 63 | `rows.reverse()` at line 63, TR loop at 68-72 |
| `position_manager.py` sl_zones ATR | line 2682 | `_atr_rows_slz.reverse()` at 2682, TR loop at 2683-2687 |
| `position_manager.py` pump_exit ATR | line 2793 | `_atr_rows.reverse()` at 2793, TR loop at 2794-2798 |

**Live ATR test** (`python3 -c "from ride_it_exit import _get_atr; print(_get_atr('BTC', 14))"`):

| Token | func_atr | manual_atr (ASC) | match | buggy_atr (DESC) | inflation | ATR% |
|-------|----------|-------------------|-------|-------------------|-----------|------|
| BTC | 347.214286 | 347.214286 | ✅ | 516.571429 | +48.8% | 0.405% |
| ETH | 13.125714 | 13.125714 | ✅ | 15.478571 | +17.9% | 0.483% |
| AVAX | 0.100071 | 0.100071 | ✅ | 0.106143 | +6.1% | 0.897% |
| SOL | 0.582500 | 0.582500 | ✅ | 0.796071 | +36.7% | 0.482% |
| DOGE | 0.000623 | 0.000623 | ✅ | 0.000922 | +48.0% | 0.654% |

- Function ATR matches manual ASC computation **exactly** for all tokens.
- Buggy version inflated ATR 6-49% for these tokens (audit claimed 14-103%; inflation varies by token/volatility).
- ATR% values all in reasonable 0.4-0.9% range.
- PEPE returns 0 (no 1h candle data) — graceful fallback, no crash.
- **No connection leaks**: all 3 locations close the SQLite connection BEFORE computing ATR from already-fetched rows.

**Regression impact:** The ATR fix affects ALL signals using ATR in position_manager.py:
- **sl_zones** (`zone_aware_exit_check`): ATR is now smaller (correct) → `distance_atr = |zone_center - price| / atr` is LARGER → fewer positions within 1 ATR of a death zone → fewer `tighten_trail` triggers. This is a **correctness improvement** (old inflated ATR made zones appear closer than they were) but reduces zone-based protection for all signals. Acceptable — the old behavior was wrong.
- **pump_exit**: ATR is now smaller → `trail_distance = atr * PUMP_EXIT_TRAIL_MULT` is smaller → tighter trail for pump-chain+ trades. This is an **improvement** (correct trail distance).

---

### Fix 2: Phase-1 SL Widen — **PASS** ✅

**Evidence:** `ride_it_exit.py` lines 354-362

```python
if direction == 'LONG':
    phase1_sl = entry_price - sl_distance
    should_update = phase1_sl > current_sl * 1.0005 or phase1_sl < current_sl * 0.9995
else:
    phase1_sl = entry_price + sl_distance
    should_update = phase1_sl < current_sl * 0.9995 or phase1_sl > current_sl * 1.0005
```

**Deadzone math verified:**
- The 0.05% deadzone is correct: `1.0005` and `0.9995` are symmetric multipliers around 1.0.
- LONG path: allows both tightening (`phase1_sl > current_sl * 1.0005`) AND widening (`phase1_sl < current_sl * 0.9995`). Correct for phase-1 wide-SL design.
- SHORT path: same logic, both directions allowed. Correct.

**Edge cases tested:**

| Edge Case | Behavior | Safe? |
|-----------|----------|-------|
| `current_sl = 0` | Both bounds = 0. `phase1_sl > 0` → True → update. Correct (sets SL when none exists). | ✅ |
| Penny coin (tiny entry_price) | `sl_distance = max(atr*2.0, entry*0.013)`, capped at `entry*0.025`. All relative to entry_price. Deadzone multipliers are relative. No division by entry_price. | ✅ |
| `entry_price = 0` | Function returns HOLD early at line 300 (`if not entry_price`). | ✅ |
| Negative SL (data error) | Deadzone math still works (multiplication is symmetric). Not reachable in practice. | ✅ |

---

### Fix 3: PROFIT_MONSTER_BYPASS — **PASS** ✅

**Evidence:** `hermes_constants.py` line 1599

```python
'trend-ride', 'trend_ride_long',  # ride_it exit — exempt from PM trail/cut_loser
```

- Both entries present in `PROFIT_MONSTER_BYPASS_SIGNALS` tuple. ✅
- **cut_loser.py** (line 66-68): uses `signal LIKE '%{s}%'` — substring matching. `'trend-ride'` becomes `LIKE '%trend-ride%'`, matches `trend-ride+`, `trend-ride`, `trend-ride-long`, etc. ✅
- **profit_monster.py** (line 86-89): same list, same `LIKE '%{s}%'` matching. ✅
- **position_manager.py**: does NOT reference `PROFIT_MONSTER_BYPASS_SIGNALS` — PM trail logic lives in profit_monster.py, not position_manager.py. The in-line `should_cut_loser` (line 349) is a different mechanism (SL price breach check) and correctly does NOT check the bypass list — ride_it signals should still close when their SL is actually breached. ✅
- `'volume-breakout'` was already in the tuple (line 1598), so volume-breakout signals already bypassed PM trail/cut_loser before this commit. ✅

---

### Fix 4: UNIVERSAL_MAX_HOLD Exemption — **WARN** ⚠️ (incomplete)

**Evidence:** `position_manager.py` lines 3286-3288

```python
_pos_signal = str(pos.get('signal', '') or '')
_is_ride_it = 'ride_it' in _pos_signal or 'trend-ride' in _pos_signal or 'volume-breakout' in _pos_signal
if UNIVERSAL_MAX_HOLD_MINUTES > 0 and open_time and not _is_ride_it:
```

**Detection test results:**

| Signal String | `_match_exit_config` | `_is_ride_it` | Gap? |
|---------------|---------------------|---------------|------|
| `trend-ride+` | ride_it | True | no ✅ |
| `volume-breakout+` | ride_it | True | no ✅ |
| `volume-breakout-long+` | ride_it | True | no ✅ |
| `volume-breakout-` | ride_it | True | no ✅ |
| `volume_breakout+` | ride_it | **False** | **YES ⚠️** |
| `volume_breakout-` | ride_it | **False** | **YES ⚠️** |
| `volume_breakout` | ride_it | **False** | **YES ⚠️** |
| `volume_breakout_long` | ride_it | **False** | **YES ⚠️** |
| `mover-` | ride_it | **False** | **YES ⚠️** |
| `mover` | ride_it | **False** | **YES ⚠️** |
| `mover+` | None | False | no ✅ (removed from ride_it) |
| `trend_ride_long` | ride_it | **False** | **YES ⚠️** |
| `None` / `''` | — | False | safe ✅ (no crash) |

**Production impact** (from PostgreSQL queries):

The gap signals DO exist in trade history:
- `rs_s,volume_breakout_long` — 4 trades
- `rs_s,rs_s,volume_breakout_long` — 2 trades
- `accel_300_v2_long,volume_breakout_long` — 2 trades
- `volume_breakout` — 1 trade
- `mover` — multiple historical trades
- `mover-` — some historical trades

These signals get ride_it exit management (via `_match_exit_config` which matches `volume_breakout_long` → `ride_it` via the `volume_breakout_` prefix, and `mover`/`mover-` → `ride_it` via exact keys), but are **NOT exempted** from the 8h UNIVERSAL_MAX_HOLD force-close. The ride_it 24h max hold never applies to them.

**Currently open positions:** 2x `trend-ride+` (hyphenated) — these ARE correctly exempted. The gap does not affect live trades right now.

**Root cause:** The `_is_ride_it` check uses hyphenated substrings (`'trend-ride'`, `'volume-breakout'`) but `_match_exit_config` also matches underscore variants (`volume_breakout_long`, `volume_breakout`) and bare `mover`/`mover-` via the config keys. The two detection methods are inconsistent.

**Severity: MEDIUM-HIGH** — the gap re-introduces the exact bug Fix 4 was supposed to solve, just for a subset of ride_it-mapped signals. Not a blocker because:
1. No underscore-variant or mover ride_it trades are currently open.
2. The hyphenated variants (which are the primary ride_it signals: `trend-ride+`, `volume-breakout+`, `volume-breakout-long+`) ARE correctly exempted.
3. The fix doesn't introduce new bugs — it just doesn't cover all cases.

**Recommended fix:** Align `_is_ride_it` with `_match_exit_config`:
```python
_is_ride_it = (
    'ride_it' in _pos_signal
    or 'trend-ride' in _pos_signal or 'trend_ride' in _pos_signal
    or 'volume-breakout' in _pos_signal or 'volume_breakout' in _pos_signal
    or 'mover' in _pos_signal  # mover, mover-, mover_ — but NOT mover+
)
```
Or better yet, call `_match_exit_config` directly to check if any part maps to `'ride_it'`.

---

### Fix 5: SIGNAL_EXIT_CONFIG Changes — **PASS** ✅ (with minor pre-existing gaps)

**Evidence:** `hermes_constants.py` lines 1659-1673

| Change | Verified | Evidence |
|--------|----------|----------|
| `'volume-breakout-long+'` → `ride_it` | ✅ | Exact key match in `_match_exit_config`. Live test confirms mapping. |
| `'mover+'` removed from ride_it | ✅ | Now maps to `None` (default exit path / PM trail manages). Live test confirms. |
| `'mover-'` still on ride_it | ✅ | Intentional per commit message ("Keep mover- on ride_it"). |
| `'mover'` bare still on ride_it | ✅ | Intentional. |
| `'volume-breakout+'` still maps to ride_it | ✅ | Live test confirms. |
| `'volume_breakout+'` still maps to ride_it | ✅ | Underscore variant, matched via `volume_breakout_` prefix. |

**`_match_exit_config` rev-2 behavior verified:**
- `'volume-breakout-long+'` → exact key match → `ride_it` ✅
- `'volume-breakout+'` → exact key match → `ride_it` ✅
- `'volume_breakout_long'` → prefix match `volume_breakout_` → `ride_it` ✅
- `'mover+'` → no exact match, no `-vN` suffix, no prefix match → `None` ✅

**Minor pre-existing gaps (NOT introduced by this commit):**
- `'volume-breakout-short-'` maps to `None` — no SHORT variant configured. 1 trade in history (`rs-r69,volume-breakout-short-`). LOW severity.
- `'trend-ride-'` maps to `None` — no SHORT variant configured. No trades in history. LOW severity.

---

## Integration Checks

| Check | Result |
|-------|--------|
| Syntax compile (all 3 files) | ✅ PASS — `ast.parse` clean |
| Import `ride_it_exit` | ✅ PASS |
| Import `hermes_constants` | ✅ PASS |
| Import `position_manager` | ✅ PASS (syntax; full import requires runtime deps) |
| Constants loaded | ✅ `RIDE_IT_ENABLED=True`, `RIDE_IT_MAX_HOLD_HOURS=24`, `UNIVERSAL_MAX_HOLD_MINUTES=480` |
| Connection leaks (modified paths) | ✅ None — all SQLite/PostgreSQL connections closed before computation |
| No crash on missing data | ✅ PEPE ATR returns 0 gracefully; `signal=None` handled by `str(... or '')` |

---

## Regression Risk Assessment

| Change | Affected Signals | Risk | Assessment |
|--------|-----------------|------|------------|
| ATR fix (sl_zones) | ALL signals | MEDIUM | ATR now smaller → fewer zone-tighten triggers. Correctness improvement, but reduces profit protection near SL zones for all trades. Acceptable. |
| ATR fix (pump_exit) | pump-chain+ | LOW | Tighter trail = better profit protection. Improvement. |
| ATR fix (ride_it) | ride_it signals | LOW | Correct ATR → correct phase-1 SL width. The fix. |
| PROFIT_MONSTER_BYPASS additions | trend-ride, trend_ride_long | LOW | These signals now bypass cut_loser.py and profit_monster.py PM trail. Intended — ride_it manages them. |
| UNIVERSAL_MAX_HOLD exemption | hyphenated ride_it signals | LOW | Correctly exempts `trend-ride+`, `volume-breakout+`, `volume-breakout-long+`. |
| UNIVERSAL_MAX_HOLD exemption gap | underscore/mover ride_it signals | MEDIUM | Not exempted — still force-closed at 8h. See Fix 4 WARN. |
| `mover+` removed from ride_it | mover+ trades | LOW | Now managed by PM trail + default ATR SL/TP. Intended per audit. |
| `volume-breakout-long+` added to ride_it | volume-breakout-long+ trades | LOW | Now managed by ride_it instead of unmanaged. Intended. |

**Non-ride_it signals (pump-chain+, bb-squeeze+, etc.):** Their exit behavior is unchanged except for the sl_zones ATR fix, which makes zone-proximity checks more accurate (tighter). This is a correctness improvement, not a regression.

---

## Bugs Found (by severity)

| # | Severity | File:Line | Description |
|---|----------|-----------|-------------|
| 1 | **MEDIUM-HIGH** | `position_manager.py:3287` | `_is_ride_it` detection incomplete — misses underscore variants (`volume_breakout_long`, `volume_breakout`, `volume_breakout_short_`) and mover signals (`mover`, `mover-`) that `_match_exit_config` maps to ride_it. These signals get ride_it exit management but are NOT exempted from 8h UNIVERSAL_MAX_HOLD. The exact bug Fix 4 was supposed to solve persists for these variants. |
| 2 | LOW | `hermes_constants.py:1659-1673` | `volume-breakout-short-` has no exit config mapping (pre-existing, not from this commit). 1 trade in history. |
| 3 | LOW | `hermes_constants.py:1659-1673` | `trend-ride-` has no exit config mapping (no SHORT variant configured). No trades in history. |

---

## Recommendations

1. **Fix Bug #1 before next deploy:** Align `_is_ride_it` with `_match_exit_config` by adding underscore variants (`'volume_breakout'`, `'trend_ride'`) and mover signals to the substring check. Best approach: call `_match_exit_config` directly instead of duplicating detection logic.

2. **Monitor sl_zones behavior:** The ATR fix reduces zone-tighten triggers for all signals. Watch trade performance for the next week — if zones were providing meaningful profit protection, the corrected ATR may expose trades to larger drawdowns near death zones. This is expected and correct, but worth tracking.

3. **Add `volume-breakout-short-` to SIGNAL_EXIT_CONFIG** (LOW priority) — maps to ride_it or a SHORT-appropriate exit config.

4. **Consider adding `trend-ride-`** to SIGNAL_EXIT_CONFIG if SHORT trend-ride signals are planned.

5. **No blocker for ship:** The 2 currently open `trend-ride+` positions are correctly exempted from universal hold and will be managed by ride_it. The fixes improve ride_it exit management for the primary hyphenated signal variants. The underscore/mover gap should be closed in a follow-up commit.
