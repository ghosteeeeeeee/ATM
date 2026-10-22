# CEO Consult: Multi-Signal Confluence Window

## Context

T asked for a confluence analysis: what time window do we need for multiple different signals to fire on the same coin before the move is "legit"? Goal is to move away from single-source signals.

## Data

- 8,920 signals (Oct 7-22, 15 days) from `signals_hermes_runtime.db`
- 9,507 shadow trades from `brain/shadow_trades.db` (exit engine PnL)
- 5,969 PG closed trades from `brain/trades`

## Key Findings

### 1. Confluence Boost is Monotonic (60-min window)

| Conf Level | N | WR% | Total PnL |
|---|---|---|---|
| 1 (single) | 6,812 | 49.8 | **-87.9%** |
| 2 | 1,323 | 52.0 | **+173.2%** |
| 3 | 95 | 56.8 | +18.3% |
| 4 | 7 | 85.7 | +14.6% |

Single-source signals LOSE -87.9% total. Confluence (2+) turns it into +206%.

### 2. 60-minute window is the sweet spot

- 5m/2+: n=304, WR=38.2%, Total=-18.9% (too tight)
- 15m/2+: n=426, WR=45.3%, Total=+3.1% (still bad)
- **60m/2+: n=1,425, WR=52.5%, Total=+206.0%** (best balance)
- 60m/3+: n=102, WR=58.8%, Total=+32.9%
- 120m/4+: n=37, WR=67.6%, Total=+19.3% (highest WR but rare)
- 240m/4+: n=150, WR=56.7%, Total=+35.2%
- 480m/5+: n=76, WR=55.3%, Total=+6.5% (too loose, dilutes)

### 3. Cross-family > Same-family

| Type | N | WR% | Total PnL |
|---|---|---|---|
| Single | 6,812 | 49.8 | -87.9% |
| Same-family (2+) | 635 | 48.8 | +84.4% |
| **Cross-family (2+)** | **790** | **55.4** | **+121.6%** |

Continuum_osc + continuum_trend doesn't help (same logic). Bollinger + pump-chain is killer (WR 79-90%).

### 4. LONG Needs Confluence, SHORT Doesn't

| Direction | Conf=1 WR | Conf=2 WR | Boost |
|---|---|---|---|
| **LONG** | 47.5% (n=2,573) | **52.5%** (n=728) | **+5.0pp** |
| SHORT | 51.2% (n=4,239) | 51.4% (n=595) | +0.2pp |

Single-source LONGs: **-180.9% total PnL**. With confluence: **+100.2%**.

### 5. Best Pairs (60-min window)

| Pair | N | WR% | AvgPnL% |
|---|---|---|---|
| bollinger_squeeze_long + pump-chain | 42 | 79.4 | +0.557 |
| bollinger_squeeze_long + pump-chain-v6 | 19 | 89.5 | +0.907 |
| btc_pump_rider_long + support_resistance | 11 | 90.9 | +1.208 |
| hmacd_mtf + pump-chain | 46 | 63.0 | +0.374 |

Worst pairs: continuum_osc_short + continuum_trend_short (WR 34%, same-family).

## Proposed Recommendations

### Tier 1 — Immediate (shadow mode)
1. **Require 2+ distinct signal families within 60 minutes** for any trade entry
2. **Cross-family requirement** — signals must come from different families

### Tier 2 — Higher conviction
3. **3+ signals in 60 minutes** → size up 1.5x
4. **3+ signals in 30 minutes** → size up 2x (rare: ~2/day)

### Tier 3 — Pair-specific
5. Pre-weight bollinger_squeeze + pump-chain combos
6. Penalize same-family pairs

## Questions for CEO

1. Is the 60-minute window the right primary gate, or should we use 30min for higher conviction and accept lower trade volume?
2. Should the confluence requirement be enforced at the compactor level (blocking single-source signals) or at the decider level (allowing them but sizing down)?
3. The SHORT side doesn't benefit from confluence (WR 51.2% → 51.4%). Should we exempt SHORT from the confluence requirement, or is the +73% total PnL from confluence-SHORTs still worth the gate?
4. The cross-family requirement adds complexity (need to define signal families). Is the +6.6pp WR boost (48.8% → 55.4%) worth the implementation cost, or is "2+ distinct signal types" sufficient?
5. Should we implement this as a shadow-mode gate first (collect counterfactual data for 7 days) or go straight to enforcement given the strength of the data?

## Constraints

- 15-day data window (choppy/bearish market regime)
- Shadow trades use first_exit engine only (ATR SL/TP), not all 10 engines
- Forward returns (fwd_30m/1h/4h) are empty in shadow DB
- Existing pipeline has CONFLUENCE_REQUIRED flag and signal_compactor.py confluence logic

## Full Report

`reports/20261022-confluence-window-analysis.md` (commit `712acec2`)
