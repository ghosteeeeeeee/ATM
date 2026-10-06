# Bug Hunter Verdict — Fix 3: LLM Context Gate BTC Continuum + Live RSI

**Commit:** `45ed8064` — "CEO ships Fix 3 — LLM context gate now sees BTC continuum + live RSI"
**Auditor:** bug_hunter (independent verification)
**Date:** 2026-10-05
**File:** `scripts/decider_run.py` (+48/−5)

---

## VERDICT: ISSUES FOUND (safe to keep running, but does NOT fix the reported incident)

The change is syntactically sound, exception-safe under current DB conditions, and does not
regress any non-LLM path. It is not a shipping blocker in the "will lose money today" sense.
However, **the core delivery mechanism is broken for the exact code paths that produced the
2026-10-05 incidents**: the BTC continuum context never reaches the LLM prompt on those paths,
so the LLM would still NAY the same conf=99% BTC SHORT. One latent crash bug and one cache
design gap were also found. Fix the delivery (one-line change, see Recommendations) before
trusting this as the fix for the incident.

| # | Check | Result |
|---|-------|--------|
| 1 | Syntax & import integrity | **PASS** |
| 2 | Database query correctness | **PASS** (1 WARN, 1 latent bug) |
| 3 | Staleness guard | **PASS** |
| 4 | Prompt construction edge cases | **PASS** (1 FAIL — NULL score crash) |
| 5 | Logic correctness | **PASS** (2 WARNs — design) |
| 6 | Integration (market dict flow, cache, subprocess) | **FAIL** (HIGH — dict dropped on incident paths) |
| 7 | Regression | **PASS** (1 sideways HIGH — pre-existing dead code) |
| 8 | Live data test | **MIXED** (logic correct; delivery gap confirmed) |

---

## 1. Syntax and Import Integrity — PASS

- `python3 -c "import ast; ast.parse(...)"` → **SYNTAX OK**.
- `_ctx_gate_get_btc_continuum` defined at **line 920**, called at line 950 inside
  `_ctx_gate_get_market_context` (line 946). Defined before use. (Python resolves at call
  time anyway, but ordering is correct.)
- `_ctx_gate_get_rsi` exists at **line 863**, called at **line 1279** inside `llm_context_gate`
  — after the `CONTEXT_GATE_LLM_ENABLED` check (1263) and the cache check (1271), so it runs
  only on cache misses. Correct.
- Module scope: line 9 `import sys, subprocess, sqlite3, time, os, json, ...` and line 15
  `from paths import *` (provides `HERMES_DATA`). The function's local `import os as _bc_os`
  / `import time as _bc_time` are **safe** — aliased names cannot shadow anything, and the
  function is self-contained. `sqlite3` and `HERMES_DATA` resolve from module globals.
  Verified by executing the actual extracted function live (no NameError).

## 2. Database Query Correctness — PASS (1 WARN, 1 latent bug)

- Schema confirmed via `sqlite3 data/continuum.db ".schema continuum_states"` — all queried
  columns exist (`market_phase`, `linreg_direction`, `ema300_position`, `state_score`,
  `zscore_tier`, `ts`). 123,775 BTC rows present. Live query returned valid data.
- **WARN (LOW):** the query has **no `timeframe` filter**. Schema is
  `UNIQUE(token, timeframe, ts)` — only `timeframe='1m'` rows exist for BTC today
  (verified: `SELECT DISTINCT timeframe ... WHERE token='BTC'` → only `1m`), so the latest-row
  lookup is correct now. If other timeframes are ever written, `ORDER BY ts DESC LIMIT 1`
  could silently pick a 1h row. Add `AND timeframe='1m'` defensively.
- Empty table → `if not _bc_row: return None` → prompt shows "N/A" → safe (DEFAULT NAY).
- `ts` NULL → `_bc_ts = _bc_row[5] or 0` → `time() - 0 > 600` → True → returns None → safe.
  Negative ts → same (time − negative is large) → None. Future ts (clock skew) → passes as
  fresh — benign.
- `market_phase`/`linreg_direction`/`ema300_position` NULL → `None in (...)` is False →
  `bearish=False`, dict returned with None values → prompt prints "None" for those fields
  (ugly, but no crash).
