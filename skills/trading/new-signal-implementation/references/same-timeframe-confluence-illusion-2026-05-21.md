# Same-Timeframe Signal Confluence Is Not Real Confluence

**Date:** 2026-05-21
**Source:** Analysis of ~700 closed trades in `trades_analysis.db`, excluding accel-300 and profit-monster

---

## The Core Finding

When signals fire together in the hot-set, they appear to provide "confluence." In reality, if all signals read the **same data source and timeframe**, they are not independent — they are the same read expressed differently. When that read is wrong, ALL signals are wrong simultaneously.

### What the Trade Data Shows

| Signal Combo | Trades | Avg PnL | Total PnL | Win Rate |
|---|---|---|---|---|
| RS_SHORT_NO_ZSP (RS resistance alone) | 96 | +0.87% | +$83 | ~65% |
| RS_LONG_ZSP_LONG (RS support + 1m zscore momentum) | 73 | +0.89% | +$65 | ~50% |
| RS_SHORT_ZSP_SHORT | 43 | -0.23% | -$10 | ~45% |
| RS_LONG_ZSP_LONG (all combos) | 42 | -0.48% | -$20 | ~38% |
| zscore_pump alone (44 trades) | 44 | +9.09% | +$400 | ~55% |

**The illusion:** `rs-sXX,zscore-pump+` looks like "structural support + momentum confirmation." The numbers say otherwise — adding zscore_pump to RS reduces the edge.

**The reason:** Both signals read 1m closes from the same `price_history` table. The zscore_pump momentum reading and the RS support bounce are not independent tests of the same thesis — they are the SAME test expressed at different analytical layers. When the 1m candle closes strong, both fire together. That same candle close IS the local top or bottom.

---

## The Same-Timeframe Problem in Detail

### The 1m Data Monoculture

Every signal in the Hermes system reads from the same data:

| Signal | Data Source | Timeframe |
|---|---|---|
| `zscore_pump` | `price_history` (1m closes) | 1m |
| `rs` (support/resistance) | `price_history` (swing highs/lows from 1m) | 1m |
| `hhh` (HH/HL structure) | `price_history` (swing highs/lows from 1m) | 1m |
| `accel_300` | `price_history` (EMA gap from 1m) | 1m |
| `ema_angle` | `price_history` (EMA angle from 1m) | 1m |

When these combine in hot-set entries, they are NOT orthogonal. They are:

- **Not independent:** Same data source, same timestamp key, same bar-close timing
- **Not multi-timeframe:** No 5m, 15m, or higher confirmation required
- **Not regime-aware at the signal level:** The regime filter exists in signal_compactor, not in individual signal generators

### The Specific Failure Pattern: `rs-sXX,zscore-pump+`

The losing trades from this combo show a consistent pattern:

```
Token  Entry Price  Exit Price  Direction  Duration  PnL
VVV    41.27        41.58       SHORT      39 min    -2.38%   ← price went UP
PURR   0.0695       0.0704      SHORT      509 min   -1.84%   ← price went UP
ATOM   1.284        1.306       LONG       89 min    -1.62%   ← price went DOWN
STBL   0.0319       0.0322      LONG       105 min   -0.93%   ← price went DOWN
```

The entry fires when a 1m candle closes strong. That candle close IS the local extreme. The next 1m candle mean-reverts, and the ATR SL catches the loss.

---

## What Actually Works

### RS_SHORT without zscore_pump: +$83 on 96 trades

RS resistance (SHORT) without any 1m momentum overlay is the **only consistently profitable structural signal** in the archive.

Why: Resistance rejection is a cleaner structural event than support bounce. In crypto markets (which have structural shorting pressure from DeFi, miners, protocols), resistance levels are more reliable.

### The Profit-Monster Exit Is the Real Edge

Every winning trade exited via `profit-monster` (ATR trailing stop), not via any signal-specific TP logic. The edge in the system is:

1. **ATR trailing stop** — locks in profit when momentum fades, doesn't predict direction
2. **Structural resistance** (RS_SHORT) — provides entry edge
3. **No 1m momentum overlay** — avoids the local-extremum trap

---

## Implications for Signal Design

### Principle 1: Multi-Timeframe Required for Real Confluence

Confluence means: the 1m signal confirms the 5m trend confirms the 4h trend. If all signals are 1m, there's no confluence — just repetition.

### Principle 2: zscore_pump Should Not Be Combined with Structural Signals

zscore_pump is a 1m momentum scanner. Adding it to RS or hhh signals doesn't add edge — it adds noise and local-extremum timing risk.

### Principle 3: RS_SHORT Is Directionally More Reliable Than RS_LONG

```
RS_LONG (support): 533 trades in FLAT market = -3.48% avg
RS_SHORT (resistance): 398 trades in FLAT market = +6.65% avg
```

This is consistent with crypto's structural shorting bias.

---

## What NOT to Conclude

- **Do NOT conclude zscore_pump is "good"** because it shows +$400 total. That's +100% wins on 24 trades and -100% losses on 20 trades. The total is the sequence of random outcomes, not skill.
- **Do NOT conclude combining signals always helps.** The data shows the opposite when they're reading the same timeframe.
- **Do NOT conclude profit-monster exits are the problem.** The exit is the only part that works. The entries are the problem.

---

## Audit Action Items

1. **Decouple zscore_pump from RS combos in hot-set scoring** — apply a combo penalty when both signals read the same 1m timeframe
2. **Add multi-timeframe filter to RS** — require 5m candle confirmation before RS signal is eligible for hot-set
3. **Prioritize RS_SHORT edge in signal development** — focus SHORT signal development given directional asymmetry
4. **Consider zscore_pump standalone-only mode** — strip zscore_pump from all structural signal combos