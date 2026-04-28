---
name: signal-investigation
description: DB-first investigation of Hermes signal pipeline issues — missing signals, stuck orphans, repeated trades
---
# Signal Investigation — DB-First Approach

## Context
When a signal type appears broken, missing, or stuck, the pipeline logs rarely tell the full story. The authoritative source is always the SQLite signal DB.

## Investigation Order

### 1. Is the signal firing at all?
```bash
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT source, decision, COUNT(*) FROM signals WHERE source LIKE '%<signal>%' AND created_at > datetime('now','-4 hours') GROUP BY source, decision ORDER BY COUNT(*) DESC;"
```

### 2. Is the signal reaching the hot-set?
```bash
# Check for HOT/APPROVED/PENDING signals
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, source, decision, survival_score, created_at FROM signals WHERE source LIKE '%<signal>%' AND decision IN ('PENDING','APPROVED','HOT') ORDER BY created_at DESC LIMIT 10;"

# Check rejection reason
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT rejection_reason, COUNT(*) FROM signals WHERE source LIKE '%<signal>%' AND decision='REJECTED' GROUP BY rejection_reason ORDER BY COUNT(*) DESC;"
```

### 3. Why is it being rejected? (Check the compactor log)
```bash
tail -30 /root/.hermes/logs/signal-compactor.log | grep -i "<signal>\|CONFLUENCE\|GATE\|reject"
```
Common rejection reasons:
- `hotset_compactor_not_in_top20` → confidence too low vs other signals
- `hotset_compactor_not_in_top20_after_5_rounds` → survived 5 cycles but never broke top-20
- Single-source gate → source_parts < 2 in compactor (CONFLUENCE-GATE at line 289)

### 4. Check the compactor SOURCE WEIGHTS
Signal sources have multipliers in `signal_compactor.py` line 122:
```bash
grep -A2 "<signal>" /root/.hermes/scripts/signal_compactor.py
```
If a signal source isn't in `SIGNAL_SOURCE_WEIGHTS`, it gets `DEFAULT_SOURCE_WEIGHT = 1.0`.

### 5. Orphan signals (pending but not in hot-set)
```bash
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, source, compact_rounds, created_at FROM signals WHERE decision='PENDING' ORDER BY created_at ASC LIMIT 20;"
```
- `compact_rounds >= 5` → will be rejected on next compaction
- Signals stuck at round 0 → confluence gate blocking them

### 6. Repeating coins (same token traded over and over)
```bash
# Top traded tokens in last 24h
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, direction, COUNT(*) as cnt FROM signals WHERE decision='EXECUTED' AND created_at > datetime('now','-24 hours') GROUP BY token, direction ORDER BY cnt DESC LIMIT 10;"

# Full history of a specific repeating token
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT token, source, direction, created_at, decision FROM signals WHERE token='<TOKEN>' AND decision IN ('EXECUTED','APPROVED') AND created_at > datetime('now','-24 hours') ORDER BY created_at ASC;"
```

## Key Files
- `/root/.hermes/data/signals_hermes_runtime.db` — signal state DB
- `/root/.hermes/scripts/signal_compactor.py` — hot-set compactor (confluence gate at line 289)
- `/root/.hermes/logs/signal-compactor.log` — compactor decisions
- `/root/.hermes/logs/sync-guardian.log` — guardian orphan tracking
- `/var/www/hermes/data/flip_counts.json` — cascade flip eviction state

## Diagnostic Commands Quick Reference

### Check hot-set and signal state for a specific token
```bash
# Token's signals in runtime DB
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT id, token, source, confidence, decision, decision_reason, created_at FROM signals WHERE token='SNX' ORDER BY id DESC LIMIT 20;"

# Run compactor dry+verbose to see scoring for all tokens
cd /root/.hermes/scripts && python3 signal_compactor.py --dry --verbose 2>&1 | grep -E "SNX|Score|PASS|GATE|conf|age_m"

# Check price history for the move
sqlite3 /root/.hermes/data/signals_hermes.db \
  "SELECT price, timestamp FROM price_history WHERE token='SNX' AND timestamp > strftime('%s', 'now') - 14*3600 ORDER BY timestamp ASC;"
```

## Failure Classes

### Class 1: Signal Architecture Mismatch (not a bug)
The signal is correct but wrong for the market condition. Example: SNX pumped +6.6% over 14h but only got 2-3 combo signals through. Root cause:
- `gap-300+` fires when price < 300-SMA (mean-reversion bounce signal) — SNX was below 300-SMA for 10+ hours, so gap-300+ fired every 6 min all day as a single source
- `zscore-momentum+` confirms trend inertia — only arrived once the pump was already underway
- Confluence gate correctly blocked single-source signals
- The combo (gap-300+ + zscore-momentum+) is architecturally wrong for catching pumps: gap-300+ is mean-reversion, not momentum

**Distinguishing from bugs**: `Pre-filter: 0 signals passed` + strong combo signals in DB = timing/architecture, not a bug. Run `--dry --verbose` to confirm signals exist but aren't passing the pre-filter.

### Class 2: Compactor Bug (documented in signal-compactor-survival-bugs)
Pre-filter blocking signals that should pass, wrong source weights, staleness bugs, etc.

### Class 3: Cooldown Blocking (documented in cooldown-tracker-ms)
Loss cooldowns from prior trades blocking new signals.

## Findings from this session
1. `pct-hermes` IS firing (5k+ signals) but ALL standalone pct-hermes signals are rejected by the confluence gate (requires 2+ source components). Only survives as a minority partner in combos.
2. 79 PENDING signals are not stuck in guardian — they exist but are blocked at the compactor stage.
3. EIGEN traded 11 times in 24h because ma-cross-5m-short fires on every 5m candle rejection with no post-trade same-direction re-entry lock.
4. SNX pump (2026-04-26): gap-300+ fires as persistent single-source; zscore-momentum+ arrives late; confluence gate correct; conf=88 combo signals fired at 00:37-01:05 but appear to have missed the compaction window. Not a bug — signal architecture mismatch.
