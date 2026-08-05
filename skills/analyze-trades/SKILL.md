---
name: analyze-trades
description: Archive closed trades, reconcile prices, rebuild A/B test data, analyze results, and apply winning adjustments to Hermes trading system.
tags: [hermes, trading, analysis, ab-test, trades]
author: T
created: 2026-04-01
updated: 2026-06-06
---

# Analyze Trades — Hermes Trading Analysis

Archives closed trades, rebuilds A/B test data with corrected experiment parsing, analyzes results, and applies indicator weight adjustments.

## Quick Run

```bash
# PostgreSQL times out — use archive DB instead
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('/root/.hermes/archive/trades_analysis.db')
cur = conn.cursor()
# Schema: token, direction, signal, pnl_pct, close_time, close_reason, atr_managed
cur.execute('SELECT token, direction, signal, pnl_pct, close_time, close_reason FROM trades WHERE status="closed" ORDER BY close_time DESC LIMIT 20')
for r in cur.fetchall(): print(r)
conn.close()
EOF
```

## PostgreSQL Connection — DO NOT USE

PostgreSQL at `host=10.60.202.72` **times out on connection**. Use `/root/.hermes/archive/trades_analysis.db` (SQLite) for all trade analysis. Archive DB has the same data with better query performance.

Schema: `token, direction, signal, pnl_pct, close_time, close_reason, status, atr_managed, fees(JSON)`
closed = data['closed']  # list of trade dicts

# By signal type
by_signal = defaultdict(list)
for t in closed:
    key = f"{t.get('signal')},{t.get('direction')}"
    by_signal[key].append(t)

print(f"{'Signal':<35} {'Trades':>7} {'Win%':>7} {'Avg%':>10} {'W':>4} {'L':>4}")
for key, ts in sorted(by_signal.items(), key=lambda x: len(x[1]), reverse=True):
    wins = [t for t in ts if t.get('pnl_pct', 0) > 0]
    avg = sum(t.get('pnl_pct', 0) for t in ts) / len(ts)
    wr = len(wins) / len(ts) * 100
    print(f"{key:<35} {len(ts):>7} {wr:>7.1f}% {avg:>+10.3f}% {len(wins):>4} {len(ts)-len(wins):>4}")

# Close reasons
by_reason = defaultdict(list)
for t in closed:
    by_reason[t.get('close_reason', 'unknown')].append(t)
print("\nClose reasons:")
for reason, ts in sorted(by_reason.items(), key=lambda x: len(x[1]), reverse=True):
    avg = sum(t.get('pnl_pct', 0) for t in ts) / len(ts)
    print(f"  {reason:<25} {len(ts):>5}  avg={avg:>+8.3f}%")
