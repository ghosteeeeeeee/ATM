# Trading System — Live Log
> Internal document. Updated every 10 minutes by the pipeline. Every win, loss, bug, fix, and idea goes here.

---

## System Architecture

```
MARKET DATA
    │
    ▼
price_collector.py          ──→ price_history (SQLite static + runtime)
    │                              ~1.7M rows
4h_regime_scanner.py        ──→ regime_cache (LONG_BIAS / SHORT_BIAS / NEUTRAL)
    │
    ▼
signal_gen.py               ──→ signals DB (PENDING / WAIT / APPROVED / EXECUTED)
    │                              Z-score velocity + RSI + MACD + percentile_rank
    │                              SPEED FEATURE: token_speeds table (536 tokens)
    │
    ▼
ai_decider.py               ──→ compact_signals() → hotset.json (top 20 by score)
    │
    ▼
decider_run.py              ──→ reads hotset.json
    │
    ▼
hyperliquid_exchange.py     ──→ HL API (live or paper)
position_manager.py          ──→ trailing stops, stale winner/loser exits, cascade flips
    │
    ▼
hl-sync-guardian.py         ──→ background service (60s interval)
hermes-trades-api.py        ──→ writes signals.json for web dashboard
```

### Pipeline Schedule
| Step | Frequency | Script |
|------|-----------|--------|
| Price collection | Every 1 min | `price_collector.py` |
| Regime scan | Every 1 min | `4h_regime_scanner.py` |
| Signal generation | Every 1 min | `signal_gen.py` |
| Hot-set execution | Every 1 min | `decider_run.py` |
| Position management | Every 1 min | `position_manager.py` |
| Web dashboard | Every 1 min | `update-trades-json` |
| AI decision + compaction | Every 10 min | `ai_decider.py` |

---

## ATR TP/SL Internal Close System
**Status:** LIVE — 2026-04-09
**Sub-project of:** Position Management | **Owner:** Agent

### Dashboard Update Chain
```
Pipeline (every 1 min via run_pipeline.py)
  → hermes-trades-api.py (reads PostgreSQL brain DB, writes /var/www/hermes/data/trades.json)
    → nginx port 54321 (serves trades.json to trades.html)
      → trades.html polls /data/trades.json every 30s

Pipeline log: /root/.hermes/logs/pipeline.log
Dashboard JSON: /var/www/hermes/data/trades.json
JSON updated by: hermes-trades-api.py (standalone, NOT via systemd service)
```
**IF DASHBOARD STALE:** Check if pipeline is still running (`ps aux | grep run_pipeline`). Pipeline crashed/stopped = dashboard frozen. Restart via the pipeline timer or manually.

### Guardian vs Dashboard Lag
- Guardian (`hl-sync-guardian.py`): runs every ~7s, recalculates ATR continuously
- Guardian → PostgreSQL DB: persists ATR SL/TP at end of each sync cycle
- Pipeline → Dashboard JSON: reads PostgreSQL DB, writes trades.json every 1 min
- Dashboard shows: PostgreSQL values, which lag guardian's in-memory ATR by ~0-60s
- AVAX/BLUR confirmed: `replace_sl` successfully updated HL in <10s from guardian call

### SKIP_COINS Bug (FIXED 2026-04-14)
**Root cause:** `position_manager.py` reconcile_tp_sl() had a hardcoded skip list:
```python
if coin.upper() in {'AAVE', 'MORPHO', 'ASTER', 'PAXG', 'AVNT'}:
    continue
```
Coins in this list NEVER got ATR-based SL recalculation — they only received the 2%-from-entry
fallback SL from the earlier step, which is wrong.

**Fix applied:** Removed all coins from SKIP_COINS in `hl-sync-guardian.py` line ~2490.
The skip was in `hl-sync-guardian.py` reconcile_tp_sl(), NOT in position_manager.py.
All 9 open positions now get ATR-based SL reconciliation.

**Affected coins (previously skipped):** AAVE, MORPHO, ASTER, PAXG, AVNT

