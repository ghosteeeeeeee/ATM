# ENA Coiled Spring Analysis — Sept 3, 2025

## Current Conditions (as of ~16:50 UTC)

| Metric | Value | Context |
|--------|-------|---------|
| Price | 0.1702 | Up from 0.150 low (+13.5%) |
| RSI(14) | ~72 | Overbought after extended run |
| EMA9 | 0.1701 | Price sitting on EMA9 |
| EMA21 | 0.1660 | Rising steeply |
| EMA50 | 0.1610 | Strong support below |
| ATR(14) | 0.95% | Expanded (was 0.37% at coil) |
| Volume | Spiked 5.2M at peak, now cooling | Blow-off exhaustion possible |

**What happened:** ENA ran +13.5% from 0.150 to 0.173 in ~6 hours on massive volume.

---

## The Entry Pattern: "Coiled Spring"

### What it is
After an initial impulse establishes a bullish trend (HH/HL structure, EMA alignment), price pulls back with **declining volume** and **compressed volatility** into a support zone. When volume returns, the next leg fires.

### The 7 phases that played out

#### Phase 1 — Accumulation (Sept 2, 22:00-23:00 UTC)
- **Double bottom** at 0.1465-0.1473
- Volume spike on second test (3.0x avg) → selling exhaustion
- RSI: 29-37 (oversold)
- **Key insight:** Second test had LESS volume than first → sellers exhausted

#### Phase 2 — Initial Push (Sept 2, 23:00 - Sept 3, 01:00)
- +3.5% move from 0.147 to 0.152
- Volume elevated but controlled (1.5-2.5x avg)
- Established **first higher low at 0.149**

#### Phase 3 — Consolidation Wave 1 (Sept 3, 01:30-03:30)
- Price tightens 0.151-0.153
- Volume contracts to 0.3-0.7x avg
- ATR compresses from 0.70% to 0.47%
- Higher low maintained at 0.1505

#### Phase 4 — Second Push (Sept 3, 04:50-07:05)
- Push from 0.1505 to 0.1539
- **Volume spike: 4.6x and 5.3x** at 07:00-07:05
- RSI hits 70 (confirms bullish momentum)
- Establishes **higher high at 0.1539**

#### Phase 5 — THE COILED SPRING (Sept 3, 08:45-11:30) ← IDEAL ENTRY
This is what makes the pattern:
- Price leaks from 0.152 → 0.150 (-1.3%)
- **Volume DIES:** 0.2x-0.8x avg (5-7 consecutive low-volume bars)
- **ATR hits session LOW** at 0.37-0.43% (vs 0.97% at peak)
- **RSI drops to 33-45** (cooled from 70+)
- **Higher lows INTACT** — never broke 0.150 support
- **EMA alignment STILL bullish** (EMA9 > EMA21 > EMA50)
- Price sitting right on **EMA21/EMA50 support zone**

#### Phase 6 — THE TRIGGER (Sept 3, 11:40)
- **7.7x VOLUME SPIKE** — biggest of the day
- +1.2% single candle body
- RSI jumps from 44 to 69
- Breaks above 0.153 resistance
- **THIS is the entry confirmation**

#### Phase 7 — The Trend (Sept 3, 12:00-16:00)
- Volume stays elevated 1.5-3x avg
- Price grinds from 0.154 to 0.170 (+10.4%)
- **HH/HL structure maintained throughout**
- RSI stays elevated 65-85 (strong trend mode)
- Peak volume at 15:30-15:40 (5.2M per candle)

---

## Signal Model: `coiled_spring.py`

### Entry conditions (must pass ALL):

**Hard gates:**
1. **EMA alignment:** EMA9 > EMA21 > EMA50 (bullish trend context)
2. **Higher lows:** At least 2 ascending swing lows in recent 100 bars

**Soft conditions (need 4+ of 6):**
3. **Volume contraction:** 4+ consecutive bars with volume < 0.65x of 20-bar avg
4. **ATR compression:** ATR% below 0.55% OR declining >15%
5. **RSI sweet spot:** RSI(14) between 30-50
6. **At support:** Price within 1.5x ATR of EMA21 or EMA50

**Trigger (either mode fires):**
- **COIL MODE:** All soft conditions met, buying the dip
- **TRIGGER MODE:** Volume > 2.0x avg with prior coil bars and RSI > 45

### Confidence scoring
- Base: 55
- Volume spike bonus: up to +25
- RSI sweet spot (35-45): +10
- Clean HH/HL structure (3+ lows): up to +10
- Cap: 95

### Risk management
- **Stop loss:** 1.5x ATR below entry
- **Take profit:** 4x ATR above entry
- **R:R ratio:** ~2.7:1
- **Max hold:** 4 hours (48 x 5m bars)
- **Cooldown:** 1 hour between fires per token

### Backtest results (ENA 5m, 500 bars)
| Signal | Entry | Mode | Outcome | R |
|--------|-------|------|---------|---|
| #1 | 0.1515 | COIL | SL (8 bars) | -1.0R |
| #2 | 0.1513 | COIL | TP (5 bars) | +2.7R |
| #3 | 0.1521 | COIL | SL (2 bars) | -1.0R |
| #4 | 0.1553 | COIL | TP (15 bars) | +2.7R |
| **Total** | | | **50% WR** | **+3.3R** |

---

## What Made This Entry Special

1. **Multi-timeframe alignment:** 1h showed bullish structure, 5m showed the coil
2. **Volume told the story:** Dead volume during pullback = sellers absent, not present
3. **Volatility compression:** ATR hit 0.37% → 0.97% (2.6x expansion from coil)
4. **Support confluence:** EMA21 + EMA50 + prior structure all at same level
5. **RSI reset:** From 70+ → 33-45, creating room for the next leg
6. **The 7.7x volume spike:** The largest volume of the day confirmed the breakout

---

## Files

- Signal: `/root/.hermes/scripts/signals/coiled_spring.py`
- Constant: `COILED_SPRING_ENABLED = True` in `hermes_constants.py`
- Analysis: This file
