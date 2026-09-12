#!/usr/bin/env python3
"""
Session Brain — RAG system for DSH conversation sessions.

Parses all DSH sessions (.jsonl.zstd), embeds them with sentence-transformers,
stores in FAISS + SQLite for semantic search.

Usage:
  python3 scripts/session_brain.py --ingest     # Full ingest of all sessions
  python3 scripts/session_brain.py --update     # Incremental (new/changed only)
  python3 scripts/session_brain.py --query "bb_bounce in EXTREME regime"
  python3 scripts/session_brain.py --stats      # Show brain stats
"""

import os
import sys
import json
import time
import struct
import sqlite3
import argparse
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, os.path.dirname(__file__))
from paths import *  # noqa: F401,F403

# ── Paths ───────────────────────────────────────────────────────────────
SESSIONS_DIR = Path(os.environ.get("DSH_SESSIONS_DIR",
    "/root/.dsh/sessions/--root-.hermes--"))
DATA_DIR = Path(HERMES_DATA) if 'HERMES_DATA' in dir() else Path("/root/.hermes/data")
BRAIN_DB = DATA_DIR / "session_brain.db"
FAISS_INDEX = DATA_DIR / "session_brain.index"
FAISS_IDS = DATA_DIR / "session_brain_ids.json"

# ── Config ──────────────────────────────────────────────────────────────
CHUNK_SIZE = 500       # tokens (approximated as chars/4)
CHUNK_OVERLAP = 100    # tokens overlap between chunks
MIN_CHUNK_CHARS = 100  # minimum chars to keep a chunk
MAX_CHUNK_CHARS = 2500 # max chars per chunk (~500 tokens * 5 chars avg)
STALE_SESSION_MIN = 5  # skip sessions modified in last N minutes
EMBED_MODEL = "all-MiniLM-L6-v2"

# System noise to filter out
SYSTEM_NOISE_PATTERNS = [
    "<system-reminder>",
    "Current runtime context.",
    "This snapshot supersedes earlier",
    "You are interacting with the user through the DeepSeek Harness",
    "The browser provides no implicit DOM",
    "The client-plugin HMR receiver",
    "Starting another server does not update",
    "Do not start a replacement server",
    "Use the read tool",
    "Use the write tool",
    "Use the edit tool",
    "Use the glob tool",
    "Use the grep tool",
    "The required queries array accepts",
    "Use goal tools for one long-running",
    "Use the workflow tool ONLY when",
    "Use the ralph tool ONLY when",
    "Use subagent in the background",
    "Use subagent_fork in the background",
    "When you successfully create",
    "Track every background job",
    "You may call one or more functions",
    "You have access to the following functions",
]

# ── Database Schema ─────────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TEXT,
    file_size INTEGER,
    last_modified REAL,
    last_ingested REAL,
    chunk_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    topic TEXT,
    chunk_type TEXT,  -- user/assistant/tool/reasoning
    char_count INTEGER,
    token_estimate INTEGER,
    embedding_offset INTEGER,  -- position in FAISS index
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_chunks_session ON chunks(session_id);
CREATE INDEX IF NOT EXISTS idx_chunks_type ON chunks(chunk_type);

