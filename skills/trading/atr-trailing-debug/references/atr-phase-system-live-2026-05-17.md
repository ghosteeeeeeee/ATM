# Phase System — How k is Determined (2026-05-17)

## Two Different Phase Detection Systems

| System | Used by | Thresholds | Returns |
|--------|---------|------------|---------|
| `detect_phase()` | signal_gen.py (signal generation) | BUILDING=60, ACCEL=75, EXH=88, EXT=95 | 'quiet'/'building'/'accelerating'/'exhaustion'/'extreme' |
| `_phase_from_pct()` | tpsl_utils.py (k-scaling for SL/TP) | 50/70/90 | 'neutral'/'building'/'accelerating'/'exhaustion'/'extreme' |

**Both use direction-specific percentile** — for a SHORT position, `percentile_short` is used, NOT `percentile_long`. This is the critical detail.

---

## Stage 1 — Volatility Tier → base_k

```python
ATR_PCT_LOW_THRESH  = 0.01   # 1%
ATR_PCT_HIGH_THRESH = 0.03   # 3%
ATR_K_LOW_VOL       = 1.0    # atr_pct < 1%
ATR_K_NORMAL_VOL    = 0.75    # 1% ≤ atr_pct ≤ 3%
ATR_K_HIGH_VOL      = 0.5     # atr_pct > 3%
```

**Formula:** `atr_pct = ATR(14) / entry_price`

| atr_pct | base_k |
|---------|--------|
| < 1% (LOW_VOL) | 1.0 |
| 1–3% (NORMAL_VOL) | 0.75 |
| > 3% (HIGH_VOL) | 0.5 |

---

## Stage 2 — Phase → k multiplier (applied to base_k)

**Phase thresholds (`_phase_from_pct` in tpsl_utils.py):**

| Direction-specific percentile | Phase |
|---|---|
| ≥ 90 | accelerating (if vel > 0) or exhaustion (if vel < 0) |
| 70–89 | building (if vel > 0) or exhaustion (if vel < 0) |
| < 70 | neutral |

**Stalling check:** `stalling = (velocity < 0) and phase_tier >= ACCELERATING`

**K multipliers (K_PHASE_* in hermes_constants):**

| Phase | Stall (vel < 0) | Fast (speed_pctl ≥ 70) | Slow (speed_pctl < 70) |
|---|---|---|---|
| neutral | base_k | base_k | base_k |
| building | base_k | base_k | base_k |
| accelerating | **0.25** | **0.15** | **0.10** |
| exhaustion | **0.25** | **0.15** | **0.10** |
| extreme | **0.10** | **0.05** | **0.05** |

**Result:** `final_k = base_k × phase_multiplier`

---

## Stage 3 — Floors + Trailing Gate

**New trades (is_new_trade=True):** ATR_SL_MIN_INIT=0.003 (0.30%), ATR_SL_MAX_INIT=0.005 (0.50%)

**Established trades:** ATR_SL_MIN=0.005 (0.50%), ATR_SL_MAX=0.007 (0.70%)

**Accelerating phase:** ATR_SL_MIN_ACCEL=0.007 (0.70%), ATR_TP_MIN_ACCEL=0.010 (1.0%)

**Trailing gate (SHORT):** `new_sl >= current_sl` → BLOCKED (no loosening)

---

## Adjustable Knobs in hermes_constants

### Volatility tier K (lines 293-304)
```python
ATR_K_LOW_VOL       = 1.0    # raise to 1.25-1.5 for low-vol tokens → wider stops
ATR_K_NORMAL_VOL    = 0.75   # raise to 1.0 for normal vol
ATR_K_HIGH_VOL      = 0.5    # raise/lower to adjust high-vol exposure
```

