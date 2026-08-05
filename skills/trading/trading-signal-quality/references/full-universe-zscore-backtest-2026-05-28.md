# zscore-pump Full-Universe Backtest — 2026-05-28

**Setup:** 110 tokens × 6 lookbacks × 6 thresholds × 2 directions = 72 combos.  
**Data:** candles.db `candles_1m` ordered ASC, ~41 days, 230 tokens (110 eligible after blacklist).  
**Horizon:** 240 bars (4h). **Cooldown:** 20 bars.  
**Runtime:** 437s (7.3 min) with 3 workers. Pre-computed z-arrays architecture.

## Full 72-Combo Results (universe-aggregated)

```
LB   TH   DIR     WR      FIRES     RET
--------------------------------------------------
 30  1.5  LONG  44.5%    98,909  -0.258%
 30  2.0  LONG  44.4%    70,752  -0.280%
 30  2.5  LONG  44.4%    42,191  -0.250%
 30  3.0  LONG  44.5%    19,236  -0.227%
 30  3.5  LONG  43.9%     7,718  -0.141%
 30  4.0  LONG  42.0%     2,861  -0.073%
 30  1.5  SHORT 49.2%   100,392  +0.153%
 30  2.0  SHORT 48.8%    72,745  +0.153%
 30  2.5  SHORT 48.4%    44,352  +0.125%
 30  3.0  SHORT 47.3%    20,537  +0.051%
 30  3.5  SHORT 46.1%     8,163  -0.060%
 30  4.0  SHORT 43.2%     3,008  -0.266%
 50  1.5  LONG  44.3%    83,504  -0.117%
 50  2.0  LONG  44.1%    54,890  -0.283%
 50  2.5  LONG  43.8%    32,594  -0.302%
 50  3.0  LONG  44.2%    16,377  -0.271%
 50  3.5  LONG  43.8%     7,332  -0.232%
 50  4.0  LONG  43.2%     3,089  -0.189%
 50  1.5  SHORT 48.7%    85,037  +0.153%
 50  2.0  SHORT 48.2%    56,460  +0.128%
 50  2.5  SHORT 47.6%    33,865  +0.114%
 50  3.0  SHORT 47.1%    17,233  +0.042%
 50  3.5  SHORT 46.1%     7,773  -0.083%
 50  4.0  SHORT 44.5%     3,268  -0.254%
 75  1.5  LONG  43.9%    75,084  -0.279%
 75  2.0  LONG  43.5%    47,232  -0.290%
 75  2.5  LONG  43.2%    26,594  -0.297%
 75  3.0  LONG  43.5%    13,488  -0.250%
 75  3.5  LONG  43.7%     6,269  -0.132%
 75  4.0  LONG  43.6%     2,848  -0.029%
 75  1.5  SHORT 48.3%    76,278  +0.125%
 75  2.0  SHORT 47.5%    47,417  +0.128%
 75  2.5  SHORT 47.4%    26,593  +0.133%
 75  3.0  SHORT 46.6%    13,693  +0.054%
 75  3.5  SHORT 45.8%     6,626  -0.049%
 75  4.0  SHORT 44.7%     3,163  -0.196%
100  1.5  LONG  43.5%    70,006  -0.273%
100  2.0  LONG  43.3%    43,130  -0.276%
100  2.5  LONG  43.4%    23,475  -0.295%
100  3.0  LONG  43.7%    11,813  -0.248%
100  3.5  LONG  43.4%     5,637  -0.157%
100  4.0  LONG  43.5%     2,619  -0.232%
100  1.5  SHORT 48.1%    70,915  +0.139%
100  2.0  SHORT 47.2%    42,460  +0.130%
100  2.5  SHORT 46.3%    23,104  +0.133%
100  3.0  SHORT 46.0%    11,774  +0.061%
100  3.5  SHORT 45.1%     5,825  -0.019%
100  4.0  SHORT 44.0%     2,867  -0.231%
150  1.5  LONG  43.3%    63,243  -0.019%
150  2.0  LONG  43.4%    37,805  -0.183%
150  2.5  LONG  43.2%    19,979  -0.153%
150  3.0  LONG  43.0%     9,751  -0.129%
150  3.5  LONG  42.8%     4,700  -0.136%
150  4.0  LONG  42.5%     2,235  -0.216%
150  1.5  SHORT 47.7%    64,784  +0.160%
150  2.0  SHORT 46.3%    37,577  +0.150%
150  2.5  SHORT 45.1%    19,607  +0.190%
150  3.0  SHORT 44.7%     9,738  +0.197%
150  3.5  SHORT 42.6%     4,837  -0.039%
150  4.0  SHORT 41.3%     2,469  -0.220%
200  1.5  LONG  43.4%    58,568  -0.167%
200  2.0  LONG  43.5%    34,449  -0.150%
200  2.5  LONG  43.6%    18,028  -0.085%
200  3.0  LONG  43.0%     8,695  -0.067%
200  3.5  LONG  41.9%     4,162  -0.169%
200  4.0  LONG  41.9%     1,989  -0.121%
200  1.5  SHORT 47.3%    61,297  +0.169%
200  2.0  SHORT 46.4%    34,644  +0.150%
200  2.5  SHORT 45.3%    17,499  +0.114%
200  3.0  SHORT 44.4%     8,551  +0.002%
200  3.5  SHORT 43.8%     4,169  -0.047%
200  4.0  SHORT 41.5%     2,161  -0.213%
```

## Production Recommendation

**Best balanced config for SHORT-only zscore-pump:**
- LB=150, TH=1.5 — 47.7% WR, 64,784 fires, +0.16%/trade
- Matches production lookback (150) while gaining 3x more signals vs TH=3.0

**Best for signal volume (more confluence opportunities):**
- LB=30, TH=1.5 SHORT — 49.2% WR, 100K fires, +0.15%/trade

**LONG is not viable** — all LONG combos negative avg return. Do not use zscore-pump LONG standalone.

## Why 75% WR Is Not Achievable With Params Alone

The 75%+ live WR comes from:
1. zscore-pump direction (~47-49% SHORT)
2. profit-monster exit (winners avg +1.14%)
3. ATR trailing SL (losers avg -0.61%)

The product: 49% × (winners get +1.14%, losers get -0.61%) = positive expectancy.
Raw signal WR cannot reach 75% without the exit machinery.