CREATE TABLE IF NOT EXISTS ingest_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT,
    completed_at TEXT,
    sessions_processed INTEGER,
    chunks_created INTEGER,
    duration_seconds REAL,
    mode TEXT  -- 'full' or 'incremental'
);
"""


# ═══════════════════════════════════════════════════════════════════════
# SESSION PARSER
# ═══════════════════════════════════════════════════════════════════════

def is_noise(text: str) -> bool:
    """Check if text is system noise to filter out."""
    text_lower = text[:500].lower()
    for pattern in SYSTEM_NOISE_PATTERNS:
        if pattern.lower() in text_lower:
            return True
    return False


def clean_text(text: str) -> str:
    """Clean extracted text: strip, collapse whitespace, remove noise."""
    if not text:
        return ""
    # Strip leading/trailing whitespace
    text = text.strip()
    # Collapse multiple newlines
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    # Collapse multiple spaces
    while "  " in text:
        text = text.replace("  ", " ")
    return text


def extract_text_from_session(filepath: Path) -> Tuple[str, List[Dict], float, str]:
    """
    Parse a .jsonl.zstd session file and extract all text content.
    
    Returns:
        (title, chunks, created_at_ms, origin) where chunks is a list of {text, type, timestamp}
    """
    import zstandard as zstd
    
    title = ""
    raw_chunks = []
    created_at_ms = 0.0
    origin = "unknown"
    
    # BUG 1 fix: Accumulate streaming fragments before checking length
    # Key: (msg_type, turn, step) → accumulated text
    fragment_accumulator = {}  # {(type, turn, step): {"text": str, "timestamp": int}}
    
    def _flush_fragments():
        """Flush accumulated fragments into raw_chunks."""
        for key, frag in fragment_accumulator.items():
            text = clean_text(frag["text"])
            if text and len(text) > 20:
                raw_chunks.append({
                    "text": text,
                    "type": frag["chunk_type"],
                    "timestamp": frag["timestamp"]
                })
        fragment_accumulator.clear()
    
    try:
        dctx = zstd.ZstdDecompressor()
        with open(filepath, 'rb') as f:
            reader = dctx.stream_reader(f)
            buf = b""
            
            while True:
                data = reader.read(65536)
                if not data:
                    break
                buf += data
                
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    
                    msg_type = obj.get("type", "")
                    data_obj = obj.get("data", {})
                    
                    # ── Session title ──
                    if msg_type == "session/title":
                        title = data_obj.get("title", "")
                        continue
                    
                    # ── Session metadata (first line) ──
                    if msg_type == "session":
                        created_at_ms = obj.get("createdAt", 0)
                        origin = obj.get("origin", "unknown")
                        continue
                    
                    # ── User messages ──
                    if msg_type == "user/message":
                        content = data_obj.get("content", [])
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    text = clean_text(block.get("text", ""))
                                    if text and not is_noise(text):
                                        raw_chunks.append({
                                            "text": text,
                                            "type": "user",
                                            "timestamp": obj.get("time", 0)
                                        })
                        continue
                    
                    # ── Assistant chunks (streaming) ──
                    # BUG 2 fix: Only use assistant/chunk block-end for assistant text
                    # (skip assistant/message to avoid duplication)
                    if msg_type == "assistant/chunk":
                        chunk = data_obj.get("chunk", {})
                        if isinstance(chunk, dict):
                            if chunk.get("type") == "block-end":
                                block = chunk.get("block", {})
                                block_type = block.get("type", "")
                                text = block.get("text", "")
                                
                                # Reasoning blocks: accumulate fragments
                                if block_type == "reasoning":
                                    turn = data_obj.get("turn", 0)
                                    step = data_obj.get("step", 0)
                                    key = ("reasoning", turn, step)
                                    if key in fragment_accumulator:
                                        fragment_accumulator[key]["text"] += " " + text
                                    else:
                                        fragment_accumulator[key] = {
                                            "text": text,
                                            "chunk_type": "reasoning",
                                            "timestamp": obj.get("time", 0)
                                        }
                                else:
                                    # Text blocks: emit directly (block-end has full text)
                                    text = clean_text(text)
                                    if text and len(text) > 20:
                                        raw_chunks.append({
                                            "text": text,
                                            "type": "assistant",
                                            "timestamp": obj.get("time", 0)
                                        })
                        continue
                    
                    # ── Assistant messages (assembled) ──
                    # BUG 2 fix: SKIP — duplicated by assistant/chunk block-end
                    if msg_type == "assistant/message":
                        continue
                    
                    # ── Text chunks (batched streaming fragments) ──
                    # BUG 1 fix: Accumulate fragments by (turn, step, index)
                    if msg_type == "text-chunks":
                        texts = data_obj.get("texts", [])
                        turn = data_obj.get("turn", 0)
                        step = data_obj.get("step", 0)
                        if isinstance(texts, list):
                            for idx, t in enumerate(texts):
                                fragment_text = ""
                                if isinstance(t, str):
                                    fragment_text = t
                                elif isinstance(t, dict):
                                    fragment_text = t.get("text", "")
                                
                                if fragment_text:
                                    key = ("text", turn, step, idx)
                                    if key in fragment_accumulator:
                                        fragment_accumulator[key]["text"] += fragment_text
                                    else:
                                        fragment_accumulator[key] = {
                                            "text": fragment_text,
                                            "chunk_type": "assistant",
                                            "timestamp": obj.get("time", 0)
                                        }
                        continue
                    
                    # ── Reasoning chunks (batched streaming fragments) ──
                    # BUG 1 fix: Accumulate fragments by (turn, step, index)
                    if msg_type == "reasoning-chunks":
                        texts = data_obj.get("texts", [])
                        turn = data_obj.get("turn", 0)
                        step = data_obj.get("step", 0)
                        if isinstance(texts, list):
                            for idx, t in enumerate(texts):
                                fragment_text = ""
                                if isinstance(t, str):
                                    fragment_text = t
                                elif isinstance(t, dict):
                                    fragment_text = t.get("text", "")
                                
                                if fragment_text:
                                    key = ("reasoning", turn, step, idx)
                                    if key in fragment_accumulator:
                                        fragment_accumulator[key]["text"] += fragment_text
                                    else:
                                        fragment_accumulator[key] = {
                                            "text": fragment_text,
                                            "chunk_type": "reasoning",
                                            "timestamp": obj.get("time", 0)
                                        }
                        continue
                    
                    # ── Tool results ──
                    if msg_type == "tool/result":
                        message = data_obj.get("message", {})
                        content = message.get("content", [])
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "tool-result":
                                    inner = block.get("content", [])
                                    if isinstance(inner, list):
                                        for ic in inner:
                                            if isinstance(ic, dict) and ic.get("type") == "text":
                                                text = clean_text(ic.get("text", ""))
                                                if text and len(text) > 50:
                                                    if len(text) > MAX_CHUNK_CHARS:
                                                        text = text[:MAX_CHUNK_CHARS] + "..."
                                                    raw_chunks.append({
                                                        "text": text,
                                                        "type": "tool",
                                                        "timestamp": obj.get("time", 0)
                                                    })
                                    elif isinstance(inner, str):
                                        text = clean_text(inner)
                                        if text and len(text) > 50:
                                            if len(text) > MAX_CHUNK_CHARS:
                                                text = text[:MAX_CHUNK_CHARS] + "..."
                                            raw_chunks.append({
                                                "text": text,
                                                "type": "tool",
                                                "timestamp": obj.get("time", 0)
                                            })
                        continue
        
        # Flush any remaining accumulated fragments
        _flush_fragments()
    
    except Exception as e:
        print(f"  ERROR parsing {filepath.name}: {e}")
        return title, [], created_at_ms, origin
    
    return title, raw_chunks, created_at_ms, origin


def merge_and_chunk(raw_chunks: List[Dict], chunk_size: int = CHUNK_SIZE,
                    overlap: int = CHUNK_OVERLAP) -> List[Dict]:
    """
    Merge raw text chunks and re-chunk to target size with overlap.
    
    Strategy: concatenate consecutive chunks of same type, then split
    into target-sized chunks with overlap.
    """
    if not raw_chunks:
        return []
    
    merged = []
    current_text = ""
    current_type = raw_chunks[0].get("type", "unknown")
    
    for rc in raw_chunks:
        text = rc["text"]
        rc_type = rc.get("type", "unknown")
        
        # If type changes or adding this would exceed limit, start new merge
        if rc_type != current_type or len(current_text) + len(text) > MAX_CHUNK_CHARS * 2:
            if current_text.strip():
                merged.append({
                    "text": current_text.strip(),
                    "type": current_type
                })
            current_text = text
            current_type = rc_type
        else:
            current_text += "\n\n" + text
    
    # Don't forget the last merged chunk
    if current_text.strip():
        merged.append({
            "text": current_text.strip(),
            "type": current_type
        })
    
    # Now split merged chunks into target-sized chunks with overlap
    final_chunks = []
    target_chars = chunk_size * 4  # rough chars-per-token estimate
    overlap_chars = overlap * 4
    
    for mc in merged:
        text = mc["text"]
        if len(text) <= target_chars:
            if len(text) >= MIN_CHUNK_CHARS:
                final_chunks.append(mc)
            continue
        
        # Split with overlap
        start = 0
        chunk_idx = 0
        while start < len(text):
            end = min(start + target_chars, len(text))
            chunk_text = text[start:end]
            
            if len(chunk_text) >= MIN_CHUNK_CHARS:
                final_chunks.append({
                    "text": chunk_text,
                    "type": mc["type"],
                    "chunk_index": chunk_idx
                })
                chunk_idx += 1
            
            start += target_chars - overlap_chars
            if start >= len(text):
                break
    
    return final_chunks


# ═══════════════════════════════════════════════════════════════════════
# EMBEDDING
# ═══════════════════════════════════════════════════════════════════════

class Embedder:
    """Wraps sentence-transformers for batch embedding."""
    
    def __init__(self, model_name: str = EMBED_MODEL):
        from sentence_transformers import SentenceTransformer
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()
        print(f"Model loaded. Dimension: {self.dim}")
    
    def embed(self, texts: List[str], batch_size: int = 256) -> List[List[float]]:
        """Embed a list of texts. Returns list of float vectors."""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True  # cosine similarity = dot product
        )
        return [e.tolist() for e in embeddings]
    
    def embed_one(self, text: str) -> List[float]:
        """Embed a single text."""
        return self.model.encode([text], normalize_embeddings=True)[0].tolist()


# ═══════════════════════════════════════════════════════════════════════
# FAISS INDEX
# ═══════════════════════════════════════════════════════════════════════

class VectorStore:
    """FAISS vector store with ID mapping."""
    
    def __init__(self, dim: int = 384):
        import faiss
        self.dim = dim
        self.index = None
        self.ids = []  # mapping: faiss idx -> chunk_id
        self._load_or_create(dim)
    
    def _load_or_create(self, dim: int):
        import faiss
        if FAISS_INDEX.exists():
            print(f"Loading existing FAISS index from {FAISS_INDEX}...")
            self.index = faiss.read_index(str(FAISS_INDEX))
            if FAISS_IDS.exists():
                with open(FAISS_IDS) as f:
                    self.ids = json.load(f)
            print(f"Loaded index: {self.index.ntotal} vectors")
        else:
            print(f"Creating new FAISS index (dim={dim})...")
            # Use IndexFlatIP for inner product (cosine sim with normalized vectors)
            self.index = faiss.IndexFlatIP(dim)
            self.ids = []
    
    def add(self, embeddings: List[List[float]], chunk_ids: List[int]):
        """Add embeddings with their chunk IDs."""
        import faiss
        import numpy as np
        vectors = np.array(embeddings, dtype=np.float32)
        self.index.add(vectors)
        self.ids.extend(chunk_ids)
    
    def search(self, query: List[float], top_k: int = 10) -> List[Tuple[int, float]]:
        """Search for similar vectors. Returns [(chunk_id, score), ...]"""
        import numpy as np
        q = np.array([query], dtype=np.float32)
        scores, indices = self.index.search(q, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.ids):
                results.append((self.ids[idx], float(score)))
        return results
    
    def save(self):
        """Save index and ID mapping to disk."""
        import faiss
        faiss.write_index(self.index, str(FAISS_INDEX))
        with open(FAISS_IDS, 'w') as f:
            json.dump(self.ids, f)
        print(f"Saved FAISS index: {self.index.ntotal} vectors")
    
    @property
    def size(self) -> int:
        return self.index.ntotal if self.index else 0


# ═══════════════════════════════════════════════════════════════════════
# SESSION BRAIN
# ═══════════════════════════════════════════════════════════════════════

class SessionBrain:
    """Main class: parse, embed, store, query DSH sessions."""
    
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.db = sqlite3.connect(str(BRAIN_DB))
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self._init_db()
        self.embedder = None
        self.vector_store = None
    
    def _init_db(self):
        self.db.executescript(SCHEMA)
        self.db.commit()
    
    def _ensure_embedder(self):
        if self.embedder is None:
            self.embedder = Embedder()
    
    def _ensure_vector_store(self):
        if self.vector_store is None:
            self._ensure_embedder()
            self.vector_store = VectorStore(self.embedder.dim)
    
    def _get_sessions(self) -> Dict[str, Dict]:
        """Get all sessions from DB."""
        rows = self.db.execute(
            "SELECT id, title, last_modified, last_ingested, chunk_count, status FROM sessions"
        ).fetchall()
        return {r[0]: {"id": r[0], "title": r[1], "last_modified": r[2],
                        "last_ingested": r[3], "chunk_count": r[4], "status": r[5]}
                for r in rows}
    
    def _is_stale(self, filepath: Path) -> bool:
        """Check if session file was modified too recently (still being written)."""
        mtime = filepath.stat().st_mtime
        age_min = (time.time() - mtime) / 60
        return age_min < STALE_SESSION_MIN
    
    def _get_session_files(self) -> List[Path]:
        """Get all session .jsonl.zstd files, sorted by mtime."""
        files = list(SESSIONS_DIR.glob("*/session.jsonl.zstd"))
        files.sort(key=lambda f: f.stat().st_mtime)
        return files
    
    def ingest(self, incremental: bool = False, main_only: bool = False):
        """
        Ingest sessions into the brain.
        
        Args:
            incremental: if True, only process new/changed sessions
            main_only: if True, only ingest main (human) sessions, skip subagents
        """
        start_time = time.time()
        mode = "incremental" if incremental else "full"
        filter_label = " (main sessions only)" if main_only else ""
        print(f"\n{'='*60}")
        print(f"Session Brain — {mode.upper()} INGEST{filter_label}")
        print(f"{'='*60}")
        
        # BUG 4 fix: On full ingest, rebuild FAISS from scratch
        if not incremental:
            print("Full ingest: rebuilding FAISS index from scratch...")
            if FAISS_INDEX.exists():
                FAISS_INDEX.unlink()
            if FAISS_IDS.exists():
                FAISS_IDS.unlink()
            self.vector_store = None  # Force recreation
        
        sessions = self._get_sessions() if incremental else {}
        files = self._get_session_files()
        print(f"Found {len(files)} session files")
        
        sessions_processed = 0
        chunks_created = 0
        
        for i, filepath in enumerate(files):
            session_id = filepath.parent.name
            
            # Check if we need to process this session
            if incremental and session_id in sessions:
                existing = sessions[session_id]
                current_mtime = filepath.stat().st_mtime
                if existing["last_modified"] and existing["last_modified"] >= current_mtime:
                    continue  # Already up to date
            
            # Skip stale sessions (still being written)
            if self._is_stale(filepath):
                continue
            
            print(f"\n[{i+1}/{len(files)}] {session_id[:12]}...", end=" ", flush=True)
            
            # Parse
            title, raw_chunks, created_at_ms, origin = extract_text_from_session(filepath)
            
            # Filter: skip subagent sessions if main_only
            if main_only and origin == "subagent":
                print("(subagent, skipped)")
                continue
            
            if not raw_chunks:
                print("(no content)")
                continue
            
            # Merge and chunk
            chunks = merge_and_chunk(raw_chunks)
            if not chunks:
                print("(no chunks after merge)")
                continue
            
            print(f"{len(chunks)} chunks", end=" ", flush=True)
            
            # Embed
            self._ensure_embedder()
            texts = [c["text"] for c in chunks]
            embeddings = self.embedder.embed(texts)
            
            # Store in FAISS
            self._ensure_vector_store()
            chunk_ids = list(range(
                self.vector_store.size,
                self.vector_store.size + len(chunks)
            ))
            self.vector_store.add(embeddings, chunk_ids)
            
            # BUG 5 fix: Store created_at
            created_at_iso = None
            if created_at_ms:
                try:
                    created_at_iso = datetime.fromtimestamp(
                        created_at_ms / 1000, tz=timezone.utc
                    ).isoformat()
                except (ValueError, OSError):
                    pass
            
            # Store metadata in SQLite
            self.db.execute(
                "INSERT OR REPLACE INTO sessions (id, title, created_at, file_size, last_modified, last_ingested, chunk_count, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, title, created_at_iso, filepath.stat().st_size,
                 filepath.stat().st_mtime, time.time(), len(chunks), "indexed")
            )
            
            # Delete old chunks for this session (in case of re-ingest)
            self.db.execute("DELETE FROM chunks WHERE session_id = ?", (session_id,))
            
            for j, chunk in enumerate(chunks):
                self.db.execute(
                    "INSERT INTO chunks (session_id, chunk_index, text, chunk_type, char_count, token_estimate, embedding_offset) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (session_id, j, chunk["text"], chunk["type"],
                     len(chunk["text"]), len(chunk["text"]) // 4,
                     chunk_ids[j])
                )
            
            self.db.commit()
            sessions_processed += 1
            chunks_created += len(chunks)
            print("✓")
        
        # Save FAISS index
        if self.vector_store and self.vector_store.size > 0:
            self.vector_store.save()
        
        # Log ingest
        duration = time.time() - start_time
        self.db.execute(
            "INSERT INTO ingest_log (started_at, completed_at, sessions_processed, chunks_created, duration_seconds, mode) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(),
             sessions_processed, chunks_created, duration, mode)
        )
        self.db.commit()
        
        print(f"\n{'='*60}")
        print(f"INGEST COMPLETE ({mode})")
        print(f"  Sessions processed: {sessions_processed}")
        print(f"  Chunks created: {chunks_created}")
        print(f"  Total vectors: {self.vector_store.size if self.vector_store else 0}")
        print(f"  Duration: {duration:.1f}s")
        print(f"{'='*60}\n")
    
    def query(self, query_text: str, top_k: int = 10, 
              min_score: float = 0.0) -> List[Dict]:
        """
        Semantic search across all sessions.
        
        Returns list of {text, session_id, score, type, chunk_index}
        """
        self._ensure_embedder()
        self._ensure_vector_store()
        
        if self.vector_store.size == 0:
            print("Brain is empty. Run --ingest first.")
            return []
        
        # Embed query
        query_vec = self.embedder.embed_one(query_text)
        
        # Search
        results = self.vector_store.search(query_vec, top_k=top_k * 2)
        
        # Enrich with metadata
        enriched = []
        for chunk_id, score in results:
            if score < min_score:
                continue
            row = self.db.execute(
                "SELECT c.session_id, c.text, c.chunk_type, c.chunk_index, "
                "s.title FROM chunks c JOIN sessions s ON c.session_id = s.id "
                "WHERE c.embedding_offset = ?",
                (chunk_id,)
            ).fetchone()
            if row:
                enriched.append({
                    "session_id": row[0],
                    "text": row[1][:500],
                    "type": row[2],
                    "chunk_index": row[3],
                    "title": row[4],
                    "score": score
                })
            if len(enriched) >= top_k:
                break
        
        return enriched
    
    def stats(self) -> Dict:
        """Get brain statistics."""
        session_count = self.db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        chunk_count = self.db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        indexed = self.db.execute(
            "SELECT COUNT(*) FROM sessions WHERE status = 'indexed'"
        ).fetchone()[0]
        
        last_ingest = self.db.execute(
            "SELECT completed_at, sessions_processed, chunks_created, duration_seconds, mode "
            "FROM ingest_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        
        # Type breakdown
        type_counts = self.db.execute(
            "SELECT chunk_type, COUNT(*) FROM chunks GROUP BY chunk_type"
        ).fetchall()
        
        # FAISS size
        faiss_size = FAISS_INDEX.stat().st_size if FAISS_INDEX.exists() else 0
        
        return {
            "sessions_total": session_count,
            "sessions_indexed": indexed,
            "chunks_total": chunk_count,
            "chunk_types": {t: c for t, c in type_counts},
            "faiss_index_size_mb": round(faiss_size / 1024 / 1024, 1),
            "last_ingest": {
                "completed_at": last_ingest[0] if last_ingest else None,
                "sessions": last_ingest[1] if last_ingest else 0,
                "chunks": last_ingest[2] if last_ingest else 0,
                "duration_s": last_ingest[3] if last_ingest else 0,
                "mode": last_ingest[4] if last_ingest else None,
            } if last_ingest else None,
            "db_size_mb": round(BRAIN_DB.stat().st_size / 1024 / 1024, 1) if BRAIN_DB.exists() else 0,
        }


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Session Brain — RAG for DSH sessions")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ingest", action="store_true", help="Full ingest of all sessions")
    group.add_argument("--update", action="store_true", help="Incremental update (new/changed only)")
    group.add_argument("--query", type=str, help="Semantic search query")
    group.add_argument("--stats", action="store_true", help="Show brain statistics")
    parser.add_argument("--main-only", action="store_true",
                        help="Only ingest main (human) sessions, skip subagents")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results for query")
    parser.add_argument("--min-score", type=float, default=0.0, help="Minimum similarity score")
    
    args = parser.parse_args()
    brain = SessionBrain()
    
    if args.ingest:
        brain.ingest(incremental=False, main_only=args.main_only)
    elif args.update:
        brain.ingest(incremental=True, main_only=args.main_only)
    elif args.query:
        results = brain.query(args.query, top_k=args.top_k, min_score=args.min_score)
        if not results:
            print("No results found.")
            return
        print(f"\n{'='*60}")
        print(f"QUERY: {args.query}")
        print(f"RESULTS: {len(results)}")
        print(f"{'='*60}\n")
        for i, r in enumerate(results, 1):
            print(f"[{i}] score={r['score']:.3f} | {r['type']} | session={r['session_id'][:12]}")
            print(f"    title: {r['title'][:80]}")
            print(f"    text: {r['text'][:200]}")
            print()
    elif args.stats:
        s = brain.stats()
        print(f"\n{'='*60}")
        print("SESSION BRAIN STATS")
        print(f"{'='*60}")
        print(f"  Sessions: {s['sessions_indexed']}/{s['sessions_total']} indexed")
        print(f"  Chunks: {s['chunks_total']}")
        print(f"  Chunk types: {s['chunk_types']}")
        print(f"  FAISS index: {s['faiss_index_size_mb']} MB")
        print(f"  SQLite DB: {s['db_size_mb']} MB")
        if s['last_ingest']:
            li = s['last_ingest']
            print(f"  Last ingest: {li['completed_at']}")
            print(f"    Sessions: {li['sessions']}, Chunks: {li['chunks']}")
            print(f"    Duration: {li['duration_s']:.1f}s ({li['mode']})")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
