# Signal Spec: Grind Breakout (grind-breakout-v2)

## Thesis

**Volume-confirmed resistance breakouts with positive acceleration continue.** When a token consolidates in a tight range with declining volume, then breaks above the range high with a volume surge AND accelerating momentum, the move has institutional backing — not just retail noise. The acceleration component catches the move EARLY, before pump-chain signals fire (which wait for a much larger price move).

**Market mechanic:** Smart money accumulates during consolidation (low volume, tight range). When they're done accumulating, they push price through resistance with volume. The acceleration (change in velocity) reveals whether the push is gaining or losing steam. Positive acceleration + volume + resistance break = institutional accumulation transitioning to markup.

**Why this catches CHIP/CFX-style moves early:**
- CHIP: consolidated 0.0516–0.0519 for 75min with 0.0–0.1x volume, then broke at 16:15–16:25 with 1.8–2.4x volume and +1.7%/+2.5%/+2.0% bars. Our pump-chain signal didn't fire until 21:00 — 4.75 hours late.
- CFX: consolidated 0.0595–0.0608 for 90min with 0.2–0.5x volume, then broke at 17:00–17:10 with +1.0%/+1.2% bars. Pump-chain fired at 21:24 — after the move was done.

## Entry Conditions (LONG)

```
ENTRY: Price closes above N-bar high (resistance breakout)
       + Volume >= VOL_MULT × 20-bar average volume
       + Acceleration > 0 (velocity increasing)
       + MACD histogram rising (optional confirmation)
```

### Detailed Conditions

| # | Condition | Parameter | Default | Rationale |
|---|-----------|-----------|---------|-----------|
| 1 | **BB compression before breakout** | `BB_COMPRESS_MAX` | 3.0% | BB width must be below this within last 10 bars. Tight coil = coiled spring. CHIP was 0.62%, CFX was 5.5%. |
| 2 | Price breaks above resistance | `RESISTANCE_BARS` | 20 | 20-bar high on 5m = ~100min consolidation range |
| 3 | Breakout bar closes in top 50% of range | `BREAKOUT_BODY_MIN` | 0.5 | Confirms buying pressure, not just a wick |
| 4 | Volume surge | `VOL_SURGE_MULT` | 2.0 | 2x average = institutional participation |
| 5 | Volume during compression was low | `COMPRESS_VOL_MAX` | 0.6 | Volume must have been below 60% of average during compression. Dead volume = accumulation. |
| 6 | Acceleration positive | `ACCEL_MIN` | 0.0 | Velocity increasing = move gaining steam |
| 7 | MACD histogram rising (optional) | `MACD_RISE_ENABLED` | True | Secondary momentum confirmation |
| 8 | Not overextended | `MAX_MOVE_FROM_RANGE` | 3.0% | Don't chase if price already moved >3% from breakout level |

### Compression Precondition (Condition 1+5)

The compression filter is what separates V2 from pump-chain (which fires on any pump). Evidence from the target moves:

| Token | BB Width Before Breakout | Volume Before Breakout | Move |
|-------|-------------------------|----------------------|------|
| CHIP | **0.62%–1.34%** | 0.0x–0.6x | +29.4% |
| CFX | **5.5%** (compressing from 18.6%) | 0.1x–0.3x | +20.7% |

**Compression check:** At breakout, BB(20, 2.0) width must have been below `BB_COMPRESS_MAX` within the last `COMPRESS_LOOKBACK` bars (10 bars = 50 minutes on 5m). AND volume during those compression bars must have been below `COMPRESS_VOL_MAX` × average.

This filters out tokens that are already volatile (no coil = no spring). It also catches the accumulation phase — smart money buying quietly in a tight range before the markup.

### SHORT Entry (Mirror)

```
ENTRY: Price closes below N-bar low (support breakdown)
       + Volume >= VOL_MULT × 20-bar average volume
       + Acceleration < 0 (velocity decreasing)
       + MACD histogram falling (optional confirmation)
```

## Exit Rules

