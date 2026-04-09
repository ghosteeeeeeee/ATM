#!/usr/bin/env python3
"""
Hebbian Associative Memory Engine for Hermes
"neurons that fire together, wire together" — Donald Hebb, 1949

Stores concept nodes and synapse weights. When concepts co-occur,
their connection strength grows. Retrieval returns ranked associations.
"""

import sqlite3
import os
import time
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = "/root/.hermes/brain/associative_memory.db"

# Weight dynamics
WEIGHT_CEILING = 100.0
WEIGHT_FLOOR = 0.5
WEIGHT_INCREMENT = 1.0
DECAY_FACTOR = 0.999  # Elephant memory: ~3% loss per year, ~0.3% per month


class HebbianEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create schema if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS concept_nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    label_type TEXT DEFAULT 'concept',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS synapse_weights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    concept_a_id INTEGER NOT NULL,
                    concept_b_id INTEGER NOT NULL,
                    weight REAL DEFAULT 1.0,
                    co_occurrences INTEGER DEFAULT 1,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (concept_a_id) REFERENCES concept_nodes(id),
                    FOREIGN KEY (concept_b_id) REFERENCES concept_nodes(id),
                    UNIQUE(concept_a_id, concept_b_id)
                )
            """)
            # Indexes for fast lookup
            conn.execute("CREATE INDEX IF NOT EXISTS idx_synapse_a ON synapse_weights(concept_a_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_synapse_b ON synapse_weights(concept_b_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_node_name ON concept_nodes(name)")
            conn.commit()

    def _get_or_create_node(self, name: str, label_type: str = "concept") -> int:
        """Get node id, creating if needed. Updates last_seen."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT id FROM concept_nodes WHERE name = ?",
                (name,)
            )
            row = cur.fetchone()
            if row:
                conn.execute(
                    "UPDATE concept_nodes SET last_seen = CURRENT_TIMESTAMP WHERE id = ?",
                    (row[0],)
                )
                return row[0]
            cur = conn.execute(
                "INSERT INTO concept_nodes (name, label_type) VALUES (?, ?)",
                (name, label_type)
            )
            return cur.lastrowid

    def _normalize_pair(self, a_id: int, b_id: int) -> tuple:
        """Ensure consistent ordering for symmetric storage."""
        return (a_id, b_id) if a_id < b_id else (b_id, a_id)

    def learn_pair(
        self,
        concept_a: str,
        concept_b: str,
        label_type_a: Optional[str] = None,
        label_type_b: Optional[str] = None
    ) -> float:
        """
        Record that concept_a and concept_b fired together.
        Increments synapse weight. Creates nodes if needed.
        Returns the new weight.
        """
        a_id = self._get_or_create_node(concept_a, label_type_a or "concept")
        b_id = self._get_or_create_node(concept_b, label_type_b or "concept")

        if a_id == b_id:
            return 0.0  # Don't self-link

        a_norm, b_norm = self._normalize_pair(a_id, b_id)

        with sqlite3.connect(self.db_path) as conn:
            # Upsert synapse
            cur = conn.execute(
                "SELECT weight, co_occurrences FROM synapse_weights WHERE concept_a_id = ? AND concept_b_id = ?",
                (a_norm, b_norm)
            )
            row = cur.fetchone()

            if row:
                old_weight = row[0]
                new_weight = min(WEIGHT_CEILING, old_weight + WEIGHT_INCREMENT)
                new_count = row[1] + 1
                conn.execute("""
                    UPDATE synapse_weights
                    SET weight = ?, co_occurrences = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE concept_a_id = ? AND concept_b_id = ?
                """, (new_weight, new_count, a_norm, b_norm))
            else:
                new_weight = WEIGHT_INCREMENT
                conn.execute("""
                    INSERT INTO synapse_weights (concept_a_id, concept_b_id, weight, co_occurrences)
                    VALUES (?, ?, ?, 1)
                """, (a_norm, b_norm, new_weight))

            conn.commit()
            return new_weight

    def learn_set(self, concepts: list, label_types: Optional[list] = None) -> list:
        """
        Learn all pairs from a set of concepts that fired together.
        Creates C(n,2) pairs. Returns list of (pair, weight) tuples.
        """
        if len(concepts) < 2:
            return []

        results = []
        label_types = label_types or [None] * len(concepts)

        for i in range(len(concepts)):
            for j in range(i + 1, len(concepts)):
                w = self.learn_pair(concepts[i], concepts[j], label_types[i], label_types[j])
                results.append(((concepts[i], concepts[j]), w))

        return results

    def recall(
        self,
        concept: str,
        k: int = 5,
        min_weight: float = WEIGHT_FLOOR
    ) -> list:
        """
        Given a concept, return top-K associated concepts ranked by weight.
        Returns list of (concept_name, label_type, weight, co_occurrences).
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT id, label_type FROM concept_nodes WHERE name = ?",
                (concept,)
            )
            row = cur.fetchone()
            if not row:
                return []

            node_id = row[0]

            # Bidirectional lookup via symmetric pair
            cur = conn.execute("""
                SELECT
                    CASE WHEN concept_a_id = ? THEN concept_b_id ELSE concept_a_id END as other_id,
                    weight,
                    co_occurrences
                FROM synapse_weights
                WHERE (concept_a_id = ? OR concept_b_id = ?)
                  AND weight >= ?
                ORDER BY weight DESC
                LIMIT ?
            """, (node_id, node_id, node_id, min_weight, k))

            results = []
            for other_id, weight, count in cur.fetchall():
                cur2 = conn.execute(
                    "SELECT name, label_type FROM concept_nodes WHERE id = ?",
                    (other_id,)
                )
                node_row = cur2.fetchone()
                if node_row:
                    results.append((node_row[0], node_row[1], weight, count))

            return results

    def decay_all(self, decay_factor: float = DECAY_FACTOR, min_age_days: int = 7) -> int:
        """
        Apply decay to old synapses. Returns number of rows affected.
        """
        cutoff = datetime.now() - timedelta(days=min_age_days)
        cutoff_str = cutoff.isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("""
                UPDATE synapse_weights
                SET weight = weight * ?, last_updated = CURRENT_TIMESTAMP
                WHERE last_updated < ?
                  AND weight > ?
            """, (decay_factor, cutoff_str, WEIGHT_FLOOR))
            conn.commit()
            return cur.rowcount

    def get_stats(self) -> dict:
        """Return summary statistics."""
        with sqlite3.connect(self.db_path) as conn:
            nodes = conn.execute("SELECT COUNT(*) FROM concept_nodes").fetchone()[0]
            synapses = conn.execute("SELECT COUNT(*) FROM synapse_weights").fetchone()[0]
            total_weight = conn.execute("SELECT SUM(weight) FROM synapse_weights").fetchone()[0]
            top_edges = conn.execute("""
                SELECT a.name, b.name, sw.weight, sw.co_occurrences
                FROM synapse_weights sw
                JOIN concept_nodes a ON a.id = sw.concept_a_id
                JOIN concept_nodes b ON b.id = sw.concept_b_id
                ORDER BY sw.weight DESC
                LIMIT 10
            """).fetchall()
            label_dist = conn.execute("""
                SELECT label_type, COUNT(*) FROM concept_nodes GROUP BY label_type
            """).fetchall()

            return {
                "nodes": nodes,
                "synapses": synapses,
                "total_weight": total_weight or 0.0,
                "top_edges": [
                    {"a": r[0], "b": r[1], "weight": r[2], "co_occurrences": r[3]}
                    for r in top_edges
                ],
                "label_distribution": dict(label_dist),
            }

    def clear_all(self):
        """Dangerous: wipe all data."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM synapse_weights")
            conn.execute("DELETE FROM concept_nodes")
            conn.commit()


