# Signal Quality vs Quantity Plan — 2026-08-04

## Problem Statement

System generates 18,000+ signals/week but only executes 4. Total PnL: -$4.08. High-volume signals are low quality (lose money). Low-volume signals are high quality (can't scale).

## Current State

| Signal | Generated | Executed | Exec Rate | PnL | WR |
|--------|-----------|----------|-----------|-----|-----|
| zscore_rising_long | 4,729 | 0 | 0.0% | -$0.20 | 0% |
| zscore_rising_short | 4,555 | 0 | 0.0% | -$0.46 | 0% |
| tl_break_long | 1,347 | 0 | 0.0% | -$0.92 | 25% |
| tl_break_short | 998 | 0 | 0.0% | -$0.46 | 34% |
| velocity | 1,224 | 0 | 0.0% | -$0.53 | 0% |
| pattern_wolf | 381 | 0 | 0.0% | -$0.26 | 0% |
| accel_300 | 502 | 1 | 0.2% | -$0.19 | 33% |
| bb_bounce | 111 | 3 | 2.7% | +$0.01 | 0% |

## Root Cause

1. **Quantity without quality** — zscore_rising/tl_break generate thousands but 0 execute
2. **Quality signals have low volume** — accel_300/bb_bounce fire rarely
3. **The mismatch** — high-volume = lose money, low-volume = can't scale

## Fix Strategy (Default: Fix, Don't Disable)

### Priority 1: Fix High-Volume Losers

| Signal | Problem | Fix |
|--------|---------|-----|
| zscore_rising | 0% exec, -$0.66 PnL | Add trend filter + RSI confirmation |
| tl_break | 0% exec, -$1.38 PnL | Already has ADX+EMA — check why 0 execute |
| velocity | 0% exec, -$0.53 PnL | Add momentum confirmation |
| pattern_wolf | 0% exec, -$0.26 PnL | Add trend alignment filter |

### Priority 2: Scale Quality Signals

| Signal | Problem | Fix |
|--------|---------|-----|
| accel_300 | 50% WR but 0.2% exec | Already relaxed — monitor |
| bb_bounce | Quality filters working | Already improved — monitor |
| pattern_scanner | Low volume | Keep as-is |

### Priority 3: New Signal Development

| Approach | Rationale |
|----------|-----------|
| Trend-aligned mean reversion | bb_bounce model — quality over quantity |
| Volume confirmation | Add volume check to all signals |
| Multi-timeframe alignment | 1H trend + 5m entry |

## Implementation Checklist

- [ ] zscore_rising: Add trend filter (1H EMA20/50)
- [ ] tl_break: Debug why 0 execute despite ADX+EMA filters
- [ ] velocity: Add momentum confirmation
- [ ] pattern_wolf: Add trend alignment filter
- [ ] All signals: Add RSI confirmation (LONG < 40, SHORT > 60)
- [ ] Monitor accel_300/bb_bounce for decay
- [ ] Track execution rate improvement

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Execution rate | 0.02% | >1% |
| PnL | -$4.08 | >$0 |
| WR | 26.9% | >40% |
| Trades/day | 4 | >10 |

## Notes

- **Fix is default** — improve signals before disabling
- **Quality over quantity** — 10 good signals > 1000 noise signals
- **Monitor decay** — any signal can lose edge within 48h
