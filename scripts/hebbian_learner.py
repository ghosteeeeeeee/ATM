#!/usr/bin/env python3
"""
Hebbian Network Seeder — bootstraps initial synapses from existing brain files.

Scans all brain/*.md files and extracts co-occurring concepts, seeding the
associative memory network so it's not empty on day one.

Run once to populate initial links, then let natural usage grow the network.
"""

import re
import sys
import os
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/scripts')
from hebbian_engine import HebbianEngine

BRAIN_DIR = Path("/root/.hermes/brain")
SKILLS_DIR = Path("/root/.hermes/skills")

# Label type inference helpers
KNOWN_TOKENS = {"BTC", "ETH", "SOL", "SCR", "AVAX", "XRP", "DOGE", "ADA", "DOT", "LINK", "UNI", "AAVE", "MKR", "SNX", "UMA", "DYDX", "ZETA", "ORDI", "BIGTIME", "MET", "PENDLE", "SAND", "AXS", "ICP", "ETHFI", "SKY", "GMX", "LDO", "CRV", "FXS", "APE"}
KNOWN_SKILLS = {
    "brain-memory", "associative-recall", "code-review", "code-audit", "wasp", "pipeline-analyst",
    "pipeline-review", "signal-flip", "clear-all", "sync-trades", "sync-open-trades",
    "stale-trades", "closed-trades-eval", "blocklist-decision", "hermes-session-wrap",
    "analyze-trades", "prompt-training", "candle-predictor-tuner", "full-review",
    "project-management", "plan", "writing-plans", "systematic-debugging",
    "test-driven-development", "subagent-driven-development"
}
KNOWN_INFRA = {"Tokyo", "Dallas", "SSH", "nginx", "systemd", "PostgreSQL", "SQLite", "pgvector"}
KNOWN_FILES = {"TASKS.md", "PROJECTS.md", "DECISIONS.md", "trading.md", "lessons.md", "brain.md", "SOUL.md", "SOPs.md", "CONTEXT.md", "ideas.md"}

def infer_label(name: str) -> str:
    if name in KNOWN_TOKENS:
        return "token"
    if name in KNOWN_SKILLS or name.startswith("skill:"):
        return "skill"
    if name in KNOWN_INFRA:
        return "infra"
    if name in KNOWN_FILES:
        return "file"
    if name.startswith("scripts/") or name.endswith(".py"):
        return "file"
    if name.startswith("## ") or name.startswith("### "):
        return "concept"
    return "concept"

def extract_concepts(text: str) -> list:
    """Extract potential concept names from markdown text."""
    concepts = []
    
    # Headers: ## Project Name, ### Task Name
    headers = re.findall(r'^#{2,3}\s+(.+)$', text, re.MULTILINE)
    for h in headers:
        clean = re.sub(r'\[.*?\]', '', h).strip()  # Remove [links]
        clean = re.sub(r'[`*_~]', '', clean)
        if len(clean) > 2 and len(clean) < 80:
            concepts.append(clean)
    
    # Inline code: `something`
    codes = re.findall(r'`([^`]+)`', text)
    for c in codes:
        if len(c) > 2 and not c.startswith("$"):
            concepts.append(c)
    
    # Bold/italic: **something** or *something*
    bolds = re.findall(r'\*\*([^*]+)\*\*', text)
    for b in bolds:
        if len(b) > 2:
            concepts.append(b)
    
    # File paths: /root/.hermes/... or scripts/...
    paths = re.findall(r'(?:/root/\.hermes/[^\s`\)]+|scripts/[^\s`\)]+)', text)
    for p in paths:
        concepts.append(p)
    
    # Known tokens in all-caps context
    tokens = re.findall(r'\b([A-Z]{2,6})\b', text)
    for t in tokens:
        if t in KNOWN_TOKENS:
            concepts.append(t)
    
    # Skill references: skill:name or "skill-name"
    skill_refs = re.findall(r'(?:skill[:\-]?\s*)?["\']?([a-z\-]{3,30})["\']?(?:\s+skill)?', text, re.IGNORECASE)
    for s in skill_refs:
        if s.lower() in [x.lower() for x in KNOWN_SKILLS]:
            concepts.append(s.lower().replace(" ", "-"))
    
    return concepts

def normalize_concept(name: str) -> str:
    """Normalize concept name for deduplication."""
    name = name.strip()
    name = re.sub(r'\[.*?\]', '', name)
    name = re.sub(r'[`*_~<>]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def seed_from_file(engine: HebbianEngine, filepath: Path, label: str = "concept"):
    """Parse a file, extract concepts, learn all pairs within it."""
    if not filepath.exists():
        print(f"  SKIP (not found): {filepath}")
        return 0

    text = filepath.read_text()
    raw_concepts = extract_concepts(text)
    concepts = []
    seen = set()
    for c in raw_concepts:
        norm = normalize_concept(c)
        if norm and len(norm) > 1 and norm not in seen:
            seen.add(norm)
            lt = infer_label(norm)
            concepts.append((norm, lt))

    if len(concepts) < 2:
        print(f"  SKIP (<2 concepts): {filepath.name}")
        return 0

    count = 0
    for i in range(len(concepts)):
        for j in range(i + 1, len(concepts)):
            a, lt_a = concepts[i]
            b, lt_b = concepts[j]
            engine.learn_pair(a, b, lt_a, lt_b)
            count += 1

    print(f"  {filepath.name}: {len(concepts)} concepts, {count} pairs")
    return count

def main():
    print("=== Hebbian Network Seeder ===")
    print(f"Brain dir: {BRAIN_DIR}")
    print()

    # Wipe existing data for clean seed
    engine = HebbianEngine()
    print("Clearing existing network...")
    engine.clear_all()
    
    total_pairs = 0

    # Seed from brain files
    print("\n[Brain Files]")
    for f in sorted(BRAIN_DIR.glob("*.md")):
        total_pairs += seed_from_file(engine, f)

    # Seed from key scripts (only most important ones)
    print("\n[Key Scripts]")
    key_scripts = [
        "/root/.hermes/scripts/signal_gen.py",
        "/root/.hermes/scripts/ai_decider.py",
        "/root/.hermes/scripts/position_manager.py",
        "/root/.hermes/scripts/hl-sync-guardian.py",
        "/root/.hermes/scripts/decider_run.py",
        "/root/.hermes/scripts/hebbian_engine.py",
    ]
    for s in key_scripts:
        total_pairs += seed_from_file(engine, Path(s), "file")

    # Seed from skills
    print("\n[Skills]")
    skill_files = list(SKILLS_DIR.glob("*/SKILL.md"))
    skill_files += list(SKILLS_DIR.glob("*/skills/*/SKILL.md"))
    for sf in skill_files[:20]:  # cap at 20
        total_pairs += seed_from_file(engine, sf)

    print(f"\n=== Seed Complete ===")
    print(f"Total pairs learned: {total_pairs}")
    stats = engine.get_stats()
    print(f"Nodes: {stats['nodes']}")
    print(f"Synapses: {stats['synapses']}")
    print(f"Top edges:")
    for e in stats['top_edges'][:10]:
        print(f"  {e['a']} <-> {e['b']}: {e['weight']:.1f}")

if __name__ == "__main__":
    main()
