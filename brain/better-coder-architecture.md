# Better Coder — Architecture Doc
**Created:** 2026-04-08  
**Layer 1 (Agent Core) + Layer 2 (ReAct Loop) Design**

---

## Overview

This doc covers Phase 1 implementation: building the `hermes-coding-mcp` server (Layer 1) and designing the ReAct orchestration loop with embeddings-based tool routing (Layer 2).

**Sources:** nauvalazhar/build-your-own-ai-coding-agent, morphllm.com (4-tool minimum), kevinrgu/autoagent (Docker harness)

---

## Layer 1 — hermes-coding-mcp Server

### Design Philosophy

- **4 tools minimum** per morphllm.com research: Read, Write, Execute, Search
- **Code search = 60%+ of agent time** — make this first-class
- **Edit format > model choice** — structured diff output matters
- **Typed params with Pydantic** — every tool validated, documented, fail-gracefully
- **Stdio transport** — stdio for local CLI integration (matches hermes-agent pattern)

### Tool Definitions

#### Tool 1: `read_file`
```
Purpose: Read file contents with line range support
Params:
  - path: string (required) — absolute file path
  - start_line: int (optional, default=1) — first line to return
  - end_line: int (optional) — last line to return  
  - max_lines: int (optional, default=500) — max lines per call
Description: "Read a file's contents. Use start_line/end_line for large files."
Returns: JSON with {path, lines, total_lines, truncated}
Errors: file_not_found, permission_denied, read_timeout
```

#### Tool 2: `write_file`  
```
Purpose: Create or overwrite a file with content
Params:
  - path: string (required) — absolute file path
  - content: string (required) — file content
  - create_dirs: bool (optional, default=true) — create parent dirs
Description: "Write content to a file. Creates missing directories."
Returns: JSON with {path, bytes_written, created}
Errors: permission_denied, disk_full, invalid_path
```

#### Tool 3: `search_code`
```
Purpose: Grep-like code search with regex and file filtering
Params:
  - query: string (required) — regex pattern
  - path: string (optional, default=".") — directory to search
  - file_pattern: string (optional, default="*") — glob like "*.py"
  - context_lines: int (optional, default=2) — lines around match
  - max_results: int (optional, default=100) — max matches
  - include_binary: bool (optional, default=false)
Description: "Search code files with regex. Returns path, line numbers, and matched lines."
Returns: JSON array of {path, line, content, line_count}
Errors: search_timeout, permission_denied, invalid_regex
```

#### Tool 4: `execute_command`
```
Purpose: Run shell commands in a sandboxed environment
Params:
  - command: string (required) — shell command to run
  - cwd: string (optional) — working directory
  - timeout_secs: int (optional, default=60) — max execution time
  - environment: dict (optional) — env vars to set
  - max_output_kb: int (optional, default=256) — truncate stdout/stderr
Description: "Execute a shell command. Returns exit code, stdout, stderr."
Returns: JSON with {exit_code, stdout, stderr, duration_ms}
Errors: timeout, non_zero_exit, permission_denied, oom_killed
```

### MCP Server Implementation Pattern

```python
from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP("hermes-coding-mcp")

@mcp.tool()
async def read_file(
    path: str = Field(description="Absolute file path to read"),
    start_line: int = Field(default=1, ge=1),
    end_line: int | None = None,
    max_lines: int = Field(default=500, ge=1, le=5000),
) -> str:
    """Read a file's contents with optional line range."""
    try:
        p = Path(path)
        if not p.exists():
            return json.dumps({"isError": True, "error": "file_not_found", "path": path})
        lines = p.read_text().splitlines()
        total = len(lines)
        start_idx = min(start_line - 1, total)
        end_idx = min(end_line or start_line + max_lines - 1, total)
        selected = lines[start_idx:end_idx]
        return json.dumps({
            "path": str(p),
            "lines": selected,
            "total_lines": total,
            "truncated": end_idx < total
        })
    except PermissionError:
        return json.dumps({"isError": True, "error": "permission_denied", "path": path})
    except Exception as e:
        return json.dumps({"isError": True, "error": str(e), "path": path})
```

