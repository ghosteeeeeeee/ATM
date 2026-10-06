=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-10-06 05:12 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| mtf-regime-trend- | SHORT | 0.0% | -$0.53 | 3 (24h) | MTF_REGIME_TREND_MINUS_ENABLED=False + NEVER_REENABLE |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No candidates met WR>55% + PnL>$0.05 + 5T |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-squeeze+ | LONG | 62.5% | -$0.24 | 8 (24h) | Watch — 72h 41T 65.9% +$0.15 still positive. HIGH regime 26T 65.4% WR but -$0.15 (R:R bleed). EXTREME already blocked. No kill. |
| trend-ride+ | LONG | 42.9% | -$0.18 | 7 (24h) | Watch — new signal (T directive 2026-10-05). 6h deteriorated 20%WR -$0.33. All regimes <50% WR but n too small. R:R: losers bigger than winners. |
| bb-bounce-v2-long+ | LONG | 50.0% | -$0.09 | 2 (24h) | Watch — below volume threshold. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 100% | +$0.06 | 1 (24h) | n=1, too small to boost |
| doji-bottom-long | LONG | 100% | +$0.12 | 1 (24h) | n=1, too small to boost |

ISSUES:
- Inversions: 0 found (24h). Clean.
- mtf-regime-trend- SHORT: all 3 regimes already at 0.0 in volatility_gate_v2 (CEO 2026-10-06). Flag was still True — inconsistent. Now aligned False + NEVER_REENABLE.
- bb-squeeze+ HIGH regime: 65.4% WR but negative PnL over 72h — R:R problem (oversold chase / hard_max_loss per prior audits), not win-rate. Left enabled.
- trend-ride+ is 1 day old — premature to kill at 7T despite negative PnL. Monitor 48h.
