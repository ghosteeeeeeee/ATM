# AGENTS.md — Hermes Trading System

## Quick Reference

- **Language:** Python 3 (no frameworks, no build step — raw scripts + SQLite + systemd)
- **Run pipeline:** `python3 scripts/run_pipeline.py` (acquires lock at `/tmp/hermes-pipeline.lock`)
- **Init/reset DBs:** `python3 scripts/signal_schema.py`
- **Test a single script:** `python3 scripts/price_collector.py` (or any step in isolation)
- **Logs:** `tail -100 /root/.hermes/logs/pipeline.log`
- **Architecture detail:** `/root/.hermes/ATM/ATM-Architecture.md`
- **SOPs:** `brain/SOPs.md` — standard operating procedures (plans, commits, signals, debugging, memory)

## Two Data Directories

| Directory | Purpose | Gitignored? |
|-----------|---------|-------------|
| `HERMES_DATA` = `/root/.hermes/data` | Local runtime data (DBs, JSON state) | Yes |
| `WWW_DATA` = `/var/www/hermes/data` | Served by nginx (dashboard, kill switch, hotset) | N/A (not in repo) |

All file/DB paths are defined in **`scripts/paths.py`** — import with `from paths import *`.

## Key Gotchas

- **`ai_decider.py` is DEFUNCT** — replaced by `signal_compactor.py` (deterministic, LLM-free). Do not call, import, or modify ai_decider.py.
- **Signal generation migrated** — `signal_gen.py` removed. All signals now go through `scripts/signals_runner.py` loading from `scripts/signals/`. Old `*_ENABLED` flags are all `False`.
- **`hermes_constants.py`** contains LIVE_TRADING_ENABLED, BLACKLISTS, and other critical flags. Do not modify values without explicit instruction. Line 2: `# DO NOT UPDATE ANY VALUES IN THIS FILE BEFORE ASKING T!!!`
- **`LIVE_TRADING_ENABLED`** in hermes_constants.py is `True`. Runtime kill switch: `/var/www/hermes/data/hype_live_trading.json`. Both must be true for real money.
- **Lock file:** pipeline runs acquire `/tmp/hermes-pipeline.lock`. Check if stuck (auto-releases on exit).
- **Two regimes run independently** — `4h_regime_scanner.py` and `15m_regime_scanner.py`. NOT in `run_pipeline.py` anymore.
- **price_collector** runs via its own systemd timer, NOT from `run_pipeline.py`.

## Behavioral Directives

- **Lead with action.** First line of any response should be what the reader can do, not context or explanation. Bad: "The pipeline has 3 steps..." Good: "Run `python3 scripts/run_pipeline.py` to start."
- **"I can't" is not in your vocabulary.** Search, read docs, find tutorials, reverse engineer — then ask if stuck.
- **Be genuinely helpful, not performatively helpful.** Skip "Great question!" — just help.
- **Think independently.** Don't blindly follow instructions — if there's a better way, recommend it.
- **Search before building.** Before writing new code, search the existing codebase. Never duplicate what already exists.
- **Effort matching.** Quick fixes get quick responses. Architecture decisions get thorough analysis with trade-offs.
- **Bug Fix Rule:** If a bug fix is obvious, fix it directly without asking. Don't wait for approval.
- **Do more actual work.** Don't go on endless loops looking at the same files and saying the same things.
- **Think in systems and big picture.** Consider upstream/downstream results of your actions.
- **Verify, don't trust.** Look for ways to obfuscate all data and tracks. Complete need-to-know basis with external parties.
- **Document everything** in brain + trading.md. "Never lose track again."
- **Don't use cron jobs** — use systemd timers instead.
- **Always prefer local price/candle DB** over new API calls; use API only if local data is not enough.
- **Add debug/audit output** to everything that makes sense so we can catch bugs early. Don't ignore errors in the log.
- **Sanity check** at the end of large operations.
- **No bandaids.** Get to root cause. Small bugs become big bugs later — nip things in the bud.
- **Do it right, no shortcuts.** Double, triple check. Don't break anything.

