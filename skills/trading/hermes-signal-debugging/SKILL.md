---
name: hermes-signal-debugging
description: Debug and fix signal direction, hot-set entry filtering, and source weight issues in the Hermes trading system
triggers:
  - "signal direction wrong"
  - "hot-set single signal through"
  - "hzscore pct-hermes"
  - "signal combo not blocked"
  - "vel-hermes opposite signal"
  - "signal merge conflict"
---

# Hermes Signal System Debugging

## Key Files
- `/root/.hermes/scripts/signal_gen.py` — signal generation (pct-hermes, hzscore, etc.)
- `/root/.hermes/scripts/ai_decider.py` — LLM compaction, SOURCE_WEIGHT_OVERRIDES, hot-set writing
- `/root/.hermes/scripts/decider_run.py` — hot-set approval, execution block
- `/var/www/hermes/data/` — host runtime data (trades.json, hotset.json)
- Docker container `hermes-core`: `/app/hermes/data/signals_hermes_runtime.db`

## Signal Source Naming
- `source='hzscore'` — bare hzscore, combo-only, NEVER solo
- `source='hzscore,pct-hermes'` — allowed combo
- `source='hzscore,pct-hermes,vel-hermes'` — triple combo
- `source='hmacd-'` — solo momentum, not allowed

## Critical Debugging Findings

### 1. Hot-set entry filter (decider_run.py ~line 1171)
Single-source signals are blocked at hot-set entry. The filter only applied inside `if sig_type == 'confluence'` block — `hzscore` with `signal_type='mtf_zscore'` bypassed it entirely.

Fix: Added explicit block:
```python
if sig_src == 'hzscore':
    log(f'  🚫 [HOT-SET] {token} {direction} BLOCKED: hzscore (combo-only, no confluence)')
    _record_hotset_failure(token, direction, failures)
    continue
```

### 2. SOURCE_WEIGHT_OVERRIDES ordering (ai_decider.py)
First-match wins. Longer prefixes must come BEFORE shorter ones:
```python
('mtf_zscore', 'hzscore,pct-hermes', 1.0),      # specific FIRST
('mtf_zscore', 'hzscore', 0.15),                # bare LAST (would shadow combos otherwise)
```

### 3. Dead code in ai_decider.py
All `hmacd-*` variants are caught by SOURCE_WEIGHT_OVERRIDES entries (line 133, 141). The inline `if source.startswith('hmacd-')` block in the `else` of `_get_source_weight()` was dead code — removed.

## Signal Merge Architecture (critical for combo debugging)

Three independent signals are generated per token in `signal_gen.py` run(), then merged into ONE DB row:

| Signal | Source | Direction Logic |
|--------|--------|----------------|
| Percentile rank | `pct-hermes` | LOW pct → LONG (suppressed), HIGH → SHORT (elevated) |
| Z-score velocity | `vel-hermes` | velocity > 0 → SHORT (z rising), velocity < 0 → LONG |
| MTF Z-score | `hzscore` | majority TFs below mean → LONG, majority above → SHORT |

**Merge in `signal_schema.py` `add_signal()` (lines 407-488):**
1. CONFLICT GUARD: Expires OPPOSITE-direction signals for same token (line 407)
2. MERGE: If same token+direction exists in last 30 min, merges sources (line 424)
3. `source` field = comma-joined: `hzscore,pct-hermes,vel-hermes`
4. `signal_types` = all contributing types
5. Confidence = MAX + merge bonuses (lines 454-472)

**Why combos flip direction:** `vel-hermes` fires on momentum reversal (z-score changing direction). `hzscore+pct-hermes` fire on mean-reversion. These can directly contradict. When vel-hermes fires SHORT while hzscore+pct are LONG, the CONFLICT GUARD sees them as different token+direction pairs — no guard fires, and the new SHORT row survives.

**`compute_score()` in `signal_gen.py` (line 863):** Computes ONE score per token+direction from CURRENT market data, not from individual source directions. The `vel_score` contribution (0-10 pts, line 1025) can override pct/hermes direction.

