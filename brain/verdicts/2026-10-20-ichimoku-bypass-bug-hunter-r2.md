# Bug Hunter Re-verification: ichimoku bypass fixes (06e7bd3b)

## Summary
6 of 7 original findings are genuinely fixed — the kill switch now works end-to-end (proven by simulation: flag flip → fresh import → gate denies), SHORT scope-creep is gone, Decimal alert and atomic write verified. **But the fix introduced a CRITICAL regression: removing `'ichimoku'` from `STANDALONE_BYPASS_SIGNALS` left 5 downstream single-source guards tuple-only, so every single-source ichimoku LONG that passes the new gate is hard-blocked at the hotset-final guard (and pending-approve, preserve-merge, safety-filter, preserve-filter). The CEO-approved LONG loosening is now 100% dead — r1 had "bypass live + kill dead"; r2 has "kill live + bypass dead".** Additionally the kill query now measures an empty cohort (`signal='ichimoku+'` never appears in PG; the executor stores `signal_type` = `ichimoku_long`), so even the working kill machinery can never trigger.

## Verdict: FAIL

The safety mechanisms are fixed and verified, but the feature they protect no longer functions, and the kill criteria watch a cohort that can never fill. Must-fix before this can ship: (a) wire the direction-aware bypass into the 5 downstream single-source guards, (b) fix the kill query cohort.

## Fix Verification

