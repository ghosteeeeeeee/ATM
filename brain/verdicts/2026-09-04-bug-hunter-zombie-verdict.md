# Bug Hunter Verdict: Stale Signal Zombie Loop Investigation

**Date:** 2026-09-04
**Auditor:** Bug Hunter (DeepSeek Harness)
**Scope:** Second zombie loop — PRESERVE-APPROVED-UPSERT creating infinite signal survival
**Severity:** HIGH (not CRITICAL — staleness decay limits actual damage)

---

## Executive Summary

**CONFIRMED: There IS a second zombie loop mechanism**, but it is **not as severe as claimed**. The PRESERVE-APPROVED-UPSERT mechanism creates a fresh APPROVED row with `CURRENT_TIMESTAMP`, allowing preserved entries to survive indefinitely through repeated compaction cycles. However, staleness decay (5min for non-favorites, 8.3min for favorites) acts as a natural circuit breaker — entries DO eventually drop from the hotset.

**Two dead-code staleness checks are confirmed**, but they are **redundant** with the staleness decay mechanism in signal_compactor.py, NOT the primary defense that was bypassed.

**The real zombie loop risk:** Signals that fire every ~4 minutes (like ema300-dip) can cycle through DB→hotset→preserve→UPSERT→DB indefinitely, accumulating survival_rounds and keeping a perpetual hold on an execution slot. The cleanup_stale_approved(1h) is the ONLY hard stop.

---

## Claim-by-Claim Verification

### Claim 1: PRESERVE-APPROVED-UPSERT creates APPROVED rows with `created_at=CURRENT_TIMESTAMP`

**VERDICT: ✅ CONFIRMED**

**Evidence:**
- `signal_compactor.py:2267-2285`: INSERT statement uses `CURRENT_TIMESTAMP` for both `created_at` and `updated_at`
- This refreshes the signal's apparent age to "just now" every compaction cycle
- The UPDATE path (line 2256-2265) also sets `updated_at=CURRENT_TIMESTAMP`

**Impact:** The preserved signal appears "fresh" to the 10-minute compaction query, allowing it to be picked up again in the next cycle.

### Claim 2: Compactor SQL picks up fresh APPROVED rows

**VERDICT: ✅ CONFIRMED**

**Evidence:**
- `signal_compactor.py:1160-1162`: Main query filters `created_at > datetime('now', '-10 minutes')` AND `decision IN ('PENDING', 'APPROVED')`
- Since PRESERVE-APPROVED-UPSERT writes `created_at=CURRENT_TIMESTAMP`, the row is always within the 10-minute window
- The "Maintain APPROVED signals" section (line 2532-2543) bumps `survival_rounds` and `hot_cycle_count` for APPROVED signals still in top-10

### Claim 3: entry_origin_ts resets when preserved entry drops

**VERDICT: ✅ CONFIRMED**

**Evidence:**
- `signal_compactor.py:1806-1813`: When `prev_entry` exists, `entry_origin_ts` carries forward from previous hotset entry
- `signal_compactor.py:1813`: When `prev_entry` does NOT exist (entry dropped, new signal fires), `entry_origin_ts = time.time()` — fresh start
- `signal_compactor.py:2947-2951` in `_filter_safe_prev_hotset`: Same logic — if `entry_origin_ts` is None, set to current time

**Impact:** When a signal drops (staleness=0) and a new PENDING signal fires, the cycle restarts with a fresh entry_origin_ts. This is the "zombie rebirth" mechanism.

### Claim 4: `created_at` NOT returned by `get_approved_signals()` — staleness check dead code

**VERDICT: ✅ CONFIRMED — DEAD CODE**

**Evidence:**
- `signal_schema.py:2645-2683`: SQL SELECT does NOT include `created_at` — returns: id, token, direction, count, max_conf, min_conf, types, source, price, leverage, hot_rounds, learned_sl_multiplier, signal_metadata
- `signal_schema.py:2686-2720`: Results converted to dict via `dict(r)` — `created_at` is NOT in the dict
- `decider_run.py:2728`: `signal_created_at = sig.get('created_at')` — ALWAYS returns `None`
- `decider_run.py:2729`: `if signal_created_at:` — ALWAYS False → staleness check NEVER executes

**Impact:** The V2 staleness check (SIGNAL_STALENESS_MAX_AGE_MIN = 5 min) is completely disabled. Any signal that makes it to the execution loop passes through this gate unchecked.

