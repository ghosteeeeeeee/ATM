# R:R Engine Bug Hunt #2 — Risk-Reward Engine Audit

**Auditor:** bug_hunter
**Date:** 2026-10-05
**Scope:** `risk_reward_engine.py` (full), `entry_gates.py` rr_gate integration, `signal_compactor.py` rr_mult integration, RR_ENGINE constants in `hermes_constants.py`

**Note on file locations given in the task:**
- RR_ENGINE constants are at `hermes_constants.py:3601–3674`, **not** lines 3085–3130 (that range covers Confluence Gate / Dead Hours).
- signal_compactor rr_mult integration is at **lines 1783–1829**, not 990–1030 (that range is the z-score accel penalty).

**Production state relevant to all findings:**
- `RR_ENGINE_ENABLED=True`, `RR_ENGINE_SHADOW=True`, `RR_ENGINE_FORCE=False` → the engine's regime/score gate **never blocks** in production (shadow override at `risk_reward_engine.py:740–747`).
- `RR_ENGINE_CONF_ENABLED=True`, `RR_ENGINE_CONF_SHADOW=False` → the confidence **multiplier is live** — it is currently the engine's only real enforcement.
- The 5 signal files that call `rr_gate` (breakout_pullback, volume_climax, warrior_sr_confirm, engulfing, wall_street_cycle) **discard** the returned sl/tp — they use only the pass boolean (`add_signal()` takes no sl/tp). Engine SL/TP currently affects no trade via those paths.

---

## Test Results (all 5 required tests executed)

| Test | Result |
|------|--------|
| 1. Imports | ✅ OK |
| 2. Edge cases | Zero/negative price → `pass=False` ✅. FAKECOIN: rr=1.15, score=26.375, grade=F (ATR fallback 0.75% NORMAL, SL 1.3%, TP 1.5%) |
| 3. Regime thresholds | FLAT 2.5, NORMAL 2.0, HIGH 1.3, EXTREME 2.0, hard-block 0.70 — match constants |
| 4. Direction | All 4 assertions True — SL/TP placement correct both directions |
| 5. Multiplier curve | ETH 0.85x mediocre, BTC 0.70x poor (rr=0.77 > 0.70 hard block), SOL 0.70x poor, DOGE 1.00x neutral |

Additional probes run: multiplier-branch monkeypatch (14 synthetic cases), cache-staleness probe (BTC 80000→90000), `_compute_score` synthetic maps (5 cases), `compute_structural_rr` synthetic maps (6 cases), BB zero-width, legacy-gate always-block proof, dead-constant greps.

---

## Bugs Found

### BUG-1 — Legacy rr_gate fallback can mathematically NEVER pass (HIGH)
**File:** `entry_gates.py:146–175`
**What:** When the engine path is unavailable (ImportError) or raises (line 142), rr_gate falls back to the legacy ATR-based calculation. With current constants (`ATR_SL_MIN=0.013`, `ATR_TP_MIN=0.013`, `ENTRY_RR_MIN_RATIO=2.0`):
- ATR fallback path: rr = 0.013/0.013 = **1.00 < 2.0 → always blocked**
- S/R path: sr_dist is capped at `tp_max = price * 0.025` (line 162, hardcoded 2.5%), so max rr = 0.025/0.013 = **1.923 < 2.0 → always blocked**

Proven empirically with close-based swings at exactly the 2.5% cap: `pass=False, rr=1.9231`.
**Impact:** Wrong behavior — opposite of fail-open. Any runtime exception in the engine (not ImportError) silently converts to "block ALL rr_gate signals" → signal drought. Setting `RR_ENGINE_ENABLED=False` also blocks everything.
**Severity:** HIGH
**Fix:** Raise `tp_max` above `ENTRY_RR_MIN_RATIO × ATR_SL_MIN` (e.g., 2.6%+), or lower `ENTRY_RR_MIN_RATIO` for the legacy path, or make the legacy path fail-open (return True) instead of blocking when it can't reach its own threshold. Also move the hardcoded `0.025` to `hermes_constants.py`.

---

