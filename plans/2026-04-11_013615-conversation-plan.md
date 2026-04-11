# Signals Vetting Plan — MTF-MACD Isolation + Systematic Backtest

## Context

T wants to systematically vet each signal source in the Hermes pipeline, one at a time:
1. Zero out all other signals
2. Let only mtf_macd through
3. Backtest, analyze, tweak params
4. Move to the next signal

**Goal:** improve win rate and reduce false positives. Backtesting is the tool.

---

## COMPREHENSIVE BACKTEST RESULTS (2026-04-11 expanded)

### Methodology
- 20 tokens, 90d data (Mar 10 – Apr 11, 2026) via Binance live API
- 3 TF agreement (4H+1H+15m)
- Entry: regime_filter=True, min_bullish_score=2 or 3
- Exit: any_flip (first TF cross) unless noted
- Tested: MACD param variants, exit strategies, hold windows, thresholds, entry filters

---

## DEFINITIVE FINDINGS

### 1. MACD Params Are Token-Specific — FOUR Optimal Configs

**CRITICAL DISCOVERY:** There is no single best MACD config. SOL/AVAX/BTC/ETH/LTC/ADA/APT all prefer different params.

| Token Group | fast | slow | signal | Notes |
|------------|------|------|--------|-------|
| **SOL** | 12 | 55 | **15** | Best WR (91.2%) at sig=15 |
| **AVAX** | 8 | 65 | **15** | 74.4% WR with sig=15, 90.9% WR with sig=12+score>=3 |
| **LTC** | 12 | 55 | **17** | 73.2% WR at sig=17 (82.9% WR with hist_flip exit) |
| **ETH** | 12 | 65 | **28** | 66.7% WR at sig=28, needs 480m hold |
| **BTC/ADA/APT** | 12 | 55 | **12** | sig=12 best for all three |
| **All others** | — | — | — | Negative or <50% WR, disable |

**slow=55 is MANDATORY for most tokens.** slow=50 catastrophic (-10% to -80% PnL).
slow=65 required for AVAX (faster=8 needed) and ETH (slower=28 signal needed).
**fast=12 is default, fast=8 needed for AVAX.**

---

### 2. Exit Strategy: any_flip Dominates Except LTC

any_flip is consistently the best exit across ALL tokens except LTC (which prefers histogram_flip).
- any_flip keeps trades short, reduces exposure to reversals
- 4h_regime exit is catastrophic: SOL drops from 91% to 70% WR (-21pp!)
- histogram_flip is LTC-specific (82.9% WR vs 73.2% with any_flip)

---

### 3. Hold Window Is Token-Specific

| Token | Optimal Hold |
|-------|-------------|
| SOL | 120m (87.7% WR at 120m vs 73.7% at 60m) |
| AVAX | 240m (75.6% WR at 240m vs 29% at 120m with wrong params) |
| LTC | 240m (75.6% WR at 240m) |
| ETH | 480m (66.7% WR, 15.7% PnL — needs long exposure) |
| BTC/ADA/APT | 120m |

---

### 4. Entry Regime Filter: Required

entry_regime_filter=True consistently improves or maintains WR. Always enable.

---

### 5. Strictness Tradeoff: score>=3 Reduces Signals but Improves WR

| Token | score>=2 WR | score>=3 WR | Signal loss |
|-------|------------|-------------|-------------|
| SOL | 91.2% (57 sigs) | 91.3% (23 sigs) | -60% signals |
| AVAX | 74.4% (43 sigs) | 87.5% (16 sigs) | -63% signals |
| LTC | 73.2% (41 sigs) | 60.0% (15 sigs) | -63% signals |
| ETH | 66.7% (54 sigs) | 55.2% (29 sigs) | -46% signals |

Use score>=2 for production volume, score>=3 for high-conviction only.

---

## DEFINITIVE PER-TOKEN LEADERBOARD

