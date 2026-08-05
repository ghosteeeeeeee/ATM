# 2026-05-08 P0 Incident: Uncommitted Changes Audit

## The Pattern

Uncommitted disk changes (`git status --short` → `M` or `??`) are the PRIMARY source of P0 incidents in Hermes. They are:
- **Invisible** to `git log` and `git diff` (only `git diff HEAD` shows them)
- **Live** — running in production without being in git
- **Unrevertable** via git bisect
- **Dangerous** — orphan creation blocks, DELETE SQL, and race-condition markers hide here

**Every debugging session must start with:**
```bash
cd /root/.hermes && git status --short  # first step always
```

## Files Changed in Last 24h (before fix)

| File | Status | What Changed | Breaking? |
|------|--------|--------------|-----------|
| `scripts/hl-sync-guardian.py` | Modified (uncommitted) | Closing marker system + orphan creation block (lines 351-408, 3638-3678) | YES — P0 |
| `scripts/brain.py` | Modified (uncommitted) | Loss cooldown helpers, 14 signal params, stale orphan check, DB insert exception handler | OK |
| `scripts/decider_run.py` | Modified (uncommitted) | `_is_guardian_closing()` check, signal indicator fields | YES — P0 (closing marker check) |
| `scripts/signal_compactor.py` | Modified (uncommitted) | Confluence gate (2+ types required), regime 5m, opp penalty floor | OK (by design) |
| `scripts/run_pipeline.py` | Modified (uncommitted) | Architecture redesign (signals_runner in background, ai_decider/signal_gen removed) | OK |
| `scripts/archive-trades.py` | Untracked (NOT in git) | JSON archive + PostgreSQL DELETE on `--apply` | YES — P0 if `--apply` run |

## The Breaking Change: Orphan Creation Block

**Location:** `hl-sync-guardian.py` lines ~3638-3678 (uncommitted diff)

**Code path:**
```python
# When no DB record exists for an orphan HL position:
else:
    cur_orphan.execute("""
        INSERT INTO trades (token, direction, ..., trade_id, is_guardian_close, guardian_reason)
        VALUES (..., lev * 1000000, TRUE, 'guardian_orphan')
    """)
    orphan_id = cur_orphan.fetchone()[0]
    close_ok = _close_orphan_paper_trade_by_id(orphan_id, coin, direction, entry_px, lev, 'guardian_orphan')
```

**The bug:** `_close_orphan_paper_trade_by_id()` queries `WHERE id = %s` — it searches by auto-increment `id`, but the INSERT used `trade_id = lev * 1000000`. The query finds nothing → returns False → `_clear_closing_marker()` never called → marker stays forever.

**Stale marker consequence:** `guardian-closing-markers.json` accumulates entries with `trade_id: null`. 48 tokens blocked from trading. decider_run logs "SKIP: {token} — guardian closing in progress (race guard)" for every token.

## The Correct Orphan Guard (Already Existed)

```python
# Line ~1145 — ORPHAN GUARD:
if orphan_row is None:
    continue  # No DB record — skip orphan creation, don't create phantom
```

This `continue` already prevents phantom orphan records. The new block at 3638 is dead code that only triggers if something bypasses the orphan guard — which it can't with the current structure.

**Fix:** Remove the orphan creation block (lines ~3638-3678). The ORPHAN GUARD already handles this correctly.

## Archive-Trades.py: DELETE is Never Auto-Run

`archive-trades.py` was NOT triggered during the incident window. Evidence:
- Archive directory contains May 7 files, not May 8
- PostgreSQL `trades` table has 2 remaining rows (XLM/PURR guardian orphans)
- No systemd timer or cron job for `archive-trades.py`

**But:** the DELETE capability is dangerous and should be removed regardless. Archive to JSON only.

## Git Diff Commands Used

```bash
cd /root/.hermes && git status --short                         # first step
cd /root/.hermes && git diff HEAD -- scripts/hl-sync-guardian.py  # uncommitted changes
cd /root/.hermes && git diff HEAD -- scripts/brain.py
cd /root/.hermes && git diff HEAD -- scripts/decider_run.py
cd /root/.hermes && git diff HEAD -- scripts/signal_compactor.py
cd /root/.hermes && git diff HEAD -- scripts/run_pipeline.py
cd /root/.hermes && git log --oneline -5                        # recent commits
cd /root/.hermes && git show HEAD:scripts/hl-sync-guardian.py | grep orphan  # committed version
```

## Key Facts (2026-05-08 22:00 UTC)

| Item | Value |
|------|-------|
| PostgreSQL trades | 2 rows (PURR id=8780 trade_id=3000000, XLM id=8774 trade_id=5000000) |
| Guardian closing markers | 48 stale entries, all `trade_id: null` |
| Archive directory | May 7 files only (no May 8 run) |
| Hot-set | Empty (confluence gate blocks single-source) |
| HL open positions | None (all closed by guardian) |
| Confluence gate | INTENTIONAL — single-source signals blocked by user instruction |

## Restoration Path

1. `git checkout -- scripts/hl-sync-guardian.py` — revert orphan creation block + closing marker system
2. `git checkout -- scripts/decider_run.py` — revert `_is_guardian_closing()` check
3. `echo '{}' > /root/.hermes/data/guardian-closing-markers.json` — clear stale markers
4. Remove DELETE from `archive-trades.py` (or delete the file entirely if not needed)
5. Keep: `run_pipeline.py` changes (architecture is correct), `signal_compactor.py` confluence gate (by design), `brain.py` changes (loss cooldown is correct)