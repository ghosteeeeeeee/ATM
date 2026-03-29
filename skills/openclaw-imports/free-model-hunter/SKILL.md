---
name: free-model-hunter
description: Daily automated search for best free OpenRouter models. Benchmarks speed, updates stats, and auto-configures fallback. Use when you want to find the fastest free model daily.
---

# Free Model Hunter

Automatically finds the best free OpenRouter model each day by benchmarking latency and updates your fallback config.

## What It Does

1. **Fetches** free models from OpenRouter
2. **Benchmarks** each model's latency with quick tests
3. **Applies bias** towards known good performers (Liquid, Nemotron, Gemma)
4. **Updates** stats file with daily rankings
5. **Auto-configures** best model as fallback in OpenClaw

## Files

- Script: `/root/.openclaw/workspace/skills/free-model-hunter/free_model_hunter.py`
- Stats: `/root/shared_notes/free-model-stats.md`

## Usage

### Run Manually
```bash
python3 /root/.openclaw/workspace/skills/free-model-hunter/free_model_hunter.py
```

### Setup Daily Cron
```bash
# Run at 6am daily
0 6 * * * /root/.openclaw/workspace/.venv/bin/python3 /root/.openclaw/workspace/skills/free-model-hunter/free_model_hunter.py >> /var/log/free-model-hunter.log 2>&1
```

## Biased Models

These models get a 30% speed boost in rankings:
- liquid/lfm-2.5-1.2b-instruct
- nvidia/nemotron-3-nano-30b-a3b
- google/gemma-3-4b-it

## Output

Stats saved to `/root/shared_notes/free-model-stats.md` with:
- Daily rankings by latency
- Working/failed models
- Best model of the day
- Config update command

## Example Stats Output

```markdown
# Free Model Stats
Last Updated: 2026-02-27 06:00

## Today's Rankings
| Rank | Model | Latency | Status |
|------|-------|---------|--------|
| 1 | liquid/lfm-2.5-1.2b-instruct | 0.42s | ✅ ⭐ |
| 2 | nvidia/nemotron-3-nano-30b-a3b | 0.93s | ✅ ⭐ |
```

## Requirements

- OPENROUTER_API_KEY in environment
- Python: requests

## Skill Commands

This skill doesn't register CLI commands - run the script directly or via cron.
