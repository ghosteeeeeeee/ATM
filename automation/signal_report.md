=== Signal Performance Report ===
Period: Last 6h | 24h | 7d | Generated: 2026-09-02 16:10 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| accel-300-v3-long+ | LONG | 35.3% | -$0.87 | 17 (24h) | Set ACCEL_300_V3_LONG_ENABLED=False. In NEVER_REENABLE, re-enabled with fixes that didn't work. ALL ATR_SL hits. |
| range-reversion-long+ | LONG | 16.7% | -$0.62 | 6 (24h) | Set RANGE_REVERSION_ENABLED=False, RANGE_REVERSION_PLUS_ENABLED=False. In NEVER_REENABLE, re-enabled with fixes that didn't work. ALL ATR_SL hits. |

ALREADY KILLED (verified):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| accel-300-v2-long | LONG | 28.6% | -$0.74 | 21 (7d) | Already False. In NEVER_REENABLE. |
| accel-300-v2-short- | SHORT | 27.3% | -$0.20 | 11 (7d) | Already False. In NEVER_REENABLE. |
| pump-catcher+ | LONG | 29.4% | -$0.35 | 17 (7d) | Already False. In NEVER_REENABLE. |
| atr-spike+ | LONG | 28.6% | -$0.15 | 7 (7d) | Already False. In NEVER_REENABLE. |

WATCH LIST:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| slow-grind- | SHORT | 25.0% | -$0.30 | 4 (7d) | Borderline (4T < 5T kill threshold). All ATR_SL. Monitor. |
| confluence-,ichimoku- | SHORT | 28.6% | -$0.46 | 7 (7d) | Combo signal — no individual kill flag. All ATR_SL. |
| bb-bounce-short | SHORT | 60.3% | -$0.24 | 58 (7d) | High WR but negative PnL (avg -$0.004). Sizing issue? |
| bb-bounce-long+ | LONG | 60.0% | -$0.18 | 25 (7d) | High WR but negative PnL. Sizing issue? |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| accel-300-v2- | SHORT | 52.8% | +$1.46 | 72 (7d) | Best performer. No boost needed (already dominant). |
| bb-bounce-long+ | LONG | 83.3% | +$0.08 | 6 (24h) | Strong 24h. Low sample. |
| r2-trend-short4 | SHORT | 100% | +$0.19 | 2 (24h) | Perfect but too few trades. |

ISSUES:
- Two NEVER_REENABLE signals (accel-300-v3-long, range-reversion) were re-enabled on 2026-09-02 with "fixes" that didn't work. Both killed again. NEVER_REENABLE should mean NEVER.
- bb-bounce-short has 60.3% WR but negative PnL — suggests winning trades are small and losing trades are large. R:R imbalance.
- 290 total trades in 7d with -$2.64 net PnL. System is net negative.

STATS:
- 6h: 4 trades, mixed results
- 24h: 40 trades, $-0.87 net
- 7d: 290 trades, $-2.64 net
- Open positions: 5 (all fresh, $0.00 PnL)
