=== Signal Performance Report ===
Period: Last 6h (EMPTY) | 24h (EMPTY) | 48h (12T, 50% WR, -$0.85) | 7d (163T, 44.2% WR, -$2.78)
Generated: 2026-09-26 11:15 UTC

## ⚠️ CRITICAL: 33-HOUR TRADING DROUGHT

Last trade closed: 2026-09-25 02:26 UTC (33h ago)
Pipeline runs every 1 min — signals ARE being generated (ichimoku, bb-bounce-v2, etc.)
**Compactor outputs 0 tokens to hotset.json.** All signals filtered out.

Root cause: signals generated but fail to survive compaction
- 6 PENDING (5-6 min old, not yet scored)
- 4,075 EXPIRED, 238 SKIPPED, 0 APPROVED
- "No signals above 50% confidence — skipping execution"

**This is the #1 priority — not signal performance tuning.**

---

## KILLED (executed):

| Signal | Dir | WR | PnL | Trades (7d) | Action |
|--------|-----|-----|-----|--------|--------|
| mover+ | LONG | 25.0% | -$1.19 | 8 | KILL — EXTREME=0% (3T), HIGH=40% (5T). Both losing. |
| accel-300-breakout | SHORT | 28.6% | -$0.12 | 7 | KILL — Only fires in EXTREME, 28.6% WR. |

## REGIME-BASED BLOCKS (proposed):

| Signal | Dir | Regime | WR | PnL | Action |
|--------|-----|--------|-----|-----|--------|
| pullback-entry- | SHORT | EXTREME | 33.3% | -$0.76 | Block EXTREME (9T) |
| pullback-entry- | SHORT | NORMAL | 33.3% | -$0.39 | Block NORMAL (3T) |
| pump-chain- | SHORT | HIGH | 20.0% | -$0.60 | Block HIGH (5T) |

## BOOSTED (executed):

| Signal | Dir | WR | PnL | Trades (7d) | Action |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 60.0% | +$0.70 | 5 | Strongest performer |
| grind-trend+ | LONG | 100.0% | +$0.25 | 2 | Small sample, watch |

## LOSERS (watch list):

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 40.9% | -$1.16 | 22 | Losing in EXTREME/NORMAL, break-even in HIGH |
| pump-chain- | SHORT | 45.5% | -$0.93 | 33 | Terrible in HIGH (20%), marginal elsewhere |
| bb-bounce-v2-long+ | LONG | 41.7% | -$0.26 | 12 | Watch — below 45% threshold |
| continuum-osc+ | LONG | 75.0% | -$0.05 | 4 | Good WR but slightly negative PnL |

## WINNERS:

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 60.0% | +$0.70 | 5 | Best performer — boost |
| grind-trend+ | LONG | 100.0% | +$0.25 | 2 | Tiny sample, promising |
| continuum-osc+ | LONG | 75.0% | -$0.05 | 4 | Good WR, near break-even |
| pump-chain+ | LONG | 44.2% | +$0.27 | 43 | Highest volume, slightly positive |

## ISSUES:

1. **CRITICAL: 33h trading drought** — Hotset is empty. Compactor filtering all signals out. Pipeline running but no execution.
2. No signal inversions detected in 24h.
3. `mover+` and `accel-300-breakout` should be killed (proposed above).
4. `pullback-entry-` and `pump-chain-` losing in specific regimes — regime blocks proposed.
