# Counter-Trend Entry Bug — 2026-05-13 Root Cause

## Summary

15 losing LONG trades in 6 hours (08:30-14:30 UTC). All had confidence 77-98%, all bullish signals.
Root cause: **accel-300 firing when price is BELOW EMA300**, not above it. Combined with no 4h trend filter.

## Key Finding: All Entries Below EMA300

| Token | Dir | Entry Price | EMA300 | Gap% | 4h Trend | Alignment |
|-------|-----|------------|--------|------|----------|-----------|
| NEAR | LONG | 1.5786 | 1.6013 | -1.4% | UP | ❌ counter-trend |
| BRETT | LONG | 0.00974 | 0.01012 | -3.8% | UP | ❌ counter-trend |
| BERA | LONG | 0.4036 | 0.4109 | -1.8% | UP | ❌ counter-trend |
| ONDO | LONG | 0.3862 | 0.3955 | -2.3% | UP | ❌ counter-trend |
| LINEA | LONG | 0.00391 | 0.00398 | -1.7% | UP | ❌ counter-trend |
| S | LONG | 0.04963 | 0.05083 | -2.4% | UP | ❌ counter-trend |
| GRIFFAIN | SHORT | 0.01176 | 0.01230 | -4.4% | DOWN | ✅ aligned |
| ATOM | SHORT | 2.0761 | 2.1107 | -1.6% | **UP** | ❌❌ catastrophic |
| MERL | SHORT | 0.03546 | 0.03635 | -2.4% | DOWN | ✅ aligned |

## Root Causes

### 1. accel-300 Logic Firing Counter-to-EMA Trend

The signal name implies "price accelerating above EMA300." But all entries had price **below** EMA300.
Possible causes:
- `price_history` staleness: data ends March 2026, not May 2026 — EMA(300) calculation may be wrong
- EMA(300) warmup insufficient: need ~1500 bars for reliable EMA300, but price_history may not have enough
- Signal logic bug: gap-300- fires LONG when EMA300 > SMA300, but this is a relative comparison, not an absolute price test

### 2. No 4h Trend Filter in Signal Compactor

`signal_compactor.py` has 1m regime filtering (`get_regime_1m`) but NO check against 4h EMA20/EMA50 trend.
ATOM SHORT is the clearest failure: 4h EMA20 > EMA50 (UP trend), yet system fired SHORT.

### 3. ATR SL Too Tight

All losing trades hit `atr_sl_hit` within 1-10 min. The ATR stop is getting hit on normal pullbacks in a trending market.
Price enters below EMA300 → gets immediately stopped out → price then continues in original trend direction.

## Debugging Commands

```bash
# Check EMA300 position for any token at entry time
python3 - <<'EOF'
import sqlite3, time
token = 'NEAR'
conn = sqlite3.connect('/root/.hermes/data/candles.db')
c = conn.cursor()
c.execute("SELECT close FROM candles_1m WHERE token=? ORDER BY timestamp DESC LIMIT 300", (token,))
rows = c.fetchall()
closes = [r[0] for r in reversed(rows)]
# Manual EMA300
ema = sum(closes[:300]) / 300
k = 2 / (301)
for c in closes[300:]:
    ema = c * k + ema * (1 - k)
print(f"EMA300: {ema:.6f}, Latest close: {closes[-1]:.6f}, Gap: {(closes[-1]/ema - 1)*100:.2f}%")
EOF

# Check 4h trend for any token
python3 - <<'EOF'
import sqlite3
token = 'ATOM'
conn = sqlite3.connect('/root/.hermes/data/candles.db')
c = conn.cursor()
c.execute("SELECT close FROM candles_4h WHERE token=? ORDER BY timestamp DESC LIMIT 50", (token,))
rows = c.fetchall()
closes = [r[0] for r in reversed(rows)]
ema20 = sum(closes[-20:])/20
ema50 = sum(closes[-50:])/50
trend = "UP" if ema20 > ema50 else "DOWN"
print(f"{token}: 4h EMA20={ema20:.6f}, EMA50={ema50:.6f}, Trend={trend}")
EOF
```

## Fixes Needed

1. **Add EMA300 proximity filter**: Entry price must be within +1% of EMA300 for LONG, -1% for SHORT
2. **Add 4h trend filter in compactor**: Block LONG if 4h EMA20 < EMA50, block SHORT if 4h EMA20 > EMA50
3. **Investigate accel-300 price source**: Verify whether it's reading from price_history (stale) or candles_1m (live)
4. **Tighten ATR SL**: Current ATR SL is too tight for entries below EMA300 in trending market

## Critical: Two Parallel Code Paths

There are TWO separate accel_300 implementations that may both be running:

| Path | File | MIN_GAP_PCT | PERSISTENCE_BARS | Used By |
|------|------|-------------|-----------------|---------|
| Old | `/root/.hermes/scripts/accel_300_signals.py` | 0.10 | 3 | signal_gen.py |
| New | `/root/.hermes/scripts/signals/accel_300.py` | 0.20 | 2 | signals_runner.py (FAST signals) |

The old version (0.10, 3 bars) was running on May 13 when the bad trades fired. The new version (0.20, 2 bars) was committed in the same day's PR (de86b7c) but may not have been live.

## Critical: Staleness Check Bug

`detect_accel_300` uses `time.time()` in the staleness check:

```python
price_age_minutes = (time.time() - price_ts) / 60
```

This means when back-testing or replaying historical signals, `price_age_minutes` uses the **current** wall clock time, NOT the historical signal time. All historical price checks will appear "stale" (age >120s) when replaying with `time.time()=now`, making it impossible to replicate historical signal behavior.

This cannot be fixed without passing the historical timestamp into the detect function.

## Related Files

- `accel_300.py` — signal source (new version, signals_runner.py)
- `accel_300_signals.py` — old version (signal_gen.py path, was live May 13)
- `signal_compactor.py` — hot-set selection (needs 4h trend filter)
- `candles.db` — live 1m/4h candles (use this for price/EMA checks)
- `signals_hermes.db` — price_history (STALE, do not use for signal generation)"