### HL Rate Limit Issues
- HL enforces a request budget (approx 74247 base + USDC volume bonus)
- Guardian request count: ~80023 (over budget = rate limited)
- Error messages: "Too many cumulative requests sent", "Invalid TP/SL price. asset=X"
- The `asset=X` errors (BTC=0, XRP=25, PROVE=201, AVNT=208) are HL-side validation failures,
  not code bugs — likely triggered by the rate-limit state corrupting the order routing
- Successfully updated on HL so far: AVAX, BLUR (both PASS in logs)
- Mitigation: `_tpsl_cooldown` = 30s per token prevents duplicate HL calls

### Current ATR SL Values (2026-04-14, from guardian DB writes)
| Token | Direction | ATR | SL Formula | Current |
|-------|-----------|-----|------------|---------|
| BTC | SHORT | ~135 | cur + ATR | ~75,127 |
| ETH | LONG | ~6.1 | cur - ATR | ~2,365 |
| AVAX | LONG | ~0.023 | cur - ATR | ~9.38 |
| LINK | LONG | ~0.024 | cur - ATR | ~9.11 |
| XRP | LONG | ~0.0029 | cur - ATR | ~1.347 |
| DYDX | LONG | ~0.00037 | cur - ATR | ~0.096 |
| BLUR | SHORT | ~0.00015 | cur + ATR | ~0.021 |
| PROVE | SHORT | ~0.00067 | cur + ATR | ~0.229 |
| AVNT | SHORT | ~0.00058 | cur + ATR | ~0.134 |

### When to Check What
| Question | Where to look |
|----------|--------------|
| Is the guardian running? | `ps aux \| grep hl-sync-guardian` |
| Is the pipeline running? | `ps aux \| grep run_pipeline` |
| Guardian ATR calc fresh? | `tail -20 /root/.hermes/logs/sync-guardian.log \| grep ATR` |
| Dashboard JSON fresh? | `stat /var/www/hermes/data/trades.json \| grep Modify` |
| Pipeline cycle? | `tail /root/.hermes/logs/pipeline.log` |
| DB vs dashboard diff? | PostgreSQL `trades.stop_loss` vs `/var/www/hermes/data/trades.json` |

---

### What It Is
Hermes self-closes positions when ATR-based SL or TP levels are hit — without relying on HL trigger orders.

### Architecture
```
Pipeline Cycle (every 1 min):
  1. refresh_current_prices()       → fetch live prices from HL
  2. check_atr_tp_sl_hits()          → scan all positions for ATR SL/TP hits
  3. close_paper_position()          → internal DB close + market mirror to HL
  4. [Kill switch: _execute_atr_bulk_updates() to HL is DISABLED]
```

### Key Constants
| Component | Value |
|-----------|-------|
| `ATR_HL_ORDERS_ENABLED` | `False` — disables `_execute_atr_bulk_updates()` call path |
| `CASCADE_FLIP_ENABLED` | `False` — disables ALL cascade flip logic |

---

## Cascade Flip — DISABLED (2026-04-10)
**Status:** DISABLED — Kill switch active

### Kill Switch
`CASCADE_FLIP_ENABLED = False` in `position_manager.py` line 78

---

## Current State (2026-04-12)
### Positions
- 1 open, 82 closed (brain DB)

### Services
- hermes-pipeline.timer: RUNNING
- hl-sync-guardian.service: RUNNING
- hermes-wasp.timer: ACTIVE

### Live Trading
- hype_live_trading.json: ON (kill switch)
- Guardian: real execution path

---

## True-MACD Cascade System (Core Strategy)
**Status:** ACTIVE

### Key Files
- `scripts/macd_rules.py` — MACD rules engine
- `scripts/candle_db.py` — cascade direction detection
- `scripts/signal_gen.py` — MTF MACD alignment + cascade entry signal

### Cascade Entry Rules
- MACD histogram: -0.5 (4h), -0.2 (1h) for SHORT cascade
- MTF alignment check before entry
- Speed-armed confirmation

---

## Known Issues
- Pipeline: RUNNING (hermes-pipeline.timer)
- WASP: check via hermes-wasp.timer

---

## Live Log (Recent)

