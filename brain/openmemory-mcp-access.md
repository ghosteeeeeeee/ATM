# Shared MCP Servers

All MCP servers shared across OpenCode, DSH, and other agents.
Config: `/root/.hermes/config/shared-mcp.json`

## Servers

| Server | Type | URL / Command | Purpose |
|--------|------|---------------|---------|
| **openmemory** | remote (HTTP) | `http://localhost:8080/mcp` | Cross-session memory |
| **sequential-thinking** | local (stdio) | `npx -y @modelcontextprotocol/server-sequential-thinking` | Step-by-step reasoning |
| **fetcher** | local (stdio) | `npx -y fetcher-mcp` | Web page fetching |

## OpenMemory Endpoint

```
POST http://localhost:8080/mcp
Headers:
  x-api-key: dev-key-123
  Content-Type: application/json
```

Protocol: JSON-RPC 2.0 over HTTP POST.

## Methods

- `tools/list` — list available tools
- `tools/call` — invoke a tool (e.g. `openmemory_query`, `openmemory_store`, `openmemory_list`)
- `resources/list` — list resources
- `resources/read` — read a resource

## Quick Test

```bash
# Test OpenMemory
curl -X POST http://localhost:8080/mcp \
  -H "x-api-key: dev-key-123" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"openmemory_query","arguments":{"query":"test"}}}'

# Test sequential-thinking (if running)
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | npx -y @modelcontextprotocol/server-sequential-thinking
```

## Notes

- OpenMemory must be running on localhost:8080 (check with `curl http://localhost:8080/mcp`)
- Auth is required for OpenMemory — missing `x-api-key` header returns `authentication_required` error
- Sequential-thinking and fetcher run on-demand via npx (no server needed)
- Works with any MCP-compatible harness: Claude Desktop, Cursor, opencode, DSH, custom agents

## Command Guard

Dangerous bash patterns shared across all agents:
`/root/.agents/hooks/dangerous-patterns.txt`

Blocks: `rm /`, `rm ~`, `dd` to disks, `mkfs`, `sudo rm`, fork bombs, `curl|wget | sh`, `git push --force`, `git push --delete`, `chmod 777 /`, `gh repo delete`, `gh auth token`, etc.
