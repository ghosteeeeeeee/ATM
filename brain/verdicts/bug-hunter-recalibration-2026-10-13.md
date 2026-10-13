# Bug Hunter: Recalibration Verification (84a38707)

**Commit:** `84a38707fbc9aaf31287e35e3eeeb32f5178d8f9` — "recalibration: CEO-approved 5 changes"
**Verified:** 2026-10-13 by bug_hunter (all checks executed live, not read-only)

## Verdict: SAFE (ship) — with 3 MEDIUM follow-ups, none blocking

All 5 approved changes are correctly implemented, all 3 files parse and import cleanly, the RR regime exemption was validated live against the production continuum.db (it actively works — BTC LONG R:R 0.42 was released from hard-block to 0.7x penalty during this review), and every documented edge case fails open correctly. The MEDIUM issues are consistency/observability gaps, not crashes or money-losing paths.

## Issues Found

### MEDIUM-1 — `[RR-REGIME-EXEMPT]` log tag is dead code; revert trigger is unmeasurable
`risk_reward_engine.py:1118`. The tag fires only inside `if rr < _rr_effective_block` AND requires `_rr_regime_exempt and rr >= RR_ENGINE_CONF_HARD_BLOCK_RR (0.55)`. But when exempt, `_rr_effective_block = 0.35`, so the branch is only reachable with `rr < 0.35` — which can never satisfy `rr >= 0.55`. Verified numerically across rr ∈ [0.2 … 0.55]: tag never fires.
Worse: regime-exempted trades that are **allowed** (rr 0.35–0.55) return via the graded-multiplier path with a generic reason ("RR PENALTY: ... poor") — no exemption marker anywhere. **Live proof:** `rr_confidence_multiplier('BTC','LONG',83000)` with BTC at LEAN_BULL+ABOVE returned `mult=0.7, 'RR PENALTY: R:R=0.42 grade=D (poor)'` — this trade was released *only* because of the exemption (0.42 < 0.55), yet nothing in the output says so.
**Impact:** The constant's documented revert trigger ("10+ regime-exempted trades lose >$1 in 7d") cannot be tracked from logs. **Fix:** append the tag to the *allow* reason when `_rr_regime_exempt and RR_ENGINE_CONF_HARD_BLOCK_RR_CONFIRMED <= rr < RR_ENGINE_CONF_HARD_BLOCK_RR`, or log a line at exemption time.

### MEDIUM-2 — decider_run.py:3494 still hardcodes the 0.3 penalty floor (diverged from PENALTY_MULT_FLOOR=0.5)
`decider_run.py:3494`: `_exec_mult = max(_pp, 0.3)  # floor at 0.3, same as compactor SCORE-FLOOR`.
The compactor floor was raised to 0.5 via `PENALTY_MULT_FLOOR`, but this second copy — whose comment explicitly claims parity with the compactor — was not. The raw `_pp` stored in `_penalty_product_tracker` is pre-floor, so decider's exec-confidence multiplication still floors at 0.3.
**Impact:** Recalibration #2 is half-applied. A signal with penalty product 0.32 scores as if floored to 0.5 in the compactor but gets exec confidence cut at 0.3 → more `PENALTY-BLOCK` skips at execution than the CEO approved. Direction is conservative (blocks more), so not money-losing — but contradicts the approved change. Also violates the no-hardcoded-constants convention. **Fix:** `from hermes_constants import PENALTY_MULT_FLOOR` and use it here (one line).

### MEDIUM-3 — Pump-chain RSI floors now INVERTED vs general floors
`decider_run.py:1146,1185`: `_floor = SHORT_RSI_*_FLOOR_PUMP_CHAIN if 'pump-chain' in source else SHORT_RSI_*_FLOOR` → pump-chain = 40, everyone else = 35 (both soft and hard). The constants/comments still say "pump-chain gets **lower** floor (40 vs 45)" — after this commit pump-chain gets a **higher** floor than generic. On top of that, `PUMP_CHAIN_SHORT_RSI_MIN = 45` (untouched) still blocks pump-chain SHORT RSI<45 at detection time in signal_compactor:3192 (unless the BTC-bearish bypass applies).
**Net effect:** the RSI 35–45 SHORT band is now open for every signal family **except** pump-chain — yet own-conclusions 2026-10-12 evidence showed pump-chain's 40-45 band was the *profitable* one (19T 63.2%WR +$0.48) while the aggregate 40-45 bleed came from OTHER signals. The recalibration opens the band for the families that bled and keeps it closed for the family that worked. Not a crash/trap — each floor is individually defensible — but the priority inversion deserves an explicit CEO call: either lower the pump-chain floors to match (35/35, and PUMP_CHAIN_SHORT_RSI_MIN 45→40), or confirm the stricter pump-chain stance is intentional. Stale comments at decider_run.py:1144, 1183 should be corrected either way.

