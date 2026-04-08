# Better Coder — Quick Reference

**Status:** WIRED AND ACTIVE (2026-04-08)

## What It Is

The Better Coder is Hermes's built-in autonomous coding pipeline — a 5-layer architecture for world-class AI-assisted coding:

1. **Layer 1 — MCP Server** (`hermes-coding-mcp`) — 4 core tools
2. **Layer 2 — ReAct Loop** — think → route → act → observe → decide
3. **Layer 3 — Memory Graph** — SQLite knowledge graph + pattern library
4. **Layer 4 — Tool Router** — embeddings-based tool selection
5. **Layer 5 — Parallel Dispatcher** — concurrent pipeline execution

## MCP Tools Available

| Tool | Description |
|------|-------------|
| `read_file` | Read file with line range support. Params: `path`, `offset?`, `limit?` |
| `write_file` | Create/overwrite file. Params: `path`, `content` |
| `search_code` | Regex search in files. Params: `pattern`, `path?`, `file_glob?` |
| `execute_command` | Run shell command. Params: `command`, `timeout?`, `workdir?` |

## Quick Start

```bash
# Start the MCP server
python3 /root/.hermes/mcp/hermes-coding-mcp/server.py

# Verify tools via hermes mcp
hermes mcp list
hermes mcp test hermes-coding-mcp
```

## Architecture

```
Better Coder Pipeline:
  TASKS.md → ParallelDispatcher → PipelineWorker (ReAct loop)
                              → ToolRouter (embeddings)
                              → MCP Tools (read_file, write_file, search_code, execute_command)
                              → Memory Graph (context loader + session writer)
```

## Key Files

- **Server:** `/root/.hermes/mcp/hermes-coding-mcp/server.py`
- **Dispatcher:** `/root/.hermes/mcp/hermes-coding-mcp/dispatcher/dispatcher.py`
- **Worker:** `/root/.hermes/mcp/hermes-coding-mcp/dispatcher/worker.py`
- **Router:** `/root/.hermes/mcp/hermes-coding-mcp/router/router.py`
- **Memory:** `/root/.hermes/mcp/hermes-coding-mcp/memory/graph_db.py`

## Integration

Added to Hermes via:
```bash
hermes mcp add hermes-coding-mcp --command python3 --args /root/.hermes/mcp/hermes-coding-mcp/server.py
```

Tools are auto-enabled in new sessions.

## Cron Job

Parallel dispatcher runs every 30 min via `hermes-pipeline` cron job.

## Status History

- 2026-04-08: Wired into Hermes. All 4 tools enabled. E2E tested.