# Brain System Docs

**See also:** [subagents.md](./subagents.md) — 150+ AI agent personas across 16 domains

## MiniMax API Usage

**Plan:** Text Generation — 5 Hours/month
**Time Range:** 20:00-00:00 (UTC)
**Reset:** ~2.5 hours from last check
**Current:** 503/1500 tokens used (34%)

> Update this section when usage resets or plan changes.

## API Credentials

- **Provider:** minimax (OpenAI-compatible)
- **Base URL:** `https://api.minimax.io/v1`
- **Model:** `MiniMax-M2` (your plan's available model)
- **Token:** stored in `/root/.hermes/auth.json` → `credential_pool.minimax[0].access_token`
- **Fallback:** Ollama at `localhost:11434` (qwen2.5:1.5b) if minimax unavailable

## Hot-Set Pipeline

See `trading.md` for the full pipeline. Key files:

- `/var/www/hermes/data/hotset.json` — authoritative hot-set (written by ai_decider.py every 10 min)
- `/var/www/hermes/data/signals.json` — web dashboard output (reads from hotset.json, enriched with live RSI)
- `ai_decider.py` — compaction + scoring + AI decision gate
- `hermes-trades-api.py` — writes signals.json for web UI (reads hotset.json as authoritative source)
