# SKILL.md Trim Log

## 2026-06-08
- SKILL.md hit100,014 chars (limit: 100,000). Routine trigger trim deferred.
- New trigger added via support file: `rs-blacklist-staleness-guard-verification-jun-2026.md`
- Trigger: "are RS signals using blacklists for stale tokens"

## Prior Trim Candidates (suggested oldest/most-stale triggers to remove when making room)
- Any trigger referencing a specific date in 2026-04 or 2026-05 that has a corresponding reference file with root-cause documented — those are already handled by the reference file and the trigger is redundant.
- Triggers that are just bug ID numbers (e.g. "SAND blocks both directions") can be replaced with the semantic trigger that already exists.
