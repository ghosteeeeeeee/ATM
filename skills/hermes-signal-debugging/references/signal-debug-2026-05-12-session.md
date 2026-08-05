# Signal Debug: Session Learnings 2026-05-12

## SHORT Signal Confidence Bias — Root Cause

**Problem:** SHORT signals always score lower than LONG because the best SHORT signals emit structurally lower confidence:
- `accel-300+` (LONG): 60-70 base → max 70 (cap lowered from 80 today)
- `ema9-sma20-` (SHORT): 55-68 base → structurally lower
- `hh_hl_breakout` SHORT: flat 65

**Fix applied:** Lowered `accel-300+` cap from 80→70 (`signals/accel_300.py` line 390). Makes them competitive.

## Confluence Collapse Fix — Numeric Suffixes

**Problem:** `ma-death14,ma-death17` were counted as 2 unique types (fake confluence), `hhh-short5,hhh-short6` same. Same signal at different bars_since timestamps should be 1 type.

**Fix in `signal_compactor.py`** — `_signal_type_key()` strips numeric suffixes:
```python
def _signal_type_key(part: str) -> str:
    m = re.match(r'^([a-z][a-z0-9_-]*)([+-]?)(\d+)$', part)
    if m:
        prefix, suffix, _ = m.groups()
        return prefix + suffix  # 'hhh-short6' → 'hhh-short'
    return part
```

This applies to both directions (LONG and SHORT) symmetrically.

## Trend Purity Required for ALL Entries

**Problem:** Previously only accel-300+ was required for LONG. Now both LONG and SHORT require trend_purity co-signal:
- LONG: `trend_purity+` OR `tl_break_long` required
- SHORT: `trend_purity-` required

This was implemented in TWO places in `signal_compactor.py`:
1. `run_compaction` hot-set filter (line 862-875) 
2. `_filter_safe_prev_hotset` for preserved entries (line 1304-1314)

**Effect:** Hot-set goes empty — confluence gate (2+ unique types) + trend_purity requirement together are very strict. `signal_gen` fires at most 1 signal type per token per cycle, so tokens rarely get 2+ unique types within 5-min window. **This is correct behavior.**

## signals.json vs hotset.json Divergence

**Key finding:** `signals.json` (written by `_enrich_and_write_signals` in signal_compactor) contains APPROVED entries that predate recent filter changes. Entries like `accel-300+` (ZK, 2Z) and SHORTs without `trend_purity-` (LTC, FIL, SKY) are stale — they were APPROVED before the trend_purity requirement was added.

**Why it confused the user:** The dashboard showed `accel-300+` alone passing despite the new filter. The filter IS working — hotset.json is correctly empty. signals.json APPROVED is stale legacy data.

**Rule:** When diagnosing "why is X in hot-set despite rule Y", check `/var/www/hermes/data/hotset.json` (canonical source of truth), NOT `signals.json`.

## hh_hl_breakout SHORT Bounce Trap

**Problem:** `hh_hl_breakout` SHORT fires when `price < last_sw_price` (price breaks below the swing low). In a ranging market, price breaks below the LL, bounces, then reverses. The signal fires at the breakdown point — not the bounce.

**Fix discussed (not yet implemented):** Add range-position filter — only fire SHORT if price is in bottom 1 ATR of the 20-bar range:
```python
recent_high = max(c['high'] for c in candles[-20:])
atr = _compute_atr(candles)
if price > recent_high - atr:  # too close to range top → bounce territory
    return None
```

## Per-Direction Kill-Switch Flags

All 27 signals now have `*_PLUS_ENABLED` and `*_MINUS_ENABLED` flag pairs in `hermes_constants.py`. Short for signals missing them:
- `accel_300.py` — added (line 370-375 patch)
- `rs.py` — added before LONG/SHORT add_signal
- `counter_flip.py` — added before add_signal
- `tl_break.py` — added before SHORT add_signal
- `mtf_macd.py` (registry name `hmacd_mtf`) — added before add_signal

## Debugging Command Reference

```bash
# Check canonical hot-set (source of truth)
cat /var/www/hermes/data/hotset.json

# Run signal_compactor verbose to see filter decisions
cd /root/.hermes/scripts && python3 signal_compactor.py --verbose

# Check signals.json APPROVED (note: may be stale)
cat /var/www/hermes/data/signals.json | python3 -c "..."

# Check signals in DB
cd /root/.hermes/scripts && python3 << 'EOF'
import sqlite3, sys
sys.path.insert(0, '.')
from paths import RUNTIME_DB
conn = sqlite3.connect(RUNTIME_DB)
cur = conn.cursor()
cur.execute("SELECT token, direction, source, confidence FROM signals WHERE decision='APPROVED' ORDER BY created_at DESC LIMIT 20")
for r in cur.fetchall():
    print(f"{r[0]} {r[1]} conf={r[3]} src={r[2]}")
EOF
```

## Validated Findings

1. **trend_purity filter is working correctly** — confirmed via `signal_compactor --verbose` output showing `🚫 [HOTSET-FILTER] TIA: LONG blocked — requires trend_purity+`
2. **Confluence gate is working correctly** — confirmed via `🔒 [CONFLUENCE-GATE-BLOCK]` logs
3. **Empty hot-set is expected** — confluence (2+ types) + trend_purity required together is very strict; signal_gen can only produce 1 type per token per cycle
4. **signals.json is NOT the hot-set** — it's a separate write from `_enrich_and_write_signals` and can contain stale entries
5. **`hh_hl_breakout` SHORT fires on breakdown** — correct direction but catches the initial breakdown in ranging markets before the bounce