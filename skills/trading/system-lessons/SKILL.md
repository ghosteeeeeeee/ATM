# System Lessons from Video Transcripts

Source: YouTube video transcripts analyzed 2026-08-05
Videos: "I Replaced Hermes Agent And OpenClaw With This", "QWEN just CRASHED the industry"

## Memory System

**Lesson:** Auto-saved memory goes stale fast. The Hermes Agent creator found facts like "current stack is Rails" persisted long after they became false. Auto-created skills were junk that degraded performance.

**Action for Hermes:**
- OpenMemory + hebbian memory already human-curated (good)
- Add periodic memory audit: tag with `created_at` and `last_reinforced`
- Prune anything unreinforced for 30+ days
- Never let signal_compactor auto-generate memory entries

## Security Architecture

**Lesson:** Polling > webhooks. No exposed ports = no inbound attack surface. The Coldcard $100M drain happened because open-source code sat unpatched for 5 years — AI models now audit code line-by-line and find vulnerabilities humans missed.

**Action for Hermes:**
- Document polling-over-webhooks as intentional architecture
- Run `pip-audit` weekly on dependencies
- Pin all dependency versions (no floating `>=`)
- Ensure `.secrets.local` never leaks to logs
- API keys: minimum permissions, IP-whitelisted, rotate quarterly

## Long-Running Task Stability

**Lesson:** Small mistakes compound in long-horizon tasks. Qwen succeeded at 10-day autonomous coding because it had self-correction (state machine + dispatcher + monitor + watchdog).

**Action for Hermes:**
- Pipeline IS a state machine — add watchdog timer
- Detect stall: if `pipeline.lock` older than expected, or last signal > 2× normal interval
- Add weekly signal quality self-check — halt if WR drops below threshold

## Configuration Philosophy

**Lesson:** Minimal, opinionated config beats sprawling options. Single YAML with channel, agent, context, jobs. Reviewable, version-controlled.

**Action for Hermes:**
- `hermes_constants.py` with warning header is the right pattern
- Ensure no undocumented config drift
- Add `Description=` to all systemd timer/service files

## Agent Orchestration

**Lesson:** Requirements → issues → agent claims → states → tests → CI → merge. The watchdog monitors the whole loop.

**Action for Hermes:**
- Pipeline already follows this pattern (signals → compactor → decider → execution)
- Missing: watchdog that detects compactor producing garbage or signals going stale

## Priority Actions

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 1 | `pip-audit` weekly | Low | Security |
| 2 | Pipeline watchdog timer | Medium | Reliability |
| 3 | Memory staleness audit | Low | Memory quality |
| 4 | Weekly signal quality self-check | Medium | Trading quality |
| 5 | Document security architecture | Low | Documentation |

## Key Insight

> "The more skills you have, the worse your agent will perform generally because every time it runs, it has to decide whether to load any of those skills."

Keep Hermes focused. Fewer, better signals > many mediocre ones. Quality over quantity.