### Error Handling Strategy

Every tool returns JSON with consistent structure:
```json
{"isError": false, "data": {...}}
{"isError": true, "error": "error_code", "message": "...", "recoverable": bool}
```

Error codes: `file_not_found`, `permission_denied`, `invalid_regex`, `timeout`, `non_zero_exit`, `read_timeout`, `disk_full`, `invalid_path`

Retryable errors: `timeout`, `transient_failure` — agent should retry 3x before escalating

---

## Layer 2 — ReAct Loop Pattern

### Flow Diagram (Text-Based)

```
                    ┌─────────────────────────┐
                    │   ORCHESTRATOR          │
                    │   (Agents Orchestrator) │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  THINK: Analyze task    │
                    │  "What do I need to do?"│
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  ROUTE: Pick tool       │
                    │  (embeddings router)    │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
    ┌─────▼─────┐        ┌─────▼─────┐        ┌─────▼─────┐
    │ READ/WRITE│        │ SEARCH    │        │ EXECUTE   │
    │  (file)   │        │ (code)    │        │ (shell)   │
    └─────┬─────┘        └─────┬─────┘        └─────┬─────┘
          │                     │                     │
          └─────────────────────┼─────────────────────┘
                    ┌───────────▼─────────────┐
                    │  OBSERVE: Get result     │
                    │  Parse output, check err │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  DECIDE: Success?        │
                    │  - Yes: next step or done │
                    │  - No: retry (max 3)      │
                    │  - Fatal: escalate        │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  LOOP or EXIT            │
                    └─────────────────────────┘
```

### ReAct State Machine

```python
class ReActState:
    task: str                          # Current task description
    history: list[ToolCall]            # All tool calls so far
    retries: int = 0                   # Current retry count
    MAX_RETRIES: int = 3
    
    def step(self, tool_result: ToolResult) -> Action:
        if tool_result.is_error and tool_result.recoverable:
            if self.retries < self.MAX_RETRIES:
                self.retries += 1
                return RETRY_SAME_TOOL
            else:
                return ESCALATE
        elif self.task_complete(tool_result):
            return DONE
        else:
            self.retries = 0
            return DECIDE_NEXT_TOOL
```

### Orchestrator Prompt Pattern (from nauvalazhar)

The orchestrator uses a structured system prompt:

```
You are a coding agent. You operate in a ReAct loop:
1. THINK: Analyze what the task requires
2. ROUTE: Select the appropriate tool
3. ACT: Call the tool with parameters
4. OBSERVE: Parse the result
5. DECIDE: Continue, retry, or finish

Available tools:
- read_file(path, start_line, end_line): Read file contents
- write_file(path, content): Write/create files
- search_code(query, path, file_pattern): Search code
- execute_command(command, cwd, timeout_secs): Run shell commands

Think carefully about each step. If a tool fails, check if it's
recoverable (timeout, transient) and retry, or escalate if fatal.
```

---

## Layer 2 — Embeddings-Based Tool Router

### Why Embeddings for Routing?

Based on morphllm.com research, the tool router picks the right tool for a given task. Rather than hardcoded rules, we use embedding similarity between:
- Task description (from user prompt)
- Tool descriptions + usage patterns

### Embedding Model Choice

**Model:** `sentence-transformers/all-MiniLM-L6-v2`
- 384 dimensions, fast (12ms per encode on CPU)
- Good performance on code/search tasks
- Can run locally, no API calls needed

Alternative (if available): `BAAI/bge-base-en-v1.5` (larger, more accurate)

### Indexing Strategy

```
Tool Index (built at startup):
  tool_name: "read_file"
  description: "Read file contents with line range support"
  params_schema: {path, start_line, end_line, max_lines}
  usage_examples: [
    "read the config file",
    "show me the main.py contents",
    "cat /etc/hosts"
  ]
  embedded_vector: [0.123, -0.456, ...]  # 384-dim

For search: same approach for search_code tool.
```

### Routing Algorithm

