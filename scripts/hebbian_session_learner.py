#!/usr/bin/env python3
"""
Hebbian Session Co-occurrence Learner

Scans Hermes's session/conversation data and learns entity co-occurrences.
Run manually or via cron. Processes:
- Recent session dumps (request_dump_*.json)
- ai_decider decisions log (wandb-local/decisions.jsonl)
- event log (data/event-log.jsonl)

Usage:
  python3 scripts/hebbian_session_learner.py [days_back]
  python3 scripts/hebbian_session_learner.py --dry-run  # just show what would be learned
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/scripts')
from hebbian_engine import HebbianEngine
from hebbian_entity_extractor import extract_entities

HERMES_DIR = Path("/root/.hermes")
SESSIONS_DIR = HERMES_DIR / "sessions"
DATA_DIR = HERMES_DIR / "data"
WANDB_DIR = HERMES_DIR / "wandb-local"

# Trading-specific label types
REGIMES = {"SHORT_BIAS", "NEUTRAL", "LONG_BIAS", "UP_BIAS", "DOWN_BIAS", "RANGING"}
DIRECTIONS = {"LONG", "SHORT"}
DECISIONS = {"APPROVED", "SKIPPED", "HOT_APPROVED", "WAIT", "REJECTED", "PENDING"}


def parse_session_dump(filepath: Path) -> list[str]:
    """Extract all user/assistant message text from a session dump."""
    texts = []
    try:
        with open(filepath) as f:
            data = json.load(f)
        request = data.get("request", {})
        # Extract user message
        if isinstance(request, dict):
            messages = request.get("messages", [])
            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    texts.append(content.strip()[:2000])
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            txt = block.get("text", "")
                            if txt.strip():
                                texts.append(txt.strip()[:2000])
    except Exception as e:
        pass
    return texts


def learn_from_text(engine: HebbianEngine, text: str, source: str, label_types: list = None) -> int:
    """Extract entities from text and learn all co-occurring pairs. Returns count."""
    entities = extract_entities(text)
    if len(entities) < 2:
        return 0

    concepts = [e[0] for e in entities]
    ltypes = [e[1] for e in entities]
    for i in range(len(concepts)):
        for j in range(i + 1, len(concepts)):
            engine.learn_pair(concepts[i], concepts[j], ltypes[i], ltypes[j])
    return len(entities)


def learn_from_decisions_log(engine: HebbianEngine, days_back: int = 3) -> int:
    """Learn from ai_decider decisions log — token + regime + direction + decision."""
    log_path = WANDB_DIR / "decisions.jsonl"
    if not log_path.exists():
        return 0

    cutoff = datetime.now() - timedelta(days=days_back)
    count = 0

    with open(log_path) as f:
        for line in f:
            try:
                d = json.loads(line)
                ts = datetime.fromisoformat(d.get("timestamp", "1970"))
                if ts < cutoff:
                    continue

                token = d.get("top_token", "")
                regime = d.get("regime", "")
                direction = d.get("decision", "")  # actually direction field
                decision = d.get("decision", "")
                reason = d.get("reason", "")

                pairs = []
                if token:
                    pairs.append(("token", token))
                if regime and regime in REGIMES:
                    pairs.append(("regime", regime))
                if direction and direction in DIRECTIONS:
                    pairs.append(("direction", direction))
                if decision and decision in DECISIONS:
                    pairs.append(("decision", decision))

                for i in range(len(pairs)):
                    for j in range(i + 1, len(pairs)):
                        lt_a, a = pairs[i]
                        lt_b, b = pairs[j]
                        engine.learn_pair(a, b, lt_a, lt_b)
                        count += 1

            except Exception:
                continue

    return count


def learn_from_event_log(engine: HebbianEngine, days_back: int = 3) -> int:
    """Learn from event log — events and their associated entities."""
    log_path = DATA_DIR / "event-log.jsonl"
    if not log_path.exists():
        return 0

    cutoff = datetime.now() - timedelta(days=days_back)
    count = 0

    with open(log_path) as f:
        for line in f:
            try:
                d = json.loads(line)
                ts_str = d.get("timestamp", "")
                if not ts_str:
                    continue
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts < cutoff:
                    continue

                # Extract key fields as concepts
                event_type = d.get("type", d.get("event", ""))
                if event_type:
                    entities = extract_entities(event_type)
                    concepts = [e[0] for e in entities]
                    if len(concepts) >= 2:
                        engine.learn_set(concepts)
                        count += 1

            except Exception:
                continue

    return count


def learn_from_sessions(engine: HebbianEngine, days_back: int = 3) -> int:
    """Learn from session dump files."""
    cutoff = datetime.now() - timedelta(days=days_back)
    count = 0

    if not SESSIONS_DIR.exists():
        return 0

    for fp in sorted(SESSIONS_DIR.glob("request_dump_*.json"), reverse=True)[:50]:
        # Parse date from filename: request_dump_20260328_044135_
        m = re.search(r'request_dump_(\d{8})', fp.name)
        if m:
            date_str = m.group(1)
            try:
                file_date = datetime.strptime(date_str, "%Y%m%d")
                if file_date < cutoff:
                    continue
            except ValueError:
                pass

        texts = parse_session_dump(fp)
        for text in texts:
            if learn_from_text(engine, text, fp.name):
                count += 1

    return count


def main():
    dry_run = "--dry-run" in sys.argv
    days_back = 3
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        days_back = int(sys.argv[1])

    engine = HebbianEngine()

    print(f"=== Hebbian Session Learner ===")
    print(f"Days back: {days_back}")
    print(f"Dry run: {dry_run}")
    print()

    total_pairs = 0

    # 1. Session dumps
    print("[Session Dumps]")
    n = learn_from_sessions(engine, days_back)
    print(f"  Processed {n} session turns")
    total_pairs += n

    # 2. Decisions log
    print("[Decisions Log]")
    n = learn_from_decisions_log(engine, days_back)
    print(f"  Learned {n} trading decision pairs")
    total_pairs += n

    # 3. Event log
    print("[Event Log]")
    n = learn_from_event_log(engine, days_back)
    print(f"  Learned {n} event pairs")
    total_pairs += n

    print()
    if dry_run:
        print("DRY RUN — no changes written")
    else:
        print(f"Total pairs learned: {total_pairs}")
        stats = engine.get_stats()
        print(f"Network now: {stats['nodes']} nodes, {stats['synapses']} synapses")
        print("Top edges:")
        for e in stats['top_edges'][:8]:
            print(f"  {e['a']} <-> {e['b']}: {e['weight']:.1f}")


if __name__ == "__main__":
    main()
