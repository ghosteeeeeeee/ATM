# Independent Audit v2: Risk-Reward Engine Spec + Audit Review

**Auditor:** Independent V2 Review
**Date:** 2026-08-26
**Files Reviewed:** 13 source files, 1 spec, 1 v1 audit

---

## Overall Verdict

**APPROVE WITH MINOR CHANGES** — The spec is well-designed and the concept is sound. The v1 auditor correctly identified 3 real bugs (Chinese constant name, ATR unit mismatch, missing signal_type parameter) but made several **factually wrong claims** about the codebase and was **overly conservative** on design choices that would weaken the engine's value. The spec needs small corrections, not architectural rethinks.

---

## Agree with First Auditor

**The three critical bugs are real and must be fixed before implementation:**

1. **W1: Chinese characters in constant name (CONFIRMED).** Line 453: `RR_ENGINE_SL_STRUCTURAL缓冲` is a syntax error. Rename to `RR_ENGINE_SL_STRUCTURAL_BUFFER`. Uncontroversial.

2. **W2/Finding 1: ATR cache stores dollar ATR, spec expects ATR% (CONFIRMED).** I verified the live file: `atr_cache.json` has `{"BTC": {"atr": 373.5, "ts": ...}}` — raw dollar ATR, no `atr_pct`. The existing `_get_cached_atr()` in `entry_gates.py` line 62 does `entry.get('atr_pct', entry.get('atr'))` which falls through to the raw 373.5. If the spec's `compute_vol_width()` doesn't convert `atr_dollar / price * 100`, everything gets classified as EXTREME and the engine breaks. **This is the most dangerous bug in the spec.**

3. **W3: signal_type missing from _compute_score() (CONFIRMED).** The function signature on line 312 is `_compute_score(rr_ratio, vol_width, liquidity, sr_map)` but line 336 calls `signal_type` which isn't in scope. This is a `NameError` at runtime. Must add `signal_type` as a parameter or remove the dependency.

**Good recommendations from v1 auditor:**

4. **Finding 5: Reuse rs_signals.py S/R code.** The spec proposes building a new S/R map builder, but `rs_signals.py` already has battle-tested `_find_swing_highs_lows()`, `_cluster_levels()`, and `_build_level_touches()`. Importing from rs_signals is cleaner than reimplementing. However, I'd implement this as "call rs_signals for candle S/R, then merge with liquidation_map's existing composite S/R" — not a full refactor of rs_signals.

5. **Finding 6: signal_type API issue.** Adding `signal_type` to `rr_gate()` is a minor API change that only affects 2 callers (`engulfing.py` line 323, and the docstring in entry_gates.py line 15). Both already pass it or could easily add an optional kwarg. Low risk.

6. **W12: _regime_alignment_pts() needs a full implementation spec.** The spec gives only two examples. Since `volatility_gate.py` already has `REGIME_SIGNALS` mapping (lines 31-107) — the complete signal-to-regime compatibility table — the scoring function should just look up `signal_type in REGIME_SIGNALS[regime]`. No need to invent a new classification.

---

## Disagree with First Auditor

**The first auditor made several factually wrong claims and overly conservative recommendations:**

### 1. WRONG: "RS_MIN_TOUCHES = 30" (v1 Audit W10, line 91)

The first auditor claims `RS_MIN_TOUCHES = 30` in `rs_signals.py`. **This is wrong.** The actual value is `RS_MIN_TOUCHES = 5` (line 38 of `rs_signals.py`).

The spec's `SR_MIN_TOUCHES = 3` is only 2 below the existing system's minimum. This is a reasonable delta — the engine's S/R map is for R:R assessment, not for signal generation. A lower threshold means the engine considers more levels as "valid," giving it a richer structural picture. The v1 auditor's recommendation of "10 as middle ground" would actually be MORE restrictive than the existing signal, which makes no sense.

**My take:** `SR_MIN_TOUCHES = 3` is fine. If anything, consider matching `RS_MIN_TOUCHES = 5` for consistency, but 3 is defensible.

### 2. WRONG: "EXTREME regime should be skipped entirely" (v1 Audit W6)

The first auditor claims `volatility_gate.py` says EXTREME should "skip entirely." **This is wrong.** The volatility_gate allows specific signals through in EXTREME (lines 95-106):
- `continuation+,hzscore+`, `hzscore+,mover+`
- `mover+`, `mover-`
- `bb_bounce`
- `wave_catcher`, `wave_catcher+`, `wave_catcher-`
- `ct-hot`, `ct-hot+`, `ct-hot-`
- `hl_copy_trader`
- `liq-hunt`, `liq-hunt+`, `liq-hunt-`
- `tl_break`, `tl_break_long`, `tl_break_short`
- `confluence+`, `confluence-`