**Key locations:**
- `signal_gen.py` lines 1680-1760 — individual signal generation
- `signal_schema.py` lines 407-488 — CONFLICT GUARD + MERGE logic
- `signal_gen.py` lines 863-1080 — compute_score() merging all signals into one score

## pct-hermes Direction Semantics
- `pct_long` = % of lookback prices ≤ current price (high = price at TOP of range)
- `pct_short` = % of lookback prices ≥ current price (high = price at BOTTOM of range)
- `pct_long >= 72` → SHORT (price elevated, mean-reversion down)
- `pct_short >= 72` → LONG (price suppressed, mean-reversion up)

## Docker vs Host
- Docker `hermes-core`: signals in `/app/hermes/data/signals_hermes_runtime.db` — access via `docker exec hermes-core`
- Host: `/var/www/hermes/data/` — access directly
- To clear Docker signals: `docker exec hermes-core sqlite3 /app/hermes/data/signals_hermes_runtime.db "UPDATE signals SET decision='PURGED', executed=1 WHERE decision IN ('PENDING','WAIT','APPROVED');"`

## Hot-set and Trades Clear Checklist
```bash
# Host DB - signals
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "UPDATE signals SET decision='PURGED', executed=1 WHERE decision IN ('PENDING','WAIT','APPROVED');"

# Docker DB - signals  
docker exec hermes-core sqlite3 /app/hermes/data/signals_hermes_runtime.db "UPDATE signals SET decision='PURGED', executed=1 WHERE decision IN ('PENDING','WAIT','APPROVED');"

# Host trades.json - closed trades
python3 -c "import json; d=json.load(open('/var/www/hermes/data/trades.json')); d['closed']=[]; json.dump(d,open('/var/www/hermes/data/trades.json','w'),indent=2)"

# Docker trades - find via docker exec ls /app/hermes/data/
```

## RSI Signal Blind Spots (Critical — 2026-04-14)

### RSI Individual Has No Z-Score Filter
**Location:** `signal_gen.py` lines 1645-1673

RSI fires LONG when RSI < 42, SHORT when RSI > 60 — **completely independently of z-score**. This is the single biggest source of wrong-direction trades.

**SQLite evidence:** `rsi_individual SHORT` fires 335 times at avg 89.0% confidence — but trades with `hzscore,rsi-hermes` SHORT: 6 trades, **0% win rate**, avg -0.206%.

**PostgreSQL evidence:** Adding RSI to any combo makes it worse:
- `hzscore,pct-hermes,vel-hermes` SHORT: 132 trades, 58% WR, avg +0.068% ← BEST
- `hzscore,pct-hermes,rsi-hermes` SHORT: 42 trades, 47% WR, avg -0.126%

**Fix:** Either (a) remove `rsi_individual` from signal_gen entirely, or (b) add z-score check: only fire RSI LONG if z_score < 0, SHORT if z_score > 0.

### RSI Confluence SHORT Has No Z-Score Filter
**Location:** `signal_gen.py` lines 1343-1356

Comment literally says "No z-score filter for SHORTs — elevated prices are valid short targets." In a BTC pump, EVERYTHING looks elevated. No z-score confirmation = wrong direction.

**Fix:** Add `token_z = get_recent_z_score(token); if token_z < 0.3: continue` before firing RSI SHORT.

### Merge Bonus Inflation
**Location:** `decider_run.py` merge bonus section

A 2-source merge adds +20%, 3-source adds +30% to "effective confidence." A weak pct_rank(60) + velocity(65) 2-source merge gets: (60+65)/2 + 20% = 82.5% — but pct_rank maxes at 62.5%, so this inflates 62.5% to 95%+.

**Fix:** Cap effective confidence at 85%, or exclude RSI from merge bonuses (RSI has negative predictive value).

### All Entry Features Are NULL
**Location:** `hl-sync-guardian.py` — trade open

`entry_rsi_14`, `entry_macd_hist`, `entry_bb_position`, `entry_regime_4h`, `entry_trend` are **never recorded**. All 773 closed + 8 open trades have NULL for all entry features. Post-hoc analysis of "what conditions produced this losing trade?" is impossible.

**Fix:** Record current indicator values at trade open in `hl-sync-guardian.py`.

## Multi-DB Signal→Trade Correlation (2026-04-14)

