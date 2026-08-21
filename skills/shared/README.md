# Shared Skills — Single Source of Truth

This directory contains **symlinks** to the original OpenCode skills.
All skills are maintained in one place: `/root/.config/opencode/skills/`

**DO NOT COPY** — edit the originals, both systems get the update.

## Architecture

```
/root/.config/opencode/skills/     ← SOURCE (OpenCode)
        ↓ symlinks
/root/.hermes/skills/shared/       ← DSH references
```

## Available Skills (37 total)

### Trading & Analysis
| Skill | Purpose |
|-------|---------|
| `signal-lab` | Signal analysis and testing |
| `signal-backtest` | Backtesting signals |
| `signal-quality-tuner` | Tune signal parameters |
| `signal-combo-analyzer` | Analyze signal combinations |
| `trade-analysis` | Analyze trade performance |
| `trade-stats` | Trade statistics |
| `winrate-calculator` | Winrate calculations |
| `hotset-debug` | Debug hotset issues |
| `phantom-trades` | Debug phantom trades |

### Verification & Debugging
| Skill | Purpose |
|-------|---------|
| `post-change` | Full verification workflow (bug_hunter → OpenMemory → commit) |
| `bug-hunter` | Code audit specialist with common bug patterns |

### System & Workflow
| Skill | Purpose |
|-------|---------|
| `decisions` | Decision tracking |
| `handoff` | Session handoff |
| `ceo-comm` | CEO communication |
| `pipeline-visualizer` | Pipeline visualization |

### Content & Research
| Skill | Purpose |
|-------|---------|
| `graphify` | Knowledge graph |
| `transcript-miner` | Transcript mining |
| `youtube-watch` | YouTube analysis |
| `download-pdfs` | PDF download |

### Books (16)
Wyckoff, Price Action, Trading Psychology, and more.

## MCP Servers

Shared config: `/root/.hermes/config/shared-mcp.json`

| Server | Purpose |
|--------|---------|
| `openmemory` | Cross-session memory |
| `sequential-thinking` | Step-by-step reasoning |
| `fetcher` | Web page fetching |

## Command Guard

Dangerous patterns shared across all agents:
`/root/.agents/hooks/dangerous-patterns.txt`

## Adding New Skills

1. Add to `/root/.config/opencode/skills/` (source)
2. Create symlink here: `ln -sf /root/.config/opencode/skills/new-skill new-skill`
3. Both OpenCode and DSH can now use it

## Rules

- **Never copy** — always symlink
- **Edit originals** — changes propagate to both systems
- **One source of truth** — prevents divergence
