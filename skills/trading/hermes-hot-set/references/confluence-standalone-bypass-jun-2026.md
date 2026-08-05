# Confluence Gate Blocking Standalone Signals (2026-06-09)

## Problem

Signal compactor confluence gate (signal_compactor.py:571-589) requires 2+ unique signal types. Pure accel-300 signals (no RS co-signal) were blocked → hotset stays empty → 0 trades.

**Evidence from trading.log:**
```
🔒 [CONFLUENCE-GATE-BLOCK] ONDO SHORT: only 1 unique types {accel-300-} — need 2+
🔒 [CONFLUENCE-GATE-BLOCK] DASH SHORT: only 1 unique types {accel-300-} — need 2+
Pre-filter: 0 signals passed safety filters
Wrote hotset.json with 0 tokens (cycle=60244)
```

Signal counts in DB:
- 248 pure accel-300 EXPIRED (confluence blocked)
- 18 PENDING (currently blocked)
- 5 EXECUTED (only had 2+ sources)

## Root Causes

1. **Confluence gate too strict** — pure accel-300 (conf=70) always blocked since no RS co-signal arrives within 5-min window
2. **RS_TOUCH_HARD_CAP=150 too aggressive** — blocking signals in 151-180 range which has partial validity; 160 RS signals blocked (151-200 range)
3. **No bypass for strong standalone signals** — accel-300 with very high confidence should sometimes fire without RS

## Fix Applied

### 1. Accel-300 Standalone Bypass (signal_compactor.py)

Added bypass for pure accel-300 signals with high enough confidence:

**hermes_constants.py:**
```python
ACCEL_300_STANDALONE_BYPASS_ENABLED = True   # kill switch
ACCEL_300_STANDALONE_BYPASS_CONFIDENCE = 70  # accel-300 fires at 70 max
```

**signal_compactor.py confluence gate (line ~581):**
```python
if unique_signal_types >= 2:
    pass_gate = True
    gate_msg = f'{unique_signal_types} unique types'
else:
    # Accel-300 Standalone Bypass
    if (ACCEL_300_STANDALONE_BYPASS_ENABLED
            and unique_signal_types == 1
            and source.startswith('accel-300')
            and conf >= ACCEL_300_STANDALONE_BYPASS_CONFIDENCE):
        pass_gate = True
        gate_msg = f'standalone accel-300 conf={conf:.0f}% >= {ACCEL_300_STANDALONE_BYPASS_CONFIDENCE}%'
    else:
        gate_msg = f'only {unique_signal_types} unique types {{{source}}} — need 2+'
```

**Note:** ACCEL_300_STANDALONE_BYPASS_CONFIDENCE must be <= 70 (accel-300 cap). Setting to 70 means ALL pure accel-300 signals pass (since they all fire at conf=70). Setting to 71+ would mean NO signals pass (bypass never fires).

### 2. RS_TOUCH_HARD_CAP Raised (hermes_constants.py)

```python
RS_TOUCH_HARD_CAP = 180  # was 150 — preserve 151-180 range which has partial validity
```

Also added `RS_DECIDER_MIN_TOUCHES = 80` (was 150) — lower floor lets more RS through, hard cap catches the truly exhausted ones.

### 3. New Constants Added

All previously hardcoded values moved to hermes_constants:
- `ACCEL_300_MARGINAL_ACCEL_BARS = 3` — bars_since_cross threshold for marginal acceleration check
- `ACCEL_300_BARS_UNKNOWN = 999` — sentinel when cross_bar not found
- `ACCEL_300_BAR_GAP_THRESH_SEC = 150` — bar-to-bar gap guard threshold
- `RS_ATR_DIST_FALLBACK = 999` — atr_dist fallback when atr_pct=0

## Constants Centralized (hermes_constants.py)

| Constant | Value | Location |
|----------|-------|----------|
| ACCEL_300_STANDALONE_BYPASS_ENABLED | True | line ~725 |
| ACCEL_300_STANDALONE_BYPASS_CONFIDENCE | 70 | line ~726 |
| RS_TOUCH_HARD_CAP | 180 | line ~267 |
| RS_DECIDER_MIN_TOUCHES | 80 | line ~266 |
| RS_BROKEN_SHORT_ENABLED | False | line ~273 |
| ACCEL_300_MIN_GAP_PCT_LONG | 0.20 | line ~479 |
| ACCEL_300_MIN_GAP_PCT_SHORT | 0.25 | line ~480 |
| ACCEL_300_MIN_GAP_GROWTH_SHORT | 0.07 | line ~475 |
| ACCEL_300_STALE_BARS | 60 | line ~490 |
| ACCEL_300_STALE_BARS_SHORT | 55 | line ~491 |
| ACCEL_300_MARGINAL_ACCEL_BARS | 3 | line ~493 |
| ACCEL_300_BARS_UNKNOWN | 999 | line ~494 |
| ACCEL_300_BAR_GAP_THRESH_SEC | 150 | line ~495 |

## Diagnostic Commands

```bash
# Check confluence gate blocks
grep "CONFLUENCE-GATE-BLOCK" /var/www/hermes/logs/trading.log | tail -20

# Check pure accel-300 signals
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT decision, COUNT(*) FROM signals WHERE source IN ('accel-300+','accel-300-') AND created_at > datetime('now', '-2 hours') GROUP BY decision;"

# Check hotset contents
cat /var/www/hermes/data/hotset.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'hotset: {len(d.get(\"entries\",[]))} entries')"

# Verify bypass firing
grep "standalone accel-300" /var/www/hermes/logs/trading.log | tail -10
```

## What Still Gets Blocked

- Pure rs-s or rs-r (no accel-300) — still needs 2+ signal types
- Pure mtp-zscore — still needs 2+ signal types
- accel-300 with conf < 70 — would never happen (cap is 70)

## Files Modified

- `/root/.hermes/scripts/hermes_constants.py` — 12 new/changed constants
- `/root/.hermes/scripts/signal_compactor.py` — standalone bypass added at confluence gate
- `/root/.hermes/scripts/signals/accel_300.py` — per-direction thresholds + hardcoded values replaced
- `/root/.hermes/scripts/signals/rs.py` — touch hard cap + broken-short kill-switch + hardcoded 999 replaced
- `/root/.hermes/scripts/decider_run.py` — touch hard cap gate added