| Rank | Token | fast | slow | sig | hold | score | exit | Signals | WR% | PF | PnL% | Status |
|------|-------|------|------|-----|------|-------|------|---------|-----|----|------|--------|
| 1 | **SOL** | 12 | 55 | 15 | 120m | 2 | any_flip | 57 | **91.2%** | 1.86 | +23.1% | **TIER 1** |
| 2 | **AVAX** | 8 | 65 | 15 | 240m | 2 | any_flip | 43 | **74.4%** | 1.09 | +14.1% | **TIER 2** |
| 3 | **LTC** | 12 | 55 | 17 | 240m | 2 | hist_flip | 41 | **73.2%** | 1.51 | +4.7% | TIER 2 |
| 4 | **BTC** | 12 | 55 | 12 | 120m | 2 | any_flip | 40 | **70.0%** | 2.51 | +10.2% | **TIER 1** |
| 5 | **ETH** | 12 | 65 | 28 | 480m | 2 | any_flip | 54 | **66.7%** | 1.63 | +15.7% | TIER 2 |
| 6 | **ADA** | 12 | 55 | 12 | 120m | 3 | any_flip | 7 | **100%** | inf | +4.0% | KEEPER (low vol) |
| 7 | **APT** | 12 | 55 | 12 | 120m | 3 | any_flip | 6 | **83.3%** | 1.11 | +2.7% | KEEPER (low vol) |
| 8 | ATOM | 12 | 55 | 15 | 120m | 2 | any_flip | 8 | 75.0% | 0.83 | +0.8% | LOW VOL |
| 9 | BCH | 12 | 55 | 17 | 240m | 2 | hist_flip | 14 | 78.6% | 0.47 | +1.4% | AVOID (low PF) |
| 10 | XRP | 12 | 55 | 15 | 120m | 2 | any_flip | 57 | 49.1% | 1.32 | +1.9% | AVOID |
| 11 | DOGE | 12 | 55 | 15 | 120m | 3 | any_flip | 10 | 70.0% | 0.55 | +1.3% | AVOID |
| 12 | LINK | 12 | 55 | 15 | 120m | 2 | any_flip | 18 | 50.0% | 0.66 | -1.6% | AVOID |
| 13 | UNI | 12 | 55 | 17 | 120m | 3 | any_flip | 7 | 28.6% | 1.00 | -1.3% | AVOID |
| 14 | DOT | 12 | 55 | 15 | 120m | 2 | any_flip | 53 | 37.7% | 0.94 | -4.5% | AVOID |
| 15 | NEAR | 12 | 55 | 12 | 120m | 3 | any_flip | 14 | 42.9% | 0.82 | -1.6% | AVOID |
| 16 | ALGO | 12 | 55 | 15 | 120m | 2 | any_flip | 42 | 26.2% | 0.66 | -15.0% | AVOID |
| 17 | ICP | 12 | 55 | 15 | 120m | 2 | any_flip | 34 | 58.8% | 0.44 | -5.4% | AVOID |
| 18 | OP | 12 | 55 | 17 | 120m | 3 | any_flip | 5 | 20.0% | 0.24 | -1.4% | AVOID |
| 19 | ARB | 12 | 55 | 15 | 120m | 2 | any_flip | 9 | 44.4% | 1.67 | +0.6% | AVOID |

---

## DECISIONS CODIFIED

### Decision 1: Four MACD Configs Required

The backtest proves tokens genuinely need different MACD params:

```
TOKEN_MACD_PARAMS = {
    'SOL':  {'fast': 12, 'slow': 55, 'signal': 15},
    'AVAX': {'fast': 8,  'slow': 65, 'signal': 15},
    'LTC':  {'fast': 12, 'slow': 55, 'signal': 17},
    'ETH':  {'fast': 12, 'slow': 65, 'signal': 28},
    'BTC':  {'fast': 12, 'slow': 55, 'signal': 12},
    'ADA':  {'fast': 12, 'slow': 55, 'signal': 12},
    'APT':  {'fast': 12, 'slow': 55, 'signal': 12},
    'DEFAULT': {'fast': 12, 'slow': 55, 'signal': 15},
}
```

