#!/usr/bin/env python3
"""
Extract DSH sessions and dump them into OpenMemory.

Each session gets stored as a memory with:
- Session ID and timestamp
- Session title
- User's original request (first meaningful user message)
- Key assistant decisions/actions
- Files changed (from tool results)
- Session summary
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

SESSIONS_DIR = Path("/root/.dsh/sessions/--root-.hermes--")
OPENMEMORY_URL = "http://localhost:8080/mcp"
OPENMEMORY_KEY = "dev-key-123"
MAX_CONTENT_LEN = 4000  # Max chars per memory entry
INTER_CALL_DELAY = 1.0  # Seconds between store calls (rate limit: 100/min)


def mcp_call(method, params=None, retries=5):
    """Make a JSON-RPC call to OpenMemory with retry on 429."""
    for attempt in range(retries):
        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": method,
            "params": params or {},
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            OPENMEMORY_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "x-api-key": OPENMEMORY_KEY,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode()
                # Handle SSE format
                if body.startswith("event:"):
                    for line in body.split("\n"):
                        if line.startswith("data:"):
                            return json.loads(line[5:].strip())
                return json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = min(2 ** attempt * 2, 30)  # 2, 4, 8, 16, 30s
                print(f"  Rate limited, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"  MCP call failed: HTTP {e.code}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"  MCP call failed: {e}", file=sys.stderr)
            return None
    print(f"  MCP call failed after {retries} retries", file=sys.stderr)
    return None


def decompress_session(session_path):
    """Decompress a zstd session file and return list of JSON objects."""
    try:
        result = subprocess.run(
            ["zstd", "-d", "-c", str(session_path)],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            return []
        messages = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    messages.append(json.loads(line))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
        return messages
    except Exception as e:
        print(f"  Decompress failed: {e}", file=sys.stderr)
        return []


def extract_user_text(msg):
    """Extract text content from a user message."""
    content = msg.get("data", {}).get("content", [])
    if not isinstance(content, list):
        return ""
    texts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "")
            # Skip system reminders and runtime context
            if text.startswith("<system-reminder>") or text.startswith("Current runtime context"):
                continue
            if "AGENTS.md" in text[:200]:
                continue
            texts.append(text)
    return "\n".join(texts).strip()


def extract_assistant_text(msg):
    """Extract text from an assistant message."""
    content = msg.get("data", {}).get("content", [])
    if not isinstance(content, list):
        return ""
    texts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            texts.append(block.get("text", ""))
    return "\n".join(texts).strip()


def extract_tool_files(messages):
    """Extract file operations from tool calls/results."""
    files_changed = set()
    for msg in messages:
        if msg.get("type") == "tool/call":
            data = msg.get("data", {})
            # Extract file paths from tool calls
            args = data.get("arguments", {})
            if not isinstance(args, dict):
                continue
            for key in ("file_path", "path", "pattern"):
                val = args.get(key)
                if val and isinstance(val, str) and ("/" in val or val.endswith(".py")):
                    files_changed.add(val)
            name = data.get("name", "")
            if name in ("write", "edit"):
                fp = args.get("file_path", "")
                if fp and isinstance(fp, str):
                    files_changed.add(fp)
    return sorted(files_changed)[:20]  # Cap at 20 files


def extract_tool_calls_summary(messages):
    """Extract a summary of tool calls made."""
    tool_counts = {}
    for msg in messages:
        if msg.get("type") == "tool/call":
            name = msg.get("data", {}).get("name", "unknown")
            tool_counts[name] = tool_counts.get(name, 0) + 1
    # Sort by count descending, return top 10
    sorted_tools = sorted(tool_counts.items(), key=lambda x: -x[1])
    return [f"{name}({count})" for name, count in sorted_tools[:10]]


def extract_subagent_delegations(messages):
    """Extract subagent delegations."""
    delegations = []
    for msg in messages:
        if msg.get("type") == "tool/call":
            data = msg.get("data", {})
            name = data.get("name", "")
            if name in ("subagent", "subagent_fork", "ralph"):
                args = data.get("arguments", {})
                if isinstance(args, dict):
                    desc = args.get("description", args.get("objective", "unknown"))
                    delegations.append(str(desc)[:100])
    return delegations


def format_session_memory(session_data, messages):
    """Format a session into a memory entry."""
    session_id = session_data.get("id", "unknown")
    created_at = session_data.get("createdAt", 0)
    cwd = session_data.get("cwd", "")
    preset = session_data.get("agentPreset", "unknown")

    # Convert timestamp
    if created_at:
        dt = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
        date_str = dt.strftime("%Y-%m-%d %H:%M UTC")
    else:
        date_str = "unknown date"

    # Get title
    title = ""
    for msg in messages:
        if msg.get("type") == "session/title":
            title = msg.get("data", {}).get("title", "")
            break

    # Get user messages (skip system noise)
    user_texts = []
    for msg in messages:
        if msg.get("type") == "user/message":
            text = extract_user_text(msg)
            if text and len(text) > 10:  # Skip trivial
                user_texts.append(text)

    # Get assistant messages (first few)
    assistant_texts = []
    count = 0
    for msg in messages:
        if msg.get("type") == "assistant/message":
            text = extract_assistant_text(msg)
            if text and len(text) > 20:
                assistant_texts.append(text[:500])
                count += 1
                if count >= 3:
                    break

    # Get files changed
    files = extract_tool_files(messages)

    # Get tool usage
    tools_used = extract_tool_calls_summary(messages)

    # Get subagent delegations
    delegations = extract_subagent_delegations(messages)

    # Build memory content
    parts = []
    parts.append(f"## DSH Session: {title or 'Untitled'}")
    parts.append(f"- **ID:** {session_id}")
    parts.append(f"- **Date:** {date_str}")
    parts.append(f"- **Working Dir:** {cwd}")
    parts.append(f"- **Agent Preset:** {preset}")
    parts.append("")

    if user_texts:
        parts.append("### User Request")
        # Take first meaningful user message, truncate
        first_user = user_texts[0][:1000]
        parts.append(first_user)
        parts.append("")

    if assistant_texts:
        parts.append("### Key Actions/Decisions")
        for at in assistant_texts[:2]:
            parts.append(f"- {at[:400]}")
        parts.append("")

    if files:
        parts.append("### Files Changed")
        for f in files:
            parts.append(f"- `{f}`")
        parts.append("")

    if tools_used:
        parts.append(f"### Tools Used: {', '.join(tools_used)}")

    if delegations:
        parts.append("### Subagent Delegations")
        for d in delegations:
            parts.append(f"- {d}")

    content = "\n".join(parts)
    if len(content) > MAX_CONTENT_LEN:
        content = content[:MAX_CONTENT_LEN] + "\n... (truncated)"

    return content, title, date_str


def store_memory(content, tags, title="", session_id="", date_str=""):
    """Store a memory entry in OpenMemory."""
    metadata = {}
    if session_id:
        metadata["dsh_session_id"] = session_id
    if date_str:
        metadata["session_date"] = date_str
    if title:
        metadata["session_title"] = title

    result = mcp_call("tools/call", {
        "name": "openmemory_store_project",
        "arguments": {
            "content": content,
            "project_id": "hermes",
            "tags": tags,
            "metadata": metadata,
        }
    })
    return result


def main():
    # Parse args
    only_ids = set()
    if len(sys.argv) > 1 and sys.argv[1] == "--only":
        only_ids = set(sys.argv[2:])
        print(f"Processing only {len(only_ids)} specified sessions")

    # Discover all sessions
    session_dirs = sorted(SESSIONS_DIR.iterdir())
    session_dirs = [d for d in session_dirs if d.is_dir()]

    if only_ids:
        session_dirs = [d for d in session_dirs if d.name in only_ids]

    print(f"Found {len(session_dirs)} DSH sessions")
    print(f"OpenMemory URL: {OPENMEMORY_URL}")
    print()

    # Test OpenMemory connectivity
    test = mcp_call("tools/call", {
        "name": "openmemory_query",
        "arguments": {"query": "test", "k": 1}
    })
    if test is None:
        print("ERROR: Cannot reach OpenMemory. Aborting.")
        sys.exit(1)
    print("OpenMemory connected OK")
    print()

    success = 0
    failed = 0
    skipped = 0

    for i, session_dir in enumerate(session_dirs):
        session_file = session_dir / "session.jsonl.zstd"
        if not session_file.exists():
            print(f"[{i+1}/{len(session_dirs)}] SKIP {session_dir.name} (no session file)")
            skipped += 1
            continue

        print(f"[{i+1}/{len(session_dirs)}] Processing {session_dir.name}...")

        # Decompress
        messages = decompress_session(session_file)
        if not messages:
            print(f"  SKIP: no messages")
            skipped += 1
            continue

        # Get session metadata
        session_data = {}
        for msg in messages:
            if msg.get("type") == "session":
                session_data = msg
                break

        if not session_data:
            print(f"  SKIP: no session metadata")
            skipped += 1
            continue

        # Skip current (active) session
        if session_data.get("id") == os.environ.get("DSH_SESSION_ID"):
            print(f"  SKIP: active session")
            skipped += 1
            continue

        # Format
        try:
            content, title, date_str = format_session_memory(session_data, messages)
        except Exception as e:
            print(f"  FAIL: format error: {e}")
            failed += 1
            continue
        tags = ["dsh-session", "hermes"]
        if title:
            # Add first few words as tag
            title_words = title.split()[:3]
            tags.extend([w.lower().strip(",.") for w in title_words if len(w) > 2])

        # Store
        try:
            result = store_memory(content, tags, title, session_data.get("id", ""), date_str)
            if result and not result.get("error"):
                success += 1
                print(f"  OK: stored ({len(content)} chars)")
            else:
                failed += 1
                err = result.get("error", "unknown") if result else "no response"
                print(f"  FAIL: {err}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: store error: {e}")

        # Rate limit - don't hammer OpenMemory
        time.sleep(INTER_CALL_DELAY)

    print()
    print(f"=== DONE ===")
    print(f"  Success: {success}")
    print(f"  Failed:  {failed}")
    print(f"  Skipped: {skipped}")
    print(f"  Total:   {len(session_dirs)}")


if __name__ == "__main__":
    main()
