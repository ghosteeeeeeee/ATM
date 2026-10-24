# Own Conclusions: New Signals (vol_momentum + volbreak_cont) — Independent Validation

**Auditor:** independent own-conclusions pass (fresh read, no priming from prior analysis)
**Date:** 2026-10-24
**Method:** read all 6 files from scratch + 151 independent executed checks + live dry scans + stubbed run()-path tests. Every claim below is backed by code I ran, not by reading.

## Summary

Both signals implement their spec exactly, fail closed on every missing input, and are correctly wired (constants, registry, vol-gate EXTREME-only routing with mult 1.0, exit config, family maps). All code executes clean: compile ✓, flags-off run ✓ (0 signals, exit 0), 20/20 author selftests ✓, my own 151-check harness ✓, real-data dry scan ✓ (vol_momentum found 1 sane match on 182 tokens, volbreak 0 — no exceptions). I found no logic bugs. I did find 3 real infrastructure issues the wiring review can miss (dead SHORT band, merged-source vol-gate leak, missing add_signal defense-in-depth gate) — none block shadow mode; all should be settled before any enable flip.

## Verdict: APPROVE (as shadow-mode, ENABLED=False — unchanged status quo)

Approve the code as shipped OFF. Enabling either flag — especially `VOLMOM_MINUS_ENABLED` — requires the recommendations below to be resolved first.

## Signal Logic

### vol_momentum.py — CORRECT
- **Evidence (executed):** All 5 spec conditions verified line-by-line against `_evaluate()` and re-tested synthetically: SHORT fires iff RSI(14) < 35 (strict; RSI==35.0 → no fire), ATR% ≥ 1.5 (ATR==1.5 fires, 1.4999 blocked — consistent with `classify_volatility(1.5) == 'EXTREME'`), price < EMA300 (strict; price==EMA → no fire), momentum_state == 'falling' (exactly; 'flat'/None blocked), vol ≥ 1.2× 20-bar avg (1.20 fires, 1.1999 blocked). LONG mirrors with strict > 70 / > EMA300 / 'rising'.
- **Fail-closed:** atr=None, rsi=None, momentum=None, momentum='flat', <350 candles, zero volume, price=0, negative closes → all return None (verified).
- **Window math (verified with probe series):** volume avg = `volumes[-21:-1]` = exactly 20 prior bars, current bar excluded; ratio = last bar / that avg. No off-by-one.
- **Direction separation (verified):** RSI=30+falling+above-EMA → none; RSI=75+rising+below-EMA → none; RSI=30+rising → none; RSI=75+falling → none. SHORT and LONG bands (35/70) are mutually exclusive — no overlap, no flip-flop.
- **EMA:** `_compute_ema` 300-period over 350 closed 5m candles, chronological order correct (oldest-first fetch verified in SQL), seed = first price (house convention, see New Findings F6).
- **Live data:** dry scan over 182 tokens produced exactly 1 match — YGG SHORT rsi=33.2 atr=1.694% vol=1.48x mom=falling — internally consistent values, no exceptions.
- **Confidence:** base 65, +5 ATR ≥ 3.0%, +5 RSI ≥5 pts beyond band edge (strict), clamped [55,88]; verified 65/70/75 outcomes and bounds.

### volbreak_cont.py — CORRECT
- **Evidence (executed):** Volume > 2× 20-bar avg (2.00 fires, 1.9999 blocked), ATR% ≥ 1.5 (1.5 fires, 1.4999/None blocked), price > EMA300 (strict — flat series blocked), close > max(prev 3 bar highs) with the window `highs[-4:-1]` verified to be exactly the 3 prior bars excluding the current one (probe: max==349, len==3). Breakout boundary: close == prev_high → blocked (strict >), +0.0001 above → fires.
- **Fail-closed:** atr=None, <350 candles, zero volume → None (verified).
- **LONG-only:** no SHORT path exists; `run()` requires both master and PLUS flags.
- **Confidence:** 65, +5 when vol ≥ 4× (2× the 2× threshold), clamped — verified 65/70.
- **Live data:** dry scan 0 matches / 182 tokens, clean exit (strict conditions in calm market — expected).

## Infrastructure

### Constants — PASS
All 15 VOLMOM_* + 14 VOLBREAK_CONT_* constants present in hermes_constants.py (lines 3742–3785), correctly named, no hardcoded magic numbers in either signal file (house rule respected). Thresholds match spec: ATR floor 1.5, RSI 35/70, vol mult 1.2/2.0, EMA 300/350 warmup, cooldown 60 min, conf floor 55 > add_signal's 50 floor.

### Registration — PASS
`scripts/signals/__init__.py`: both modules imported in try/except, both registry entries present with string flags `'VOLMOM_ENABLED'`/`'VOLBREAK_CONT_ENABLED'` (resolved via getattr → dynamic), run fns importable (`_run_signal` name resolution falls back to `signals.<name>` correctly). Verified with real import: entries resolve to False, neither appears in `get_registered_signals()` while flags are OFF. No import errors, no registry warnings.

