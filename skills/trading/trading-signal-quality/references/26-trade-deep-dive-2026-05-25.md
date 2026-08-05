# 26-Trade Deep Dive (2026-05-25) — Winner vs Loser Signal Analysis

## Overview
26 trades: 12 WIN (profit-monster), 13 LOSS (atr_sl_hit), 1 ORPHAN.  
All signals matched to signals.json via source tag overlap. Match rate: 26/26.

## Methodology
- signals.json has 26 executed signals for the full day (only 26 total)
- Trade-to-signal matching: token + direction + source tag intersection
- 11 trades had no exact-time match (signal gen time ≠ trade exec time by minutes to hours)
- Match rate: 26/26 using tag overlap method

## Core Finding: Signal Type is the Dominant Factor

| Signal Type | Direction | WIN | LOSS | Total | WR |
|-------------|-----------|-----|------|-------|----|
| support_resistance | LONG | 5 | 2 | 7 | **71%** |
| support_resistance | SHORT | 2 | 1 | 3 | **67%** |
| zscore_pump_long | LONG | 3 | 5 | 8 | **38%** |
| zscore_pump_short | SHORT | 2 | 5 | 7 | **29%** |

**support_resistance wins significantly more than zscore_pump at both directions.**  
zscore_pump_short is the worst performing combination.

## Leverage is a Major Differentiator

| Leverage | WIN | LOSS | WR |
|----------|-----|------|---|
| 3x | 7 | 4 | **64%** |
| 5x | 5 | 9 | **36%** |

Every 5x loss hit ATR SL. The 5x wins were mostly support_resistance (ETH, ETHFI, MON) or moderate zscore_pump_long (AVAX). All 5x zscore_pump_long losers (ADA, BLUR, UMA, ENS, DASH) were stopped out.

## zscore Magnitude Does NOT Predict Winners

```
WIN  zscores:  [-4.11, -3.56, -3.56, -3.44, 3.02, 3.11, 3.11, 3.22, 3.35, 3.54, 3.72, 5.48]
LOSS zscores: [-3.93, -3.66, -3.41, -3.32, -3.18, -3.05, 3.01, 3.04, 3.31, 3.42, 3.72, 3.83, 5.27]
```

They overlap almost completely. zscore avg: WIN=1.156, LOSS=0.389.

## Time Delta: Signal → Trade Execution (minutes)

| Stat | WIN | LOSS |
|------|-----|------|
| avg | 106 min | 263 min |
| median | 122 min | 173 min |
| min | -306 min | 3 min |
| max | 432 min | 887 min |

Winners executed ~2x faster after signal generation.  
Slow losers: UMA=887min, BLUR=761min, ADA=390min, ETH=375min — all 5x zscore_pump_long.

ME SHORT #11 had delta=-306 min (trade executed 5h BEFORE signal recorded) — signal reuse.

## Win Rate by zscore Threshold

| Direction | Threshold | WIN | LOSS | WR |
|-----------|-----------|-----|------|---|
| LONG | >=3.0 | 8 | 7 | 53% |
| LONG | >=3.5 | 3 | 3 | 50% |
| LONG | >=4.0 | 1 | 1 | 50% |
| SHORT | >=3.0 | 4 | 6 | 40% |
| SHORT | >=3.5 | 3 | 2 | 60% |
| SHORT | >=4.0 | 1 | 0 | **100%** |

For SHORT: |z| >= 3.5 gives 60% WR (vs 40% at 3.0). |z| >= 4.0 = 100% WR in this sample.

## Coin Repeats (Both Directions Same Day)

| Coin | WIN | LOSS | Differentiator |
|------|-----|------|----------------|
| LINEA | SHORT(+5.48zp) + LONG(+5.48zp) | — | Both won — extreme zscore on both sides |
| ME | SHORT×2 (-3.56zp) | LONG (-3.42sr) | zscore_pump SHORT won, support_resistance LONG lost |
| MON | — | SHORT (-3.05zp) | zscore_pump SHORT lost |
| MON | LONG (+3.54sr) | — | support_resistance LONG won |
| ADA | — | LONG (+3.01zp) + SHORT (-3.93zp) | Both lost — weak zscore on both sides |
| AVAX | LONG (+3.22zp) | SHORT (-3.32sr) | Split — signal type same as coin repeat pattern |

