# Automation Team Improvements Plan

**Created:** 2026-08-26
**Status:** DRAFT — awaiting CEO approval
**Priority:** HIGH — automation gaps directly impact win rate and system improvement velocity

---

## Executive Summary

The Hermes automation team has 8 LLM agents and 3 learning engines, but two of the three learning engines are broken or stuck. The hebbian system IS working (3,955 trade outcomes, 45/day), but the session learner and self-learner have significant gaps that slow down system improvement.

**Current state:**
- ✅ Hebbian trade learning: WORKING (3,955 outcomes, synapses updating)
- ❌ Session learner: DEAD (0 session_summaries, no session dumps)
- ⚠️ Self-learner: STUCK (only tunes 1 parameter, oscillating in local optimum)
- ❌ A/B learner: DEFUNCT (no timer, never runs)

---

## Issue 1: Session Learner is Dead

### What It Is
`hebbian_session_learner.py` is supposed to scan session/conversation dumps (`sessions/request_dump_*.json`) and learn entity co-occurrences from what T actually discussed. This feeds the hebbian associative memory with conversational context — what topics were discussed together, what decisions were made, what worked.

### Current State
- `session_summaries` table: **0 rows**
- Session dumps directory: likely empty or not being generated
- The learner runs but processes 0 sessions

### Why It Matters
Without session data, the hebbian network only learns from trade outcomes. It misses:
- What T discussed before making a decision
- Which signals/topics were correlated in conversation
- Context about why certain trades were taken
- Learning from debugging sessions and analysis

### Root Cause
The session dumps (`sessions/request_dump_*.json`) are not being generated. This is likely because:
1. The DSH/OpenCode session export mechanism isn't writing to that directory
2. Or the format changed and the learner can't parse it

### Fix

**Option A: Wire OpenMemory → Hebbian Bridge**
- Instead of relying on session dumps, query OpenMemory API for recent conversations
- Extract entities from OpenMemory entries and feed them to hebbian
- This is the modern approach — OpenMemory is the source of truth for sessions

**Option B: Fix Session Dump Generation**
- Investigate why `sessions/request_dump_*.json` isn't being created
- Fix the export mechanism
- Keep the existing learner working

**Recommendation:** Option A — OpenMemory is already the session store, don't duplicate.

### Implementation

```python
# New script: hebbian_openmemory_bridge.py
# Runs every 6 hours via systemd timer
# 1. Query OpenMemory for recent entries (last 6h)
# 2. Extract entities from each entry
# 3. Feed co-occurring pairs to HebbianEngine
# 4. Mark entries as processed (avoid re-processing)
```

**Effort:** Level 2 (new script, single file)
**Risk:** Low — additive, no existing behavior changed

---

## Issue 2: Self-Learner is Stuck in Local Optimum

### What It Is
`self_learner.py` runs daily at 06:00 UTC. It analyzes signal performance and adjusts parameters to improve win rate. It has a `PARAM_CONFIG` dict that defines which parameters can be tuned and their ranges.

### Current State
- Only tunes **1 parameter**: `TREND_FILTER_NEUTRAL_PCT`
- This parameter oscillates between 0.24-0.30 for weeks
- The learner is stuck — it tightens, WR drops, it loosens, WR drops, repeat
- Other parameters in `PARAM_CONFIG` are never tested

### Why It Matters
The self-learner is supposed to be the system's auto-improvement engine. If it's stuck, the system isn't learning from its mistakes. The 48.8% WR (30d) could be improved by tuning other parameters.

### Root Cause
1. `PARAM_CONFIG` only has 2 entries: `TREND_FILTER_NEUTRAL_PCT` and `SPEED_MIN_THRESHOLD`
2. The `param_map` in `tune_signal_params()` only maps 4 signal types to parameters
3. Other signals (r2_trend, hzscore, coin_tracker_hot, etc.) have no tuning parameters defined
4. The learner only tests one parameter at a time — no combinatorial search

### Fix

**Step 1: Expand PARAM_CONFIG**
Add tunable parameters for all active signals:

```python
PARAM_CONFIG = {
    # Existing
    'TREND_FILTER_NEUTRAL_PCT': {'min': 0.20, 'max': 0.60, 'step': 0.05, 'tighten': 'down'},
    'SPEED_MIN_THRESHOLD': {'min': 20, 'max': 80, 'step': 5, 'tighten': 'up'},
    
    # NEW — Signal-specific parameters
    'R2_TREND_LONG_MIN_R2': {'min': 0.50, 'max': 0.85, 'step': 0.05, 'tighten': 'up'},
    'R2_TREND_LONG_MIN_SLOPE': {'min': 0.001, 'max': 0.008, 'step': 0.001, 'tighten': 'up'},
    'R2_TREND_LONG_MAX_RSI': {'min': 60, 'max': 85, 'step': 5, 'tighten': 'down'},
    'R2_TREND_LONG_MIN_PRE_MOVE': {'min': 0.1, 'max': 0.5, 'step': 0.05, 'tighten': 'up'},
    
    'COIN_TRACKER_HOT_MIN_COMPOSITE': {'min': 50, 'max': 75, 'step': 2, 'tighten': 'up'},
    'COIN_TRACKER_HOT_RECENCY_MIN': {'min': 0.20, 'max': 0.50, 'step': 0.05, 'tighten': 'down'},
    
    'BB_BOUNCE_MIN_RSI_DROP': {'min': 10, 'max': 40, 'step': 5, 'tighten': 'up'},
    'BB_BOUNCE_MIN_BB_WIDTH': {'min': 0.01, 'max': 0.05, 'step': 0.005, 'tighten': 'down'},
    
    'HZSCORE_MIN_ZSCORE': {'min': 1.5, 'max': 3.0, 'step': 0.25, 'tighten': 'up'},
    
    # Exit parameters
    'ATR_SL_MIN': {'min': 0.010, 'max': 0.025, 'step': 0.0025, 'tighten': 'down'},
    'ATR_SL_MAX': {'min': 0.025, 'max': 0.050, 'step': 0.005, 'tighten': 'up'},
    'PM_TRAIL_ACTIVATE_PCT': {'min': 0.003, 'max': 0.008, 'step': 0.001, 'tighten': 'down'},
    'PM_TRAIL_DISTANCE_PCT': {'min': 0.001, 'max': 0.005, 'step': 0.001, 'tighten': 'up'},
    
    # Filter parameters
    'SIGNAL_FILTER_RSI_MAX': {'min': 65, 'max': 85, 'step': 5, 'tighten': 'down'},
    'SIGNAL_FILTER_SPEED_MIN': {'min': 30, 'max': 60, 'step': 5, 'tighten': 'up'},
}
```

**Step 2: Expand param_map to cover all active signals**

```python
param_map = {
    'bb_bounce': ['TREND_FILTER_NEUTRAL_PCT', 'BB_BOUNCE_MIN_RSI_DROP', 'BB_BOUNCE_MIN_BB_WIDTH'],
    'bb_bounce_short': ['TREND_FILTER_NEUTRAL_PCT', 'BB_BOUNCE_MIN_RSI_DROP'],
    'r2_trend_long': ['R2_TREND_LONG_MIN_R2', 'R2_TREND_LONG_MIN_SLOPE', 'R2_TREND_LONG_MAX_RSI', 'R2_TREND_LONG_MIN_PRE_MOVE'],
    'r2_trend_short': ['R2_TREND_LONG_MIN_R2', 'R2_TREND_LONG_MIN_SLOPE'],
    'coin_tracker_hot': ['COIN_TRACKER_HOT_MIN_COMPOSITE', 'COIN_TRACKER_HOT_RECENCY_MIN'],
    'hzscore': ['HZSCORE_MIN_ZSCORE'],
    'tl_break': ['TREND_FILTER_NEUTRAL_PCT', 'SPEED_MIN_THRESHOLD'],
    'stop_hunt_reversal_long': ['SPEED_MIN_THRESHOLD'],
    'return_exhaustion': ['SPEED_MIN_THRESHOLD'],
    'spike_exhaustion_short': ['SPEED_MIN_THRESHOLD'],
    'wave_catcher': ['SPEED_MIN_THRESHOLD'],
    'continuation': ['SPEED_MIN_THRESHOLD'],
    'atr_spike': ['SPEED_MIN_THRESHOLD'],
    # Global exit params — tune for ALL signals
    '_global': ['ATR_SL_MIN', 'ATR_SL_MAX', 'PM_TRAIL_ACTIVATE_PCT', 'PM_TRAIL_DISTANCE_PCT'],
    # Global filter params — tune for ALL signals
    '_filters': ['SIGNAL_FILTER_RSI_MAX', 'SIGNAL_FILTER_SPEED_MIN'],
}
```