### Vol-gate routing — PASS
Verified by monkeypatching `get_atr_pct` and calling the real `should_trade_v2` for all 6 name variants × 4 regimes (24 combos):
- EXTREME → TRADE, `combined_mult = 1.0` for `vol-momentum+`, `vol-momentum-`, `vol_momentum_long`, `vol_momentum_short`, `volbreak-cont+`, `volbreak_cont_long` (all present in `REGIME_SIGNALS['EXTREME']`, lines 220–223).
- NORMAL / HIGH / FLAT → SKIP ("not suited for {regime}") for all 6. Family multipliers confirmed: Momentum & Volume = 1.0 in EXTREME, 0.0 in NORMAL (belt-and-braces even if allowlist were bypassed).
- `signal_family()` resolves all 6 variants correctly (Momentum / Volume) through the strip-and-fallback lookup.
- Entry condition (1h ATR ≥ 1.5) and `classify_volatility` use the same `get_atr_pct`, so detection regime and gate regime can't disagree — no detect/gate seam.
- No collision with existing guards: `'volume-breakout'` HIGH block and pump-chain blocks do not substring-match the new sources (verified both).

### Exit config — PASS
Real `position_manager._match_exit_config` (the single module-level matcher): `vol-momentum+`/`vol_momentum_long` → pm_trail, `vol-momentum-`/`vol_momentum_short` → pump_exit, `volbreak-cont+`/`volbreak_cont_long` → pm_trail. Explicit direction + underscore signal_type keys present (pump-chain v5/v6 lesson applied). Cross-contamination checked: `volume-breakout+` → ride_it unchanged, `volume_breakout_short` → ride_it unchanged. Both source and signal_type forms resolve — whichever the trade row carries.

### run() orchestration — PASS (26/26 stubbed checks)
Flags-off returns 0 with zero side effects (both). Direction→signal_type/source mapping exact (LONG→`vol_momentum_long`/`vol-momentum+`, SHORT→`vol_momentum_short`/`vol-momentum-`, volbreak→`volbreak_cont_long`/`volbreak-cont+`). Per-direction flags suppress independently. Stale price (>10 min), active cooldown, open position, blacklists (both directions), `@`-prefixed keys, and `add_signal` exceptions (logged, no crash) all handled. `add_signal` receives timeframe=5m, rsi_14/momentum_state attached for vol_momentum. Open-position tokens confirmed uppercase in DB → `token.upper() in open_pos` is sound.

## New Findings

**F1 — VOLMOM_MINUS (SHORT) is 100% dead at execution, not merely "collides" (medium, documented but understated).**
Entry requires RSI < 35. But `OVERSOLD_SHORT_RSI_MAX=35` **and** `SHORT_RSI_HARD_FLOOR=45` hard-block every SHORT with RSI < 45 on *every* path — signal_compactor, decider_run detect-time AND exec-time floors (lines 1233–1303, 2188–2252), brain.py, ai_trader_precheck. The entire VOLMOM SHORT entry band (RSI<35) is unreachable. Enabling `VOLMOM_MINUS_ENABLED` without a guardrail waiver produces zero trades and useless shadow data. The constants comment flags the collision, but "requires CEO ruling" should read: *SHORT side is dead code until the knife guard is explicitly waived for this source — do not enable, do not expect shadow fills.*

