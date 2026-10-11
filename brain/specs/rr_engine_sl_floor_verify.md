# RR Engine SL Floor Clamp — Verification Report

**Date:** 2026-10-09
**Verifier:** bug_hunter
**Commit under test:** `8ab8a986` — "fix: clamp SL to ATR_SL_MIN after structural extension loop"
**File:** `scripts/risk_reward_engine.py` — `compute_structural_rr()` (line 494)
**Constants:** `ATR_SL_MIN = 0.013` (decimal, = 1.3%) — `hermes_constants.py:686`

**Overall verdict: PASS (6/6 checks). One test premise corrected (Check 5), one minor sideways finding.**

---

## Check 1 — Clamp exists and is correctly placed — PASS

- SL extension loop: lines 516–538
- Clamp: lines 540–547 — **after** the loop, **before** TP calculation (starts line 549)

```python
# Clamp SL to minimum floor — structural loop can shrink SL below ATR_SL_MIN
sl_floor = getattr(hc, 'ATR_SL_MIN', 0.015)
if sl_distance_pct < sl_floor:
    sl_distance_pct = sl_floor
    if direction == 'LONG':
        sl_price = price - (price * sl_distance_pct)
    else:
        sl_price = price + (price * sl_distance_pct)
```

The clamp correctly recomputes `sl_price` for **both** directions and only fires when
`sl_distance_pct < floor` — it can never shrink a legitimate extension. The returned dict
rounds `sl_distance_pct * 100` to percent, so units are consistent end-to-end.

## Check 2 — ETH case (was SL=0.26%, R:R=3.68, Grade A) — PASS

```
ETH LONG: SL=1.30% R:R=0.98 Grade=D
  SL >= 1.3%: True
  R:R < 4.0 (not inflated): True
[rr-engine] SHADOW BLOCK ETH LONG $2500.0000: R:R 0.98 < 2.5 minimum for FLAT regime
```

The fake high-quality setup is gone. SL is at the 1.30% floor, R:R=0.98 (not 3.68),
Grade D (not A), and the engine now **correctly SHADOW BLOCKS** the trade
(R:R 0.98 < 2.5 FLAT-regime minimum). Root-cause bug is fixed.

## Check 3 — Normal tokens, both directions — PASS (8/8 floor_ok=True)

| Token | Dir | SL% | R:R | Grade | floor_ok |
|-------|-----|-----|-----|-------|----------|
| BTC $80000 | LONG  | 1.30 | 0.77 | F | ✅ |
| BTC $80000 | SHORT | 1.30 | 0.48 | D | ✅ |
| ETH $2500  | LONG  | 1.30 | 0.98 | D | ✅ |
| ETH $2500  | SHORT | 1.30 | 0.72 | D | ✅ |
| SOL $100   | LONG  | 1.30 | 1.13 | F | ✅ |
| SOL $100   | SHORT | 1.30 | 1.13 | C | ✅ |
| BLUR $0.018| LONG  | 1.30 | 1.33 | F | ✅ |
| BLUR $0.018| SHORT | 1.30 | 1.33 | C | ✅ |

No token/direction combination produced SL < 1.3%.

## Check 4 — SHORT direction clamp — PASS

Synthetic: price=100 SHORT, resistance at 100.5 (between entry and initial SL@101.3).
Without the clamp, the loop sets SL = 100.5 + buffer = 100.7 → 0.70% (shrinkage).
With the clamp:

```
SHORT shrinkage res@100.5: SL=1.30% sl_price=101.3 (floor ok: True)
```

Clamp fires and recomputes `sl_price` above entry correctly. Live SHORT legs in
Check 3 also all ≥ 1.3%.

## Check 5 — Legitimate extensions are NOT clamped — PASS (test premise corrected)

⚠️ **The test as specified is based on a wrong premise.** The loop condition is
`price > level_price > sl_price` (LONG) — it only matches structural levels **between
entry and the current SL**. A support *far below* the initial SL is **never matched**,
so nothing extends to it — with or without the clamp. Proven by simulation with the
floor disabled entirely (removes both pre-loop min and post-loop clamp):

```
No-floor sim, level@96: SL=1.00%   ← ATR value only; loop never matched the level
```

The task's "Extension preserved: False" output is a **bad test expectation, not a bug** —
the clamp is a no-op here (SL never changed from its ATR/floor value).

The **true** extension-preserved case — a level just above the floor SL where the loop
extends SL *deeper* than the floor — verified working:

```
Legit extension level@98.75: SL=1.45% (>1.30% = clamp no-op, extension preserved)
```

**Clamp semantics confirmed correct:** it only raises `sl_distance_pct` when below the
floor; any extension that lands above the floor passes through untouched.

## Check 6 — No structural levels: clamp is safe — PASS

```
No levels (ATR=1.0%):        SL=1.30%  ← pre-loop max() at line 508 already applied the floor; post-loop clamp no-op
No levels high ATR (2.5%):   SL=2.50%  ← clamp strictly a no-op, value untouched
```

With an empty `sr_map` the loop body never executes, so `sl_distance_pct` is already
≥ floor from the pre-existing `max()` at line 508. The post-loop clamp adds nothing
and changes nothing. (Note: with the floor in place, the `sl_distance_pct <= 0 →
rr_ratio = 999` fail-open at line 592–593 is now unreachable dead code — harmless.)

---

## Extra: root-cause mechanism confirmed

The original ETH shrinkage came from the loop's **last-match-wins** behavior on
unsorted `sr_map`: each iteration compares against the *updated* `sl_price`, so a
nearer level processed after a farther one pulls the SL back toward entry (99.5 →
extends to 99.3, then 99.9 → extends to 99.7 = 0.3%... down to ETH's 0.26%).
Multi-level synthetic reproduces the mechanism and the clamp catches it:

```
Multi-level shrinkage (99.5 then 99.9): SL=1.30%  ✅
```

## Sideways finding (minor)

`'sl_source': 'ATR'` is hardcoded at line 603 in the returned dict — even when the
structural loop extended the SL. `tp_source` is tracked properly; `sl_source` is a
misleading label for dashboards/audits. **Severity: cosmetic/observability. Suggested
fix:** set `sl_source = 'STRUCTURAL'` when the loop modifies `sl_price`, else `'ATR'`.
Not fixed here (out of scope for this verification).

## Evidence basis

Every number above comes from code actually executed in this session
(`evaluate_rr`, `compute_structural_rr`, monkeypatched `hc.ATR_SL_MIN` for the
pre-fix simulation). No values from memory or estimation.
