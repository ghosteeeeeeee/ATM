=== Signal Performance Report ===
Period: 2026-09-11 | Last 6h + 24h

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 25.0% | -$0.47 | 4 | BB_BOUNCE_V2_LONG_ENABLED = False |
| pump-chain+ | LONG | 22.2% | -$0.62 | 9 | Already killed (PUMP_FLOW_PLUS_ENABLED = False) |

REGIME BLOCKS (executed):
| Signal | Dir | Regime | WR | Action |
|--------|-----|--------|-----|--------|
| pullback-entry- | SHORT | NORMAL | 42.9% | Added Pullback_Entry_Short: 0.0 to NORMAL in volatility_gate_v2.py |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| accel-300-v4-short- | SHORT | 0.0% | -$0.44 | 3 | Blacklisted (accel-300 in blacklist) |
| pullback-entry- | SHORT | 37.5% | -$0.42 | 8 | NORMAL regime blocked, EXTREME/HIGH winners |
| mover+ | LONG | 80.0% | -$0.16 | 5 | High WR but negative PnL — watch |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| mover- | SHORT | 100.0% | $0.46 | 3 | Healthy |
| open-skies+ | LONG | 66.7% | $0.16 | 3 | Healthy |
| pump-chain- | SHORT | 63.2% | -$0.14 | 19 | High WR, slight negative — monitor |

ISSUES:
- No signal inversions detected
- pump-chain+ LONG killed but trades still closing (pre-kill entries)
- accel-300-v4-short- at 0% WR but only 3 trades — too few to blanket kill

ACTIONS TAKED:
1. Set BB_BOUNCE_V2_LONG_ENABLED = False (hermes_constants.py:2177)
2. Added Pullback_Entry_Short: 0.0 to NORMAL regime (volatility_gate_v2.py:231)
