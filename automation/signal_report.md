# Signal Performance Report
**Generated:** 2026-09-14 22:20 UTC | **Period:** Last 6h + 24h

## Overall Stats (24h)
- **Total trades:** 44 | **WR:** 47.7% | **PnL:** -$0.10

---

## KILLED (executed this cycle)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 38.5% | -$0.21 | 13 | **KILLED** — all regimes <50% WR, 6h 0%WR |

**Regime breakdown (pump-chain- SHORT, 24h):**
- EXTREME: 6T, 33% WR, -$0.19
- HIGH: 6T, 33% WR, -$0.03
- NORMAL: 1T, 100% WR, +$0.01 (1 trade, not significant)

**Already killed:** pump-chain+ LONG (PUMP_FLOW_PLUS_ENABLED=False, killed earlier today)

---

## BOOSTED (executed this cycle)

None. No signals met boost criteria (WR >55%, 5+ trades, positive PnL, consistent across tokens).

---

## WINNERS

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| rr-struct-v2+ | LONG | 4 | 100% | +$0.35 | 6 | 66.7% | +$0.09 | ENABLED |
| pullback-entry- | SHORT | 1 | 0% | -$0.06 | 14 | 57.1% | +$0.46 | ENABLED |

**pullback-entry-** — Lifetime: 58T, 62.1% WR, +$2.57. Strong across EXTREME (2T, 100%) and HIGH (9T, 55.6%). Primary profit driver.

**rr-struct-v2+** — New signal (Sep 14), 100% WR in6h across NORMAL regime. Watch for durability.

---

## LOSERS (watch list)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| pump-chain+ | LONG | 1 | 100% | +$0.28 | 7 | 28.6% | -$0.38 | KILLED |
| pump-chain- | SHORT | 4 | 0% | -$0.50 | 13 | 38.5% | -$0.21 | KILLED |

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## ISSUES

- pump-chain+ already killed (PUMP_FLOW_PLUS_ENABLED=False) — old trades still in 24h window
- pump-chain- killed this cycle — all regimes <50% WR, 6h 0% WR trend worsening

---

## KILL AUDIT

| Flag | New Value | Reason | Verified |
|------|-----------|--------|----------|
| PUMP_FLOW_MINUS_ENABLED | False | 24h 38.5%WR -$0.21, all regimes <50% WR | Yes (grep confirmed) |
| Added to NEVER_REENABLE_FLAGS | — | Prevent rotator re-enable | Yes (edit confirmed) |

---

*Report auto-generated. Next report: ~6h from now.*