EOF
```

## trades.json Structure
```python
data = json.load(open('/var/www/hermes/data/trades.json'))
# data is dict: {'updated', 'open_count', 'closed_count', 'page_size', 'open', 'closed'}
closed = data['closed']  # list of trade dicts
# Each trade: {coin, direction, signal, pnl_pct, close_reason, closed, ...}
```

## Key Findings (2026-06-06 — 931 closed trades, no 96h activity)

### accel-300+ LONG is catastrophically broken — only accel-300-,rs-s-broken works
| Signal | Win Rate | Avg % | Trades | Verdict |
|--------|----------|-------|--------|---------|
| accel-300-,rs-s-broken | 52.9% | +19.18% | 138 | ✅ KEEP |
| accel-300-,trend_purity- | 52.9% | +0.43% | 8 | ⚠️ Small n |
| accel-300+,rs-s36 | 52.9% | +0.19% | 9 | ⚠️ Small n |
| **accel-300+ (ALL variants)** | **9.4%** | **-58%** | **53** | 🚫 DISABLE |
| zscore_pump | 45% | +9.09% | 44 | ⚠️ |

**Action: Disable all accel-300+ LONG variants** — every combination is destroying the account.
Only `accel-300-,rs-s-broken` (SHORT side with rs-s-broken confirmation) is consistently profitable.

Direction breakdown (931 trades):
- SHORT: 80/155 (51.6%), avg +0.178%
- LONG: 10/45 (22.2%), avg -0.410%

No closed trades in last 96h — data pipeline broke May 27, all signals blocked by stale price_age > 10min.
|--------|-------|
| Trades | 45 |
| Win Rate | 22.2% |
| Avg PnL | -0.41% |
| RS broken trades | 0 (all 45 required RS confirmation) |
| Close reason | 33× atr_sl_hit avg -0.86%, 10× profit-monster avg +1.18% |

**Root cause**: RS confirmation is backwards for accel-300+ LONG. Every LONG trade required RS confirmation — but broken RS levels (strong momentum) outperform confirmed ones (weak/range-bound). The RS filter was designed for SHORT context where broken = good; applied to LONG it filters OUT every winning signal.

**Fix**: Require accel-300+ LONG to fire ONLY on rs-broken signals (or disable LONG entirely until fixed).

### accel-300- SHORT is working correctly
| Metric | Value |
|--------|-------|
| Trades | 155 |
| Win Rate | 51.6% |
| Avg PnL | +0.18% |
| rs-broken WR | 53.2% (139 trades) |
| rs-confirmed WR | 37.5% (16 trades) |

RS broken signals outperform confirmed for SHORT too — but not as severely.

### RS broken vs confirmed (all 200 trades)
| Signal Type | Trades | Win Rate | Avg PnL |
|-------------|--------|----------|---------|
| rs-broken | 139 | 53.2% | +0.20% |
| rs-confirmed | 61 | 26.2% | -0.30% |

RS confirmation is filtering out good trades and passing bad ones. The `RS_DECIDER_CONF_FLOOR=60` and `RS_DECIDER_MIN_TOUCHES=150` are too permissive.

### Regime filter is too tight for current market
- 81 tokens have real slopes (0.04–0.08%/bar) but regime threshold at 0.015%/bar blocks ALL LONG signals
- Market is SHORT-biased: 81 tokens slope < -0.015, 0 tokens slope > +0.015
- **accel-300+ LONG needs regime slope lowered to ~0.008%** to fire in current conditions

## Actions Required

1. **accel-300+ LONG killswitch** — Set `ACCEL_300_PLUS_ENABLED = False` until RS logic is fixed. 22% WR with -0.41% avg is destroying the portfolio.
2. **RS broken only for LONG** — New flag `ACCEL_300_PLUS_RS_BROKEN_ONLY = True`: only fire accel-300+ LONG on rs-broken signals. Remove RS confirmation requirement for LONG direction.
3. **Tighten RS decider** — Raise `RS_DECIDER_CONF_FLOOR` 60→70 and `RS_DECIDER_MIN_TOUCHES` 150→175 to filter out weak levels.
4. **Lower regime slope for accel-300** — Hardcoded at accel_300.py:410/413 as 0.015. Move to hermes_constants as `ACCEL_300_REGIME_SLOPE_PCT = 0.008` to allow flat-market signals.
5. **Relax gap growth** — `ACCEL_300_MIN_GAP_GROWTH` 0.08→0.05: ME fails at 0.08 with real growth, too restrictive.
6. **Relax MIN_GAP_PCT** — `MIN_GAP_PCT_LONG` 0.20→0.15: let weaker gaps through when regime passes.

## Hot Set Validation Rules

Tokens in hot set must have ALL of:
- `z_score` not NULL
- `rsi_14` not NULL
- `macd_hist` not NULL
- `confidence` > 60
- Minimum regime alignment check (per-token z_score_tier + macro regime)
- NOT in HOTSET_BLOCKLIST

### Archive Exploration — Querying Existing Archives

Archived trades live in **`/root/.hermes/archive/trades/`** as JSON files (PostgreSQL archive tables were dropped 2026-05-08).

**rebuild_ab_results.py is DEPRECATED** — it references PostgreSQL tables that no longer exist. For experiment/AB analysis, parse the JSON archives directly.

```bash
# Inspect a JSON archive
python3 -c "
import json
d = json.load(open('/root/.hermes/archive/trades/trades_archive_20260508_015041.json'))
print(d['count'], 'trades')
print('Columns:', d['columns'])
print('Sample:', d['trades'][0])
"

# Export a specific archive to CSV
python3 -c "
import json, csv
d = json.load(open('/root/.hermes/archive/trades/trades_archive_20260508_015041.json'))
rows = d['trades']
writer = csv.DictWriter(open('/tmp/trades.csv', 'w'), fieldnames=list(rows[0].keys()))
writer.writeheader()
writer.writerows(rows)
print(f'Exported {len(rows)} to /tmp/trades.csv')
"
```

Archive structure:
```
/root/.hermes/archive/trades/
  trades_archive_YYYYMMDD_HHMMSS.json          — live closed trades snapshot
  trades_archive_YYYYMMDD_HHMM.json              — brain DB table dumps (32 files, ~3,800 trades)
  archive_closed_trades_20260414_184604.json   — 865 closed trades
  closed_trades_archive.json                    — 86 closed trades
  archive_*_duplicates_*.json                  — duplicate cleanup logs
  archive_*_phantoms_*.json                     — phantom cleanup logs
```

Each JSON: `{"archived_at", "source", "count", "columns", "trades": [...]}`

```bash
# Quick count all archives
python3 -c "
import json, os, glob
total = 0
for f in sorted(glob.glob('/root/.hermes/archive/trades/*.json')):
    try:
        d = json.load(open(f))
        n = len(d.get('trades', []))
        print(f'{os.path.basename(f):50s} {n:5d}')
        total += n
    except: pass
print(f'TOTAL: {total}')
"
```

## Re-run Analysis

Run this skill weekly or after major pipeline changes. Archive before each run.
