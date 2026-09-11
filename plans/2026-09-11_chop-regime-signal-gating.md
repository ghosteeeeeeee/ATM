# Chop Regime Signal Gating

**Date:** 2026-09-11
**Status:** CEO APPROVED (CONDITIONAL) → AWAITING IMPLEMENTATION
**Trigger:** 4 consecutive losses — all entered when BTC 30m momentum was flat. Trend signals firing into chop.
**CEO Verdict:** CONDITIONAL GO — Layer A + revised Layer B with LOG_ONLY flag. Skip C, Defer D.

---

## Problem Statement

Last 20 trades entered when BTC 30m momentum was between -0.5% and +0.5%:

```
-0.02%  -0.12%  +0.24%  -0.01%  -0.01%  +0.00%  -0.13%  -0.45%
+0.15%  -0.01%  -0.04%  -0.48%  +0.05%  -0.48%  -0.45%  +0.46%
+0.33%  -0.37%  -0.23%  -0.18%
```

**Every single trade entered in chop.** The signals are trend signals (pump-chain, pullback-entry) firing into flat markets.

### Why Existing Filters Failed

| Filter | What It Should Do | Why It Failed |
|--------|------------------|---------------|
| Chop Detector | Block momentum in chop | Voting system — BTC voted CHOP but other votes overrode |
| NEUTRAL_BLOCK | Block signals in NEUTRAL | STANDALONE_BYPASS lets pump-chain/pullback-entry bypass the block |
| Alt-BTC Divergence | Block divergent entries | Only checks alt DOWN while BTC UP — opposite happened (alt UP while BTC flat) |

**The critical gap:** `STANDALONE_BYPASS_SIGNALS` (line 2136) includes pump-chain, pullback-entry, and most other signals. They bypass the neutral block entirely (signal_compactor.py:1807). Classification changes don't matter if the bypass skips the check.

---

## Solution: 2 Layers (CEO-Approved)

### Layer A: Hard BTC Momentum Gate

**What:** When BTC 30m momentum is flat, block ALL momentum-family signals. Binary gate, no voting.

**CEO assessment:** Correct, but impact overstated — catches 2/4 named losses (BCH, APT), not 6/8. SAND and ENA are pullback-entry (classified MEAN_REVERSION), untouched by momentum gate.

**Constants:**
```python
BTC_CHOP_GATE_ENABLED = True
BTC_CHOP_GATE_THRESHOLD = 0.15  # % — matches CHOP_DETECTOR_BTC_MOM_THRESHOLD
```

**Implementation:** ~10 lines in `_score_signal()` at line 957, BEFORE chop detector.

**CEO note:** Overrides token momentum bypass in chop_detector.py:330. Correct behavior — BTC flat = no tailwind regardless of altcoin momentum. Document this tradeoff.

---

### Layer B (Revised): Gate the STANDALONE_BYPASS Itself

**What the plan proposed:** Modify signal classification (block momentum, allow mean-reversion in NEUTRAL).

**CEO finding:** This is COSMETIC. pump-chain and pullback-entry are in STANDALONE_BYPASS — they bypass the neutral block entirely. Changing classification doesn't help.

**CEO revision:** Add BTC momentum check to the STANDALONE_BYPASS bypass condition:

```python
# Line 1807 — current:
elif unique_signal_types >= 2 or bare_source in STANDALONE_BYPASS_SIGNALS:

# Revised:
elif unique_signal_types >= 2 or (bare_source in STANDALONE_BYPASS_SIGNALS and _btc_momentum_ok):
```

Where `_btc_momentum_ok = abs(btc_30m_momentum) >= 0.15%`.

**This prevents ANY single-source signal from bypassing the neutral block when BTC is flat** — regardless of signal classification.

**Implementation:** ~5 lines in signal_compactor.py neutral block check.

---

### ~~Layer C: Continuum Oscillator~~ → SKIPPED (CEO: over-engineering)

Adds 20 lines + DB reads + variance calculations on top of 4 existing voters. Layers A+B address the root cause. Revisit only if A+B leave measurable gaps after 2 weeks.

### ~~Layer D: Enable RS in Flat~~ → DEFERRED (CEO: underperformed)

RS source weight suppression is intentional (0.4 penalty). Re-enabling without fixing the signal itself just lets noise through. Defer until RS is re-engineered.

---

## Implementation

### Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `scripts/hermes_constants.py` | Add BTC_CHOP_GATE constants + LOG_ONLY flag | ~5 lines |
| `scripts/signal_compactor.py` | Add BTC gate check + gate STANDALONE_BYPASS in neutral block | ~15 lines |

**Total: ~20 lines + 3 constants.**

### LOG_ONLY Mode

New constant for testing:
```python
CHOP_GATE_LOG_ONLY = True  # Set False after 48h of clean logs
```

When True, log what would be blocked without actually blocking. Run 48h before going live.

---

## Expected Impact

**CEO revised estimate:** Layer A catches 2/4 named losses. Layer B catches the other 2 (SAND, ENA) by preventing STANDALONE_BYPASS in flat BTC.

| Layer | Trades Affected | Estimated Impact |
|-------|----------------|-----------------|
| Layer A (BTC gate) | BCH SHORT, APT LONG | +$0.25 |
| Layer B (bypass gate) | SAND SHORT, ENA SHORT | +$0.35 |
| **Total** | | **+$0.60** |

---

## Risk Analysis

| Risk | Severity | Mitigation |
|------|----------|------------|
| Layer A blocks valid entries during brief BTC dips | Medium | 0.15% is conservative; strong trends >0.3% |
| Layer B doesn't fix STANDALONE_BYPASS gap | **Fixed** | Revised to gate bypass condition itself |
| Mean-reversion signals lose in true NEUTRAL | Medium | LOG-ONLY first; kill if WR <45% at 10 trades |
| Token momentum bypass overridden | Low | Correct behavior — BTC flat = no tailwind |

---

## Testing Plan

1. **LOG-ONLY (48h):** Add both gates with `CHOP_GATE_LOG_ONLY=True`. Log what would be blocked.
2. **Review logs:** Verify no false positives (valid entries that would have been blocked).
3. **Enable live:** Set `CHOP_GATE_LOG_ONLY=False`. Monitor signal volume.
4. **Abort trigger:** If signal volume drops >25% or WR drops below 45% at 20+ trades → revert.

---

## CEO-Approved Implementation Order

1. Layer A (BTC hard gate) — 10 lines, high confidence
2. Layer B (bypass gate) — 5 lines, addresses the real gap
3. LOG-ONLY flag — 3 lines, enables safe testing
4. Enable live after 48h clean logs