**F2 — Merged-source vol-gate leak (low-medium, PRE-EXISTING infra, demonstrated).**
`add_signal` merges one row per token+direction with comma-joined sources, and `should_trade_v2` passes the EXTREME allowlist if **ANY** comma-part matches. Demonstrated live: `should_trade_v2('BTC', 'mover+,vol-momentum+')` with ATR=0.8 (NORMAL) → **TRADE, mult=1.0** (merged string resolves family 'Other', so the Momentum=0.0 / Volume=0.0 NORMAL blocks also don't apply), while solo `vol-momentum+` correctly → SKIP. So the EXTREME-only habitat holds only while the signal's source stands alone in its row; if a vol_momentum/volbreak signal merges with a NORMAL-admitted source (e.g. `mover+`) and ATR drops below 1.5 between detection and execution, it executes outside its mined habitat. Pre-existing behavior shared by all allowlist-gated signals — not introduced by this change — but it directly weakens "EXTREME-only by design" for the new pair. Fix suggestion: in `context_gate`/`should_trade_v2`, evaluate each comma-part against the regime allowlist separately and require the *specific* source to be admitted (or at minimum, require it for sources whose habitat is a single regime).

**F3 — No add_signal-layer flag gate for the new sources (low).**
`signal_schema.add_signal` carries per-source kill-switch gates (`if _comp == 'momentum+' and not MOMENTUM_PLUS_ENABLED: return None`, ~40 such gates for other families; exact-match, so no false collision with 'vol-momentum+' — verified). The new `vol-momentum±` / `volbreak-cont+` sources have **no** gate. With flags OFF nothing calls add_signal for them (registry + run() both gate), so impact today is defense-in-depth only — but convention across every other family is three layers, and these have two. Add `VOLMOM_*`/`VOLBREAK_CONT_*` gates in add_signal before any enable flip.

**F4 — vol_momentum LONG's +5 RSI confidence bonus is unreachable in live execution (low, informational).**
Bonus requires RSI > 75 (`VOLMOM_LONG_RSI_MIN + 5`), but `LONG_RSI_CEILING=75` hard-blocks LONG with RSI > 75 at execution. Live LONG band is effectively (70, 75] and max attainable confidence is 70, not 75. Consistent with the constants comment ("RSI 70-75 LONG band is kept open") — but the confidence formula advertises a bonus that can never ride a real trade; either accept as ranking-only or move the bonus threshold to ≥ 72.

**F5 — Check-order inconsistency between the two signals (low, perf).**
`volbreak_cont.run()` checks blacklist + cooldown **before** `detect()`; `vol_momentum.run()` runs `detect()` first (≈4–5 DB queries per token per minute) and only then checks blacklists/cooldown. On a 182-token fast-loop this doubles wasted queries for cooled-down tokens. Move the blacklist/cooldown/price-age checks above `detect()` in vol_momentum for parity.

**F6 — EMA300 warmup is thin (info, house convention).**
350 bars for a 300-period EMA seeded at the first close leaves ~9.8% seed weight; in a trending 350-bar series the EMA is biased toward the oldest close, which makes price-vs-EMA fire slightly easier near the boundary in BOTH directions. Identical `_compute_ema` pattern exists in ema300_breakthrough, mtf_regime_trend, ema300_dip, continuation — so this is house style, not a defect of this change. Note for signal_analyst: raising `*_EMA_MIN_CANDLES` to ~900 would de-bias all EMA300 signals uniformly.

**F7 — Spec-vs-code boundary semantics (info, benign).**
Spec says ATR "> 1.5%" and volume "> 2×"; code fires at exactly 1.5 / exactly 2.0 (>=). The ATR choice is *correct* — it matches `classify_volatility`'s EXTREME boundary (>=1.5), keeping entry and regime classification consistent. The volbreak 2.0 exact tie is a float-tie non-issue. RSI boundaries are strict exactly per spec.

**F8 — Audit housekeeping (info).** My stubbed run()-path tests wrote 6 synthetic `[vol-momentum]`/`[volbreak-cont]` lines into `/var/www/hermes/logs/signals.log` via `_log`; I removed exactly those lines (backup at `/tmp/signals.log.bak`). No legitimate entries with those prefixes exist (flags OFF), verified 0 remaining matches.

## What I could NOT verify
- Execution-time behavior of the trades themselves (exit engines pm_trail/pump_exit in live position management) — wiring verified, runtime behavior only observable after enable.
- The shadow-data thesis itself (17,321 shadow signals, expectancy numbers in the docstrings) — taken on faith as the analyst's prior work; my scope was code correctness, not re-deriving the mining results.

## Recommendations
1. **Do not enable `VOLMOM_MINUS_ENABLED`** until the CEO explicitly rules on the OVERSOLD knife guard for this source — as shipped, it is a guaranteed zero-trade flag (F1).
2. Before enabling either signal, add the add_signal-layer kill-switch gates for the 3 new source forms (F3) — cheap, matches house convention.
3. Open a ticket for the merged-source vol-gate leak (F2) — affects every EXTREME-only signal, worth a systemic fix in `should_trade_v2`, but NOT a blocker for shadow mode.
4. Accept that live LONG band is (70,75] and conf caps at 70, or adjust the bonus threshold (F4); document in the enable-plan.
5. Reorder vol_momentum.run() checks (blacklist/cooldown before detect) for parity with volbreak_cont (F5).
6. Restart the pipeline after any flag flip (AGENTS.md rule) — run() binds flags at import.
7. Keep `--dry` scans in the enable-validation loop: vol_momentum produced 1/182 live match right now, so expect a low fire rate; do not mistake a quiet first week for a dead signal.

## Approval
- [x] Approved as-is (for shadow mode, ENABLED=False — no code changes required before shadow)
- [ ] Approved with changes (list changes) — *see Recommendations 1–5 as pre-conditions for any ENABLE flip*
- [ ] Rejected (explain why)

*Evidence artifacts: `/tmp/audit_new_signals.py` (125 checks), `/tmp/audit_run_paths.py` (26 checks), `/tmp/audit_out.txt` (full output). All executed in this session.*
