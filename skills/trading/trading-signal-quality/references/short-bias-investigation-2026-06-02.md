# SHORT Bias Investigation — 2026-06-02

## Three Questions and Answers

### Q1: Why do accel-300 and rs-s-broken fire more SHORT?

**Actual ratios (from signals.json):**
- accel_300_short: 76, accel_300_long: 8 (9.5x asymmetry)
- rs-s-broken: 246 SHORT, rs-r+touch LONG: 5 (49x asymmetry)

The asymmetry is in **signal generation logic**, not source weights:

**accel-300:** fires when price is BELOW EMA300 with growing gap (downtrend). In a declining market, price stays persistently below EMA300 → gap grows → fires SHORT. For LONG (accel-300+), price must be ABOVE EMA300 with growing gap — in a declining market, price rarely crosses above EMA300 → barely fires.

**rs-s-broken:** fires when a support level is breached (price fell through it). In a falling market, supports break constantly → 246 fires. rs-r+touch (LONG) fires when price touches resistance and bounces — requires price to rally to resistance, which is less common in a declining market.

**Conclusion:** Not a bug. Market-driven generation asymmetry. In an uptrending market the ratios would flip.

---

### Q2: Source weights should be 1.0 if asymmetric generation is "true" — aren't they biased?

**Correction to prior claim.** Source weights (e.g., accel-300+ weight=0.8 vs accel-300- weight=1.0) do NOT address generation frequency — they adjust signal *trust* after generation. They are correct as-is.

The weights reflect:
- `accel-300+` (LONG): 0.8 weight = suppress LONG when it does fire (catches knives in ranging markets)
- `accel-300-` (SHORT): 1.0 weight = full trust

**Why asymmetric weights are correct:** The 2026-06-01 chop filter analysis showed accel-300+ fires on shallow crosses in flat markets → false breakouts. The lower weight compensates for this. accel-300- has the chop filter (mirror-symmetric) but still fires more legitimately in downtrending markets.

**The real question** is whether the market is generating asymmetric signals correctly. If yes, weights are fine. If no (e.g., accel-300+ is being incorrectly suppressed), the weight itself would need adjustment — but the regime filter already handles this via reg_mult=1.50 for aligned signals.

---

### Q3: Is the regime calculation incorrectly computing LONG_BIAS?

**Regime scanner** (`15m_regime_scanner.py`):

```
LONG_BIAS:  slope_pct > 0.35% AND r2 > 0.5
SHORT_BIAS: slope_pct < -0.35% AND r2 > 0.5
NEUTRAL:    |slope_pct| < 0.20% OR r2 < 0.4
```

**Actual data** (regime_5m.json, 2026-06-02):
- All 98 tokens: NEUTRAL
- 0 LONG_BIAS, 0 SHORT_BIAS
- Highest R2 tokens: SUSHI r2=0.777 slope=-0.176%, XMR r2=0.773 slope=+0.159% — both below 0.35% threshold

**Verdict:** Regime calculation is **mathematically correct**. The thresholds are strict by design (0.35% slope + 0.5 R²). No token crosses the threshold in the current market.

**The regime is not incorrectly computing anything.** The market is genuinely NEUTRAL by this scanner's definition, even though most slopes are slightly negative.

---

## Why SHORT Bias Exists Despite NEUTRAL Regime

The regime scanner classifies all 98 tokens as NEUTRAL, but the signal generators are still producing ~90% SHORT because:

1. Most slopes are slightly negative (-0.03% to -0.18%) even if below the 0.35% LONG_BIAS threshold
2. `rs-s-broken` fires on support breach regardless of regime (only checks regime for penalty calculation at line 528-531)
3. `accel-300` has an internal regime check (line 407-410) but this uses a different metric (1m slope vs regime_5m.json)

The system correctly implements per-coin regime filtering. The SHORT bias is a market regime × signal architecture interaction, not a bug.

---

## Key Data Points

| Signal | SHORT fires | LONG fires | Ratio |
|--------|------------|------------|-------|
| accel_300 | 76 | 8 | 9.5x |
| support_resistance (rs-s-broken) | 246 | 5 | 49x |
| All signals | ~350 | ~13 | 27x |

| Metric | Value |
|--------|-------|
| signals.json: total signals | 380 |
| signals.json: SHORT | 366 (96%) |
| signals.json: LONG | 13 (3.4%) |
| Executed trades: SHORT | 33 (92%) |
| Executed trades: LONG | 3 (8%) |
| Pending: SHORT | 95 (97%) |
| Pending: LONG | 3 (3%) |
| regime_5m.json: overall | NEUTRAL |
| Tokens in NEUTRAL | 98/98 |
| Tokens in SHORT_BIAS | 0 |
| Tokens in LONG_BIAS | 0 |