### BUG-2 — Regime minimums are non-enforcing in production; multiplier ignores them (HIGH)
**File:** `risk_reward_engine.py:740–747` (shadow override); `risk_reward_engine.py:962–976` (hardcoded curve)
**What:** `RR_ENGINE_SHADOW=True` forces `passed=True` on every would-be block, so the regime minimums (FLAT 2.5, NORMAL 2.0, HIGH 1.3, EXTREME 2.0) suppress nothing. The only live enforcement is `rr_confidence_multiplier`, whose curve uses **hardcoded** thresholds (3.0/2.0/1.5) that are **not regime-adjusted**. Example inconsistency: a HIGH-regime setup with rr=1.4 passes the engine min (1.3) but gets "poor" 0.70x; a FLAT setup with rr=2.2 fails the FLAT min (2.5) but gets neutral 1.0x.
**Impact:** Wrong behavior — the entire regime-threshold logic (check category 2) has zero production effect; R:R quality is judged by a flat curve that contradicts the regime design.
**Severity:** HIGH (behavioral/config, but critical to know before trusting any "engine is gating" claim)
**Fix:** Either flip `RR_ENGINE_SHADOW=False` + `RR_ENGINE_FORCE=True` once validated, or make `rr_confidence_multiplier` consult `_get_rr_min(regime)` so the live path honors regime thresholds. Move the 3.0/2.0/1.5 curve values into `hermes_constants.py` (convention: no hardcoded constants).

---

### BUG-3 — S/R cache keyed by token only — stale maps for up to 300s (HIGH)
**File:** `risk_reward_engine.py:241–247` (`build_sr_map` cache), `:267`
**What:** `_sr_cache` is keyed by `token.upper()` only. It ignores: (a) the evaluation price, (b) caller-provided `candles_5m`, (c) cluster-file updates. Probe: `evaluate_rr('BTC','LONG',80000)` then `evaluate_rr('BTC','LONG',90000)` (12.5% move, within TTL) returned the **identical list object** — `r1['sr_map'] is r2['sr_map'] == True`. Levels at ~83436 carried `distance_pct≈-0.01` while true distance from 90000 was 7.3%. Score changed 40.6→26.6 on stale clarity data.
**Impact:** Wrong behavior — `_compute_score` S/R clarity (category 5) consumes stale `distance_pct`; `rr_structural.py:202–226` gates real signals on `grade/score` computed from these maps. Distances and level types reflect the price at first evaluation, not the current one.
**Severity:** HIGH (score correctness + signal firing)
**Fix:** Include a price bucket (or exact price) in the cache key, accept caller-provided candles as a cache-busting input, and/or invalidate on liquidation_clusters.json mtime. Minimum viable: key = `(token, round(price, 4) bucket)`.

---

### BUG-4 — Signed vs absolute `distance_pct` mixed in one sorted map (MEDIUM-HIGH)
**Files:** `risk_reward_engine.py:225–231` (`_merge_sr_maps` sort), `:135–155` (candle levels absolute), `liquidation_map.py:682–685` (book levels carry **signed** distance_pct from the order-book snapshot)
**What:** Candle levels store `distance_pct = abs(...)` vs candle close; ORDER_BOOK levels (`get_sr_levels`) carry **signed** `distance_pct` vs the snapshot price; liquidation levels store absolute vs the cluster snapshot. `_merge_sr_maps` sorts all by `distance_pct` → negative signed values sort first → the merged map is **not ordered by true proximity**. Probe confirmed: at eval price 90000, the map head showed 83436-levels with `distance_pct=-0.01`.
Consequences:
- `_compute_score` (line 630) takes `target_levels[0]` — for SHORT, probe showed score 49 (grade D) instead of 62 (grade C): a signed -2.0 support hits the `<0.3 → 12 pts "too close"` branch instead of the 25-pt sweet spot. **13-point swing across the `MIN_SCORE=50` boundary.**
- Level `type` is assigned vs `candles_5m[-1]['close']` (lines 132–148), not the eval price — types can be on the wrong side when signal price ≠ last close.
- TP selection itself is safe (recomputes `abs(level_price - price)` and filters by price comparison, lines 523–542).
**Impact:** Wrong behavior — S/R clarity score distorted, most severely for SHORT; feeds `rr_structural` gating.
**Severity:** MEDIUM-HIGH
**Fix:** Normalize all `distance_pct` to absolute-vs-eval-price at merge time (`_merge_sr_maps` should recompute `abs(level['price'] - price) / price * 100` for every level), and assign `type` vs the eval price, not the candle close.