That's **11+ signal types** allowed in EXTREME. The "skip" behavior only applies when no signal is specified (line 207-208: `if regime == 'EXTREME': return ('SKIP', ...)`) — i.e., the generic filter, not the signal-aware filter. When a signal IS provided and it works in EXTREME, `should_trade()` returns `('TRADE', regime)`.

The spec's EXTREME R:R threshold of 2.0 is appropriate for these continuation/momentum signals that thrive on volatility. The v1 auditor's recommendation to "block entirely or require 3.0+" would kill valid EXTREME trades that the existing system allows.

### 3. OVERLY CONSERVATIVE: "Start with RR_ENGINE_MIN_RATIO_NORMAL = 2.5" (v1 line 217)

The first auditor suggests tightening the NORMAL threshold from 2.0 to 2.5. But the existing `rr_gate()` already has `ENTRY_RR_MIN_RATIO = 2.0`. The whole point of the engine is to make R:R evaluation *smarter* (structural targets instead of arbitrary ATR multiples), not to make it *stricter*. If the engine correctly identifies structural TP targets, many signals that currently fail the 2.0 gate with ATR-based TP would actually PASS with a higher R:R because the structural target is closer (realistic TP) and the SL is placed beyond nearby structure.

Starting at 2.5 would increase block rate and potentially starve the pipeline for no reason. Start at 2.0 (same as current), let shadow mode data validate whether the smarter R:R actually produces better outcomes.

### 4. MISLEADING: "BB_STDDEV mismatch is a bug" (v1 Audit W4)

The first auditor flags that `range_finder.py` and `bb_bounce.py` use `BB_STDDEV = 1.8` while the spec proposes 2.0. This is **not a bug — it's an appropriate divergence.** The signals use 1.8 for *entry detection* (band touches). The engine uses BB width for *volatility regime assessment* (how wide are the bands relative to price?). Using 2.0 for the engine gives a slightly wider band, which produces a more conservative squeeze detection — a reasonable choice for an R:R filter. Making them match isn't required and the difference is minor.

That said, using 1.8 for consistency is also fine. This is a style choice, not a correctness issue. The v1 auditor overstates this as a "must fix."

### 5. WRONG about "Finding 4: TP Cap"

The first auditor says the 3.0% TP cap "may be too tight." But the existing system has `ATR_TP_MAX = 0.020` (2.0%). The spec's 3.0% is actually **wider** than the current cap, allowing the engine to capture structural targets between 2.0-3.0% that the current system ignores. This is a pure improvement. The v1 auditor's concern about FLAT regime needing 3.5% is valid in theory, but in practice, FLAT regime tokens with low ATR (0.48% × 2.0 = 0.96% ATR-based TP) rarely have structural levels at 3.5%. The 3.0% cap is fine.

### 6. WRONG about "cascade_risk bidirectional" (v1 line 222-223)

The v1 auditor recommends making cascade_risk bidirectional (risk for SL side, opportunity for TP side). But the spec ALREADY handles this — the `compute_liquidity_proximity()` function distinguishes between `clusters_ahead` (TP magnets = opportunity) and `clusters_behind` (SL risk). The `magnet_score` captures the upside, and `cascade_risk` captures the downside. The spec just doesn't use the word "bidirectional" — the logic is already there.

---

## New Findings (missed by both spec and v1 audit)

### NF1: Liquidation Cluster Format Discrepancy — `total_size` vs `total_notional_usd`

The spec says (line 243): "nearest_cluster_usd: USD size of nearest cluster." But looking at the actual data format:

```json
{
  "price": 64.09,
  "total_size": 10341753.8,      // This is in USD (margin size)
  "total_notional_usd": 662379416.72,  // This is the notional (margin × leverage)
  "count": 1,
  "max_leverage": 20.0
}
```

