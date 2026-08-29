# All Pump Loops — Spec

**Created:** 2026-08-29
**Status:** DISCOVERED — ready for implementation
**Owner:** T (CEO)

---

## Summary

The token correlation network contains **130+ three-node loops** and **20+ four-node loops**, plus the main 10-node pump loop. The network is dense with cycles — tokens form many small high-WR loops, not just one big loop.

---

## 🏆 Top 3-Node Loops (avg WR >= 75%)

| Loop | Avg WR | Each Hop |
|------|--------|----------|
| AVAX → LINK → AXS → AVAX | **94%** | All high WR |
| SKY → GRIFFAIN → ME → SKY | **89%** | Strong entry |
| AXS → ASTER → XRP → AXS | **89%** | Fast cycle |
| AXS → 0G → XRP → AXS | **88%** | Fast cycle |
| CAKE → MERL → 0G → CAKE | **87%** | Loop hop in main loop |
| BSV → ME → 2Z → BSV | **86%** | High volume |
| BSV → JUP → ME → BSV | **85%** | High volume |
| FET → SKY → ONDO → FET | **84%** | Mid-cap cycle |
| XMR → ASTER → 2Z → XMR | **83%** | Cross-loop bridge |
| AVNT → BSV → 0G → AVNT | **82%** | Entry to main loop |

### All 3-Node Loops (130 total)

| # | Loop | Avg WR |
|---|------|--------|
| 1 | AVAX → LINK → AXS → AVAX | 94% |
| 2 | SKY → GRIFFAIN → ME → SKY | 89% |
| 3 | AXS → ASTER → XRP → AXS | 89% |
| 4 | AXS → 0G → XRP → AXS | 88% |
| 5 | CAKE → MERL → 0G → CAKE | 87% |
| 6 | BSV → ME → 2Z → BSV | 86% |
| 7 | BSV → JUP → ME → BSV | 85% |
| 8 | FET → SKY → ONDO → FET | 84% |
| 9 | XMR → ASTER → 2Z → XMR | 83% |
| 10 | AVNT → BSV → 0G → AVNT | 82% |
| 11 | UNI → GRIFFAIN → ME → UNI | 81% |
| 12 | AVAX → LINK → TIA → AVAX | 81% |
| 13 | UNI → SKR → 2Z → UNI | 80% |
| 14 | MON → DASH → 2Z → UNI → MON | 85% |
| 15 | FET → UNI → SKR → FET | 73% |
| 16 | FET → TIA → ONDO → FET | 77% |
| 17 | CAKE → SKR → 0G → CAKE | 77% |
| 18 | FET → NIL → BCH → FET | 76% |
| 19 | UNI → SKR → MORPHO → UNI | 76% |
| 20 | ZK → BSV → 0G → ZK | 78% |

---

## 🔄 Top 4-Node Loops

| Loop | Avg WR |
|------|--------|
| MON → DASH → 2Z → UNI → MON | 85% |
| MON → DASH → 2Z → SKR → MON | 80% |
| MON → DASH → 2Z → ADA → MON | 79% |

---

## 🔗 Main Pump Loop (10 nodes)

```
ME → GRIFFAIN → SKR → BSV → ASTER → CAKE → 0G → BCH → MORPHO → XMR
 86%    73%      62%   62%    80%     80%    60%   57%    50%
```

---

## 📊 Loop Statistics

| Metric | Value |
|--------|-------|
| 3-node loops | 130 |
| 4-node loops | 20+ |
| Main loop | 10 nodes |
| Best 3-node WR | 94% (AVAX→LINK→AXS) |
| Best 4-node WR | 85% (MON→DASH→2Z→UNI) |
| Total unique tokens in loops | ~40 |

---

## 🎯 Usage Ideas

### 1. Loop-Aware Chain Fire

When a token in a loop fires, predict the next 2-3 tokens in the cycle.

```
AVAX fires → LINK (94% WR) → AXS (94% WR) → back to AVAX
```

### 2. Loop Entry Timing

Enter at the start of a high-WR loop for maximum profit.

### 3. Loop Break Detection

When a hop fails, skip subsequent hops in the loop.

### 4. Multi-Loop Arbitrage

If two loops overlap (share tokens), the shared tokens get double-boosted.

### 5. Dashboard Visualization

Show all loops in the dashboard — filter by WR, size, and tokens.

---

## Implementation Priority

| # | Feature | Impact | Effort |
|---|---------|--------|--------|
| 1 | Add all loops to dashboard | HIGH | Small |
| 2 | Loop-aware chain fire | HIGH | Medium |
| 3 | Loop break detection | MEDIUM | Small |
| 4 | Entry timing optimization | MEDIUM | Medium |
| 5 | Multi-loop arbitrage | LOW | Large |
