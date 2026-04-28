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

1. **pipeline.log** — has execution details NOT in signals DB:
   - ATR value at open (visible as `[ATR] TOKEN: k=1.000 ATR=0.0017 (0.12%)`)
   - Actual SL/TP prices ($0 = bug)
   - Trailing params (activation %, distance %)
   - Close reason (atr_sl_hit, atr_tp_hit, HL_SL_CLOSED, etc.)
   - Speed % at execution
   - **IMPORTANT:** Check for `SL sanity check triggered` warnings — these reset SL/TP incorrectly
   ```
   grep "EXEC:.*TOKEN" /root/.hermes/logs/pipeline.log
   grep "TOKEN" /root/.hermes/logs/pipeline.log | grep "2026-04-25"
   ```

2. **signals_hermes_runtime.db** — signal record (signals that entered the hot-set):
   ```
   sqlite3 /root/.hermes/data/signals_hermes_runtime.db "
   SELECT id, source, confidence, value, price, created_at, decision, signal_types,
          hot_cycle_count, effective_confidence
   FROM signals WHERE token='TOKEN'
   AND created_at >= 'YYYY-MM-DD HH:MM:SS'
   ORDER BY created_at"
   ```
   **Key field:** `decision=EXECUTED` means guardian picked it up. But a signal can be created at T and EXECUTED at T+30min. Always check `created_at` vs pipeline EXEC timestamp to detect execution latency.

3. **trades.json** — actual trade record (check for MULTIPLE trades on same token):
   ```
   python3 -c "
   import json
   with open('/var/www/hermes/data/trades.json') as f:
       data = json.load(f)
   for t in data.get('open', []) + data.get('closed', []):
       if t.get('coin') == 'TOKEN':
           print(json.dumps(t, indent=2))
   "
   ```
   **IMPORTANT:** Always check if the position is already closed before running full analysis. Also check for multiple trades on the same token — there may be a CLOSED trade before the current OPEN one.

4. **ATR** — best read directly from pipeline.log as `[ATR] TOKEN: k=X ATR=Y (Z%)`. Do NOT rely on atr_cache.json (may not exist). The pipeline.log ATR is ground truth.

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
        print(f"[{status}] trade_id? entry={t.get('entry')} exit={t.get('exit')} "
              f"pnl={t.get('pnl_pct')}% close_reason={t.get('close_reason')} "
              f"opened={t.get('opened')} signal={t.get('signal')}")
```

**Common error:** Running full analysis on a CLOSED trade when there's an OPEN trade on the same token. Always confirm the position is still open AND get the correct entry/exit/signal values before proceeding. The pipeline.log may show multiple EXEC lines for the same token at different times.

**Rule:** If the position is already closed, do NOT proceed with live-position analysis. Use the closed trade data only.

### Phase 1: Find the executed signal + check execution quality

First check pipeline.log — it tells you what actually happened at open:
```bash
strings logs/pipeline.log | grep "EXEC:.*TOKEN"
strings logs/pipeline.log | grep "TOKEN" | grep "YYYY-MM-DD"
```

Key things to look for:
- `EXEC:` line — entry price, SL/TP values, confidence, signal sources
- `[WARN] SL sanity check triggered for TOKEN` — SL was reset to a fallback (usually 1%). This means the original SL/TP computation failed or was overridden. Investigate why.
- `ATR=X at open time` — if ATR=0, the HL API failed to return ATR
- `SL=$0.0000 TP=$0.0000` — NOT ALWAYS A BUG. For non-pump trades, decider_run.py intentionally passes sl=0, tp=0 to defer ATR-based SL/TP to position_manager._collect_atr_updates(). The ATR log line following the EXEC line shows the real computed ATR values. However, if the `[ATR]` line shows ATR=0 or the SL sanity check warning, that IS a bug.
- `trail=X%` params — were trailing stops set correctly?
- `spd=X%` — speed % at execution, below 50% means stale signal

### Phase 2: Get signals from DB

```
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "
SELECT id, source, confidence, value, price, created_at, decision, signal_types,
       hot_cycle_count, effective_confidence
