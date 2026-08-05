---
name: analyze-trades
description: Archive closed trades, reconcile prices, rebuild A/B test data, analyze results, and apply winning adjustments to Hermes trading system.
tags: [hermes, trading, analysis, ab-test, trades]
author: T
created: 2026-04-01
updated: 2026-05-12
---

# Analyze Trades — Hermes Trading Analysis

Archives closed trades, reconciles prices, rebuilds A/B test data, analyzes results, and applies indicator weight adjustments.

## Archive Tool: archive-trades.py

**Primary archiver** — `/root/.hermes/scripts/archive-trades.py` (524 lines). Use this, not the old inline script.

```bash
# Dry run — see what would be archived
python3 /root/.hermes/scripts/archive-trades.py --dry-run

# Actually archive (writes JSONL gzip, then deletes from PostgreSQL)
python3 /root/.hermes/scripts/archive-trades.py --apply

# Rebuild analysis SQLite DB from scratch
python3 /root/.hermes/scripts/archive-trades.py --rebuild-db

# Limit for testing
python3 /root/.hermes/scripts/archive-trades.py --dry-run --limit 10
```

**What it does, in order:**
1. Fetches closed trades from PostgreSQL (`status='closed'`, `close_time IS NOT NULL`)
2. Builds `/root/.hermes/archive/trades_analysis.db` (SQLite WAL mode) with full trade + signal join
3. Archives trades to gzipped JSONL in `/root/.hermes/archive/trades/` — one file per day, appends not overwrites, dedupes by trade ID
4. Deletes archived trades from PostgreSQL (only after confirmed archive write)

**⚠️ Archive format:** New archives are **JSONL gzip** (one JSON object per line), NOT the old `{"archived_at", "count", "columns", "trades": [...]}` blob. `analyze_archive_trades.py` currently only reads the old blob format. See `references/archive-jsonl-fix.md` for the deserialization patch.

---

## Key Findings (2026-04-06 — 209 closed trades after cleanup)

### System Bug Summary
| Bug | Count | Impact |
|-----|-------|--------|
| hl_position_missing | 19 DELETED | Orphan HL positions with corrupted entry prices (~$10). Root cause: `add_orphan_trade` parameter swap (entry_price ↔ amount_usdt). Fix applied 2026-04-05. |
| guardian_missing | ~50 | Guardian lost track, forced near-zero close — top winners |
| trailing_exit | ~30 | Trailing SL triggered — solid wins |

### System Health (cleaned)
- **Total closed:** 209 trades (after 19 corrupted deletions)
- **Net PnL:** +$17.90 | LONG: +$10.84 | SHORT: +$7.06
- LONG: 92 trades (43W/49L, 47% WR)
- SHORT: 117 trades (53W/64L, 45% WR) ← unexpectedly strong

### Systematic Losers
| Token | Direction | n | Net | Action |
|-------|-----------|---|-----|--------|
| ME | LONG | 10 | -$2.77 | **ADDED TO BLACKLIST** 2026-04-06 |

## Signal Root-Cause Step (2026-05-21)

**Trigger:** T asks "why are we always on the wrong side" or "wrong side of the trade" — this is a SIGNAL QUALITY issue, not just a PnL reporting issue.

When analyzing losing/wrong-side trades, for each losing trade:
1. Identify the triggering signal from `signal_type` field
2. Check `confluence` field — was there a second signal, or was it single-source?
3. Check `regime` field — did signal direction match regime?
4. If single-source signal on wrong-side trade → that signal type is the problem, not the system
5. Cross-reference with hot-set.json during the trade window — was the signal in the hot-set or a rogue?

**Key insight (2026-05-21):** Single-source signals are NOT allowed in hot-set. All hot-set trades need confluence. If a losing trade had only one signal, it should NOT have been in the hot-set — the filter failed.

**Output format for wrong-side analysis:**
```
COIN DIRECTION | Entry | Exit | PnL% | Signal | Regime | Confluence | Was in Hot-Set?
```

