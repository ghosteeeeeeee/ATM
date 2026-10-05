=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-10-05 ~10:00 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No blanket kills — mtf-regime-trend- wins in NORMAL (66.7% WR) |

REGIME BLOCKS (executed):
| Signal | Dir | Regime | WR | PnL | Action |
|--------|-----|--------|-----|-----|--------|
| mtf-regime-trend- | SHORT | HIGH | 33.3% | -$0.40 | SIGNAL_TYPE_OVERRIDES → 0.0 (all-time 6T) |
| mtf-regime-trend- | SHORT | EXTREME | 0% | -$0.23 | SIGNAL_TYPE_OVERRIDES → 0.0 (24h 2T) |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 80% | +$0.12 | 5 | signal_compactor weight 1.3→1.4 (BABY/ETC/ETH/HYPE) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-squeeze+ | LONG | 68.4% | -$0.19 | 19 | Watch — high WR but R:R inverted (avg loss > avg win). EXTREME already blocked. |
| bb-bounce-v3-long+ | LONG | 66.7% | +$0.16 | 3 | Watch — below 5T boost threshold. NORMAL already blocked (46.7% WR). |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 80% | +$0.12 | 5 | BOOSTED 1.3→1.4 — 4 winning tokens |
| bb-bounce-v3-long+ | LONG | 66.7% | +$0.16 | 3 | Active, small sample |
| bb-squeeze+ | LONG | 100% (6h) | +$0.13 | 3 | 6h clean, 24h R:R inverted |

ISSUES:
- No direction inversions found (24h).
- mtf-regime-trend SHORT active >24h (first trade 2026-10-02), losing in HIGH/EXTREME, winning in NORMAL — regime-blocked, not killed.
- bb-squeeze+ has 68.4% WR but negative PnL ($-0.19/24h) — wins are small, losses are large. Watch R:R.
- FAMILY_MAP: mtf-regime-trend added (was returning 'Other' — prior sideways issue from 2026-10-03).
- Pipeline restart needed to load volatility_gate_v2.py and signal_compactor.py changes.