FROM signals WHERE token='TOKEN'
AND created_at >= 'YYYY-MM-DD HH:MM:SS'
ORDER BY created_at"
```

**Critical check:** Compare `created_at` (when signal was born) against the pipeline EXEC timestamp (when guardian actually traded). If signal was created 30+ minutes before execution, the market conditions may have changed significantly.

### Phase 3: Verify each signal component

For each source in the signal:
1. Look up the source file (e.g., `gap300_signals.py`, `zscore_momentum.py`)
2. Compute the signal value independently using `signals_hermes.db` price_history
3. Compare against the stored value in signals_hermes_runtime.db
4. Check if threshold was met

### Phase 4: Check pct-hermes for extreme values

pct-hermes value > 70 = overbought, < 30 = oversold. Going LONG when pct-hermes > 70 is aggressive/counter-trend. Going SHORT when pct-hermes < 30 is also aggressive.

```bash
# Get pct-hermes value from signals DB
sqlite3 data/signals_hermes_runtime.db "
SELECT value FROM signals WHERE token='TOKEN' AND source LIKE '%pct-hermes%'
AND created_at >= 'YYYY-MM-DD HH:MM:SS' ORDER BY created_at"
```

### Phase 5: ATR at signal time

ATR is best read directly from pipeline.log. Search for `[ATR] TOKEN:` lines near the EXEC line:
```
grep "\[ATR\].*TOKEN" /root/.hermes/logs/pipeline.log
```
This will show the ATR value, the k multiplier used, and the resulting SL/TP.

**Red flags:**
- `ATR=0` or ATR at 0.00% — HL API failed to return ATR, SL/TP will be $0 (BUG)
- Very low ATR (e.g., XRP at 0.10-0.12%) — tight stops are easily hit by normal market noise. Tokens with ATR < 0.15% of price need wider SL buffers or should be treated as high-risk entries.
- `using stale cache` in pipeline log — ATR data is old, may not reflect current volatility

### Phase 6: Assess

- Was the data fresh at signal time?
- Was the threshold met or barely met?
- Was the confluence appropriate?
- Any red flags (barely-there crossings, stale data)?
- Was ATR available at open? (ATR=0 → SL/TP=$0 BUG)
- Any conflicting signals? (pct-hermes at extreme opposite direction)

## Output Format

```
Token: PEOPLE
Signal: gap-300+,pct-hermes+
Confidence: 89%
Direction: LONG
Entry: $0.007996
Exit: $0.007971
PnL: -0.33% | Duration: 12min | Close: atr_sl_hit

Gap-300+: PASS — gap_pct=0.1016%, widening, direction consistent
pct-hermes+: WARN — value=98.5 (EXTREME overbought), LONG is counter-trend
Confluence: PASS — both agree LONG
Data freshness: PASS — price_history fresh, candles.db 15m=300s old
ATR at open: FAIL — ATR=0, SL/TP=$0 (BUG: fallback not applied)

