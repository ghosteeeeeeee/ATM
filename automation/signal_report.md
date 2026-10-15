=== Signal Performance Report ===
Period: Last 6h | 24h (generated 2026-10-15 20:13 UTC)

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No signal met kill criteria (WR<30%, 5+ trades, PnL<-$0.10) |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No signal met boost criteria (WR>55%, 5+ trades, PnL>$0.05) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-short- | SHORT | 0.0% | -$0.37 | 3 (48h) | WATCH — all 3 losses in EXTREME regime (3T 0W 14d); n too small to act; candidate for EXTREME regime multiplier in volatility_gate_v2 if trend continues |
| volume-buildup+ | LONG | 0.0% | -$0.26 | 3 (48h) | ALREADY KILLED 2026-10-14 — VOLUME_BUILDUP_PLUS_ENABLED=False; residual trades from before kill |
| ai-trader-manual | SHORT | 0.0% | -$0.18 | 1 (24h) | WATCH — single manual trade, not auto-signal |
| bb-bounce-v2-long+ | LONG | 33.3% | -$0.12 | 6 (48h) | WATCH — wins NORMAL (14T 67%W +$0.45) and FLAT (4T 100%W +$0.17), loses EXTREME (6T 50%W -$0.08); do NOT kill — profitable overall 14d; EXTREME regime filter candidate if bleed continues |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 50.0% | +$0.52 | 6 (24h) | ACTIVE — sole volume driver; 10T 50%W +$0.80 over 48h; profitable only in EXTREME (58T 34%W +$1.31), loses HIGH/NORMAL — existing regime gating working |
| volume-buildup- | SHORT | 100.0% | +$0.41 | 4 (48h) | ACTIVE |
| pump-chain- | SHORT | 25.0% | +$0.26 | 8 (48h) | ACTIVE — low WR but positive PnL (asymmetric winners); 24h sample only 1 trade -$0.03 |
| r2v2-long3 | LONG | 66.7% | +$0.01 | 3 (48h) | ACTIVE |

ISSUES:
- None: zero direction inversions in last 24h (checked long-signal/SHORT and short-signal/LONG).
- Low activity: only 14 closed trades in 24h (net -$0.16). Below kill-sample thresholds by design — no action taken.
