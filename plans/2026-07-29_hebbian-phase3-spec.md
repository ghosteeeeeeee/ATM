# Spec: Hebbian Phase 3 — Beyond WR Estimate

**Date:** 2026-07-29
**Status:** SPEC — awaiting review
**Inspiration:** Brain.db now has 1007 nodes / 5706 synapses of trade-outcome data. Time to extract more value from it.

---

## Status of Phase 1/2 (DONE)

| Phase | Feature | Commit |
|-------|---------|--------|
| 1 | Auto-enrichment + 2573-trade backfill | `f42cdd5` |
| 2a | similar_setup_lookup() (PostgreSQL) | `5824e78` |
| 2b | Hebbian write-back on close | `ed35cd1` |
| 2c | Hebbian WR estimate at decision time | `94ed919` |

**Phase 2c (Hebbian WR estimate) shipped:**
- Reads `recall(token)` → finds (token, signal) → estimates WR
- WR ≥ 60% with n ≥ 3 → +5 confidence boost
- WR ≤ 30% with n ≥ 5 → -10 confidence penalty
- Calibrated math: `WR = (weight + N - 1) / (2N)` when weight > 1.0
- Live data: APEX + accel-300-,rs-s-broken = 72% WR (boost)
- ~10 active token↔signal pairs qualify

---

## Phase 3: Four More Profitable Uses

### 3a. Token Sentiment Check (HIGH PRIORITY)