Verdict: flawed — pct-hermes at 98.5 is overbought, going LONG is aggressive
```

### Phase 7: Check Market Regime / Choppiness

**MANDATORY for any multi-signal confluence trade.**

Before trusting a high-confidence signal, verify the market isn't choppy:

```
# Check ATOM 4h candles for range-bound behavior
sqlite3 /root/.hermes/data/candles.db "
SELECT datetime(timestamp, 'unixepoch'), close FROM candles_4h
WHERE token='ATOM' ORDER BY timestamp DESC LIMIT 12"
```

Choppy market signature: price oscillating within a defined range with no clear direction. In chop, MACD crosses on all timeframes are noise, not signal. The compactor will boost 3 marginal signals to 99% — but that's 3x noise, not signal.

**Quick chop check:** If the 4h candles show no candle with close more than 2% from the previous close (consistently), the market is choppy. In chop: reject MACD signals, be skeptical of z-score at threshold boundary.

### Phase 8: Compute Z-Score Signal Value Directly

When verifying `zscore_momentum` signals and candles.db is stale, use `signals_hermes.db price_history` as ground truth:

```python
import sqlite3, math, statistics
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
cur = conn.cursor()
cur.execute('''
    SELECT price FROM price_history
    WHERE token="TOKEN" AND timestamp <= UNIX_TIMESTAMP_OF_SIGNAL
    ORDER BY timestamp DESC LIMIT 60  -- lookback from signal DB config
''')
closes = list(reversed([r[0] for r in cur.fetchall()]))
mean = statistics.mean(closes)
std_sample = statistics.stdev(closes)  # sample stdev (Python default)
current_price = PRICE_AT_SIGNAL_TIME
z = (current_price - mean) / std_sample
print(f'z={z:.4f}, |z|={abs(z):.4f} > 2.0? {abs(z) > 2.0}')
conn.close()
```

**Critical:** Use `statistic.stdev()` (sample stdev, N-1 denominator) — NOT population stdev. zscore_momentum.py uses sample stdev internally. Population stdev gives a slightly different value and will produce wrong comparisons.

### Phase 9: Verify Each Signal Source Individually

The compactor weighs and combines signals — but 3 marginal signals at 80% confidence each can compound to 99%. High confidence from the compactor does NOT mean high signal quality. Check each signal independently:

**oc-mtf-macd:**
```
sqlite3 /root/.hermes/data/candles.db "
SELECT datetime(timestamp, 'unixepoch'), close FROM candles_1m
WHERE token='TOKEN' ORDER BY timestamp DESC LIMIT 20"
# Also check 5m, 15m, 1h, 4h
# In chop: if all 5 timeframes oscillate within 1-2% with no clear trend = FALSE SIGNAL
```

**oc-zscore-v9:** External OpenClaw signal — cannot verify internally. Check the confidence value:
- `val=2.0` (at threshold) = marginal
- `val=3.0` (at cap) = strong

**zscore_momentum:** Compute from price_history as shown in Phase 8:
- `|z| > 2.5` = strong signal
- `|z| 2.0-2.5` = marginal (one bar of noise can flip it)
- `|z| < 2.0` = no signal (shouldn't be in hot-set)

## Common Issues Found
## Common Issues Found

1. **SL/TP=$0 in EXEC line + ATR=0 in [ATR] line** — HL API failed to return ATR at execution, fallback SL/TP was not applied. This IS a bug.
2. **SL=$0 in EXEC line but [ATR] shows valid ATR** — this is NORMAL for non-pump trades. decider_run intentionally passes sl=0 to defer to position_manager. Check the [ATR] line for the real values.
3. **SL sanity check triggered** — `[WARN] SL sanity check triggered for TOKEN` means SL was reset to a hardcoded 0.5-1% instead of ATR-based. Investigate the original ATR value.
4. **pct-hermes extreme** — pct-hermes >70 (overbought) or <30 (oversold) conflicts with direction
5. **Execution latency > 20 min** — signal fires but trade opens much later (max positions, cooldown, etc.). Check `created_at` vs pipeline EXEC time.
6. **3 consecutive losses on same token** — suggests systemic signal issue, check blocklist
7. **atr_sl_hit with tight trailing** — trailing stop activated, check if trail params are too tight
8. **Very low ATR (< 0.15% of price)** — tokens like XRP with tiny ATR have tight stops easily hit by normal noise. Consider wider SL buffers or flag as high-risk entries. ATR of 0.10% means a 1.5x SL is only 0.15% — one bad candle and you're out.
9. **Multiple trades on same token** — always check trades.json for both open AND closed trades on the same token before analyzing. A position may have closed while you were preparing the analysis.
10. **Merged source ghost attribution** — when signal_schema.py merges a new signal with an existing PENDING signal (same token+direction), it takes the UNION of all historical sources. This means a source tag from a prior signal that is no longer actively firing can be carried forward, making the EXEC line's source list look like multi-signal confluence when only ONE signal actually fired.

    **How to detect:** The signals DB shows `source='gap-300+,zscore-momentum+'` but the individual signals table only has ONE signal_type entry (e.g., `gap-300+`). There is no separate `zscore-momentum+` record near the execution time.

    **Why it matters:** The compactor requires 2+ sources for high-confidence execution. If a below-threshold signal (e.g., zscore=0.92 vs 2.0 threshold) gets merged with a valid signal (gap-300+), the EXEC line will show `[gap-300+,zscore-momentum+]` with 99% confidence — but zscore-momentum+ never actually fired. The 99% came from the merge bonus, not from genuine confluence.

    **Verification:** Query the signals DB for ALL records of this token near the execution time. If `source='A+,B+'` but only signal_type `A` appears in the DB (no `B` record), `B+` is ghost attribution from a prior merge cycle.

    ```sql
    -- Check all signals for the token around execution time
    SELECT id, source, signal_type, confidence, value, price, created_at, decision
    FROM signals WHERE token='TOKEN'
    AND created_at >= 'YYYY-MM-DD HH:MM:SS'
    AND created_at <= 'YYYY-MM-DD HH:MM:SS'
    ORDER BY created_at
    ```
    If the source field contains `X+,Y+` but only `X` appears as signal_type, `Y+` is ghosted.

11. **Stale candles.db despite fresh price_history** — gap-300 and zscore_momentum use `signals_hermes.db price_history` (fresh 1m closes), NOT candles.db. candles.db feeds the HL API and can be hours stale while price_history is fresh. Do NOT use candles.db to verify gap-300 or zscore_momentum data freshness — use `signals_hermes.db price_history` instead.

    **How to detect:** Check `signals_hermes.db` directly:
    ```sql
    sqlite3 /root/.hermes/data/signals_hermes.db \
      "SELECT datetime(max(timestamp),'unixepoch') FROM price_history WHERE token='TOKEN'"
    ```
    Compare against candles.db:
    ```sql
    sqlite3 /root/.hermes/data/candles.db \
      "SELECT datetime(max(ts),'unixepoch') FROM candles_1m WHERE token='TOKEN'"
    ```
    Large gap = candles.db is stale but signals use price_history (not affected).

12. **Ghost EXECUTED signals** — A signal can be marked EXECUTED in the signals DB but never appear in trades.json. This happens when the guardian attempted the order (marking EXECUTED) but HL rejected/failed to fill. Subsequent signals on the same token then find no open position and open a NEW trade. Always check for EXECUTED-but-not-in-trades signals:

    ```sql
    -- Find signals marked EXECUTED but with no corresponding trade
    SELECT id, token, source, signal_type, created_at, decision
    FROM signals WHERE decision='EXECUTED'
    AND created_at >= 'YYYY-MM-DD HH:MM:SS'
    AND created_at <= 'YYYY-MM-DD HH:MM:SS'
    ORDER BY created_at
    ```
    If the EXECUTED signal has no trade in trades.json, the guardian tried but HL didn't fill.