def main():
    """CLI for testing."""
    import sys
    engine = HebbianEngine()

    if len(sys.argv) < 2:
        print("Usage: hebbian_engine.py <command> [args]")
        print("  learn <a> <b>")
        print("  learn-set <concept1> <concept2> ...")
        print("  recall <concept> [k]")
        print("  stats")
        print("  decay")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "learn" and len(sys.argv) == 4:
        w = engine.learn_pair(sys.argv[2], sys.argv[3])
        print(f"Learned: {sys.argv[2]} <-> {sys.argv[3]} (weight={w})")

    elif cmd == "learn-set" and len(sys.argv) > 3:
        concepts = sys.argv[2:]
        results = engine.learn_set(concepts)
        for (a, b), w in results:
            print(f"Learned: {a} <-> {b} (weight={w})")

    elif cmd == "recall" and len(sys.argv) >= 3:
        k = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        results = engine.recall(sys.argv[2], k=k)
        if not results:
            print(f"No associations for '{sys.argv[2]}'")
        for name, ltype, weight, count in results:
            print(f"  [{weight:.1f}x{count}] {name} ({ltype})")

    elif cmd == "stats":
        s = engine.get_stats()
        print(f"Nodes: {s['nodes']}")
        print(f"Synapses: {s['synapses']}")
        print(f"Total weight: {s['total_weight']:.1f}")
        print("Label distribution:", s["label_distribution"])
        print("Top edges:")
        for e in s["top_edges"]:
            print(f"  {e['a']} <-> {e['b']}: {e['weight']:.1f} ({e['co_occurrences']} fires)")

    elif cmd == "decay":
        n = engine.decay_all()
        print(f"Decayed {n} synapses")

    else:
        print("Unknown command")
        sys.exit(1)


if __name__ == "__main__":
    main()
