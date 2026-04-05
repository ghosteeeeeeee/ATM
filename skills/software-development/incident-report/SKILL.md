---
name: incident-report
description: Run a structured incident post-mortem using the Incident Response Commander methodology. Use when a production incident, bug, or operational failure occurs in the Hermes trading system. Produces severity classification, full timeline, 5 Whys, root cause analysis, action items, and lessons learned.
color: "#e63946"
emoji: "🚨"
---

# Incident Report Skill

## When to Use
- A production incident occurs (bug, crash, data loss, phantom positions, sync failures)
- After resolving any trading system anomaly that required manual intervention
- During the weekly/monthly reliability review
- Any time a new failure mode is discovered in the system

## What This Produces

### 1. Severity Classification (SEV1–SEV4)
```
SEV1: Full outage, data loss risk, security breach — <5 min response
SEV2: Financial discrepancy, degraded service, key feature down — <15 min
SEV3: Minor feature broken, workaround available — <1 hour
SEV4: Cosmetic issue — next business day
```

### 2. Post-Mortem Document
- Executive summary (2-3 sentences)
- Impact assessment (financial, data integrity, decision quality)
- Full timeline with UTC timestamps
- Root cause analysis with 5 Whys
- What went well / what went poorly
- Action items with owners, priority, due dates
- Lessons learned
- Detection and prevention controls (current vs. needed)

## How to Run

### Step 1: Gather Raw Incident Data
Before calling this skill, collect as much of the following as available:
```
- Exact timestamps (UTC) of: discovery, first symptom, root cause trigger
- Financial impact: PnL, fees, position sizes
- Systems affected: which DBs, exchanges, tokens
- What was observed vs. what was expected
- What actions were taken to resolve
- Any pre-existing issues that contributed
```

### Step 2: Run the Skill
```
Use skill: incident-report
Provide: all gathered incident data as context
```

### Step 3: Review and File
- Review the generated post-mortem
- File to `/root/.hermes/reports/`
- Create follow-up issues or cron jobs for action items

## Quick-Start Template (if skill unavailable)

If the skill system is down, use this markdown template directly:

```markdown
# POST-MORTEM: [Incident Title]

**Incident ID:** INC-[YEAR]-[###]
**Date:** YYYY-MM-DD
**Severity:** SEV[1-4]
**Status:** [Open/Resolved]
**Author:** [Name]

## Executive Summary
[2-3 sentences: what happened, impact, resolution]

## Timeline (UTC)
| Time | Event |
|------|-------|
| HH:MM | [First symptom detected] |
| HH:MM | [Root cause identified] |
| HH:MM | [Mitigation applied] |
| HH:MM | [Resolved] |

## Impact
- Financial: [$X lost / $0]
- Data Integrity: [description]
- Decision Quality: [description]
- Duration: [X hours]

## 5 Whys
1. Why did [symptom]? → [answer]
2. Why did [answer 1]? → [answer]
3. Why did [answer 2]? → [answer]
4. Why did [answer 3]? → [answer]
5. Why did [answer 4]? → [root systemic issue]

## Root Cause
[Technical explanation of failure chain]

## Action Items
| ID | Action | Owner | Priority | Due | Status |
|----|--------|-------|----------|-----|--------|
| 1  | ...    | TBD   | P1       | ... | Open   |

## Lessons Learned
1. [Key takeaway]
2. [Key takeaway]
```

## Incident Patterns in Hermes

### Known Failure Modes
1. **Phantom positions**: brain↔HL divergence with no reconcile mechanism
2. **Stale timer reset**: micro-oscillations resetting staleness without directional progress
3. **Corrupted stop_loss**: physically impossible values entered without validation
4. **Compaction counter bugs**: silent failures in survival scoring due to wrong field names
5. **Token blocklist gaps**: signals generated for tokens that should be blocked

### Detection Patterns
- `get_open_positions()` returns fewer positions than HL shows → phantom
- Position pnl doesn't match HL unrealized pnl → stale data
- `compact_rounds` counter always 0 for a token that should be compacting → field name bug
- `last_move_at` keeps resetting without price progress → stale timer design issue

## Output Location
All incident reports go to: `/root/.hermes/reports/`
Naming convention: `INC-[YEAR]-[###]-[short-title].md`
