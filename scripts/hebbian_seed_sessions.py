#!/usr/bin/env python3
"""
Hebbian Retroactive Seeder — seeds the associative memory network
from historical Hermes sessions and decisions logs.

Usage:
  python3 scripts/hebbian_seed_sessions.py [batch_size]

batch_size: number of sessions per batch (default 50)
             run in chunks to avoid memory issues
"""

import json
import os
import re
import sys
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

HERMES_DIR = Path("/root/.hermes")
SESSIONS_DIR = HERMES_DIR / "sessions"
DB_PATH = HERMES_DIR / "brain" / "associative_memory.db"

# Known vocabularies for entity extraction
KNOWN_TOKENS = {
    "BTC", "ETH", "SOL", "SCR", "AVAX", "XRP", "DOGE", "ADA", "DOT", "LINK",
    "UNI", "AAVE", "MKR", "SNX", "UMA", "DYDX", "ZETA", "ORDI", "BIGTIME",
    "MET", "PENDLE", "SAND", "AXS", "ICP", "ETHFI", "SKY", "GMX", "LDO",
    "CRV", "FXS", "APE", "INJ", "TIA", "SEI", "WIF", "PEPE", "SHIB", "FLOKI",
    "ARB", "OP", "MATIC", "POL", "GALA", "ENJ", "MANA", "RNDR", "VET",
    "THETA", "ALGO", "FTM", "NEAR", "APT", "SUI", "TON", "XLM", "HBAR",
    "ORDI", "SATS", "RUNE", "THALES",
}

KNOWN_SKILLS = {
    "brain-memory", "associative-recall", "code-review", "code-audit", "wasp",
    "pipeline-analyst", "pipeline-review", "signal-flip", "clear-all", "sync-trades",
    "sync-open-trades", "stale-trades", "closed-trades-eval", "blocklist-decision",
    "hermes-session-wrap", "analyze-trades", "prompt-training", "candle-predictor-tuner",
    "full-review", "project-management", "plan", "writing-plans", "systematic-debugging",
    "subagent-driven-development", "brain-memory", "kanban", "github",
    "youtube-watcher", "arbitrage", "heartmula", "excalidraw", "ascii-art",
    "self-improving-agent", "proactive-agent-lite", "kanban-review",
    "signal-compaction", "stale-trades", "clear-all", "fresh-run",
    "prompt-training", "analyze-trades", "full-review", "wasp",
}

KNOWN_INFRA = {
    "Tokyo", "Dallas", "SSH", "nginx", "PostgreSQL", "SQLite", "pgvector",
    "Docker", "systemd", "cron", "uvicorn", "FastMCP", "SSE", "REST", "API",
    "JSON", "SQLite", "systemd", "systemd timer",
}

KNOWN_FILES = {
    "TASKS.md", "PROJECTS.md", "DECISIONS.md", "trading.md", "lessons.md",
    "brain.md", "SOUL.md", "SOPs.md", "CONTEXT.md", "ideas.md",
    "signal_gen.py", "ai_decider.py", "position_manager.py", "decider_run.py",
    "hebbian_engine.py", "hl-sync-guardian.py", "atrm.py",
}

KNOWN_PROJECTS = {
    "Cascade Flip", "Chart Pattern Recognition", "Signal Quality Improvement",
    "Win Rate Investigation", "Session Checkpoint", "ATR Trailing Stop",
    "Hot-Set Compaction", "Pipeline Health", "Hebbian Memory",
    "Hype Live Trading", "Better Coder", "WASP", "Brain Sync",
}

# ---------------------------------------------------------------------------
# Entity extraction (simplified, fast)
# ---------------------------------------------------------------------------

INLINE_CODE = re.compile(r'`([^`]+)`')
FILE_PATHS = re.compile(r'(?:/root/\.hermes/[^\s`\)\]"\'\\]+|scripts/[^\s`\)\]"\'\\]+)')
BOLD_TEXT = re.compile(r'\*\*([^*]+)\*\*')
ALL_CAPS = re.compile(r'\b([A-Z]{2,10})\b')
LOWER_FILE = re.compile(r'\b([a-z][a-z0-9_-]+\.py)\b')
CAMEL = re.compile(r'\b([A-Z][a-z]+[A-Z][A-Za-z]+)\b')

