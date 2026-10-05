# Bug Hunter Verdict — `trend_ride_long` signal pre-ship audit

**Date:** 2026-10-05 21:2x UTC
**Auditor:** bug_hunter (delegated subagent)
**Scope:** 5 changed files — `scripts/signals/trend_ride_long.py` (new), `scripts/hermes_constants.py`, `scripts/signals/__init__.py`, `scripts/signal_schema.py`, `scripts/signal_compactor.py`
**Method:** Static review + live execution of every edge case, positive path, and integration path (all tests run in-process against the real modules/DBs; positive-path tests used monkeypatched DB functions and a guarded `add_signal` — **no signal rows or cooldowns were written to any DB**)

---

## VERDICT: ISSUES FOUND

**Safe to commit/ship in the current FROZEN state** — both flags are `False`, verified live: the signal cannot fire, cannot write to the signals DB, and is excluded from `get_registered_signals()`. All 10 audit categories executed. **No CRITICAL or HIGH issues.** One **MEDIUM** bug (`_get_closes` missing `is_closed=1`) **must be fixed before the Oct 6 00:38 enablement** — it does not affect entry conditions, only the optional 1h confidence boost.

---

## Checks

### 1. Source String Consistency — PASS
All four locations match exactly, case-sensitive `'trend-ride+'`:
- `scripts/signals/trend_ride_long.py:58` — `SOURCE_LONG = 'trend-ride+'`
- `scripts/signal_schema.py:953` — `if _comp == 'trend-ride+' and not TREND_RIDE_LONG_PLUS_ENABLED` (add_signal Layer 2)
- `scripts/signal_schema.py:2850` — `if c == 'trend-ride+': return not TREND_RIDE_LONG_PLUS_ENABLED` (is_component_disabled)
- `scripts/signal_compactor.py:590` — `('trend_ride_long', 'trend-ride+'): 1.0`

`_comp` derivation verified: `signal_schema.py:809-810` splits `source` on `,` and loops each component; a lone `source='trend-ride+'` yields `_comp == 'trend-ride+'`. Live test: `add_signal(source='trend-ride+')` → `DEBUG add_signal BLOCKED ... TREND_RIDE_LONG_PLUS_ENABLED=False` → returns `None`. Live test: `is_component_disabled('trend-ride+')` → `True`. Weight lookup live-tested: `signal_compactor._get_source_weight('trend_ride_long', 'trend-ride+')` → `1.0`.

### 2. Flag Consistency — PASS
- `hermes_constants.py:2239-2240` defines `TREND_RIDE_LONG_ENABLED = False`, `TREND_RIDE_LONG_PLUS_ENABLED = False`
- `signals/__init__.py:42` imports **both** flags; registry entry `:495` uses `'TREND_RIDE_LONG_ENABLED'` (string form — resolved live via `_resolve_enabled` → `getattr(hc, ...)` → `False`)
- `signal_schema.py:755` (add_signal import block) and `:2670` (is_component_disabled import block) both import both flags
- `trend_ride_long.py:40-41` imports both flags; uses `TREND_RIDE_LONG_PLUS_ENABLED` in `scan_signals()` at `:251` (Layer 1 kill-switch guard)
- Live: `get_registered_signals()` excludes `trend_ride_long` (flag False); `_resolve_enabled(entry)` → `False`

### 3. DB Connection Safety — PASS
All four DB-touching functions use `conn = None` + `try/except/finally: if conn: conn.close()`:
- `_get_closes` (`:65-81`), `_get_ohlcv` (`:87-103`), `_get_candle_age` (`:109-122`), `scan_signals` (`:230-243`)
- Live-tested extensively (real DB reads + mocked scans); no lock errors, no leaks. `timeout=10`/`timeout=5` consistent with peer signals.

### 4. Edge Cases — PASS (all executed, not inferred)
| Case | Result | Evidence |
|---|---|---|
| Empty closes → `_compute_ema` | `None` | live test |
| Short closes (< period) → `_compute_ema` | `None` | live test |
| All-gains closes → `_compute_rsi` | `100.0` | live test (30 rising pts) |
| All-losses closes → `_compute_rsi` | `0.0` | live test (30 falling pts) |
| `avg_loss == 0` (constant prices) | `100.0` explicitly (`:149-150`) | live test |
| Empty candles → `_compute_avg_volume` | `None` | live test |
| Token with no candles → `detect()` | `None`, no crash (`:166-168` age check → `None`) | live test (`ZZZZNONEXISTENTXYZ`) |
| `scan_signals()` empty token list | `0`, no crash | live test (mocked empty fetchall) |
| Short RSI input (< period+1) | `None` | live test |