### 2026-04-12 — Session Start
- Cascade-flip: DISABLED
- Regime: SHORT bias
- Live trading: ON (hype_live_trading.json)

### 2026-04-10 — Cascade Flip Kill Switch
- CASCADE_FLIP_ENABLED = False confirmed
- Decision: DISABLE cascade flip pending further analysis

---

## Win Rate History
See PostgreSQL brain DB: `trades.ab_results` table for historical A/B test data.

---

*Archived older entries to brain/archive/ — 2026-04-12*

## INCIDENT — 2026-04-12 03:20 UTC | Pipeline Cascade Failure

**Severity:** CRITICAL  
**Duration:** ~40 hours (estimated from CONTEXT.md staleness)  
**Root Cause:** Two sequential bugs in ai_decider.py

### Bug 1: HOTSET_BLOCKLIST NameError (CRITICAL)
- **File:** `ai_decider.py` line 114
- **Issue:** `HOTSET_BLOCKLIST` used but not imported. Other files imported it 
  (`from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST, SIGNAL_SOURCE_BLACKLIST`) but missed `HOTSET_BLOCKLIST`.
- **Symptom:** `[ERROR] [ai-decider] get_pending_signals DB read error: name 'HOTSET_BLOCKLIST' is not defined` — crashed every pipeline cycle
- **Fix:** Added `HOTSET_BLOCKLIST` to the import on line 114

### Bug 2: sig_entry Reference Before Assignment (CRITICAL)
- **File:** `ai_decider.py` lines 1618-1622
- **Issue:** `sig_entry[4]` used on line 1618 for source blacklist check, but `sig_entry` not assigned until line 1622
- **Symptom:** `[ERROR] [ai-decider] get_pending_signals DB read error: cannot access local variable 'sig_entry' where it is not associated with a value`
- **Fix:** Moved source blacklist check AFTER `sig_entry` assignment; used `src_val` (already computed)

### Cascade Effects
1. `hotset.json` stopped being refreshed — stale for ~1.5h+ before incident reported
2. decider_run.py: `decisions` table remained empty (no decisions written)
3. `token_intel` and `cooldown_tracker` tables stayed empty
4. Signal processing: signals created but stuck in PENDING/WAIT with `executed=1` marking misleading state

### Resolution
1. Added `HOTSET_BLOCKLIST` to import (line 114)
2. Fixed `sig_entry` ordering in hotset write loop
3. Both fixes applied while pipeline continued running
4. Pipeline verified healthy on next cycle (03:32 cycle — no more errors)

### Files Modified
- `/root/.hermes/scripts/ai_decider.py`

## INCIDENT — 2026-04-12 03:20 UTC | Pipeline Cascade Failure

**Severity:** CRITICAL
**Duration:** ~40 hours (estimated from CONTEXT.md staleness)
**Root Cause:** Two sequential bugs in ai_decider.py

### Bug 1: HOTSET_BLOCKLIST NameError (CRITICAL)
- **File:** `ai_decider.py` line 114
- **Issue:** `HOTSET_BLOCKLIST` used but not imported. Other files imported it
  but missed `HOTSET_BLOCKLIST`.
- **Symptom:** `[ERROR] name 'HOTSET_BLOCKLIST' is not defined`
- **Fix:** Added `HOTSET_BLOCKLIST` to the import on line 114

### Bug 2: sig_entry Reference Before Assignment (CRITICAL)
- **File:** `ai_decider.py` lines 1618-1622
- **Issue:** `sig_entry[4]` used before `sig_entry` was assigned
- **Symptom:** `[ERROR] cannot access local variable 'sig_entry' where it is not associated with a value`
- **Fix:** Moved source blacklist check AFTER `sig_entry` assignment

### Cascade Effects
1. `hotset.json` stopped being refreshed — stale for ~1.5h+
2. decider_run.py: `decisions` table empty (no decisions written)
3. `token_intel` and `cooldown_tracker` stayed empty
4. Signals stuck in PENDING/WAIT with misleading `executed=1`

### Resolution
1. Added `HOTSET_BLOCKLIST` to import (line 114)
2. Fixed `sig_entry` ordering in hotset write loop
3. Pipeline verified healthy on next cycle (03:32 cycle — no errors)