---

### BUG-5 — `touches` vs `strength` conflation in SL extension (MEDIUM)
**Files:** `risk_reward_engine.py:497` (compute_structural_rr), `:1043` (manage_exit)
**What:** `level_touches = level.get('touches', level.get('strength', 0))` treats order-book `strength` (hundreds, e.g. 307.6) and liquidation `total_size` (millions) as if they were swing-touch counts. The `level_touches < 5 → skip` filter (line 498) is therefore meaningless for non-candle sources: probe confirmed a **single** ORDER_BOOK wall (strength 307.6) extends the SL, while candle levels legitimately need 5 clustered swing touches.
**Impact:** Wrong behavior — SL placed/extended based on single order-book walls or one large liquidation cluster, defeating the "strong structural level" intent.
**Severity:** MEDIUM
**Fix:** Only apply the touches≥5 filter to `source == 'CANDLE'` levels (use `touches`); for book/liquidation levels use their own strength semantics with a separate, documented threshold — or require touches for all and treat strength separately.

---

### BUG-6 — `RR_ENGINE_SR_CLUSTER_ATR` is not ATR-scaled; `atr_pct` param dead (MEDIUM)
**File:** `risk_reward_engine.py:100–130`; constant `hermes_constants.py:3625`
**What:** Constant comment says "merge levels within **1.0 × ATR** of each other", but line 128–130 passes `1.0` **directly** to `_cluster_levels` as a percent threshold (its code at `rs_signals.py:147` compares against percent: `*100.0 <= cluster_atr_pct`). The `atr_pct` parameter of `_build_candle_sr` (line 100) is **never used in the body** — confirming the ATR multiplication was intended but never implemented. Effect: BTC FLAT (ATR 0.4%) clusters at 1.0% = 2.5× ATR → over-merges distinct levels; EXTREME (ATR 2.5%) under-merges. Additionally `_cluster_levels`' docstring ("e.g. 0.003 = 0.3%") contradicts its own code — a future caller passing 0.003 gets 0.003% clustering.
**Impact:** Wrong behavior — regime-dependent S/R map quality distortion.
**Severity:** MEDIUM
**Fix:** `cluster_dist = atr_pct * RR_ENGINE_SR_CLUSTER_ATR` (use the already-fetched atr_pct); fix the `_cluster_levels` docstring to "percent (e.g. 0.3 = 0.3%)".

---

### BUG-7 — Multiplier: engine-blocked R:R doesn't hard-block; fail-open signature fragile (MEDIUM)
**File:** `risk_reward_engine.py:941–952`, `:962–976`
**What (probe-verified, 14 synthetic cases):**
1. When the engine genuinely blocks for R:R (`pass=False`, reason `"R:R ..."`), the multiplier applies only the curve — rr=1.0 → **0.70x, not 0.0x**. Only reasons starting with `"Score"` hard-block (line 951). Two integration points disagree on what "blocked" means.
2. With `RR_ENGINE_SHADOW=True` (current), `pass` is always True → the Score hard-block branch **never fires**; only grade F (<35) blocks.
3. Fail-open detection is signature-fragile: `if rr >= 999 and score == 0` (line 943) matches only `_result()`'s exact shape. The structural path's own `rr=999` (`sl_distance_pct <= 0`, line 555–556) with score≠0 → probe returned **1.30x BOOST** ("R:R=999 grade=A exceptional"). Currently unreachable because `ATR_SL_MIN=0.013` floors the SL, but any future SL-floor change or a bad negative ATR turns a failure into a maximal boost.
4. Docstring (line 929) says "R:R < 1.0 → 0.00x hard block"; the constant is **0.70** (`hermes_constants.py:3653`, lowered 2026-09-23). Stale doc.
**Impact:** Wrong behavior (inconsistent enforcement), edge case (latent boost-on-failure), cosmetic (stale doc).
**Severity:** MEDIUM
**Fix:** Hard-block when `rr < _get_rr_min(regime)` too (or at least when `block_reason` starts with "R:R"); detect fail-open via a dedicated flag in the result dict instead of the (999, score==0) signature; update the docstring.

---

