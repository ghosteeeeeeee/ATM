=== Signal Performance Report ===
Generated: 2026-08-16 23:08 UTC

## Period: Last 6h | 24h

### KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No kill candidates below threshold |

### BLOCKED BY USER (cannot kill):
| Signal | Dir | WR | PnL | Trades (24h) | Status |
|--------|-----|-----|-----|--------|--------|
| ct-hot+ | LONG | 16.7% | -$0.61 | 12 | TESTING MODE — DO NOT DISABLE per user (re-enabled 2026-08-16). In NEVER_REENABLE_FLAGS but overridden. |

### BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| r2-trend-long4 | LONG | 66.7% | +$0.05 | 3 (24h) | On watch — needs 5+ trades to boost |

### LOSERS (watch list):
| Signal | Dir | WR | PnL (24h) | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| (null) | LONG | 0% | -$0.14 | 4 | guardian_orphan trades — not a signal bug |
| bb_bounce+ | LONG | 0% | -$0.04 | 2 | Under threshold (needs 5+) |
| hl_copy_trader,range_finder- | SHORT | 0% | -$0.06 | 2 | Under threshold |

### WINNERS:
| Signal | Dir | WR | PnL (24h) | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2-trend-long4 | LONG | 66.7% | +$0.05 | 3 | Healthy |
| r2-trend-long5 | LONG | 100% | +$0.03 | 1 | Sample too small |
| r2-trend-long9 | LONG | 100% | +$0.03 | 1 | Sample too small |
| return_exhaustion_long | LONG | 100% | +$0.04 | 1 | Sample too small |
| bb_bounce+,hzscore- | SHORT | 100% | +$0.10 | 1 | Sample too small |
| r2-trend-long2 (7d) | LONG | 64.7% | +$0.19 | 17 | Best 7d performer |
| bb_bounce+ (7d) | LONG | 58.3% | +$0.21 | 24 | Consistent winner |

### 7d Top Losers (for reference):
| Signal | Dir | WR | PnL | Trades |
|--------|-----|-----|-----|--------|
| wave_catcher+ | LONG | 37.5% | -$0.42 | 8 |
| ct-hot+ | LONG | 42.4% | -$0.42 | 33 |
| range_breakout+ | LONG | 25.0% | -$0.41 | 8 |
| trend_momentum_near_sma+ | LONG | 16.7% | -$0.37 | 6 |

### ISSUES:
- **COIN_TRACKER_HOT conflict**: ct-hot+ is in NEVER_REENABLE_FLAGS (line 926-928) but also set to True (line 1697-1699) with "TESTING MODE — DO NOT DISABLE". These are contradictory. The signal_rotator will skip it per NEVER_REENABLE, but the flag is True. Either remove from NEVER_REENABLE or set flag False.
- **Null signal trades**: 5 guardian_orphan trades closed with $0 or small losses. These are orphaned positions cleaned up by the guardian, not signal bugs.
- **Overall system quiet**: Only 16.7% of 24h trades are from ct-hot+. System activity is low.

### ACTION REQUIRED:
1. Resolve COIN_TRACKER_HOT conflict — either remove from NEVER_REENABLE_FLAGS or disable the flags
2. ct-hot+ has 12 trades at 16.7% WR in 24h — clear loser but user-protected
