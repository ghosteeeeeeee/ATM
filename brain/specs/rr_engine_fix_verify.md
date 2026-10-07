# RR Engine Fix Verification — Bug Hunt #2 Follow-Up

**Verifier:** bug_hunter (CEO delegation)
**Date:** 2026-09-30
**Scope:** Verify the 6 fixes from bug hunt #2 (BUG-1, 3, 4, 5, 7, 9). Not a new bug hunt — confirmation gate only.
**Method:** Code inspection of `scripts/entry_gates.py` + `scripts/risk_reward_engine.py`, plus functional tests (monkeypatched edge cases, synthetic S/R maps, forced legacy path) executed in `scripts/`.

## Verdict Summary

| Bug | Fix | Verdict |
|-----|-----|---------|
| BUG-1 | Legacy rr_gate fallback fail-open | ✅ **PASS** |
| BUG-3 | S/R cache key includes price bucket | ✅ **PASS** |
| BUG-4 | Absolute distance_pct at merge | ✅ **PASS** (distance) / ⚠️ **PARTIAL** (type recompute — see findings) |
| BUG-5 | Source-aware touches vs strength | ✅ **PASS** |
| BUG-7 | Fail-open detection rr>=999 | ✅ **PASS** |
| BUG-9 | BB zero-width `is not None` | ✅ **PASS** |

**Overall: 5 clean PASS + 1 PASS with residual gap. The fixes are correct as described and safe to consider complete for the core behaviors; one residual gap in BUG-4's type recompute and two latent issues are flagged below for follow-up.**

---

## BUG-1: Legacy rr_gate fallback can never pass — ✅ PASS

**Code evidence** (`entry_gates.py:171-177`):
```python
rr = tp_distance / sl_distance
if rr < ENTRY_RR_MIN_RATIO:
    # Legacy path can't reach its own threshold (ATR_SL_MIN ≈ ATR_TP_MIN → rr ≈ 1.0)
    # Don't block — fail-open. The RR engine is the primary gate.
    _log(f"RR LEGACY PASS: {token} {direction} rr={rr:.2f} < {ENTRY_RR_MIN_RATIO} (legacy can't reach threshold, fail-open)")
    return True, 0, 0, rr
```
Returns `True` (was `False` pre-fix).

**Functional evidence** (forced legacy path by setting `hermes_constants.RR_ENGINE_ENABLED = False` at runtime):
```
ATR_SL_MIN=0.013 ATR_TP_MIN=0.013
Implied legacy rr (no S/R TP): 1.000
Implied legacy rr (best S/R TP 2.5%): 1.923 < ENTRY_RR_MIN_RATIO=2.0
[entry-gates] RR LEGACY PASS: FAKECOIN_XYZ LONG rr=1.00 < 2.0 (legacy can't reach threshold, fail-open)
[entry-gates] RR LEGACY PASS: FAKECOIN_XYZ SHORT rr=1.00 < 2.0 (legacy can't reach threshold, fail-open)
Legacy LONG  pass=True sl=0 tp=0 rr=1.0
Legacy SHORT pass=True sl=0 tp=0 rr=1.0
```

**Key confirmation:** Even in the *best* case (S/R TP target at the 2.5% cap), legacy rr = 0.025/0.013 = **1.923 < 2.0** — the legacy path can mathematically *never* reach its own threshold with current constants. Pre-fix this path blocked 100% of fallback signals. Fail-open is the only viable behavior and it is now implemented. Pre-fix blocking behavior confirmed gone.

---

## BUG-3: S/R cache keyed by token only — ✅ PASS

**Code evidence** (`risk_reward_engine.py:247-253`):
```python
# Check cache — key includes price bucket so S/R distances stay fresh
cache_key = (token.upper(), round(price, 1))  # bucket to 0.1 to avoid cache thrash
if cache_key in _sr_cache:
    cached_ts, cached_map = _sr_cache[cache_key]
    if now - cached_ts < _CACHE_TTL:
        return list(cached_map)  # return copy to avoid cache corruption
```

**Functional evidence:**
```
BTC@80k: score=33.625 levels=18
BTC@90k: score=19.75 levels=18
Distinct maps: True
Scores differ: True
SR prices @80k: [83332.0, 83333.0, ...]
SR prices @90k: [85250.28, 83848.16, 83523.89, 83351.0, ...]
```
Different scores, different level sets, distinct map objects. (Synthetic prices sit far from live BTC ≈ 83367, which is why all levels are 4%+ away — expected for off-price evals, and exactly the scenario where the old token-only cache served stale maps.)

