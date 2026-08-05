# RS Signal Compaction Death — 2026-05-28 Investigation

## Root Cause

All RS signals expire with `decision_reason='compaction_stale_5min'` because:
1. `signal_compactor.py` lines 391-400: PENDING signals older than 5 min without co-signals are EXPIRED
2. RS is single-source — no second signal type arrives within 5 min → every RS PENDING dies

## Key Data

```
RS signals by day:
  2026-05-27: 33 (total)
  2026-05-28: 70 (total through 05:00)

RS signal decisions (24h):
  EXPIRED: 102 (all compaction_stale_5min)
  PENDING: 1 (W, at 04:55:29 — survived because it just arrived)

RS signals by hour (2026-05-27-28):
  2026-05-28 04:00:  5
  2026-05-28 03:00: 23
  2026-05-28 02:00: 15
  2026-05-28 01:00: 20
  2026-05-28 00:00:  7
  2026-05-27 23:00: 14
  2026-05-27 22:00: 19
```

**Important context:** RS signals only started May 27 — before that, zero RS signals existed in DB.
The user said "previously producing many signals and then stopped" — but the data shows signals ARE
being generated. The issue is compaction is killing them all except one (W).

## Key Diagnostics

```bash
# RS signals in last 60 min by type
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT signal_type, COUNT(*) FROM signals \
   WHERE created_at >= datetime('now', '-60 minutes') GROUP BY signal_type;"

# Why RS signals expire
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT decision_reason, COUNT(*) FROM signals WHERE signal_type='support_resistance' \
   AND decision='EXPIRED' GROUP BY decision_reason;"

# Last RS signals with their age
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, created_at, decision, combo_key FROM signals \
   WHERE signal_type='support_resistance' ORDER BY ROWID DESC LIMIT 10;"

# Price history freshness — is the non-blacklist universe updating?
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
import hermes_constants as hc
import sqlite3, time
blacklist = hc.SHORT_BLACKLIST | hc.LONG_BLACKLIST
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
c = conn.cursor()
now = int(time.time())
c.execute('SELECT token, MAX(timestamp) FROM price_history GROUP BY token')
for token, max_ts in c.fetchall():
    age = now - max_ts
    if age > 120 and token not in blacklist:
        print(f'STALE: {token} {age}s')
"

# Run rs manually — confirm it fires on fresh tokens
cd /root/.hermes/scripts && python3 -c "
import sys; sys.path.insert(0, '.')
from signal_schema import init_db, get_all_latest_prices
from signals.rs import scan_rs_signals
init_db()
prices = get_all_latest_prices()
# Filter to non-blacklisted + fresh
import hermes_constants as hc
blacklist = hc.SHORT_BLACKLIST | hc.LONG_BLACKLIST
valid = {k:v for k,v in prices.items() if v.get('price') and k not in blacklist}
added, tokens = scan_rs_signals(valid)
print(f'RS signals: {added}, tokens: {tokens}')
"
```

## Confluence Requirement is Working As Designed

The 5-min expiry is intentional — signals that can't find a co-signal within 5 min are
low-quality (single-source). Only W survived because its timestamp (04:55:29) is only ~5 min old
as of the last compaction run.

The real question: why can't RS find a co-signal within 5 min? Because:
1. RS fires → PENDING with `combo_key='W:LONG:rs-s184'`
2. No other signal fires for W in the next 5 min
3. Compaction expires it

**Fix options:**
- Increase signal diversity so second source arrives faster (other signals need to fire for same coin)
- Increase the 5-min window (risky — allows stale single-source signals to persist)
- Make RS self-contained with its own co-signal requirement (similar to mtp_zscore which has internal confluence)

## Related Bugs

- Bug 20 (price_collector oneshot overlap): caused complete signal starvation (all signals reported stale)
- Confluence gate starvation (2026-05-28): hot-set stays empty because only 1 signal type fires
- RS itself was working fine — it fired 1 signal when tested against fresh tokens