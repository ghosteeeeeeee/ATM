# Reversal Trap Pattern — Root Cause Analysis
**Date:** 2026-05-21
**Session context:** T asked to review all closed trades and diagnose why signals are correct but trades still lose.

---

## The Finding (931 trades, 835 analyzed)

**46% of atr_sl_hit losses are reversal traps** — price moved in our favor first (avg +1.63%), then reversed and hit our SL (avg 0.96% adverse), costing us the gain.

The remaining 54% were straight losses (price went against us immediately — likely bad signal timing or wrong direction).

**On the win side:** 44% of profit-monster wins survived an initial adverse move first, confirming the system CAN be right but needs a wider buffer to survive the "one more overshoot" before reversal.

---

## Root Causes

### 1. zscore_pump signals fire at extremes, fills are off-entry

The signal fires when z_score reaches ±3-4 (extreme), predicting local top/bottom. But fills happen after the move starts — price often overshoots one more candle before reversing. The SL gets placed at nadir × floor, and the overshoot creates adverse movement that sets nadir off-entry.

```
Signal fires at z=+3.8 (LONG on extreme)
Entry filled at local top (price already moved 1-3%)
Price continues up 0.5-1.5% more against our SHORT position
Nadir set at entry (or slightly below)
SL = nadir × 1.007 = very tight to current
Local top forms → price drops → SL hit in 0.3-0.7%
Signal was RIGHT — reversal happens exactly as predicted
But we got stopped out BEFORE the gain materialized
```

### 2. Trailing activation (1%) is too wide for low-ATR tokens

For tokens with 0.03-0.08% ATR (FET, BSV, TAO), a 1% activation threshold = 15-30 candles of movement. The reversal happens in 2-5 candles. Trailing never activates. SL stays at nadir × floor. Reversal hits SL before trailing can tighten.

### 3. SL anchored to nadir (tracks adverse only), not entry

When price moves in our favor, nadir tracks the low/peak. But when price reverses, the nadir-based SL gives back the favorable move. The trailing mechanism is the only way to tighten SL toward current price, but its activation threshold is too coarse for low-ATR tokens.

### 4. profit-monster is doing trailing's job reactively

profit-monster fires at 2-3% fixed gain. By then the reversal is already underway. A proper trailing mechanism would tighten SL much earlier (at 0.3-0.5% favorable), preventing the reversal from ever reaching the SL.

---

## The Numbers

```
atr_sl_hit losses: 620 total
  Reversal traps: 283 (46%) — avg favorable +1.63%, adverse that hit SL 0.96%
  Straight losses: 337 (54%) — went against us immediately

profit-monster wins: 215 total
  Survived initial adverse: 95 (44%) — avg adverse first 1.49%
  Easy wins: 120 (56%) — went our way immediately

Loss reversal traps: 283/620 = 46%
Win survival rate:  95/215  = 44%

Both are ~44-46% — this is the same pattern playing out.
The system survives when SL is just wide enough, loses when it's too tight.
```

---

## Specific Trade Examples (Reversal Traps)

| Token | Dir  | Favorable | Adverse | SL%   | PnL%  | Conf | Close |
|-------|------|-----------|---------|-------|-------|------|-------|
| TAO   | LONG | +0.96%    | -0.25%  | 0.52% | +0.23%| 98.0 | profit-monster |
| TIA   | LONG | +4.43%    | -3.91%  | 0.51% | -0.28%| 85.8 | atr_sl_hit |
| SUI   | LONG | +3.72%    | -3.20%  | 0.01% | -0.02%| 95.8 | atr_sl_hit |
| IMX   | LONG | +6.39%    | -5.86%  | 0.06% | +0.06%| 98.0 | profit-monster |
| DYDX  | LONG | +21.39%   | -20.78% | 0.01% | -0.01%| 95.8 | atr_sl_hit |
| PURR  | SHORT| +2.42%    | -1.51%  | 0.19% | +0.71%| 91.8 | profit-monster |

---

## Key Files

- `/root/.hermes/scripts/tpsl_utils.py` (lines 355-415) — trailing logic, SL computed from nadir
- `/root/.hermes/scripts/hermes_constants.py` — ATR floors and TP parameters
- `/root/.hermes/data/candles.db` — 1m candle data for ATR computation
- `/root/.hermes/archive/trades_analysis.db` — 931 closed trades with full trade record

---

## Recommendations (No changes — report only per T's instruction)

1. **Add profit_lock_sl**: `effective_sl = min(nadir_based_sl, current_price × (1 - lock_pct))` — SL tightens as price moves favorably
2. **Make trailing_activation ATR-proportional**: `trailing_activation = max(0.002, atr_pct × 3)` — 7-8× more responsive for low-ATR tokens
3. **Initialize nadir to entry_price**: `lowest_price = entry_price` on open — prevents off-entry anchor problem
4. **Cap adverse move threshold**: If `pnl_pct > 0.50%`, auto-tighten SL to `current × 0.997` for 5× trades
5. **Store momentum_state in trade history**: `_signal_momentum_state` is NULL for all 931 archived trades — prevents post-hoc analysis

---

## Session Metadata

- **Analysis run:** 2026-05-21, T asked for report-only (no changes)
- **Data source:** `/root/.hermes/archive/trades_analysis.db` — 931 closed trades
- **DB schema:** `trades` table (status, direction, entry_price, exit_price, highest_price, lowest_price, pnl_pct, close_reason, _signal_type, _signal_confidence, _signal_momentum_state)
- **ATR data:** `/root/.hermes/data/candles.db` — 1m candles, `candles_1m(token, ts, open, high, low, close)`
- ** atr_sl_hit:** 620 trades (avg PnL=-0.278%)
- **profit-monster:** 215 trades (avg PnL=+2.678%)
- **Reversal trap rate:** 46% of atr_sl_hit losses
- **Winning survival rate:** 44% of profit-monster wins