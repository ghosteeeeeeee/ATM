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
