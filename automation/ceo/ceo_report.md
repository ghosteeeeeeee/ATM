# Recalibration Decision — 2026-10-13

**Status:** APPROVED — implement in order below, each with independent revert trigger.
**Context:** System severely throttled (not fully frozen — 16 trades/24h, but 3W/16T −$1.20). WR 36.7% Oct 6-12 vs 53.9% Sep 28-Oct 5. Frequency halved (32→18/day).

## Evidence corrections (verified from brain DB + pipeline logs)

The report had three factual errors — decisions below account for the corrected numbers:

1. **"Profitability didn't improve" is FALSE.** PnL: Sep 28–Oct 5 = **+$0.15** (256T, 53.9% WR) → Oct 6–12 = **+$0.46** (128T, 36.7% WR). Tight filters cut losers harder than they cut winners — profit per trade nearly tripled. The freeze is a *frequency* problem, not a *profitability* problem.
2. **Blocker distribution was wrong.** Actual 24h counts: CONFLUENCE 294 blocks (2215 passes — 12% rate, NOT the main killer), RR HARD BLOCKED 133, SHORT-CONTINUUM 331, MAXXED 240, CONTINUUM-BULL 234, PENALTY-BLOCK 148, EXEC-RSI-HARD-FLOOR only 2. The RR engine is the #1 *hard* killer; CONTINUUM+MAXXED together are the volume killers.
3. **return_exhaustion_short is ALREADY in STANDALONE_BYPASS** (hermes_constants.py:2924). It has **1 closed trade ever (0W −$0.11)**. The fix is disable, not bypass.

Current BTC state at decision time: **BULLISH** (continuum score 98-100, STRONG_POS). CONTINUUM-BULL blocking SHORTs is *correct* behavior right now — not a bug.

---

## Decisions

### 1. RR Engine regime exemption — ✅ APPROVED

**Value:** In confirmed structure (LEAN_BEAR+BELOW-EMA300 for SHORTs / LEAN_BULL+ABOVE-EMA300 for LONGs), `RR_ENGINE_CONF_HARD_BLOCK_RR` effective threshold **0.55 → 0.35**. In chop, stays 0.55.

- 0.35 not 0.30 — Grade D multiplier (0.5x) already punishes these; 0.35 still blocks true garbage.
- Rationale: regime confirms direction; R:R double-gates. 133 hard blocks in 24h, nearly all LONGs in a bull market (BABY R:R 0.44, SUPER R:R 0.53).
- Implementation: `risk_reward_engine.py:1091` — check regime before applying threshold. Move effective threshold to a new constant `RR_ENGINE_CONF_HARD_BLOCK_RR_CONFIRMED = 0.35` in hermes_constants.py.
- **Revert trigger:** ≥10 regime-exempted trades (RR 0.35-0.55) close at aggregate −$1.00 or worse within 7 days → restore 0.55 globally. Log every exempted trade with tag `[RR-REGIME-EXEMPT]`.

### 2. SHORT_RSI_HARD_FLOOR: 45 → 35 — ✅ APPROVED (with scope fix)

**Value:** Both `SHORT_RSI_HARD_FLOOR` and `SHORT_RSI_FLOOR` **45 → 35**. RSI < 35 SHORT still blocked.

- The report only named HARD_FLOOR, but `SHORT_RSI_FLOOR=45` (line 898) is the primary gate — lowering only HARD_FLOOR changes nothing. Both must move.
- 35 not 30 — BANANA lesson (shorting RSI 10 = falling knife) + measured 40-45 bleed band (37T −$2.28). 35 opens the moderate-dump zone while keeping extreme oversold blocked.
- The "no bearish override" design was correct in chop; in confirmed dumps it blocks the philosophy ("every dump is a SHORT").
- **Revert trigger:** 30d rolling: SHORTs with entry RSI 35-45 aggregate PnL < −$1.00 OR WR < 40% with n≥15 → restore 45. Log entry RSI on every SHORT fill.

### 3. MAXXED_ATR_PCT_THRESH: 4.0% → 6.0% — ✅ APPROVED

**Value:** `MAXXED_ATR_PCT_THRESH = 6.0`. `MAXXED_BLOCK_ENABLED` stays True. `MAXXED_REGIME_LOG` stays True (counterfactual data collection).

