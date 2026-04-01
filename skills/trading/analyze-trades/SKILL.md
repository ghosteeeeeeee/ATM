---
name: analyze-trades
description: Archive closed trades, reconcile prices, rebuild A/B test data, analyze results, and apply winning adjustments to Hermes trading system.
category: trading
tags: [hermes, trading, analysis, ab-test, trades]
author: T
created: 2026-04-01
---

# Analyze Trades — Hermes Trading Analysis

Archives closed trades, rebuilds A/B test data with corrected experiment parsing, analyzes results, and applies indicator weight adjustments.

## Archive + Reconcile

```python
#!/usr/bin/env python3
import subprocess, json, datetime

HERMES_DB = '/root/.hermes/data/hermes.db'
RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'

def pg(sql):
    r = subprocess.run(['sudo','-u','postgres','psql','-d','brain','-t','-c',sql],
                       capture_output=True, text=True)
    return r.stdout

# Archive closed trades
ts = datetime.datetime.now().strftime('%Y%m%d_%H%M')
pg(f"CREATE TABLE IF NOT EXISTS trades_archive_{ts} AS SELECT * FROM trades WHERE status='closed'")
pg(f"DELETE FROM trades WHERE status='closed'")
pg("DELETE FROM ab_results")
print(f"Archived. Open remaining: {pg('SELECT COUNT(*) FROM trades WHERE status=open').strip()}")
```

## Key Findings (2026-04-01)

### System Bug Summary
| Bug | Count | Impact | Root Cause |
|-----|-------|--------|------------|
| guardian_missing | 22 | -$0.14 | Guardian process not connected — positions killed at 0s |
| orphan_recovery | 13 | -$2.53 | Position opens, guardian can't find it, marks orphan |
| ghost_recovery | 11 | +$0.16 | Phantom positions from past runs — mostly noise |
| hl_position_missing | 9 | -$0.56 | HL didn't register the position — timing race |

### A/B Test Results (87 archived trades, 31 real signal exits)
| Test | Winner | avgR | Current Setting | Change Needed |
|------|--------|------|-----------------|---------------|
| sl-distance-test | SL-1p0 | +1.336 | SL-1p5 | Widen to 1.0% OR wait for more data |
| trailing-stop-test | TS-1p0-0p5 | n/a | TS-1p0-0p5 | Keep — only variant getting signal matches |
| entry-timing-test | RETRACE-2 | n/a | EVO-3/EVO-5 | RETRACE variants showing better avgR — increase allocation |

### Signal Quality
- 31 real exits: 8 wins / 23 losses (26% WR)
- Net: -$60.40 — dominated by VVV -$16.27, MINA -$5.52, ALGO -$5.09
- Trailing stops too tight: most exits at 0.02-1.9% — not capturing real moves
- STABLE/VVV/AXS cut_loser exits: wrong direction signals

## Apply Indicator Weight Adjustments

After analysis, update signal source weights in signal_gen.py or config:

### Winners (increase weight):
- `hmacd-` (MTF MACD agreement): Currently unweighted — add to confluence scoring
- `hzscore` (MTF z-score agreement): Strong signals — increase weight
- `percentile_rank` (historical extremes): Good directional indicator

### Losers (decrease or filter):
- `rsi-hermes` alone: Low predictive value — only use in confluence with other signals
- `macd-confluence` alone: Too noisy without MTF confirmation — require hzscore alignment
- SHORT blacklist working: Most SHORT blacklist tokens avoided correctly

## Hot Set Validation Rules

Tokens in hot set must have ALL of:
- `z_score` not NULL
- `rsi_14` not NULL  
- `macd_hist` not NULL
- `confidence` > 60

Missing any column = disqualified, log:
```
HOT_SET_DISQUALIFIED: {token} missing {missing_column} (z={z_score}, rsi={rsi_14}, macd={macd_hist})
```

## Re-run Analysis

Run this skill weekly or after major pipeline changes to keep A/B test data fresh.
