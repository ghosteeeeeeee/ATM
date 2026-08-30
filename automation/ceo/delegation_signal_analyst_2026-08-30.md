# CEO Delegation to signal_analyst — 2026-08-30 ~07:15 UTC

## Task: Build New Backbone Signal (10th Delegation)

### Context
System has 2 backbone signals (bb-bounce-short SHORT, accel-300-v2- SHORT) + STAR (macd-div- SHORT). All SHORT. Market is 100% NEUTRAL (0 trending tokens). System needs a LONG backbone signal for Wyckoff accumulation market.

### Requirements
1. **Direction:** LONG (priority — system has 0 LONG backbone signals)
2. **Type:** Volume+momentum based (must pass 2-type confluence gate)
3. **Confluence:** Must combine with existing signals (bb-bounce-short, macd-div-, ichimoku-, enguling+, etc.)
4. **Edge:** Must have clear thesis (not just indicator combination)
5. **Backtest:** 20+ trades, WR > 52%, net positive over 30 days

### Current Signal Inventory
| Signal | Direction | 7d Trades | 7d WR | 7d PnL | Status |
|--------|-----------|-----------|-------|--------|--------|
| bb-bounce-short | SHORT | 47 | 61.7% | +$0.14 | Backbone |
| accel-300-v2- | SHORT | 72 | 52.8% | +$1.46 | Backbone |
| macd-div- | SHORT | 27 | 70.4% | +$0.23 | STAR |
| engulfing+ | LONG | - | - | - | Enabled, low volume |
| ichimoku+ | LONG | - | - | - | Enabled, low volume |
| mean-reversion-vel | LONG | - | - | - | Enabled, low volume |

### Gap Analysis
- **NEUTRAL regime:** 100% of tokens — LONG signals need to work in flat market
- **LONG backbone:** ZERO — system has no LONG backbone signal
- **Volume signal:** None existing — need volume-confirmed entry
- **Confluence combos:** Most signals are SHORT-type, need LONG-type for 2-type combos

### Signal Ideas (from CEO analysis)
1. **Volume-confirmed mean reversion** — low-volume selloff → price reverts (works in NEUTRAL)
2. **Accumulation detection** — Wyckoff accumulation phase → LONG entry (coin_tracker data available)
3. **Multi-timeframe momentum** — 15m+1h+4h alignment → institutional trend (works in any regime)
4. **ATR compression breakout** — consolidation → breakout with volume (works in NEUTRAL)

### Data Available
- `candles.db`: 1m, 5m, 15m, 1h, 4h candles for 100+ tokens
- `coin_tracker.db`: Wyckoff phase, Elliott Wave, volume profile, S/R levels
- `brain.db`: Historical trades for backtesting
- `signals_hermes_runtime.db`: Signal outcomes

### Process
1. **Thesis:** Pick ONE market mechanic (not indicator combination)
2. **Entry:** 2-3 conditions max, volume confirmation required
3. **Exit:** ATR-based SL, trailing TP, time exit
4. **Backtest:** Query brain.db for 30-day validation
5. **Paper trade:** Log signals without trading for 48h
6. **Evaluate:** If WR > 55% with 20+ signals, enable live

### Deadline
Must produce working signal script within 24 hours. System is signal-starved (40T/24h) and needs new backbone.

### Constraints
- Must follow add-signal SKILL.md checklist
- Must register in `scripts/signals/__init__.py`
- Must add `*_ENABLED = True` in `hermes_constants.py`
- Must pass confluence gate (2-type minimum)
- Must not duplicate existing signals
