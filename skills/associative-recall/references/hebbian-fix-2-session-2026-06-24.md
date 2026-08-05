# Hebbian Fix 2 — Session Transcript (2026-06-24)

## What got shipped this session

**Fix 2** — `hebbian_seed_sessions.py` and `hebbian_session_learner.py`:

- Deleted `seed_decisions_log()` (55 lines) from `hebbian_seed_sessions.py`
- Deleted `learn_from_decisions_log()` (44 lines) from `hebbian_session_learner.py`
- Both call sites removed from `main()`
- Module docstrings updated to document the Fix 2 removal
- Both files backed up to `.bak-2026-06-24`

The functions were creating the most polluted edges in the graph:
- `SKIPPED <-> NEUTRAL`: 1066 fires
- `HOT_APPROVED <-> LONG_BIAS`: 2434 fires
- `LONG_BIAS <-> GALA`: 239 fires
- `LONG_BIAS <-> ZEC`: 413 fires

The pollution source is gone. The DB still contains the residue from before Fix 2 — Fix 3 (wipe + reseed) clears it.

## Two-pass deletion (the lesson)

First attempt at Fix 2 left a stub:
```python
def learn_from_decisions_log(engine, days_back):
    # Fix 2: deleted. See docstring at top of file.
    return 0
```

This was a footgun:
- `hasattr(module, 'learn_from_decisions_log')` still returns True
- `dir(module)` still lists it
- A future patch that adds a call site would silently re-introduce the function

The second pass removed the function entirely (signature + body + docstring). The third pass added a comment-block marker so future readers understand there was something here. The final verification: `grep -rn "seed_decisions_log\|learn_from_decisions_log" /root/.hermes/scripts/*.py | grep -v .bak` returns NOTHING.

**Rule**: when removing a polluting or dangerous function, delete it completely. A stub is worse than no removal because it lies about being safe.

## Latent bug not fixed (moot)

The v3 plan called out a latent bug in `hebbian_session_learner.py` lines 99-100:
```python
direction = d.get("decision")  # actually reads "decision" field
decision = d.get("decision")   # reads same field — bug
```

Both vars got the same value. The fix would have been:
```python
direction = d.get("direction", "")
decision = d.get("decision", "")
```

Since Fix 2 deletes the entire `learn_from_decisions_log()` function, this bug becomes moot. No fix needed.

## Verification recipe (after any deletion of polluting functions)

```bash
# 1. Function is gone from imports
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
import hebbian_session_learner as m
print(f'learn_from_decisions_log exists: {hasattr(m, \"learn_from_decisions_log\")}')
# Expected: False
"

# 2. No call sites or definitions anywhere
grep -rn "seed_decisions_log\|learn_from_decisions_log" /root/.hermes/scripts/*.py 2>/dev/null | grep -v .bak
# Expected: empty (no output)

# 3. No stale docstring references
grep -n "decisions.jsonl\|decisions log" /root/.hermes/scripts/hebbian_seed_sessions.py /root/.hermes/scripts/hebbian_session_learner.py
# Expected: only matches in the Fix 2 docstring that documents the deletion (intentional)

# 4. Scripts still run (don't break the live pipeline)
timeout 10 python3 /root/.hermes/scripts/hebbian_session_learner.py --dry-run 2>&1 | head -10
# Expected: processes 0 sessions, 0 events, no crashes
```

## Open follow-ups (NOT done in this session)

- Fix 4: add `session_summaries` table to `hebbian_engine.py` (additive, low risk)
- Fix 3: backup DB → spot-check HL_COINS >= 100 → `clear_all` → reseed both seeders (DESTRUCTIVE — only after 1, 1b, 2, 4)
- Fix 5: write `hebbian_session_distill.py` (with schema transform + secret stripping)
- Fix 6: update SOUL.md to point to skill (not duplicate trigger table)
- Fix 7: enable systemd timers + new `hermes-brain-seeder.timer`

Full plan: `/root/.hermes/brain/plans/hebbian-integration-plan-2026-06-24-v3.md` (990 lines)