| Exit | Condition | Parameter | Default |
|------|-----------|-----------|---------|
| Take Profit | Trail from highest high | `TP_TRAIL_PCT` | 1.5% |
| Stop Loss | Below breakout level minus ATR buffer | `SL_ATR_MULT` | 1.5× ATR(14) |
| Time Exit | Thesis hasn't played out | `TIME_EXIT_BARS` | 24 bars (2 hours on 5m) |
| Trailing Activate | After price moves in favor | `TRAIL_ACTIVATE_PCT` | 0.8% |

**R:R target:** 1:1.5 minimum (risk $1 to make $1.50)

## Signal Type

```
SIGNAL_TYPE_LONG  = 'grind_breakout_long'
SIGNAL_TYPE_SHORT = 'grind_breakout_short'
SOURCE_LONG       = 'grind-breakout-v2+'
SOURCE_SHORT      = 'grind-breakout-v2-'
```

**Differentiation from V1 (`grind_breakout.py`):**

| Feature | V1 | V2 |
|---------|-----|-----|
| Data source | 1m price_history | 5m candles |
| Trend purity | ✅ EMA20 60% of 30 bars | ❌ (simplified) |
| Slope filter | ✅ linreg slope | ❌ (replaced by acceleration) |
| Acceleration | ✅ vel_5m > vel_15m × 1.2 | ✅ acceleration > 0 (from token_speeds) |
| **Volume surge** | ❌ **MISSING** | ✅ **2x+ average (KEY DIFFERENTIATOR)** |
| MACD confirmation | ❌ | ✅ histogram rising |
| RSI filter | ✅ 35-65 | ❌ (simplified) |
| Max move from range | ❌ | ✅ 3% (don't chase) |
| Consecutive candles | ✅ max 3 green | ❌ (simplified) |
| Total conditions | 6 | 4 (+2 optional) |

V2 is **simpler** (fewer conditions = less overfitting) but adds the **volume surge** filter that V1 is missing. Volume is the single most important confirmation for breakout validity — price without volume is noise.

## Lessons from Coiled-Spring (coiled_spring.py) — KILLED 2026-10-01

Coiled-spring attempted a similar compression-breakout pattern but failed: **22 trades, 40.9% WR, −$0.79**. Loses in ALL regimes.

| What went wrong | How V2 avoids it |
|----------------|-----------------|
| **40+ constants** — massive overfitting surface | V2 uses ~15 constants |
| **5-of-6 conditions required** — too restrictive, signals rarely fire | V2 uses 4 core conditions (compression, breakout, volume, acceleration) |
| **Required specific multi-phase pattern** (impulse → pause → second push → coiled → trigger) — too complex, rarely aligns | V2 just checks: was it compressed? Did it break out with volume? Is it accelerating? |
| **Required bullish trend first** (HH/HL structure, EMA alignment) — blocks counter-trend breakouts | V2 has no trend requirement — works in any regime |
| **RSI 30-50 filter** — too restrictive, blocks strong momentum | V2 has no RSI filter |
| **LONG only** — can't catch breakdowns | V2 works both directions |
| **Normal-only regime** — vol gate blocked HIGH/EXTREME | V2 should be regime-agnostic (backtest will confirm) |

**The core mistake:** Coiled-spring tried to define the EXACT pattern (multi-phase, specific indicators). V2 uses a simpler question: **"Was this token quiet, and is it now moving with volume?"** — that's what CHIP and CFX did.

## Constants (hermes_constants.py)

```python
# ── Grind Breakout V2 ─────────────────────────────────────────────────────
# grind_breakout_v2.py — volume-confirmed resistance breakout with acceleration
GRIND_BREAKOUT_V2_ENABLED = True          # master kill-switch
GRIND_BREAKOUT_V2_PLUS_ENABLED = True     # LONG direction
GRIND_BREAKOUT_V2_MINUS_ENABLED = True    # SHORT direction
GRIND_BREAKOUT_V2_COOLDOWN_HOURS = 2      # per token+direction cooldown

# Entry conditions
GRIND_BREAKOUT_V2_RESISTANCE_BARS = 20    # lookback for resistance/support
GRIND_BREAKOUT_V2_VOL_SURGE_MULT = 2.0    # volume must be >= Nx average
GRIND_BREAKOUT_V2_VOL_AVG_PERIOD = 20     # bars for average volume
GRIND_BREAKOUT_V2_ACCEL_MIN = 0.0         # min acceleration (0.0 = must be positive)
GRIND_BREAKOUT_V2_MACD_RISE_ENABLED = True # require MACD histogram rising
GRIND_BREAKOUT_V2_MAX_MOVE_FROM_RANGE = 3.0  # max % move from breakout level (don't chase)
GRIND_BREAKOUT_V2_BREAKOUT_BODY_MIN = 0.5 # min body/range ratio for breakout bar

# Compression precondition (the coiled spring)
GRIND_BREAKOUT_V2_BB_COMPRESS_MAX = 3.0   # BB(20,2.0) width must be below this % before breakout
GRIND_BREAKOUT_V2_COMPRESS_LOOKBACK = 10  # bars to check for compression (10 bars = 50min on 5m)
GRIND_BREAKOUT_V2_COMPRESS_VOL_MAX = 0.6  # volume must be below this × avg during compression
GRIND_BREAKOUT_V2_BB_PERIOD = 20          # BB period
GRIND_BREAKOUT_V2_BB_STDDEV = 2.0         # BB standard deviations

# Exit rules
GRIND_BREAKOUT_V2_TP_TRAIL_PCT = 1.5      # trail from highest high
GRIND_BREAKOUT_V2_SL_ATR_MULT = 1.5       # SL = ATR(14) × this below breakout
GRIND_BREAKOUT_V2_TIME_EXIT_BARS = 24     # exit after N bars if thesis fails
GRIND_BREAKOUT_V2_TRAIL_ACTIVATE_PCT = 0.8  # trailing activates after this profit

# Confidence
GRIND_BREAKOUT_V2_CONF_BASE = 75          # base confidence
GRIND_BREAKOUT_V2_CONF_FLOOR = 50         # min confidence
GRIND_BREAKOUT_V2_CONF_CAP = 88           # max confidence (system ceiling)
GRIND_BREAKOUT_V2_CONF_VOL_BONUS = 5      # +5 if volume > 3x average
GRIND_BREAKOUT_V2_CONF_ACCEL_BONUS = 3    # +3 if acceleration > 0.01
GRIND_BREAKOUT_V2_CONF_MACD_BONUS = 2     # +2 if MACD histogram rising
```

## Data Sources

| Data | Source | Use For |
|------|--------|---------|
| 5m candles | `candles.db` → `candles_5m` | Price action, volume, resistance |
| 1m candles | `candles.db` → `candles_1m` | Fallback for acceleration |
| token_speeds | `signals_hermes_runtime.db` | Acceleration, velocity (pre-computed) |

## Signal Flow

```
1. Fetch 5m candles (last 50 bars)
2. Compute 20-bar high/low (resistance/support)
3. Check if current close breaks above resistance (LONG) or below support (SHORT)
4. Compute volume ratio (current / 20-bar average)
5. Compute acceleration from token_speeds or from candle closes
6. Check MACD histogram direction
7. Check max move from range (don't chase)
8. If all conditions pass → emit signal
```

## Backtest Plan

1. **Historical validation:** Query brain DB for tokens that had >10% moves in last 30d. Check if the entry conditions would have fired BEFORE the move.
2. **Win rate target:** >52% on 20+ trades
3. **Avg PnL target:** >0.05% per trade (covers fees)
4. **R:R validation:** Check MFE/MAE ratio on historical trades

## Risks

1. **False breakouts:** Price breaks resistance then reverses — mitigated by volume + acceleration filter
2. **Late acceleration:** Acceleration can turn negative quickly in crypto — mitigated by tight stop loss
3. **Correlation with existing signals:** May overlap with pump-chain or bb-squeeze — need to check signal correlation in backtest
4. **Volume manipulation:** Low-cap tokens can fake volume — mitigated by requiring 2x+ average (harder to sustain)

## Implementation Checklist

- [ ] Create `scripts/signals/grind_breakout_v2.py`
- [ ] Add constants to `hermes_constants.py`
- [ ] Register in `scripts/signals/__init__.py`
- [ ] Add to `STANDALONE_BYPASS_SIGNALS` (if backtested)
- [ ] Add vol gate entry in `volatility_gate_v2.py` REGIME_SIGNALS
- [ ] Backtest on 30d historical data
- [ ] Paper trade 2 weeks
- [ ] Deploy live
