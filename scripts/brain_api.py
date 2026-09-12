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

PORT = int(os.environ.get("BRAIN_API_PORT", 54322))


def query_db(sql: str, params: tuple = ()) -> list:
    """Query SQLite and return list of dicts."""
    if not BRAIN_DB.exists():
        return []
    conn = sqlite3.connect(str(BRAIN_DB))
    conn.row_factory = sqlite3.Row
    try:
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
