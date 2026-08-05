---
name: signal-winner-archive-analysis-2026-05-08
description: Archive analysis of winning trade signal indicators — what z_score, rsi_14, macd_hist, confidence values correlate with profitable trades
tags: [hermes, signals, winners, archive, z-score, rsi, macd]
author: T
created: 2026-05-08
updated: 2026-05-08
---

# Archived Trade → Signal Indicator Analysis (2026-05-08)

## Summary

Analyzed 5,477 archived trades + 576K signals from `/root/.hermes/archive/trades/` and `/root/.hermes/archive/signals/` to determine what indicator values the biggest winners had.

**⚠️ CRITICAL DATA GAP**: Signal archive starts **April 3 04:28 UTC**. Trades from March 31 / April 1 / April 2 have **no matched signals**. Of the top 60 winners, 35+ have no matched signal data.

## Winner Signal Fingerprint (25 matched winners, April 3+ trades)

| Metric | Avg | Min | Max | Notes |
|--------|-----|-----|-----|-------|
| z_score | **-0.662** | — | — | Slightly oversold — mean reversion works |
| rsi_14 | **41.2** | — | — | Mid-range, not extreme |
| confidence | **71.3** | — | — | Moderate conviction |
| macd_hist | **+0.000882** | — | — | Slightly positive momentum |

### By Signal Type (matched winners only, all 100% WR on small n)

| signal_type | n | z_avg | rsi_avg | conf_avg |
|-------------|---|-------|----------|----------|
| mtf_macd | 8 | -0.449 | 43.4 | 92.9 |
| percentile_rank | 5 | -1.359 | 37.8 | 42.9 |
| mtf_zscore | 5 | -0.198 | 45.7 | 79.0 |
| confluence | 4 | -0.546 | 40.9 | 78.0 |
| rsi_individual | 3 | -0.995 | 34.1 | 38.9 |

### Key Insight

Winners tend to fire at slightly **oversold** conditions (z_score negative) with **moderate confidence** (71), **mid-range RSI** (41, not extreme oversold), and **slightly positive MACD hist**.

## A/B Test Results — SL Distance Variants (1,220 real trades)

| SL Variant | n | Win Rate | avg_PNL | net_PNL |
|---|---|---|---|---|
| SL-3p0 | 180 | 16.1% | +$0.14 | **+$25.96** ← best net |
| SL3pct | 220 | 29.1% | +$0.07 | +$15.17 |
| SL80pct-E5 | 7 | 28.6% | +$2.13 | +$14.93 |
| SL2pct | 258 | 33.3% | +$0.04 | +$9.58 |
| SL2pct-E3 | 14 | 50.0% | -$0.00 | -$0.05 |
| SL1pct | 86 | 34.9% | -$0.08 | -$6.78 |
| SL-1p2 | 13 | 30.8% | -$0.53 | -$6.84 |
| SL-1p5 | 224 | 18.3% | -$0.09 | -$20.63 |
| SL-2p0 | 108 | 24.1% | -$0.21 | -$22.34 |
| SL-1p0 | 86 | 37.2% | -$0.44 | -$37.75 |

**Tightest SL (SL-3p0) is most profitable net despite lowest WR (16%)** — wide SLs let winners run but give back too much on losers.

## A/B Test Results — Entry Timing Variants

| Entry Timing | n | Win Rate | net_PNL |
|---|---|---|---|
| IMMEDIATE | 585 | 21.4% | **+$37.96** ← best |
| EVO-3 | 22 | 45.5% | -$1.43 |
| RETRACE-2 | 167 | 34.7% | -$20.21 |
| EVO-5 | 12 | 16.7% | -$7.52 |
| RETRACE-5 | 421 | 30.4% | -$38.10 |
| IMMEDIATE-CF | 13 | 7.7% | -$22.90 |

**IMMEDIATE dominates net despite lowest WR** — waiting for pullbacks causes missed moves.

## How to Cross-Reference Trades → Signals

Trade records contain experiment metadata (SL variant, timing) but NOT z_score/rsi/macd values. You must look up the corresponding signal.

```python
import gzip, re, json, os
from datetime import datetime
from collections import defaultdict

def parse_dt(s):
    if not s: return None
    s = s.replace('Z', '').replace('+00:00', '')
    s = re.sub(r'\.\d+', '', s)  # strip fractional seconds
    try:
        return datetime.fromisoformat(s)
    except:
        return None

def load_signals(gz_path):
    sigs = defaultdict(list)
    with gzip.open(gz_path, 'rt') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            s = json.loads(line)
            key = (s.get('token'), s.get('direction'))
            sigs[key].append(s)
    return sigs

april = load_signals('/root/.hermes/archive/signals/signals_2026-04.jsonl.gz')
may = {}
if os.path.exists('/root/.hermes/archive/signals/signals_2026-05.jsonl.gz'):
    may = load_signals('/root/.hermes/archive/signals/signals_2026-05.jsonl.gz')

all_sigs = defaultdict(list)
for k, v in april.items(): all_sigs[k].extend(v)
for k, v in may.items(): all_sigs[k].extend(v)

def find_signal(token, direction, open_time_str, max_seconds=14400):
    """Find closest signal within 4hr window. Returns (signal, diff_seconds)."""
    open_dt = parse_dt(open_time_str)
    if not open_dt: return None, None
    key = (token, direction)
    sigs = all_sigs.get(key, [])
    best, best_diff = None, float('inf')
    for s in sigs:
        sig_dt = parse_dt(s.get('created_at', ''))
        if not sig_dt: continue
        diff = abs((sig_dt - open_dt).total_seconds())
        if diff < best_diff:
            best_diff, best = diff, s
    return (best, best_diff) if best_diff <= max_seconds else (None, best_diff)
```

## Archived Files

- Trades: `/root/.hermes/archive/trades/` — 42 files, ~5,556 trades total
- Signals: `/root/.hermes/archive/signals/signals_2026-04.jsonl.gz` (404K signals, Apr 3–30)
- Signals: `/root/.hermes/archive/signals/signals_2026-05.jsonl.gz` (171K signals, May)
