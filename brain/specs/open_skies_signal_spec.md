# Open Skies Signal — Spec

**Author:** CEO (Hermes Trading System)
**Date:** 2026-09-05
**Type:** Trend-following LONG signal
**Reference:** ZEN LONG 2026-09-04 23:02 — broke through all resistance, +7.23% in 50 bars

---

## 1. Thesis

Coins that have broken through all resistance with strong upward momentum and no ceiling in sight. The structural R:R is excellent because there's nothing stopping price from running — no walls, no clusters, no historical levels to reject.

**Core insight:** "No resistance" isn't a data gap — it's a structural characteristic. It means price has broken free from all overhead supply. The RR engine already recognizes this (25 pts S/R Clarity for open skies). This signal fires when the breakout is fresh and the trend is confirmed.

---

## 2. The ZEN Pattern (Reference Case)

```
ZEN LONG — 2026-09-04 23:02
Entry: $6.87 | ATR: 3.26% | Regime: EXTREME

Price action:
- Price above SMA20 (+2.03%) and SMA50 (+4.31%)
- 20-bar return: +5.22%
- 50-bar return: +7.23%
- Volume spike: 79K at breakout (vs 15K avg)

S/R structure:
- Resistance levels above: 0 (OPEN SKIES)
- Support levels below: 5 (strong floor at $6.24-$6.79)
- Nearest support: $6.79 (3.8% below entry)

RR Engine verdict: Grade C (was F before open-skies fix)
```

**Key characteristics:**
1. Price has broken through ALL resistance (zero levels above)
2. Strong support floor below (safety net)
3. Uptrend confirmed (above both SMA20 and SMA50)
4. Volume spike on breakout
5. Higher highs forming

---

## 3. Signal Logic

### Detection (LONG only)

```python
def detect(token):
    """
    1. Get 5m candles (100 bars)
    2. Compute SMA20 and SMA50
    3. Check S/R map for resistance levels
    4. Check trend quality
    5. Check volume confirmation
    """
```

### Conditions (all must be true)

| # | Condition | Threshold | Rationale |
|---|-----------|-----------|-----------|
| 1 | Price > SMA20 | Close > SMA20 | Uptrend confirmed |
| 2 | Price > SMA50 | Close > SMA50 | Longer-term trend up |
| 3 | No resistance above | 0 resistance levels in S/R map | Open skies — nothing stopping price |
| 4 | Support below | ≥2 support levels below price | Safety net — floor in place |
| 5 | Positive momentum | 20-bar return > 1.5% | Move has legs |
| 6 | Volume confirmation | Last 5 avg > 1.5× prev 5 avg | Breakout has volume |
| 7 | Higher highs | At least 2 higher highs in last 10 bars | Structurally bullish |

### Entry

- **Direction:** LONG only (open skies is bullish by definition)
- **Entry price:** Current close
- **SL:** Below nearest support level (or 1.5 × ATR if no support)
- **TP:** Trail-based (open skies = no fixed target, ride the trend)

### Exit

- **Primary:** Trailing stop (0.5% activation, 0.3% distance)
- **Secondary:** ATR SL hit
- **Tertiary:** Re-entry of resistance (ceiling reforms = trade done)

---

## 4. Data Sources

| Data | Source | Freshness |
|------|--------|-----------|
| Candles (5m) | `candles.db` | ~1 min |
| S/R map | `risk_reward_engine.build_sr_map()` | 5 min cache |
| ATR% | `volatility_gate.get_atr_pct()` | ~1 min |
| Volume | `candles_5m.volume` | ~1 min |

---

## 5. Confidence Scoring

| Component | Points | Logic |
|-----------|--------|-------|
| Open skies | 30 | No resistance = 30 pts (primary signal) |
| Trend quality | 25 | Above SMA20+SMA50 + positive slope |
| Volume | 20 | Breakout volume confirmation |
| Momentum | 15 | 20-bar return magnitude |
| Support strength | 10 | Number and proximity of support levels |
| **Total** | **100** | |

**Grade thresholds:**
- A (80+): Strong open skies breakout with volume
- B (65-79): Good setup with minor weakness
- C (50-64): Adequate but needs monitoring
- Below 50: Don't fire

---

## 6. Constants (for hermes_constants.py)

```python
# ── Open Skies Signal ─────────────────────────────────────────────────────
OPEN_SKIES_ENABLED = True
OPEN_SKIES_PLUS_ENABLED = True    # LONG only (no SHORT — open skies is bullish)
OPEN_SKIES_MINUS_ENABLED = False  # SHORT not applicable (open skies = bullish)

# Trend filters
OPEN_SKIES_SMA_FAST = 20          # Fast MA period
OPEN_SKIES_SMA_SLOW = 50          # Slow MA period
OPEN_SKIES_PRICE_ABOVE_SMA = True # Price must be above both SMAs

# Momentum
OPEN_SKIES_MIN_RETURN_20 = 1.5    # % — minimum 20-bar return
OPEN_SKIES_MIN_RETURN_50 = 0.0    # % — minimum 50-bar return (optional)

# Volume
OPEN_SKIES_VOL_SPIKE_RATIO = 1.5  # Last 5 avg must be 1.5× prev 5 avg

# S/R structure
OPEN_SKIES_MIN_SUPPORT_LEVELS = 2 # Minimum support levels below price
OPEN_SKIES_MAX_RESISTANCE = 0     # Must be zero — that's the whole point

# Higher highs
OPEN_SKIES_HH_MIN = 2             # Minimum higher highs in last 10 bars
OPEN_SKIES_HH_WINDOW = 10         # Bars to check for higher highs

# Cooldown
OPEN_SKIES_COOLDOWN_HOURS = 4     # Per-token cooldown after fire

# Confidence
OPEN_SKIES_MIN_CONFIDENCE = 60    # Minimum confidence to fire
OPEN_SKIES_MAX_CONFIDENCE = 92    # Cap below momentum signals
```

---

## 7. File Changes

| File | Change |
|------|--------|
| `scripts/signals/open_skies.py` | **NEW** — signal generator |
| `scripts/hermes_constants.py` | Add `OPEN_SKIES_*` constants |
| `scripts/signals/__init__.py` | Register signal |

---

## 8. Risk Management

**Why this is safe:**
1. LONG only — no shorting open skies (that's catching knives)
2. SL below support — structured stop, not arbitrary
3. Volume confirmation — avoids low-conviction breakouts
4. Trend filter — only fires above SMA50 (established trend)
5. RR engine integration — gets full S/R Clarity points (25 pts)

**Why this is dangerous:**
1. Late entry — if the move is already extended, you're chasing
2. False breakout — price could reverse back below resistance
3. Low volume — some 5m candles have 0 volume (data quality issue)

**Mitigations:**
1. Require 20-bar return > 1.5% (momentum has legs)
2. Require volume spike (real buying, not noise)
3. Require support below (floor in place)
4. Use trailing stop (lock in profits as trend runs)

---

## 9. Backtest Plan

1. Run signal on all tokens with 5m candle data
2. Check: what % of open-skies signals resulted in profitable trades?
3. Compare: open-skies WR vs overall signal WR
4. Tune: adjust thresholds based on data
5. Shadow mode first, enforce after 7 days

---

## 10. Integration with RR Engine

The open-skies signal benefits from the RR engine's open-skies fix:
- **Before fix:** Open-skies signals got Grade F (hard blocked) because no resistance = 0 S/R Clarity points
- **After fix:** Open-skies signals get full S/R Clarity points (25 pts) because no resistance = room to run

This is a positive feedback loop: the signal fires on open skies, the engine recognizes open skies as good, and the trade gets a confidence boost.
