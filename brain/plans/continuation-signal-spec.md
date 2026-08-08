# Signal Spec: `continuation` — Re-entry After Profitable Close

## Concept

When a trade closes in profit, the momentum that produced that profit may still be active. This signal scans for re-entry opportunities in the same direction within a short window after close.

**"There is momentum in the current waters. More fish are likely around."**

## Trigger

Trade closes with `pnl_pct > CONTINUATION_MIN_PNL` (default: +0.3%). Window: `CONTINUATION_WINDOW_SEC` seconds after close (default: 300s = 5 min).

## Detection Flow

```
Trade closes (profit-monster, T1, trail)
  → Is close_reason in CONTINUATION_TRIGGER_REASONS? (configurable)
  → Is pnl_pct >= CONTINUATION_MIN_PNL?
  → Is close_time within CONTINUATION_WINDOW_SEC of now?
  → Check price action since close:
      5m:  Still moving same direction? (momentum alive)
      15m: Trend intact? (not reversing)
      1h:  Not exhausted? (RSI not extreme, z-score not extreme)
  → If continuation conditions met → fire signal same direction
```

## Timeframe Analysis

| TF | Purpose | Check |
|----|---------|-------|
| 5m | Momentum alive | Price still moving in trade direction since close, or pulled back <50% of the move |
| 15m | Trend intact | 15m candle closes in trade direction, or shallow pullback |
| 1h | Not exhausted | RSI not overbought (>75 for LONG) / oversold (<25 for SHORT), z-score <2.0 |

## Parameters (hermes_constants.py)

```python
# ── Continuation (re-entry after profitable close) ──────────────────────
CONTINUATION_ENABLED = True
CONTINUATION_PLUS_ENABLED = True        # re-enter LONG after LONG close
CONTINUATION_MINUS_ENABLED = True       # re-enter SHORT after SHORT close
CONTINUATION_MIN_PNL = 0.3              # % — minimum PnL to trigger re-entry
CONTINUATION_WINDOW_SEC = 300           # seconds after close to scan
CONTINUATION_TRIGGER_REASONS = (        # which close reasons trigger scan
    'profit-monster', 'profit-monster-T1', 'profit-monster-trail',
    'profit_monster', 'atr_tp_hit',
)
CONTINUATION_RSI_MAX_LONG = 75          # don't re-enter LONG if 1h RSI > this
CONTINUATION_RSI_MIN_SHORT = 25         # don't re-enter SHORT if 1h RSI < this
CONTINUATION_ZSCORE_MAX = 2.0           # don't re-enter if |z-score| > this
CONTINUATION_PULLBACK_MAX_PCT = 50      # max pullback % of the move to still qualify
CONTINUATION_CONF_BASE = 80
CONTINUATION_CONF_FLOOR = 65
CONTINUATION_CONF_CAP = 90
CONTINUATION_COOLDOWN_MIN = 60          # per-token cooldown (longer than normal)
```

## Source Strings

| Direction | Source | signal_type |
|-----------|--------|-------------|
| LONG | `continuation+` | `continuation_long` |
| SHORT | `continuation-` | `continuation_short` |

## Confluence Bonus

If the original signal's source is also still firing (e.g., `bb_bounce+` is still active), add +5 confidence. This catches "second wave" setups where the original conditions haven't changed.

## What It Does NOT Do

- Does NOT fire on losses (only profit exits)
- Does NOT fire on stale exits (time_exit, peak_exit, regime flip)
- Does NOT fire if price has reversed significantly since close (>50% pullback)
- Does NOT fire if higher TF shows exhaustion (RSI extreme, z-score extreme)

## Data Sources

- **Trade close events**: PostgreSQL `trades` table (close_time, close_reason, pnl_pct)
- **Price action**: candles.db (5m, 15m, 1h)
- **Indicators**: Compute RSI/z-score from 1h candles

## Pipeline Integration

- **Speed**: Fast signal (single-token poll, not full scan) — runs in `STEPS_EVERY_MIN`
- **Layer 1**: Kill-switches, blacklists, cooldown (standard)
- **Layer 2**: `add_signal()` enforcement
- **Layer 3**: `signal_compactor` scoring