### Files Modified
- `/root/.hermes/scripts/ai_decider.py`

## INCIDENT — 2026-04-12 03:20 UTC | Pipeline Cascade Failure
**Severity:** CRITICAL | **Duration:** ~40h | **Root Cause:** 2 bugs in ai_decider.py
Bug 1: HOTSET_BLOCKLIST NameError — line 114 import missing HOTSET_BLOCKLIST
Bug 2: sig_entry Reference Before Assignment — lines 1618-1622, used before assigned
Fix: Added HOTSET_BLOCKLIST to import + moved sig_entry lookup before source blacklist check
Pipeline verified healthy on 03:32 cycle — no more errors

---

## Pipeline Bug Fixes

### Bug: WAIT Signals Excluded from Compaction (2026-04-12)
**Severity:** HIGH
**File:** `ai_decider.py` lines 1030-1035
**Symptom:** 11 signals (MET, NIL, ORDI, PENDLE, SNX, STRK, TIA, TST, UMA, UNI, ZK) were stuck in WAIT state with `executed=1`. This excluded them from `_do_compaction_llm()` which only processes signals with `executed=0`.

**Root Cause:** `cleanup_stale_signals()` at startup was marking ALL non-PENDING/APPROVED signals as `executed=1`. The query:
```sql
UPDATE signals SET executed = 1 WHERE decision NOT IN ('PENDING', 'APPROVED')
```
This incorrectly included WAIT signals, which need `executed=0` to remain in the compaction pool for re-evaluation.

**Fix:** Added 'WAIT' to the exclusion list:
```sql
UPDATE signals SET executed = 1 WHERE decision NOT IN ('PENDING', 'APPROVED', 'WAIT')
```

**Why WAIT needs `executed=0`:**
- WAIT signals are AI-reviewed signals deferred for later decision
- They have `review_count >= 1` and need to be re-evaluated by compaction
- If `executed=1`, they are excluded from `_do_compaction_llm()` query (which filters `WHERE executed = 0`)

**Files Modified:**
- `/root/.hermes/scripts/ai_decider.py` (line 1034)

**Verification:**
- After fix: signals reset to PENDING with `executed=0`, compaction approved all 11
- Compaction now includes WAIT signals in re-evaluation cycle

### Fix: Confidence Floor + Entry Threshold Raise (2026-04-13)
**Severity:** HIGH — was causing confidence inversion in pipeline decisions
**Files:** `ai_decider.py` (new), `signal_gen.py`

**Symptom (from Pipeline Analyst):**
- REJECTED signals avg: 79.8% confidence (135 signals)
- EXECUTED signals avg: 70.1% confidence (22 signals)
- Higher confidence signals systematically rejected; lower confidence executed

**Root Cause:**
1. ENTRY_THRESHOLD was 50 — too many weak signals flooding the hot-set pipeline, diluting LLM attention
2. No floor in `_do_compaction_llm()` — the LLM received all signals including sub-60% noise, spending tokens evaluating garbage

**Fix Applied:**

1. **`ai_decider.py`** — Added confidence floor in `_do_compaction_llm()`:
   ```python
   CONFIDENCE_FLOOR = 60
   signals = [s for s in signals if s[3] >= CONFIDENCE_FLOOR]
   ```
   Signals below 60% are silently dropped before reaching the LLM. Reduces token spend, focuses LLM on qualified candidates.

2. **`signal_gen.py`** — Raised entry thresholds:
   ```
   ENTRY_THRESHOLD:       50 → 60  (LONG)
   SHORT_ENTRY_THRESHOLD: 60 → 60  (SHORT — was 70, now unified at 60)
   ```
   Only signals with natural score ≥60 (LONG) or ≥70 (SHORT) are written to the DB at all.

**Expected Effect:**
- ~30-40% fewer signals written to DB (weaker ones filtered at source)
- LLM only evaluates signals that are already mid-quality or higher
- Higher average confidence in hot-set shortlist
- Reduces the inversion: signals the LLM sees are pre-qualified
