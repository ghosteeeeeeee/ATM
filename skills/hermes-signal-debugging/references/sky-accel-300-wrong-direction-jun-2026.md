# SKY SHORT on accel-300-,rs-r74: Wrong Direction

**Date:** 2026-06-18  
**Trade:** SKY SHORT @ $0.0574, SL hit $0.0580, PnL = -1.02%  
**Signal:** `accel-300-,rs-r74` — executed 20:13 EDT

---

## Root Cause

`accel-300-` fired SHORT while SKY was consistently **+0.82% above EMA300**.

HL API price data for SKY around signal time (EDT):

| Time | Price | EMA300 | Gap |
|------|-------|--------|-----|
| 20:12 | 0.057296 | 0.056886 | +0.72% |
| 20:13 | 0.057355 | 0.056889 | **+0.82%** ← signal fires |
| 20:14 | 0.057527 | 0.056893 | +1.11% |

SKY was in a steady uptrend. The SHORT was fundamentally wrong.

---

## Why accel-300 Fired Anyway

**Primary cause:** `signals_hermes.db` price_history had a **data gap** for SKY during the signal window (22:50 UTC to 23:23 UTC — a 33-minute hole). The `accel_300.py` bar-to-bar gap guard (line ~189-198) only detects anomalous bar spacing, NOT silent absence of entire minutes. When price_history is missing bars, accel-300 silently operates on whatever data it has and computes a phantom gap_pct.

**Secondary issue:** The `value` field in the signals DB shows `71.4` for this signal — which is an RS confidence score, not a gap_pct. The `accel-300-` and `rs-r74` components got merged into one DB row via `GROUP_CONCAT`, and the value column was shared/overwritten. This makes gap_pct-based post-hoc diagnosis impossible without reconstructing from raw price_history.

---

## Diagnostic Commands

```bash
# Check price_history for gaps around signal time
# Signal time: 2026-06-18 20:13 EDT = 2026-06-19 00:13 UTC = 1781825580
python3 -c "
import sqlite3, datetime
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = conn.cursor()
cur.execute('''
    SELECT timestamp, price FROM price_history
    WHERE token = ?
    AND timestamp >= ?
    AND timestamp <= ?
    ORDER BY timestamp ASC
''', ('SKY', 1781823000, 1781827000))
rows = cur.fetchall()
for r in rows:
    print(datetime.datetime.fromtimestamp(r[0]).strftime('%H:%M:%S'), r[1])
"
# Expected: continuous 1-min bars around signal time
# If output shows gaps or jumps >> 60s between timestamps = data hole

# Cross-check HL API for ground truth
curl -s https://api.hyperliquid.xyz/info \
  -H 'Content-Type: application/json' \
  -d '{"type":"candleSnapshot","req":{"coin":"SKY","interval":"1m","startTime":1781817000000,"endTime":1781830000000}}'

# Check if signals_hermes_runtime gap300_state is stale for the token
python3 -c "
import sqlite3, datetime
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute('SELECT * FROM gap300_state WHERE token=?', ('SKY',))
print(cur.fetchone())
"
```

---

## Fixes Needed

1. **accel_300.py data gap guard:** The current guard only flags bars with > mean+3σ spacing. When entire minutes are missing from price_history (not a spacing anomaly, just nothing), the guard passes silently. Need to add a **time-range continuity check**: if the latest price is > 120 seconds old OR if the total bar count at the signal time is less than expected for the lookback window, return `[]`.

2. **signal_compactor value column collision:** When multiple signals are merged via `GROUP_CONCAT`, the `value` column (which stores gap_pct for accel-300) gets the last-write-wins value from whichever signal was processed last. RS signals write their confidence, overwriting gap_pct. The compaction query should either store gap_pct and RS confidence in separate columns, or prevent merging that destroys signal-specific metadata.

3. **EMA300 regime cross-check in compaction:** Before executing, verify signal direction aligns with current EMA300 regime. A `SHORT` signal when price is > 0.5% above EMA300 should be flagged or suppressed regardless of other scores.
