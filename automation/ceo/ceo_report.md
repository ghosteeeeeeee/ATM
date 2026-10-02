## CEO Report — 2026-10-02 (Plan Review: SHORT Signal Drought)

### VERDICT

**Plan is directionally correct. Fix 1 is real, verified, and SHIPPED. Fixes 2–6 approved with conditions. Do NOT wholesale-sync or repoint decider to v2 — that would break more than it fixes.**

Verified numbers (PG brain, just queried):
- 24h: 53T **60.4% WR +$0.81** — system positive overall
- 7d: LONG +$2.04/117T 52.1% | SHORT **-$1.32/48T 45.8%**
- Oct 2: **51 LONG / 1 SHORT** — drought confirmed (1 SHORT = HYPER pump-chain-, RSI 19.6, lost -$0.13)
- Oct 1: 13 LONG / 17 SHORT (35.3% WR, -$0.78) — shorts existed, they lost
- Critical claim VERIFIED: `continuum-trend-` in v1 REGIME_SIGNALS was FLAT-only; `decider_run.py:1554` imports v1; conf=99 BTC SHORT killed "not suited for NORMAL"

### DECISIONS

| # | Decision | Rationale |
|---|----------|-----------|
| **Fix 1** | **APPROVED — APPLIED + committed** | Selective v1 patch: added `continuum-trend±` to NORMAL/HIGH/EXTREME (already in FLAT). Asserts pass; pump-chain- HIGH/EXTREME blocks intact. **NOT a wholesale sync/repoint.** |
| **Fix 2** | **APPROVED (pattern)** | Bear-structure-gated exemption, same shape as SHORT-RSI-FLOOR-OVERRIDE. Code already sits UNCOMMITTED in `signal_compactor.py` working tree — commit + restart to load. Monitor 24h. |
| **Fix 3** | **APPROVED (pattern)** | VEL-FILTER downtrend exemption, bear-gated only (not blanket). Implement after Fix 2 lands and is clean. |
| **Fix 4** | **PRESERVE-SPIKE WINS at RSI<30** | 14d data: RSI<25 = 23T **8.7%WR -$2.62** (hard floor justified); RSI 25-30 = 23T 56.5%WR but **avg_pct -0.63** (R:R inverted). BANANA lesson stands. FLOOR-OVERRIDE keeps working in the 30–40 band only. |
| **Fix 5** | **CONDITIONAL — RSI 65–75 only, bear-gated, 48h monitor** | 14d: RSI 65–75 = 3T 66.7% +$0.30; 75+ = 1T. Tiny sample. Allow 65–75 in confirmed bear structure; **RSI 75+ stays blocked**. Auto-revert if WR<40% at 5+ trades. |
| **Fix 6** | **AUTHORIZED — read-only audit first** | Inventory every SHORT-only gate; each needs a bear exemption or a data-backed unconditional reason. No gate changes until audit lands. |

### RISKS (desk missed these)

1. **Wholesale v1↔v2 sync or repointing decider to v2 would be catastrophic.** v1 has **132** signals, v2 has **84**. **55 signals exist in v1 only** — including `volume-breakout-long+` (best signal), `doji-bottom-long`, `bb-squeeze+`, `mtf-regime-trend±`. Repointing kills those LONGs. Also v2 still has `pump-chain-` in HIGH — sync would **undo signal_reporter's Oct 1 HIGH kill**. Fix 1 stays additive-to-v1 only.
2. **`SHORT_RSI_HARD_FLOOR=25` is unconditional by design** (Oct 1, "no bearish override") — plan never mentions it. Even after Fixes 2–4, RSI<25 shorts stay dead. That is correct per BANANA lesson; just know it's there.
3. **Fix 2 code is already in the working tree, uncommitted.** Not "write new code" — commit + restart. Pipeline must be restarted or decider/compactor keep running old modules.
4. **"LONGs executed freely" ≠ "LONGs won."** mtf-regime-trend+ LONG ran 9× on Oct 2 and lost **-$0.46**. Unblocking shorts is necessary, not sufficient — short R:R/exit quality is a separate bleed (hard_sl 6T -$1.03/48h dominant).
5. **Many monitor windows active** (oscillator retune, bollinger, SHORT-CONTINUUM, HARD_FLOOR, ema_reclaim, bb-squeeze). Ship Fix 1 + Fix 2 as separate commits with restarts; do not stack Fixes 3–5 in the same restart.
6. **v1 `should_trade` has no fail-open** — missing signal = hard SKIP. Table completeness is load-bearing. v2 fail-open behavior differs — another reason not to repoint blindly.

### NEXT STEPS

1. **Restart pipeline** — load Fix 1 (v1 table) + existing pump-chain bear override in working tree
2. **Commit Fix 2 working tree** (`signal_compactor.py` pump-chain bear override) — separate commit
2b. **24h monitor:** SHORT trade count (target: >5/day in SHORT_BIAS), continuum-trend- executions, pump-chain bear-bypass win rate
3. **Fix 3 (VEL-FILTER)** — implement bear-gated exemption after Fix 2 is clean 24h
4. **Fix 5** — narrow RSI 65–75 bear exemption, 48h kill rule WR<40% @ 5T
5. **Fix 6** — delegate audit to bug_hunter (read-only inventory of SHORT-only gates)
6. **Fix 4** — document precedence in constants comment: HARD_FLOOR(25) > PRESERVE-SPIKE(30) > FLOOR-OVERRIDE(30–40 bear) > CEILING(65)
7. **Separate issue (not this plan):** SHORT exit quality — hard_sl dominant, profit-monster-trail 9T -$0.24 (winners not paying). Delegate to signal_analyst after gates unblocked.

**Standing rule unchanged:** CONFLUENCE_REQUIRED, LIVE_TRADING_ENABLED, CEO_PROTECTED_FLAGS untouched.
