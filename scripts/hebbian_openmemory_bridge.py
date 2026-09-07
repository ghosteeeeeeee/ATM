#!/usr/bin/env python3
"""
Hebbian–OpenMemory Bridge

Queries OpenMemory for recent entries, extracts entities, and feeds
co-occurring pairs to the HebbianEngine. Replaces the dead session
dump learner (request_dump_*.json were never generated).

Usage:
  python3 scripts/hebbian_openmemory_bridge.py [hours_back]
  python3 scripts/hebbian_openmemory_bridge.py --dry-run
"""

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, '/root/.hermes/scripts')
from hebbian_engine import HebbianEngine
from hebbian_entity_extractor import extract_entities
from paths import HERMES_DATA

MCP_URL = "http://localhost:8080/mcp"
API_KEY = "dev-key-123"
PROCESSED_FILE = os.path.join(HERMES_DATA, 'openmemory_bridge_processed.json')
BATCH_SIZE = 20


def _query_openmemory(method, arguments):
    """Call OpenMemory MCP API."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": method, "arguments": arguments},
    }).encode()
    req = urllib.request.Request(
        MCP_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "x-api-key": API_KEY,
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read())
    result = body.get("result", {})
    content = result.get("content", [])
    # Response has multiple text blocks — first is human-readable, second is JSON
    for c in content:
        if c.get("type") == "text":
            text = c["text"]
            # Find the JSON object in this text block
            start = text.find('{"items"')
            if start == -1:
                start = text.find('{')
            if start >= 0:
                try:
                    return json.loads(text[start:])
                except json.JSONDecodeError:
                    continue
    return None


def _load_processed():
    """Load set of already-processed entry IDs."""
    try:
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_processed(ids):
    """Save processed entry IDs (keep last 5000 to avoid unbounded growth)."""
    trimmed = list(ids)[-5000:]
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(trimmed, f)


def _extract_text(entry):
    """Pull readable text from an OpenMemory entry."""
    preview = entry.get('content_preview', '')
    entry_id = entry.get('id', '')
    if not entry_id:
        return preview

    # Fetch full memory by ID
    try:
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "openmemory_get",
                "arguments": {"id": entry_id},
            },
        }).encode()
        req = urllib.request.Request(
            MCP_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "x-api-key": API_KEY,
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
        result = body.get("result", {})
        for c in result.get("content", []):
            if c.get("type") == "text":
                data = json.loads(c["text"])
                content = data.get("content", "")
                if content:
                    return content[:3000]
    except Exception:
        pass
    return preview


def learn_from_openmemory(hours_back=6, dry_run=False):
    """Query OpenMemory for recent entries and learn co-occurrences."""
    cutoff_ms = int((datetime.now(timezone.utc) - timedelta(hours=hours_back)).timestamp() * 1000)
    processed = _load_processed()
    engine = HebbianEngine() if not dry_run else None

    # Fetch recent memories
    data = _query_openmemory("openmemory_list", {"limit": BATCH_SIZE})
    if not data or "items" not in data:
        print("  No entries returned from OpenMemory")
        return 0

    learned = 0
    skipped = 0
    new_ids = set(processed)

    for entry in data["items"]:
        entry_id = entry.get("id", "")
        last_seen = entry.get("last_seen_at", 0)

        if entry_id in processed:
            skipped += 1
            continue
        if last_seen < cutoff_ms:
            skipped += 1
            continue

        text = _extract_text(entry)
        if not text or len(text) < 20:
            skipped += 1
            continue

        entities = extract_entities(text)
        if len(entities) < 2:
            skipped += 1
            new_ids.add(entry_id)
            continue

        if not dry_run:
            concepts = [e[0] for e in entities]
            ltypes = [e[1] for e in entities]
            for i in range(len(concepts)):
                for j in range(i + 1, len(concepts)):
                    engine.learn_pair(concepts[i], concepts[j], ltypes[i], ltypes[j])

        learned += 1
        new_ids.add(entry_id)

    if not dry_run:
        _save_processed(new_ids)

    return learned


def main():
    dry_run = "--dry-run" in sys.argv
    hours_back = 24
    for arg in sys.argv[1:]:
        if arg.isdigit():
            hours_back = int(arg)

    print(f"=== Hebbian–OpenMemory Bridge ===")
    print(f"Hours back: {hours_back}")
    print(f"Dry run: {dry_run}")
    print()

    n = learn_from_openmemory(hours_back, dry_run)
    print(f"Learned from {n} OpenMemory entries")

    if not dry_run:
        engine = HebbianEngine()
        stats = engine.get_stats()
        print(f"Network: {stats['nodes']} nodes, {stats['synapses']} synapses")
        for e in stats.get('top_edges', [])[:5]:
            print(f"  {e['a']} <-> {e['b']}: {e['weight']:.1f}")


if __name__ == "__main__":
    main()