### Claim 5: accel-300 staleness check also disabled

**VERDICT: ✅ CONFIRMED — DEAD CODE**

**Evidence:**
- `decider_run.py:3045`: `_entry_origin = sig.get('entry_origin_ts') or 0` — `entry_origin_ts` is NOT in the signal dict from `get_approved_signals()`, so this is always 0
- `decider_run.py:3046`: `if not _entry_origin and sig.get('created_at'):` — `_entry_origin` is 0 (falsy) but `created_at` is None (falsy) → neither branch fires
- `decider_run.py:3054`: `_hotset_age_min = (time.time() - _entry_origin) / 60.0 if _entry_origin else 0` — `_entry_origin` is 0 → `_hotset_age_min` is 0
- `decider_run.py:3055`: `if _hotset_age_min > 10:` — NEVER True → accel staleness check NEVER blocks

**Impact:** accel-300 signals have NO staleness protection at the execution level.

### Claim 6: Indefinite cycle through DB→hotset→preserve→UPSERT→DB

**VERDICT: ⚠️ PARTIALLY CONFIRMED — BOUNDED BY STALENESS DECAY**

**The cycle DOES exist:**
1. Signal fires → PENDING in DB
2. Compactor picks up → APPROVED in DB (line 2485-2494)
3. Enters hotset.json with entry_origin_ts
4. Next cycle: preserved from previous hotset
5. PRESERVE-APPROVED-UPSERT writes new APPROVED row with `created_at=CURRENT_TIMESTAMP`
6. Compactor picks up the fresh APPROVED row → back to step 3

**But staleness decay IS a circuit breaker:**
- Non-favorites: staleness=0 after 5 minutes → entry drops from hotset
- Favorites: staleness=0 after 8.3 minutes → entry drops from hotset
- `_filter_safe_prev_hotset` (line 2892, 2957): `if entry_staleness <= 0.01: continue` — drops dead entries

**The gap:** The cycle CAN sustain if the signal fires every ~4 minutes (within the staleness window). ema300-dip fires every ~1-3 minutes for active tokens, so it CAN maintain the cycle indefinitely. The only hard stop is `cleanup_stale_approved(hours=1)` which runs once at the start of each decider_run cycle.

---

## Additional Findings

### FINDING 1: 4,520 signals with survival_rounds > 0 but hot_cycle_count = 0

**SEVERITY: MEDIUM**

There are 4,520 signals in the DB with `survival_rounds > 0` but `hot_cycle_count = 0`. The most extreme is W:LONG with `survival_rounds=108` and `hot_cycle_count=0`.

**Root Cause:** The compactor approval path (line 2485-2494) sets `survival_rounds` from the hotset entry but the signal is then SKIPPED by decider_run (not executed). The `hot_cycle_count` is only incremented when the signal is in the hotset AND approved — but if the signal is never approved (stays PENDING), `hot_cycle_count` stays 0 while `survival_rounds` accumulates from hotset.json.

**Impact:** `survival_rounds` is used for execution ranking (line 2541: `rounds = sig.get('hot_rounds', 0)`). Inflated `survival_rounds` could cause stale signals to be ranked higher than fresh ones.

### FINDING 2: ema300-dip generates massive signal volume with 0% execution rate

**SEVERITY: LOW**

From Sep 1-4: 843 EXPIRED + 119 SKIPPED = 962 ema300-dip signals, with only 2 ICP LONG trades executed (from purged signals). The 96.2% expiry rate suggests ema300-dip fires too aggressively for the current market conditions.

**Impact:** DB bloat (72,432 total signals), wasted compaction cycles, hotset occupied by signals that never execute.

### FINDING 3: Signal purging removes executed signals but preserves zombie evidence

**SEVERITY: LOW**

Signals that triggered trades (like id=1591598, 1593791) are purged from the DB after execution. This makes it impossible to trace the full lifecycle of executed signals. The `cleanup_stale_approved(1h)` expires non-executed APPROVED signals, but executed signals are purged separately.

---

## Verification of ICP:LONG Lifecycle

**Trade 1 (id=14813):**
- Opened: 2026-09-03 03:23:25
- Closed: 2026-09-03 05:07:55 (0.22% profit)
- Signal: ema300-dip, conf=99%, signal_id=1591598 (PURGED)
- Hotset history: ICP(r18) at iteration time — survived 18 compaction cycles