**Problem:** Some tokens are chronic losers. APEX, BLUR, SKR have HIGH WR — but other tokens (which we don't have data for yet) might be chronic losers. `recall(token)` already returns top-K associations; we can check if those are positive (HOT_APPROVED, SHORT_BIAS) or negative (SKIPPED, NEUTRAL, LOSS).

**Solution:** Pre-trade token sentiment filter using production brain.db concepts.

```python
def token_sentiment(token, k=20):
    """Returns (-1.0 to +1.0) sentiment from recall(token)."""
    eng = HebbianEngine()
    recall = eng.recall(token, k=k)
    if not recall:
        return 0.0  # novel token, neutral
    positive_labels = {'HOT_APPROVED', 'APPROVED', 'SHORT_BIAS', 'LONG_BIAS'}
    negative_labels = {'SKIPPED', 'WAIT', 'NEUTRAL'}
    pos_w = neg_w = 0
    for concept, label, weight, count in recall:
        if label == 'decision' and concept in positive_labels:
            pos_w += weight
        elif label == 'decision' and concept in negative_labels:
            neg_w += weight
    total = pos_w + neg_w
    return (pos_w - neg_w) / total if total > 0 else 0.0
```

**Action:**
- sentiment ≤ -0.7 → SKIP (token has chronic negative decisions)
- sentiment ≥ +0.7 → BOOST (+3 confidence, optional)

**Files:** `decider_run.py:context_gate()`, add after rule-based, before similar_setup.

**Expected impact:** Filter out tokens that historically get SKIPPED — should reduce ~10-20% of low-quality setups.

---

### 3b. Cross-Token Co-Fire Patterns (MEDIUM)

**Problem:** BTC and ETH fire together (currently weight=99.6 from 233 fires in production brain.db). If a strong BTC signal fires, ETH is likely to follow shortly.

**Solution:** When a signal fires for a "leader" token, boost confidence on leader-following tokens.

```python
def cofire_pattern_boost(token, signal, direction):
    """Returns confidence delta if this token co-fires with a high-WR leader."""
    eng = HebbianEngine()
    recall = eng.recall(token, k=30)
    # Look for HIGH-weight associations to other tokens
    for concept, label, weight, count in recall:
        if label == 'token' and weight >= 50 and count >= 50:
            # This token strongly co-fires with another token
            # Boost confidence (they fire together = same wave)
            return +3
    return 0
```

**Caveats:**
- Requires ≥50 co-occurrences (statistical significance)
- Boost only, not penalty (avoid blocking on weak co-fire patterns)
- Log every boost for backtest validation

**Files:** `decider_run.py:context_gate()`, add after token_sentiment.

**Expected impact:** When BTC fires, ETH co-fire gets +3 confidence. In a correlated market, this captures the "wave riding" effect.

---

### 3c. Cluster Detection / Hot Period (MEDIUM)

**Problem:** When many signals co-occur (high co-occurrence cluster in brain.db), this is a "hot period" — market is active and our signals have higher edge. When activity drops, signals are noise.

**Solution:** Compute cluster density — how many concept pairs fire together for this signal.

```python
def cluster_density(signal):
    """Returns 0.0-1.0 density of signal's co-occurrence cluster."""
    eng = HebbianEngine()
    recall = eng.recall(signal, k=50)
    if not recall:
        return 0.0
    total_weight = sum(r[2] for r in recall)
    total_count = sum(r[3] for r in recall)
    # Higher count = more co-occurrences = denser cluster
    if total_count == 0:
        return 0.0
    return min(total_weight / (total_count * 5), 1.0)  # normalize
```

**Action:**
- density ≥ 0.6 → BOOST (+3 confidence, "hot signal")
- density < 0.1 → no boost, no penalty (cold)

**Files:** `decider_run.py:context_gate()`, add after cofire.

**Expected impact:** Boost signals that have dense historical co-occurrence — these are "real" patterns, not noise.

---

### 3d. Regime Match (LOWER PRIORITY)

**Problem:** We compute `_get_current_phase()` from token_speeds. But we don't know if this phase matches the historical winning phases for this signal.

**Solution:** Combine Hebbian cluster weights with current phase to score setup quality.

```python
def regime_match_score(token, signal, current_phase):
    """Returns 0.0-1.0 score: does current phase match signal's winning history?"""
    eng = HebbianEngine()
    # Get phases associated with this signal (e.g., 'falling', 'rising', 'flat')
    recall = eng.recall(signal, k=30)
    phase_weight = 0
    for concept, label, weight, count in recall:
        if label == 'concept' and concept in {'falling', 'rising', 'flat', 'accelerating', 'decelerating'}:
            if concept == current_phase.lower():
                return min(weight / 10, 1.0)  # high weight = strong match
    return 0.5  # neutral
```

**Action:** Score < 0.3 → -5 confidence (regime mismatch).

**Files:** `decider_run.py:context_gate()`, add after cluster_density.

**Expected impact:** Reduce counter-trend trades where phase doesn't match signal's winning history.

---

## Implementation Priority

| Priority | Phase | Why |
|----------|-------|-----|
| **1 (HIGH)** | 3a Token sentiment | Simple, uses existing production brain.db labels (HOT_APPROVED, SKIPPED). Direct filter for chronic losers. |
| **2 (MED)** | 3b Co-fire boost | Low complexity, captures correlated market behavior. BTC↔ETH already proven (weight 99.6). |
| **3 (MED)** | 3c Cluster density | Requires more brain.db data to be meaningful. Defer until 6+ months of trade-outcome writes accumulate. |
| **4 (LOW)** | 3d Regime match | Overlaps with existing `_get_current_phase()`. Marginal benefit. |

## Recommended Timeline

- **Week 1**: Ship 3a (Token sentiment) — 1-day implementation + 1-day A/B test
- **Week 2**: Ship 3b (Co-fire boost) — 2-day implementation + 3-day validation
- **Month 2**: Re-evaluate 3c/3d based on 3a/3b impact data

## Constants (hermes_constants.py)

```python
# ── Phase 3a: Token Sentiment ────────────────────────────────────────────────
TOKEN_SENTIMENT_ENABLED = False        # enable after 1-week backtest validation
TOKEN_SENTIMENT_K = 20                 # top-K recall concepts to evaluate
TOKEN_SENTIMENT_SKIP_THRESHOLD = -0.7  # sentiment ≤ this → SKIP
TOKEN_SENTIMENT_BOOST_THRESHOLD = 0.7  # sentiment ≥ this → +3 confidence
TOKEN_SENTIMENT_BOOST_AMOUNT = 3       # confidence boost on positive sentiment

# ── Phase 3b: Co-Fire Boost ──────────────────────────────────────────────────
COFIRE_BOOST_ENABLED = False           # enable after Phase 3a validates
COFIRE_MIN_WEIGHT = 50                 # minimum synapse weight to count as co-fire
COFIRE_MIN_COUNT = 50                  # minimum co-occurrences for statistical sig
COFIRE_BOOST_AMOUNT = 3                # confidence boost on co-fire match
```

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| 3a over-blocks good tokens (sentiment is noisy) | High skip threshold (-0.7), only 5% of tokens should trigger |
| 3b creates false positives (BTC↔ETH doesn't always lead) | Min count = 50, only verified strong correlations |
| 3c/3d require more data than we have | Defer until 2026-Q4 after 6+ months Hebbian writes |
| Multiple new soft advisories compound | Total boost cap: max +15 confidence across all layers |

## Verification Plan

1. **Backtest each phase** on 2538 historical trades (simulate gate decisions)
2. **A/B test** with 50/50 split for 1 week each
3. **Measure** WR improvement, drawdown, signal survival rate
4. **Re-tune** thresholds based on data

## Files to Modify

| Phase | File | Change |
|-------|------|--------|
| 3a | `hebbian_engine.py` | Add `token_sentiment()` |
| 3a | `decider_run.py` | Wire into context_gate() between rule-based and similar_setup |
| 3a | `hermes_constants.py` | Add TOKEN_SENTIMENT_* constants |
| 3b | `decider_run.py` | Add `cofire_pattern_boost()`, wire after token sentiment |
| 3b | `hermes_constants.py` | Add COFIRE_* constants |
| 3c/3d | `decider_run.py` | Add `cluster_density()` and `regime_match_score()` |
| — | `AGENTS.md` | Document Phase 3 |
| — | `plans/2026-07-29_hebbian-phase3-spec.md` | THIS FILE |

## Decision: Ship 3a first

Token sentiment has the highest expected impact-to-effort ratio:
- Uses existing production brain.db labels (HOT_APPROVED, SKIPPED)
- One new function, one wiring change
- A/B testable in 1 week
- If WR improves 3-5%, ship 3b
- If WR doesn't improve, abandon Hebbian enhancements and stick with WR estimate only

## Open Questions

1. Should sentiment check be HARD block (like similar_setup <30%) or SOFT (advisory)?
   - Recommendation: HARD skip only when sentiment ≤ -0.85 (very strong negative)
2. Should we add Hebbian-only fallback when PostgreSQL similar_setup fails?
   - Recommendation: No, fail-open is already in place
3. Should 3b co-fire boost count token→token OR token→signal?
   - Recommendation: Both, but weight token→signal co-fire higher (more specific)