### 1. [CRITICAL, r1] — Auto-revert was a no-op (flag had zero trading-path readers) — **FIXED**
- **Evidence**: `signal_compactor.py:3338-3349` — the new confluence-gate branch does `from hermes_constants import ICHIMOKU_LONG_BYPASS_ENABLED` inside the gate itself. `'ichimoku'` confirmed removed from the tuple (live import: `'ichimoku' in STANDALONE_BYPASS_SIGNALS == False`).
- **Simulation (real code extracted by line range and exec'd)**: flag=True + LONG single `ichimoku+` → `pass_gate=True, msg='ichimoku LONG bypass (CEO 2026-10-20)'`. Flag=False → `pass_gate=False, msg='... (ichimoku bypass disabled)'`.
- **End-to-end revert simulation** (`/tmp/ichimoku_r2_test2_revert.py`, isolated copy + fake psycopg2 returning Decimal bad-WR row): guardrail flipped the constants file, file compiles, fresh process imports flag=False, and the real gate code then denies the bypass. The kill chain now actually kills.
- **Caveat**: what it kills is already dead (see New Finding #1) — the mechanism is correct but currently protects nothing.

### 2. [HIGH, r1] — Kill alert silently dropped (Decimal JSON TypeError) — **FIXED**
- **Evidence**: `vacation_guardrail.py:312-315` — `n_trades/n_wins = int(...)`, `pnl/wr = float(...)`.
- **Simulation**: fake psycopg2 returned `(6, 1, Decimal('-12.34'), Decimal('16.7'))`; patched `write_alert` json-serialized the payload — no TypeError, alert delivered with `{'n_trades': 6, 'wr': 16.7, 'pnl': -12.34}` (all native types).

### 3. [HIGH, r1] — ichimoku SHORT loosened in non-LONG_BIAS regimes (scope creep) — **FIXED**
- **Evidence**: `ICHIMOKU_SHORT_LONG_BIAS_BLOCK` removed (import raises ImportError); gate is direction-aware (`direction.upper() == 'LONG'`).
- **Simulation**: single-source `ichimoku-` SHORT → blocked with flag both True and False. The upstream NEUTRAL SHORT block (line 2943) no longer matches ichimoku either (tuple-only) → SHORT fully blocked.
- **Live log corroboration**: pre-fix leak visible at 16:20:00 (a1b80950 code): `TRX SHORT: {ichimoku-} ... PASS (NEUTRAL-relax: standalone bypass (ichimoku))` — exactly the r1 HIGH #3 scope creep; post-fix code has no such path (verified by simulation).

### 4. [MEDIUM, r1] — Kill query measured wrong cohort — **NOT FIXED (regressed to an empty cohort)**
- **Evidence**: `vacation_guardrail.py:301` uses `signal = 'ichimoku+'`. But the executor stores `_signal_for_trade = signal_type or source` (`decider_run.py:2358`), and `signal_type` for the ichimoku signal is **`'ichimoku_long'`** (`signals/ichimoku_cloud.py:53-56`, `SIGNAL_TYPE_LONG='ichimoku_long'`, `SOURCE_LONG='ichimoku+'`). Live PG: zero rows ever have `signal='ichimoku+'`; `strategy='Hermes-ichimoku+'` count = 0; the only 2 single-source ichimoku trades ever stored (SHORT, 2026-08-31) have bare `signal='ichimoku'`. The r1 recommendation explicitly said the stored single-source value is bare `'ichimoku'` and suggested `signal IN ('ichimoku','ichimoku+')` — the fix narrowed to a value that does not exist in the data.
- **Impact**: `n_trades` stays 0 forever → `n_trades >= 5` never true → the 40% WR kill criterion can never fire on real data. The kill machinery works (proven) but watches an empty table slice.
- **Fix**: `AND signal IN ('ichimoku_long', 'ichimoku', 'ichimoku+')`, or cleanly `AND strategy = 'Hermes-ichimoku+'` (exact single-source source-string; confluence strategies contain commas). Anchor on `open_time >=` bypass activation while at it.

### 5. [MEDIUM, r1] — Shadow log fired pre-gate with wrong reasons — **PARTIALLY FIXED**
- **Fixed**: moved to `signal_compactor.py:3483-3500`, after `signals.append` (3481) and after `CONFLUENCE-GATE-PASS` (3482) — and therefore also after the VOL-GATE-BYPASS check at 3460-3468. Trades that never passed the gate no longer pollute the counterfactual data. Fires only when `'ichimoku' in gate_msg`, i.e. only when the bypass was actually used.
- **Not fixed**: reasons still say "would have been blocked by: vol=HIGH / 4h=NEUTRAL" — r1 asked to relabel these as policy-criteria flags because a trade reaching this point in 4h NEUTRAL already survived the LONG-NEUTRAL block via momentum/continuum exceptions, and there is no vol HIGH/EXTREME hard block for ichimoku anywhere. Labeling unchanged.
- **New nuance**: because of New Finding #1, the shadow now logs "bypass used" for trades that later die at the hotset-final guard — "used" still doesn't mean "fired end-to-end".

### 6. [MEDIUM, r1] — Non-atomic revert write raced compactor import — **FIXED (with a new LOW)**
- **Evidence**: `vacation_guardrail.py:327-331` — temp file + `os.replace` (atomic on same FS). Simulation: revert executed, no `.tmp` leftover, target file replaced intact and compiles.
- **New LOW**: `hermes_constants.py` is mode **0600**; `open(tmp,'w')` creates the temp with 0644 (umask 022) and `os.replace` carries that over — every auto-revert silently widens the CEO-protected file from 0600 to world-readable. Fix: `os.chmod(tmp_path, os.stat(const_path).st_mode)` before replace.

### 7. [LOW, r1] — No try/finally on PG connection — **FIXED**
- **Evidence**: `vacation_guardrail.py:288-310` — `conn = None; cur = None`, inner try/finally closes both with None-guards. Exception before `row` is assigned leaves `row` undefined → NameError → caught by outer except → logged, no bad revert (fail-safe).

## New Findings

### [SEVERITY: CRITICAL — NEW] The bypass is comprehensively dead: 5 downstream single-source guards are still tuple-only
- **Location**: `signal_compactor.py:4906-4939` (HOTSET-FINAL guard), `5018-5034` (PRESERVE-MERGE), `5526-5540` (PENDING-APPROVE), `5701-5715` (SAFETY-FILTER last resort), `6102-6110` (PRESERVE-FILTER).
- **Issue**: All five guards hard-block `CONFLUENCE_REQUIRED=True` single-source entries unless the source is in `STANDALONE_BYPASS_SIGNALS` or is accel-300. Removing `'ichimoku'` from the tuple fixed the r1 scope-creep but stripped these sites of any ichimoku path. The new Step-2 gate (3338) passes the signal; the hotset-final guard then kills it with `🚫 [HOTSET-FINAL-BLOCK] ... src='ichimoku+' (not standalone bypass)`. Grep confirms `ICHIMOKU` appears in the compactor ONLY at 3337-3349 (gate) and 3483-3500 (shadow) — no downstream branch exists.
- **Verified by executing the real code** (lines 4906-4939 extracted and run): `src='ichimoku+'` → BLOCKED; control cases `pump-chain+` and `ai-trader+` → ALLOWED. Live log since the fix shows zero bypass uses (consistent).
- **Impact**: The CEO-approved LONG loosening does nothing — the system behaves as if a1b80950 never shipped. Not a money-leak (fail-safe direction), but the feature, its shadow data collection, and the kill criteria are all inert. Net: r1 "bypass live + kill dead" → r2 "kill live + bypass dead".
- **Fix**: add the same direction-aware check (`'ichimoku' in bare_src and direction LONG and ICHIMOKU_LONG_BYPASS_ENABLED`) to all five guards — ideally extract one shared helper (e.g. `is_standalone_bypass(src, direction)`) so the 11 bypass sites can't drift apart again.

### [SEVERITY: MEDIUM — NEW] Kill query cohort is empty (folded into Finding 4 above — listed here for the fix list)
- Same evidence as #4: `signal='ichimoku+'` exists in no era of PG data; stored value will be `ichimoku_long`.

### [SEVERITY: LOW — NEW] Auto-revert widens file permissions 0600 → 0644
- Temp file created with default umask perms, then `os.replace`'d over the 0600 constants file. chmod the temp to the original mode before replace.

### [SEVERITY: INFO — NEW] raw_signals.json census mislabels bypassed ichimoku LONG
- `signal_compactor.py:2378-2382` — the census labels any <2-part non-tuple signal `blocked_by='CONFLUENCE_GATE'`, independent of the real gate. Once the bypass is revived, single-source ichimoku LONG will show `decision='BLOCKED'` in raw_signals.json while actually passing. Reporting-only drift; mirror the direction-aware check there too.

### [SEVERITY: INFO] r1 leftovers still open (not claimed fixed, noted for tracking)
- `get_regime_4h` fallback still conflates NEUTRAL with missing data (r1 LOW #7) — fail-open for regime blocks on data-gap tokens.
- `n_wins` (vacation_guardrail.py:313) still computed and unused. Substring match `'ichimoku' in bare_source` asymmetry (future rename hazard) persists by design.
- Gate's disabled-flag branch captures the elif chain, so with flag=False an ichimoku LONG single-source also loses the temporal-confluence shadow path — behaviorally acceptable (kill should stop all bypass routes), noted for awareness.
- The auto-revert remains the first unattended writer of the CEO-protected `hermes_constants.py` — AGENTS.md still doesn't document it.

## Verified Working
- `python3 -m py_compile` passes on all three files (hermes_constants, signal_compactor, vacation_guardrail).
- Live constants: `'ichimoku' in STANDALONE_BYPASS_SIGNALS == False`; `ICHIMOKU_LONG_BYPASS_ENABLED == True`; `ICHIMOKU_SHORT_LONG_BIAS_BLOCK` import fails (removed as claimed).
- Gate logic (real code, exec'd): LONG+flag → pass; LONG+flag off → blocked with explicit reason; SHORT → always blocked; confluence (2 types) → passes via `2 unique types`; non-ichimoku single-source → unchanged behavior; 4h NEUTRAL LONG → gate branch still grants (upstream LONG-NEUTRAL block applies its own exceptions first).
- End-to-end auto-revert: fake-Decimal bad WR (6T, 16.7%) → file flipped atomically, alert JSON-serialized with float types, kill log line emitted, no tmp leftover, reverted file compiles, fresh import sees flag False, real gate code denies the bypass.
- Kill guardrail is scheduled: `hermes-vacation-guardrail.timer` active, every 30 min (next trigger 17:27 UTC); `check_ichimoku_bypass_kill()` is first in `main()`.
- Shadow log placement: post-gate, post-vol-gate, post-`signals.append` — counterfactual entries now only for trades that passed the confluence gate.
- Scope: variables `unique_signal_types` (2704), `bare_source` (2706), `direction`, `_regime_4h` (2721), `_vol_regime` (2734) all defined before the new gate/shadow blocks — no NameError risk.
- No other code path grants single-source ichimoku into hotset/decider: all entry points funnel through the five tuple-only guards (verified by reading each).

## Recommendations
1. **Must-fix #1**: wire the direction-aware ichimoku LONG + `ICHIMOKU_LONG_BYPASS_ENABLED` check into all five downstream single-source guards (4906/5018/5526/5701/6102) — via a shared helper — otherwise the feature stays dead.
2. **Must-fix #2**: fix the kill cohort: `AND signal IN ('ichimoku_long','ichimoku','ichimoku+')` (or `strategy = 'Hermes-ichimoku+'`), anchored on open_time ≥ activation.
3. After both fixes: end-to-end test with a paper single-source ichimoku LONG (signal → compactor → hotset_final → decider) before trusting the loosening again — the r1 audit verified the gate, r2 verifies the gate, nobody has yet verified the full path end-to-end.
4. LOW hygiene: preserve file mode in the atomic write; relabel shadow reasons as policy flags; drop unused `n_wins`; mirror the bypass check in the raw_signals census; document the auto-revert writer in AGENTS.md.
5. Restart note: compactor runs a fresh process per minute — new code is picked up automatically; confirm with an ichimoku LONG entry once #1 lands.
