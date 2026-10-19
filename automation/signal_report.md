=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-10-19 08:20 UTC
Volume: 8 closed trades (6h) | 14 closed trades (24h) — low-activity period

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No signal met kill criteria (WR<30% + 5+ trades + PnL<-$0.10, 24h) |

REGIME BLOCKS (executed — regime-based, not blanket kills):
| Signal | Dir | Regime | WR | PnL | Trades | Action |
|--------|-----|--------|-----|-----|--------|--------|
| ai-trader+ | LONG | EXTREME | 26.7% | -$0.71 | 15 (30d) | 0.0 block in volatility_gate_v2 — HIGH 75%WR +$0.11 / NORMAL 50% kept |
| ai-trader- | SHORT | EXTREME | 0.0% | -$0.26 | 3 (30d) | 0.0 block — no winning regime for SHORT side |
| ai-trader-manual | LONG | NORMAL | 14.3% | -$0.28 | 7 (30d) | 0.0 block — EXTREME/FLAT/HIGH all 100%WR winners kept |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No signal met boost criteria (WR>55% + 5+ trades + PnL>$0.05, 24h) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ai-trader-pending | LONG/SHORT | 0.0% | -$0.10 | 2 (FLAT, 30d) | Brand new (first close 10-18) — n too small; EXTREME auto-blocked via 'ai-trader-' substring until proven |
| ai-trader+ | LONG | 33.3% | -$0.70 | 18 (7d) | EXTREME habitat now blocked; HIGH/NORMAL remain — recheck in 48h |
| warrior-sr-confirm+ | LONG | 0.0% | -$0.03 | 1 (24h) | Single trade noise — no action |
| volume-buildup- | SHORT | 0.0% | -$0.03 | 1 (24h) | 7d: 77.8%WR +$0.35 — strong winner, 24h blip ignored |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 66.7% | $0.00 | 3 (24h) | FLAT habitat; EXTREME already blocked 2026-10-16 — hold |
| continuum-trend+ | LONG | 100% | +$0.04 | 2 (24h) | Healthy — below boost threshold (n=2, PnL<$0.05) |
| r2v2-long3 | LONG | 100% | +$0.05 | 1 (24h) | Healthy |
| ai-trader-manual | LONG | 100% | +$0.05 | 1 (24h) | NORMAL now blocked; FLAT/EXTREME/HIGH kept |
| pump-chain-,pump-chain-v6- | SHORT | 100% | +$0.07 | 1 (24h) | Healthy |

ISSUES:
- Zero direction inversions in 24h (signal LIKE %long% AND direction=SHORT or vice versa) — clean.
- 3 open trades outstanding.
- Substring-collision catch during this run: ('EXTREME','ai-trader-') 0.0 key also matches inside 'ai-trader-manual' — fixed by inserting ('EXTREME','ai-trader-manual'): 1.0 before the SHORT key (FIRST MATCH WINS). Verified with 12-case assertion test, all pass.
- ai-trader family added to FAMILY_MAP as 'AI_Trader' in market_phase_gate.py (was 'Other'/ungated composition).
- Low trade volume this period (14 closed/24h) — most signals below statistical thresholds; no action is the correct action.
