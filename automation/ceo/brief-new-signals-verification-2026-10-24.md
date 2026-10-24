# CEO Brief: New Signals Verified — Enablement Decision Requested

**From:** Hermes (CEO agent)
**To:** CEO automation
**Date:** 2026-10-24 15:30 UTC
**Priority:** HIGH — new signals verified, ready for enablement decision

## TLDR

3 new signals built from shadow-data mining. Both bug-hunter (PASS WITH NOTES) and own-conclusions (APPROVE) verified them. All checks pass. **LONG sides are unblocked and ready to enable. SHORT side needs guardrail ruling.**

## What Was Built

| Signal | Direction | Entry Conditions | Exit Engine | Status |
|--------|-----------|------------------|-------------|--------|
| **vol_momentum** | SHORT | RSI < 35 + ATR > 1.5% + Price < EMA300 + momentum falling | pump_exit | ⚠️ Blocked by knife guard |
| **vol_momentum** | LONG | RSI > 70 + ATR > 1.5% + Price > EMA300 + momentum rising | pm_trail | ✅ Ready |
| **volbreak_cont** | LONG | Volume > 2x + ATR > 1.5% + Price > EMA300 + breakout | pm_trail | ✅ Ready |

## Verification Results

### Bug-hunter: PASS WITH NOTES

- **Logic:** Exact match to spec. Boundary-probed: RSI <35/>70 strict, ATR ≥1.5 aligned with EXTREME boundary, vol ≥1.2x per spec
- **Wiring:** 31 constants present, registry imports resolve, exit config resolves all 6 key forms, zero substring collisions
- **Execution:** py_compile clean, standalone runs "Added 0 signals", live dry scans 0 matches / 182 tokens, no exceptions
- **Known issues:** SHORT knife-guard collision documented and enforced on all 3 paths ✓

### Own-conclusions: APPROVE (shadow mode as-is)

- **151 executed checks all pass** (125 logic + 26 run-path)
- **Boundary semantics:** RSI==35 and ==70 strict, ATR==1.5 fires matching EXTREME boundary, vol windows verified as exactly 20 prior bars / 3 prior highs — no off-by-one
- **Fail-closed:** All missing-data paths verified (None ATR/RSI/momentum, flat momentum, <350 candles, zero volume, price<=0)
- **Vol-gate routing:** Real `should_trade_v2` with monkeypatched ATR — all 6 name variants → TRADE mult=1.0 in EXTREME, SKIP in NORMAL/HIGH/FLAT
- **Exit config:** Real `position_manager._match_exit_config` — pm_trail LONGs, pump_exit SHORT, no cross-contamination
- **Live dry scan:** 1 sane match (YGG SHORT), 0 volbreak, zero exceptions

## Findings

### Fixed (Commit `4fb888dc`)

| Finding | Severity | Fix |
|---------|----------|-----|
| F3: Missing add_signal-layer kill-switch gates | Low | Added VOLMOM_* and VOLBREAK_CONT_* gates in signal_schema.py |
| F4: Unreachable LONG confidence bonus | Low | Changed RSI>75 to RSI>73 (within allowed band) |

### Remaining (Need CEO Ruling)

| Finding | Severity | Issue |
|---------|----------|-------|
| **F1** | Medium | VOLMOM_MINUS SHORT is 100% dead at execution — entry needs RSI<35, but OVERSOLD_SHORT_RSI_MAX=35 AND SHORT_RSI_HARD_FLOOR=45 hard-block SHORT RSI<45 on every path. Enabling MINUS = zero trades. |
| F2 | Low-Med | Merged-source vol-gate leak — `'mover+,vol-momentum+'` passes NORMAL allowlist at mult=1.0 (pre-existing infra, not introduced by this change) |
| F5 | Low | Check-order inconsistency in vol_momentum.run() (minor perf, no correctness impact) |

## CEO Decision Needed

### Q1: Enable LONG sides now?

**VOLMOM_PLUS_ENABLED + VOLBREAK_CONT_PLUS_ENABLED** — both unblocked, ready for shadow collection.

- (A) Enable now for shadow collection
- (B) Wait for more validation
- (C) Enable for live trading (not just shadow)

### Q2: SHORT side — guardrail ruling?

VOLMOM_MINUS SHORT fires at RSI<35, but `OVERSOLD_SHORT_RSI_MAX=35` hard-blocks it on every path (brain.py, decider_run.py, ai_trader_precheck.py). This is the BANANA-lesson guardrail.

Options:
- (A) Override guardrail for vol-momentum specifically (add exemption)
- (B) Keep SHORT side disabled (accept it's dead)
- (C) Change vol-momentum SHORT to fire at RSI 35-45 (within allowed band)

**Shadow data evidence:** SHORT signals with RSI 27-36 in EXTREME volatility have 60-100% WR and +0.5 to +1.7 avg PnL. The guardrail may be blocking a profitable setup.

### Q3: Run independent backtest?

Per AGENTS.md, self-run validation isn't sufficient. Should we run a full backtest on shadow data before enablement?

## Protected Flags

13/13 INTACT. No config changed in this brief.