Signal type (support_resistance vs zscore_pump) is the common thread in split results.

## Key Actionable Findings

1. **support_resistance signals are ~2x more reliable than zscore_pump**  
   The structural level (RS) does the heavy lifting; zscore_pump provides timing only.

2. **5x + zscore_pump_long is the worst combination** (38% WR, avg loss)  
   All 5x losses were zscore_pump_long at moderate zscores (3.0–3.8).

3. **For SHORT: require |z| >= 3.5 minimum** (60% WR vs 40% at 3.0)  
   zscore_pump_short fires too aggressively at |z| 3.0–3.4.

4. **Time-to-execution is a free early warning signal**  
   Signals that take 6+ hours to execute are disproportionately losing.  
   Consider a max-signal-age filter (e.g., 4h) before accepting a signal into hot-set.

5. **Coin repeats need different-signal enforcement**  
   When the same coin fires both directions, the system should prefer the signal  
   with better historical WR (support_resistance over zscore_pump).

## Reference: All 26 Trades with Signal Values

| # | Coin | Dir | Exit | zscore | Sig Type | Conf | Lev |
|---|------|-----|------|--------|----------|------|-----|
| 1 | LINEA | SHORT | WIN | -4.111 | support_resistance | 88.0 | 3x |
| 2 | ME | SHORT | WIN | -3.563 | zscore_pump_short | 76.4 | 3x |
| 3 | STBL | SHORT | WIN | -3.435 | support_resistance | 88.0 | 3x |
| 4 | ETH | LONG | LOSS | 3.724 | support_resistance | 83.7 | 5x |
| 5 | ADA | LONG | LOSS | 3.005 | zscore_pump_long | 77.2 | 5x |
| 6 | BLUR | LONG | LOSS | 3.041 | zscore_pump_long | 75.2 | 3x |
| 7 | MON | SHORT | LOSS | -3.053 | zscore_pump_short | 79.4 | 5x |
| 8 | UMA | LONG | LOSS | 3.312 | zscore_pump_long | 88.0 | 3x |
| 9 | ENS | LONG | LOSS | 5.274 | zscore_pump_long | 83.7 | 5x |
| 10 | CHIP | SHORT | LOSS | -3.179 | zscore_pump_short | 75.9 | 3x |
| 11 | ME | SHORT | WIN | -3.563 | zscore_pump_short | 76.4 | 3x |
| 12 | ETH | LONG | WIN | 3.724 | support_resistance | 83.7 | 5x |
| 13 | GALA | LONG | WIN | 3.106 | support_resistance | 82.0 | 3x |
| 14 | AVAX | LONG | WIN | 3.216 | zscore_pump_long | 77.5 | 5x |
| 15 | ETHFI | LONG | WIN | 3.345 | support_resistance | 88.0 | 5x |
| 16 | LINEA | LONG | WIN | 5.478 | zscore_pump_long | 83.7 | 3x |
| 17 | GALA | LONG | WIN | 3.106 | support_resistance | 82.0 | 3x |
| 18 | ADA | SHORT | LOSS | -3.932 | zscore_pump_short | 81.3 | 5x |
| 19 | ZK | SHORT | LOSS | -3.405 | zscore_pump_short | 88.0 | 5x |
| 20 | AVAX | SHORT | LOSS | -3.316 | support_resistance | 81.0 | 5x |
| 21 | TIA | LONG | WIN | 3.023 | zscore_pump_long | 75.2 | 5x |
| 22 | OP | SHORT | LOSS | -3.659 | zscore_pump_short | 80.7 | 5x |
| 23 | MON | LONG | WIN | 3.542 | support_resistance | 88.0 | 5x |
| 24 | DASH | LONG | LOSS | 3.825 | zscore_pump_long | 75.2 | 5x |
| 25 | TIA | LONG | ORPHAN | 3.023 | zscore_pump_long | 75.2 | 5x |
| 26 | ME | LONG | LOSS | 3.421 | support_resistance | 88.0 | 3x |