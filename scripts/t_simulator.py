#!/usr/bin/env python3
"""
t_simulator.py — "What would T say?" — FAISS vector search over T's past decisions.

Indexes T's decision patterns from ceo_kanban.md, brain/DECISIONS.md, and
brain/decisions/*.md into a FAISS vector database. When the automation team
faces a decision T would normally make, it searches for the closest past
decision and follows T's established pattern.

Usage:
    python3 scripts/t_simulator.py index          # Build/rebuild the index
    python3 scripts/t_simulator.py search "query"  # What would T say?
    python3 scripts/t_simulator.py list            # List indexed decisions
"""
import os
import sys
import re
import json
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import HERMES_DATA

INDEX_DIR = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 't_simulator')
os.makedirs(INDEX_DIR, exist_ok=True)

DECISIONS_JSON = os.path.join(INDEX_DIR, 'decisions.json')
FAISS_INDEX = os.path.join(INDEX_DIR, 'index.faiss')


def parse_t_decisions():
    """Extract T's direct decisions from kanban and decision files."""
    decisions = []

    # From ceo_kanban.md — lines with T decisions
    kanban_path = os.path.join(HERMES_DATA, '..', 'automation', 'ceo', 'ceo_kanban.md')
    if os.path.exists(kanban_path):
        with open(kanban_path) as f:
            for line in f:
                if 'T decision' in line or 'T directive' in line or '— T' in line or '—CEO' in line:
                    decisions.append({
                        'source': 'kanban',
                        'text': line.strip()[:500],
                        'type': 'directive',
                    })

    # From DECISIONS.md
    decisions_path = os.path.join(HERMES_DATA, '..', 'brain', 'DECISIONS.md')
    if os.path.exists(decisions_path):
        with open(decisions_path) as f:
            content = f.read()
            # Split by headers or decision blocks
            for block in re.split(r'\n(?=#|\d+\.)', content):
                if len(block.strip()) > 50:
                    decisions.append({
                        'source': 'DECISIONS.md',
                        'text': block.strip()[:500],
                        'type': 'decision',
                    })

    # From brain/decisions/*.md
    for f in glob.glob(os.path.join(HERMES_DATA, '..', 'brain', 'decisions', '*.md')):
        with open(f) as fh:
            content = fh.read()
            decisions.append({
                'source': os.path.basename(f),
                'text': content[:500],
                'type': 'file',
            })

    return decisions


def build_index():
    """Build FAISS index from T's decisions."""
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np

    decisions = parse_t_decisions()
    print(f"Parsed {len(decisions)} decisions")

    if not decisions:
        print("No decisions found — check source files")
        return

    # Embed
    model = SentenceTransformer('all-MiniLM-L6-v2')
    texts = [d['text'] for d in decisions]
    embeddings = model.encode(texts, show_progress_bar=True)

    # Build FAISS index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings.astype('float32'))

    # Save
    faiss.write_index(index, FAISS_INDEX)
    with open(DECISIONS_JSON, 'w') as f:
        json.dump(decisions, f, indent=2)

    print(f"Index built: {index.ntotal} vectors, dim={dim}")
    print(f"Saved: {FAISS_INDEX}")


def search(query, top_k=5):
    """Search for the most similar past T decision."""
    from sentence_transformers import SentenceTransformer
    import faiss

    if not os.path.exists(FAISS_INDEX):
        print("Index not found. Run: python3 scripts/t_simulator.py index")
        return []

    index = faiss.read_index(FAISS_INDEX)
    with open(DECISIONS_JSON) as f:
        decisions = json.load(f)

    model = SentenceTransformer('all-MiniLM-L6-v2')
    q_emb = model.encode([query]).astype('float32')

    distances, indices = index.search(q_emb, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < len(decisions):
            results.append({
                'similarity': float(1 / (1 + dist)),
                'source': decisions[idx]['source'],
                'type': decisions[idx]['type'],
                'text': decisions[idx]['text'][:300],
            })

    return results


def list_decisions():
    """List all indexed decisions."""
    if not os.path.exists(DECISIONS_JSON):
        print("Index not found. Run: python3 scripts/t_simulator.py index")
        return

    with open(DECISIONS_JSON) as f:
        decisions = json.load(f)

    print(f"{len(decisions)} decisions indexed:")
    for i, d in enumerate(decisions):
        print(f"  [{i}] ({d['source']}) {d['text'][:80]}...")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='T Simulator — "What would T say?"')
    parser.add_argument('action', choices=['index', 'search', 'list'])
    parser.add_argument('query', nargs='?', help='Search query (for search action)')
    parser.add_argument('--top-k', type=int, default=5)
    args = parser.parse_args()

    if args.action == 'index':
        build_index()
    elif args.action == 'search':
        if not args.query:
            print("Usage: python3 scripts/t_simulator.py search 'your question'")
            sys.exit(1)
        results = search(args.query, args.top_k)
        print(f"\nWhat would T say about: '{args.query}'\n")
        for i, r in enumerate(results):
            print(f"  {i+1}. (similarity={r['similarity']:.2f}, {r['source']})")
            print(f"     {r['text'][:200]}")
            print()
    elif args.action == 'list':
        list_decisions()
