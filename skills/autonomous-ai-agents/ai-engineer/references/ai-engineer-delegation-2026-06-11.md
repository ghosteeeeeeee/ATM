# ai-engineer Subagent — 2026-06-11 Session Findings

## Task: Audit hl-sync-guardian.py patches (4 patches, 4267 lines)

**Result:** Completed in 96s, 14 API calls. No timeout. Correctly identified all bugs.

## What Was Delegated

Three patches to audit + three prior-session fixes to verify + known issue (continue at line 1199):
- Patch 1: `_poll_open_fill_once()` (lines 876-891) — dead code, never called
- Patch 2: `reconcile_hype_to_paper` entry price sync (lines 1073-1115)
- Patch 3: `sync_pnl_from_hype` float coercion (lines 1517-1526)
- Known issue: `continue` at line 1199 blocks orphan creation

## What Subagent Found (All Correct)

1. `_poll_open_fill_once` is defined but never called — dead code
2. `continue` at line 1199 makes orphan creation unreachable
3. Orphan creation path never creates a paper trade (but Paths A+B do handle some orphans)
4. `dup_row` path uses stale `entry_px` for `hl_entry_price` — not written in UPDATE

All findings verified in main session before implementing fixes.

## What Was NOT in the Subagent's Report (Correctly)

Subagent did NOT claim the following were bugs (correctly identified them as non-issues):
- `sync_pnl_from_hype` float coercion (Patch 3) — verified correct
- Path B ON CONFLICT fix — verified correct
- Stale-refresh direction mismatch fix — verified correct

## Why This Delegation Succeeded (vs Prior Sessions)

**Good delegation hygiene:**
- Gave subagent exact line numbers for patched sections
- Gave subagent the exact code to read (not just "audit the file")
- Provided prior-session fixes to verify (not just "find all bugs")
- Provided specific trade timeline (AAVE @ 15:40/17:01, AVNT opens/closes)
- Provided DB schema so subagent knew what columns exist
- Task was scoped: "audit hl-sync-guardian.py patches" not "audit entire trading system"

**Prior sessions failed because:**
- Task was too broad ("audit entire trading system" = 20+ files)
- Subagent was given file paths without line ranges
- No verification checklist was provided

## Key Verification Steps Done in Main Session

```bash
# 1. Confirmed dead code — grep returns 1 match (definition only)
grep -n "_poll_open_fill_once" /root/.hermes/scripts/hl-sync-guardian.py

# 2. Confirmed continue blocks orphan creation — read specific lines
sed -n '1195,1210p' /root/.hermes/scripts/hl-sync-guardian.py

# 3. Syntax check
python3 -m py_compile /root/.hermes/scripts/hl-sync-guardian.py

# 4. Read patched sections before applying more patches
sed -n '876,891p' /root/.hermes/scripts/hl-sync-guardian.py
sed -n '1073,1115p' /root/.hermes/scripts/hl-sync-guardian.py
```

## Rule for Future Delegations

When delegating patch audits to ai-engineer:
1. Give exact file + line ranges for each patched section
2. List prior-session fixes to verify (not just "find all bugs")
3. Give specific trade timeline if the audit involves trade mirroring
4. Give DB schema if the audit involves DB writes
5. Task scope: 1 file + specific sections = 96s; entire system = timeout

The subagent is effective when the task is precise. It fails when the task is open-ended.