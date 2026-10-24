# Bug Hunter Verification: New Signals (vol_momentum + volbreak_cont)

## Summary
Both signals compile, run clean (0 fires, flags OFF), pass 20/20 selftests, and their logic matches spec exactly (verified with synthetic boundary probes). Infrastructure wiring — constants, registration, vol-gate routing (EXTREME 1.0 / NORMAL 0.0), exit config, family mapping — all verified programmatically with zero substring collisions. No bugs found; 1 LOW (SHORT-side knife-guard collision, expected/documented) + 2 INFO findings.

## Verdict: PASS WITH NOTES

## Signal Logic Verification

### vol_momentum.py — PASS
- SHORT: RSI(14) < 35 (`<` strict, verified RSI=35.0 blocked / 34.9 fires) + ATR% ≥ 1.5 (verified 1.4999 blocked / 1.5 fires, matches `classify_volatility` EXTREME boundary) + close < EMA300 (verified oversold-above-EMA blocked) + momentum_state == 'falling' + vol ≥ 1.2× 20-bar avg (verified 1.199x blocked / 1.20x fires) — spec exact.
- LONG: RSI(14) > 70 (`>` strict, verified 70.0 blocked / 70.1 fires) + close > EMA300 + momentum_state == 'rising' + same ATR/vol floors — spec exact.
- Direction separation verified: RSI=30 falling below-EMA fires SHORT only; RSI=30 rising below-EMA blocked; mid-band RSI=50 blocked both sides.
- Fail-closed verified: missing ATR → None, missing RSI → None, momentum None/flat → None, <350 candles → None, price ≤ 0 → None, vol_avg ≤ 0 → None (selftests + live).
- Confidence: base 65, +5 when ATR% ≥ 2× floor (verified atr=3.1 → 75), +5 when RSI 5+ pts beyond band edge (verified rsi=29 → 70), clamped to [55, 88] — all within add_signal's 50 floor.
- Cooldown (`get_cooldown(token, direction=...)` before fire, `set_cooldown` after add), LONG/SHORT_BLACKLIST (per direction), open-position skip, price-age (10 min) — all present in `run()`.

### volbreak_cont.py — PASS
- LONG only: vol ≥ 2× 20-bar avg (spec says "> 2×" — impl fires at exactly 2.00x, see INFO finding) + ATR% ≥ 1.5 + close > EMA300 (strict) + close > max(HIGH of previous 3 bars) (strict; verified close == prev_high blocked, and close measured against HIGHS not closes) — spec exact.
- Fail-closed verified: missing ATR → None, <350 candles → None, no-breakout → None, downtrend (below EMA300) → None.
- Confidence: base 65, +5 when vol ≥ 4× (2× the 2× threshold), clamped [55, 88].
- Cooldown (per-token LONG), LONG_BLACKLIST, open-position skip, price-age — all present.

## Infrastructure Wiring

### Constants — PASS
17 VOLMOM_* + 14 VOLBREAK_CONT_* at `hermes_constants.py:3736-3785`, all correctly named/placed with rationale comments; every imported symbol resolves (module imports clean). `hermes_constants.py` DO-NOT-CHANGE rule respected — only additions, no existing values touched.

### Registration — PASS
`signals/__init__.py:495-502, 597-598`: both imported (run != None verified live) and registered with correct ENABLED flag names (`VOLMOM_ENABLED`, `VOLBREAK_CONT_ENABLED`); `_warn_broken_registry_entries` covers them. Default fast cadence fine (full scan measured 1.8s).

### Vol-gate routing — PASS
- `volatility_gate_v2.py:220-223`: all 6 runtime strings (sources `vol-momentum+/-`, `volbreak-cont+` + signal_types `vol_momentum_long/short`, `volbreak_cont_long`) in EXTREME REGIME_SIGNALS; absent from NORMAL/HIGH/FLAT → SKIP 'not suited'.
- End-to-end `get_combined_multiplier`: EXTREME → 1.0, NORMAL → 0.0 (hard block via Momentum/Volume family), HIGH → 0.0 for volbreak (Volume block) / 1.0 for vol_momentum (harmless — blocked by REGIME_SIGNALS membership anyway).
- SIGNAL_TYPE_OVERRIDES: zero substring collisions for all 3 signal_types across all 4 regimes (programmatically checked).
- Exit config (`SIGNAL_EXIT_CONFIG:1971-1978` + `_match_exit_config` verified live): `vol-momentum+`→pm_trail, `vol-momentum-`→pump_exit, `vol_momentum_long`→pm_trail, `vol_momentum_short`→pump_exit, `volbreak-cont+`/`volbreak_cont_long`→pm_trail. Lookalikes (`volume-breakout+`, `volume_buildup+`) unaffected.
- Family mapping (`market_phase_gate.py:42-43, 92`): all hyphen/underscore/bare forms resolve to Momentum / Volume (verified via `signal_family()`).

