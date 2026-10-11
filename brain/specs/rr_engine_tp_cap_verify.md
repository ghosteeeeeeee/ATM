# RR Engine — TP Cap ATR Scaling Fix Verification

**Date:** 2026-10-11
**Verifier:** bug_hunter
**Commit under test:** `2669cd78` — "fix: TP cap scales with ATR — R:R < 1 by construction bug"
**Files:** `scripts/risk_reward_engine.py` (`_get_tp_max_pct`, line 458; call site, line 541), `scripts/hermes_constants.py` (`RR_ENGINE_TP_ATR_SCALING = 1.5`, line 3734)

## Verdict: PASS (fix verified) — 2 adjacent findings flagged, neither is a regression of this fix

---

## Check 1: TP cap scaling math — PASS

`_get_tp_max_pct(regime, atr_pct)` returns `max(regime_cap, atr_pct × 1.5 / 100)` when `atr_pct > 0`.

EXTREME regime sweep (task's exact test):

| ATR | TP cap | R:R cap (vs SL = ATR×1.0) |
|-----|--------|---------------------------|
| 0.5% | 2.00% | 4.00 |
| 1.0% | 2.00% | 2.00 |
| 1.5% | 2.25% | 1.50 |
| 2.0% | 3.00% | 1.50 |
| 3.0% | 4.50% | 1.50 |
| 4.0% | 6.00% | 1.50 |
| 5.0% | 7.50% | 1.50 |
| 6.0% | 9.00% | 1.50 |

Strict sweep with correct regime per ATR **and** the SL floor (`ATR_SL_MIN = 1.3%`) over ATR 1.0–6.0 in 0.1% steps: **worst-case R:R cap = 1.500** (values printing as 1.49999… are float epsilon; all round to 1.500). R:R ≥ 1.5 by construction holds for the ATR-fallback TP path at all ATR ≥ 1.0%.

Crossover math checks out: at ATR = 1.333%, ATR × 1.5 = 2.0% = HIGH/EXTREME regime cap exactly; above that the scaled cap dominates, below it the regime cap dominates and still yields ≥ 1.5 (e.g., ATR 1.0%: SL floor 1.3%, cap 2.0% → 1.54).

**Caveat (by design, not a bug):** the ≥ 1.5 guarantee covers the TP-cap/ATR-fallback path. When a structural S/R target exists, TP = nearest target (0.5%–tp_max), so R:R can legitimately be lower if the nearest target is genuinely close (verified: CHIP-like, support 0.8% below entry, ATR 3.58% → TP 0.8%, R:R 0.22, `tp_src=CANDLE`). Those cases are caught by the regime `rr_min` gate (2.0 EXTREME), not the cap — correct behavior.

## Check 2: Call site passes atr_pct — PASS

`risk_reward_engine.py:541`: `tp_max = _get_tp_max_pct(regime, atr_pct)` — confirmed in source and in the fix diff. Grep over the whole repo shows exactly one definition (line 458) and one call site (line 541); no stale single-arg callers anywhere.

## Check 3: No regression on low-ATR tokens — PASS

For ATR where `ATR × 1.5 < regime_cap`, the function returns the regime cap unchanged (scaling is a `max()`, purely widening):

- FLAT 0.30%/0.40% → 3.00% cap (scaled would be 0.45%/0.60%)
- NORMAL 0.50%/0.90%/0.99% → 2.50% cap
- HIGH 1.20% → 2.00% cap

Live: SOL (ATR 0.73%, NORMAL) → cap 2.5%, R:R 1.13; ETH (ATR 0.48%, NORMAL) → cap 2.5%; BTC (ATR 0.31%, FLAT) → cap 3.0%. Behavior identical to pre-fix for these tokens.

## Check 4: Real tokens — PASS

Live run of `evaluate_rr(token, 'SHORT', px)` (data as of 2026-10-11):

| Token | ATR | Regime | R:R | Grade | TP source | SL% | TP% |
|-------|-----|--------|-----|-------|-----------|-----|-----|
| BLUR | 0.86% | NORMAL | 1.33 | C | ATR | 1.30 | 1.73 |
| AR | 1.46% | HIGH | **1.50** | C | ATR | 1.46 | 2.19 |
| ARB | 1.71% | EXTREME | **1.50** | C | ATR | 1.71 | 2.56 |
| CHIP | 3.58% | EXTREME | **1.50** | C | ATR | 3.58 | 5.38 |
| BTC | 0.31% | FLAT | 0.48 | D | ATR | 1.30 | 0.62 |
| ETH | 0.48% | NORMAL | 3.68 | A | ATR | 0.26 | 0.96 |

All high-ATR tokens (AR, ARB, CHIP) land exactly at R:R = 1.50 — previously CHIP (ATR 3.58%) would have computed 2.0/3.58 = **0.56** and been blocked by construction. Fix works end-to-end through `evaluate_rr`.

Note: `pass=True` everywhere in this run is **shadow mode** (`RR_ENGINE_SHADOW=True`, `RR_ENGINE_FORCE=False` in hermes_constants.py:3713-3714). ARB/CHIP/BLUR/BTC show `block_reason` (would-block) but are not actually blocked yet. Also, live ATR is a moving number — BLUR/BTC were not high-ATR at test time.

## Check 5: atr_pct=None fallback — PASS

`_get_tp_max_pct('EXTREME', None)` → 2.00% (regime cap only). The guard `if atr_pct and atr_pct > 0` treats None as falsy → no scaling. Regime caps with None: FLAT 3.00%, NORMAL 2.50%, HIGH 2.00%, EXTREME 2.00% — all pre-fix values.

## Check 6: atr_pct=0 — PASS

`atr=0` and `atr=0.0` → falsy → regime cap (2.00% EXTREME / 2.50% NORMAL). No division exists in the function; explicit assert over `[None, 0, 0.0, -1]` shows no `inf`/`nan`. Negative ATR (`-1`) also falls through to regime cap (guard `atr_pct > 0`).

---

## Findings (adjacent, not regressions of this fix)

### Finding 1 — LOW: mirror-image degenerate R:R on very low-ATR tokens

The fix closed the R:R < 1 hole on the **high** end, but the **low** end has the same shape of problem: for ATR < ~0.65%, TP fallback (2 × ATR, floored only by `RR_ENGINE_TP_MIN_PCT = 0.5%`) is smaller than the SL floor (`ATR_SL_MIN = 1.3%`) → R:R < 1 by construction. Reproduced: ATR 0.31% → TP 0.62%, SL 1.30%, R:R 0.48 (this is exactly BTC in the live run). These tokens are blocked by `rr_min` (2.5 FLAT) anyway, so the trading outcome is arguably correct — but the mechanism is degenerate math, the same class of flaw that was just fixed. Suggested fix: give the ATR-fallback TP a floor of `SL × rr_min_floor` or skip evaluation (regime-skip) for ATR < 0.65% instead of emitting a fake R:R.

### Finding 2 — MEDIUM: structural SL adjustment bypasses the ATR_SL_MIN floor (and can *shrink* SL)

In `compute_structural_rr` (lines 516-538), the loop that "extends SL beyond structural levels" also matches levels **closer** to entry than the ATR-based SL, which *tightens* the SL below the empirically tuned 1.3% floor. Reproduced: SHORT at 2500, ATR 0.48%, resistance at 2506.5 (+0.26%) → SL shrank from 1.30% to 0.46%. Seen live on ETH: SL 0.26% vs ATR 0.48%, producing an inflated R:R 3.68 and Grade A. `ATR_SL_MIN` exists because 55% of below-entry SL hits had distance < 1.3% (brain_auditor Sep 14) — the structural path silently defeats it, and inflated R:R/score can push weak trades through the gate. Suggested fix: after the structural loop, enforce `sl_distance_pct = max(sl_distance_pct, ATR_SL_MIN)` (or `ATR_SL_MIN_EXTREME` in EXTREME), and only accept structural adjustments that *widen* SL.

### Observation (informational)

Engine is in shadow mode — none of these blocks are live yet. The `rr_min` thresholds (EXTREME 2.0, HIGH 1.3) are above the 1.5 construction floor, so when force mode is switched on, high-ATR tokens will pass the R:R math but still need score ≥ 50 to clear the gate.

## Test evidence

All four task-specified tests executed successfully from `/root/.hermes/scripts` (import OK; math sweep OK; real-token run OK; None/0 fallback OK), plus: strict regime sweep with SL floor (worst R:R = 1.500), low-ATR no-regression matrix, SOL live run, structural-target path check, whole-repo caller grep, and git diff review of commit `2669cd78`.