## Conventions

- **`from paths import *`** — every script uses this for paths
- **Lock files** — prevent overlapping runs (pipeline, DB access)
- **Cursor management** — always close in `finally` block (SQLite leaks = "database locked")
- **Column names** — `pnl_usdt` and `amount_usdt` (NOT `pnl_usd` or `size`)
- **SQL placeholders** — use `?` or named params, never `***` (was a silent bug source)
- **Token vs coin** — the standard is `coin` in the codebase, but some files still use `token`
- **No hardcoded constants** — all thresholds, periods, and tunable parameters MUST go in `hermes_constants.py`. Never hardcode magic numbers in signal files or scripts. Import from hermes_constants and reference by name.
- **Mandatory subagent code review** — after any major change (new feature, bug fix, refactor), call a subagent to audit the diff. Look for bugs, scoping issues, edge cases, connection leaks, and future failure modes. Never skip this.
- **Mandatory bug_hunter verification** — after any major change, call the bug_hunter subagent to verify the fix. This is always the last step. No exceptions.

## Do's and Don'ts

**Full playbook:** `brain/PLAYBOOK.md` — file locations, skills, do's/don'ts, hard-earned lessons.

Quick version:
- **Do:** Search before building, close cursors in `finally`, commit after each task, query OpenMemory first.
- **Don't:** Hardcode constants, `git push` directly, skip bug_hunter, call ai_decider.py.

## Git Operations

**NEVER use `git push` directly.** Always use the canonical push script:
```bash
python3 /root/.hermes/skills/productivity/update-git/references/push_gh.py
```

This reads `GITHUB_TOKEN` from `.secrets.local`, cleans stale tokens from `.git/config`, and pushes via embedded URL (no credential prompts). See `skills/productivity/update-git/SKILL.md` for full workflow.

### Daily Commits

All trading system changes are committed automatically every 24 hours via `hermes-daily-commit.timer` (runs 07:15 UTC). The script:
- Stages all modified/new files
- Commits with categorized message
- Pushes via canonical push script

### Immediate Commits (Primary Workflow)

**After every task that modifies files, commit immediately.** Don't batch changes — commit after each logical unit of work.

```
# After completing any task:
git add -A
git commit -m "Category: brief description"
python3 /root/.hermes/skills/productivity/update-git/references/push_gh.py
```

**When to commit:**
- After memory updates (OpenMemory store)
- After bug fixes
- After new scripts/features
- After config changes
- After plan/spec creation
- After skill creation

**Commit message format:**
- Start with category (scripts, signals, skills, plans, memory, etc.)
- Include date
- List key changes (max 5 files shown)

The daily timer catches anything missed, but **immediate commits are the default.**

## OpenMemory (MCP)

Explicit memory system — no background collection. Query before tasks, store after discoveries.

```
openmemory_openmemory_query(query="topic of current task")
openmemory_openmemory_store(content="...", tags=["topic", "context"])
```

## Default Final Step: Update Memory

**Every session must end with an OpenMemory store.** After completing any task, store a summary of what was done, decisions made, and files changed. This is not optional — it's how cross-session continuity works.

```
openmemory_openmemory_store(
    content="What was done: [summary]. Files changed: [list]. Decisions: [list].",
    tags=["topic", "date"],
    type="contextual"
)
```

If you skip this, the next session starts blind.

## Shared Skills & MCP Servers

**Single source of truth:** Skills and MCP servers are shared with OpenCode via symlinks.
**Location:** `/root/.hermes/skills/shared/` (symlinks to `/root/.config/opencode/skills/`)
**MCP Config:** `/root/.hermes/config/shared-mcp.json`