### BUG-8 — Cache poisoning + shared mutable cache object (MEDIUM)
**File:** `risk_reward_engine.py:241–268`
**What:** (a) `build_sr_map` caches even **empty** maps: a token first evaluated before candles/cluster data exist gets an empty `sr_map` for the full 300s TTL even after data arrives. (b) The cache stores and returns the **same list object** (probe: `is` identity True); `_merge_sr_maps:227` mutates level dicts in place (`type` lowercasing) — any consumer mutating the returned map corrupts the cache for all later calls in-process.
**Impact:** Wrong behavior (missing S/R → ATR-fallback TP + zero clarity for 5 min after data becomes available), corruption hazard.
**Severity:** MEDIUM
**Fix:** Don't cache empty results (or cache with a short negative-TTL); return a deep copy (or freeze) from the cache.

---

### BUG-9 — BB zero-width falsy bugs (MEDIUM)
**File:** `risk_reward_engine.py:345, 351` (`compute_vol_width`), `:273–305` (`_compute_bb_width`)
**What:** `_compute_bb_width` on flat closes returns `width=0.0` (probe-verified). `compute_vol_width` then:
- Line 345: `bb_score = min(1.0, (bb_width or 0) / 0.08) if bb_width else 0.3` — `bb_width=0.0` is falsy → **bb_score=0.3 (energy bonus) for zero volatility** instead of 0.
- Line 351: `round(bb_width, 4) if bb_width else None` — **0.0 stored as None** ("no data") in the result dict.
Classic falsy-vs-zero bug pattern.
**Impact:** Wrong behavior — flat/squeeze coins get inflated energy score; BB width reported missing.
**Severity:** MEDIUM
**Fix:** Use `if bb_width is not None` in both places.

---

### BUG-10 — "Open skies" full clarity points on garbage maps (MEDIUM)
**File:** `risk_reward_engine.py:639–643` (`_compute_score`)
**What:** When `sr_map` is non-empty but contains no level on the reward side (e.g., LONG with only supports), clarity gets **full 25 points** ("open skies"). Probe verified (74.5 total, grade B). The comment documents this as intentional — but combined with BUG-3/BUG-4/BUG-8, a stale or signed-distance-corrupted map can present "no reward-side level" when one actually exists → max clarity on garbage. Also asymmetric with the no-data case (empty map → 0 pts).
**Impact:** Wrong behavior in edge cases; score inflation feeds `rr_structural` A/B-grade gating.
**Severity:** MEDIUM
**Fix:** Only award open-skies points when the map is fresh (cache-hit-free) and levels were actually evaluated vs the current price; otherwise fall back to a neutral value.

---

