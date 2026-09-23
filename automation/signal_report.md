# === Signal Performance Report ===
Period: Last 6h | 24h | 7d  
Generated: 2026-09-23 05:11 UTC

## KILLS (already executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 0.0% | -$1.54 | 6 (24h) | KILLED `PULLBACK_ENTRY_MINUS_ENABLED=False` (2026-09-22 23:12 UTC). 38T/7d 34.2%WR -$2.30. No new signals since kill. |
| open-skies+ | LONG | 20.0% | -$0.42 | 5 (7d) | KILLED `OPEN_SKIES_PLUS_ENABLED=False` (2026-09-22). 3T in HIGH 0%WR. |
| grind-trend- | SHORT | 20.0% | -$0.38 | 5 (7d) | KILLED `GRIND_TREND_MINUS_ENABLED=False` (2026-09-19). |

## BOOSTED:
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 64.7% | +$1.26 | 17 (7d) | WATCH — best performer. EXTREME regime only per volatility_gate_v2. |

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 0.0% | -$0.76 | 3 (24h) | WATCH — 7d is 41.8%WR +$1.23 (55T). 24h is bad luck in EXTREME. |
| pump-chain- | SHORT | 33.3% | -$0.38 | 6 (7d) | OK — 30d is 57.4%WR +$0.24 (61T). 7d is noise. |
| btc-pump-rider+ | LONG | 0.0% | -$0.18 | 3 (30d) | WATCH — 3 trades in 30d, too small to kill. |

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 64.7% | +$1.26 | 17 (7d) | Running hot |
| pump-chain+ | LONG | 41.8% | +$1.23 | 55 (7d) | Net positive despite 24h blip |
| grind-trend+ | LONG | 50.0% | +$0.24 | 18 (7d) | Steady |
| bb-bounce-v2-long+ | LONG | 66.7% | -$0.01 | 3 (7d) | Tiny rounding loss |

## ISSUES:
- **No direction inversions detected**
- **pullback-entry- was bypassing kill flag** — `PULLBACK_ENTRY_MINUS_ENABLED=False` was set at 23:12 UTC Sep 22, but 6 trades from earlier that day still show in the 24h window. Flag is working (no new signals since).
- **System 24h: 21 trades, 38.1% WR, -$1.82 PnL** — dominated by pullback-entry- losses (now killed)
- **System 7d: 185 trades, 45.4% WR, -$0.10 PnL** — roughly breakeven
- **21 signals in NEVER_REENABLE_FLAGS** — loaded correctly

## Actions taken:
- None needed this run — all kill candidates already have flags set
- volume-breakout-long+ flagged for monitoring (boost candidate if trend holds)
