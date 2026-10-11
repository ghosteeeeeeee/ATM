# Signal Performance Report
**Generated:** 2026-10-11 16:15 UTC | **Period:** Last 6h | 24h

## Overall Stats
- **24h closed trades:** 19 | **PnL:** +$0.97
- **6h closed trades:** 3 | **PnL:** +$0.65

---

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None killed |

No signal met kill criteria (WR < 30% AND 5+ trades AND net PnL < -$0.10 over 24h). Closest: `volume-breakout-long+` at 0% WR / -$0.23, but only 2 trades — insufficient sample.

---

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None boosted |

No signal met boost criteria (WR > 55% AND 5+ trades AND PnL > $0.05). Closest: `doji-bottom-long` at 75% WR / +$0.35 across 4 tokens, but only 4 trades (needs 5+).

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 0.0% | -$0.23 | 2 | ⚠️ Watch — active since 2026-09-17; kill if 24h sample reaches 5+ trades at this WR |
| ai-trader+ | LONG | 0.0% | -$0.07 | 1 | Watch — new signal (first trade 2026-10-09) |
| r2v2-long4 | LONG | 0.0% | -$0.03 | 1 | Watch — new signal (first trade 2026-10-10) |
| hmacd_mtf-+ | LONG | 0.0% | -$0.02 | 1 | Watch — new signal (first trade 2026-10-09) |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2v2-long3 | LONG | 50.0% | +$0.47 | 2 | Positive, low sample |
| pump-chain+,pump-chain-v6+ | LONG | 33.3% | +$0.39 | 3 | Net positive despite low WR (CFX +$0.63 win covers 2 losses) |
| doji-bottom-long | LONG | 75.0% | +$0.35 | 4 | ⭐ Boost candidate — consistent across 3/4 tokens (NXPC, AIXBT, SYRUP green); 1 more win qualifies for boost |
| bb-bounce-v2-long+ | LONG | 66.7% | +$0.07 | 3 | Green, low sample |
| oversold-bounce+ | LONG | 100.0% | +$0.04 | 1 | Green, single trade |

---

## ISSUES

- **No signal inversions found** in the last 24h. All `*long*` signals traded LONG.
- **Low trade volume:** only 19 closed trades in 24h, 3 in last 6h. Few signals reach statistical thresholds for kill/boost decisions this cycle.
- **volume-breakout-long+** is the top watch-list item: 35 lifetime trades, -$0.23 in last 24h at 0% WR (2 trades). If it continues losing, check regime performance before any kill (winning regimes → volatility_gate_v2 multiplier, not blanket disable).
