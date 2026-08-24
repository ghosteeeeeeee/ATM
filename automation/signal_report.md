# Signal Performance Report
**Generated:** 2026-08-24 23:08 UTC | **Period:** Last 6h + 24h

---

## KILLED (executed this cycle):

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| ct-hot- | SHORT | 0.0% | -$0.34 | 6 (7d) | KILLED — COIN_TRACKER_HOT_MINUS_ENABLED=False. Added to NEVER_REENABLE. |
| ct-hot+ | LONG | 25.0% | -$0.68 | 8 (24h) | Already killed — COIN_TRACKER_HOT_PLUS_ENABLED=False (prev cycle). |

---

## BOOSTED (executed this cycle):

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No signals meet all boost criteria (WR>55%, PnL>$0.05, 5+ trades, consistent across tokens). |

---

## WINNERS (watch list — potential future boost):

| Signal | Dir | 24h WR | 24h PnL | 24h T | 7d WR | 7d PnL | 7d T | Status |
|--------|-----|--------|---------|-------|-------|--------|------|--------|
| bb_bounce+ | LONG | 88.2% | +$0.95 | 17 | 84.2% | +$0.98 | 19 | ENABLED — consistent across tokens (CHIP, NEO, MNT, ETH) |
| macd-div- | SHORT | 75.0% | +$0.02 | 12 | 75.0% | +$0.02 | 12 | ENABLED — marginal PnL but high WR |
| hzscore- | SHORT | 100.0% | +$0.44 | 2 | 50.0% | +$0.09 | 10 | ENABLED — too few trades for boost |

---

## LOSERS (watch list):

| Signal | Dir | 24h WR | 24h PnL | 24h T | 7d WR | 7d PnL | 7d T | Status |
|--------|-----|--------|---------|-------|-------|--------|------|--------|
| hl_copy_trader | SHORT | 33.3% | -$0.31 | 3 | 20.0% | -$0.55 | 5 | WATCH — HYPE SHORT bleeding |
| confluence-,ct-hot-,macd-div- | SHORT | 0.0% | -$0.32 | 2 | 0.0% | -$0.32 | 2 | WATCH — below kill threshold (need 5+ trades) |
| bb-bounce-short,confluence- | SHORT | 50.0% | -$0.11 | 2 | 50.0% | -$0.11 | 2 | WATCH — need more data |

---

## OPEN POSITIONS (current):

| Signal | Dir | Trades | Avg PnL | Total PnL |
|--------|-----|--------|---------|-----------|
| hl_copy_trader | SHORT | 1 | -$0.080 | -$0.08 |
| bb_bounce+ | LONG | 2 | -$0.035 | -$0.07 |
| hl_copy_trader | LONG | 1 | -$0.060 | -$0.06 |
| ct-hot-,rs-r70 | SHORT | 1 | $0.000 | $0.00 |

---

## DIRECTION INVERSIONS (24h):

**No inversions found.** All signals respect their direction labels.

---

## ISSUES:

- **ct-hot- SHORT permanently dead**: 0% WR across 6 trades. Added to NEVER_REENABLE_FLAGS.
- **hl_copy_trader SHORT on HYPE**: 20% WR, 5 trades, -$0.55 (7d). Other tokens fine — HYPE SHORT-specific issue.
- **Signal starvation**: Only 2 signals with 2+ trades in last 6h. Pipeline may need more signal diversity.

---

## VERIFIED NUMBERS:

All figures queried directly from PostgreSQL brain DB (`trades` table) on 2026-08-24 23:08 UTC. Timezone-naive comparison used (`NOW() AT TIME ZONE 'UTC'`). No OpenMemory queries (skipped per directive).

---

*Report auto-generated. Next report: ~6h from now.*
