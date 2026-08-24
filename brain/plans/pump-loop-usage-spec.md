# Pump Loop Usage — Spec

**Created:** 2026-08-24
**Status:** SPEC
**Owner:** T (CEO)

---

## The Pump Loop

```
ME → GRIFFAIN → SKR → BSV → ASTER → CAKE → 0G → BCH → MORPHO → XMR
 86%    73%      62%   62%    80%     80%    60%   57%    50%
+0.94% +0.55%   +0.22% +0.26% +0.68%  +0.77% +0.10% +0.28% -0.12%
```

Cumulative PnL if you ride the full loop: **+3.68%**

---

## Usage Ideas

### 1. Cascade Prediction (Priority: HIGH)

When a leader fires, predict the next 2-3 tokens in the chain and fire signals on all of them with decreasing confidence.

**Current:** chain_fire fires on 1 follower.
**New:** chain_fire fires on 1st, 2nd, and 3rd followers.

```
ME fires
  → GRIFFAIN (hop 1): conf=85
  → SKR (hop 2): conf=72
  → BSV (hop 3): conf=65
```

**Implementation:**
- Modify `chain_fire.py` to look 3 hops deep
- Decrease confidence by 5 per hop
- Only fire on hops that meet min thresholds

### 2. Loop-Aware Scoring (Priority: MEDIUM)

Tokens in the pump loop get boosted confidence in the signal compactor.

**Implementation:**
- Add `LOOP_TOKENS` set to hermes_constants.py
- If signal token is in LOOP_TOKENS, boost confidence by +3
- If signal token is in LOOP_TOKENS and a loop neighbor just fired, boost by +5

### 3. Entry Timing Optimization (Priority: MEDIUM)

Not all hops are equal. Score hops by quality:

| Hop | Quality | Action |
|-----|---------|--------|
| 1-2 (ME→GRIFFAIN→SKR) | 🟢 High | Max confidence, auto-approve |
| 3-6 (SKR→BSV→ASTER→CAKE→0G) | 🟡 Medium | Standard confidence |
| 7-9 (BCH→MORPHO→XMR) | 🔴 Low | Reduce confidence, manual only |

### 4. Reverse Loop Trading (Priority: LOW)

Some reverse hops work:
- `0G → CAKE: 100% WR`
- `GRIFFAIN → ME: 100% WR`

Could trade the reverse loop when it activates.

### 5. Loop Break Detection (Priority: HIGH)

When a hop fails, skip subsequent hops.

```
BSV → ASTER: LOSS
  → Skip CAKE, 0G, BCH, MORPHO for next 4 hours
```

**Implementation:**
- Track hop failures in correlation_engine
- If hop N fails, set cooldown on hops N+1, N+2, N+3

### 6. Multi-Loop Arbitrage (Priority: LOW)

If two loops overlap, shared tokens get double-boosted.

### 7. Time-Based Loop Activation (Priority: LOW)

Check if the loop activates more at certain hours using cadence data.

---

## Implementation Order

| # | Feature | Impact | Effort |
|---|---------|--------|--------|
| 1 | Cascade prediction | HIGH | Medium |
| 2 | Loop break detection | HIGH | Small |
| 3 | Entry timing optimization | MEDIUM | Small |
| 4 | Loop-aware scoring | MEDIUM | Small |
| 5 | Reverse loop trading | LOW | Medium |
| 6 | Multi-loop arbitrage | LOW | Large |
| 7 | Time-based activation | LOW | Small |
