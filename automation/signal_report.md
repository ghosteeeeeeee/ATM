# Signal Performance Report
**Generated:** 2026-10-09 23:12 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Trades (6h):** 5 | **PnL:** +$0.29
- **Trades (24h):** 17 | **PnL:** -$0.16
- **Volume anomaly:** Trade volume dropped from ~33/day (days 6-7 ago) to 12-18/day over the last 3 days (~50% decline).

---

## KILLED (executed):

None. No signal met kill criteria (5+ trades 24h, WR<30%, PnL<-$0.10). Sample sizes too small to act.

---

## BOOSTED (executed):

None. No signal met boost criteria (5+ trades 24h, WR>55%, PnL>$0.05).

---

## LOSERS (watch list):

| Signal | Dir | 24h WR | 24h PnL | 24h Trades | Status |
|--------|-----|--------|---------|------------|--------|
| continuum-trend+ | LONG | 0.0% | -$0.17 | 1 | WATCH (n=1) |
| pump-chain+,pump-chain-v6+ | LONG | 0.0% | -$0.16 | 2 | WATCH |
| hmacd_mtf-+ | LONG | 0.0% | -$0.14 | 1 | WATCH (n=1) |
| continuation+ | LONG | 0.0% | -$0.10 | 2 | WATCH |
| pump-chain- | SHORT | 0.0% | -$0.07 | 1 | WATCH |

**Near-miss (72h):** `pump-chain-` SHORT — 20.0% WR over 10 trades but **net +$0.46**. Low-WR/high-R:R profile: 2 trail hits (+$1.14) offset 8 small losses. Not a kill: PnL is positive and 24h sample is n=1. All closed trades in EXTREME regime (9 trades, -$0.11) — but overall positive, so no regime block warranted yet. Keep on watch.

---

## WINNERS:

| Signal | Dir | 24h WR | 24h PnL | 24h Trades | Status |
|--------|-----|--------|---------|------------|--------|
| volume-breakout-long+ | LONG | 100.0% | +$0.30 | 1 | ENABLED |
| bb-bounce-v2-long+ | LONG | 100.0% | +$0.10 | 1 | ENABLED |
| ai-trader+ | LONG | 100.0% | +$0.09 | 1 | ENABLED |
| r2v2-long3 | LONG | 100.0% | +$0.03 | 1 | ENABLED |
| pump-chain+ | LONG | 33.3% | +$0.06 | 3 | ENABLED (marginal) |

---

## SIGNAL INVERSIONS:

**None.** All signals respect direction labels (checked `signal LIKE '%long%' AND direction='SHORT'` and inverse).

---

## ISSUES:
- Trade volume ~50% lower over last 3 days vs earlier in the week. Root cause unknown — could be market conditions, recent filter tightening (LONG_RSI_CEILING 85→75, CONF_FILTER_MAX 92→95 on 2026-10-09), or both. Worth monitoring.
- Previous report (23:04) listed `pump-chain+` 24h PnL as +$0.55; verified current value is +$0.06. This report uses freshly queried numbers.
- No actions executed this cycle — no kill or boost candidates met minimum sample-size thresholds (5+ trades 24h).

---

*Report auto-generated. Next report: ~6h from now.*
