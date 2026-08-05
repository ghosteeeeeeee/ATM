# RS Signal Staleness — New Pattern (2026-05-28)

## Symptom
RS fires only 1 signal (W) on a full scan of 92 tokens. BTC and 120+ other tokens show "stale price_history" in RS output.

## Root Cause (Different from Prior RS Staleness Bugs)

The `_get_candles_1m()` staleness check in rs.py IS working correctly — it checks `rows[0][0]` (newest row, after the ORDER BY ASC subquery wrapper). The staleness is **legitimate data age**, not a code bug.

**The real cause: price_collector only writes prices for non-blacklisted tokens.**

- `price_collector.py` filters out `SHORT_BLACKLIST | LONG_BLACKLIST` (130 tokens) before writing
- BTC is in SHORT_BLACKLIST → price_collector never writes BTC to price_history
- BTC's price_history row is 37+ minutes old → legitimately stale → rs.py correctly skips it
- 92 tokens get fresh prices per cycle (non-blacklisted HL universe)
- 120 tokens are blacklisted (stale by design)
- 18 tokens are delisted from Hyperliquid (stale, not in allMids response)

```
Fresh (<2min): 92 tokens   ← non-blacklisted HL universe
Stale (blacklisted): 120 tokens ← never written by price_collector
Stale (non-blacklisted): 18 tokens ← delisted from HL, not in allMids
```

## Key Finding

**rs.py code is working correctly.** When tested on 92 fresh tokens, it fired 1 signal (W).

The limitation is the token universe, not the rs.py logic.

## Diagnostic Commands

```bash
# Check price_history freshness for all tokens
python3 -c "
import sys, time, sqlite3
sys.path.insert(0, '/root/.hermes/scripts')
import hermes_constants as hc
blacklist = hc.SHORT_BLACKLIST | hc.LONG_BLACKLIST
now = int(time.time())
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
c.execute('SELECT token, MAX(timestamp) FROM price_history GROUP BY token')
rows = c.fetchall()
fresh = sum(1 for _, ts in rows if (now-ts) <= 120)
stale_bl = sum(1 for t, ts in rows if (now-ts) > 120 and t in blacklist)
stale_nbl = sum(1 for t, ts in rows if (now-ts) > 120 and t not in blacklist)
print(f'Fresh: {fresh}, Stale-blacklisted: {stale_bl}, Stale-non-blacklisted: {stale_nbl}')
"

# Check BTC specifically
sqlite3 /root/.hermes/data/signals_hermes.db "SELECT token, MAX(timestamp), datetime(MAX(timestamp),'unixepoch') FROM price_history WHERE token='BTC' GROUP BY token"

# Check if token is in blacklist
python3 -c "import sys; sys.path.insert(0,'/root/.hermes/scripts'); import hermes_constants as hc; print('BTC in SHORT_BLACKLIST:', 'BTC' in hc.SHORT_BLACKLIST)"
```

## Relationship to Prior RS Staleness Bugs

| Date | Root Cause | Fix |
|------|-----------|-----|
| 2026-05-12 | `add_signal()` missing source/confidence args | Added missing kwargs |
| 2026-05-12 | `rows[-1]` checked wrong edge (old bug, was actually correct after subquery) | No fix needed |
| 2026-05-28 | price_collector doesn't write blacklisted tokens → legitimate staleness | Not a rs.py bug |

## Fix Options (Not Implemented)

1. **Shorten freshness threshold** in rs.py: `_get_candles_1m()` uses 120s. Lower values risk firing on old data.
2. **Investigate why BTC is in SHORT_BLACKLIST** — it was added at some point, causing price_history to stop updating.
3. **18 non-blacklisted stale tokens** (AI, BNT, CATI, etc.) are delisted from HL — their staleness is correct behavior, no fix needed.