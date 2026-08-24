# Pump Loop Discovery — 2026-08-24

## The Loop

```
ME → GRIFFAIN → SKR → BSV → ASTER → CAKE → 0G → BCH → MORPHO → XMR
 86%    73%      62%   62%    80%     80%    60%   57%    50%
+0.94% +0.55%   +0.22% +0.26% +0.68%  +0.77% +0.10% +0.28% -0.12%
```

**8 hops, 9 tokens, cumulative avg PnL: +3.68%**

The loop cycles: XMR → GRIFFAIN → SKR → BSV → ASTER → CAKE → 0G → BCH → MORPHO → XMR

## Key Stats

- Loop length: 8 hops (9 nodes)
- Entry points: ME → GRIFFAIN (86% WR, 1.8x lift, n=14)
- Entry points: FET → BSV (82% WR, 1.9x lift, n=11)
- Per-hop WR: 50-86%
- Per-hop lift: 1.3-1.8x
- Built from 3,708 trades via correlation_engine.py

## The Chain with Stats

| Hop | Leader | Follower | n | WR | Lift | Avg PnL |
|-----|--------|----------|---|-----|------|---------|
| 1 | ME | GRIFFAIN | 14 | 86% | 1.8x | +0.94% |
| 2 | GRIFFAIN | SKR | 15 | 73% | 1.3x | +0.55% |
| 3 | SKR | BSV | 13 | 62% | 1.3x | +0.22% |
| 4 | BSV | ASTER | 8 | 62% | 1.5x | +0.26% |
| 5 | ASTER | CAKE | 5 | 80% | 1.3x | +0.68% |
| 6 | CAKE | 0G | 5 | 80% | 1.7x | +0.77% |
| 7 | 0G | BCH | 5 | 60% | 1.4x | +0.10% |
| 8 | BCH | MORPHO | 7 | 57% | 1.4x | +0.28% |

Note: MORPHO → XMR is the 9th hop (50% WR, -0.12% PnL) — weakest link.

## Quality Tiers

| Tier | Hops | Quality | Action |
|------|------|---------|--------|
| 🟢 High | 1-2 (ME→GRIFFAIN→SKR) | 73-86% WR | Max confidence |
| 🟡 Medium | 3-6 (SKR→BSV→ASTER→CAKE→0G) | 62-80% WR | Standard confidence |
| 🔴 Low | 7-9 (BCH→MORPHO→XMR) | 50-57% WR | Reduce confidence |

## Reverse Loop (partial)

Some reverse hops work:
- `0G → CAKE: 100% WR` (forward is 80%)
- `GRIFFAIN → ME: 100% WR` (forward is 86%)

## Verified by Independent Audit

- Chain data confirmed in correlations.db
- ME→GRIFFAIN: n=14, wr=85.7% ✓
- chain_fire fired 2× on ADA (from BSV leader) ✓
- Both ADA signals expired (0 executed trades) ✓