STOP_WORDS = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'new', 'old', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'now', 'see', 'way', 'who', 'did', 'use', 'this', 'that', 'with', 'from', 'they', 'will', 'would', 'there', 'their', 'what', 'been', 'when', 'more', 'have', 'some', 'into', 'only', 'other', 'then', 'than', 'also', 'back', 'just', 'over', 'such', 'even', 'most', 'your', 'every', 'after', 'before', 'because', 'between', 'through'}

def infer_label(candidate: str) -> str:
    c = candidate.strip()
    c_lower = c.lower()
    if c in KNOWN_TOKENS:
        return "token"
    if c_lower in [s.lower() for s in KNOWN_SKILLS]:
        return "skill"
    if c in KNOWN_INFRA:
        return "infra"
    if c in KNOWN_FILES:
        return "file"
    if c in KNOWN_PROJECTS:
        return "project"
    if c_lower.endswith('.py'):
        return "file"
    if '/' in c:
        return "file"
    return "concept"

def extract_entities(text: str) -> list[tuple[str, str]]:
    """Fast entity extraction, returns list of (concept, label_type)."""
    found = []
    seen = set()

    for m in INLINE_CODE.finditer(text):
        v = m.group(1).strip()
        if len(v) > 1 and v not in seen and v.lower() not in STOP_WORDS:
            seen.add(v)
            found.append((v, infer_label(v)))

    for m in FILE_PATHS.finditer(text):
        v = m.group(0).strip()
        if v not in seen:
            seen.add(v)
            found.append((v, "file"))

    for m in BOLD_TEXT.finditer(text):
        v = m.group(1).strip()
        if len(v) > 2 and v not in seen and v.lower() not in STOP_WORDS:
            seen.add(v)
            found.append((v, infer_label(v)))

    for m in CAMEL.finditer(text):
        v = m.group(1).strip()
        if len(v) > 2 and v not in seen and v.lower() not in STOP_WORDS:
            seen.add(v)
            found.append((v, infer_label(v)))

    for m in ALL_CAPS.finditer(text):
        v = m.group(1).strip()
        if v not in seen and v not in {'API', 'SQL', 'SSH', 'URL', 'TCP', 'UDP', 'HTTP', 'HTTPS', 'JSON', 'XML', 'CSV', 'IDE', 'GPT', 'LLM', 'CLI', 'PID', 'UID', 'GID', 'UTC', 'EST', 'PST'}:
            seen.add(v)
            found.append((v, infer_label(v)))

    for m in LOWER_FILE.finditer(text):
        v = m.group(1).strip()
        if v not in seen:
            seen.add(v)
            found.append((v, "file"))

    return found

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def node_id(conn, name: str, label_type: str) -> int:
    cur = conn.execute(
        "SELECT id FROM concept_nodes WHERE name = ?",
        (name,)
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO concept_nodes (name, label_type, created_at, last_seen) VALUES (?, ?, ?, ?)",
        (name, label_type, int(time.time()), int(time.time()))
    )
    return cur.lastrowid

def learn_pair(conn, a: str, lt_a: str, b: str, lt_b: str):
    id_a = node_id(conn, a, lt_a)
    id_b = node_id(conn, b, lt_b)
    if id_a == id_b:
        return

    # Check existing synapse
    cur = conn.execute(
        "SELECT id, weight, co_occurrences FROM synapse_weights WHERE (concept_a_id = ? AND concept_b_id = ?) OR (concept_a_id = ? AND concept_b_id = ?)",
        (id_a, id_b, id_b, id_a)
    )
    row = cur.fetchone()
    now = int(time.time())

    if row:
        new_weight = min(row[1] + 1.0, 100.0)
        new_count = row[2] + 1
        conn.execute(
            "UPDATE synapse_weights SET weight = ?, co_occurrences = ?, last_updated = ? WHERE id = ?",
            (new_weight, new_count, now, row[0])
        )
    else:
        conn.execute(
            "INSERT INTO synapse_weights (concept_a_id, concept_b_id, weight, co_occurrences, last_updated) VALUES (?, ?, 1.0, 1, ?)",
            (id_a, id_b, now)
        )

# ---------------------------------------------------------------------------
# Session file parsing
# ---------------------------------------------------------------------------

