# Multi-Signal Confluence Window Analysis

**Date:** 2026-10-22  
**Data:** 8,920 signals (Oct 7-22) × 9,507 shadow trades × 5,969 PG trades  
**Goal:** Find optimal time window + minimum signal count for confluence that maximizes WR and PnL

---

## TLDR

**60-minute window, 2+ distinct signal types** is the sweet spot. Single-source signals LOSE money (-87.9% total PnL). Confluence with cross-family signals (e.g. bollinger + pump-chain) produces the best results (WR 55.4% vs 48.8% for same-family). LONG signals benefit far more from confluence than SHORT.

---

## 1. The Confluence Boost is Real and Monotonic

At 60-minute window, the more distinct signal types that fire on the same token+direction, the better the outcome:

| Conf Level | N | WR% | AvgPnL% | TotalPnL% | |
|---|---|---|---|---|---|
| 1 (single) | 6,812 | 49.8 | -0.013% | **-87.9%** | ████████████████████████ |
| 2 | 1,323 | 52.0 | +0.131% | **+173.2%** | ██████████████████████████ |
| 3 | 95 | 56.8 | +0.192% | +18.3% | ████████████████████████ |
| 4 | 7 | **85.7** | **+2.087%** | +14.6% | ██████████████████████████████████████████ |

**The single-source signals are dragging the system down.** 6,812 signals with no confluence lost -87.9% total. The 1,425 signals WITH confluence (2+) produced +206% total.

## 2. Window Sweep — 60min is the Sweet Spot

| Window | MinConf | N | WR% | AvgPnL% | TotalPnL% |
|---|---|---|---|---|---|
| 5m | 2 | 304 | 38.2 | -0.062% | -18.9% |
| 15m | 2 | 426 | 45.3 | +0.007% | +3.1% |
| **30m** | **3** | **31** | **67.7** | **+0.468%** | +14.5% |
| **60m** | **2** | **1,425** | **52.5** | **+0.145%** | **+206.0%** |
| 60m | 3 | 102 | 58.8 | +0.322% | +32.9% |
| 120m | 4 | 37 | 67.6 | +0.522% | +19.3% |
| 240m | 4 | 150 | 56.7 | +0.235% | +35.2% |
| 480m | 5 | 76 | 55.3 | +0.086% | +6.5% |

**Best balance:** 60-min window, 2+ signals → n=1,425, WR 52.5%, Total +206%  
**Highest WR (usable):** 60-min window, 3+ signals → n=102, WR 58.8%  
**Highest WR (rare):** 30-min window, 3+ signals → n=31, WR 67.7%

## 3. Cross-Family Beats Same-Family

| Type | N | WR% | AvgPnL% | TotalPnL% |
|---|---|---|---|---|
| Single (Conf=1) | 6,812 | 49.8 | -0.013% | -87.9% |
| Same-family (Conf≥2) | 635 | 48.8 | +0.133% | +84.4% |
| **Cross-family (Conf≥2)** | **790** | **55.4** | **+0.154%** | **+121.6%** |

When 2+ signals from DIFFERENT families (e.g. bollinger + pump-chain, or hmacd + pump-chain) fire together, WR jumps to 55.4%. Same-family confluence (e.g. continuum_osc + continuum_trend) only gets 48.8% — barely better than single-source.

**Reasoning:** Same-family signals share underlying logic and don't provide independent confirmation. Cross-family signals validate from different angles (volume + structure, momentum + trend, etc.).

## 4. LONG Benefits Far More Than SHORT

| Direction | Conf=1 WR | Conf=2 WR | Boost | Conf=1 Total | Conf=2 Total |
|---|---|---|---|---|---|
| **LONG** | 47.5% (n=2,573) | **52.5%** (n=728) | **+5.0pp** | **-180.9%** | **+100.2%** |
| SHORT | 51.2% (n=4,239) | 51.4% (n=595) | +0.2pp | +93.0% | +73.0% |

**LONG single-source signals are catastrophic** (-180.9% total PnL across 2,573 signals). Adding confluence turns them from -180.9% to +100.2%. SHORT signals are roughly neutral with or without confluence.

This aligns with the market regime: the past 2 weeks have been choppy/bearish, so LONG entries need more confirmation.

## 5. Best Signal Pairs (60-min window)

| Pair | N | WR% | AvgPnL% |
|---|---|---|---|
| bollinger_squeeze_long + pump-chain | 42 | **79.4** | **+0.557** |
| bollinger_squeeze_long + pump-chain-v6 | 19 | **89.5** | **+0.907** |
| btc_pump_rider_long + support_resistance | 11 | **90.9** | **+1.208** |
| btc_pump_rider_long + pump-chain | 19 | 73.7 | +1.305 |
| pump-chain + volume_breakout_short | 22 | 77.3 | +1.047 |
| continuum_score_long + support_resistance | 12 | 83.3 | +0.319 |
| hmacd_mtf + pump-chain | 46 | 63.0 | +0.374 |

**Killer combo:** bollinger_squeeze_long + pump-chain (any variant) → WR 79-90%, Avg +0.56-0.91%.

**Worst pairs to avoid:**
| Pair | N | WR% | AvgPnL% |
|---|---|---|---|
| continuum_osc_short + continuum_trend_short | 64 | 33.9 | -0.244 |
| ichimoku_short + volume_buildup_short | 31 | 43.3 | -0.252 |

These are same-family pairs that don't add information.

## 6. Best 3-Signal Combos

| Combo | N | WR% | AvgPnL% |
|---|---|---|---|
| bollinger_squeeze_long + pump-chain + pump-chain-v6 | 12 | **91.7** | **+0.808** |
| continuum_osc_short + continuum_score_short + pump-chain | 6 | **100.0** | +0.560 |

---

## Recommendations

### Tier 1 — Immediate (shadow mode)
1. **Require 2+ distinct signal families within 60 minutes** for any trade entry
   - Would have turned -87.9% (singles) into +206% (confluence)
   - Especially critical for LONG: single-source LONGs lost -180.9%
   
2. **Cross-family requirement** — signals must come from different families, not just different signal types within the same family

### Tier 2 — Higher conviction (optional)
3. **3+ signals in 60 minutes** → WR 58.8%, could size up 1.5x
4. **3+ signals in 30 minutes** → WR 67.7%, could size up 2x (but rare: ~2/day)

### Tier 3 — Pair-specific boosts
5. **Pre-weight** bollinger_squeeze + pump-chain combos (WR 79-90%)
6. **Pre-weight** btc_pump_rider + support_resistance (WR 91%)
7. **Penalize** same-family pairs like continuum_osc + continuum_trend (WR 34%)

---

## Methodology

- **Signals:** 8,920 signals from `signals_hermes_runtime.db` (Oct 7-22, 15 days)
- **Outcomes:** 9,507 shadow trades from `brain/shadow_trades.db` using `first_exit_pnl_pct` (ATR SL/TP engine)
- **Confluence counting:** For each signal, count distinct `signal_type` values on same (token, direction) within [t, t+window]
- **Outcome matching:** Nearest shadow trade within 30 minutes of signal timestamp
- **Limitations:** 15-day window, market-specific (choppy/bearish), first_exit engine not all 10 engines

---

## Data Quality Notes

- 8,920 signals, 9,507 shadow trades, 5,969 PG closed trades
- Shadow DB has MFE/MAE data for 8,657 trades (91%)
- Forward returns (fwd_30m/1h/4h) are empty in shadow DB — used exit engine PnL instead
- All results reproducible from `/tmp/confluence_analysis.py` and `/tmp/confluence_v2.py`
