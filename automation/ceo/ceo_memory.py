#!/usr/bin/env python3
"""
ceo_memory.py — read-side access to OpenMemory for the CEO runners.

Why this exists: the CEO occasionally WRITES to OpenMemory (3 store calls across all
deep runs on record — 3 of 12 runs stored anything) but nothing in its runners or
prompts ever READS it back: zero `openmemory_openmemory_query` calls across all 240
logged tool calls. It therefore rediscovers context from scratch each run — re-grepping
recent_changes.log, re-reading CURRENT.md, re-running the same SQL. That re-discovery
is what a 33-tool-call, 27-minute investigation was made of. This is the read half of
an existing store, not a new subsystem.

Deliberately small and dependency-free (stdlib only): no vector store, no embeddings.
OpenMemory already does the retrieval; we only call it and bound the output so a big
memory cannot blow the CEO's context budget.

Usage:
    ceo_memory.py "ceo recent decisions"
    ceo_memory.py "volatility gate" --max-chars 1200
    ceo_memory.py --check          # probe only: is OpenMemory reachable?

Exit codes: 0 ok, 3 OpenMemory unreachable, 4 bad args, 2 argparse usage error.
"""
import argparse
import json
import sys
import urllib.request

MCP_URL = "http://localhost:8080/mcp"
API_KEY = "dev-key-123"
# Bounded on purpose. The CEO's fixed prompt load is ~12KB; an unbounded memory dump
# would push it toward the compaction threshold, which is the failure mode this whole
# runner stack exists to avoid. Callers should keep results well under this.
DEFAULT_MAX_CHARS = 2000
DEFAULT_TIMEOUT = 15


def query_openmemory(tool, arguments, timeout=DEFAULT_TIMEOUT):
    """Call one OpenMemory MCP tool. Returns the joined text blocks, or raises."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }).encode()
    req = urllib.request.Request(
        MCP_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            # Required: the server 406s without BOTH types. This exact header was
            # missing from the curl examples in AGENTS.md and failed twice in a row
            # before being caught (2026-10-12).
            "Accept": "application/json, text/event-stream",
            "x-api-key": API_KEY,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    # We advertise Accept: application/json, text/event-stream, so the server is
    # entitled to answer either. It answers JSON today; if it ever switches to SSE
    # framing ("data: {...}" lines), a bare json.loads would fail and every call
    # would report rc 3 "unavailable" — the same silent-failure family as the
    # missing-Accept 406 that bit us twice. Handle both.
    text = raw.decode("utf-8", errors="replace")
    stripped = text.lstrip()
    # SSE events may open with an "event:" line before their "data:" line, so match
    # on the presence of a data: line rather than the first non-space character.
    if "\ndata:" in "\n" + stripped or stripped.startswith("data:"):
        # SSE: take the last data line, which carries the final event.
        for line in reversed(text.strip().splitlines()):
            if line.startswith("data:"):
                text = line[len("data:"):].strip()
                break
    body = json.loads(text)
    if "error" in body:
        raise RuntimeError(f"MCP error: {body['error']}")
    content = body.get("result", {}).get("content", [])
    # MCP wraps text in content blocks; join them so nothing is silently dropped.
    return "\n".join(c.get("text", "") for c in content if c.get("type") == "text").strip()


def main():
    ap = argparse.ArgumentParser(description="Read OpenMemory for the CEO.")
    ap.add_argument("query", nargs="?", help="search text")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                    help=f"truncate output to this many chars (default {DEFAULT_MAX_CHARS})")
    ap.add_argument("--tool", default="openmemory_query",
                    help="MCP tool (openmemory_query or openmemory_list)")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--check", action="store_true", help="probe reachability only")
    args = ap.parse_args()

    # Cap the cap. `--max-chars 0` would print only the truncation marker, and a
    # negative value would slice from the wrong end — both defeat the whole point,
    # which is bounding what reaches the CEO's context window.
    if args.max_chars <= 0:
        print(f"[CEO-MEMORY] --max-chars must be > 0 (got {args.max_chars})", file=sys.stderr)
        return 4

    if args.check:
        try:
            query_openmemory("openmemory_list", {}, timeout=args.timeout)
        except Exception as e:
            print(f"[CEO-MEMORY] UNREACHABLE: {e}", file=sys.stderr)
            return 3
        print("[CEO-MEMORY] reachable")
        return 0

    if not args.query and args.tool == "openmemory_query":
        print("[CEO-MEMORY] need a query string, or --tool openmemory_list, or --check",
              file=sys.stderr)
        return 4

    try:
        arguments = {"query": args.query} if args.query else {}
        text = query_openmemory(args.tool, arguments, timeout=args.timeout)
    except Exception as e:
        # Fail SOFT and loudly-but-small: a memory read must never abort a CEO run.
        # The run can proceed without it — it just loses the head start.
        print(f"[CEO-MEMORY] unavailable ({e}) — proceeding without memory context.",
              file=sys.stderr)
        return 3

    if not text:
        print("[CEO-MEMORY] no matching memories.")
        return 0

    if len(text) > args.max_chars:
        text = text[:args.max_chars] + f"\n...[truncated, {len(text)} chars total]"
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