def parse_session_file(fp: Path) -> list[tuple[str, str]]:
    """Extract (role, content) pairs from a session dump file."""
    try:
        with open(fp) as f:
            data = json.load(f)
    except Exception:
        return []

    body = data.get("request", {}).get("body", {})
    if isinstance(body, dict):
        messages = body.get("messages", [])
    elif isinstance(body, list):
        messages = body
    else:
        return []

    result = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role in ("user", "assistant", "system") and isinstance(content, str) and content.strip():
            result.append((role, content.strip()[:3000]))  # cap per message
    return result

# ---------------------------------------------------------------------------
# Main seeder
# ---------------------------------------------------------------------------

def seed_sessions(batch_size: int = 50):
    """Seed from all session dumps in batches."""
    session_files = sorted(SESSIONS_DIR.glob("request_dump_*.json"), reverse=True)
    print(f"Found {len(session_files)} session files")

    conn = get_connection()
    total_sessions = 0
    total_pairs = 0
    total_entities = 0

    for batch_start in range(0, len(session_files), batch_size):
        batch = session_files[batch_start:batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        print(f"\nBatch {batch_num}: processing {len(batch)} sessions...")

        for fp in batch:
            messages = parse_session_file(fp)
            if not messages:
                continue

            # Learn within each message
            for role, content in messages:
                if role in ("user", "assistant"):  # skip system prompts
                    entities = extract_entities(content)
                    if len(entities) < 2:
                        continue

                    concepts = [e[0] for e in entities]
                    ltypes = [e[1] for e in entities]
                    for i in range(len(concepts)):
                        for j in range(i + 1, len(concepts)):
                            learn_pair(conn, concepts[i], ltypes[i], concepts[j], ltypes[j])
                            total_pairs += 1
                    total_entities += len(entities)
                    total_sessions += 1

            # Commit after every file to avoid huge transactions
            conn.commit()

        print(f"  Batch {batch_num} done: {total_sessions} sessions, {total_entities} entities, {total_pairs} pairs")

    conn.close()
    print(f"\n=== Session Seeding Complete ===")
    print(f"Sessions processed: {total_sessions}")
    print(f"Entities extracted: {total_entities}")
    print(f"Pairs learned: {total_pairs}")

def seed_decisions_log():
    """Seed from trading decisions log."""
    decisions_path = HERMES_DIR / "wandb-local" / "decisions.jsonl"
    if not decisions_path.exists():
        print("No decisions.jsonl found")
        return 0

    conn = get_connection()
    count = 0

    with open(decisions_path) as f:
        for line in f:
            try:
                d = json.loads(line)
                token = d.get("top_token", "")
                regime = d.get("regime", "")
                direction = d.get("direction", "")
                decision = d.get("decision", "")
                reason = d.get("reason", "")

                # Build entity list
                parts = []
                if token:
                    parts.append((token, "token"))
                if regime:
                    parts.append((regime, "concept"))
                if direction:
                    parts.append((direction, "concept"))
                if decision:
                    parts.append((decision, "concept"))

                # Add entities from reason text
                if reason:
                    parts.extend(extract_entities(reason[:500]))

                # Deduplicate
                seen = {}
                for name, lt in parts:
                    if name not in seen:
                        seen[name] = lt

                concepts = list(seen.keys())
                ltypes = [seen[c] for c in concepts]

                for i in range(len(concepts)):
                    for j in range(i + 1, len(concepts)):
                        learn_pair(conn, concepts[i], ltypes[i], concepts[j], ltypes[j])
                        count += 1

            except Exception:
                continue

    conn.commit()
    conn.close()
    return count

if __name__ == "__main__":
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 100

    print("=== Hebbian Retroactive Seeder ===")
    print(f"Batch size: {batch_size}")
    print()

    # Seed from sessions
    print("[Sessions]")
    seed_sessions(batch_size)

    # Seed from decisions log
    print("\n[Decisions Log]")
    n = seed_decisions_log()
    print(f"Learned {n} pairs from decisions log")

    # Final stats
    conn = get_connection()
    stats = conn.execute("SELECT COUNT(*), SUM(weight), COUNT(DISTINCT label_type) FROM concept_nodes").fetchone()
    synapse_count = conn.execute("SELECT COUNT(*) FROM synapse_weights").fetchone()[0]
    conn.close()

    print(f"\n=== Final Network State ===")
    print(f"Nodes: {stats[0]} | Total weight: {stats[1]:.0f} | Label types: {stats[2]}")
    print(f"Synapses: {synapse_count}")