**Step 3: Add feedback loop tracking**
Track before/after metrics for every parameter adjustment. Revert if WR doesn't improve by 2% after 15+ trades.

**Effort:** Level 2 (modify existing script)
**Risk:** Medium — parameter changes affect live trading. Must have safety guards.

---

## Issue 3: A/B Learner is Defunct

### What It Is
`ab_learner.py` was supposed to analyze SL distances per token, compute regime performance, and write trade patterns. It uses PostgreSQL.

### Current State
- No systemd timer — never runs
- Uses psycopg2 (PostgreSQL) but has no scheduled execution
- The trade_patterns.json file exists but may be stale

### Fix
Either:
1. **Delete it** — the self-learner covers parameter tuning, and the hebbian system covers pattern learning. A/B learner is redundant.
2. **Re-activate it** — add a systemd timer, fix any bugs, integrate with the learning pipeline

**Recommendation:** Delete it. It's redundant with self_learner + hebbian.

**Effort:** Level 1 (delete file, remove references)
**Risk:** Low — nothing depends on it

---

## Issue 4: Hebbian Trade Learning — Verify & Strengthen

### Current State (Verified Working)
- ✅ `position_manager.py` calls `HebbianEngine().learn_trade_outcome()` on every trade close
- ✅ 3,955 trade outcomes in `trade_log` table
- ✅ 45 outcomes in last 24h
- ✅ 27,249 synapses, 16,869 with co_occurrences > 0
- ✅ 16,175 synapses updated in last 7d
- ✅ Synapse weights show real strengthening (0.5 → 4.0+)

### What Could Be Better
1. **Verify the hebbian gate is actually used in trading decisions** — check if `hebbian_trade_boost()` in `decider_run.py` is actually called and influencing confidence
2. **Check if the feedback loop works** — does a winning trade actually strengthen the right concept pairs? Does a losing trade weaken them?
3. **Monitor synapse quality** — are the strengthened synapses meaningful (e.g., "bb_bounce+ → SOL → win") or noise?

### Implementation
Add a monitoring dashboard that shows:
- Top 10 strongest synapses (what the system "knows" works)
- Top 10 weakest synapses (what the system "knows" doesn't work)
- Hebbian gate influence on recent trades (how much did hebbian boost/suppress confidence)

**Effort:** Level 1 (monitoring only, no behavior change)
**Risk:** None

---

## Implementation Priority

| # | Issue | Effort | Impact | Priority |
|---|-------|--------|--------|----------|
| 1 | Self-learner expansion | Level 2 | HIGH — unlocks auto-tuning of 15+ parameters | 🔴 Do first |
| 2 | Session learner → OpenMemory bridge | Level 2 | MEDIUM — enriches hebbian with conversation context | 🟡 Do second |
| 3 | Hebbian monitoring dashboard | Level 1 | LOW — visibility only | 🟢 Nice to have |
| 4 | Delete A/B learner | Level 1 | LOW — cleanup | 🟢 Do anytime |

---

## Success Metrics

After implementation, measure:
1. **Self-learner parameter diversity** — should tune 5+ parameters per week (vs 1 now)
2. **Session learner activity** — should process 50+ entries per day (vs 0 now)
3. **Hebbian synapse quality** — top synapses should correlate with actual winning signals
4. **Win rate trend** — should improve from 48.8% → 52%+ within 2 weeks of self-learner expansion

---

## Files to Modify

| File | Change |
|------|--------|
| `scripts/self_learner.py` | Expand PARAM_CONFIG, param_map, add feedback loop |
| `scripts/hebbian_session_learner.py` | Rewrite to query OpenMemory instead of session dumps |
| `scripts/hebbian_engine.py` | Add monitoring/query functions |
| `config/` | Add systemd timer for OpenMemory bridge |
| `automation/` | Delete ab_learner.py if approved |

---

*Plan created by CEO agent — 2026-08-26*
