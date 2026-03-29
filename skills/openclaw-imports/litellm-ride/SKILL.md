---
name: litellm-ride
description: Manage AI models through LiteLLM proxy. Routes OpenClaw through LiteLLM for load balancing, free model fallbacks, and multi-provider support. Use when user wants to use MiniMax, OpenRouter free models, or set up a unified AI proxy.
---

# LiteLLM Ride - Unified AI Proxy for OpenClaw

## What This Skill Does

Configures OpenClaw to route through **LiteLLM** (localhost:4000) instead of direct API calls. This enables:
- **Free OpenRouter models** as fallbacks
- **MiniMax** and other providers through single endpoint
- **Load balancing** across providers
- **Automatic retries** on rate limits

## Prerequisites

1. **Environment variables** — Check with `litellm-ride envcheck`:
   ```bash
   export OPENROUTER_API_KEY="sk-or-v1-..."
   export MINIMAX_API_KEY="..."
   # Optional:
   export LITELLM_MASTER_KEY="..."
   ```

2. **Install the skill**:
   ```bash
   cd ~/.openclaw/workspace/skills/litellm-ride
   pip install -e .
   ```

## Architecture

```
OpenClaw → LiteLLM (localhost:4000) → 
  ├── openrouter/free (automatic fallback)
  ├── minimax/MiniMax-Text-01
  ├── openrouter/qwen/qwen3-8b:free
  └── [your other providers]
```

## Commands

| Command | Description |
|---------|-------------|
| `litellm-ride auto` | Configure with default models (free + MiniMax) |
| `litellm-ride start` | Start LiteLLM proxy on port 4000 |
| `litellm-ride status` | Show current configuration |
| `litellm-ride add <model>` | Add a model (free, minimax, qwen) |
| `litellm-ride remove <name>` | Remove a model |
| `litellm-ride primary <name>` | Set primary model |
| `litellm-ride sync` | Force sync config |
| `litellm-ride envcheck` | Check environment variables |
| `litellm-ride list` | Show available default models |

## Quick Start

```bash
# 1. Configure models
litellm-ride auto

# 2. Start the proxy (in background)
litellm-ride start &

# 3. Configure OpenClaw to use litellm
openclaw config set agents.defaults.model.primary "litellm/free"
# Or use a specific model:
openclaw config set agents.defaults.model.primary "litellm/minimax"

# 4. Restart gateway
openclaw gateway restart
```

## Configuring OpenClaw

After running `litellm-ride auto`, update your config:

```bash
# Point to litellm endpoint
openclaw config set agents.defaults.apiBase "http://localhost:4000"

# Set model (mapped through litellm)
openclaw config set agents.defaults.model.primary "free"

# Add fallbacks
openclaw config set agents.defaults.model.fallbacks '["minimax", "qwen3"]'

openclaw gateway restart
```

## Adding Custom Providers

```bash
# Add Anthropic through litellm
litellm-ride add anthropic-claude
```

Or edit `~/.openclaw/litellm_config.yaml` directly.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `litellm-ride: command not found` | `cd ~/.openclaw/workspace/skills/litellm-ride && pip install -e .` |
| Connection refused on 4000 | Run `litellm-ride start` first |
| Rate limits | LiteLLM auto-retries; add more fallbacks with `litellm-ride auto` |
| Model not found | Check `litellm-ride status` and `litellm-ride envcheck` |

## Files Created

- `~/.openclaw/litellm-ride/config.yaml` — Skill config
- `~/.openclaw/litellm_config.yaml` — LiteLLM proxy config
