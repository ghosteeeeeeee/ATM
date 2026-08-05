# Signal Pipeline Debug Session — 2026-05-07

## Root Causes Found

### 1. `accel_300` Was Completely Dead (Critical)
**Symptom**: accel-300+ never appeared in hot-set despite being "enabled"

**Root cause**: `signals_runner.py` calls `getattr(mod, 'run', None)` to execute each signal module.
`accel_300.py` had NO `run()` function — only `scan_accel_300_signals()`. The module returned
`None` and was silently skipped every cycle. It had never fired a single signal.

**Fix**: Add `run()` wrapper to `accel_300.py`:
```python
def run() -> int:
    prices = get_all_latest_prices()
    return scan_accel_300_signals(prices)
```

**Affected signals** (13 total missing `run()`):
`rs`, `ma_cross`, `ma_cross_5m`, `hh_hl`, `guppy`, `macd_accel`, `trend_purity`,
`phase_accel`, `fast_momentum`, `momentum`, `mtf_momentum`, `hmacd`, `accel_300`

### 2. Compaction SQL Window Never Updated (Critical)
**Symptom**: pct-hermes- expires before hzscore can merge (5-min vs 5-min firing mismatch)

**Problem**: When extending window from 5→15 min, only the log message was patched.
The actual SQL `AND created_at > datetime('now', '-5 minutes')` was NOT changed.
Only `log(f"...5-min window...")` was updated to `log(f"...15-min window...")`.

**Fix**: `replace_all=True` on the SQL line too:
```python
AND created_at > datetime('now', '-15 minutes')  # replace_all=True
```

**Verification**: Run compaction and check log output shows `X combo_keys in 15-min window`.

### 3. `pct-hermes-` is a Losing Standalone Signal
**Symptom**: SHORT side flooded with pct-hermes- signals, losing money

**Data** (trades.json, 200 real trades):
| Signal | Trades | WR | PnL |
|--------|--------|-----|------|
| `accel-300+,hzscore-` | 24 | 42% | +$10.47 |
| `accel-300+` solo | 13 | 31% | +$3.45 |
| `pct-hermes-` solo | 13 | 23% | **-$0.32** |
| `hzscore+,vel-hermes-` | 5 | 20% | **-$0.47** |

**Fix**: Remove `pct-hermes-` from `GOOD_STANDALONE_SIGNALS`. It requires a co-signal.

### 4. Signal Architecture: Signals Can't Naturally Merge
**Symptom**: Despite window changes, hzscore+ and pct-hermes- never share the same token

**Root cause**: Different signal generators fire at different times on different tokens.
`hzscore+` fires on ~20 tokens (ANIME, ATOM...), `pct-hermes-` fires on ~46 tokens (ADA, AVAX...).
Zero overlap in 2 hours of data. The `GROUP BY combo_key` merging only works when the SAME
generator fires multiple times. Cross-generator merging requires either:
(a) UPSERT that merges sources on same token+direction, OR
(b) Post-insertion aggregation query

### 5. `accel-300+` Approved Too Fast
**Symptom**: accel-300+,hzscore- combo (42% WR, $10.47) only happened 24 times vs 13 solo accel-300+ trades

**Root cause**: accel-300+ in GOOD_STANDALONE_SIGNALS → gets approved within 3 minutes.
hzscore- fires every 5 minutes → can't merge because accel-300+ is already APPROVED.

**Fix**: Add minimum age check. accel-300+ must survive 5 minutes in PENDING before approval:
```python
is_accel = ck and 'accel-300+' in ck
min_age = 5.0 if is_accel else 0.0
if age_m < min_age:
    still_pending_ids.append(sid)
    continue
```

## Hot-Set Quality Baseline (2026-05-07)

All-time from trades.json (200 trades, 34% WR, $30.95 total):
- `accel-300+,hzscore-`: 42% WR, $10.47 (BEST combo)
- `accel-300+` solo: 31% WR, $3.45 (still profitable)
- `hzscore+,pct-hermes-`: 50% WR, $0.43
- `pct-hermes-` solo: 23% WR, -$0.32 (LOSER)

## Accel-300+ Allowlist
`ACCEL_300_TOKEN_ALLOWLIST = ['LINK', 'UNI', 'XMR', 'AAVE', 'MKR', 'USDT', 'WBTC', 'WETH']`
When scanner runs on all tokens in DRY mode, LINK/XMR/WBTC/ETH/AAVE/UNI fire.
Live execution: `recent_trade_exists` or cooldown blocks most → only a few tokens pass.

## Debugging Commands

```bash
# Check which signals have run()
cd /root/.hermes/scripts && python3 << 'PYEOF'
import sys; sys.path.insert(0, '.')
for mod_name in ['pct_hermes','vel_hermes','hzscore','accel_300','rs','ma_cross_5m']:
    mod = __import__(f'signals.{mod_name}', fromlist=[''])
    has_run = hasattr(mod, 'run')
    print(f"{mod_name}: run={'YES' if has_run else 'MISSING'}")
PYEOF

# Check runtime DB signal production
python3 << 'PYEOF'
import sqlite3
rconn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
rc = rconn.cursor()
rc.execute("""
    SELECT signal_type, direction, COUNT(*) as n
    FROM signals WHERE created_at > datetime('now', '-30 minutes')
    GROUP BY signal_type, direction ORDER BY n DESC
""")
for r in rc.fetchall(): print(f"  {r[0]}({r[1]}): {r[2]}")
PYEOF

# Check trades.json signal breakdown
python3 << 'PYEOF'
import json
from collections import defaultdict
with open('/var/www/hermes/data/trades.json') as f:
    t = json.load(f)
closed = t.get('closed', [])
by_sig = defaultdict(lambda: {'n':0,'wins':0,'pnl':0.0})
for trade in closed:
    sig = trade.get('signal','unknown')
    by_sig[sig]['n'] += 1
    by_sig[sig]['wins'] += 1 if trade.get('pnl_pct',0) > 0 else 0
    by_sig[sig]['pnl'] += trade.get('pnl_usdt', 0)
for sig, d in sorted(by_sig.items(), key=lambda x: x[1]['pnl'], reverse=True):
    n, w, pnl = d['n'], d['wins'], d['pnl']
    print(f"  {sig[:50]:50s}: n={n:3d} WR={w/max(1,n)*100:4.0f}% ${pnl:+.2f}")
PYEOF
```
