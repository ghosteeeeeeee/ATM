---
name: trade-analysis
description: Post-trade signal analysis — verify signals were valid before position closes
triggers:
  - trade fires (EXECUTED signal in DB)
  - position closes
  - new signal combination in hot-set
---

# Trade Analysis Skill

Run after a trade fires to verify signal correctness before/during the position. Goal: identify if signals were mathematically valid and data was fresh.

## Critical Sources (in order of importance)

**IMPORTANT — DB paths:** Always use `/root/.hermes/data/` for local DBs and `/var/www/hermes/data/` for live trading state. The runtime signals DB is at `/root/.hermes/data/signals_hermes_runtime.db`. The atr_cache.json may not exist — ATR is visible directly in pipeline.log.

1. **pipeline.log** — has execution details NOT in signals DB
2. **signals_hermes_runtime.db** — signal record
3. **trades.json** — actual trade record (check for MULTIPLE trades on same token)
4. **ATR** — best read from pipeline.log as `[ATR] TOKEN: k=X ATR=Y`

## Steps

### Phase 0: Identify Which Position You're Analyzing (MANDATORY FIRST STEP)

**Before touching any logs or signal DBs, always do this:**

```python
import json
with open('/var/www/hermes/data/trades.json') as f:
    data = json.load(f)
for t in data.get('open', []) + data.get('closed', []):
    if t.get('coin') == 'TOKEN':
        status = 'OPEN' if t.get('status') == 'open' else 'CLOSED'
        print(f"[{status}] entry={t.get('entry')} exit={t.get('exit')} "
              f"pnl={t.get('pnl_pct')}% close_reason={t.get('close_reason')}")
```

**Rule:** If the position is already closed, do NOT proceed with live-position analysis. Use the closed trade data only.

### Phase 1: Find the executed signal + check execution quality

```bash
strings logs/pipeline.log | grep "EXEC:.*TOKEN"
strings logs/pipeline.log | grep "TOKEN" | grep "YYYY-MM-DD"
```

Key things to look for:
- `EXEC:` line — entry price, SL/TP values, confidence, signal sources
- `[WARN] SL sanity check triggered for TOKEN` — SL was reset to a fallback
- `ATR=0` or ATR at 0.00% — HL API failed to return ATR, SL/TP will be $0 (BUG)
- `trail=X%` params — were trailing stops set correctly?
- `spd=X%` — speed % at execution, below 50% means stale signal

### Phase 2: Get signals from DB

```
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "
SELECT id, source, confidence, value, price, created_at, decision, signal_types
FROM signals WHERE token='TOKEN'
AND created_at >= 'YYYY-MM-DD HH:MM:SS'
ORDER BY created_at"
```

**Critical check:** Compare `created_at` (when signal was born) against the pipeline EXEC timestamp (when guardian actually traded). If signal was created 30+ minutes before execution, the market conditions may have changed significantly.

### Phase 3: Verify each signal component

For each source in the signal:
1. Look up the source file (e.g., `gap300_signals.py`, `zscore_momentum.py`)
2. Compute the signal value independently using `signals_hermes.db price_history`
3. Compare against the stored value in signals_hermes_runtime.db
4. Check if threshold was met

### Phase 4: Check pct-hermes for extreme values

pct-hermes value > 70 = overbought, < 30 = oversold. Going LONG when pct-hermes > 70 is aggressive/counter-trend.

## Common Issues Found

1. **SL/TP=$0 in EXEC line + ATR=0** — HL API failed to return ATR at execution, fallback SL/TP was not applied. This IS a bug.
2. **SL=$0 in EXEC line but [ATR] shows valid ATR** — this is NORMAL for non-pump trades. decider_run intentionally passes sl=0 to defer to position_manager. Check the [ATR] line for the real values.
3. **SL sanity check triggered** — SL was reset to a hardcoded 0.5-1% instead of ATR-based.
4. **pct-hermes extreme** — pct-hermes >70 (overbought) or <30 (oversold) conflicts with direction.
5. **Execution latency > 20 min** — signal fires but trade opens much later.
6. **Very low ATR (< 0.15% of price)** — tokens like XRP with tiny ATR have tight stops easily hit by normal noise.
7. **Multiple trades on same token** — always check trades.json for both open AND closed trades before analyzing.
8. **Merged source ghost attribution** — when signal_schema.py merges a new signal with an existing PENDING signal, it takes the UNION of all historical sources. A source tag from a prior signal that is no longer actively firing can be carried forward.
9. **Stale candles.db despite fresh price_history** — gap-300 and zscore_momentum use `signals_hermes.db price_history` (fresh 1m closes), NOT candles.db.
10. **Ghost EXECUTED signals** — signal marked EXECUTED but never appears in trades.json = guardian attempted but HL didn't fill.
