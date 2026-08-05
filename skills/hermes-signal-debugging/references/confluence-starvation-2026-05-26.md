# Confluence Starvation — 2026-05-26

## Problem
System-wide signal starvation: hotset.json stays empty, no trades firing, PENDING signals never graduate.

## Root Causes

### 1. CONFLUENCE GATE: 2+ unique signal types required
Every blocked entry in trading.log shows:
```
CONFLUENCE-GATE-BLOCK: only 1 unique types {rs-s##} — need 2+
```

The signal type normalizer strips ALL trailing digits:
```
rs-s1051, rs-s1251, rs-s440 → normalized to 'rs-s' (ONE type)
rs-r234, rs-r225 → normalized to 'rs-r' (ONE type)
```

**Multiple RS levels at different prices = ONE signal type.** No second signal type means no entry.

### 2. zscore-pump not firing
At threshold=3.0, lookback=150 bars, almost no tokens qualify:
```
GRIFFAIN: z=-0.795, LINK: z=-0.916, BCH: z=-1.137
2Z: z=-1.470, ME: z=-0.903, FET: z=-0.283, LIT: z=-1.206
AVAX: z=-0.325, OP: z=-0.927
```
No |z| > 3.0 means no zscore-pump companion signal → RS-only setups always blocked.

### 3. Price age gap
signals_hermes.db price_history: 179/191 tokens have data age ~2.5min (fresh).
12 tokens are stale (>5min).
All confluence-blocked tokens (GRIFFAIN, LINK, BCH, etc.) have FRESH prices — the issue is signal computation, not data.

### 4. Historical firing evidence
The system DID fire confluence signals earlier (AVAX SHORT rs-r641+zscore-pump-, LIT SHORT rs-r2093+rs-r740+zscore-pump-).
These required BOTH strong RS levels AND strong zscore-pump momentum simultaneously — rare.

## What Changed
- Around 01:00-02:00 UTC, market shifted to RS-only signals (momentum died)
- zscore-pump firing rate dropped to near zero as price became choppy/sideways
- Confluence gate then blocked everything since RS alone never qualifies

## Key Files
- `signal_compactor.py` lines 530-580: confluence gate logic + _signal_type_key normalizer
- `signals/zscore_pump.py`: zscore-pump signal generation (threshold=3.0, lookback=150)
- `signals_hermes_runtime.db`: signals table (source column = comma-separated parts)
- `signals_hermes.db`: price_history (1m closes, fresh every ~1min)

## Diagnostic Commands
```bash
# Check signal composition in runtime DB
python3 -c "
import sqlite3, time, re
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
cur = conn.cursor()
cur.execute('SELECT token, direction, source, confidence, created_at FROM signals ORDER BY created_at DESC LIMIT 50')
rows = cur.fetchall()
for r in rows:
    parts = r[2].split(',') if r[2] else []
    unique = set(re.sub(r'\d+$', '', p) for p in parts)
    print(f\"{r[0]:8} {r[1]:5} ut={len(unique)} src='{r[2]}'\")
"

# Check zscore-pump readiness for key tokens
python3 -c "
import sqlite3, time, statistics
PRICE_DB = '/root/.hermes/data/signals_hermes.db'
tokens = ['AVAX','LINK','BCH','GRIFFAIN','2Z','LIT','FET','OP']
for tok in tokens:
    conn = sqlite3.connect(PRICE_DB)
    cur = conn.cursor()
    cur.execute('SELECT price FROM price_history WHERE token=? ORDER BY timestamp DESC LIMIT 160', (tok,))
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    if len(rows) < 152: print(f'{tok}: only {len(rows)} prices'); continue
    rows.reverse()
    chunk = rows[-150:]
    mean = statistics.mean(chunk); stdev = statistics.stdev(chunk)
    z = (rows[-1] - mean) / stdev if stdev > 0 else 0
    print(f'{tok:8}: z={z:+.3f} |z|_threshold=3.0 → {\"SIGNAL\" if abs(z)>3.0 else \"no signal\"}')
"

# Check hotset and confluence blocking
grep "CONFLUENCE-GATE-BLOCK\|HOTSET-FINAL-ADD\|PENDING" /var/www/hermes/logs/trading.log | tail -30
```

## Potential Fixes
1. **Reduce zscore-pump threshold** (3.0 → 2.5) so it fires more often as companion
2. **Reduce zscore-pump lookback** (150 → 80-100) to catch shorter momentum cycles
3. **Multi-level RS exemption**: if RS has 3+ levels at different prices for same direction, treat as valid multi-source (exception to confluence rule)
4. **Confluence softening**: allow single-source signals through if confidence > 90 AND survival_score > threshold