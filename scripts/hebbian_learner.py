#!/usr/bin/env python3
"""
Hebbian Network Seeder — bootstraps initial synapses from existing brain files.

Scans all brain/*.md files and extracts co-occurring concepts, seeding the
associative memory network so it's not empty on day one.

Run once to populate initial links, then let natural usage grow the network.

Fix 1b: imports infer_label and extract_entities from hebbian_entity_extractor
(single source of truth — Fix 1's HL_COINS filter applies here too). Local
vocabularies and entity extractor deleted.
"""

import re
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/scripts')
from hebbian_engine import HebbianEngine
# Fix 1b: use shared infer_label and HL_COINS for label consistency (single source
# of truth for vocabularies), but use a MARKDOWN-SPECIFIC extractor rather than
# the session-text extract_entities. Reason: extract_entities is tuned for chat
# text (CamelCase, AT_MENTIONS, all-caps coins) and finds too many concepts in
# markdown docs (every .py path, every bold word, every code block) — produces
# 200+ concepts per doc and O(n²) pair explosion. Markdown has its own structure
# (headers, bold, code blocks) that should drive extraction.
from hebbian_entity_extractor import infer_label, HL_COINS  # normalize_concept is internal to entity_extractor

from paths import *
BRAIN_DIR = Path("/root/.hermes/brain")
SKILLS_DIR = Path("/root/.hermes/skills")


def extract_concepts(text: str) -> list:
    """
    Markdown-specific concept extraction for brain docs and SKILL.md files.

    Looks for high-signal structural markers only:
    - Headers: ## Project Name, ### Task Name
    - Inline code: `something`
    - Bold: **something**
    - File paths: /root/.hermes/... or scripts/...
    - ALL_CAPS tokens (must be in HL_COINS or KNOWN_TOKENS to count)

    Deliberately does NOT use extract_entities — that extractor finds too many
    concepts in markdown content (200+ per file) which causes O(n²) pair explosion
    in seed_from_file. Cap is 30 concepts per file via the [:30] slice.
    """
    concepts = []

    # Headers (highest signal — usually project/task names)
    headers = re.findall(r'^#{2,3}\s+(.+)$', text, re.MULTILINE)
    for h in headers:
        clean = re.sub(r'\[.*?\]', '', h).strip()
        clean = re.sub(r'[`*_~]', '', clean)
        if 2 < len(clean) < 80:
            concepts.append((clean, infer_label(clean)))

    # Inline code (file refs, function names, command names)
    # Restrict to single-line inline code only (no newlines) — prevents the
    # bold/capture patterns from pulling in multi-line code blocks.
    codes = re.findall(r'`([^`\n]{2,80})`', text)
    for c in codes:
        if not c.startswith('$'):
            concepts.append((c, infer_label(c)))

    # Bold text (key terms) — restrict to short, single-line content only.
    # Old regex `\*\*([^*]+)\*\*` was greedy and captured multi-line code blocks
    # (e.g. entire hl-sync-guardian.py body) when wrapped in ** for formatting.
    # New regex: max 60 chars, no equals signs (filters out code assignments),
    # no curly braces (filters out dicts/code), no double underscores.
    bolds = re.findall(r'\*\*([^*\n=]{2,60})\*\*', text)
    for b in bolds:
        b = b.strip()
        if b and '{' not in b and '(' not in b:
            concepts.append((b, infer_label(b)))

    # File paths (very high signal for co-occurrence with everything else)
    # Restrictive regex: must end with a recognizable filename (e.g. .py, .json,
    # .md, .db, .log). This stops the regex from capturing huge chunks of code
    # that just happen to contain a path-like substring.
    paths = re.findall(
        r'(?:/root/\.hermes/[^\s`\'")\]]*\.(?:py|json|md|db|log|sh|txt|csv)|'
        r'scripts/[a-zA-Z_][a-zA-Z0-9_]*\.py)',
        text
    )
    for p in paths:
        concepts.append((p, "file"))

    # ALL_CAPS coins (using shared HL_COINS + KNOWN_TOKENS via infer_label).
    # {2,8} matches entity_extractor's ALL_CAPS regex for consistency.
    tokens = re.findall(r'\b([A-Z]{2,8})\b', text)
    for t in tokens:
        lt = infer_label(t)
        if lt == "token":  # only emit if it's a real coin
            concepts.append((t, lt))

    # Cap at 30 concepts per file to keep pair count bounded.
    # With 30 concepts: 30*29/2 = 435 pairs per file (manageable).
    # With 200 concepts (old behavior): 200*199/2 = 19,900 pairs per file (unusable).
    return concepts[:30]


def normalize_concept(name: str) -> str:
    """Normalize concept name for deduplication. Filters out obvious garbage."""
    name = name.strip()
    name = re.sub(r'\[.*?\]', '', name)
    # DON'T strip underscores — they break file paths like signal_compactor.py
    name = re.sub(r'[`*~<>]', '', name)
    name = re.sub(r'\s+', ' ', name)
    name = name.strip()
    # Filter out obvious code/garbage patterns
    if not name or len(name) < 2:
        return ''
    # Code patterns that shouldn't be concepts:
    # - Contains `=` mid-string (assignment)
    # - Starts with digit followed by space (numbered list artifact like "5 for i in range")
    # - Contains `def ` or `class ` (function definitions)
    # - Contains `os.path.` or other module paths
    if '=' in name and ' ' in name:  # mid-string = is code
        return ''
    if re.match(r'^\d+\s', name):  # numbered list residue
        return ''
    if 'def ' in name or 'class ' in name or 'import ' in name:
        return ''
    if name.startswith(('os.', 'sys.', 'json.', 'sqlite3.', 'psycopg2.')):
        return ''
    # Filter out paths that aren't actual files (no extension on final segment)
    if name.startswith('/root/') and '.' not in name.split('/')[-1]:
        return ''
    return name


