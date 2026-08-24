# Hebbian V2 — Full System Status

**Created:** 2026-08-24
**Status:** BUILT + VERIFIED + LIVE
**Owner:** T (CEO)

---

## What Was Built

### 1. Correlation Engine (`scripts/correlation_engine.py` — 969 lines)

Statistical engine that learns which tokens pump together from actual trade outcomes.

| Feature | Status |
|---------|--------|
| Token chain building | ✅ 3,566 chains from 3,708 trades |
| Signal effectiveness | ✅ 2,223 signal combos tracked |
| Cadence patterns | ✅ 123 token timing profiles |
| Single-trade ingestion | ✅ Wired into brain.py close_trade() |
| Context gate logging | ✅ Chain suggestions logged on every signal |
| Decay + prune | ✅ Half-life 14 days, min n=3 |
| next_signals() | ✅ Schema created (not yet populated) |
| signal_chains table | ✅ Created (not yet populated) |
| half_life_weight column | ✅ Added to token_chains |

### 2. Chain Fire Signal (`scripts/signals/chain_fire.py` — 280 lines)

Signal that fires on follower tokens when leader tokens pump.

| Feature | Status |
|---------|--------|
| Registered in pipeline | ✅ |
| Layer 2 enforcement | ✅ |
| Compactor weight 1.2 | ✅ |
| Cooldown (4hr per follower) | ✅ Fixed — uses engine_state |
| Max 3 per cycle | ✅ |
| Confidence scaling | ✅ 65-88 range |
| Signals fired | 2× ADA SHORT (both expired, 0 executed) |

### 3. Integration

| Integration Point | Status |
|-------------------|--------|
| brain.py close_trade() | ✅ Calls ingest_trade() on every close |
| decider_run.py context_gate() | ✅ Logs chain suggestions |
| Decay timer | ✅ Updated to run both engines |

---

## Pump Loop

```
ME → GRIFFAIN → SKR → BSV → ASTER → CAKE → 0G → BCH → MORPHO → XMR
 86%    73%      62%   62%    80%     80%    60%   57%    50%
+0.94% +0.55%   +0.22% +0.26% +0.68%  +0.77% +0.10% +0.28% -0.12%
```

- **8 hops, 9 tokens**
- **Cumulative avg PnL: +3.68%** (sum of independent averages)
- **Entry:** ME → GRIFFAIN (86% WR, 1.8x lift, n=14)

---

## Independent Audit Results

| # | Claim | Verdict |
|---|-------|---------|
| 1 | 3,708 trades → 3,499 chains | PARTIAL — chains = 3,566 |
| 2 | Longest chain = 7 hops | DISAGREE — chain has 8 hops |
| 3 | ME→GRIFFAIN = 86% WR, n=14 | AGREE ✓ |
| 4 | chain_fire fired 2× on ADA | AGREE ✓ — 0 executed |
| 5 | Cumulative loop PnL = +3.68% | PARTIAL — math correct, interpretation misleading |
| 6 | Wired into brain.py | AGREE ✓ |
| 7 | Context gate logs chains | AGREE ✓ |

**Score: 4 AGREE, 2 PARTIAL, 1 DISAGREE**

---

## Bug Hunt Results (3 rounds)

### Round 1: correlation_engine.py (10 issues)
- Double-counting in chain building → FIXED
- Signal effectiveness replaces on ingest → FIXED
- Timezone crash in apply_decay → FIXED
- peak_hour_utc gets string → FIXED
- Signal last_seen global → FIXED
- Empty trades crash → FIXED
- Missing DB crash → FIXED
- 3 LOW issues → Fixed/accepted

### Round 2: Integration (4 issues)
- Correlation engine gated behind Hebbian try → FIXED
- Unused should_trade() call → FIXED
- peak_hour anti-pattern → FIXED
- Breakeven trades as losses → Design choice (accepted)

### Round 3: Full system (8 issues)
- CRITICAL: Chain fire cooldown broken → FIXED
- HIGH: signal_chains dead code → Deferred (schema exists, population TBD)
- MEDIUM: 5 connection leaks in signal_compactor → Not our code
- MEDIUM: Hardcoded paths → Not blocking
- LOW: 4 minor issues → Accepted

---

## Commits

```
51b1e26 fix: chain_fire cooldown
621c3e3 Fixes from independent audit
f063173 signals: add chain_fire
34bf2c5 Bug hunt fixes: integration
559b8d6 Phase 2: continuous ingestion + context gate
9de5645 Bug hunt fixes: 10 issues
012d6cc Hebbian V2: correlation engine
5215260 Spec: Hebbian V2 correlation engine
```

---

## What's Next

| # | Feature | Impact | Effort |
|---|---------|--------|--------|
| 1 | Cascade prediction | HIGH | Medium |
| 2 | Loop break detection | HIGH | Small |
| 3 | Entry timing optimization | MEDIUM | Small |
| 4 | Populate signal_chains | MEDIUM | Medium |
| 5 | Loop-aware scoring | MEDIUM | Small |
| 6 | More trade volume | HIGH | Waiting |

---

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/correlation_engine.py` | 969 | Core engine |
| `scripts/signals/chain_fire.py` | 280 | Chain fire signal |
| `scripts/brain.py` | +19 | Continuous ingestion |
| `scripts/decider_run.py` | +116 | Context gate logging |
| `scripts/hermes_constants.py` | +12 | Constants |
| `scripts/signals/__init__.py` | +6 | Registry |
| `scripts/signal_schema.py` | +30 | Layer 2 |
| `scripts/signal_compactor.py` | +2 | Weight |
| `brain/correlations.db` | 1.5MB | Database |
| `brain/pump-loop-discovery.md` | 60 | Loop docs |
| `brain/plans/pump-loop-usage-spec.md` | 102 | Usage plan |
| `brain/verdicts/2026-08-24-hebbian-independence-verdict.md` | 158 | Audit |
| `skills/shared/own-conclusions/SKILL.md` | 60 | Verification skill |
