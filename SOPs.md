# SOPs.md - Standard Operating Procedures

## Security Rule

**Never expose ports publicly.** All services (gateway, VNC, dashboards on port 80, etc.) must bind to localhost only (127.0.0.1). SSH (port 333 on Dallas) is the ONLY exception that may be exposed externally.

---

## Memory & Documentation

### After Each Session
- Save key facts to `brain.md`
- Update `CONTEXT.md` if anything significant happened (new trades, system fixes, wins/losses, decisions)

### CONTEXT.md (`/root/.hermes/CONTEXT.md`)
- T's living session doc — keep it short and tidy
- Update after significant events: new trades, system fixes, wins/losses, important decisions
- Current snapshot should reflect what's active right now

### Trading Live Log (`/root/.hermes/brain/trading.md`)
- **Updated every 10 minutes by the pipeline** (written by `ai_decider.py` + pipeline hooks)
- Contains: current positions, hot-set status, 7-day stats, active ideas, live log of bugs/fixes, known issues
- This is the system's live journal — everything to do with the trading system goes here
- Any significant event (trade closed, bug found, fix applied, idea generated) gets a timestamped entry

---

## API Calls

**Use `requests.post()` for all local HTTP API loops** (Ollama, Hyperliquid, etc.) — ~3x faster than subprocess curl. Subprocess curl is fine for one-off shell commands, not loops.

---

## Skills

### After Hard Tasks (5+ tool calls)
- Save the approach as a skill with `skill_manage create`
- Include: trigger conditions, exact commands, pitfalls, verification steps

### If a Skill is Wrong or Stale
- Patch it immediately with `skill_manage patch` — don't wait to be asked
- Outdated skills are liabilities

---

## Git

- Commit meaningful changes to `/root/.hermes` regularly
- **jobs.json stays untracked** (`git rm --cached`) — contains job prompts, file paths, architecture details
- Always review cron/jobs.json for sensitive content before (re)committing

---

## Ollama Fallback

If cloud APIs (MiniMax) are unavailable, fall back to Ollama at `localhost:11434` with model `qwen2.5:1.5b`. This ensures resilience for overnight/background runs.

---

## Trading System

### Key Files
- `ai_decider.py` — compaction + scoring + AI decision gate
- `hotset.json` (`/var/www/hermes/data/hotset.json`) — authoritative hot-set (written every 10 min)
- `signals.json` (`/var/www/hermes/data/signals.json`) — web dashboard output (reads hotset.json, enriched with live RSI)
- `hermes-trades-api.py` — writes signals.json for web UI

