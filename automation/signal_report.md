=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-10-02 ~16:00 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No candidates met ALL kill criteria |

NOTE: mtf-regime-trend+ LONG (9T 44.4% WR -$0.46) was ALREADY killed earlier today — `MTF_REGIME_TREND_PLUS_ENABLED = False` (auto_1hr 2026-10-02 15:11). Flag re-verified False. Residual closed trades only.

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb-squeeze+ | LONG | 60.0% | +$0.21 | 25 | Weight 1.2x in signal_compactor.py; added to FAMILY_MAP (Squeeze) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| continuum-osc+ | LONG | 50.0% | -$0.04 | 2 | Watch — lifetime 8T 50% -$0.11 |
| pump-chain- | SHORT | 0.0% | -$0.13 | 1 | Watch — single trade, no action |
| bb-squeeze+,rs-s33 | LONG | 0.0% | -$0.10 | 1 | Watch — combo, single trade |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-squeeze+ | LONG | 60.0% | +$0.21 | 25 | Boosted — 24 tokens, multi-token consistent |
| bb-bounce-v3-long+ | LONG | 100.0% | +$0.23 | 3 | Winner — below 5T boost threshold |
| volume-breakout-long+ | LONG | 100.0% | +$0.94 | 2 | Winner — below 5T boost threshold |
| bb-bounce-v2-long+ | LONG | 100.0% | +$0.12 | 2 | Winner — below 5T boost threshold |
| continuum-trend+ | LONG | 100.0% | +$0.32 | 1 | Winner — single trade |

ISSUES:
- No direction inversions found in last 24h.
- bb-squeeze was missing from FAMILY_MAP (returned 'Other') — fixed, added to Squeeze family.
- mtf-regime-trend+ HIGH regime was losing (6T 33.3% -$0.40) but signal already blanket-killed; no regime gate needed.
- No signals met ALL kill criteria this cycle. Low trade volume (52 closed trades/24h) limits sample sizes.
