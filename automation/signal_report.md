=== Signal Performance Report ===
Generated: 2026-08-25 | Period: Last 6h + 24h + 7d

## System Totals (24h)
- Trades: 86 | WR: 55.8% | PnL: -$1.54

---

## KILLED (already executed — no new kills needed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| ct-hot+ | LONG | 36.4% (7d) | -$3.65 (7d) | 66 (7d) | KILLED 2026-08-24, NEVER_REENABLE. 24h trades are residual from before kill. |
| macd-div+ | LONG | 20.0% (7d) | -$0.55 (7d) | 5 (7d) | KILLED 2026-08-23. Dead signal, no edge. |

---

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+ | LONG | 87.5% (24h) / 82.6% (7d) | +$0.86 (24h) / +$1.21 (7d) | 16 (24h) / 23 (7d) | Top performer. Already has combo multipliers in signal_compactor. Consistent across 14 tokens. |

---

## WATCH LIST (approaching kill criteria)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| hl_copy_trader | SHORT | 25.0% | -$0.52 | 4 (24h) | ONE trade from kill threshold (5+). 7d: 16.7% WR, -$0.76. If next trade loses → kill. |
| tl_break_short | SHORT | 50.0% | -$0.22 | 10 (24h) | Marginal losses. DASH -$0.34, BSV -$0.14 dragging it. DOGE +$0.21 winner. Monitor. |
| macd-div- | SHORT | 69.2% | -$0.14 | 13 (24h) | High WR but negative PnL = small wins, bigger losses. Avg PnL -$0.01/trade. |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+ | LONG | 87.5% | +$0.86 | 16 (24h) | Star performer. 14/16 winners. |
| hl_copy_trader | LONG | 66.7% | +$0.02 | 6 (24h) | Break-even. 7d: 54.5% WR, +$2.49 (66T). Volume play. |
| r2-trend-long4 | LONG | 75.0% | +$0.11 | 8 (7d) | Steady performer. |
| r2-trend-long3 | LONG | 61.5% | +$0.18 | 13 (7d) | Consistent edge. |

---

## ISSUES
- **No signal inversions found.** All LONG signals fire LONG, all SHORT fire SHORT.
- **Overall PnL negative despite 55.8% WR.** Position sizing too small to overcome losing trades. Avg winning trade ~$0.07, avg losing trade ~$0.14. Risk:reward asymmetry needs addressing.
- **ct-hot+ still showing 6 trades in 24h window.** These were opened before the kill on Aug 24. Flag is confirmed False. No action needed.
- **Combo signals (confluence- variants) all losing.** Multi-signal confluence SHORTs not adding value — 0% WR on most. Consider pruning combo rules.

---

## 7d Context
| Signal | Dir | WR | PnL | Trades |
|--------|-----|-----|-----|--------|
| hl_copy_trader | LONG | 54.5% | +$2.49 | 66 |
| bb_bounce+ | LONG | 82.6% | +$1.21 | 23 |
| r2-trend-long3 | LONG | 61.5% | +$0.18 | 13 |
| ct-hot+ | LONG | 36.4% | -$3.65 | 66 |
| hl_copy_trader | SHORT | 16.7% | -$0.76 | 6 |
| macd-div+ | LONG | 20.0% | -$0.55 | 5 |
