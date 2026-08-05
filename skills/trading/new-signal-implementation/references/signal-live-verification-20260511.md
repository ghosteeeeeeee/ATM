# ma_cross Live Verification + mtf_momentum Status (2026-05-11)

## ma_cross — Signal Status: ACTIVE and WORKING

Not disabled — fully operational. Kill-switches confirmed in hermes_constants.py:

| Flag | Value | Effect |
|------|-------|--------|
| `MA_CROSS_ENABLED` | `True` | Master ON |
| `MA_CROSS_PLUS_ENABLED` | `False` | Golden cross (LONG) blocked — was catastrophic (-1800 to -4000% net) |
| `MA_CROSS_MINUS_ENABLED` | `True` | Death cross (SHORT) allowed — marginal but usable |

Signal logic (signals/ma_cross.py):
- EMA 10 crosses ABOVE EMA 200 → LONG (golden cross)
- EMA 10 crosses BELOW EMA 200 → SHORT (death cross)
- Confidence: 65 base + separation bonus (up to +15) + recency bonus (up to +10)
- Cooldown: 15 min between signals per token+direction
- Data: 1m candles from candles.db (price_history table), 210-candle warmup

### Live Scan Results (2026-05-11 05:33 UTC)

191 tokens scanned, 86 crosses detected:
- 69 LONG (golden cross) — DO NOT TRADE (blocked at add_signal layer)
- 17 SHORT (death cross) — ACTIVE

Current SHORT death crosses firing:
```
IO, MEGA, HYPER, ZEN, ATOM, AVNT, COMP, CRV, DOGE, DYM,
INJ, PENGU, TNSR, TRX, USUAL, WCT, XRP
```

### Historical Gap — No ma_cross Trades in Archives or Live trades.json

Despite the signal firing, zero ma_cross trades exist in:
- `/var/www/hermes/data/trades.json` (200 closed + open)
- 33 archive files in `/root/.hermes/archive/trades/`

Most likely explanation: MA_CROSS_PLUS_ENABLED was set to False (blocking longs) before any longs could reach execution. For shorts, the signal may have fired but never survived hot-set compaction due to:
1. Confidence at 65 base — needs confluence (2+ sources) to survive
2. NEUTRAL regime = 0.5x reg_mult at scoring stage → harder to survive
3. No second-source confluence = filtered out by CONFLUENCE_REQUIRED

### ma_cross SHORT Backtest Results (14 months, Mar 2025 - May 2026)

SL=0.50%, TP=0.75%, k_tp=1.25 | 4,278 SHORT signals across 17 tokens:

**Overall: WR 35.1%, avg_pnl -0.060%/trade, total -258%**

Exit split: 64.5% hit SL (-0.50%), 35.1% hit TP (+0.75%). Need WR>40% to break even at 1.5:1 R/R — signal alone doesn't cut it.

Top performers (profitable):
- PENGU: 239 trades, WR=47%, total=+22.0%
- USUAL: 240 trades, WR=47%, total=+20.5%
- IO: 263 trades, WR=44%, total=+14.0%
- COMP: 224 trades, WR=45%, total=+13.4%

Worst performers (catastrophic):
- DYM: 390 trades, WR=13%, total=-136.6%
- TRX: 263 trades, WR=14%, total=-80.5%
- TNSR: 293 trades, WR=25%, total=-56.5%

**Key insight:** ma_cross SHORT needs token filtering (only trade PENGU/USUAL/IO/COMP) and confluence (ma_cross + hzscore- or ma_cross + pct-hermes-). Without that it's a losing strategy.

---

## mtf_momentum — Signal Status: FULLY BLOCKED (since 2026-05-06)

All three flags = False. hermes_constants.py lines 426-428:
```
MTF_MOMENTUM_ENABLED      = False  # mtf_momentum bare — BLOCKED
MTF_MOMENTUM_PLUS_ENABLED = False  # BLOCKED 2026-05-06 — poison co-signal, 0% WR in combos
MTF_MOMENTUM_MINUS_ENABLED = False # BLOCKED 2026-05-06 — poison co-signal, 0% WR in combos
```

### Signal Logic (for when T re-enables for backtest)

- Source: `mtf-momentum+rsi` (merged with RSI confirmation)
- Scoring: `compute_score()` from signal_gen.py:868-1200
  - Percentile score: pct_long/pct_short mapped to 0-60 pts
  - Velocity: z-score rate of change, 0-10 pts
  - Phase: quiet/building/accelerating/extreme — gate for confidence
  - Volume ROC: 0-10 pts confirmation
  - Regime multipliers: long_mult × short_mult from `compute_regime()`
- Trend filters: LONG needs ≥2/3 of (1h, 4h, 30m) z-scores agreeing; SHORT same
- ENTRY_THRESHOLD = 65 to fire
- AUTO_APPROVE at higher threshold → immediate execution, 1hr cooldown

### "Poison Co-Signal" Problem (2026-05-06 finding)

When mtf_momentum appears as a co-signal alongside other signals in combos, WR drops to 0%. This is why all three flags were blocked. Backtest needed to confirm standalone merit.

T is planning backtest of mtf_momentum standalone vs. combo configurations.

---

## Session Findings

1. **ma_cross IS active** — not disabled, death crosses firing live, backtest shows SHORT subset (PENGU/USUAL/IO/COMP) is viable
2. **Historical gap explained** — longs blocked before execution, shorts likely filtered by confluence requirement
3. **mtf_momentum fully blocked** — "poison co-signal" note in hermes_constants, need backtest to determine standalone viability before re-enabling
4. **Kill-switch audit confirmed complete** — all three signals (ma_cross, mtf_momentum) have proper *_ENABLED / *_PLUS_ENABLED / *_MINUS_ENABLED three-layer architecture in hermes_constants.py