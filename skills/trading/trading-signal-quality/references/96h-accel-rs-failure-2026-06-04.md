# 96h Signal Failure Analysis — 2026-06-04

## Bottom Line
**96h window (2026-06-04):** 484 trades, 4 wins, -$65 total PnL.
-accel-300+,rs-sXXX (LONG): 62 trades, **0 wins**, -$9.04
- accel-300-,rs-s-broken (SHORT): 300 trades, **4 wins (1.3%)**, -$38.55

This contrasts sharply with the 30-day view which showed overall net profitability.
The 30-day "recovery" was driven by earlier June trades — the last 96h are a
complete structural failure of both signal families.

---

## accel-300+,rs-sXXX (LONG) — 0% WR, 62 trades

**Every single token lost.** Zero wins in 96h.

| Token | RS Level | PnL% | Confidence |
|-------|----------|------|------------|
| ASTER | rs-s80 | -0.01% to -0.91% | 95.8 |
| DYDX | rs-s1025 | -0.04% to -0.94% | 94.1 |
| CAKE | rs-s22 | -0.28% | 92.4 |
| TIA | rs-s16,rs-s24 | -0.33% to -1.23% | 98.0 |
| ZK | rs-s750 | -0.35% to -1.25% | 95.8 |
| TON | rs-s961 | -0.75% to -1.20% | 95.0 |
| 2Z | rs-s72 | -0.76% to -1.66% | 98.0 |

Historical winners (pre-96h) had RS levels 28-136 touches. The 96h losing trades
have RS levels across the full range: some very low (<25, brand new), most very
high (>500, likely invalidated/broken).

**RS touch buckets vs PnL (96h):** No bucket — from 0 to 3000+ touches — produced a single win.
All 62 trades lost. This is not a threshold problem; the signal family is broken
in the current market regime.

**Confidence distribution:** conf=95.8-98.0 on virtually every trade. The system
is extremely confident and completely wrong. Confidence is orthogonal to outcomes.

**Historical winners (from signal_outcomes, any time):**
- MON accel-300+,rs-s28,rs-s32: +2.72% (conf=91.8)
- PEOPLE accel-300+,rs-s82: +2.74% (conf=98.0)
- NEAR accel-300+,rs-s378: +1.61% (conf=79.2)
- MOVE accel-300+,rs-s136: +3.22% (conf=95.8)
- CHIP accel-300+,rs-s594: +1.35% (conf=78.5)

All historical winners paired with RS levels in the 28-600 touch range.

---

## accel-300-,rs-s-broken (SHORT) — 1.3% WR, 300 trades

**79% of all SHORT volume.** 4 wins in 300 trades. Total PnL: -$38.55.

| Token | PnL% | Notes |
|-------|------|-------|
| BCH | +5.22%, +4.32% | 2 trades, only wins in entire 300-trade sample |
| BSV | +1.47%, +0.57% | 2 trades, also wins |

**The 4 wins:** BCH and BSV — both had conf=92-98%, genuine breakdowns with
real bounce-back. These are the only legitimate rs-s-broken signals in 96h.

**The 296 losses:** Every other trade was a falling knife. Price broke support,
rallied slightly (triggering bounce confirmation), system fired SHORT, then
price continued down to SL.

**PnL distribution (rs-s-broken):**
- WIN: 10 trades (3.3%)
- LOSS < -0.5%: 23 trades
- LOSS -0.5 to -1%: 73 trades
- LOSS -1 to -2%: 158 trades
- LOSS > -2%: 36 trades

The bulk of losses are -1 to -2% — systematic ATR SL hits.

---

## accel-300-,rs-rXXX (SHORT) — 0% WR in 96h

40 trades, 0 wins, all small losses. rs-rXXX resistance levels for SHORT are
also failing — the resistance levels are being broken upward rather than
rejecting price.

---

## Key Constants Currently Deployed

From `hermes_constants.py` (confirmed at /root/.hermes/scripts/hermes_constants.py):