- 4.0 was calibrated to a lower-vol regime; ATR routinely hits 5-6% now. BLUR blocked at 6.04% for hours.
- Position sizing already scales with ATR/leverage — risk per trade bounded.
- **Revert trigger:** 14d rolling: trades with entry ATR 4-6% (newly unblocked band) aggregate PnL < −$1.50 → restore 4.0. The shadow log already tags these.

### 4. Penalty multiplier floor: 0.3 → 0.5 — ✅ APPROVED (Option A)

**Value:** `signal_compactor.py:2143` `_mult_floor = 0.3 → 0.5`. Also hoist to hermes_constants as `PENALTY_MULT_FLOOR = 0.5` (conventions: no hardcoded constants).

- Option B (remove one multiplier) requires knowing which multiplier to cut — more analysis, more delay. Floor raise is one number, global, and directly addresses the failure mode: floored-to-0.3 signals still below the 40% PENALTY-BLOCK threshold.
- At 0.5, floored signals clear the 40% exec threshold. Multipliers that genuinely stack high still bite (product > 0.5 unaffected).
- **Revert trigger:** 7d: signals that fire *only because* of the 0.5 floor (product was 0.3-0.5) close 0W/n≥5 → revert floor to 0.3. Tag these `[FLOOR-RELIEF]` in logs.

### 5. return_exhaustion_short — ✅ DISABLE (not bypass)

**Value:** `RETURN_EXHAUSTION_SHORT_ENABLED = False` (hermes_constants.py:3401).

- Already in STANDALONE_BYPASS (line 2924) — the report's proposed fix is a no-op.
- 1 closed trade ever: 0W −$0.11. Zero edge, burns signal-slot and confluence-gate cycles.
- **Revert trigger:** none — it has no edge to regress to. Re-enable only with a fresh 30d backtest showing positive PnL.

---

## Recalibrations NOT approved (and why)

- **CONTINUUM-BULL / SHORT-CONTINUUM:** Correct behavior. BTC is bullish — blocking SHORTs is the filter doing its job. These blocked 565 attempts in 24h because the market is one-directional, not because they're broken.
- **CONFLUENCE gate:** 12% block rate (294/2509). Not the freeze driver. SYRUP ichimoku+ single-source block is a per-signal bypass question, not a gate-recalibration question — handle via STANDALONE_BYPASS review separately if ichimoku+ has a proven solo edge.
- **CHASE filter:** No significant recent block volume. Leave alone.
- **PENALTY-BLOCK threshold (40%):** Floor raise (#4) addresses the cause; lowering the threshold would compound with the old floor and mask the problem.

## Implementation order

| # | Change | Risk | Files |
|---|--------|------|-------|
| 1 | `RETURN_EXHAUSTION_SHORT_ENABLED = False` | None (dead signal) | hermes_constants.py |
| 2 | `MAXXED_ATR_PCT_THRESH = 6.0` | Low (sizing scales) | hermes_constants.py |
| 3 | `PENALTY_MULT_FLOOR 0.3→0.5` | Low | signal_compactor.py + hermes_constants.py |
| 4 | `SHORT_RSI_FLOOR` + `SHORT_RSI_HARD_FLOOR` 45→35 | Medium | hermes_constants.py |
| 5 | RR regime exemption (0.35 confirmed / 0.55 chop) | Medium (code change) | risk_reward_engine.py + hermes_constants.py |

**After each change: restart pipeline** (stale-code lesson). Order is lowest-risk-first so a bad step is caught before the next lands.

## Cross-cutting revert

Any change causing **−$2.00 aggregate over 24h from newly-unblocked trade classes** → revert that specific change immediately, keep the rest. Tag every newly-allowed trade with which recalibration unblocked it.

## Note on the WR drop

WR fell 53.9%→36.7% *after* the Oct 6-7 tightening, but PnL rose. This is consistent with the filters cutting mid-tier winners and losers alike, leaving fewer but (per unit) better trades — until volume dropped to near-zero. The recalibrations above restore frequency without returning to the pre-Oct-6 regime: every loosening has a measured revert trigger and a log tag for counterfactual audit.