- **FAIL (MEDIUM, latent): `state_score` NULL → TypeError in prompt construction.** The prompt
  line uses `score={_prompt_cont.get('score',0):.1f}` — `.get('score',0)` only defaults when
  the **key is missing**; when the DB value is NULL the key exists with value `None`, and
  `f"{None:.1f}"` raises `TypeError: unsupported format string passed to NoneType.__format__`.
  **Reproduced live** (see §4, Path D). Currently **0 NULLs** across all 123,775 BTC rows, so
  this is latent — but see §4 for why it is not contained.
- `zscore_tier` NULL → `f"z={...}"` with no format spec → prints "z=None". Cosmetic only.

## 3. Staleness Guard — PASS

- Guard: `_bc_ts = _bc_row[5] or 0; if _bc_time.time() - _bc_ts > 600: return None`.
  Evaluated **before** the bearish logic — correct order.
- ts=0 → `time() - 0 > 600` → True → None. ✓ (as the task expected)
- ts=None → `or 0` → same as ts=0 → None. ✓
- ts negative → `time() - (-x) > 600` → True → None. ✓
- No recent BTC data → None → prompt "N/A" → **fails safe**: with no bear structure shown,
  the new DEFAULT reads "uncertain otherwise → NAY". The stale path cannot produce a GO.
- Live check: latest BTC row was **40s old** at test time; guard passes. Data cadence is
  ~30s, so the 600s window covers ~20 rows of slack.

## 4. Prompt Construction Edge Cases — PASS (1 FAIL)

All simulated against the **actual code logic** (extracted function + exact f-string lines):

- `_prompt_cont` is None → `_cont_str = 'N/A'`. ✓ (Path B below)
- `_prompt_rsi` is None → `_rsi_str = 'N/A'` (line 1288 ternary). ✓
- `market` dict lacks `'btc_continuum'` key → `.get('btc_continuum')` → None → "N/A". ✓
- `market == {}` (string-AMBIGUOUS path, see §6) → same → "N/A". ✓
- `_ctx_gate_get_rsi` for any token string: tested `NONEXISTENT_TOKEN_XYZ` and `''` → both
  return `None`, no exception (rsi_utils returns None on insufficient candles; inline
  fallback has try/except → None). ✓

**End-to-end prompt simulation (live data):**

```
LIVE continuum: {'phase': 'CALM', 'linreg': 'LEAN_BULL', 'ema': 'BELOW',
                 'score': 35.14, 'z': 'POS', 'bearish': False}
LIVE BTC RSI:  61.49

PATH A: dict AMBIGUOUS (line 1246 fall-through) — market present
  Live RSI: 61.5
  BTC Continuum: CALM+LEAN_BULL+BELOW score=35.1 z=POS

PATH B: string AMBIGUOUS (speed<20 / RSI filter / momentum) — market DROPPED
  Live RSI: 61.5
  BTC Continuum: N/A                      ← fix invisible to LLM on this path

PATH C: dump-day dict path (incident conditions + fix)
  Live RSI: 45.0
  BTC Continuum: RECOVERY+LEAN_BEAR+BELOW score=12.3 z=NEG [BEAR STRUCTURE]

PATH D: score=None (latent crash)
  CRASH TypeError: unsupported format string passed to NoneType.__format__
```

**FAIL (MEDIUM): the score=None TypeError is not contained.** The prompt-building code
(lines 1279–1288) runs **outside** any try/except — the try block starts at line 1379 (around
the subprocess call). AST analysis of `run()` confirms **no try block covers line 4137**
(the `context_gate(...)` call), and `__main__` (line 4638) has no try either. So the exception
propagates: `llm_context_gate` → `context_gate` → `run()` loop → **process crash**.
`run_pipeline.py` then logs `decider_run: FAILED` and **no signals execute that cycle**
(fail-closed for that cycle, but the decider is down). A single NULL-score row is replaced
within ~30s, so today this would be a one-cycle blip; intermittent NULLs from the continuum
writer would cause intermittent decider crashes. Sanitize at source (see Recommendations).

## 5. Logic Correctness — PASS (2 design WARNs)

**Bearish condition** `_phase in ('DECLINING','CALM','RECOVERY') and _linreg in ('LEAN_BEAR','BEAR') and _ema == 'BELOW'`:
- Correct all-3-agree check per spec. Live-tested against 7 scenarios (dump-day variants →
  True; genuine recovery RECOVERY+LEAN_BULL+ABOVE → False; DECLINING+NEUTRAL+BELOW → False;
  DECLINING+LEAN_BEAR+AT → False). All correct.