```python
RS_DECIDER_MIN_TOUCHES = 200   # minimum touches for decider to approve
RS_DECIDER_ZBONUS_TOUCHES = 50 # relaxed when |z| > 2.5
RS_DECIDER_ZBONUS_ZSCORE = 2.5
RS_DECIDER_CONF_PENALTY = 15
RS_DECIDER_CONF_FLOOR  = 55

RS_MIN_CONFIDENCE = 60

MIN_GAP_PCT_LONG  = 0.20   # price must be 0.20% above EMA300 to fire LONG
MIN_GAP_PCT_SHORT = 0.20   # price must be 0.20% below EMA300 to fire SHORT
ACCEL_300_MIN_GAP_GROWTH   = 0.03  # gap must grow by 0.03% vs 3 bars ago
ACCEL_300_MIN_GAP_EXPANSION = 0.10  # price must be 0.10% farther from EMA than at cross

ACCEL_300_BLOCK_COSIGS = {'ma-cross-5m+', 'pct-hermes+'}  # 16.7% / 35.7% WR

RS_LEVEL_BROKEN_LOOKBACK = 200  # candles to check for level invalidation
```

---

## Recommended Threshold Changes (Constants Only)

### For accel-300+,rs-sXXX LONG:

**Raise MIN_GAP_PCT_LONG** — the 0.20% gap is too shallow for reliable bounces:

```python
MIN_GAP_PCT_LONG = 0.30   # was 0.20 — require stronger gap at cross
```

**Add RS level MAX touch threshold** — block very high touch counts
(levels likely invalidated/broken in current regime):

```python
RS_DECIDER_MAX_TOUCHES = 300   # NEW — block RS levels above 300 touches
```

This is a NEW constant not currently in hermes_constants.py. It requires
a code change in signal_compactor or decider_run.

**Raise ACCEL_300_MIN_GAP_EXPANSION** for LONG:

```python
ACCEL_300_MIN_GAP_EXPANSION = 0.15   # was 0.10 — price must be 0.15% farther from EMA than at cross
```

### For accel-300-,rs-s-broken SHORT:

**Add RS_BROKEN_MAX_DISTANCE** — block falling knives (highest impact fix):

```python
RS_BROKEN_MAX_DISTANCE = 1.5   # NEW — block if price > 1.5 ATRs below broken level
```

This is a NEW constant requiring a code change in rs.py. The mechanism:
if `broken_distance > RS_BROKEN_MAX_DISTANCE`, suppress the signal entirely.

**Raise MIN_GAP_PCT_SHORT** mirror of LONG:

```python
MIN_GAP_PCT_SHORT = 0.30   # was 0.20 — require stronger gap confirmation on SHORT
```

**Raise ACCEL_300_MIN_GAP_EXPANSION for SHORT:**

```python
ACCEL_300_MIN_GAP_EXPANSION_SHORT = 0.15   # NEW — mirror for SHORT direction
```

---

## What Would Have Helped in 96h Window

| Change | Expected Impact |
|--------|----------------|
| RS_DECIDER_MAX_TOUCHES=300 | Would block rs-s1025, rs-s750, rs-s2888+ — eliminates ~40% of losing LONGs |
| MIN_GAP_PCT_LONG=0.30 | Would require deeper cross — filters shallow bounces that fail |
| RS_BROKEN_MAX_DISTANCE=1.5 | Would block falling knives — eliminates most of the 296 losing rs-s-broken trades |
| MIN_GAP_PCT_SHORT=0.30 | Would filter shallow crossDOWN into flat EMA — fewer false SHORTs |

---

## Diagnostic Query for Future Sessions

```python
# 96h signal quality check — run at start of every session
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()
cutoff = (datetime.now() - timedelta(hours=96)).strftime('%Y-%m-%d %H:%M:%S')

c.execute(f"""
    SELECT signal_type, direction, COUNT(*) as n,
           SUM(is_win) as wins,
           ROUND(SUM(pnl_usdt), 2) as total_pnl
    FROM signal_outcomes
    WHERE closed_at > '{cutoff}'
    GROUP BY signal_type, direction
    ORDER BY total_pnl ASC
""")
print(f"{'SIG':<45} {'DIR':<6} {'N':>5} {'W':>4} {'WR%':>7} {'TOTAL_PNL':>10}")
for row in c.fetchall():
    sig, d, n, wins, total_pnl = row
    wr = wins/n*100 if n > 0 else 0
    print(f"{sig[:43]:<45} {d:<6} {n:>5} {wins:>4} {wr:>6.1f}% {total_pnl:>10}")
conn.close()
```