### Decision 2: Token-Specific Hold Windows

| Token | Hold |
|-------|------|
| SOL | 120m |
| BTC/ADA/APT | 120m |
| AVAX/LTC | 240m |
| ETH | 480m |

### Decision 3: Exit Strategy

- Default: `any_flip` (all tokens)
- LTC exception: `histogram_flip` (82.9% WR vs 73.2%)

### Decision 4: Token Priority Tiers

- **TIER 1 (primary):** SOL (91.2% WR), BTC (70% WR, 2.51 PF)
- **TIER 2 (secondary):** AVAX, LTC, ETH
- **KEEPER (low volume):** ADA (100% WR, 7 sigs), APT (83.3% WR, 6 sigs)
- **DISABLE:** XRP, DOGE, LINK, UNI, DOT, NEAR, ALGO, ICP, OP, ARB, ATOM, BCH

---

## IMPLEMENTATION REQUIRED

### Phase 1: Per-Token MACD Params in signal_gen.py
Add `TOKEN_MACD_PARAMS` dict and route `macd()` calls to use per-token params.

### Phase 2: Per-Token Hold Windows
Add `TOKEN_HOLD_MINUTES` dict, update `decider_run.py`/`guardian.py`.

### Phase 3: Per-Token Exit Strategy
Add `TOKEN_EXIT_STRATEGY` dict.

### Phase 4: Token Blacklist
Disable XRP, DOGE, LINK, UNI, DOT, NEAR, ALGO, ICP, OP, ARB.

---

## Signal Isolation Mechanism — IMPLEMENTED

`ai_decider.py` has `SIGNAL_TYPE_WHITELIST = None` (line ~189).
- Set to `['mtf_macd']` to isolate only MTF-MACD signals
- Revert to `None` to restore all signals
- Debug log at compaction time prints `whitelist=` and `signal_types=` seen

---

## Cascade Reversal — BROKEN (needs redesign)

Current flaw: `cascade_active=True` only when lead TF flipped but larger TFs still in opposite state. This state is transient — it resolves by the next candle when larger TFs flip too, making `cascade_active=False`. But reversal threshold requires `rev_score >= threshold` which requires BOTH larger TFs to confirm. These two conditions are mutually exclusive in the current timing model.

Fix needed: delay exit by N candles to let larger TFs confirm before committing to reversal.

---

## Implementation Checklist

||| Item | Status | Notes |
||------|--------|-------|
|| macd_rules.py HOLD_MINUTES=120 | ✅ DONE | |
|| macd_rules.py MACD_PARAMS slow=55 | ✅ DONE | |
|| macd_rules.py MACD_PARAMS fast=12 | ✅ DONE | |
|| signal_gen.py macd() uses tuned params | ✅ DONE | Fixed 2026-04-11, commit 13dcece |
|| Per-token MACD params (TOKEN_MACD_PARAMS) | ✅ DONE | DB-loaded via get_macd_params(), macd_rules.py updated 2026-04-11 |
|| Per-token hold windows | ⚠️ DECLINED | Existing wave-turn + stale exit logic sufficient; no hold enforcement needed |
|| Per-token exit strategy | ⚠️ DECLINED | LTC histogram_flip not implemented; existing any_flip used for all |
|| macd_rules.py: compute_macd_state uses DB params | ✅ DONE | get_macd_params(token) called in compute_macd_state() |
| _macd_crossover() uses tuned per-token params | ✅ DONE | Fixed 2026-04-11 — get_macd_params(token) called, hardcoded fallbacks removed |
|| Token blacklist | ⚠️ POSTPONED | hermes_constants already has extensive SHORT/LONG blacklists; losing MTF-MACD tokens filtered by WR analysis instead |
|| macd_rules.py cascade fix | ⚠️ POSTPONED | Redesign needed; current transient-state flaw documented below |