### LOW-1 — sqlite3.connect creates an empty continuum.db when the file is missing
Verified: with `continuum.db` absent, `connect()` creates a zero-byte file, then the query raises `no such table` → caught → fail-open to 0.55 (correct behavior). Side effect: a junk zero-byte DB file can appear in HERMES_DATA. Use `mode=ro` URI or check `os.path.exists` first if you want it pristine. Same latent pattern already exists in the pre-existing bearish-override blocks (signal_compactor:4071, decider_run:1163), so it's consistent house style — not new debt.

### LOW-2 — Stale comments (cosmetic)
- `signal_compactor.py:3967`: "(4.0)" — threshold is now 6.0.
- `decider_run.py:1104`: "SHORT_RSI_HARD_FLOOR=45 already hard-SKIPs" — now 35.

### LOW-3 — Extra SQLite connect on every rr_confidence_multiplier call
The continuum query runs for every signal scored, even when `rr >= 0.55` where the result is unused. Measured live: full call ~1–7ms, connection with `timeout=3`. Not a performance concern at current scale; trivial improvement is to check `rr < RR_ENGINE_CONF_HARD_BLOCK_RR` before querying.

### INFO — No timeframe filter in the continuum query
`SELECT ... WHERE token='BTC' ORDER BY ts DESC LIMIT 1` ignores `timeframe`. Verified: BTC currently has only `1m` rows (145k rows total in table), so no ambiguity today. If 5m/1h writers ever land, the newest row across *all* timeframes wins and the regime could flip on write ordering. Consider `AND timeframe='1m'` (or whichever is authoritative) when multi-TF writers appear.

## RR Regime Exemption Code Review

Code: `risk_reward_engine.py:1091–1119` (inside `rr_confidence_multiplier`).

| Check | Result |
|---|---|
| Direction check LONG vs SHORT | ✅ Correct. `direction.upper()` handles lowercase; `elif` chain means a direction can only match one branch. Verified live: LONG+LEAN_BULL+ABOVE → exempt at 0.35; SHORT same row → correctly stays 0.55. |
| linreg_direction matching | ✅ Correct against live enum: DB contains exactly {LEAN_BEAR, NEUTRAL, LEAN_BULL, BEAR, BULL}; tuples ('LEAN_BULL','BULL') / ('LEAN_BEAR','BEAR') match, NEUTRAL correctly excluded. |
| ema300_position matching | ✅ Correct. DB contains {ABOVE, AT, BELOW}; 'AT' correctly exempts nobody (tested). |
| Freshness guard `< 600` | ✅ Correct. Live BTC row age was 6–25s. Synthetic 660s-old row → no exemption. |
| NULL ts | ✅ Safe. `(_rr_ts or 0)` → age ≈ epoch → stale → no exemption (tested). Schema says `ts INTEGER NOT NULL` anyway, so defense-in-depth only. |
| Fail-open on exception | ✅ Correct at both levels. Inner `except Exception: pass` → threshold stays 0.55 (missing DB, missing table, empty table, `direction=None` AttributeError all tested → 0.55). Outer handler (line 1149) returns 1.0 neutral on any other engine error. |
| DB connection closed | ✅ Yes — `try/finally` around the query, closes before any downstream logic. No cursor leak. |
| Interaction with structural blocks | ✅ No conflict. The exemption only relaxes the numeric R:R threshold; line 1120–1121 (`if not result['pass'] and block_reason`) still hard-blocks structural failures regardless of exemption. Grade F also still blocks first (line 1089). |
| Conflict with RR engine's own regime checks | ✅ None. evaluate_rr's regime-min-R:R check ("min=2.0 for NORMAL regime") is shadow-logging only and unaffected. |
| Direction neither LONG nor SHORT | ✅ `'BOTH'` → no branch matches → 0.55. `None` → AttributeError → caught → 0.55. |

**Live end-to-end proof the feature works:** `rr_confidence_multiplier('BTC','LONG',83000.0)` with BTC continuum = LEAN_BULL/ABOVE/fresh → R:R 0.42 returned `0.7 (poor)` instead of hard block `0.0` — without the exemption, 0.42 < 0.55 would have been killed. Elapsed 7ms.

