# OpenMemory MCP Access

## Endpoint

```
POST http://localhost:8080/mcp
Headers:
  x-api-key: dev-key-123
  Content-Type: application/json
```

Protocol: JSON-RPC 2.0 over HTTP POST.

## MCP Config for Any Client

```json
{
  "mcpServers": {
    "openmemory": {
      "type": "streamableHttp",
      "url": "http://localhost:8080/mcp",
      "headers": {
        "x-api-key": "dev-key-123"
      }
    }
  }
}
```

## Methods

- `tools/list` — list available tools
- `tools/call` — invoke a tool (e.g. `openmemory_query`, `openmemory_store`, `openmemory_list`)
- `resources/list` — list resources
- `resources/read` — read a resource

## Quick Test

```bash
curl -X POST http://localhost:8080/mcp \
  -H "x-api-key: dev-key-123" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"openmemory_query","arguments":{"query":"test"}}}'
```

## Notes

- Server must be running on localhost:8080 (check with `curl http://localhost:8080/mcp`)
- Auth is required — missing `x-api-key` header returns `authentication_required` error
- Works with any MCP-compatible harness: Claude Desktop, Cursor, opencode, custom agents
