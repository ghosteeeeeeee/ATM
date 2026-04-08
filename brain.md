# Brain System Docs

**See also:** [subagents.md](./subagents.md) — 150+ AI agent personas across 16 domains

---

## File Anchors — Path Reference (search here, not CONTEXT.md)

### Brain Files
| File | Purpose |
|------|---------|
| `brain/TASKS.md` | Task tracker — active todos, linked to projects |
| `brain/PROJECTS.md` | Project tracker — active projects, status, owner |
| `brain/DECISIONS.md` | Decision log — why we made each call |
| `brain/ideas.md` | Ideas backlog — new ideas, status, next step |
| `brain/trading.md` | Trading system state — positions, regime, bugs |
| `brain/lessons.md` | Hard-won lessons — never repeat these mistakes |
| `brain/upgrades.md` | System upgrade history |

### Key Data Files
| File | Purpose |
|------|---------|
| `CONTEXT.md` | Per-call session anchor — Quick Status, Focus, Critical Flags |
| `SOUL.md` | System identity, self-model, directives |
| `SOPs.md` | Standard operating procedures |
| `config.yaml` | Hermes agent config |
| `data/hotset.json` | Active signal hot-set (top 10 tokens) |
| `data/trades.json` | Paper trade history |
| `data/kanban.json` | Kanban board JSON (synced with TASKS.md) |
| `data/signals_hermes_runtime.db` | Local SQLite signal runtime DB |
| `data/hype_live_trading.json` | Live trading kill switch |

### Core Scripts
| Script | Purpose |
|--------|---------|
| `scripts/ai_decider.py` | AI decision gate — scoring, compaction, hot-set builder |
| `scripts/decider_run.py` | Pipeline orchestrator — runs every minute |
| `scripts/hl-sync-guardian.py` | Position mirror — keeps HL in sync with paper |
| `scripts/position_manager.py` | SL/TP management, cascade flip |
| `scripts/signal_gen.py` | Signal generation — momentum + pattern scanner |
| `scripts/hermes-trades-api.py` | Trades JSON API for web dashboard |
| `scripts/kanban_api.py` | Kanban board API server (port 3461) |
| `scripts/hermes_write_with_lock.py` | Flock-based file writer (prevents write collisions) |
| `scripts/context-compactor.py` | Auto-patches CONTEXT.md Quick Status every 30 min |
| `scripts/sync_kanban_tasks.py` | Bidirectional TASKS.md ↔ kanban.json sync |
| `scripts/hermes-brain-sync.py` | Daily 6am EST deep PM audit (read-only) |

### Trading Skills
| Skill | Category |
|-------|----------|
| `hermes-session-wrap` | trading |
| `signal-compaction` | trading |
| `wasp` | trading |
| `full-review` | trading |
| `closed-trades-eval` | trading |
| `stale-trades` | trading |
| `signal-flip` | trading |
| `blocklist-decision` | trading |
| `sync-trades` | trading |
| `sync-open-trades` | trading |
| `analyze-trades` | trading |
| `prompt-training` | trading |
| `project-management` | productivity |
| `hermes-brain-sync` | productivity |

### Systemd Timers
| Timer | Schedule | Purpose |
|-------|----------|---------|
| `hermes-pipeline.timer` | Every minute | Main trading pipeline |
| `hermes-git-release.timer` | Daily | Git commit + release package |
| `hermes-brain-sync.timer` | Daily 05:00 UTC (6am EST) | Deep PM audit |

### Web / Ports
| Port | Service |
|------|---------|
| 54321 | Git web UI + download releases (nginx) |
| 3461 | Kanban API server (kanban_api.py) |
| 18790 | Hermes gateway (agent framework) |
| 11434 | Ollama local LLM (qwen2.5:1.5b fallback) |
| 8080 | Not in use |

---

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