**Cache bucketing behavior verified:**
```
_CACHE_TTL = 300s
cache keys: [('BTC', 80000.0), ('BTC', 90000.0), ('BTC', 80000.1), ('BTC', 80001.5)]
80000 vs 90000 distinct lists: True
80000.05 → bucket ('BTC', 80000.1) — separate from 80000.0 (0.1 rounding works)
80001.5 → separate bucket: True
```
Stale window for any given price is now bounded by the 0.1-price bucket + 300s TTL, instead of serving a map built at a wildly different price for up to 300s. ✅

**⚠️ Latent issue found (LOW):** `return list(cached_map)` is a **shallow** copy — the level dicts are shared with the cache. Verified:
```
After mutating returned copy, cached value: -999 (orig was 0.02586...)
Same dict object shared with cache: True
```
No current caller mutates level dicts (compute_structural_rr / _compute_score / manage_exit / signal path are all read-only), so this is **not an active bug** — but any future caller that mutates a returned level will silently corrupt that (token, bucket) cache entry for up to 300s. Suggested hardening: `return [dict(l) for l in cached_map]`.

---

## BUG-4: Signed vs absolute distance_pct — ✅ PASS (distance) / ⚠️ PARTIAL (type)

**Code evidence** (`risk_reward_engine.py:218-239`):
```python
for level in candle_levels:
    level['distance_pct'] = abs(level['price'] - price) / price * 100 if price > 0 else 999
    level['type'] = 'resistance' if level['price'] > price else 'support'   # recomputed ✅
    ...
for level in liq_levels:
    level['type'] = level.get('type', '').lower()                            # NOT recomputed ⚠️
    level['distance_pct'] = abs(level['price'] - price) / price * 100 if price > 0 else 999
    ...
all_levels.sort(key=lambda x: x.get('distance_pct', 999))
```

**Functional evidence — distance_pct (the core fix):**
```
Levels: 18
All distances >= 0: True
Min distance: 4.1650%
Sample distances: [4.17, 4.17, 4.17, 4.17, 4.17, 4.17, 4.17, 4.17]
distance_pct matches abs formula vs 80000: True
```
Cross-checked **every** level: `distance_pct == abs(level_price - eval_price)/eval_price*100` exactly (1e-6 tolerance). Sorting by proximity is now sound. ORDER_BOOK levels that previously carried signed distances from the raw liquidation map (`liquidation_map.py` stores e.g. `-0.001` / `+0.001`) are normalized at merge time. ✅

**⚠️ Residual gap — type not recomputed for non-CANDLE levels:**
ORDER_BOOK/LIQUIDATION levels keep their scan-time `type` (computed by the liquidation map vs *its* scan price ≈ 83363 for BTC). Inspecting the merged map at eval price 80000:
```
83354.00  support      ORDER_BOOK   ← ABOVE 80000 but still 'support' (stale)
83363.00  support      ORDER_BOOK   ← ABOVE 80000 but still 'support' (stale)
83364.00  resistance   ORDER_BOOK   ← happens to be right at live price
83523.89  resistance   CANDLE       ← correctly recomputed ✅
83848.16  resistance   CANDLE       ← correctly recomputed ✅
Levels ABOVE 80000 NOT marked resistance: 9 (all ORDER_BOOK)
```
**Impact assessment (contained):**
- SL/TP targeting in `compute_structural_rr` compares `level_price` vs `price` directly — **does not use `type`** → SL/TP prices unaffected.
- `compute_liquidity_proximity` also uses price comparison → unaffected.
- Only `_compute_score`'s S/R-clarity component filters by `type` (line 641-643) → score can be distorted *only when eval price drifts from the liq-map scan price* (fast moves, or off-price evals). At live prices (83367 vs scan 83363) the discrepancy is negligible; in the synthetic test it's 9 mislabeled levels.
- The fix description says "type is recomputed vs eval price" — it is, for CANDLE levels only.

**Suggested follow-up (one line, low risk):** in the `liq_levels` loop, replace the bare lowercase with:
```python
level['type'] = 'resistance' if level['price'] > price else 'support'
```
(Semantically correct for all sources: below-eval-price = support.)

---

## BUG-5: touches vs strength conflation — ✅ PASS

**Code evidence** (`risk_reward_engine.py:504-515`):
```python
for level in sr_map:
    level_price = level['price']
    # Only apply touches filter to candle levels; book/liq levels use different semantics
    if level.get('source') == 'CANDLE':
        level_touches = level.get('touches', 0)
        if level_touches < 5:
            continue  # weak candle level, don't adjust
    else:
        # Book/liq levels: skip if strength is negligible
        strength = level.get('strength', level.get('total_size', 0))
        if strength <= 0:
            continue
```
Branches on `level.get('source')` exactly as specified. ✅

