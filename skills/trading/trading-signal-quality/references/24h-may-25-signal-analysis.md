# 24h Signal Analysis — May 25 2026

## Source: PostgreSQL brain.trades + SQLite signals_hermes_runtime.signals

## 31 closed trades (24h window)

### WINNERS — 14 trades, all via profit-monster

All winners were combo signals: `rs-rXXXX,zscore-pump-` (SHORT) or `rs-sXXXX,zscore-pump+` (LONG).
No winner was zscore-pump alone. support_resistance was the entry trigger, zscore-pump confirmed direction.

| Token | Dir | PnL%   | Dur(min) | Signal                       | z-score |
|-------|-----|--------|----------|------------------------------|---------|
| TIA   | LONG  | +1.25 | 59  | rs-s546,zscore-pump+        | 3.2     |
| ME    | SHORT | +1.11 | 75  | rs-r560,zscore-pump-        | 3.1     |
| ENS   | SHORT | +1.09 | 47  | rs-r1934,zscore-pump-       | 3.3     |
| CAKE  | SHORT | +1.08 | 442 | rs-r148,zscore-pump-        | 3.2     |
| AVAX  | LONG  | +1.06 | 416 | rs-s4295,zscore-pump+       | 3.2     |
| AXS   | SHORT | +1.02 | 158 | rs-r52,zscore-pump-         | 3.3     |
| AVAX  | SHORT | +0.95 | 431 | rs-r419,zscore-pump-        | 3.4     |
| LINEA | LONG  | +0.95 | 21  | rs-s552,zscore-pump+        | 3.6     |
| GALA  | LONG  | +0.95 | 429 | rs-s1296,rs-s2793,zscore-pump+ | 3.3  |
| ETH   | LONG  | +0.95 | 579 | rs-s306,zscore-pump+        | 3.4     |
| GALA  | LONG  | +0.93 | 128 | rs-s287,zscore-pump+        | 3.3     |
| MON   | LONG  | +0.92 | 122 | rs-s96,zscore-pump+         | 3.5     |
| ETHFI | LONG  | +0.91 | 135 | rs-s156,zscore-pump+        | 3.3     |
| AXS   | SHORT | +0.11 |  0.1| rs-r40,zscore-pump-         | 3.3     |

**Winner pattern:** z-score 3.0–3.6, combo rs + zscore-pump, profit-monster trailing exit.

---

### LOSERS — 17 trades, 3 failure modes

#### Failure Mode 1: Fast kills — zscore-pump caught falling knife (0–15 min)

```
AXS SHORT  -0.11%   0.1min  rs-r40+zscore-pump-  (instant reversal after SHORT entry)
ME LONG    -0.20%   0.0min  rs-s128+zscore-pump+ (immediate reversal, order filled then reversed)
CHIP SHORT -0.71%  13min   rs-r2142+rs-r279+zscore-pump-
DASH LONG  -0.55%  38min   rs-s95+zscore-pump+
```

z-score 3.0–3.8. Divergence check fired (VEL_THD=-0.5) but too late — momentum already exhausted.

#### Failure Mode 2: Shorting into macro bounce (~02:00 UTC May 25)

```
ADA SHORT  -1.01%  198min  rs-r156+zscore-pump-   z=-3.9
OP SHORT   -1.13%  170min  rs-r116,zscore-pump-   z=-3.7
ZK SHORT   -1.32%  172min  rs-r128,zscore-pump-   z=-3.4
AVAX SHORT -1.00%  172min  rs-r136,rs-r359+zscore-pump-  z=-3.3
ETH SHORT  -0.98%   16min  rs-r8745,zscore-pump-  z=-3.5
SNX SHORT  -0.93%   30min  rs-r200,zscore-pump-   z=-3.1
LINEA SHORT -0.66%  33min  rs-r176,zscore-pump-  z=-3.5
```

All entered ~01:59–02:01 UTC. Caught the exact macro bottom. Direction was correct on a 170-min horizon but entry timing was catastrophically wrong. ETH only lost -0.98% because it stopped out in 16 min; ADA/OP/ZK/AVAX survived 170-200 min and got crushed.

#### Failure Mode 3: Counter-trend LONGs/ SHORTs that never materialized

```
ENS LONG   -0.77%  153min  rs-s68,zscore-pump+  (support bounce failed)
UMA LONG   -0.88%  886min  rs-s192,zscore-pump+ (14+ hours, bounce never came)
MON SHORT  -0.81%   68min  rs-r200,zscore-pump-
```

---

## Key Constants Findings

### 1. Cooldown discrepancy (CRITICAL — likely causing noise re-fires)

```
Memory:     ZSCORE_PUMP_COOLDOWN_BARS = 20  (set 2026-04-22 per memory)
Code file:  ZSCORE_PUMP_COOLDOWN_BARS = 5   (line 600 of hermes_constants.py)
```

5 bars = re-fire every 5 min per coin. Too aggressive — allows the same coin to dominate the hot-set with repeated signals in chop. Memory says it was raised to 20 after cascade flip was disabled. **Must verify which is actually deployed and correct the discrepancy.**

### 2. zscore-pump divergence params need tightening

Current:
```python
ZSCORE_PUMP_DIVERGENCE_VEL_THD  = -0.5   # sharper rejection of tired moves
ZSCORE_PUMP_DIVERGENCE_BARS     = 5       # declining bars to confirm
ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 3.5   # z above this = overextended
```

Proposed:
```python
ZSCORE_PUMP_DIVERGENCE_VEL_THD  = -0.8   # stricter — need sharper rejection
ZSCORE_PUMP_DIVERGENCE_BARS     = 8       # longer window (8 min vs 5 min)
ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 4.5   # allow entries up to 4.5 (ENS/LINEA winners had z=5.4)
```

### 3. Winners always need rs + zscore-pump combo

zscore-pump alone is noise. The system only wins when:
- support_resistance provides the structural level (rs-sXXXX for LONG, rs-rXXXX for SHORT)
- zscore-pump confirms direction and timing
- Both fire together → hot-set entry

**Action:** In hermes_constants, consider raising `ZSCORE_PUMP_THRESHOLD` to 3.5 to reduce solo zscore-pump noise, since solo zscore-pump has never produced a winner.

### 4. Time-of-day filter needed — 02:00 UTC cluster

The 02:00 UTC May 25 short entries (ADA, OP, ZK, AVAX, ETH, SNX, LINEA) all failed together. This looks like a systematic macro liquidity window. Consider a **signal blackout window** around 01:30–03:30 UTC when multiple tokens are likely to liquidate/short-squeeze together.

---

## support_resistance signal status

signals_hermes_runtime.signals shows support_resistance signals were overwhelmingly `EXPIRED` (not reaching hot-set). Only a handful of RS signals reached `EXECUTED`:
- ME LONG support_resistance EXECUTED (88.0 conf)
- MON LONG support_resistance EXECUTED (88.0 conf)
- AVAX SHORT support_resistance EXECUTED (81.0 conf)
- GALA LONG support_resistance EXECUTED (82.02 conf)
- ETHFI LONG support_resistance EXECUTED (88.0 conf)
- LTC SHORT support_resistance EXECUTED (81.34 conf)

All other RS signals expired without execution. The winners all came from combos where RS reached the hot-set AND zscore_pump confirmed.

---

## PnL Summary

```
Winners (profit-monster):  14 trades, avg +0.93%
Losers (atr_sl_hit):       17 trades, avg -0.83%
Net:                       -$0.28 (system lost money in this 24h window)
```

Losses are all from zscore-pump entries catching the wrong side — not from support_resistance failures.