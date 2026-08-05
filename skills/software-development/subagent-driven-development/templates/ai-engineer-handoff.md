---
name: ai-engineer-handoff
description: Create a structured handoff document for delegating complex investigations to the ai-engineer subagent
triggers:
  - "delegate to ai-engineer"
  - "handoff to subagent"
  - "subagent investigation"
---

# AI Engineer Handoff — Skill Template

## When to Use
When you need to delegate a complex investigation or implementation task to the `ai-engineer` subagent, and the task has substantial context that needs to be pre-bundled into a handoff document.

## How to Use
1. Create a handoff markdown document at `/tmp/ai-enginer-handoff.md` (note: deliberate typo in filename to avoid conflicts)
2. Fill in the template sections below
3. Launch the subagent via terminal, passing the handoff content as context
4. The subagent reads the doc and has everything it needs to proceed without asking you

## Handoff Template

```markdown
# [Mission Title] — AI Engineer Handoff

## Mission
[1-2 sentence clear goal]

## Known Context
- [Key facts about the system, files, state]
- [Credentials/endpoints if needed]
- [What was already tried]

## Key Files to Inspect
- [File paths with line/function hints]

## Known Symptoms
1. [Symptom 1]
2. [Symptom 2]

## Constraints
- [What NOT to break]
- [What's sensitive/irreversible]
- [Live trading state if relevant]

## Investigation Steps (optional — subagent can also chart its own course)
1. [First thing to check]
2. [Then...]
```

## Example Usage

```bash
cat << 'EOF' > /tmp/ai-enginer-handoff.md
# DB/HL Sync Investigation — AI Engineer Handoff

## Mission
Investigate why the Hermes DB and Hyperliquid (HL) are out of sync.

## Key Context
- Live trading: ON
- HL wallet: 0x324a9713603863FE3A678E83d7a81E20186126E7
- PostgreSQL: host='/var/run/postgresql' database='brain'
- Signals SQLite: /root/.hermes/data/signals_hermes_runtime.db

## Known Symptoms
1. Guardian phantom trades (paper=TRUE, no real HL position)
2. trades.json stale vs DB
3. HL rate-limiting (429) blocking market_close

## Constraints
- Don't fire real trades during investigation
- Guardian is the execution path — be careful

## Things to Check
1. PostgreSQL trades table for orphans
2. guardian-pending-retry.json for stuck tokens
3. Guardian heartbeat (PID alive?)
4. HL open positions vs DB open trades
EOF
```

## Key Principles
- **Be specific about file paths and line numbers** — don't make the subagent search
- **Include what's already been tried** — avoids redundant work
- **State constraints explicitly** — especially around live trading
- **Bundle all context in one doc** — subagent has no memory of your conversation

## Pitfalls
- Forgetting to include the actual mission question — subagent will investigate the wrong thing
- Not specifying constraints — subagent may take irreversible actions
- Omitting credential info — subagent can't authenticate to services it doesn't know about