- **Consistent with pre-existing Fix 1** inline check (lines 1082–1084): identical condition,
  identical 600s guard. The two copies agree — good, though it is duplicated logic (see §7).

**WARN (MEDIUM): RECOVERY in the phase list — false-positive risk during real recoveries.**
Quantified against live DB (last 24h, token=BTC, 2,879 rows):

| Window | Rows | bearish=True | Rate |
|--------|------|--------------|------|
| 24h    | 2,879 | 704 | **24.5%** |
| 2h     | 240   | 139 | **57.9%** |

Bearish-state breakdown (24h): **RECOVERY = 431 (61% of all bearish states)**, CALM = 198,
DECLINING = 75. `ema300_position` and `linreg_direction` are slow/lagging indicators, so
during a genuine V-bottom recovery the state stays RECOVERY+LEAN_BEAR+BELOW for an extended
period — exactly when shorts are most dangerous (bounce risk). The DEFAULT-GO criteria would
therefore fire for uncertain RSI≥40 shorts during a large fraction of recovery periods.
This matches Fix 1's intent (consistent), but it is a real behavioral exposure. Monitor the
win rate of DEFAULT-GO'd shorts; consider excluding RECOVERY or adding a score gate.

**WARN (MEDIUM): DEFAULT change — "uncertain + bear structure + RSI≥40 → GO" is a significant
widening.** Previously DEFAULT was always NAY. Mitigating factors, all verified:
- `SHORT_RSI_FLOOR = 40` (hermes_constants line 868) already hard-blocks RSI<40 shorts in
  `rule_based_context_gate` (lines 1090–1093) for any path that reaches the floor checks, so
  the LLM DEFAULT only widens the net for shorts with RSI≥40 that passed the rule gate.
- The data cited in hermes_constants supports the band: "RSI 45-55 SHORT = 26T 69.2% WR
  +$1.07 (BEST BAND); RSI <40 SHORT = 72T 27.8% WR −$5.34".
