#!/usr/bin/env python3
"""
Hebbian Entity Extractor — lightweight concept extraction for Hermes.

Uses Hermes's own known-vocabulary lists to extract typed entities from text.
No LLM required — fast, deterministic, can run on every session turn.

Returns: list of (concept_name, label_type) tuples.
Label types: token, skill, file, concept, project, infra, person
"""

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Hermes Known Vocabularies
# ---------------------------------------------------------------------------

KNOWN_TOKENS = {
    "BTC", "ETH", "SOL", "SCR", "AVAX", "XRP", "DOGE", "ADA", "DOT", "LINK",
    "UNI", "AAVE", "MKR", "SNX", "UMA", "DYDX", "ZETA", "ORDI", "BIGTIME",
    "MET", "PENDLE", "SAND", "AXS", "ICP", "ETHFI", "SKY", "GMX", "LDO",
    "CRV", "FXS", "APE", "INJ", "TIA", "SEI", "WIF", "PEPE", "SHIB", "FLOKI",
    "ARB", "OP", "MATIC", "POL", "GALA", "ENJ", "MANA", "AX", "RNDR", "VET",
    "THETA", "ALGO", "FTM", "NEAR", "APT", "SUI", "SEI", "TON", "XLM", "HBAR",
    "XDC", "IOST", "ZIL", "KAVA", "ANKR", "ONT", "NPT", "ILV", "RARE",
}

KNOWN_SKILLS = {
    "brain-memory", "associative-recall", "code-review", "code-audit", "wasp",
    "pipeline-analyst", "pipeline-review", "signal-flip", "clear-all", "sync-trades",
    "sync-open-trades", "stale-trades", "closed-trades-eval", "blocklist-decision",
    "hermes-session-wrap", "analyze-trades", "prompt-training", "candle-predictor-tuner",
    "full-review", "project-management", "plan", "writing-plans", "systematic-debugging",
    "test-driven-development", "subagent-driven-development", "plan", "brain-memory",
    "kanban", "github", "youtube-watcher", "arbitrage", "heartmula", "excalidraw",
    "ascii-art", "webhook", "self-improving-agent", "proactive-agent-lite",
}

KNOWN_INFRA = {
    "Tokyo", "Dallas", "SSH", "nginx", "systemd", "PostgreSQL", "SQLite", "pgvector",
    "Docker", "systemd", "cron", "systemd timer", "uvicorn", "FastMCP", "SSE",
    "REST", "API", "JSON", "SQLite", "Tokyo", "TKY", "DAL",
}

KNOWN_FILES = {
    "TASKS.md", "PROJECTS.md", "DECISIONS.md", "trading.md", "lessons.md",
    "brain.md", "SOUL.md", "SOPs.md", "CONTEXT.md", "ideas.md", "kanban.json",
    "hotset.json", "signals.json", "config.yaml", "memory-index.md",
}

KNOWN_PROJECTS = {
    "Cascade Flip Enhancement", "Chart Pattern Recognition", "Signal Quality Improvement",
    "Win Rate Investigation", "Session Checkpoint/Restore System", "ATR Trailing Stop",
    "Hot-Set Compaction", "Pipeline Health Monitoring", "Self-Learning via W&B",
    "Hebbian Associative Memory Network",
}

KNOWN_PERSONS = {
    "T", "Agent", "hermes", "claude", "gpt", "human",
}

# ---------------------------------------------------------------------------
# Extraction patterns
# ---------------------------------------------------------------------------

# CamelCase / PascalCase identifiers (e.g. cascadeFlip, HyperLiquid)
CAMEL_CASE = re.compile(r'\b([A-Z][a-z]+[A-Z][A-Za-z]+)\b')

# ALLCAPS token-like words (case-insensitive)
ALL_CAPS = re.compile(r'\b([A-Z]{2,8})\b')

# lowercase file references like signal_gen.py, cascade_flip.py
LOWER_FILE = re.compile(r'\b([a-z][a-z0-9_-]+\.py)\b')

# lowercase concept phrases: cascade-flip, hyperliquid, etc (known concepts)
LOWER_CONCEPT = re.compile(r'\b([a-z][a-z0-9_-]{2,30})\b')

# Inline code: `something`
INLINE_CODE = re.compile(r'`([^`]+)`')

# File paths: /root/.hermes/... or scripts/...
FILE_PATHS = re.compile(r'(?:/root/[^\s`\'")\]]+|scripts/[^\s`\'")\]]+|/var/[^\s`\'")\]]+)')