### 5. Indicator Math — PASS (one docstring WARN, see Bug #2)
- **EMA** (`:125-133`): `k = 2.0/(period+1)` correct. Verified numerically: step-function EMA20 = 86.489043 matches independent manual computation with k=2/21 to 1e-9. Constant-price input → EMA = price. Seed = `closes[0]` (oldest) with oldest-first input — standard recursive EMA.
- **RSI** (`:136-152`): SMA-of-last-N gains/losses. Verified numerically against manual calc on mixed data (got 72.4409 = manual 72.4409). Formula `100 - 100/(1+rs)` correct. **Docstring says "Wilder's smoothing approximation" but implementation is SMA-of-last-N** — identical to `slow_grind_long.py:123-135` (the closest peer); true Wilder recursion exists in `grind_trend.py:126-140`. Math is internally consistent; comment is wrong (Bug #2).
- **`_get_ohlcv`** (`:84-103`): filters `is_closed = 1` (`:92`) and returns oldest-first (`reversed(rows)` at `:98`). Verified against real DB: last returned candle == latest `is_closed=1` close (ADA: 0.269285 both).
- **`_get_closes`** (`:63-81`): does **NOT** filter `is_closed` — **Bug #1 (MEDIUM)**.

### 6. Control Flow — PASS
- `scan_signals()` uses `continue` (never `return None`) for every guard: staleness `:247-248`, kill-switch `:251-252`, blacklist `:255-256`, cooldown `:259-260`, detect-fail `:263-264`. Live-tested: cooldown-active → 0 signals; blacklisted token → 0 signals; stale price → 0 signals — all without crash.
- `detect()` returns `None` (never a dict with None values) on every failure path — live-tested 8 failure modes.
- Cooldown: `get_cooldown(token, direction='LONG')` at `:259`; `set_cooldown(token, 'LONG', hours=TREND_RIDE_COOLDOWN_HOURS)` at `:279` — live-verified exact args `('FAKETOKEN','LONG',3)`.
- Blacklist: `token.upper() in LONG_BLACKLIST` at `:255` — `LONG_BLACKLIST` is a `set` (104 entries), `in` is O(1). Live-tested skip behavior.

### 7. Hardcoded Numbers — WARN (LOW severity)
Raw numerics in the script:
- `:247` `price_age_minutes(token) > 10` — matches the literal `> 10` pattern used in 10+ peer signals (slow_grind_long, grind_breakout, breakout_long, accel_300 family…); only `pullback_entry.py:295` uses a constant (`PULLBACK_STALENESS_MIN`). Peer-consistent, but convention prefers constants.
- `:211` `conf + 5` (HTF boost), `:215-216` `55 <= rsi <= 65` + `conf + 3` (sweet-spot boost), `:236` `- 3600` (token universe window), `:171` buffer offsets `+10/+5/+5` — genuinely tunable, should live in `hermes_constants.py` per AGENTS.md "No hardcoded constants". LOW because frozen and immaterial to correctness.
- Acceptable: `timeout=10/5` (DB timeouts, universal pattern), `k=2.0/(period+1)` (math constant).

### 8. Integration — PASS (live-verified end-to-end)
- Registry entry `signals/__init__.py:495` exactly: `{'name': 'trend_ride_long', 'enabled': 'TREND_RIDE_LONG_ENABLED', 'run': _trend_ride_long_run}` ✓
- Import block `:181-184` try/except — import succeeded in test (`run fn is None?: False`); `sys.path` resolution matches `slow_grind_long` pattern (signals_runner runs with `scripts/` on path).
- `def run():` with no params (`:283-285`) — `_run_signal` dispatches `fn()` when `co_argcount == 0` ✓
- `add_signal()` call (`:266-276`) live-verified via guarded scan (flags monkeypatched ON, `add_signal` stubbed): all kwargs correct — `token='FAKETOKEN'` (upper), `direction='LONG'`, `signal_type='trend_ride_long'`, `source='trend-ride+'`, `confidence=83`, `value=64.7`, `price=107.68`, `exchange='hyperliquid'`, `timeframe='5m'` ✓
- Positive-path `detect()` live-verified on tuned synthetic uptrend+pullbacks: RSI=64.7 → fires with conf=83 (base 75 + HTF 5 + sweet-spot 3), matches hand-computed expectation exactly.
- Confidence range 75–88 sits inside `CONF_FILTER` bounds [70, 92) — will not be hard-blocked by `_score_signal`'s confidence filter (`hermes_constants.py:1291-1293`, verified live).
- Signals table exists in runtime DB with all needed columns (`token, direction, signal_type, source, confidence, value, price, exchange, timeframe, signal_types, ...`).
- Runs as FAST signal (not in `_SLOW_SIGNALS`) — consistent with `slow_grind_long`; ~105 tokens × ≤5 DB queries/detect, same load profile as peers.

### 9. Layer 2 Coverage — PASS
- `add_signal()` Layer 2 blocks when `TREND_RIDE_LONG_PLUS_ENABLED=False` (`signal_schema.py:952-955`) — **live-verified**: `add_signal(source='trend-ride+', ...)` → blocked + debug log + `None`.
- `is_component_disabled()` returns `True` when flag False (`:2850`) — **live-verified**. Actively consumed: 7 call sites in `signal_compactor.py` (scoring loop `:3099`, preserved-entry guards `:2205/:2334/:4010/:4186/:4614`) and `decider_run.py:3282` — disabled-component stale rows are skipped end-to-end.
- Both use exact string `'trend-ride+'`.
- Edge note (informational): `is_component_disabled('trend-ride')` (bare, no `+`) → `False`. Same pattern as `slow-grind+`. Not reachable — the script writes only via the `SOURCE_LONG` constant.

### 10. Freeze Safety — PASS
- `hermes_constants.py:2239-2240`: `TREND_RIDE_LONG_ENABLED = False`, `TREND_RIDE_LONG_PLUS_ENABLED = False` — freeze comment present ("until Oct 6 00:38").
- `git diff scripts/hermes_constants.py`: **only** the trend_ride block (lines 2232-2252) added — zero other constants touched.
- Live: flags `False` in module; `get_registered_signals()` excludes the signal; `scan_signals()` returns 0; `add_signal` blocks at Layer 2. Triple-redundant kill.

---

## Bugs

### Bug #1 — MEDIUM — `_get_closes()` missing `is_closed=1` filter
**File:** `scripts/signals/trend_ride_long.py:63-81`
The1h closes query (`:69-72`) has no `AND is_closed = 1`. The DB contains unclosed 1h candles (verified live: ADA/AIXBT/ALGO/ALT/APT all have `is_closed=0` rows in `candles_1h` right now). Peer `slow_grind_long.py:72` — the file this signal was clearly modeled on — **does** filter `is_closed = 1` in the identical helper.
**Impact:** the optional higher-TF boost (`:199-211`) computes 1h EMA20/EMA50 including a forming candle. Live measurement: EMA20 diff 0.0003–0.0000, EMA50 diff up to 0.0009 (ADA) between filtered/unfiltered. In fast moves the forming candle can flip the `ema_fast_1h > ema_slow_1h` decision, mis-scoring the +5 confidence boost. **Entry conditions are unaffected** — conditions 1-4 use 5m data via `_get_ohlcv`, which filters correctly. No direct money-loss path; correctness/consistency defect.
**Fix:** add `AND is_closed = 1` to the `WHERE` clause at `:70-72`. One line. **Fix before Oct 6 enablement.**

### Bug #2 — LOW — RSI docstring misstates the algorithm
**File:** `scripts/signals/trend_ride_long.py:137`
Docstring: "Simple RSI (Wilder's smoothing approximation)". Implementation is SMA of the last N gains/losses (no Wilder recursion) — numerically verified and identical to `slow_grind_long.py:123-135`; true Wilder lives in `grind_trend.py:126-140`. Misleading for anyone tuning the RSI zone.
**Fix:** reword to "SMA of last N gains/losses (consistent with slow_grind_long)".

### Bug #3 — LOW — Tunable numbers hardcoded in signal script
**File:** `scripts/signals/trend_ride_long.py:211` (`+5`), `:215` (`55/65`), `:216` (`+3`), `:236` (`3600`), `:171` (`+10/+5/+5` buffers); `:247` (`> 10`, peer-consistent)
AGENTS.md convention: all thresholds/tunables must live in `hermes_constants.py`. These tune the confidence scoring and universe window; when tuning post-enablement they'd require editing the signal file instead of constants.
**Fix:** promote to `TREND_RIDE_HTF_BOOST`, `TREND_RIDE_RSI_SWEET_MIN/MAX`, `TREND_RIDE_SWEET_BOOST`, `TREND_RIDE_UNIVERSE_WINDOW_S`, etc. Non-blocking (LOW) — frozen, and `> 10` matches 10+ peers.

---

## Sideways Findings (unrelated, per See-Something-Say-Something)

1. **INFO** — working tree carries unrelated uncommitted changes alongside this signal: `scripts/candles_lock.py` (new), `price_collector.py`/`paths.py`/`_aggregate_1m.py` (DRIFT-007 HL candle fallback + candles lock), `_candidates/bollinger_squeeze_*.py` (backtest metric refresh). None touch trend_ride constants (verified via diff), but commit the trend_ride files **separately** so the audit trail stays clean.
2. **INFO** — `detect()` docstring (`:164`) says "Return {direction, confidence, value, price}" but the dict also carries `htf_aligned`. Cosmetic.
3. **INFO** — `trend_ride_long` is **not** in `STANDALONE_BYPASS_SIGNALS` (`hermes_constants.py:2699`) and `CONFLUENCE_REQUIRED = True`. A lone trend_ride signal will not trade unless `CONFLUENCE_NEUTRAL_RELAX` applies (NEUTRAL regime) or another signal co-fires. System-wide gate — CEO decision whether it should fire alone.

---

## Recommendations (ordered)

1. **Before Oct 6 00:38 enablement:** add `AND is_closed = 1` to `_get_closes` (`trend_ride_long.py:70-72`). One-line fix; matches peer convention; removes forming-candle distortion from the 1h boost.
2. **Before enablement:** after flipping flags, **restart the pipeline** (AGENTS.md: detection-time vs execution-time condition gap — new code must be loaded).
3. **Verify backtest RSI methodology** (not verifiable from the script alone): the header cites "30d, signal-time RSI from `_signal_metadata`". The codebase contains both SMA-RSI (slow_grind_long, this signal) and Wilder-RSI (grind_trend) implementations; `_signal_metadata.rsi_14` provenance varies by the signal that wrote it. If the 50-70 zone was validated on Wilder RSI, SMA-RSI boundary membership can differ slightly at the edges. Recommend confirming the backtest used an SMA-style RSI matching `_compute_rsi` — or re-validating zone membership. **This audit did not mine `_signal_metadata` provenance; the backtest numbers in the docstring were NOT independently reproduced.**
4. Fix the RSI docstring (Bug #2); promote tunables to constants when convenient (Bug #3).
5. CEO decision: add `'trend-ride+'` to `STANDALONE_BYPASS_SIGNALS` if the signal should fire alone? (Finding #3.)
6. Document the signal in `brain/` per convention — no `brain/*.md` references to trend_ride found.
7. Commit trend_ride files separately from the candles_lock/DRIFT-007 working-tree changes (Sideways Finding #1).

---

## Test Evidence Summary (all executed live)

```
Module import OK; flags False/False confirmed
EMA: empty/short→None; step-function match k=2/(p+1) to 1e-9
RSI: all-gains→100.0; all-losses→0.0; constant→100.0; mixed→72.4409==manual
_avg_volume: empty/short→None; normal→11.0
detect(nonexistent)→None; scan_signals(flags off)→0; scan(empty tokens)→0
is_component_disabled('trend-ride+')→True (live)
add_signal(source='trend-ride+')→BLOCKED+None (live)
registry _resolve_enabled→False; excluded from get_registered_signals() (live)
detect() positive path (synthetic uptrend+pullbacks): fires conf=83 == hand-calc (live)
detect() 8 failure modes → all None (live)
scan_signals() positive path (flags ON, add_signal stubbed): add_signal kwargs
  all correct; cooldown ('FAKETOKEN','LONG',3) correct (live)
guards: cooldown/blacklist/stale-price → 0 signals each (live)
_get_source_weight('trend_ride_long','trend-ride+')→1.0 (live)
py_compile: all 5 files OK
is_closed: _get_ohlcv filters correctly (real DB); _get_closes does NOT (Bug #1)
CONF_FILTER [70,92) vs conf range 75-88 → passes (live)
```

**No DB writes were performed during this audit** — positive-path integration tests used a stubbed `add_signal` and stubbed `set_cooldown`.

*— bug_hunter, 2026-10-05*
