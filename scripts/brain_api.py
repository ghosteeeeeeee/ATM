#!/usr/bin/env python3
"""
Brain Dashboard API — serves JSON for the brain dashboard.

Usage:
  python3 scripts/brain_api.py                    # Run on port 54322
  python3 scripts/brain_api.py --port 54322

Endpoints:
  GET /api/brain/stats          → session brain health metrics
  GET /api/brain/recommendations → all audit recommendations
  GET /api/brain/drift          → current config drift items
  GET /api/brain/topics         → topic frequency across sessions
  GET /api/brain/creative       → creative improvement ideas
  GET /api/brain/sessions       → session list with metadata
  GET /api/brain/session/<id>   → single session detail
  GET /api/brain/search?q=      → semantic search across sessions
  GET /api/brain/timeline       → session timeline data
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(__file__))

BRAIN_DB = Path("/root/.hermes/data/session_brain.db")
RECOMMENDATIONS_FILE = Path("/root/.hermes/brain/audit_recommendations.json")
CREATIVE_FILE = Path("/root/.hermes/brain/creative_improvements.json")
AUDIT_LOG = Path("/root/.hermes/brain/audit_log.json")
CHANGES_LOG = Path("/root/.hermes/brain/changes_log.json")
AUDIT_LOG = Path("/root/.hermes/brain/audit_log.json")

PORT = int(os.environ.get("BRAIN_API_PORT", 54322))


def query_db(sql: str, params: tuple = ()) -> list:
    """Query SQLite and return list of dicts."""
    if not BRAIN_DB.exists():
        return []
    conn = sqlite3.connect(str(BRAIN_DB))
    conn.row_factory = sqlite3.Row
    try:
        # Load sqlite-vec if querying vec_chunks
        if 'vec_chunks' in sql:
            import sqlite_vec
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_stats() -> dict:
    """Session brain health stats."""
    sessions = query_db("SELECT COUNT(*) as cnt FROM sessions")
    indexed = query_db("SELECT COUNT(*) as cnt FROM sessions WHERE status = 'indexed'")
    chunks = query_db("SELECT COUNT(*) as cnt FROM chunks")
    types = query_db("SELECT chunk_type, COUNT(*) as cnt FROM chunks GROUP BY chunk_type")
    last_ingest = query_db(
        "SELECT completed_at, sessions_processed, chunks_created, duration_seconds, mode "
        "FROM ingest_log ORDER BY id DESC LIMIT 1"
    )
    
    faiss_size = 0
    faiss_path = Path("/root/.hermes/data/session_brain.index")
    if faiss_path.exists():
        faiss_size = faiss_path.stat().st_size
    
    db_size = BRAIN_DB.stat().st_size if BRAIN_DB.exists() else 0
    
    return {
        "sessions_total": sessions[0]["cnt"] if sessions else 0,
        "sessions_indexed": indexed[0]["cnt"] if indexed else 0,
        "chunks_total": chunks[0]["cnt"] if chunks else 0,
        "chunk_types": {t["chunk_type"]: t["cnt"] for t in types},
        "faiss_index_mb": round(faiss_size / 1024 / 1024, 1),
        "faiss_status": "ready" if faiss_path.exists() else "ingesting",
        "db_size_mb": round(db_size / 1024 / 1024, 1),
        "last_ingest": last_ingest[0] if last_ingest else None,
    }


def get_recommendations() -> list:
    """All audit recommendations."""
    if RECOMMENDATIONS_FILE.exists():
        try:
            with open(RECOMMENDATIONS_FILE) as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return [data]
        except Exception:
            return []
    return []


def get_drift() -> list:
    """Config drift items from recommendations."""
    recs = get_recommendations()
    drift = []
    for rec in recs:
        for item in rec.get("drift_findings", []):
            if isinstance(item, dict):
                item["timestamp"] = rec.get("timestamp", "")
                drift.append(item)
            elif isinstance(item, str):
                drift.append({"finding": item, "timestamp": rec.get("timestamp", "")})
    return drift


def get_topics() -> list:
    """Topic frequency from sessions."""
    return query_db(
        "SELECT topic, COUNT(*) as cnt FROM chunks WHERE topic IS NOT NULL "
        "GROUP BY topic ORDER BY cnt DESC LIMIT 30"
    )


def get_topic_relationships() -> dict:
    """Topic co-occurrence relationships for force-directed graph."""
    if not BRAIN_DB.exists():
        return {"nodes": [], "edges": []}
    
    conn = sqlite3.connect(str(BRAIN_DB))
    conn.row_factory = sqlite3.Row
    
    # Get dominant topic per session
    rows = conn.execute(
        "SELECT session_id, topic, COUNT(*) as cnt FROM chunks "
        "WHERE topic IS NOT NULL GROUP BY session_id, topic"
    ).fetchall()
    conn.close()
    
    # Build co-occurrence
    from collections import Counter
    session_topics = {}
    for r in rows:
        sid, topic = r["session_id"], r["topic"]
        if sid not in session_topics:
            session_topics[sid] = set()
        session_topics[sid].add(topic)
    
    pair_counts = Counter()
    topic_session_counts = Counter()
    for sid, topics in session_topics.items():
        topics = sorted(topics)
        for t in topics:
            topic_session_counts[t] += 1
        for i in range(len(topics)):
            for j in range(i + 1, len(topics)):
                pair_counts[(topics[i], topics[j])] += 1
    
    # Build nodes
    max_count = max(topic_session_counts.values()) if topic_session_counts else 1
    nodes = []
    for topic, cnt in topic_session_counts.most_common():
        nodes.append({"id": topic, "count": cnt, "size": cnt / max_count})
    
    # Build edges (top pairs only)
    edges = []
    for (a, b), cnt in pair_counts.most_common(30):
        if cnt >= 5:
            edges.append({"source": a, "target": b, "weight": cnt})
    
    return {"nodes": nodes, "edges": edges}


def get_creative() -> list:
    """Creative improvement ideas."""
    if CREATIVE_FILE.exists():
        try:
            with open(CREATIVE_FILE) as f:
                return json.load(f)
        except Exception:
            return []
    return []


def get_sessions(limit: int = 50, offset: int = 0) -> list:
    """Session list with metadata."""
    return query_db(
        "SELECT id, title, chunk_count, last_modified, last_ingested, status "
        "FROM sessions ORDER BY last_modified DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )


def get_session_detail(session_id: str) -> dict:
    """Single session with its chunks."""
    sessions = query_db(
        "SELECT * FROM sessions WHERE id = ?", (session_id,)
    )
    if not sessions:
        return {"error": "Session not found"}
    
    session = sessions[0]
    chunks = query_db(
        "SELECT chunk_index, text, chunk_type, char_count "
        "FROM chunks WHERE session_id = ? ORDER BY chunk_index",
        (session_id,)
    )
    session["chunks"] = chunks
    return session


_brain_singleton = None

def get_brain():
    """BUG 3 fix: Singleton — load SessionBrain once, reuse across requests."""
    global _brain_singleton
    if _brain_singleton is None:
        from session_brain import SessionBrain
        _brain_singleton = SessionBrain()
    return _brain_singleton


def search_sessions(query_text: str, top_k: int = 10) -> list:
    """Semantic search across sessions using session_brain."""
    try:
        brain = get_brain()
        return brain.query(query_text, top_k=top_k)
    except Exception as e:
        return [{"error": str(e)}]


def get_timeline() -> list:
    """Session timeline data for charts."""
    return query_db(
        "SELECT id, title, created_at, last_modified, chunk_count "
        "FROM sessions WHERE last_modified IS NOT NULL "
        "ORDER BY last_modified DESC LIMIT 100"
    )


def get_audit_log() -> list:
    """Full audit log history."""
    if AUDIT_LOG.exists():
        try:
            with open(AUDIT_LOG) as f:
                return json.load(f)
        except Exception:
            return []
    return []


def get_changes() -> list:
    """All config changes made by brain auditor and CEO."""
    if CHANGES_LOG.exists():
        try:
            with open(CHANGES_LOG) as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return [data]
        except Exception:
            return []
    return []


def reject_creative(index: int, reason: str = "") -> dict:
    """Reject a creative improvement by setting its status to rejected."""
    if not CREATIVE_FILE.exists():
        return {"error": "No creative improvements file"}
    
    try:
        with open(CREATIVE_FILE) as f:
            data = json.load(f)
        
        if not isinstance(data, list) or index is None or index < 0 or index >= len(data):
            return {"error": f"Invalid index {index}"}
        
        data[index]["status"] = "rejected"
        data[index]["rejected_at"] = datetime.now(timezone.utc).isoformat()
        if reason:
            data[index]["reject_reason"] = reason
        
        with open(CREATIVE_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return {"ok": True, "idea": data[index].get("idea", "")}
    except Exception as e:
        return {"error": str(e)}


def boost_creative(index: int) -> dict:
    """Boost/approve a creative improvement so CEO prioritizes it."""
    if not CREATIVE_FILE.exists():
        return {"error": "No creative improvements file"}
    
    try:
        with open(CREATIVE_FILE) as f:
            data = json.load(f)
        
        if not isinstance(data, list) or index is None or index < 0 or index >= len(data):
            return {"error": f"Invalid index {index}"}
        
        data[index]["status"] = "boosted"
        data[index]["boosted_at"] = datetime.now(timezone.utc).isoformat()
        
        with open(CREATIVE_FILE, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return {"ok": True, "idea": data[index].get("idea", "")}
    except Exception as e:
        return {"error": str(e)}


# ── HTTP Handler ────────────────────────────────────────────────────────

class BrainAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        if path == "/api/brain/stats":
            self._json_response(get_stats())
        elif path == "/api/brain/recommendations":
            self._json_response(get_recommendations())
        elif path == "/api/brain/drift":
            self._json_response(get_drift())
        elif path == "/api/brain/topics":
            self._json_response(get_topics())
        elif path == "/api/brain/creative":
            self._json_response(get_creative())
        elif path == "/api/brain/sessions":
            limit = int(params.get("limit", [50])[0])
            offset = int(params.get("offset", [0])[0])
            self._json_response(get_sessions(limit, offset))
        elif path.startswith("/api/brain/session/"):
            session_id = path.split("/api/brain/session/")[1]
            self._json_response(get_session_detail(session_id))
        elif path == "/api/brain/search":
            q = params.get("q", [""])[0]
            top_k = int(params.get("top_k", [10])[0])
            self._json_response(search_sessions(q, top_k))
        elif path == "/api/brain/timeline":
            self._json_response(get_timeline())
        elif path == "/api/brain/audit-log":
            self._json_response(get_audit_log())
        elif path == "/api/brain/changes":
            self._json_response(get_changes())
        elif path == "/api/brain/topic-graph":
            self._json_response(get_topic_relationships())
        else:
            self._json_response({"error": "Not found"}, 404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/api/brain/creative/reject":
            # Reject a creative improvement by index
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}
                index = body.get("index")
                reason = body.get("reason", "")
                self._json_response(reject_creative(index, reason))
            except Exception as e:
                self._json_response({"error": str(e)}, 400)
        elif path == "/api/brain/creative/boost":
            # Boost/approve a creative improvement
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(content_length)) if content_length > 0 else {}
                index = body.get("index")
                self._json_response(boost_creative(index))
            except Exception as e:
                self._json_response({"error": str(e)}, 400)
        else:
            self._json_response({"error": "Not found"}, 404)
    
    def _json_response(self, data, status=200):
        body = json.dumps(data, default=str, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    
    def log_message(self, format, *args):
        pass  # Suppress request logging


def main():
    server = HTTPServer(("0.0.0.0", PORT), BrainAPIHandler)
    print(f"Brain API running on port {PORT}")
    print(f"Endpoints:")
    print(f"  GET /api/brain/stats")
    print(f"  GET /api/brain/recommendations")
    print(f"  GET /api/brain/drift")
    print(f"  GET /api/brain/topics")
    print(f"  GET /api/brain/creative")
    print(f"  GET /api/brain/sessions")
    print(f"  GET /api/brain/session/<id>")
    print(f"  GET /api/brain/search?q=")
    print(f"  GET /api/brain/timeline")
    print(f"  GET /api/brain/audit-log")
    server.serve_forever()


if __name__ == "__main__":
    main()
