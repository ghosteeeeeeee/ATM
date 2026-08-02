# Plan: Fix Hot-Set Signals Not Graduating to Trades

## Goal
Hot-set signals (from signal_compactor → hotset.json) must consistently graduate to actual trades (paper + live mirror). Currently broken; zero trades from the new signal pipeline.

---

## Root Causes Found

### BUG 1 — CRITICAL: `hot_cycle_count` never updated by signal_compactor (pipeline deadlock)

**What it is:**
- `signal_compactor.py` (every 5 min) APPROVEs signals and increments `compact_rounds` in the DB.
- It does NOT increment `hot_cycle_count`.
- `hype-sync.py` (the only thing that increments `hot_cycle_count`) is a standalone script with NO systemd timer — it never runs automatically.
- `hype-sync.py` queries `WHERE hot_cycle_count >= 1` before allowing mirror_open.
- 27 of 41 APPROVED signals have `hot_cycle_count=0`, `compact_rounds=1`.
- Result: approved signals are locked out of mirror_open forever.

**Code path:**
- `signal_compactor.py` Step 13: `UPDATE signals SET decision='APPROVED', compact_rounds = compact_rounds + 1` — NO hot_cycle_count
- `hype-sync.py` `get_hot_tokens()`: `WHERE hot_cycle_count >= ?` — reads hot_cycle_count, never updated
- `hl-sync-guardian.py` line 1902: same check `hot_cycle_count >= 1`

**Fix:**
In `signal_compactor.py`, after APPROVEing signals, also increment `hot_cycle_count`:
```python
c.execute(f"""
    UPDATE signals
    SET hot_cycle_count = COALESCE(hot_cycle_count, 0) + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE id IN ({placeholders})
""", approved_ids)
```

This directly synchronizes what `hype-sync.py` was supposed to do (increment hcc for APPROVED signals).

---

### BUG 2 — `signal_compactor.py` confluence enforcement gutted (commented out)

**What it is:**
- The confluence enforcement filter was removed in the 2026-04-17 commit with the comment that it "blocked wrong-row sources."
- The replacement comment says "single-source signals blocked by MAX() aggregation" — but MAX() doesn't block anything, it just picks one source arbitrarily.
- The GROUP BY query uses `GROUP_CONCAT(DISTINCT source)` but never validates that ≥2 distinct sources exist.
- Result: single-source signals can enter the hot-set and graduate to trades.

**Code path:**
- `signal_compactor.py` lines 198-203: confluence pre-filter completely removed.
- Step 1 query uses `GROUP_CONCAT(DISTINCT source)` — merges all sources into one string but has no validation.
- After hot-set ranking (Step 7-8), there's no check that the merged source has ≥2 components.

**Fix:**
After Step 7 (scored/sorted), add confluence enforcement before building hotset_entries:
```python
# Validate merged sources have ≥2 distinct components
if len(set(s['row'][4].split(','))) < 2:  # source is column index 4
    log(f"  🚫 [CONFLUENCE] {token}: single-source — skipping")
    continue
```
Alternatively, add HAVING clause to the Step 1 SQL query to require ≥2 distinct sources.

---

### BUG 3 — Speed cache never written to disk (scoring uses stale/default data)

**What it is:**
- `signal_compactor.py` loads speed data from `SPEED_CACHE_FILE = /root/.hermes/data/speed_cache.json`.
- That file does NOT EXIST — confirmed by `find / -name "speed_cache.json"` returning nothing.
- The fallback to `token_speeds` DB table works (compact_rounds increments), but speed_percentile defaults to 50.0 for all tokens.
- The `speed_tracker.py` writes to `HERMES_DATA = "/root/.hermes/data"`, same path. Why it doesn't exist is unclear — possibly the pipeline step that calls `speed_tracker.update()` writes it but the write path is broken.
- Every compaction cycle logs: `WARN Speed cache not found at /root/.hermes/data/speed_cache.json — using defaults`

**Impact:**
- `speed_mult = 1.0 + (0.10 if speed_percentile >= 80 else 0)` — always 1.0 because speed_percentile defaults to 50.
- Tokens that should get +10% speed bonus never get it.
- Wave phase, momentum_score, is_overextended all default to neutral/50/false.

**Fix:**
1. First: verify `speed_tracker.py` writes to the correct path — check if `SPEED_CACHE` constant matches what `signal_compactor.py` imports.
2. If the write path is broken (path mismatch or permission), fix it.
3. The `signal_compactor.py` fallback to `token_speeds` DB table (lines 227-243) is good — it should backstop. But if `speed_tracker.update()` isn't called by the pipeline, the table is also stale.

---