**Trade 2 (id=14876):**
- Opened: 2026-09-03 21:37:27
- Closed: 2026-09-03 22:32:32
- Signal: ema300-dip, conf=99%, signal_id=1593791 (PURGED)
- Hotset history: appeared in hotset at 21:37 with score=51.56

**Key observation:** Both trades used ema300-dip signals that had accumulated survival_rounds through the preserve cycle. The signals themselves were purged, but the hotset.json carried forward the survival_rounds from previous cycles.

---

## Issues Ranked by Severity

### ISSUE 1: Dead staleness checks in decider_run.py
**SEVERITY: HIGH**
**FILES:** `decider_run.py:2728-2757`, `decider_run.py:3045-3060`
**ROOT CAUSE:** `get_approved_signals()` does not return `created_at` or `entry_origin_ts`, making both staleness checks dead code.
**FIX:** Add `created_at` to the SQL SELECT in `get_approved_signals()` (signal_schema.py:2645). The field exists in the DB schema but is not queried.
**VERIFICATION:** After fix, check logs for `[STALE]` and `[ACCEL-STALE-MAX]` entries.

### ISSUE 2: PRESERVE-APPROVED-UPSERT creates zombie loop
**SEVERITY: HIGH**
**FILES:** `signal_compactor.py:2267-2285`
**ROOT CAUSE:** Preserved entries get APPROVED rows with `created_at=CURRENT_TIMESTAMP`, refreshing their age and allowing indefinite survival through repeated compaction cycles.
**FIX:** Two options:
1. **Conservative:** Add a maximum age check in PRESERVE-APPROVED-UPSERT — if the preserved entry's original `entry_origin_ts` is >30 minutes old, don't write the APPROVED row.
2. **Aggressive:** Remove PRESERVE-APPROVED-UPSERT entirely — rely on the normal PENDING→APPROVED flow. If a preserved entry has no PENDING signal in the DB, it shouldn't be APPROVED.
**VERIFICATION:** After fix, check that preserved entries don't accumulate survival_rounds beyond 5-10.

### ISSUE 3: entry_origin_ts resets on re-entry
**SEVERITY: MEDIUM**
**FILES:** `signal_compactor.py:1813`, `signal_compactor.py:2949-2951`
**ROOT CAUSE:** When a preserved entry drops (staleness=0) and a new PENDING signal fires, `entry_origin_ts` resets to `time.time()`, restarting the staleness clock.
**FIX:** Consider carrying forward the original `entry_origin_ts` from the DB signal's `created_at` rather than resetting. This would make the staleness timer absolute (from first signal creation) rather than relative (from last hotset entry).
**VERIFICATION:** After fix, check that re-entering signals don't get fresh entry_origin_ts.

---

## Uncertainties

- **Assumptions:** The pipeline was running normally during the ICP:LONG trades (Sep 3). The ema300-dip signal frequency (~1-3 min) is typical for this signal source.
- **Edge cases not verified:**
  - Whether the 1-hour `cleanup_stale_approved` actually prevents indefinite zombie loops in practice (it runs once per decider_run cycle, but preserved entries refresh their timestamp each compaction)
  - Whether the `_filter_safe_prev_hotset` staleness check (line 2892, 2957) is actually effective when entries are preserved every cycle
  - Whether the `PRESERVE-APPROVED-UPSERT` UPDATE path (line 2256-2265) also refreshes `created_at` (it doesn't — it only updates `survival_rounds`, `hot_cycle_count`, `updated_at`, `source`, `combo_key`, `signal_metadata`)
- **Potential side effects of fixes:**
  - Removing PRESERVE-APPROVED-UPSERT could cause preserved entries to not execute (the original BUG-014 issue)
  - Adding `created_at` to `get_approved_signals()` could break other callers that don't expect this field
  - Changing entry_origin_ts reset logic could affect staleness timing for legitimate fresh signals

---

## Conclusion

The second zombie loop is real but bounded. The primary risk is **signal slot occupation** — a signal that fires every ~4 minutes can maintain a perpetual hold on a hotset slot, preventing other signals from entering. The dead staleness checks in decider_run.py are a separate issue that should be fixed regardless, as they represent a defense-in-depth failure.

**Recommended priority:**
1. Fix the dead staleness checks (add `created_at` to `get_approved_signals()` SQL) — quick fix, high value
2. Add maximum age guard to PRESERVE-APPROVED-UPSERT — prevents indefinite zombie survival
3. Investigate entry_origin_ts reset logic — lower priority but addresses root cause
