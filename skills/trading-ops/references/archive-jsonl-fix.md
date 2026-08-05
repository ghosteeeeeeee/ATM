# archive-trades.py JSONL Format Fix

**Problem:** `archive-trades.py` (deployed 2026-05-11) writes archives as **gzipped JSONL** — one JSON object per line. The existing `analyze_archive_trades.py` `load_trades()` function only handles the old `{"archived_at", "count", "columns", "trades": [...]}` blob format. New archives are silently invisible to analysis.

**Files affected:**
- `/root/.hermes/scripts/analyze_archive_trades.py` — `load_trades()` function (line 45)
- `/root/.hermes/skills/trading-ops/scripts/analyze_archive_trades.py` — same script in skill dir (line 45)

## Fix for load_trades()

In `load_trades()`, after the existing `.json` handling, add a `.json.gz` branch that tries JSONL first:

```python
def load_trades():
    all_trades = []
    for f in sorted(os.listdir(ARCHIVE_TRADES)):
        if not f.endswith('.json') and not f.endswith('.json.gz'):
            continue
        path = os.path.join(ARCHIVE_TRADES, f)
        try:
            if f.endswith('.json.gz'):
                # Try JSONL first (archive-trades.py format since 2026-05-11)
                with gzip.open(path, 'rt') as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                            if isinstance(rec, dict) and rec.get('pnl_usdt') is not None:
                                all_trades.append(rec)
                        except json.JSONDecodeError:
                            # Not JSONL — fall through to blob parse
                            fh.seek(0)
                            d = json.load(fh)
                            trades = d.get('trades', [])
                            if isinstance(trades, list):
                                for t in trades:
                                    if isinstance(t, dict) and t.get('pnl_usdt') is not None:
                                        all_trades.append(t)
                            break
            else:
                with open(path) as fh:
                    d = json.load(fh)
                trades = d.get('trades', [])
                if isinstance(trades, list):
                    for t in trades:
                        if isinstance(t, dict) and t.get('pnl_usdt') is not None:
                            all_trades.append(t)
        except Exception as e:
            print(f"  SKIP {f}: {e}", file=sys.stderr)
    return all_trades
```

**Required imports** (already present at top of script):
```python
import gzip, json, os, sys  # gzip and json already imported
```

## How to distinguish formats without parsing

- **JSONL gzip**: first line parses as a dict with integer-like `id` field (e.g., `{"id": 9238, ...}`)
- **Old blob**: first line parses as a dict with `trades` key (a list)

## Verification after fix

```bash
python3 /root/.hermes/scripts/analyze_archive_trades.py 2>&1 | head -5
# Should show signals + trades count including recent JSONL archives
```