## BLACKLIST UPDATES (2026-04-06)
- **+ME** to LONG_BLACKLIST — 10 trades, net -$2.77 (hermes_constants.py)

## Actions Required

1. **ME LONG blacklist** — Added to LONG_BLACKLIST in hermes_constants.py.
2. **Corrupted trades purged** — 19 `hl_position_missing` trades with entry ~$10 deleted. DB now clean.
3. **SHORT vs LONG balance** — MONITOR: SHORT WR 45% vs LONG WR 47% in recent batch. Consider relaxing SHORT regime filter.
4. **Guardian aggressiveness** — Consider: guardian is closing trades before trailing SL triggers. Top winners close at 1-2% via guardian while trailing SL could capture 3-5%.
5. **Signal quality audit** — After any "wrong side" complaint, run Signal Root-Cause step above before reporting PnL numbers.

## Hot Set Validation Rules

Tokens in hot set must have ALL of:
- `z_score` not NULL
- `rsi_14` not NULL
- `macd_hist` not NULL
- `confidence` > 60
- Minimum regime alignment check (per-token z_score_tier + macro regime)
- NOT in HOTSET_BLOCKLIST

## Signal ↔ Trade Cross-Reference (CRITICAL)

Trade records in the archive contain **experiment metadata** (SL distance variant, entry timing, trailing stop settings) but **NOT actual indicator values** (z_score, rsi_14, macd_hist, confidence). To get indicator data for a trade, you MUST look up the corresponding signal.

### Where Signal Data Lives

Signals are archived as gzipped JSONL in:
- `/root/.hermes/archive/signals/signals_2026-04.jsonl.gz` — April 2026 (starts **April 3 04:28 UTC**)
- `/root/.hermes/archive/signals/signals_2026-05.jsonl.gz` — May 2026

⚠️ **Gap alert**: Signals archive starts April 3. Any trade opened before that date (March 31, April 1, April 2) will have **NO matched signals** even if the trade itself is in the archive. The live signals DB (`signals_hermes_runtime.db`) only goes back to May 6 — not useful for historical analysis.

### Matching Trades to Signals

```python
import gzip, re, json, os
from datetime import datetime
from collections import defaultdict

def parse_dt(s):
    """Parse ISO datetime strings, stripping fractional seconds and TZ."""
    if not s: return None
    s = s.replace('Z', '').replace('+00:00', '')
    s = re.sub(r'\.\d+', '', s)  # drop fractional seconds
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

### Key Signal Fields for Analysis

| Field | What it tells you |
|---|---|
| `z_score` | Distance from mean — negative = oversold, positive = overbought |
| `rsi_14` | 30 = oversold, 70 = overbought |
| `macd_hist` | Momentum direction and strength |
| `confidence` | Signal conviction (0–100) |
| `signal_type` | Which indicator fired: `mtf_macd`, `mtf_zscore`, `percentile_rank`, `rsi_individual`, `confluence` |
| `momentum_state` | `bullish` / `bearish` / `neutral` |
| `decision` | `EXECUTED` / `APPROVED` / `EXPIRED` / `SKIPPED` / `COMPACTED` |

### Winner Signal Fingerprint (from archive analysis, 25 matched trades)

From 25 matched winners (April 3+ trades):
- **z_score avg: -0.662** (slightly oversold — mean reversion works)
- **rsi_14 avg: 41.2** (mid-range, not extreme)
- **confidence avg: 71.3** (moderate)
- **signal_type WR**: mtf_macd 100%, percentile_rank 100%, mtf_zscore 100%, confluence 100%, rsi_individual 100%

## Archive Exploration

Archived trades live in **`/root/.hermes/archive/trades/`** — two formats coexist:

**Old JSON blob** (pre-2026-05-11):
```
{"archived_at", "source", "count", "columns", "trades": [...]}
```
42 files, ~5,556 total archived trades.

**New JSONL gzip** (2026-05-11 onward, from archive-trades.py):
```
{id: 9238, token: "ATOM", ..., "archived_at": "2026-05-12T..."}
{id: 9234, token: "XRP", ..., "archived_at": "2026-05-12T..."}
```
One file per day (e.g., `trades_archive_2026-05-12.json.gz`), appends not overwrites, dedupes by trade ID.

**`analyze_archive_trades.py` only reads the old blob format.** See `references/archive-jsonl-fix.md` for the deserialization patch before analyzing new archives.

```bash
# Inspect old JSON blob archive
python3 -c "
import json
d = json.load(open('/root/.hermes/archive/trades/trades_archive_20260508_015041.json'))
print(d['count'], 'trades')
print('Columns:', d['columns'])
print('Sample:', d['trades'][0])
"