The `liquidation_map.py` composite S/R builder (line 521) uses `cl["total_size"]` for strength. The spec should clarify which field to use. For cascade risk, `total_notional_usd` matters (that's the forced selling volume). For S/R strength, `total_size` (margin at risk) is arguably more relevant. **Both fields should be available in the engine's output.**

### NF2: Composite S/R Already Exists in liquidation_map.py

The spec (Section 3.1.4) proposes building a new merge/rank function for S/R from candle swings, order book, and liquidation clusters. But `liquidation_map.py` **already does this** (lines 503-530) — it builds `composite_sr` that merges book-based S/R with liquidation clusters, sorted by proximity, top 15 per coin.

The engine should:
1. Read `liquidation_clusters.json → support_resistance` (already merged by liquidation_map.py)
2. Add candle-based S/R from swing detection
3. Re-sort by proximity

This is simpler than the spec suggests. Don't reimplement what liquidation_map.py already does.

### NF3: `get_sr_levels()` Already Exists as a Clean API

`liquidation_map.py` line 636-639 has `get_sr_levels(coin)` which reads `liquidation_clusters.json` and returns the composite S/R for a coin. The engine can call this directly instead of manually parsing the JSON file.

### NF4: ATR_PCT_FALLBACK = 0.03 Causes Wrong Regime

`hermes_constants.py` line 611: `ATR_PCT_FALLBACK = 0.03` (3.0%). This is used in `rr_gate()` when ATR cache is empty. But 3.0% is >1.5%, so any token with missing ATR data would be classified as EXTREME by the engine. The engine should either:
- Use the existing `volatility_gate.get_atr_pct()` (computes from candles, has its own fallback logic)
- Or detect the fallback case and treat it as NORMAL instead of EXTREME

### NF5: Signal Files That Call rr_gate Are Limited

Only `engulfing.py` (line 323) and the entry_gates.py docstring reference `rr_gate()`. Many signals (bb_bounce, range_finder, momentum, etc.) don't call `rr_gate()` at all. The spec's "20-40% block rate" metric assumes the engine runs on all signals, but it only runs on signals that explicitly call it. Either:
- Upgrade Option A works (all current rr_gate callers automatically benefit)
- But don't expect the engine to filter most signals unless rr_gate is added to more signal files

This isn't a bug — it's a scope clarification the spec should include.

### NF6: Spec's Regime Thresholds Mismatch volatility_gate.py

The spec (Section 3.2) shows FLAT < 0.48%, NORMAL 0.48-1.0%, HIGH 1.0-1.5%, EXTREME >1.5%. These match `volatility_gate.py` exactly (lines 155-162). Good — no issue here. But the spec's R:R table says:

| Regime | Expected R:R |
|--------|-------------|
| FLAT | 3.0+ |
| NORMAL | 2.0+ |
| HIGH | 1.5+ |
| EXTREME | 2.0+ |

The HIGH regime threshold (1.5+) is **lower** than NORMAL (2.0+). This makes sense: HIGH volatility means wider SL (ATR-based), so the minimum R:R can be lower because the absolute $ reward is still meaningful. But the spec doesn't explain this rationale, and a reader might think it's a typo. Add a note.

### NF7: Caching Assumes Single-Process with File Reads

The spec's in-memory caches (`_sr_cache`, `_vol_cache`) are process-local dicts. But the pipeline runs as separate scripts (signals via `signals_runner.py`, price collection via separate systemd). Each process gets its own dict. The 5-min TTL means re-computation on every process start, which is fine for correctness but wastes CPU if many signals fire simultaneously.

This is a minor efficiency concern, not a correctness issue. The file-based caches (atr_cache, liquidation_clusters.json) are the real cross-process state. The in-memory dict is just a within-process optimization.

### NF8: Missing `candles_5m` Fetch Logic

The spec's `evaluate_rr()` accepts `candles_5m=None` as optional. When None, it should fetch from `candles.db`. But the spec doesn't show the fetch code. The engine needs to query `candles_5m` from `candles.db` when not provided. `engulfing.py` already has `_get_5m_candles()` — consider reusing that pattern or adding a shared utility.

---

## Practical Concerns

### 1. Pipeline Latency
The spec targets <500ms additional latency. The engine reads 3 files + 1 DB query:
- `atr_cache.json` (tiny, ~1KB) — ~5ms
- `liquidation_clusters.json` (10-50KB) — ~10-20ms
- `candles.db` (20 candles for BB, 300 for swing detection) — ~10-30ms
- In-memory computation — ~10ms
- Total: ~35-65ms. Well within budget.

But `liquidation_clusters.json` is only updated every 5 minutes. If signals fire right after a pipeline run (file is fresh), latency is fine. If they fire 4.5 minutes later, the data is stale but still fast to read.

### 2. Edge Case: Token Not in liquidation_clusters.json
The spec's SCAN_TOKENS in `liquidation_map.py` (line 35-40) only covers 30 tokens. If a signal fires for a token outside this list, there's no liquidation/S/R data from the order book. The engine should handle this gracefully — candle-only S/R is still valuable. The spec says "fail-open" but should be explicit: "if liquidation data unavailable, use candle S/R only, don't block."

### 3. Edge Case: Candle Database Cold Start
After a system restart, `candles.db` might not have 300 candles for swing detection. The engine needs to handle `len(candles) < SR_LOOKBACK` gracefully — use what's available, don't fail.

### 4. Shadow Mode Logging Volume
If 20-30 signals/day fire, shadow mode adds ~30 log entries/day. Not a volume concern. But the log format should include enough detail for retrospective analysis (which signals were blocked, what their actual outcome was). The spec's `_log()` format in Section 4.2 is good.

### 5. Backtest Validation Is Critical
The spec's Section 8.2 says: "block rate should be >70% losers." This is the most important metric. If the engine blocks 30% of signals and those blocked signals have >40% WR, it's destroying value. Shadow mode MUST collect outcome data for at least 7 days before enforcement.

---

## My Recommendation

### Build This. In This Order.

**Phase 1: Fix the 3 bugs, ship shadow mode (1-2 hours)**
1. Fix `RR_ENGINE_SL_STRUCTURAL缓冲` → `RR_ENGINE_SL_STRUCTURAL_BUFFER`
2. In `compute_vol_width()`, convert dollar ATR to ATR%: `atr_pct = atr_dollar / price * 100` (OR use `volatility_gate.get_atr_pct()`)
3. Add `signal_type=None` parameter to `_compute_score()` signature
4. Set `RR_ENGINE_SHADOW = True`, `RR_ENGINE_FORCE = False`
5. Implement the engine with in-memory-only logging (no blocking yet)

**Phase 2: Reuse existing code (30 min)**
- For candle S/R: call `rs_signals._find_swing_highs_lows()` and `rs_signals._cluster_levels()`
- For order book S/R: call `liquidation_map.get_sr_levels(coin)`
- Don't build `_sr_map.py` as a new module — the spec's architecture diagram shows it as separate, but it should just be functions inside `risk_reward_engine.py`

**Phase 3: Run shadow mode for 7 days**
- Log every signal: would the engine have blocked it? What grade?
- Cross-reference with actual trade outcomes
- Calculate: blocked-signal WR vs. allowed-signal WR
- Only proceed to enforcement if blocked WR < 40%

**Phase 4: Tune and enforce (after data)**
- Adjust thresholds based on shadow mode data
- Set `RR_ENGINE_SHADOW = False`, `RR_ENGINE_FORCE = True`
- Monitor: block rate, false positive rate, pipeline latency

### What to Ignore from v1 Audit

| v1 Recommendation | Why I Disagree |
|---|---|
| Tighten NORMAL threshold to 2.5 | Existing system uses 2.0; engine should be smarter, not stricter |
| EXTREME should block entirely | volatility_gate allows 11+ signals in EXTREME; blocking kills valid trades |
| Match BB_STDDEV to 1.8 | 2.0 is appropriate for regime assessment; not a correctness issue |
| SR_MIN_TOUCHES = 10 | rs_signals uses 5; the engine needs richer data, 3 is fine |
| Start with stricter thresholds | Gather data first at current thresholds, tighten later if data warrants |

### What to Take from v1 Audit

| v1 Finding | Action |
|---|---|
| Fix Chinese constant name | ✅ Must fix |
| Fix ATR unit conversion | ✅ Must fix (most critical) |
| Fix signal_type parameter | ✅ Must fix |
| Define _regime_alignment_pts fully | ✅ Use REGIME_SIGNALS from volatility_gate |
| Reuse rs_signals.py code | ✅ Import, don't reimplement |
| Compare with legacy in shadow mode | ✅ Good idea, add to logging |
| Per-component data availability | ✅ Add explicit fallbacks |

---

## Summary

The spec is 90% ready for implementation. The three bugs (Chinese constant, ATR units, signal_type) are real and easy to fix. The v1 auditor correctly identified these but then overcorrected with conservative recommendations that would weaken the engine. The biggest risks are not design flaws — they're the ATR unit bug (which would break everything) and the lack of shadow mode data (which means we're guessing at thresholds).

**Ship the spec with the 3 bug fixes. Run shadow mode. Let data decide the rest.**
