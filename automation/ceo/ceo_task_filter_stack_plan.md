# Brief: Filter Stack Audit — Plan Approval

## Context

The system is functionally frozen. For 24+ hours, 20-25 signals fire per cycle but 0-1 trades execute. The filter stack between signal detection and trade execution is killing everything.

**Data (verified with SQL + pipeline logs):**
- Trade frequency dropped from ~31/day (Sep 28–Oct 5) to ~16/day (Oct 6–12)
- WR dropped from ~55% to ~41% over the same period
- 40+ SHORT signals fired during BTC dump (21:02–21:50, Oct 12). All expired. 0 trades.
- IO SHORT fired at 19:17 (1.5h before dump accelerated), CFX at 21:22, CHIP at 21:02. All on time. All expired.
- 22 PENDING signals at 01:30 with 0 hotset entries.
- BTC pumping → LONG signals fire → RR engine grade F → 0 trades.
- BTC dumping → SHORT signals fire → SHORT-RSI-HARD-FLOOR blocks at RSI < 45 → 0 trades.

**Root causes identified:**

1. **Confluence gate** blocks single-source signals even when they fire 3+ times (return_exhaustion-short × 8 tokens, pump-chain- × 12 tokens during dump)
2. **RR engine** gives grade C/D to SHORT during dumps (R:R looks bad because price already moved) and grade F to BTC LONG during pumps
3. **Penalty gate** crushes 99% confidence to 29-32% via stacked multipliers (vol regime × oscillator × SHORT-NORMAL × RR), below 40% execution threshold
4. **SHORT-RSI-HARD-FLOOR = 45** blocks SHORTs when RSI < 45 — exactly when dumps are happening
5. **SLOPE-FILTER** reads micro-bounces (+0.15%) as "price trending up" during dumps

## Proposed 3-Phase Plan

### Phase 1: Ship temporal confluence (today)
- Spec: `plans/temporal-confluence-spec.md` (committed, SQL bug fixed)
- Counts repeated fires for same token+direction as confluence evidence
- Bypasses ONLY the confluence gate — all downstream filters still apply
- Ship in shadow mode first (48h counterfactual), then flip ON

### Phase 2: Audit RR engine + penalty gate (today/tomorrow)
- Run independent backtest: "If we removed the RR penalty for SHORT during bear structure, what happens?"
- The CEO's own data shows filters reduced trades 2x and WR dropped 14 points
- The filters are removing edge, not protecting it

### Phase 3: Reduce SHORT-RSI-HARD-FLOOR (this week)
- Backtest SHORT performance by RSI band
- If RSI < 45 SHORTs have positive expectancy during bear structure, lower floor or add bear-structure exemption
- CEO already added bear-structure exemption for SHORT_RSI_CEILING (65-75 band) — floor needs same treatment

## What NOT to do
- Don't remove confluence gate entirely (spatial confluence is still valuable)
- Don't remove HALL-SHAME (blocks genuinely bad tokens)
- Don't remove chase block (CEO's quality-tiered exemption handles GRASS case)
- Don't change everything at once — ship one at a time, measure, then next

## Question for CEO

1. Do you approve this 3-phase plan?
2. Priority: Phase 1 (temporal confluence shadow) or Phase 2 (RR engine audit) first?
3. Any filters I'm missing that should be in the audit?
4. For Phase 2: should the RR engine be exempted for SHORT during bear structure, or should the threshold be lowered globally?
5. Risk tolerance: how many additional losses are acceptable while we tune the filter stack?