## Proposed Step-by-Step Fix

### Step 1: Fix hot_cycle_count sync in signal_compactor.py

**File:** `/root/.hermes/scripts/signal_compactor.py`

After line 431 (the APPROVED UPDATE), add:
```python
# Sync hot_cycle_count — was only incremented by hype-sync.py (no timer).
# Now done here so hype-sync/hl-sync-guardian hot-set gates work correctly.
if approved_ids:
    placeholders_hcc = ','.join(['?' for _ in approved_ids])
    c.execute(f"""
        UPDATE signals
        SET hot_cycle_count = COALESCE(hot_cycle_count, 0) + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id IN ({placeholders_hcc})
    """, approved_ids)
    log(f"Synced hot_cycle_count for {len(approved_ids)} approved signals")
```

This makes `signal_compactor.py` the authoritative updater of `hot_cycle_count` (as was always intended).

---

### Step 2: Fix confluence enforcement in signal_compactor.py

**File:** `/root/.hermes/scripts/signal_compactor.py`

After the scored list is built and before deduplication (after line 306), add:
```python
# ── CONFLUENCE ENFORCEMENT: require ≥2 distinct sources ─────────────────────
# Grouped signals with merged_source must actually have ≥2 components.
# Single-source signals don't deserve the hot-set slot.
confluence_ok = []
for s in scored:
    merged_src = s['row'][4] or ''  # column index 4 = merged_source
    src_parts = [p.strip() for p in merged_src.split(',') if p.strip()]
    if len(src_parts) < 2:
        log(f"  🚫 [CONFLUENCE-FILTER] {s['row'][0]}: single-source ('{merged_src}') — skipped")
        continue
    confluence_ok.append(s)

scored = confluence_ok
```

---

### Step 3: Investigate speed_cache.json disappearance

**Files to check:**
- `speed_tracker.py` line 26: `SPEED_CACHE = os.path.join(HERMES_DATA, "speed_cache.json")`
- `signal_compactor.py` line 32: `SPEED_CACHE_FILE = os.path.join(HERMES_DATA, "speed_cache.json")`
- Both write to `/root/.hermes/data/speed_cache.json` — same path, correct.

**Action:** Run `speed_tracker.py` manually and check if the file is created:
```bash
python3 /root/.hermes/scripts/speed_tracker.py
# Then check:
ls -la /root/.hermes/data/speed_cache.json
```

If the file is NOT created after running, the `speed_tracker.update()` write logic is broken (likely the write is attempted but fails silently).

If the file IS created but doesn't persist, something is deleting it.

---

### Step 4: Verify all fixes with dry-run

After making changes:
```bash
python3 /root/.hermes/scripts/signal_compactor.py --dry --verbose
```

Expected output:
- `hot_cycle_count` increments logged
- Single-source signals filtered out
- Speed cache loaded (no WARN about missing file)

---

## Files to Change

| File | Change |
|------|--------|
| `/root/.hermes/scripts/signal_compactor.py` | (1) Add `hot_cycle_count` sync after APPROVED update. (2) Add confluence filter before deduplication. (3) Debug speed_cache if still missing. |

---

## Validation

1. **DB check:** `sqlite3 /root/.hermes/data/signals_hermes_runtime.db "SELECT hot_cycle_count, COUNT(*) FROM signals WHERE decision='APPROVED' GROUP BY hot_cycle_count"` — after fix, APPROVED signals should have `hot_cycle_count >= 1`.

2. **Confluence check:** hotset.json entries should have sources like `hzscore+,vel-hermes-` (2+ comma-separated), not bare `hzscore-`.

3. **Speed cache:** No more `WARN Speed cache not found` in `signal-compactor.log`.

4. **Trade execution:** After 2+ compaction cycles, APPROVED signals with `hot_cycle_count >= 1` should pass the `hype-sync.py` gate and reach `mirror_open`.

---

## Risks & Tradeoffs

- **Risk:** Changing `hot_cycle_count` to increment every 5 min means signals that stay APPROVED for 10 cycles will have `hot_cycle_count=10`. The de-escalation check in `ai_decider.py` (`hot_cycle_count >= 5 → de-escalate`) might fire unexpectedly. Mitigation: de-escalation threshold may need adjustment.

- **Tradeoff:** The 60-min fallback in `hype-sync.py` (`get_recent_signal_tokens`) still helps with pipeline lag. If `hot_cycle_count=0` but `created_at < 60 min ago`, the signal still passes. This is fine as a safety net.

- **Open question:** Why does `speed_cache.json` not exist? May need to trace `speed_tracker.update()` write path. Could be the file write is happening but being overwritten by a pipeline step that writes an empty/partial file.