**Functional evidence** (synthetic sr_map, LONG @ 100.0, ATR 1.0% → baseline SL 98.7; structural level at 99.2 sits between entry and SL):
```
No relevant level baseline SL: 98.7
CANDLE touches=2 SL:     98.7  (weak candle level skipped ✅)
CANDLE touches=5 SL:     99.0  (extended below level ✅)
LIQUIDATION strength=1 SL: 99.0  (extended ✅ — pre-fix this was SKIPPED because 1 < 5)
LIQUIDATION strength=0 SL: 98.7  (negligible strength skipped ✅)
ORDER_BOOK strength=307 SL: 99.0  (included via strength>0 ✅)
Branches on level source: True
```
The pre-fix bug had two faces, both resolved:
1. Tiny-but-real book/liq levels (strength=1) were wrongly skipped by the touches>=5 filter → now included.
2. Order-book strength (307) was semantically treated as "307 touches" → semantics now separated per source.

---

## BUG-7: Fail-open detection fragile — ✅ PASS

**Code evidence** (`risk_reward_engine.py:957-966`):
```python
# Fail-open detection: engine couldn't evaluate → return neutral
# Covers both _result() signature (rr=999, score=0) and structural path (rr=999, any score)
if rr >= 999:
    return 1.0, "RR FAIL-OPEN: engine could not evaluate (no data)"

# Hard block conditions
if grade == 'F':
    return 0.0, f"RR HARD BLOCK: grade=F (score={score})"
if rr < getattr(hc, 'RR_ENGINE_CONF_HARD_BLOCK_RR', 0.70):
```
`rr >= 999` caught regardless of score. Hard-block threshold synced to constant: `hermes_constants.py:3653` → `RR_ENGINE_CONF_HARD_BLOCK_RR = 0.70`, used via `getattr` (was previously hardcoded inline). ✅

**Functional evidence** (monkeypatched `evaluate_rr` to inject exact result shapes):
```
Fail-open result: rr=999 score=0 grade=A
Forced fail-open rr=999 score=62: mult=1.0x reason=RR FAIL-OPEN: engine could not evaluate (no data)
Forced fail-open rr=999 score=0:  mult=1.0x reason=RR FAIL-OPEN: engine could not evaluate (no data)
Real rr=5.0 grade A:              mult=1.3x reason=RR BOOST: R:R=5.00 grade=A (exceptional)
```
- The critical BUG-7 scenario — **rr=999 with score≠0** (structural path: `compute_structural_rr` line 572 sets `rr_ratio = 999` when `sl_distance_pct <= 0`, while the score is still computed normally) — now returns **1.0x**. Pre-fix this fell through to the graded curve: rr=999 ≥ 4.0 with grade A → **1.30x boost**, or grade B → 1.15x. Bug confirmed fixed.
- rr=999 score=0 (the `_result()` fail-open shape) also 1.0x.
- Real boost path intact (rr=5.0 grade A → 1.30x), so the fix didn't disable the multiplier curve.

**Note on FAKECOIN test:** `mult=0.0x reason=RR HARD BLOCK: grade=F (score=26.375)` — this is **not** a fail-open path and **not** a bug. With no candle/book data, the engine still evaluates via ATR fallback (rr=1.15, empty sr_map → score 26.4 → grade F) and grade F legitimately hard-blocks per design. See sideways finding #4 for a related design question.

**Downstream consumer confirmed:** `signal_compactor.py:1799/1828` calls `rr_confidence_multiplier()` — so this fix directly prevents fail-open results from inflating live signal confidence. ✅

---

## BUG-9: BB zero-width falsy — ✅ PASS

**Code evidence** (`risk_reward_engine.py:345-361`) — all three sites use `is not None`:
```python
bb_squeeze = bb_width is not None and bb_width < squeeze_thresh      # line 346
if bb_width is not None:
    bb_score = min(1.0, bb_width / 0.08)
else:
    bb_score = 0.3  # no BB data — neutral
...
'bb_width': round(bb_width, 4) if bb_width is not None else None,   # lines 360-361
```
No truthiness checks on bb_width remain in `compute_vol_width`. ✅

**Functional evidence:**
```
ETH BB width: 0.005 (type=float)   Is None: False   Is 0.0: False
Flat BB width from _compute_bb_width: 0.0 (position=0.5)
FLATTOKEN bb_width=0.0 atr_pct=0.75 energy=0.225
Expected energy if fixed: 0.225 | if bug present: 0.345
```
The decisive test: monkeypatched candles to be perfectly flat (all closes = 100.0) → `_compute_bb_width` returns **exactly 0.0**. `compute_vol_width` then produced `bb_width=0.0` and `energy_score=0.225`:
- Fixed formula: `0.6 × atr_score(0.375) + 0.4 × bb_score(0.0/0.08=0.0) = 0.225` ✅ **matches**
- Buggy formula (0.0 falsy → None → 0.3 bonus): `0.6 × 0.375 + 0.4 × 0.3 = 0.345` ❌ does not match
Zero-width squeeze now correctly scores 0 energy contribution instead of receiving the neutral 0.3 data-missing bonus. ✅