```python
def route_task(task_description: str, tools: list[Tool]) -> Tool:
    """Route a task to the most appropriate tool using embeddings."""
    task_embedding = embed_model.encode(task_description)
    
    scores = []
    for tool in tools:
        # Cosine similarity between task and tool description
        similarity = cosine_similarity(task_embedding, tool.embedding)
        
        # Boost score if task contains tool name or common aliases
        name_boost = 0.2 if tool.name in task_description.lower() else 0.0
        
        # Boost for matching usage patterns
        pattern_boost = max(
            0.1 for pattern in tool.usage_patterns 
            if pattern in task_description.lower()
        )
        
        scores.append((tool, similarity + name_boost + pattern_boost))
    
    best_tool, score = max(scores, key=lambda x: x[1])
    
    # Fallback threshold: if best score < 0.3, return search_code (most general)
    if score < 0.3:
        return tools_by_name["search_code"]  # safe default
    
    return best_tool
```

### Tool Description Embeddings (Pre-computed)

At `hermes-coding-mcp` startup, embed each tool's description once and cache:

```python
TOOL_EMBEDDINGS = {
    "read_file": embed("Read a file's contents. Params: path, start_line, end_line."),
    "write_file": embed("Write or create a file with content. Params: path, content."),
    "search_code": embed("Search code using regex patterns. Returns matching lines with context."),
    "execute_command": embed("Execute a shell command and return stdout/stderr/exit code."),
}
```

### Integration with hermes-agent

The tool router lives in the orchestrator but is called before each tool selection:

```
orchestrator.py
  ├── _route_tool(task: str) -> Tool  [embeddings-based]
  ├── _call_tool(tool, params) -> Result  [MCP call]
  ├── _handle_error(result) -> Retry|Escalate
  └── _check_quality_gates(result) -> Pass|Fail
```

---

## Next Steps for Implementation

### Phase 1a: Build hermes-coding-mcp (Layer 1)
- [ ] Create `hermes-coding-mcp/` directory
- [ ] Implement `read_file` tool with error handling
- [ ] Implement `write_file` tool with error handling  
- [ ] Implement `search_code` tool with error handling
- [ ] Implement `execute_command` tool with timeout and sandbox
- [ ] Write unit tests for each tool
- [ ] Test with real agent (nauvalazhar pattern)

### Phase 1b: Design ReAct Loop (Layer 2)
- [ ] Define ReActState class with retry logic
- [ ] Create orchestrator system prompt template
- [ ] Implement tool router (embeddings-based)
- [ ] Wire into hermes-agent (orchestrator subagent)

### Phase 1c: Integration Testing
- [ ] End-to-end test: task → route → call → observe → decide
- [ ] Test error recovery: simulate timeout, verify 3 retries
- [ ] Test tool router: verify correct tool picked for 10 sample tasks

---

## File Structure

```
hermes-coding-mcp/
├── __init__.py
├── server.py          # FastMCP server, 4 tools
├── tools/
│   ├── __init__.py
│   ├── read_file.py
│   ├── write_file.py
│   ├── search_code.py
│   └── execute_command.py
├── router/
│   ├── __init__.py
│   ├── embeddings.py   # Tool embedding + cosine similarity
│   └── router.py       # route_task() function
└── tests/
    ├── test_read_file.py
    ├── test_write_file.py
    ├── test_search_code.py
    ├── test_execute_command.py
    └── test_router.py
```

---

## Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Transport | stdio | Matches hermes-agent pattern, simple for local use |
| Tool framework | FastMCP (Python) | Already used in mcp_serve.py, familiar to team |
| Embedding model | all-MiniLM-L6-v2 | Fast, local, good for code tasks |
| Error format | JSON with isError flag | Structured, agent-parseable |
| Retry strategy | 3x max, then escalate | Per nauvalazhar pattern |
| Router fallback | search_code on low confidence | Most general tool, safe default |

---

## References

- nauvalazhar/build-your-own-ai-coding-agent: ReAct loop, tool patterns
- morphllm.com: 4-tool minimum, edit format matters
- kevinrgu/autoagent: Docker-based harness, infrastructure-first
- hermes-agent/tools/mcp_tool.py: Existing MCP client (reference)
- hermes-agent/mcp_serve.py: Existing MCP server (reference pattern)