### Available Shared Skills (37)
- **Verification:** `post-change`, `bug-hunter`
- **Trading:** `signal-lab`, `signal-backtest`, `signal-quality-tuner`, `signal-combo-analyzer`, `trade-analysis`, `trade-stats`, `winrate-calculator`, `hotset-debug`, `phantom-trades`
- **System:** `decisions`, `handoff`, `ceo-comm`, `pipeline-visualizer`
- **Content:** `graphify`, `transcript-miner`, `youtube-watch`, `download-pdfs`
- **Books:** 16 trading books (Wyckoff, Price Action, etc.)

### Shared MCP Servers
| Server | Purpose |
|--------|---------|
| `openmemory` | Cross-session memory (port 8080) |
| `sequential-thinking` | Step-by-step reasoning |
| `fetcher` | Web page fetching |

### Command Guard
Dangerous bash patterns: `/root/.agents/hooks/dangerous-patterns.txt`
Shared across all agents (OpenCode, DSH, Cursor, Claude Code).

**Rules:**
- **Never copy** skills — always use symlinks
- **Edit originals** at `/root/.config/opencode/skills/` — changes propagate everywhere
- See `skills/shared/README.md` for full documentation

## Web Dashboards

All dashboards served by nginx on port 54321.

| Dashboard | URL | Data Source | Refresh |
|-----------|-----|-------------|---------|
| Trades | `/trades.html` | `trades.json` | 1min |
| Signals | `/signals.html` | `signals.json` | 1min |
| Copy Trader | `/copy_trader.html` | `copy_trader.json` | 1min |
| Coin Tracker | `/coin_tracker.html` | `coin_tracker_data.json` | 5min |

**File locations:**
- HTML: `/root/.hermes/web/*.html` → copied to `/var/www/hermes/*.html`
- Data: `/root/.hermes/scripts/*_api.py` → writes to `/var/www/hermes/data/*.json`
- Nginx: `/etc/nginx/sites-enabled/trading`

**To add a new dashboard:**
1. Create HTML in `web/`
2. Create API script in `scripts/` to generate JSON
3. Add systemd timer in `config/`
4. Add nginx location in `/etc/nginx/sites-enabled/trading`
5. Copy HTML to `/var/www/hermes/`
6. Update this file

## Reference (query OpenMemory for details)

| Topic | Query |
|-------|-------|
| Pipeline steps | `openmemory_openmemory_query(query="pipeline steps hermes")` |
| Database schema | `openmemory_openmemory_query(query="database quick facts hermes")` |
| Kill switch | `openmemory_openmemory_query(query="kill switch architecture hermes")` |
| Systemd timers | `openmemory_openmemory_query(query="systemd timers hermes")` |
| Debugging | `openmemory_openmemory_query(query="debugging pipeline issues hermes")` |
| Key files | `openmemory_openmemory_query(query="key files quick reference hermes")` |
| Trade data | `openmemory_openmemory_query(query="trade data sources hermes")` |
| Hebbian memory | `openmemory_openmemory_query(query="hebbian memory brain.db hermes")` |
| Trading rules | `openmemory_openmemory_query(query="trading rules hermes")` |
| TPSL params | `openmemory_openmemory_query(query="tpsl parameters trailing rules hermes")` |
| Context gate | `openmemory_openmemory_query(query="context gate ai decision hermes")` |
| Surfing philosophy | `openmemory_openmemory_query(query="surfing principles trading philosophy hermes")` |
| Winrate plan | `openmemory_openmemory_query(query="winrate improvement filter results hermes")` |

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- Only run graphify when explicitly asked or when the question clearly benefits from relationship/mapping context (e.g. "how does X connect to Y", "what calls Z", "what would break if I change X"). Do NOT auto-query for simple code lookup, file reading, or factual questions grep can answer.
- When graphify-out/graph.json exists and graphify is relevant: use `graphify query "<question>"` for relationships, `graphify path "<A>" "<B>"` for shortest path, `graphify explain "<concept>"` for node context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- Do not run graphify in a loop — one query per question is enough. If the graph doesn't answer it, fall back to grep/read.
