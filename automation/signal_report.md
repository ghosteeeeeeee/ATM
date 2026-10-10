=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-10-10 11:19 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No signal lost in ALL regimes — regime-block used instead |

REGIME-BLOCKED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 33.3% | -$0.23 | 9 (24h) | HIGH regime blocked (family 'Volume' 0.0x). HIGH 30d: 30% WR -$0.79. EXTREME 72% +$3.80 and NORMAL 67% +$0.31 kept. Fixed dead key 'Volume_Breakout' → 'Volume' in volatility_gate_v2.py HIGH wildcard (signal_family returns 'Volume'). |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No signal met boost bar (WR>55% + 5+ trades + PnL>$0.05) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| hmacd_mtf-- | SHORT | 33.3% | -$0.07 | 3 (24h) | Watch — below kill threshold (needs 5+ trades) |
| volume-breakout-long+ (EXTREME) | LONG | 33.3% | +$0.08 | 3 (7d) | Watch — EXTREME was 72% WR lifetime, 7d dip is noise at n=3 |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 33.3% | +$0.06 | 3 (24h) | OK — small n, positive PnL, EXTREME habitat intact |
| bb-bounce-v2-long+ | LONG | 50.0% | +$0.05 | 4 (24h) | OK — borderline, no action |

ISSUES:
- BUG FIXED: volatility_gate_v2.py HIGH wildcard had `'Volume_Breakout': 0.0` but `signal_family('volume-breakout-long+')` returns `'Volume'` — the intended HIGH block was dead code, letting volume-breakout-long+ bleed HIGH for days. Fixed key to `'Volume'`. Verified: get_combined_multiplier HIGH=0.0, EXTREME=1.0.
- 6h window almost empty (1 signal/group) — low trade throughput, likely quiet market.
- No direction inversions found in 24h.