---

## Cross-Cutting Regression Tests

**Test 1 — Imports:** `OK` ✅ (`evaluate_rr`, `rr_confidence_multiplier`, `rr_gate` all import cleanly)

**Test 6 — Direction correctness:**
```
LONG SL < entry: True (SL=78960.00)     LONG TP > entry: True (TP=80800.00)
SHORT SL > entry: True (SL=81040.00)    SHORT TP < entry: True (TP=79358.56)
```
✅ No direction inversion.

**Test 7 — Multiplier curve with live prices** (`signal_schema.get_all_latest_prices()`):
```
BTC LONG @ 83367.5:  mult=1.0x  — RR NEUTRAL: R:R=2.38 grade=C (standard)
ETH LONG @ 2572.55:  mult=1.15x — RR BOOST: R:R=4.61 grade=B (strong)
SOL LONG @ 116.145:  mult=1.0x  — RR NEUTRAL: R:R=2.04 grade=D (standard)
DOGE LONG @ 0.08884: mult=1.15x — RR BOOST: R:R=4.50 grade=B (strong)
```
✅ Curve behaves per documented logic at real prices. (SOL grade D → 1.0x is correct: only grade **F** hard-blocks; rr=2.04 ≥ 2.0 → neutral.) Real evaluations also confirm the engine reaches real S/R levels (BTC TP via CANDLE at 83848) and that shadow mode logged the would-be block for SOL score 49.5 < 50 without actually blocking.

---

## Sideways Findings (flagged per AGENTS.md "see something, say something")

1. **LOW-MEDIUM — BUG-4 residual:** `_merge_sr_maps` does not recompute `type` for ORDER_BOOK/LIQUIDATION levels (only lowercases). Score-component distortion only when eval price drifts from liq-map scan price. Fix: one-line recompute in the liq loop (see BUG-4 section).

2. **LOW — Same conflation still in `manage_exit()`:** `risk_reward_engine.py:1059` — `level_touches = level.get('touches', level.get('strength', 0))` is the exact pattern BUG-5 fixed in `compute_structural_rr`. Here it only feeds the log/reason string (`touches=307` for book levels) — exit *logic* uses `level_price` only, so no behavioral bug. Suggest applying the same source-aware treatment for consistency and clean logs.

3. **INFO — Raw signed distance_pct dependency in exit Rule 4:** `risk_reward_engine.py:1157` — `cluster.get('distance_pct', 999)  # signed!` reads **raw** cluster data (not the merged map) and deliberately uses the sign to detect the dangerous direction (`LONG` + dist<0). This is correct today and already commented, but fragile: if anyone "normalizes" raw cluster `distance_pct` to absolute (spillover from the BUG-4 cleanup), LONG liquidation-zone exits silently stop firing. Worth an explicit guard/assert or a test pinning the signed semantics.

4. **INFO — No-data tokens get confidence zeroed, not neutralized:** `FAKECOIN_XYZ` with no market data → engine evaluates via ATR fallback → grade F → `rr_confidence_multiplier` returns **0.0x** (hard block), even though `evaluate_rr`'s own `pass` stays True under shadow mode. Is zeroing confidence on tokens with zero S/R data intended? Arguably fail-open philosophy would return 1.0x (neutral) when the score is driven entirely by missing data (empty sr_map → S/R clarity = 0 pts → near-guaranteed F). Product decision needed — not a regression from these fixes.

5. **INFO — Stale comment:** `risk_reward_engine.py:55` — `_sr_cache = {}  # token -> (timestamp, sr_map)` no longer describes the key (now `(token, price_bucket)`). Trivial doc drift.

6. **INFO — Deployment state (not a bug):** `RR_ENGINE_SHADOW=True`, `RR_ENGINE_FORCE=False` in `hermes_constants.py:3602-3603`. All "SHADOW BLOCK" lines in test output are log-only — the RR engine is **not actually blocking** anything in production until FORCE is flipped. The fixes are verified at engine level; the gate itself remains in observation mode by design.

---

## Conclusion

All 6 fixes are correctly implemented and functionally verified. BUG-1, 3, 5, 7, 9 pass cleanly on both code inspection and behavioral tests. BUG-4's core guarantee — absolute, sort-safe `distance_pct` for every level — is fully verified; the "type recomputed vs eval price" half of that fix covers CANDLE levels only, with contained impact (score component only, only on price drift). No fix introduced a regression in direction correctness, the confidence multiplier curve, or imports.

**Gate status: ✅ APPROVED** — fixes considered complete, with finding #1 (liq-level type recompute) recommended as a small follow-up, and #2–#6 logged for awareness.