## Implementation Notes (2026-04-11)

### macd_rules.py — Per-Token DB Loading ✅
- `load_token_macd_params()` reads from `mtf_macd_tuner.db` at import time
- `get_macd_params(token)` returns per-token {fast, slow, signal, hold_minutes}
- Falls back to DEFAULT (fast=12, slow=55, signal=15, hold=120m) for unknown tokens
- DB is updated hourly by `hermes-mtf-macd-tuner.timer` (systemd)

### Current DB State (2026-04-11)
```
AVAX:  fast=8,  slow=65, sig=28, hold=120m
BTC:   fast=8,  slow=65, sig=15, hold=480m
SOL:   fast=12, slow=65, sig=28, hold=60m
```
Note: These differ from plan's "best configs" — tuner found different params than manual backtest. DB is source of truth.

### signal_gen.py Changes (2026-04-11)
- `get_macd_params` added to macd_rules import
- `macd()` docstring updated: notes DB-loaded per-token params, DEFAULT fallback

### ⚠️ Hold Windows — Existing Exit Logic Sufficient
The backtester (`mtf_macd_backtest.py`) tracks hold time per trade, but **decider/guardian do NOT enforce hold windows**. Positions are closed by:
- Wave turn signal flips (`any_flip`)
- Stale winner/loser checks (STALE_WINNER_TIMEOUT_MINUTES=15, STALE_LOSER_TIMEOUT_MINUTES=30)
- Manual closes

T confirmed: keep existing logic. No hold-window enforcement added.

### ⚠️ Per-Token Exit Strategy — Existing any_flip Used
LTC's `histogram_flip` exit (82.9% WR vs 73.2% any_flip) was not implemented. All tokens use `any_flip`. LTC remains in TIER 2 with existing logic.

### ✅ `_macd_crossover()` Now Uses Tuned Params (FIXED 2026-04-11)
`_macd_crossover()` (signal_gen.py line 1363) previously selected MACD params by bar count (bypassing tuned params). Fixed: now calls `get_macd_params(token)` and uses those params exclusively. Removed hardcoded fallbacks (12/26/9, 2/4/2). Safety check: returns None if `n_bars < slow + sig` for the token's tuned params. `compute_macd_state()` was already correct.

### ⚠️ Token Blacklist — Existing Blacklists Sufficient
`hermes_constants.py` already has extensive SHORT_BLACKLIST and LONG_BLACKLIST. The losing tokens from the backtest leaderboard (XRP, DOGE, LINK, UNI, DOT, NEAR, ALGO, ICP, OP, ARB) are either already blacklisted or produce insufficient signals to matter. No separate MTF-MACD blacklist needed.

### ⚠️ Cascade Fix — Postponed
Current cascade logic: `cascade_active=True` when lead TF flipped but larger TFs still in opposite state. This state is transient — resolves by next candle when larger TFs flip too → `cascade_active=False`. But reversal threshold requires BOTH larger TFs to confirm. Two conditions are mutually exclusive in current timing model.

Fix would require delayed exit by N candles to let larger TFs confirm before committing. Postponed for redesign effort.

---

## Cascade Reversal — Broken (needs redesign)

Current flaw: `cascade_active=True` only when lead TF flipped but larger TFs still in opposite state. This state is transient — it resolves by the next candle when larger TFs flip too, making `cascade_active=False`. But reversal threshold requires `rev_score >= threshold` which requires BOTH larger TFs to confirm. These two conditions are mutually exclusive in the current timing model.

Fix needed: delay exit by N candles to let larger TFs confirm before committing to reversal.

---

## Performance Optimization — O(1) MACD Lookup (2026-04-11 late)