### BUG-11 — manage_exit TRAIL_SL has no minimum-gap guard (MEDIUM)
**File:** `risk_reward_engine.py:1075–1129`; consumed at `position_manager.py:2997–3027` (persists new SL to DB)
**What:** Rule 3 trails LONG to the **highest** support below price and SHORT to the **lowest** resistance above — with no minimum distance filter (Rule 1's `min_break_dist` does not apply here). A support 0.1% below current price produces `new_sl ≈ market price`; `position_manager` persists it → the next wiggle stops the trade. Rule 1's noise filter exists precisely because "level too close = noise" — the trail path lacks the same guard.
**Impact:** Wrong behavior — premature stop-outs on live trades (this path is production-wired via exit config `rr_engine`).
**Severity:** MEDIUM
**Fix:** Apply the same `min_break_dist` (or an ATR-based minimum gap) filter in the trail calculations before accepting `best_trail`.

---

### BUG-12 — Score floor (0.3) can wash out rr penalties; boost unbounded (MEDIUM, design)
**File:** `signal_compactor.py:2045–2063`
**What:** The 26-factor multiplier product is floored at 0.3 (penalty-compounding fix). A "poor R:R" 0.70x multiplier can be completely neutralized when other factors stack the product below 0.3 (floor raises it back). The 1.30x boost has no downward symmetry. Hard blocks (rr_mult=0.0 → product ≤ 0 → `final_score=0.0`) are correctly preserved against the floor (lines 2056–2058) — verified in code.
**Impact:** Wrong behavior (soft) — the RR penalty loses its force in exactly the noisy conditions it was designed for.
**Severity:** MEDIUM (design)
**Fix:** Decide policy: either exempt rr_mult from the floor, or document that rr penalties are advisory-only when stacked.

---

## LOW Severity Findings

| # | File:Line | Bug | Impact |
|---|-----------|-----|--------|
| L1 | `risk_reward_engine.py:682` | Degenerate price (`<=0`) returns `pass=False` via **early return**, bypassing the shadow override (line 747). Shadow contract says "always pass". | Edge case — no production impact today (entry_gates rejects ≤0 first; compactor checks `_rr_price > 0`) |
| L2 | `risk_reward_engine.py:555–556` + `:943` | Structural `rr=999` path unreachable (ATR_SL_MIN floor) but would map to 1.30x boost if reached (see BUG-7.3) | Latent edge case |
| L3 | `risk_reward_engine.py:323–328` | ATR fallback comment stale/wrong: says "0.03% < 0.48% → FLAT" but code does `0.03*100=3.0 → clamp 0.75` (NORMAL). Clamp target `0.75` hardcoded, not a constant | Cosmetic + convention violation |
| L4 | `hermes_constants.py:3638, 3654, 3628` | Dead constants: `RR_ENGINE_BLOCK_SCORE`, `RR_ENGINE_CONF_HARD_BLOCK_SCORE`, `RR_ENGINE_SR_RECENCY_HALF_LIFE` — never read anywhere (grepped). Recency decay promised by the constant does not exist in code | Dead code / misleading config |
| L5 | `risk_reward_engine.py:426–432, 346, 987` | Dead code: `liquidity_bonus` computed with `RR_ENGINE_LIQ_MAGNET_BONUS/FIGHT_PENALTY` but never used in `_compute_score`; `(1 - cascade_risk) * 0` is literally zero; `energy_score` computed/cached/displayed but never gates; `get_exit_frequency` defined but **never called** anywhere | Dead code |
| L6 | `risk_reward_engine.py:664, 913` | `signal_type` param accepted and forwarded but never used in engine logic | Dead param / future footgun |
| L7 | `risk_reward_engine.py:631–638, 610, 617, 344–345` | Hardcoded scoring thresholds/weights (0.3/2.0/3.0 percent, 12.5, 20/10/12, 2.0, 0.08) not in `hermes_constants.py` — convention violation. Clarity sweet-spot (0.3–2.0%) is narrower than tp_max (2.5%) — a 2.4% target usable in NORMAL scores only 15 pts | Convention + minor inconsistency |
| L8 | `entry_gates.py:101, 108, 177–178`; `risk_reward_engine.py:391–400, 1024, 1038` | Direction compared via exact `== 'LONG'` without uppercasing — lowercase `'long'` inverts SL/TP in the legacy path and picks wrong exit rules in manage_exit. All current callers verified to pass uppercase | Latent edge case |
| L9 | `entry_gates.py:149–151` | `_get_cached_atr()` result assigned to `atr_pct` but **never used** in the legacy R:R calculation (SL/TP use fixed constants regardless of volatility) | Dead variable |
| L10 | `rs_signals.py:132` vs `:147` | `_cluster_levels` docstring ("0.003 = 0.3%") contradicts its code (compares against percent) — footgun for future callers | Cosmetic |
| L11 | `hermes_constants.py:752` | `ATR_PCT_FALLBACK = 0.03` commented "2% assumed ATR" — value is 3% | Cosmetic |
| L12 | `risk_reward_engine.py:184–196` | `_build_liq_sr`: `price = cl.get('current_price', 0)` — key exists with value `None` in the JSON → returns None, not 0; variable is dead anyway. Also reveals data-quality issue: cluster `distance_pct` values like 1838.5% exist (filtered by LIQ_MAX_DIST, OK) and `current_price` is null in the snapshot | Dead code + data-quality note |
| L13 | `risk_reward_engine.py:57, 1116 (compactor)` | `_log_dedup` and `_rr_mult_tracker` globals grow unbounded per token:direction | Memory (bounded by token universe) |
| L14 | `risk_reward_engine.py:723, 774` | `getattr(hc, 'RR_ENGINE_SHADOW', True)` / `RR_ENGINE_FAIL_OPEN` defaults: deleting the constants silently changes enforcement behavior | Convention |

---

## Categories With NO Logic Bugs Found

1. **R:R calculation correctness (new engine path):** ✅ Correct. `compute_structural_rr` keeps all distances in consistent decimal units (ATR% → decimal via `/100`), ratio = tp/sl, probe-verified both directions. The liquidation-TP percent→decimal conversion (line 547–551) is correct despite the unit trap the comment warns about. *(The legacy fallback has BUG-1, but the new path's math is sound.)*
2. **Regime threshold mapping (`_get_rr_min` / `_get_tp_max`):** ✅ Correct. FLAT/NORMAL/HIGH/EXTREME mapping matches constants and `classify_volatility` boundaries (0.48/1.0/1.5). *(Enforcement is a separate problem — BUG-2.)*
3. **Direction handling (new engine):** ✅ No inversions. LONG SL below/TP above, SHORT SL above/TP below (test 4 all True). SL structural-extension conditions correct for both directions (probe: SHORT with supports below does not extend; SHORT with resistances above does). Liquidity ahead/behind classification correct. manage_exit break/trail/liquidation rules direction-correct.
4. **Multiplier mapping (given its own thresholds):** ✅ All 14 probe cases mapped exactly per the curve (1.30/1.15/1.00/0.85/0.70/0.0). Hard-blocks at grade F and rr<0.70 work; fail-open (999,0,A) → 1.00 works.
5. **Fail-open returns:** ✅ `rr_confidence_multiplier` exception → 1.0 neutral; `manage_exit` exception → HOLD (never exits on engine failure); `evaluate_rr` exception → pass=True when `RR_ENGINE_FAIL_OPEN=True`. Correct values on every failure path except the L1/L2 edge cases noted.
6. **Shadow mode side effects:** ✅ Shadow override itself is clean — only `passed` flips, logging is deduped (60s TTL), no data mutation. *(Contract gaps at L1 and BUG-2 noted separately.)*
7. **Zero prices / missing data / extreme ATR / no-S/R tokens:** ✅ Handled — zero/negative price blocked, FAKECOIN degrades gracefully to ATR-fallback with grade F, <41 candles → empty candle S/R, <15 1h candles → ATR fallback, extreme ATR → EXTREME regime mapping correct. (BB zero-width is the one miss — BUG-9.)
8. **position_manager TRAIL_SL persistence:** ✅ Correctly updates `pos['stop_loss']` and persists to PostgreSQL with proper cursor/conn cleanup. No bug in the consumer (the missing trail-gap guard is in the engine — BUG-11).

---

## Sideways Finds (not RR-engine, flagged per AGENTS.md)

1. **`signal_compactor.py` price source staleness:** rr_mult is computed from the **last closed 5m candle** close (lines 1800–1807), combined with the engine's 300s caches → R:R multiplier can run on data up to ~10 minutes old. This is exactly the "signal detection vs execution timing" class of bug documented in AGENTS.md. Suggest at least logging `_rr_price` vs live price divergence. **Severity: MEDIUM.**
2. **`signals/rr_structural.py:202–226` and `rr_structural_v2_long.py:219`** call `evaluate_rr` directly and gate on `grade/score/rr_ratio` — they are **not protected by shadow mode** and consume the stale-cache/distorted-score outputs (BUG-3/4/10) directly. Any RR score bug propagates into live signal firing for these families. **Severity: HIGH-visibility coupling.**
3. **`hermes_constants.py` line 2 warning** ("DO NOT UPDATE ANY VALUES... ASK T") applies — BUG-2's fix involves `RR_ENGINE_SHADOW`, which must not be flipped without explicit sign-off.

---

## Priority Fix Order

1. **BUG-1** (legacy always-block) — one-line math fix; prevents total signal drought on any engine exception.
2. **BUG-3** (cache keying) — fixes score correctness for the highest-traffic consumer.
3. **BUG-4** (distance normalization at merge) — fixes SHORT-direction score distortion; also mitigates BUG-10.
4. **BUG-9** (falsy BB) — trivial two-token fix (`is not None`).
5. **BUG-5, BUG-6** — SL-extension correctness.
6. **BUG-7, BUG-2** — enforcement consistency (requires CEO decision on shadow flip).
7. **BUG-8, BUG-10, BUG-11, BUG-12** — hardening.
8. L1–L14 — cleanup pass (dead constants/code, docstrings, hardcodes).

**Total: 12 real bugs (2 HIGH, 1 MEDIUM-HIGH, 7 MEDIUM, plus 14 LOW) + 3 sideways findings. No bugs found in the 8 categories listed above — verified by execution, not by reading.**