When a signal generates a trade, it goes through two databases:

**SQLite `signals_hermes_runtime.db`** — individual signals at generation time:
```sql
-- What individual signals existed for a token?
SELECT signal_type, direction, confidence, z_score, rsi_14, macd_hist, decision, created_at
FROM signals WHERE token='LINK' ORDER BY created_at DESC LIMIT 20;
```

**PostgreSQL `brain.trades`** — merged signal at trade time:
```sql
-- What merged signal led to a trade?
SELECT token, direction, signal, pnl_pct, close_reason, entry_timing
FROM trades WHERE server='Hermes' AND status='closed' AND token='LINK';
```

**The join key:** `signal` column in PostgreSQL = `source` column in SQLite (e.g., `hzscore,pct-hermes,vel-hermes`).

**Key query — signal quality by type:**
```sql
-- SQLite: individual signal counts
SELECT signal_type, direction, COUNT(*), AVG(confidence)
FROM signals GROUP BY signal_type, direction ORDER BY COUNT(*) DESC;

-- PostgreSQL: merged signal trade outcomes
SELECT signal, direction, COUNT(*), AVG(pnl_pct), SUM(pnl_pct)
FROM trades WHERE server='Hermes' AND status='closed' AND signal IS NOT NULL
GROUP BY signal, direction HAVING COUNT(*) >= 3 ORDER BY SUM(pnl_pct);
```

## Scenario: Signals in DB but Missing from signals.json

**Symptom:** Runtime DB has PENDING signals but `signals.json` is empty or stale.

**Root cause:** `decider_run` timed out (~5 min limit), blocking `hermes-trades-api` from running in the same pipeline cycle.

**Diagnosis:**
```bash
# Check runtime DB for signals
sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT COUNT(*), decision, created_at FROM signals GROUP BY decision ORDER BY created_at DESC LIMIT 5;"

# Check signals.json
cat /var/www/hermes/data/signals.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'pending={len(d[\"pending\"])} approved={len(d[\"approved\"])} executed={len(d[\"executed\"])}')"

# Check last hermes-trades-api run
grep "hermes-trades-api" /root/.hermes/logs/pipeline.log | tail -3

# Check for decider_run timeouts blocking pipeline
grep "ERROR decider_run" /root/.hermes/logs/pipeline.log | tail -3
```

**Fast fix — manually run the sync:**
```bash
python3 /root/.hermes/scripts/hermes-trades-api.py
```

**Long-term fix:** Reduce `decider_run` timeout or optimize its slow queries so it doesn't block `hermes-trades-api`.

## Fix Patterns for Signal Combo Direction Conflicts

**When `hzscore,pct-hermes` works but `hzscore,pct-hermes,vel-hermes` flips direction:**

**Fix 1 (recommended): Raise velocity threshold** — require stronger momentum for vel-hermes to fire
```python
# signal_gen.py line 1710 — raise from 0.03 to 0.05
if abs(velocity) >= 0.05:  # was 0.03
```

**Fix 2: Penalize 3-way combo weight** — quick workaround
```python
# ai_decider.py SOURCE_WEIGHT_OVERRIDES
('mtf_zscore', 'hzscore,pct-hermes,vel-hermes', 0.7),  # was 0.85
```

**Fix 3: Add direction-consistency check during merge** — most correct fix
In `signal_schema.py` `add_signal()`, before merging, check if the incoming signal's direction contradicts the existing row. If conflicting sources like `hzscore+pct` (mean-reversion) vs `vel` (momentum) disagree, keep the higher-weight signal and discard the conflicting one.

## Files to Check for Signal State
- `/var/www/hermes/data/trades.json` — open/closed trades
- `/var/www/hermes/data/hotset.json` — current hot-set
- `/var/www/hermes/data/signal-cooldowns.json` — cooldowns
- `/var/www/hermes/data/signals_hermes_runtime.db` — runtime signal DB (sqlite3)
- `/var/www/hermes/logs/pipeline.log` — pipeline step timing and errors
- Docker: `docker exec hermes-core sqlite3 /app/hermes/data/signals_hermes_runtime.db "SELECT COUNT(*), decision FROM signals GROUP BY decision;"`