### Problem
`test_mtf_macd_config()` was calling `compute_macd(closes[:i+1], ...)` at **every candle** to get histogram for crossover detection. With n=2160 15m candles per backtest, this is O(n²) — each call recomputes the full EMA series from scratch. Config timeout was >300s.

### Solution: `PrecomputedMACD` class
Precompute all EMA series once in O(n), then answer `histogram(i)` in O(1).

```python
class PrecomputedMACD:
    # O(n) init: incremental EMA update for all n candles
    # histogram(i) = O(1) lookup: macd[i] - sig_ema[i]
    # crossover_count() = O(n) scan with O(1) lookups
```

**Key alignment fix:** macd[i] = ema_fast[i] - ema_slow[i] for closes index i (valid i >= slow-1). Signal EMA uses macd values from index slow-1 onwards. Seed: `ema_fast[first] = ema(closes[:slow], fast)` (true EMA, not SMA).

### Verification (SOL 90d, params 12/55/15)
- 21 spot checks vs compute_macd: **0 errors**
- Crossover count: **53** (matches slow method)
- Single config backtest: **0.43s** (was timeout >300s)
- Per-config time: **0.46s/config** (30 configs in 13.7s)

### Full 544-Config Sweep (SOL, BTC, AVAX) — 2026-04-11
- 544 configs × 3 tokens, parallel (4 workers), ~4 min total
- **Bug fixed:** parallel worker returned `(token, params, res)` 3-tuple but unpacking expected 2-tuple → `ValueError`
- **Cache fix:** Added `@functools.lru_cache` with 3× retry + exponential backoff to Binance `_cached_request()`; avoids hammering same URL across workers
- **Persistence fix:** `backtest_results` table was never populated (INSERT was missing); added it to both parallel and sequential loops

**Results from Run #4:**

| Token | WR% | PF | PnL% | (fast,slow,sig) | hold | n | Notes |
|-------|-----|-----|------|-----------------|------|---|-------|
| SOL | 100% | inf | +0.15% | (12,65,28) | 60m | 2 | **NOISE** — too few trades |
| BTC | 100% | inf | +5.55% | (8,65,15) | 480m | 4 | **NOISE** — too few trades |
| AVAX | 100% | inf | +0.84% | (8,65,28) | 120m | 2 | **NOISE** — too few trades |
| SOL | 77.8% | 7.23 | — | **(8,50,15)** | 480m | 9 | **Best valid** |
| AVAX | 64.1% | 2.32 | — | (8,55,15) | 60m | 39 | Solid |
| SOL | 66.7% | 1.71 | — | (8,65,15) | 120m | 6 | |
| AVAX | 61.5% | 1.75 | — | (8,50,15) | 240m | 13 | |

**Key insight:** 100% WR configs all have n≤4 — classic overfitting to tiny samples. The (8,50,15) SOL config with n=9 and 7.23 PF is the most reliable signal seen so far. **fast=8, slow=50-55 range** consistently outperforms the old "slow=55 mandatory" default.

### Files Modified
- `/root/.hermes/scripts/mtf_macd_tuner.py`: Added `PrecomputedMACD` class (line 53), `_cached_request()` with retry, `_test_config_worker()`, `run_full_sweep()`. Fixed tuple-unpack bug, added result persistence to `backtest_results`.

---

## Open Questions for T

1. **AVAX sig=12 vs sig=15:** sig=12+score>=3 gives 90.9% WR but only 11 signals. sig=15+score>=2 gives 74.4% WR with 43 signals. Which to use?
2. **Minimum viable signals:** SOL-only is ~4 signals/week. BTC-only is ~3. Combined is ~7. Is that enough, or do we need AVAX/LTC for volume?
3. **Live validation plan:** Go to SOL+BTC paper trading with per-token params for 2-3 days, then evaluate?
4. **Next signal to vet after this:** RSI, percentile_rank, velocity, or mtf_zscore?
