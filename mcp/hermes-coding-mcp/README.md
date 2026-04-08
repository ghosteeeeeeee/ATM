# Hermes Coding MCP Server

A Model Context Protocol server providing core file operations, code search, and shell command execution for the Better Coder autonomous coding agent.

## Overview

This server implements the 4 foundational tools identified in the morphllm.com research as essential for coding agents:

1. **read_file** - Read file contents with line range support
2. **write_file** - Create or overwrite files
3. **search_code** - Regex search across files
4. **execute_command** - Run shell commands

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Run as MCP Server

```bash
python server.py
```

The server uses stdio transport for local CLI integration.

### Run Verification

```bash
pip install -r requirements.txt
python -c "from server import mcp; print('OK')"
```

## Tools

### read_file

Reads a file's contents with optional line range support.

**Parameters:**
- `path` (string, required): Absolute file path to read
- `offset` (integer, optional, default=1): Line number to start reading from (1-indexed)
- `limit` (integer, optional): Maximum number of lines to read

**Returns:**
```json
{
  "isError": false,
  "path": "/path/to/file",
  "content": ["line 1", "line 2", ...],
  "total_lines": 100,
  "truncated": false,
  "offset": 1,
  "limit": 50
}
```

**Errors:** `file_not_found`, `permission_denied`, `invalid_params`

---

### write_file

Writes content to a file, creating it if needed or overwriting if it exists.

**Parameters:**
- `path` (string, required): Absolute file path to write
- `content` (string, required): Content to write to the file

**Returns:**
```json
{
  "isError": false,
  "path": "/path/to/file",
  "bytes_written": 1024,
  "created": true,
  "overwritten": false
}
```

**Errors:** `permission_denied`, `unknown`

---

### search_code

Searches for a regex pattern in files within a directory.

**Parameters:**
- `pattern` (string, required): Regex pattern to search for
- `path` (string, optional, default="."): Directory or file path to search in
- `file_glob` (string, optional): Glob pattern to filter files (e.g., "*.py", "*.js")

**Returns:**
```json
{
  "isError": false,
  "pattern": "def\\s+\\w+",
  "path": "/path/to/search",
  "file_glob": "*.py",
  "matches": [
    {"path": "/path/to/file.py", "line": 10, "content": "def hello():"},
    {"path": "/path/to/file.py", "line": 25, "content": "def world():"}
  ],
  "match_count": 2,
  "truncated": false
}
```

**Errors:** `file_not_found`, `permission_denied`, `invalid_params` (invalid regex)

---

### execute_command

Executes a shell command and returns its output.

**Parameters:**
- `command` (string, required): Shell command to execute
- `timeout` (integer, optional, default=180): Maximum execution time in seconds
- `workdir` (string, optional): Working directory for command execution

**Returns:**
```json
{
  "isError": false,
  "command": "ls -la",
  "exit_code": 0,
  "stdout": "total 12\ndrwxr-xr-x  2 user user  160 Jan 1 00:00 .\n",
  "stderr": "",
  "timeout": 180,
  "workdir": "/current/working/dir"
}
```

**Errors:** `timeout`, `permission_denied`, `invalid_params`, `unknown`

## Error Format

All tools return structured JSON. On success, `isError` is `false`. On failure:

```json
{
  "isError": true,
  "error": "file_not_found",
  "message": "File does not exist: /path/to/file"
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `file_not_found` | File or directory does not exist |
| `permission_denied` | Insufficient permissions to read/write/execute |
| `timeout` | Command exceeded timeout limit |
| `invalid_params` | Invalid parameters (bad regex, offset exceeds file length, etc.) |
| `unknown` | Unexpected error |

## Architecture

This server follows the patterns from the Better Coder architecture:

- **Layer 1 (Agent Core)** - Provides the 4 minimum tools per morphllm.com research
- **Stateless tools** - Each tool call is independent
- **Typed parameters** - Pydantic validation on all inputs
- **Structured JSON output** - Every tool returns parseable JSON
- **Fail gracefully** - Never crash, always return error messages

## Integration

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "hermes-coding": {
      "command": "python",
      "args": ["/path/to/hermes-coding-mcp/server.py"]
    }
  }
}
```

## Development

The server is designed for the Better Coder pipeline:
- Phase 1a: Foundation tools (this server)
- Phase 1b: ReAct loop orchestration
- Phase 1c: Embeddings-based tool router

See `/root/.hermes/brain/better-coder-architecture.md` for full architecture details.