- However, given bear structure is True 24.5% of the time (57.9% in the last 2h), the GO net
  widens materially during bear regimes. The prompt-visibility gap in §6 ironically limits
  the blast radius today (LLM can't see bear structure on most paths → keeps NAYing). Once
  delivery is fixed, this widening becomes fully active — ship the delivery fix together with
  monitoring, not before deciding the DEFAULT policy is acceptable.

**NAY change — "SHORT with live RSI < 40" unconditional:** correct and aligned with data.
It blocks MORE shorts than the old "z < −1.5 AND speed < 40", but SHORT_RSI_FLOOR=40 already
encodes "RSI<40 SHORT = 27.8% WR, losers" (BANANA lesson in AGENTS.md: shorting oversold =
catching a falling knife). It also **backfills a gap**: the SIGNAL_FILTER RSI check
(line 1019–1020) returns AMBIGUOUS for SHORT+RSI<42 **before** the floor checks at 1054+ ever
run, so those shorts historically reached the LLM with no hard floor applied. The new LLM NAY
now blocks them at the LLM layer using live RSI. Net: this is defense-in-depth consistent
with "every dump is a SHORT opportunity" **only for RSI≥40 dumps** — the philosophy's data
backs that. PASS.

**FLIP change** ("SHORT z<−0.7 AND live RSI≥40"): **inert**. FLIP has been disabled since
2026-08-01 (line 1388–1390: LLM FLIP → treated as WARN). No behavioral impact. Note only.

## 6. Integration — FAIL (HIGH: the fix does not reach the LLM on the incident paths)

**Market dict flow (verified by reading the actual call chain):**
1. `context_gate` (line 1584) calls `rule_based_context_gate` at line 1669.
2. `rule_based_context_gate` computes `market = _ctx_gate_get_market_context()` at line 985 —
   which now includes `btc_continuum`. ✓
3. **But** most AMBIGUOUS returns pass a **string** reason, not the dict:
   - line 997: speed < 20 → `"speed 12% < 20% (no wave)"`
   - line 1007: speed < regime-adjusted min (40 for SHORT in NORMAL/HIGH) → string
   - line 1011: momentum < 25 → string
   - line 1018/1020: RSI filter (SHORT signal RSI < 42) → string
   - line 1027/1029: z-chasing → string
   - line 1100: pullback-entry z>0.5 → string
4. Only **line 1201** (stale-price) and **line 1246** (fall-through "Ambiguous — needs LLM")
   return the full ctx dict **with `'market': market`**.
5. In `llm_context_gate` line 1277–1278: `ctx = rule_result if isinstance(rule_result, dict) else {}`
   → `market = ctx.get('market', {})` → **`{}` on every string path** →
   `_prompt_cont = market.get('btc_continuum')` → None → **"BTC Continuum: N/A"**.

**The market dict is computed and then thrown away on the paths that produced the incidents.**
Reconstructed from `logs/pipeline.log` (verified, not assumed):

| Incident | Log evidence | AMBIGUOUS path taken | Market dict? |
|----------|--------------|----------------------|--------------|
| 2026-10-05 15:43:41 | `BTC SHORT conf=99 src=continuum-trend- [spd=12%]`, vol regime=FLAT | line 997: speed 12 < 20 → **string** | **DROPPED** |
| 2026-10-05 16:10:57 | `BTC SHORT conf=99 src=continuum-trend- [spd=21%]`, vol regime=NORMAL | line 1007: speed 21 < 40 (SIGNAL_FILTER_SPEED_MIN, regime NORMAL not NEUTRAL) → **string** | **DROPPED** |

(`spd=` in the EXEC log is `speed_tracker_dr.get_token_speed(...).get('speed_percentile')` at
line 3776–3777 — the **same SpeedTracker source** `_ctx_gate_get_speed` uses at line 964, so
the logged speed is the gate's speed.)

**And the data existed at both incidents** (queried from `data/continuum.db` at the incident
epochs):

| Incident time | Continuum state | bearish (new rule) |
|---------------|-----------------|--------------------|
| 15:43:41 (epoch 1791215021) | RECOVERY + LEAN_BEAR + BELOW, score=17.1, z=NEG | **True** |
| 16:10:57 (epoch 1791216671) | CALM + LEAN_BEAR + BELOW, score=9.7, z=NEG | **True** |

**Conclusion:** at both incidents the bear structure was real, but on the paths those signals
took, the post-fix prompt would still read `BTC Continuum: N/A`. The LLM would see no bear
structure, DEFAULT would resolve to "uncertain otherwise → NAY", and the conf=99% BTC SHORT
would be **killed exactly as before**. Only the live-RSI half of the fix works on these paths
(it is fetched fresh inside `llm_context_gate` at line 1279, independent of the market dict).

**Cache — WARN (MEDIUM):**
- Cache key is `f"{token}:{source}:{direction}"` (line 1266) — **no prompt content or version
  hash**. TTL = 300s (`CONTEXT_GATE_CACHE_TTL`, hermes_constants line 831).
- `/dev/shm/hermes-ctx-gate-cache.json` confirmed **absent** (cleared as the commit claims).
  Ship-time is clean. But any **future** prompt/criteria change will silently reuse stale
  verdicts for up to 5 minutes per token:source:direction unless the file is manually cleared
  again. Include a prompt-version constant in the key.

**Fresh subprocess — PASS:** `run_pipeline.py` line 74 spawns
`subprocess.Popen([sys.executable, f'{SCRIPTS}/{name}.py'])` for `decider_run` every minute.
New code loads each cycle. ✓ (Also confirmed log shows `Running decider_run...` → fresh
process each minute.)

## 7. Regression — PASS (1 sideways HIGH, pre-existing)

- `git diff 45ed8064^..45ed8064 -- scripts/decider_run.py` reviewed in full. Changes confined
  to: (a) new `_ctx_gate_get_btc_continuum`, (b) `_ctx_gate_get_market_context` gains one dict
  key, (c) prompt text/criteria. **No rule-based GO/SKIP logic touched.** Non-LLM decisions
  are unaffected: nothing reads `btc_continuum` outside `llm_context_gate` prompt building.
- `_ctx_gate_get_btc_continuum` exception safety: outer `except Exception: return None` catches
  everything except BaseException subclasses (SystemExit/KeyboardInterrupt) — appropriate for
  a data fetch. Inner `try/finally: _bc_conn.close()` guarantees cursor/connection cleanup
  (AGENTS.md convention satisfied). `sqlite3.connect` failure → caught by outer except. ✓
- **Sideways finding (HIGH, PRE-EXISTING — not introduced by this commit):**
  `_ctx_bearish_override` (computed at lines 1066–1088, set True at 1086) is **DEAD CODE —
  never read**. Grep confirms only assignments, no consumption. The SHORT RSI floor checks
  immediately after it (lines 1090–1093) return SKIP **unconditionally**:
  ```python
  if _live_rsi_floor is not None and _live_rsi_floor < SHORT_RSI_FLOOR:
      return ('SKIP', ...)   # _ctx_bearish_override NEVER consulted
  ```
  The "Fix 1 bearish override for RSI floors" therefore **does not actually override
  anything** — bear structure does not relax the SHORT_RSI_FLOOR=40 block in the rule gate.
  The inline comment at 1052–1053 says the HARD floor has no override (intentional), but the
  soft FLOOR at 1090 also applies no override despite the code computing one. Either Fix 1 is
  broken or the override was silently disabled — **needs CEO confirmation**. Dead code that
  looks like a live safety mechanism is itself a hazard.

## 8. Live Data Test — MIXED

- **Current BTC continuum (live, actual function executed):**
  `{'phase': 'CALM', 'linreg': 'LEAN_BULL', 'ema': 'BELOW', 'score': 35.1, 'z': 'POS', 'bearish': False}`.
  Today's dump-day claim (score 10–30, LEAN_BEAR, BELOW) **would** trigger `bearish=True`
  (tested: DECLINING+LEAN_BEAR+BELOW → True; DECLINING+BEAR+BELOW → True). Note the market has
  since shifted: current linreg is LEAN_BULL and ema is BELOW → bearish=False right now.
  Continuum state changes every ~30s; do not treat any single snapshot as "today's state".
- **INJ/FIL pump-chain shorts:** task cites RSI=0 / RSI=1.9 at signal time. Live values now:
  INJ=90.6, FIL=77.1 (market moved). Cannot replay the historical RSI states; verified by
  logic instead: RSI<40 shorts are blocked at the **rule floor** on dict paths
  (SHORT_RSI_FLOOR=40, lines 1090–1093) and at the **LLM NAY** on string paths (new criterion,
  live RSI shown in prompt header). Either way **blocked** — the LLM should not (and now
  cannot easily) approve RSI<40 shorts even in bear structure. The bear override belongs to
  Fix 1's floor logic, not Fix 3's LLM criteria. **Intent satisfied.**
  Bonus live check: HBAR RSI=23.5 < SHORT_RSI_HARD_FLOOR=25 — would be hard-blocked at the
  rule gate today. ✓
- **BTC SHORT conf=99%, RSI~45 + bear structure → GO from DEFAULT?**
  - On the **dict fall-through path** (line 1246): prompt shows
    `RECOVERY+LEAN_BEAR+BELOW ... [BEAR STRUCTURE]` + `Live RSI: 45.0` → DEFAULT criteria
    "uncertain + bear + RSI≥40 → GO" applies → LLM would plausibly GO. **Works.**
  - On the **string paths the actual incidents took** (speed<20 / speed<40 for SHORT):
    prompt shows `BTC Continuum: N/A` → DEFAULT resolves to NAY → **still killed.**
  - Post-commit log check (17:53→18:08): no LLM gate decisions occurred — later gates
    (SHORT-CONTINUUM, SHORT-BB-DEAD-ZONE2, BTC-CHOP-GATE) blocked signals first. **The new
    prompt has not yet been exercised live.**

---

## Bugs Found

| ID | Severity | Description |
|----|----------|-------------|
| F3-1 | **HIGH** | BTC continuum never reaches the LLM on the incident paths. `rule_based_context_gate` returns string AMBIGUOUS reasons (speed<20 at line 997; speed<40 SHORT at line 1007; momentum/RSI/z filters at 1011/1020/1029) and `llm_context_gate` discards non-dict rule results (`ctx = {}`). Both 2026-10-05 incidents took these paths (spd=12% and spd=21%<40, regime NORMAL) while the continuum WAS bearish (RECOVERY/CALM + LEAN_BEAR + BELOW). The fix does not fix the reported bug. |
| F3-2 | **MEDIUM** | Latent crash: `state_score` NULL in continuum_states → `f"{score:.1f}"` TypeError in prompt building (line 1284), which runs outside try/except. AST-verified: no try covers the `context_gate` call (line 4137) or `__main__` → decider process crash → zero executions that cycle. 0 NULLs currently in 123,775 rows. |
| F3-3 | **MEDIUM** | LLM cache key `token:source:direction` has no prompt/version hash (TTL 300s). Future prompt changes silently serve stale verdicts for up to 5 min per key unless `/dev/shm/hermes-ctx-gate-cache.json` is manually cleared again. |
| F3-4 | **WARN (MEDIUM)** | RECOVERY+LEAN_BEAR+BELOW fires bearish=True for 61% of bearish states in 24h (57.9% of all rows in last 2h). Lagging ema/linreg keep bear structure "true" during genuine recoveries → DEFAULT GO for uncertain shorts at bounce time. Design exposure, needs monitoring. |
| F3-5 | **WARN (LOW)** | Continuum query lacks `AND timeframe='1m'`; only 1m rows exist today, but other TFs would silently break latest-row selection. |
| SIDE-1 | **HIGH (pre-existing, not this commit)** | `_ctx_bearish_override` (lines 1066–1088) computed but never read — Fix 1's bearish RSI-floor override is dead code. Floor checks at 1090–1093 are unconditional. Confirm intent with CEO; either wire it in or delete it. |

## Recommendations (ordered)

1. **Fix delivery (F3-1) — one line.** In `llm_context_gate`, fetch the continuum directly
   instead of depending on the rule-gate dict, mirroring how RSI is already fetched:
   ```python
   _prompt_cont = market.get('btc_continuum') or _ctx_gate_get_btc_continuum()
   ```
   This makes the fix work on **every** AMBIGUOUS path (string and dict), including both
   incident paths. Alternative: convert string AMBIGUOUS returns to ctx dicts carrying
   `'market': market` — but the direct fetch is smaller, and matches the existing RSI pattern.
2. **Crash-proof the prompt (F3-2).** Sanitize at source in `_ctx_gate_get_btc_continuum`:
   `'score': _score or 0` (and `'z': _z if _z is not None else '?'`), and/or guard the format:
   `_sc = _prompt_cont.get('score'); _cont_str += f" score={_sc:.1f}" if _sc is not None else " score=?"`.
3. **Version the cache key (F3-3).** Add a `_CTX_PROMPT_VERSION = 'v2026-10-05-fix3'` constant
   and key on `f"{token}:{source}:{direction}:{_CTX_PROMPT_VERSION}"`; bump on every prompt edit.
   Keep clearing `/dev/shm/hermes-ctx-gate-cache.json` after prompt deploys until then.
4. **Monitor DEFAULT-GO'd shorts (F3-4)** during RECOVERY-phase bear structure for at least
   2 weeks; if WR in that cohort drops below ~50%, exclude RECOVERY from the phase list or add
   a `state_score` ceiling. Do this **together with** recommendation 1, not after — the
   delivery fix activates the widening.
5. **Add `AND timeframe='1m'`** to the continuum query (F3-5).
6. **Resolve SIDE-1 with the CEO:** is Fix 1's bearish RSI-floor override intentionally off?
   If it should be live, line 1090–1093 must consult `_ctx_bearish_override`; if not, delete
   the dead block so it stops masquerading as a safety mechanism.
7. **Note for the record:** the FLIP-criteria edit is inert (FLIP disabled since 2026-08-01);
   the GO/NAY/DEFAULT edits are live. Post-commit logs show no LLM gate decision yet — the
   first real exercise of the new prompt will be observable in `logs/pipeline.log` under
   `[CTX-GATE]`.

## Method / Evidence

- All checks executed, not inferred: `ast.parse`, live execution of the extracted
  `_ctx_gate_get_btc_continuum` / `_ctx_gate_get_rsi`, sqlite3 schema + data queries,
  `rsi_utils.compute_rsi_1m` live calls, AST try-block analysis of `run()`, exact
  `git diff 45ed8064^..45ed8064`, and log forensics at log lines 836280–836330 and
  842230–842275 (`logs/pipeline.log`).
- Incident-time continuum states were queried from `data/continuum.db` at the exact incident
  epochs (1791215021 / 1791216671), not estimated.
- The prompt simulations in §4 replicate the exact f-string expressions from lines 1283–1288.
- What could NOT be verified: the historical live RSI values of the INJ/FIL signals at their
  original detection time (market has moved; noted as logic-verified instead).
