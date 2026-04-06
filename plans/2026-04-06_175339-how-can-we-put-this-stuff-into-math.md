# Plan: MACD Rules Engine — Built

## Status: ✅ DONE (2026-04-06)

---

## What Was Built

### 1. `macd_rules.py` — Pure MACD math engine

**Core computation:**
- EMA(12), EMA(26) computed on 40 × 1h Binance candles
- Signal line = EMA(9) of MACD series
- Histogram = MACD − Signal

**State machine captured per token:**
- `regime`: BULL (macd_line > 0) | NEUTRAL | BEAR (macd_line < 0)
- `crossover_freshness`: FRESH_BULL / STALE_BULL / NONE / STALE_BEAR / FRESH_BEAR
- `crossover_age`: candles since last crossover
- `histogram_rate`: momentum acceleration (expansion/contraction)
- `macd_above_signal`, `histogram_positive`: current state bools

**Entry rules encoded:**

```
LONG allowed when ALL of:
  ✓ regime == BULL OR crossover == FRESH_BULL
  ✓ macd_above_signal == True
  ✓ histogram_positive == True
  ✓ histogram_rate >= -0.15 (not fading fast)

SHORT allowed when ALL of:
  ✓ regime == BEAR OR crossover == FRESH_BEAR
  ✓ macd_above_signal == False
  ✓ histogram_positive == False
  ✓ histogram_rate <= +0.15 (not fading for shorts)
```

**Exit/Flip rules encoded:**

```
Exit LONG when:
  • histogram crosses zero down (momentum broken)
  • MACD crosses under signal (fresh)
  • Regime flips to BEAR
  • Histogram fading fast (rate < -0.20)

Flip LONG→SHORT when:
  • Exit LONG signal fires AND regime == BEAR or FRESH_BEAR
  • histogram deeply negative AND still falling
  • MACD far below signal (>20% divergence)

Exit SHORT / Flip Short→Long: mirror logic
```

**Bullish score (-3 to +3):**
Each of 10 votes counts once (no double-counting):
- +1: macd > signal, hist > 0, regime=BULL, FRESH_BULL, hist_rate > 0.1
- -1: macd < signal, hist < 0, regime=BEAR, FRESH_BEAR, hist_rate < -0.1

---

### 2. Integrated into `position_manager.py`

Replaced the simple `macd_state == 'cross_under'` check with `get_macd_exit_signal()` from macd_rules.py:
- Uses full state machine (not just current crossover)
- Triggers `should_flip` OR `should_exit` with specific reasons
- Logs MACD state on every tick: `bull_score`, `regime`, `xover freshness`, `histogram rate`

---

### 3. Integrated into `signal_gen.py` as entry guard

Before any new signal is emitted, both LONG and SHORT are checked:
- If both `long_entry_allowed` and `short_entry_allowed` are False → token skipped entirely
- Logs MACD state per token: `bull_score`, `regime`, `long=ALLOWED/BLOCKED`, `short=ALLOWED/BLOCKED`

---

## How to Validate

```bash
# Test MACD rules on any token
python3 /root/.hermes/scripts/macd_rules.py TRB IMX ETH BTC SOL

# Run signal_gen and watch for [macd_rules] log lines
python3 signal_gen.py 2>&1 | grep -i macd

# Run position_manager on open positions
python3 position_manager.py 2>&1 | grep -i "MACD\|macd_rules"
```

---

## What the Output Tells You

```
TRB | regime=BULL | xover=STALE/NONE (age=2) | hist=-0.010764 (rate=-0.733) | bullish_score=-2
  → LONG BLOCKED | SHORT BLOCKED
  → EXIT LONG: ['histogram_zero_cross_down', 'histogram_fading_fast']
  → FLIP LONG→SHORT: ['bear_momentum_accelerating']
```

- `regime=BULL` but `hist=-0.010764` → macd_line above zero but histogram already negative (early warning)
- `histogram_rate=-0.733` → momentum plummeting fast
- `bullish_score=-2` → 2 bearish indicators outweigh 1 bullish (macd above signal)
- EXIT LONG + FLIP LONG→SHORT → position manager will close LONG and flip to SHORT

---

## Key Improvement Over Old Logic

| Old | New |
|-----|-----|
| `macd_state == 'cross_under'` | Full state: regime + crossover freshness + histogram momentum + divergence |
| Immediate flip on any cross_under | Flip only when market confirms (BEAR regime OR FRESH_BEAR + momentum aligned) |
| No entry guard | Entry guard: if MACD rules say market isn't in valid regime, no signal emitted |
| No exit signals | Exit signals tracked separately from flip signals |
| No age tracking | crossover_age tracked — stale crossovers don't block entries |

---

## Next Steps (if needed)

1. **Backtest**: Replay TRB/IMX/SOPH/SCR historical 1h candles, check if new entry guard would have rejected the bad LONG entries
2. **Tune thresholds**: histogram_rate trigger at ±0.15 vs ±0.10 — adjust based on backtest
3. **Add to ai_decider scoring**: `bullish_score` (-3 to +3) can be added as a weighting factor in the scoring matrix