### Exit config — PASS
Explicit direction keys present for all versioned/direction forms (pump-chain v5/v6 lesson applied). SHORT→pump_exit matches shadow-data best exit; LONG→pm_trail.

## Findings

### LOW — SHORT side is hard-dead at execution (expected, correctly documented)
- **Location**: `hermes_constants.py:3748-3753`; enforcement verified at `brain.py:387-401`, `decider_run.py:1233-1254`, `ai_trader_precheck.py:315-328`
- **Issue**: VOLMOM_MINUS SHORT fires at RSI<35, but OVERSOLD_SHORT_RSI_MAX=35 knife guard + SHORT_RSI_HARD_FLOOR=45 reject every SHORT below RSI 45 on every execution path.
- **Impact**: If enabled, VOLMOM_MINUS signals will fire, be recorded, then be rejected at execution — wasted signal quota, confusing shadow stats (detection WR ≠ executed WR).
- **Fix**: Keep VOLMOM_MINUS_ENABLED=False until CEO ruling on the BANANA guardrail (as documented). Consider not enabling MINUS at all if the guardrail stands.

### INFO — momentum_state coverage is ~17% of live tokens (worse than the "~half" flagged)
- **Location**: `signal_schema.py:456-533` (`_enrich_indicators`); consumed at `vol_momentum.py:189-190`
- **Issue**: Live sample of 12 tokens with fresh 5m data: only 2 had a non-None `momentum_state` (needs ≥26 price_history rows in 60 min — sparse DB).
- **Impact**: vol_momentum fires far less often than the shadow-data thesis implies; dry scan across 182 tokens found 0 matches (fail-closed working as designed, but sample rates for enabling should assume low fire rate).
- **Fix**: None required (fail-closed is correct). If fire rate matters post-enable, consider computing momentum from the 5m closes already fetched instead of price_history.

### INFO — "shadow mode" as implemented = flags OFF = no data collected
- **Location**: `vol_momentum.py:197-198`, `volbreak_cont.py:169-170`
- **Issue**: Unlike neutral_sniper/range_reversion's SHADOW_MODE (detect + log + skip add_signal), these signals return 0 immediately when disabled — nothing is recorded anywhere.
- **Impact**: No automated counterfactual collection while "in shadow"; validation depends on manual `--dry` runs or the 5-minute shadow_trades.db approach.
- **Fix**: When ready to validate live, either add a SHADOW_MODE branch (detect + log, no add_signal — matching the neutral_sniper convention) or schedule periodic `--dry` scans.

### INFO — volbreak volume threshold fires at exactly 2.00× (spec wording says "> 2×")
- **Location**: `volbreak_cont.py:116` (`if vol_ratio < VOLBREAK_CONT_VOL_MULT: return None`)
- **Issue**: Equality passes; spec says strictly greater. (vol_momentum's ">=" matches its spec exactly.)
- **Impact**: None meaningful — boundary-only.
- **Fix**: None needed.

## Code Execution

### py_compile — PASS
Both files compile clean.

### Signal file execution — PASS
- `python3 scripts/signals/vol_momentum.py` → "Added 0 signals", exit 0 (flag OFF, no errors)
- `python3 scripts/signals/volbreak_cont.py` → "Added 0 signals", exit 0
- Selftests: vol_momentum 12/12 PASS, volbreak_cont 8/8 PASS (20/20 total)
- Dry scans (live data, read-only): vol_momentum 0 matches / 182 tokens (1.8s), volbreak_cont 0 matches / 183 tokens — both exit 0, no exceptions

## Known-Issue Verification
1. **SHORT knife-guard collision** — documented in constants + code docstrings; verified enforcement on all 3 execution paths. Handled correctly.
2. **momentum_state None for many tokens** — fails closed (verified live + selftest). Handled correctly.
3. **Watchdog `git add -A` sweep** — verified commit 186ff1c0: `hermes_constants.py` +64 lines, **0 deletions**, all additions are VOLMOM/VOLBREAK constants + exit-config keys. No unrelated constants swept. Clean.

## Recommendations
1. Before enabling: run `--dry` scans periodically (or add the SHADOW_MODE log branch) to collect real fire rates — expect LOW fire rate due to momentum_state coverage (~17%).
2. Get explicit CEO ruling before ever flipping VOLMOM_MINUS_ENABLED — the SHORT side is hard-dead against the BANANA knife guard as it stands.
3. Enabling sequence: VOLMOM_PLUS_ENABLED first (no guardrail collision), VOLBREAK_CONT_PLUS second; restart pipeline after each flag flip (AGENTS.md staleness rule).
4. Optional hardening (LOW priority): seed EMA from SMA of first 300 closes instead of prices[0] — current warm-start leaves ~10% seed weight after 350 bars (same approximation as ema300_breakthrough, so consistency is a valid defense for leaving it).