def seed_from_file(engine: HebbianEngine, filepath: Path, label: str = "concept"):
    """Parse a file, extract concepts, learn all pairs within it."""
    if not filepath.exists():
        print(f"  SKIP (not found): {filepath}")
        return 0

    text = filepath.read_text()
    # Fix 1b: use markdown-specific extractor (capped at 30 concepts)
    raw_concepts = extract_concepts(text)
    concepts = []
    seen = set()
    for name, lt in raw_concepts:
        norm = normalize_concept(name)
        if norm and len(norm) > 1 and norm not in seen:
            seen.add(norm)
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
    parser = argparse.ArgumentParser(description='Hebbian brain-md seeder')
    parser.add_argument('--since', type=str, default='', help='Only process files modified since Nh ago (e.g. "24h" or "168h" for 1 week)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be processed without writing to DB')
    parser.add_argument('--clear', action='store_true', help='Wipe DB before seeding (default: additive merge)')
    args = parser.parse_args()

    cutoff = None
    if args.since:
        hours = int(args.since.rstrip('h'))
        cutoff = datetime.now() - timedelta(hours=hours)

    def _should_process(p: Path) -> bool:
        if cutoff is None:
            return True
        return datetime.fromtimestamp(p.stat().st_mtime) >= cutoff

    print("=== Hebbian Network Seeder ===")
    print(f"Brain dir: {BRAIN_DIR}")
    print(f"Cutoff: {cutoff or 'none (process all)'}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'WRITE'}")
    print()

    engine = HebbianEngine()
    if args.clear and not args.dry_run:
        print("Clearing existing network (--clear)...")
        engine.clear_all()

    total_pairs = 0
    n_files = 0

    print("\n[Brain Files]")
    for f in sorted(BRAIN_DIR.glob("*.md")):
        if not _should_process(f):
            continue
        n_files += 1
        if args.dry_run:
            print(f"  [dry-run] {f}")
        else:
            total_pairs += seed_from_file(engine, f)

    print("\n[Key Scripts]")
    # Fix 1b: replace hardcoded dead paths (signal_gen.py, ai_decider.py) with glob.
    # Naming convention: signal_<topic>.py (e.g. signal_compactor.py is the LIVE file,
    # not defunct). Only the genuinely obsolete names go in DEAD_SCRIPTS.
    DEAD_SCRIPTS = {
        'signal_gen.py',        # defunct — replaced by signal_compactor.py
        'ai_decider.py',        # defunct — replaced by signal_compactor.py
        'signal_runner.py',     # never created (intended name, not real file)
    }
    # Critical scripts always included first (the heart of the trading system)
    PRIORITY_SCRIPTS = [
        'signal_compactor.py',  # main signal decision maker (LIVE)
        'hl-sync-guardian.py',  # exchange sync + phantom close handling (LIVE)
        'position_manager.py',  # trade lifecycle management (LIVE)
        'decider_run.py',       # hot-set execution (LIVE)
        'hermes_constants.py',  # all constants in one place (LIVE)
        'brain.py',             # DB access layer (LIVE)
        'tpsl_utils.py',        # ATR trailing SL/TP (LIVE)
    ]
    scripts_dir = Path("/root/.hermes/scripts")
    eligible = [
        p for p in scripts_dir.glob("*.py")
        if not p.name.startswith(("test_", "_"))
        and not p.name.startswith("hebbian_")
        and p.name not in DEAD_SCRIPTS
        and p.stat().st_size > 5000
    ]
    # Put priority scripts first (if they exist), then alphabetical for the rest
    by_name = {p.name: p for p in eligible}
    key_scripts = []
    for name in PRIORITY_SCRIPTS:
        if name in by_name:
            key_scripts.append(by_name[name])
    for p in sorted(eligible):
        if p not in key_scripts:
            key_scripts.append(p)
    key_scripts = key_scripts[:50]  # cap at 50 (was 30 — too low, missed signal_compactor)
    for s in key_scripts:
        if not _should_process(s):
            continue
        n_files += 1
        if args.dry_run:
            print(f"  [dry-run] {s}")
        else:
            total_pairs += seed_from_file(engine, s, "file")

    print("\n[Skills]")
    skill_files = list(SKILLS_DIR.glob("*/SKILL.md"))
    skill_files += list(SKILLS_DIR.glob("*/skills/*/SKILL.md"))
    for sf in skill_files[:20]:
        if not _should_process(sf):
            continue
        n_files += 1
        if args.dry_run:
            print(f"  [dry-run] {sf}")
        else:
            total_pairs += seed_from_file(engine, sf)

    print(f"\n=== Seed Complete ===")
    print(f"Files processed: {n_files}")
    print(f"Total pairs learned: {total_pairs}")
    if not args.dry_run:
        stats = engine.get_stats()
        print(f"Nodes: {stats['nodes']}, Synapses: {stats['synapses']}")
        print(f"Top edges:")
        for e in stats['top_edges'][:10]:
            print(f"  {e['a']} <-> {e['b']}: {e['weight']:.1f}")

if __name__ == "__main__":
    main()
