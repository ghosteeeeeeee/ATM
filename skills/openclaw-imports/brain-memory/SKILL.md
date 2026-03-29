# Brain Memory Integration

Use this skill when you need to store or retrieve AI memory with semantic search capabilities.

## When to Use

- User asks about prior conversations, decisions, or context
- You need to find related memories by meaning (not just keywords)
- Storing important information that should be retrievable later

## Quick Access (CLI)

A CLI tool is available at: `~/workspace/skills/brain-memory/bin/brain-cli`

```bash
# Get brain stats
brain-cli stats

# Semantic search (AI-powered meaning search)
brain-cli semantic "AI models"

# Text search
brain-cli search "postgres"

# Add a thought
brain-cli add "T prefers MiniMax model" "session"

# Get related thoughts
brain-cli related 1

# Get by tag
brain-cli tags "postgres"
```

## API Direct (Tokyo)

**Base URL:** `http://117.55.192.97:12345/brain/api/`

### Store a Thought

```bash
curl -s -X POST "http://117.55.192.97:12345/brain/api/add" \
  -H "Content-Type: application/json" \
  -d '{"content": "T prefers using MiniMax model", "source": "session", "session_id": "current"}'
```

### Semantic Search (AI-powered meaning search)

```bash
curl -s "http://117.55.192.97:12345/brain/api/semantic?q=model%20preferences"
```

### Text Search

```bash
curl -s "http://117.55.192.97:12345/brain/api/search?q=MiniMax"
```

### Get Related Thoughts

```bash
curl -s "http://117.55.192.97:12345/brain/api/related/1"
```

### Get Stats

```bash
curl -s "http://117.55.192.97:12345/brain/api/stats"
```

## Usage in Sessions

1. **Before answering** questions about prior work, decisions, or context:
   - First try the built-in `memory_search` tool
   - For AI-powered semantic search, use `brain-cli semantic "query"`

2. **After important conversations:**
   - Store key decisions, preferences, or context to Brain
   - Include source info (e.g., "session:2026-03-04")

3. **For complex queries:**
   - Use semantic search to find related memories by meaning

## Notes

- Brain uses pgvector for semantic similarity search
- Qwen extracts metadata (topics, entities, sentiment) automatically
- Each thought gets a unique ID for linking related concepts
- CLI tunnels through SSH to reach Tokyo's local API
