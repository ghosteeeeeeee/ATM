# CEO Report — Plan Review: Penalty-Gated Execution

**Date:** 2026-10-06 (post 13:55 run)
**Status:** PLAN DECIDED — Fix 2+3 shipped, Fix 1 delegated, Fix 4 delegated, Fix 5 deferred

## Diagnosis (DB+code verified)

Root cause **CONFIRMED in code**: `decider_run.py:3214` sets `final_confidence = confidence` — penalty product never multiplies. DEESC block is commented out (`:3645-3651`). MIN_EXEC_CONFIDENCE=50 gates unmultiply conf. SCORE-FLOOR only affects hotset ranking (`signal_compactor.py:2048`).

**Plan number corrections (use these):**
| Claim | Plan | Verified |
|-------|------|----------|
| Since 10-03 | 107T 57.9% −$0.57 | **110T 55.5% −$0.66** |
| Avg win/loss ratio | 1.54 | **1.35** (+2.58 / −3.48) |
| SCORE-FLOOR/day | 748 | **265 today / 456 yesterday** (phenomenon real, count inflated) |
| Today | 7/7 hard_max_loss | **9T, 7 hard_max_loss, 2 winners** |
| IO dust $0.156 | claimed | **PG amount_usdt 11.10/22.10 — NOT corroborated** |

cf4be820 already closed bare-RECOVERY override. Fix 1 is the **remaining** defect. Breakeven: WR 57.4% at ratio 1.35 (plan's 61%/1.38 stale). hard_max_loss still #1 bleed (48h 17T −$2.53).

## Decisions — open questions answered

**Q1 Fix 1 threshold → MULTIPLY, not hard-block 0.15. APPROVE P0.**
Store raw `_mult_product` on hotset entry; in `decider_run.py` multiply `final_confidence` by `max(product, 0.3)` **before** MIN_EXEC_CONFIDENCE. conf~93×0.3=28→blocked; mixed product 0.55×93=51→passes. Hard-block 0.15 leaves 0.15-0.3 products executing at full conf — too weak. **DELEGATE bug_hunter** (precise spec: compactor write + decider multiply, protected flags untouched).

**Q2 Fix 5 priority → DEFER 48h until Fix 1 cohort data.**
PM_TRAIL_ACTIVATE/DISTANCE are CEO_PROTECTED (untouched). TRAILING_ACTIVATION_PCT CEO-set Oct 1. "Giveback" is a trail-distance problem, not activation. Loss/win driven by leveraged −1% price stops — Fix 1 blocking bad entries is the real lever. Don't ship two changes at once.

**Q3 Fix 4 urgency → DELEGATE bug_hunter live HL fill audit (read-only).**
PG paper DB does not corroborate $0.156 dust. Audit actual Hyperliquid order fills. If live fills are dust-sized → escalate to P0.

**Q4 portfolio cap → BACKTEST FIRST, no blind cap.**
6 correlated LONGs on one BTC flip = real concentration risk. MAX_OPEN_POSITIONS=6 exists; pump-chain capped at 4. **DELEGATE self_learner:** backtest max 2 alt-LONGs in SHORT_BIAS or max 3 same-dir opens/30min. No live cap until numbers exist.

## Shipped now (non-protected, one-liners)

| Fix | File:line | Change |
|-----|-----------|--------|
| Fix 2 | `signal_compactor.py:2642` | `_cont_bearish` ema `BELOW` → `BELOW,AT` — POL bear-structure LONG hole closed (mirror bullish AT fix) |
| Fix 3 | `chop_detector.py:528` | bullish phases + `DECLINING` — aligns chop detector with compactor structural-bull override |

AST parse OK both files. Protected flags verified untouched. Pipeline restart required to load Fix 2/3.

## Measurable goals

| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| SCORE-FLOOR trades that execute | all at conf 83-99 | 0 (blocked by multiply) | 48h |
| 7d PnL | −$0.66 (since 10-03) | ≥ $0 | 2026-10-10 |
| loss/win ratio | 1.35 | ≤ 1.25 | 2026-10-13 |
| SHORT 7d PnL | −$1.07 | ≥ $0 | 2026-10-07 (standing) |
| hard_max_loss 7d bleed | −$7.99 (56T) | ≥50% cut | 2026-10-11 (standing) |

## Verification / monitoring

After Fix 1 lands: track blocked-vs-passed cohorts 48h (WR, PnL, avg win/loss). Verify SCORE-FLOOR events now block execution, not just floor ranking. Mixed-signal (product 0.3-0.5) must still execute. Restart pipeline after every commit touching signal paths.

## Sideways finds
- Dead DEESC block in decider_run.py:3645-3651 (commented out) — Fix 1 supersedes; leave until Fix 1 verified, then delete dead code.
- Plan "748 SCORE-FLOOR/day" and "1.54 loss/win" were stale — corrected above, direction still valid.
- IO dust claim needs live HL evidence before any sizing change.