**Consistency note (INFO):** this is now the 4th distinct "BTC bearish/bullish" definition in the codebase — compactor RSI bypass (linreg only, signal_compactor:4084), decider bearish override (market_phase + linreg + ema BELOW, decider_run:1175), pump-chain bypass (linreg only, signal_compactor:3216), and this exemption (linreg + ema, no market_phase). All are loosening/fail-open, so no trap today, but a SHORT could get the compactor RSI bypass yet not the RR exemption (EMA still ABOVE). Consider consolidating into one `is_btc_bullish()/is_btc_bearish()` helper eventually.

## Edge Cases Tested

All executed as live Python against synthetic DBs plus the production DB:

1. **continuum.db missing** → OperationalError caught → fail-open 0.55. ⚠️ Zero-byte file created (LOW-1).
2. **Table exists, zero rows** → `_rr_row` is None → no exemption, 0.55. ✅
3. **ts NULL** → age = epoch → stale → no exemption, 0.55. ✅
4. **ts 11 minutes old** → stale → no exemption, 0.55. ✅
5. **ema300_position = 'AT'** → no exemption, 0.55. ✅
6. **direction = 'BOTH'** → no branch matches, 0.55. ✅
7. **direction = None** → AttributeError caught internally → 0.55. ✅
8. **lowercase 'long'** → `.upper()` → exempt correctly. ✅
9. **SHORT against LEAN_BULL+ABOVE row** → no exemption (direction/regime mismatch respected). ✅
10. **Penalty floor hard-block preservation** — `if _mult_product <= 0.0: final_score = 0.0` still precedes the floor (signal_compactor:2153), so flooring to 0.5 cannot resurrect hard-blocked signals. ✅

## Filter Collision Check

1. **RR exemption vs existing regime checks:** No conflict (see review table). It composes with, not against, the existing bearish-override family. ✅
2. **SHORT_RSI_FLOOR=35 vs SHORT_RSI_HARD_FLOOR_PUMP_CHAIN=40 / FLOOR_PUMP_CHAIN=40:** Collision found — MEDIUM-3 above. Pump-chain is now stricter than generic; also PUMP_CHAIN_SHORT_RSI_MIN=45 still gates detection. Needs a CEO call.
3. **SHORT_RSI_FLOOR=35 vs brain.py / ai_trader_precheck.py:** brain.py:376 and ai_trader_precheck.py:181 read `SHORT_RSI_HARD_FLOOR` directly (now 35, consistent); no pump-chain distinction there — fine.
4. **PENALTY_MULT_FLOOR=0.5 vs decider penalty-gated execution:** Collision found — MEDIUM-2 above (`max(_pp, 0.3)` at decider_run.py:3494).
5. **RETURN_EXHAUSTION_SHORT_ENABLED=False:** Correctly gates emission at scan time (`signals/return_exhaustion_short.py:371–373`) and the registry entry (`signals/__init__.py:513`). No other consumer. Safe. ✅
6. **MAXXED_ATR_PCT_THRESH=6.0:** All 3 consumers (volatility_gate_v2.py:549, decider_run.py:2008, signal_compactor.py:3974) read the constant — 6.0 applies uniformly. ✅
7. **signal_compactor inline import:** `from hermes_constants import PENALTY_MULT_FLOOR as _mult_floor` is inside `_score_signal`; hermes_constants is already imported at module top (line 26) so the inline import hits `sys.modules` cache — works, no circularity. `_mult_floor` has no prior binding in the function (grep: only lines 2143/2156/2157/2158) — no shadowing. ✅

## Recommendation

**Ship** — the trading behavior exactly matches the CEO-approved spec and fails open everywhere it should. Then fix within 24h, in priority order:

1. **MEDIUM-2 (one line):** point decider_run.py:3494 at `PENALTY_MULT_FLOOR` — without it, change #2 is half-applied.
2. **MEDIUM-1:** add an exemption marker to the *allow* path — without it the documented revert trigger is invisible in logs.
3. **MEDIUM-3:** CEO decision — align pump-chain RSI floors with the new 35/35 regime (incl. PUMP_CHAIN_SHORT_RSI_MIN 45→40) or explicitly confirm pump-chain stays stricter; fix the stale "40 vs 45" comments either way.

Reminder from AGENTS.md: signal-path changes require a pipeline restart to load the new code — restart before measuring the recalibration's effect.