# Markdown links: [text](url)
MD_LINKS = re.compile(r'\[([^\]]+)\]\([^)]+\)')

# Bold text: **something**
BOLD_TEXT = re.compile(r'\*\*([^*]+)\*\*')

# @ mentions
AT_MENTIONS = re.compile(r'@([\w-]+)')

# ---------------------------------------------------------------------------
# Label inference
# ---------------------------------------------------------------------------

def infer_label(candidate: str) -> Optional[str]:
    """Infer label type from a concept name string."""
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
    if c in KNOWN_PERSONS:
        return "person"

    # Extensible suffix/prefix rules
    if c_lower.endswith('.py') or '/' in c:
        return "file"
    if c_lower.startswith('skill:') or c_lower.startswith('skill-'):
        return "skill"
    if c_lower.startswith('project:') or c_lower.startswith('proj-'):
        return "project"
    if c_lower in {'ssh', 'tcp', 'udp', 'http', 'https', 'api', 'db', 'sql'}:
        return "infra"

    return "concept"


def extract_entities(text: str) -> list[tuple[str, str]]:
    """
    Extract all typed entities from text.
    Returns list of (concept_name, label_type), deduplicated, in order of appearance.
    """
    found = []
    seen = set()

    # Inline code — highest confidence
    for match in INLINE_CODE.finditer(text):
        val = match.group(1).strip()
        if len(val) > 1 and val not in seen and not val.startswith('$'):
            seen.add(val)
            found.append((val, infer_label(val)))

    # File paths
    for match in FILE_PATHS.finditer(text):
        val = match.group(0).strip()
        if val not in seen:
            seen.add(val)
            found.append((val, "file"))

    # Bold text
    for match in BOLD_TEXT.finditer(text):
        val = match.group(1).strip()
        if len(val) > 1 and val not in seen:
            seen.add(val)
            found.append((val, infer_label(val)))

    # Markdown links (just the text)
    for match in MD_LINKS.finditer(text):
        val = match.group(1).strip()
        if len(val) > 1 and val not in seen:
            seen.add(val)
            found.append((val, infer_label(val)))

    # @ mentions
    for match in AT_MENTIONS.finditer(text):
        val = match.group(1).strip()
        if len(val) > 1 and val not in seen:
            seen.add(val)
            lt = infer_label(val)
            found.append((val, lt if lt != "concept" else "person"))

    # CamelCase identifiers
    for match in CAMEL_CASE.finditer(text):
        val = match.group(1).strip()
        if len(val) > 2 and val not in seen:
            seen.add(val)
            found.append((val, infer_label(val)))

    # Mixed-case known infra (Tokyo, Dallas, etc.) — check directly
    MIXED_CASE_INFRA = {"Tokyo", "Dallas", "Neural", "MacOS", "Linux", "Windows"}
    for infra in MIXED_CASE_INFRA:
        if infra in text and infra not in seen:
            seen.add(infra)
            found.append((infra, "infra"))

    # ALL_CAPS — tokens and acronyms
    for match in ALL_CAPS.finditer(text):
        val = match.group(1).strip()
        if val not in seen and val not in {'API', 'SQL', 'SSH', 'URL', 'TCP', 'UDP', 'HTTP', 'HTTPS', 'JSON', 'XML', 'CSV', 'SQL', 'IDE', 'GPT', 'LLM', 'CLI', 'PID', 'UID', 'GID'}:
            seen.add(val)
            found.append((val, infer_label(val)))

    # Lowercase .py files (signal_gen.py, etc.)
    for match in LOWER_FILE.finditer(text):
        val = match.group(1).strip()
        if val not in seen:
            seen.add(val)
            found.append((val, "file"))

    # Lowercase known concepts — only if recognized
    for match in LOWER_CONCEPT.finditer(text):
        val = match.group(1).strip()
        if val not in seen:
            lt = infer_label(val)
            if lt != "concept":  # only include if we recognized it
                seen.add(val)
                found.append((val, lt))

    return found


def extract_and_learn(text: str, engine=None) -> list:
    """
    Extract entities and learn all co-occurring pairs.
    If engine is None, just extracts without learning.
    Returns list of (concept, label_type) extracted.
    """
    entities = extract_entities(text)
    if engine is not None:
        concepts = [e[0] for e in entities]
        engine.learn_set(concepts)
    return entities