# Quick count ALL archives (both formats)
python3 -c "
import json, gzip, os
total = 0
for f in sorted(os.listdir('/root/.hermes/archive/trades/')):
    path = '/root/.hermes/archive/trades/' + f
    try:
        if f.endswith('.json.gz'):
            with gzip.open(path, 'rt') as fh:
                first = fh.readline().strip()
            rec = json.loads(first)
            if 'trades' in rec:  # old blob
                n = len(rec.get('trades', []))
            else:  # JSONL
                n = sum(1 for line in gzip.open(path, 'rt') if line.strip())
        elif f.endswith('.json'):
            d = json.load(open(path))
            n = len(d.get('trades', []))
        print(f'{f:55s} {n:5d}')
        total += n
    except Exception as e:
        print(f'ERROR {f}: {e}')
print(f'TOTAL: {total}')
"

## Live Trade Monitoring

**Critical:** Always watch `[brain.py]` logs for `✅ confirmed on HL` or `❌ FAILED`. When HL returns `success=True` on `mirror_open`, brain.py now (2026-05-21) calls `get_open_hype_positions()` to verify the position actually exists before writing to DB. If not found, it calls `close_position()` to clean up and returns None.

When T reports "trade opened and closed immediately":
1. Check `pipeline.log` for `✅ DOT confirmed on HL` (verification passed) or `❌ mirror_open FAILED`
2. Check `sync-guardian.log` — HL count vs DB count at same timestamp
3. Query the trade record — exit vs SL vs entry to determine if SL was actually hit
4. For SHORT: profit if exit < entry; SL hit only if exit >= sl (price went UP to hit SL)
5. `close_reason=atr_sl_hit` is a catch-all — not always a real SL trigger; check actual price distance

When T reports "trade opened and closed immediately":
1. Check `mirror_open returned: success=` — False = HL position never opened
2. Check guardian log `HL: N positions | DB: N open trades` — HL < DB = orphan
3. Examine `atr_sl_hit` close_reason against actual price vs SL (not always real)
4. Check `DEBUG _col_map: 44 entries → 44 params` for every INSERT

**Key commands for live monitoring:**
```bash
# Guardian: 15s cycle, shows orphan counts
tail -f /root/.hermes/logs/sync-guardian.log

# Pipeline: ATR updates, position manager closes
tail -f /root/.hermes/logs/pipeline.log

# Quick open positions check
cd /root/.hermes/scripts && python3 -c "
from _secrets import BRAIN_DB_DICT
import psycopg2
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute(\"SELECT id, token, direction, entry_price, stop_loss, current_price, pnl_pct FROM trades WHERE status='open' ORDER BY open_time DESC\")
for r in cur.fetchall():
    print(f\"id={r[0]} {r[1]} {r[2]} entry={r[3]:.4f} SL={r[4]:.4f} cur={r[5]:.4f} pnl={r[6]:.3f}%\")
"
```

See `references/live-trade-monitoring-2026-05-21.md` for full incident post-mortem of DOT #10226 — `atr_sl_hit` catch-all close reason, HL verification fix, SHORT profit analysis.

## Re-run Analysis

Run this skill weekly or after major pipeline changes. Archive before each run.
