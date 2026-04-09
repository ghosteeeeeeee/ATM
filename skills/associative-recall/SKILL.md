# Associative Recall — Session Start Hook

This skill is automatically invoked at the start of every session.

## Purpose

Before responding to the user's first message, proactively surface related context from Hermes's Hebbian memory network. This makes the agent feel like it "remembers" — surfacing related projects, recent work, past issues — all based on what has actually co-occurred in Hermes's experience.

## How It Works

At session start (or when T mentions a concept):

1. **Extract** the key concept from T's message
2. **Recall** it: `python3 /root/.hermes/scripts/hebbian_engine.py recall <concept>`
3. **Surface** top associations naturally in the response

## Manual Recall Commands

```bash
# Check what Hermes has learned about any concept
python3 /root/.hermes/scripts/hebbian_engine.py recall <concept> [k]

# Examples:
python3 /root/.hermes/scripts/hebbian_engine.py recall Tokyo
python3 /root/.hermes/scripts/hebbian_engine.py recall cascade_flip
python3 /root/.hermes/scripts/hebbian_engine.py recall SCR

# Network stats
python3 /root/.hermes/scripts/hebbian_engine.py stats
```

## Session Co-occurrence Learning

After significant sessions or work sessions, run:
```bash
python3 /root/.hermes/scripts/hebbian_session_learner.py [days_back]
```

This learns from:
- Session conversation dumps
- Trading decisions log (token + regime + direction co-occurrences)
- Event log entries

## Integration

Hebbian learning fires automatically when:
- Session learner cron runs daily
- `hebbian_session_learner.py` is run manually
- `hebbian_engine.py learn` CLI is called
- MCP tools `hebbian_learn` / `hebbian_recall` are used
- Trading decisions are processed

## Network Stats (2026-04-09)

```
Nodes: 96 | Synapses: 379
Top edges: LONG_BIAS<->HOT_APPROVED, TNSR<->SHORT_BIAS, SHORT_BIAS<->SKIPPED
```