### Phase K multipliers (lines 331-342)
```python
K_PHASE_ACCEL_STALL = 0.25  # lower to 0.10-0.15 for faster exit in accel+stall
K_PHASE_ACCEL_FAST  = 0.15  # lower to 0.05-0.10 for ultra-fast
K_PHASE_ACCEL_SLOW  = 0.10  # lower to tighten stop in low speed
K_PHASE_EXH_STALL   = 0.25
K_PHASE_EXH_FAST    = 0.15
K_PHASE_EXH_SLOW    = 0.10
K_PHASE_EXT_STALL   = 0.10
K_PHASE_EXT_FAST    = 0.05  # extreme-fast = tightest possible stop
```

### TP ratio
```python
ATR_TP_K_MULT       = 1.25  # TP = SL × 1.25 (raise to 1.5-2.0 for larger TP)
```

---

## Live Phase Scan Results (191 tokens, 2026-05-17)

```
ACCELERATING: 34 tokens
  TON(86.5), LAYER(86.0), TURBO(86.0), BIO(85.5), AIXBT(85.0), MELANIA(85.0),
  COMP(84.5), DOOD(84.0), WLD(84.0), BABY(83.5), KAS(83.0), PAXG(83.0),
  HYPE(82.0), RUNE(82.0), ENS(81.0), STBL(81.0), SUI(80.5), USTC(80.5),
  MAVIA(80.0), ORDI(78.5), PUMP(78.5), ONDO(77.5), PEOPLE(77.5), ZEREBRO(77.5),
  ENA(76.5), GALA(76.5), S(76.0), SKR(76.0), APEX(75.5), KPEPE(75.5),
  BANANA(75.0), ETHFI(75.0), FOGO(75.0), ZEC(75.0)

EXHAUSTION: 16 tokens
  REZ(94.5), SAGA(94.5), SOL(94.0), NOT(93.5), BCH(93.0), PROVE(93.0),
  SPX(93.0), ARK(92.0), MERL(92.0), MEW(91.5), AZTEC(91.0), SUPER(90.5),
  ZRO(90.5), WLFI(89.0), XAI(89.0), STRK(88.5)

EXTREME: 27 tokens
  GOAT(100.0), BLAST(100.0), INIT(100.0), KLUNC(100.0), W(100.0), ZK(100.0),
  CC(99.5), IP(99.5), KAITO(99.5), PENDLE(99.5), XLM(99.5),
  POL(99.0), VINE(99.0), MET(98.5), CHIP(98.0), MAV(97.5), TAO(97.5),
  BOME(97.0), LINK(97.0), MEGA(97.0), TRUMP(96.5), ADA(96.0), IOTA(96.0),
  UMA(96.0), DYM(95.5), GAS(95.0), IO(95.0)

BUILDING: 67 tokens
QUIET: 47 tokens
```

---

## Key Nuance: Direction-Specific Phase

A trade's k is determined by the **direction-specific percentile**, not the overall percentile.

STBL SHORT opened with `percentile_short=19.5` → phase='quiet' → k=1.0 (no acceleration squeeze).

Even though STBL's overall momentum is ACCELERATING (pct=81.0 from percentile_long), the SHORT side sees it as quiet.

**For SHORT trades:** phase based on `percentile_short`
**For LONG trades:** phase based on `percentile_long`

This means a token can be "accelerating" for LONG entries but "quiet" for SHORT entries simultaneously.

---

## Scan Script

```python
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from signal_gen import detect_phase, get_momentum_stats, PHASE_BUILDING, PHASE_ACCELERATING, PHASE_EXHAUSTION, PHASE_EXTREME
import sqlite3

conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = conn.cursor()
cur.execute("SELECT token FROM latest_prices ORDER BY token")
tokens = [r[0] for r in cur.fetchall()]
conn.close()

for token in tokens:
    stats = get_momentum_stats(token)
    if stats is None:
        continue
    pct_long = stats.get('percentile_long', 50)
    pct_short = stats.get('percentile_short', 50)
    # For SHORT trades, use pct_short; for LONG, use pct_long
    velocity = stats.get('velocity', 0)
    phase = detect_phase(pct, velocity)
```