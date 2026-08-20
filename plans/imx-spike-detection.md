# Plan: ATR Spike Signal — Catch Single-Candle Breakouts

**Date:** 2026-08-20
**Status:** Open (v3 — ATR-based, fine-tuned)
**Priority:** High — missed a +5.37% move on IMX 1m

## What Happened

IMX had a single-candle spike on 2026-08-19 at 20:51 UTC after 12 minutes of ATR compression:

| Time | Event | ATR% | ATR pctl |
|------|-------|------|----------|
| 20:22:28 | -0.50% drop (ATR expands) | 0.077% | p100 |
| 20:34:33 | ATR starts compressing | 0.049% | p15 |
| 20:39:05 | Deep compression begins | 0.044% | p5 |
| 20:50:38 | Trough (ATR = 0.022%) | 0.022% | p2 |
| 20:51:09 | **+0.40% breakout candle** | 0.049% | p57 |
| 20:51:39 | +0.89% follow-through | 0.108% | p100 |
| 20:56:41 | +2.42% big spike | 0.270% | p100 |
| 21:52:02 | Peak 0.1058 | — | — |

No signals fired. The existing `atr_compression.py` uses 5m candles + volume (too slow, no HL volume). The `pattern_scanner.py` ATR breakout is disabled (0% WR).

## Root Cause

ATR compression → expansion is the exact pattern that preceded the spike, but:
1. `atr_compression.py` requires 5m candles and volume — can't catch 1m moves
2. `pattern_scanner.py` bull/bear flags are disabled (0% WR)
3. No signal normalizes breakout size relative to pre-spike volatility

## Proposed Fix: ATR Spike Signal

### Entry point analysis

| Entry | Price | PnL at peak | Max DD | Notes |
|-------|-------|-------------|--------|-------|
| First candle (20:51:09) | 0.10041 | **+5.37%** | **0.00%** | Never went below entry for 1+ hour |
| Confirmation (20:51:39) | 0.10130 | +4.44% | -0.22% | Slower, worse PnL |

**Enter on the first breakout candle.** No confirmation needed — the first candle held immediately with zero drawdown.

### Signal logic (2 phases, no state machine)

**Phase 1 — Detect compression (every 1m)**
```
rolling_60m_atrs = last 60 ATR-14 values
percentile = how many are <= current ATR
compressed = percentile <= 15 AND atr_pct < 0.05% of price
if compressed:
    save trough_atr = min(trough_atr, current_atr)
    save trough_price = current_price
```

**Phase 2 — Fire on breakout (every 1m while compressed)**
```
candle_move = abs(close - prev_close)
candle_pct = candle_move / prev_close * 100

if candle_pct >= 0.3% AND candle_move >= 5 × trough_atr:
    direction = LONG if close > prev_close else SHORT
    confidence = base + (candle_pct / 0.3) × boost
    FIRES IMMEDIATELY — enter at this candle's close
    reset compression state
```

### Parameters (hermes_constants.py)

```python
ATR_SPIKE_ENABLED              = False   # master kill
ATR_SPIKE_PLUS_ENABLED         = True    # LONG direction
ATR_SPIKE_MINUS_ENABLED        = True    # SHORT direction
ATR_SPIKE_LOOKBACK             = 60      # rolling ATR window (1m candles)
ATR_SPIKE_COMPRESSION_PCTL     = 15      # ATR percentile to qualify as compressed
ATR_SPIKE_COMPRESSION_MAX_PCT  = 0.05    # max ATR% of price
ATR_SPIKE_BREAKOUT_MIN_PCT     = 0.3     # min candle % move
ATR_SPIKE_BREAKOUT_ATR_K       = 5.0     # min candle move as multiple of trough ATR
ATR_SPIKE_CONF_BASE            = 70      # base confidence
ATR_SPIKE_CONF_PCT_BOOST       = 15      # extra conf per 0.1% above threshold
ATR_SPIKE_CONF_CAP             = 92      # max confidence
ATR_SPIKE_COOLDOWN_MIN         = 60      # minutes between fires per token
```

### Files to create/modify

1. **NEW** `scripts/signals/atr_spike.py` — detection logic + scanner
2. **EDIT** `scripts/hermes_constants.py` — add `ATR_SPIKE_*` constants
3. **EDIT** `scripts/signals/__init__.py` — register in fast signals list
4. **EDIT** `scripts/signal_schema.py` — add source gating for `atr-spike`

### Reuse

- `signal_schema.add_signal()` — existing signal writer
- `_atr_1m()` pattern from `pattern_scanner.py` — ATR from close prices
- `price_history` table from `signals_hermes.db` — already populated by `price_collector.py`
- `atr_comp_cache` table in runtime DB — reuse for state persistence
- Same `run(prices_dict)` entry point pattern as other signals

### Key design decisions

1. **No confirmation candle** — first breakout candle is the entry. Had 0% drawdown, +1% better PnL than waiting.
2. **No volume** — HL doesn't provide it. Works without it.
3. **1m timeframe** — catches the move in real-time. 5m is too slow.
4. **Dual threshold** — both % move AND ATR multiple must be met. Filters noise while catching real breakouts.
5. **Compression tracks trough** — the lowest ATR during compression is the reference for the breakout threshold. Normalizes across tokens.
6. **No range/High-Low check** — only close-to-close move. Simplest possible.

### Known ceiling

- Momentum entry, not reversal — catches breakouts but doesn't tell you when to exit (position_manager's ATR engine handles that)
- If the spike is a one-candle wonder that immediately reverses, the signal will still fire — but the follow-through check (price holding above breakout level for 2+ candles) can be added as an optional filter
- Single-candle spikes from compressed states are rare (~1-2 per day across all tokens) — this is a high-conviction, low-frequency signal

## Verification

After implementing, test against IMX data:
```bash
python3 scripts/signals/atr_spike.py --token IMX --verbose
```

Check that it would have fired at 20:51:09 on 2026-08-19.
