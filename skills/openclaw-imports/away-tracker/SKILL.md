# Away Tracker Skill

Track time since last user message. Uses the same logic as the /away dashboard.

## Usage

```
@away-tracker how long have you been away
@away-tracker minutes since last message
@away-tracker am I away
```

## What It Does

1. Reads session files from `/root/.openclaw/agents/main/sessions/`
2. Finds the most recent user message (excluding cron/heartbeat messages)
3. Calculates minutes/seconds since that message
4. Returns "away" status and time

## Output Format

Returns JSON with:
- `away`: true/false (based on 15 min threshold)
- `minutes`: minutes since last message
- `seconds`: remaining seconds
- `last_message`: timestamp of last message
