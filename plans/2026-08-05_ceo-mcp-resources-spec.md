# CEO MCP Resources Server — Spec

## Motivation

Expose CEO outputs as queryable MCP resources so other agents (orchestrator, self_learner, bug_hunter) can query CEO state without parsing markdown files.

## Architecture

Single Python file, FastMCP, stdio transport. Standalone server (not added to hermes-coding-mcp).

## Resources (read-only)

| URI | Returns | Source |
|-----|---------|--------|
| `ceo://report/latest` | Parsed report JSON (health, performance, decisions, risks) | `ceo_report.md` |
| `ceo://decisions/pending` | Kanban TODO + IN PROGRESS items | `ceo_kanban.md` |
| `ceo://params/current` | All trading params (SL, trailing, speed, toggles) | `hermes_constants.py` |
| `ceo://performance` | 24h/7d/all-time win rate, PnL, trade count | SQLite `signal_outcomes` |
| `ceo://blacklists` | LONG + SHORT blacklisted tokens | `hermes_constants.py` |
| `ceo://signals/status` | Per-signal enabled/disabled + 7d win rate | `hermes_constants.py` + SQLite |

## Files to create

| File | Purpose |
|------|---------|
| `mcp/ceo-resources/server.py` | ~40 lines. FastMCP server with 6 `@mcp.resource()` functions |
| `systemd/hermes-ceo-resources.service` | Systemd unit (copy pattern from `hermes-coding-mcp.service`) |

## Files to modify

| File | Change |
|------|--------|
| `opencode.jsonc` | Add `ceo-resources` MCP server entry |

## Implementation sketch

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("ceo-resources")

@mcp.resource("ceo://report/latest")
def latest_report():
    # parse ceo_report.md → return JSON dict
    
@mcp.resource("ceo://decisions/pending")  
def pending_decisions():
    # parse ceo_kanban.md TODO/IN PROGRESS sections

@mcp.resource("ceo://params/current")
def current_params():
    # grep hermes_constants.py for key params

@mcp.resource("ceo://performance")
def trading_performance():
    # SQL query against signal_outcomes

@mcp.resource("ceo://blacklists")
def blacklists():
    # parse SHORT_BLACKLIST, LONG_BLACKLIST from constants

@mcp.resource("ceo://signals/status")
def signal_status():
    # all *_ENABLED flags + 7d WR per signal
```

## What's skipped

- **No write tools.** Kanban stays CEO's alone. Agents propose via separate inbox files.
- **No query parameters.** Resources return current state, not historical. Add filtering when someone actually needs it.
- **No webhooks/subscriptions.** Polling is fine for 24h strategic data.
- **No new dependencies.** `mcp` SDK already installed, `sqlite3` stdlib, markdown parsing is regex.

## CEO feedback

> "Deferred. Ship only if an agent demonstrates it can't parse ceo_report.md reliably. Otherwise, this solves a problem that doesn't exist yet."

Ship when: orchestrator misinterprets a decision, or self_learner can't extract parameter values reliably. Until then, park it.
