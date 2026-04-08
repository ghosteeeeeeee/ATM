#!/usr/bin/env python3
"""
Brain Metadata Extractor
Uses Qwen to extract metadata from user thoughts/inputs
"""

import json
import subprocess
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os

# Database connection — use centralized secrets, fail fast if missing
try:
    from _secrets import BRAIN_DB_DICT
    DB_CONFIG = BRAIN_DB_DICT.copy()
    # Override port if not set in secrets
    DB_CONFIG.setdefault('port', 5432)
except ImportError:
    raise RuntimeError(
        "Cannot import _secrets.BRAIN_DB_DICT. "
        "Ensure /root/.hermes/.secrets.local exists with BRAIN_DB_PASSWORD set."
    )

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5:1.5b"
EMBED_MODEL = "nomic-embed-text"

# Ollama health/robustness tracking
ollama_truncation_count = 0

EXTRACTION_PROMPT = """Extract structured metadata from the following thought/input.

Return ONLY valid JSON (no markdown, no explanation) with these fields:
- people: list of names of people mentioned
- topics: list of topics/subjects discussed
- action_items: list of action items or tasks mentioned
- sentiment: one of [positive, negative, neutral, mixed]
- entities: list of companies, products, or organizations
- summary: 1-sentence summary of the core idea

Input: "{content}"

Output JSON:"""

def call_ollama(prompt: str) -> dict:
    """Call Ollama API to extract metadata. Truncates prompts >3000 tokens."""
    global ollama_truncation_count

    # ── Context guard: truncate prompts >3000 tokens (rough: len/4) ─────────────
    rough_tokens = len(prompt) // 4
    if rough_tokens > 3000:
        prompt = prompt[-8000:]   # last ~2000 tokens
        ollama_truncation_count += 1
        print(f"[brain.py] Ollama prompt truncated ({rough_tokens}→~2000 tokens, "
              f"total truncations={ollama_truncation_count})")

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    try:
        import requests as _req
        resp = _req.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=60)
        resp.raise_for_status()
        response = resp.json()
        raw_resp = response.get("response", "{}")

        # ── Validate response contains required fields ──────────────────────────
        if "DECISION:" not in raw_resp or "CONFIDENCE:" not in raw_resp:
            print(f"[brain.py] Ollama response validation failed — missing DECISION/CONFIDENCE")
            return {}  # safe default

        return json.loads(raw_resp)
    except Exception as e:
        print(f"[brain.py] Ollama call failed: {e}")
        return {}  # safe default

def get_embedding(text: str) -> list:
    """Get vector embedding for text using nomic-embed-text"""
    payload = {
        "model": EMBED_MODEL,
        "prompt": text
    }
    
    import requests as _req
    resp = _req.post(f"{OLLAMA_URL}/api/embeddings", json=payload, timeout=30)
    resp.raise_for_status()
    response = resp.json()
    return response.get("embedding", [])

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        database=DB_CONFIG['database'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password']
    )

def store_thought(content: str, metadata: dict, source: str = "cli", session_id: str = None):
    """Store thought and metadata in database"""
    # Generate embedding
    print(f"Generating embedding...")
    embedding = get_embedding(content)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Insert thought with embedding
            cur.execute("""
                INSERT INTO thoughts (content, embedding, source, session_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (content, embedding, source, session_id))
            thought_id = cur.fetchone()[0]
            
            # Insert metadata
            for key, value in metadata.items():
                if isinstance(value, list):
                    for v in value:
                        cur.execute("""
                            INSERT INTO metadata (thought_id, key, value)
                            VALUES (%s, %s, %s)
                        """, (thought_id, key, str(v)))
                else:
                    cur.execute("""
                        INSERT INTO metadata (thought_id, key, value)
                        VALUES (%s, %s, %s)
                    """, (thought_id, key, str(value)))
            
            conn.commit()
            return thought_id
    finally:
        conn.close()

def extract_and_store(content: str, source: str = "cli", session_id: str = None) -> dict:
    """Main function: extract metadata and store"""
    # Build prompt
    prompt = EXTRACTION_PROMPT.format(content=content)
    
    # Extract metadata
    print(f"Extracting metadata...")
    metadata = call_ollama(prompt)
    
    # Store in database
    print(f"Storing thought in database...")
    thought_id = store_thought(content, metadata, source, session_id)
    
    return {"thought_id": thought_id, "metadata": metadata}

def search_memories(query: str, limit: int = 5) -> list:
    """Search memories by content (simple text search for now)"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t.id, t.content, t.created_at, t.source,
                       array_agg(json_build_object('key', m.key, 'value', m.value)) as metadata
                FROM thoughts t
                LEFT JOIN metadata m ON m.thought_id = t.id
                WHERE t.content ILIKE %s
                GROUP BY t.id
                ORDER BY t.created_at DESC
                LIMIT %s
            """, (f"%{query}%", limit))
            return cur.fetchall()
    finally:
        conn.close()

def semantic_search(query: str, limit: int = 5) -> list:
    """Search memories by semantic similarity (vector search)"""
    print(f"Generating query embedding...")
    query_embedding = get_embedding(query)
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t.id, t.content, t.created_at, t.source,
                       1 - (t.embedding <=> %s::vector) as similarity,
                       array_agg(json_build_object('key', m.key, 'value', m.value)) as metadata
                FROM thoughts t
                LEFT JOIN metadata m ON m.thought_id = t.id
                WHERE t.embedding IS NOT NULL
                GROUP BY t.id
                ORDER BY t.embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, limit))
            return cur.fetchall()
    finally:
        conn.close()

def get_stats() -> dict:
    """Get brain statistics"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM thoughts) as total_thoughts,
                    (SELECT COUNT(*) FROM metadata) as total_metadata,
                    (SELECT MIN(created_at) FROM thoughts) as oldest_thought,
                    (SELECT MAX(created_at) FROM thoughts) as newest_thought
            """)
            return dict(cur.fetchone())
    finally:
        conn.close()

def add_tag(thought_id: int, tag: str) -> bool:
    """Add a tag to a thought"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO meta_tags (thought_id, tag)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (thought_id, tag.lower()))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()

def link_thoughts(source_id: int, target_id: int, link_type: str = "related") -> bool:
    """Link two thoughts together"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO thought_links (source_id, target_id, link_type)
                VALUES (%s, %s, %s)
                ON CONFLICT (source_id, target_id) DO NOTHING
            """, (source_id, target_id, link_type))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()

def get_related_thoughts(thought_id: int) -> list:
    """Get all related thoughts"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t.id, t.content, t.created_at, tl.link_type
                FROM thought_links tl
                JOIN thoughts t ON t.id = tl.target_id
                WHERE tl.source_id = %s
                UNION
                SELECT t.id, t.content, t.created_at, tl.link_type
                FROM thought_links tl
                JOIN thoughts t ON t.id = tl.source_id
                WHERE tl.target_id = %s
                ORDER BY created_at DESC
            """, (thought_id, thought_id))
            return cur.fetchall()
    finally:
        conn.close()

def get_thoughts_by_tag(tag: str) -> list:
    """Get all thoughts with a specific tag"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t.id, t.content, t.created_at, t.source
                FROM thoughts t
                JOIN meta_tags mt ON mt.thought_id = t.id
                WHERE mt.tag = %s
                ORDER BY t.created_at DESC
            """, (tag.lower(),))
            return cur.fetchall()
    finally:
        conn.close()

def add_trade(token: str, side_type: str, amount_usdt: float, entry_price: float,
               exchange: str = "Hyperliquid", strategy: str = None, paper: bool = True,
               stop_loss: float = None, target: float = None, server: str = "Hermes",
               signal: str = None, confidence: float = None, address: str = None,
               sl_group: str = "control", sl_distance: float = None,
               trailing_activation: float = None, trailing_distance: float = None,
               trailing_phase2_dist: float = None,
               leverage: int = 1, experiment: str = None,
               flipped_from_trade: bool = False):
    """Add a new trade to the trades table"""
    # FIX (2026-04-05): Block conf-1s at the trades DB level — confluence means
    # ≥2 signals agreeing. num_signals=1 is not confluence, it's a single source.
    # This catches cases where the signal DB source passed the conf-1s block but
    # the strategy field (Hermes-conf-1s) slipped through to the trades DB.
    if strategy and strategy.startswith('Hermes-conf-'):
        try:
            num = int(strategy.split('-')[-1].rstrip('s'))
            if num == 1:
                print(f"✗ REJECTED: {token} {side_type} — conf-1s (single-source, min 2 required)")
                print(f"  Signal: '{signal}' | Strategy: '{strategy}'")
                return None
        except (ValueError, IndexError):
            pass
    if signal == 'conf-1s':
        print(f"✗ REJECTED: {token} {side_type} — conf-1s (single-source, min 2 required)")
        return None
    # Pre-check: dont consume ID if trade already exists
    conn_check = get_db_connection()
    cur_check = conn_check.cursor()
    cur_check.execute("SELECT id FROM trades WHERE token = %s AND server = %s AND status = 'open'", (token, server))
    if cur_check.fetchone():
        cur_check.close()
        conn_check.close()
        return None  # Skip if already open - prevents ID consumption
    cur_check.close()
    conn_check.close()

    side_type = side_type.lower() if side_type else 'long'
    direction = 'LONG' if side_type == 'long' else 'SHORT'
    
    # A/B Test: Assign SL parameters if not provided
    import random
    if sl_distance is None:
        groups = {"control": 0.03, "test_a": 0.015, "test_b": 0.01}
        sl_group = random.choice(list(groups.keys()))
        sl_distance = groups[sl_group]
    if trailing_activation is None:
        trailing_activation = 0.01  # default: activate at +1%
    if trailing_distance is None:
        trailing_distance = 0.01   # default: 1% trailing distance
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO trades (token, direction, amount_usdt, entry_price,
                          exchange, strategy, paper, stop_loss, target, server, status, open_time,
                          signal, confidence, token_address, pnl_usdt, pnl_pct,
                          sl_distance, trailing_activation, trailing_distance,
                          trailing_phase2_dist, leverage, experiment,
                          flipped_from_trade, flip_variant)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (token, direction, amount_usdt, entry_price,
          exchange, strategy, paper, stop_loss, target, server, 'open',
          signal, confidence, address, 0, 0,
          sl_distance, trailing_activation, trailing_distance,
          trailing_phase2_dist, leverage, experiment,
          int(flipped_from_trade) if flipped_from_trade else 0, 'signal-flip'))
    trade_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    # ── Mirror to Hyperliquid (real trade) ───────────────────────
    # Respects kill switch: mirror_open checks is_live_trading_enabled() internally.
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from hyperliquid_exchange import mirror_open, hype_coin, is_live_trading_enabled
        if is_live_trading_enabled():
            # HOT-SET GUARD: only mirror trades for tokens in the hot-set
            hype_token = hype_coin(token)
            from hermes_constants import HOTSET_BLOCKLIST
            try:
                import sqlite3
                conn_s = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
                cur_s = conn_s.cursor()
                cur_s.execute("SELECT 1 FROM signals WHERE token=? AND hot_cycle_count>=1 LIMIT 1", (hype_token,))
                in_hot = cur_s.fetchone() is not None
                conn_s.close()
            except Exception:
                in_hot = False  # Fail open on DB errors
            blocked = hype_token.upper() in HOTSET_BLOCKLIST
            if blocked:
                # FIX (2026-04-05): Don't close the paper trade. Keep it open for
                # tracking/audit. Just skip the HL mirror — don't destroy the paper trail.
                print(f"[brain.py] {hype_token}: on HOTSET_BLOCKLIST ({direction}) — paper trade #{trade_id} kept (no HL mirror)")
                # Return trade_id so brain DB has the paper record, but no HL position
            else:
                # Read back leverage for this trade
                conn2 = get_db_connection()
                cur2 = conn2.cursor()
                cur2.execute("SELECT leverage FROM trades WHERE id = %s", (trade_id,))
                row = cur2.fetchone()
                lev = int(row[0]) if row else 1
                cur2.close(); conn2.close()

                result = mirror_open(hype_token, direction, float(entry_price), leverage=lev)
                if result.get("success"):
                    # Plan A: record actual HL fill price as ground truth entry
                    hl_entry = result.get("hl_entry_price") or result.get("entry_price")
                    print(f"[brain.py] HYPE ✅ mirror_open SUCCESS: {direction} {result.get('size')} {hype_token} @ ${result.get('entry_price')} "
                          f"(HL_fill=${hl_entry:.6f}) leverage={lev}x (trade #{trade_id})")
                    # Update trade with ground-truth HL entry price
                    conn3 = get_db_connection()
                    cur3 = conn3.cursor()
                    cur3.execute("""
                        UPDATE trades SET entry_price = %s, hl_entry_price = %s
                        WHERE id = %s
                    """, (hl_entry, hl_entry, trade_id))
                    conn3.commit()
                    cur3.close(); conn3.close()

                    # BUG-FIX: Place SL + TP on HL immediately after entry
                    # (B3: no SL/TP was placed on initial entry — fixed here)
                    sz = result.get('size')
                    if sz and is_live_trading_enabled():
                        # Read SL and TP from the trade record
                        conn_sl = get_db_connection()
                        cur_sl = conn_sl.cursor()
                        cur_sl.execute("SELECT stop_loss, target FROM trades WHERE id = %s", (trade_id,))
                        sl_row = cur_sl.fetchone()
                        cur_sl.close(); conn_sl.close()
                        if sl_row and sl_row[0]:
                            from hyperliquid_exchange import place_sl as hl_place_sl, place_tp as hl_place_tp
                            sl_result = hl_place_sl(hype_token, direction, float(sl_row[0]), float(sz))
                            tp_result = hl_place_tp(hype_token, direction, float(sl_row[1]), float(sz)) if sl_row[1] else {"success": True}
                            if sl_result.get("success"):
                                print(f"[brain.py] ✅ SL placed on HL: {hype_token} {direction} SL=${sl_row[0]:.6f} TP=${sl_row[1]:.6f if sl_row[1] else 'N/A'}")
                                # Record HL order IDs for TP/SL (needed for cancel/replace)
                                hl_sl_oid = sl_result.get("order_id")
                                hl_tp_oid = tp_result.get("order_id") if tp_result.get("success") else None
                                if hl_sl_oid or hl_tp_oid:
                                    conn_oid = get_db_connection()
                                    cur_oid = conn_oid.cursor()
                                    cur_oid.execute("""
                                        UPDATE trades SET hl_sl_order_id = %s, hl_tp_order_id = %s
                                        WHERE id = %s
                                    """, (hl_sl_oid, hl_tp_oid, trade_id))
                                    conn_oid.commit()
                                    cur_oid.close(); conn_oid.close()
                                    print(f"[brain.py] 📝 Recorded HL order IDs: sl={hl_sl_oid}, tp={hl_tp_oid}")
                            else:
                                print(f"[brain.py] ⚠️ SL placement failed: {sl_result.get('error')} (non-fatal, paper still open)")
                else:
                    print(f"[brain.py] HYPE mirror_open blocked/failed: {result.get('message')}")
        else:
            print(f"[brain.py] Live trading OFF — paper trade {trade_id} not mirrored")
    except Exception as e:
        print(f"[brain.py] HYPE mirror_open failed (non-fatal): {e}")

    return trade_id

def close_trade(trade_id: int, exit_price: float, pnl_usdt: float = None, notes: str = None):
    """Close an existing trade. Uses Hyperliquid as ground truth for PnL (Plan B).

    After closing, queries HL /my_trades for realized PnL and updates:
        hype_pnl_usdt, hype_pnl_pct, exit_price (HL ground truth)
    Falls back to signal-based PnL calculation if HL query fails.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Get trade metadata
    cur.execute("""SELECT entry_price, amount_usdt, direction, leverage,
                          token, open_time FROM trades WHERE id = %s""", (trade_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return False

    entry_price, amount_usdt, direction, stored_lev, token, open_time = row
    lev = float(stored_lev or 1)
    amount_usdt = float(amount_usdt or 50)

    # ── Plan B: Get HL realized PnL (ground truth) ─────────────────────────────
    hype_pnl_usdt = None
    hype_pnl_pct  = None
    hl_exit_price = None

    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from hyperliquid_exchange import get_realized_pnl, mirror_close
        from datetime import datetime

        # Convert open_time to ms timestamp
        if open_time:
            if isinstance(open_time, str):
                dt = datetime.fromisoformat(open_time.replace('Z', '+00:00'))
            else:
                dt = open_time
            start_ms = int(dt.timestamp() * 1000)
        else:
            # Fallback: last 24 hours
            start_ms = int((datetime.now().timestamp() - 86400) * 1000)

        # Query HL for realized PnL for this token
        hl_data = get_realized_pnl(token.upper(), start_ms)

        if hl_data and hl_data.get("realized_pnl") is not None:
            hype_pnl_usdt = hl_data["realized_pnl"]
            hype_pnl_pct  = (hype_pnl_usdt / amount_usdt * 100) if amount_usdt else 0
            hl_exit_price = hl_data.get("exit_price") or exit_price
            print(f"[close_trade] HL ground truth — {token} pnl={hype_pnl_usdt:+.4f} ({hype_pnl_pct:+.2f}%) "
                  f"exit={hl_exit_price:.6f}")
        else:
            print(f"[close_trade] HL no fill data for {token}, using signal calc")

    except Exception as e:
        print(f"[close_trade] HL sync failed (non-fatal): {e}")

    # ── Fallback: signal-based PnL ─────────────────────────────────────────────
    if hype_pnl_usdt is None:
        if direction and direction.upper() == 'LONG':
            hype_pnl_usdt = ((float(exit_price) - float(entry_price or 1))
                             * amount_usdt * lev / float(entry_price or 1))
        else:
            hype_pnl_usdt = ((float(entry_price or 1) - float(exit_price))
                             * amount_usdt * lev / float(entry_price or 1))
        hype_pnl_pct = (hype_pnl_usdt / amount_usdt * 100) if amount_usdt else 0

    # Use HL exit price if available, else signal exit price
    final_exit = hl_exit_price or exit_price

    # ── Write to DB ────────────────────────────────────────────────────────────
    # close_reason: use notes if provided, else default to 'manual_close'
    close_reason_val = notes if notes else 'manual_close'
    cur.execute("""
        UPDATE trades SET
            exit_price    = %s,
            pnl_usdt      = %s,
            pnl_pct       = %s,
            hype_pnl_usdt = %s,
            hype_pnl_pct  = %s,
            status        = 'closed',
            close_time    = NOW(),
            close_reason  = %s,
            notes         = COALESCE(%s, '')
        WHERE id = %s
    """, (final_exit, hype_pnl_usdt, hype_pnl_pct, hype_pnl_usdt, hype_pnl_pct, close_reason_val, notes, trade_id))

    conn.commit()
    cur.close()
    conn.close()
    return True

def list_trades(status: str = None, limit: int = 20):
    """List trades from the database"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if status:
        cur.execute("""
            SELECT * FROM trades 
            WHERE status = %s 
            ORDER BY open_time DESC LIMIT %s
        """, (status, limit))
    else:
        cur.execute("SELECT * FROM trades ORDER BY open_time DESC LIMIT %s", (limit,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

def backfill_embeddings():
    """Backfill embeddings for thoughts without them"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, content FROM thoughts WHERE embedding IS NULL")
            thoughts = cur.fetchall()
            
            if not thoughts:
                print("All thoughts already have embeddings!")
                return
            
            print(f"Backfilling {len(thoughts)} embeddings...")
            for t in thoughts:
                print(f"  Generating embedding for thought #{t['id']}...")
                embedding = get_embedding(t['content'])
                cur.execute("UPDATE thoughts SET embedding = %s WHERE id = %s", (embedding, t['id']))
            
            conn.commit()
            print(f"Backfilled {len(thoughts)} embeddings!")
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  brain.py add \"Your thought here\"")
        print("  brain.py search \"query\"           # Text search")
        print("  brain.py semantic \"query\"        # AI semantic search")
        print("  brain.py stats")
        print("  brain.py tag <thought_id> <tag>")
        print("  brain.py link <source_id> <target_id> [type]")
        print("  brain.py related <thought_id>")
        print("  brain.py bytag <tag>")
        print("  brain.py trade add <token> <side> <amt> <entry> [options]")
        print("  brain.py trade close <id> <exit_price>")
        print("  brain.py trade list [--status open|closed] [--limit N]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "add":
        content = " ".join(sys.argv[2:])
        result = extract_and_store(content, source="cli")
        print(f"Stored thought #{result['thought_id']}")
        print(f"Metadata: {json.dumps(result['metadata'], indent=2)}")
    
    elif command == "search":
        query = " ".join(sys.argv[2:])
        results = search_memories(query)
        print(f"Found {len(results)} results:")
        for r in results:
            print(f"\n--- Thought #{r['id']} ---")
            print(f"Content: {r['content'][:200]}...")
            print(f"Date: {r['created_at']}")
            print(f"Source: {r['source']}")
    
    elif command == "semantic":
        query = " ".join(sys.argv[2:])
        results = semantic_search(query)
        print(f"Found {len(results)} semantic results:")
        for r in results:
            similarity = round(r['similarity'] * 100, 1)
            print(f"\n--- Thought #{r['id']} (similarity: {similarity}%) ---")
            print(f"Content: {r['content'][:200]}...")
            print(f"Date: {r['created_at']}")
            print(f"Source: {r['source']}")
    
    elif command == "stats":
        stats = get_stats()
        print(f"Total thoughts: {stats['total_thoughts']}")
        print(f"Total metadata entries: {stats['total_metadata']}")
        print(f"Oldest thought: {stats['oldest_thought']}")
        print(f"Newest thought: {stats['newest_thought']}")
    
    elif command == "tag":
        if len(sys.argv) < 4:
            print("Usage: brain.py tag <thought_id> <tag>")
            sys.exit(1)
        thought_id = int(sys.argv[2])
        tag = sys.argv[3]
        if add_tag(thought_id, tag):
            print(f"Added tag '{tag}' to thought #{thought_id}")
        else:
            print(f"Tag '{tag}' already exists for thought #{thought_id}")
    
    elif command == "link":
        if len(sys.argv) < 4:
            print("Usage: brain.py link <source_id> <target_id> [type]")
            sys.exit(1)
        source_id = int(sys.argv[2])
        target_id = int(sys.argv[3])
        link_type = sys.argv[4] if len(sys.argv) > 4 else "related"
        if link_thoughts(source_id, target_id, link_type):
            print(f"Linked thought #{source_id} -> #{target_id} ({link_type})")
        else:
            print(f"Link already exists between #{source_id} and #{target_id}")
    
    elif command == "related":
        if len(sys.argv) < 3:
            print("Usage: brain.py related <thought_id>")
            sys.exit(1)
        thought_id = int(sys.argv[2])
        related = get_related_thoughts(thought_id)
        print(f"Found {len(related)} related thoughts:")
        for r in related:
            print(f"\n--- Thought #{r['id']} ({r['link_type']}) ---")
            print(f"Content: {r['content'][:150]}...")
            print(f"Date: {r['created_at']}")
    
    elif command == "bytag":
        if len(sys.argv) < 3:
            print("Usage: brain.py bytag <tag>")
            sys.exit(1)
        tag = sys.argv[2]
        thoughts = get_thoughts_by_tag(tag)
        print(f"Found {len(thoughts)} thoughts with tag '{tag}':")
        for t in thoughts:
            print(f"\n--- Thought #{t['id']} ---")
            print(f"Content: {t['content'][:150]}...")
            print(f"Date: {t['created_at']}")
    
    elif command == "backfill":
        backfill_embeddings()
    
    elif command == "trade":
        # brain.py trade add <token> <side> <amount> <entry> [--exchange X] [--strategy X] [--paper] [--real] [--sl X] [--target X] [--server X]
        # brain.py trade close <id> <exit_price> [pnl]
        # brain.py trade list [open|closed] [limit]
        import argparse
        parser = argparse.ArgumentParser(prog="brain.py trade")
        subparsers = parser.add_subparsers(dest="subcommand", help="Trade subcommands")
        
        add_parser = subparsers.add_parser("add", help="Add a new trade")
        add_parser.add_argument("token", help="Token/symbol")
        add_parser.add_argument("side", choices=["long","short"], help="long or short")
        add_parser.add_argument("amount", type=float, help="Amount in USDT")
        add_parser.add_argument("entry", type=float, help="Entry price")
        add_parser.add_argument("--exchange", default="Hyperliquid", help="Exchange name")
        add_parser.add_argument("--strategy", help="Strategy name")
        add_parser.add_argument("--paper", action="store_true", default=False, help="Paper trade")
        add_parser.add_argument("--real", action="store_true", help="Real trade (not paper)")
        add_parser.add_argument("--sl", type=float, help="Stop loss price")
        add_parser.add_argument("--target", type=float, help="Target price")
        add_parser.add_argument("--server", default="Tokyo", help="Server (Tokyo/Dallas)")
        add_parser.add_argument("--signal", help="Signal source (alert/script/webhook)")
        add_parser.add_argument("--address", help="Token contract address")
        add_parser.add_argument("--confidence", type=float, help="Confidence factor (0-100)")
        add_parser.add_argument("--sl-group", choices=["control", "test_a", "test_b"], default="control", help="A/B test group for SL distance")
        add_parser.add_argument("--sl-distance", type=float, help="SL distance (0.005 = 0.5%%, 0.01 = 1%%)")
        add_parser.add_argument("--trailing-threshold", type=float, dest="trailing_activation", help="Trailing activation threshold")
        add_parser.add_argument("--trailing-distance", type=float, dest="trailing_distance", help="Trailing distance (e.g. 0.010 = 1%)")
        add_parser.add_argument("--trailing-phase2", type=float, dest="trailing_phase2", help="Phase 2 trailing distance (tighter, activates after phase 1)")
        add_parser.add_argument("--leverage", type=int, default=1, help="Leverage (1-10)")
        add_parser.add_argument("--experiment", help="A/B test experiment info (JSON)")
        add_parser.add_argument("--flipped", action="store_true", default=False,
                                help="Mark this trade as flipped from original signal direction")
        
        close_parser = subparsers.add_parser("close", help="Close a trade")
        close_parser.add_argument("id", type=int, help="Trade ID")
        close_parser.add_argument("exit_price", type=float, help="Exit price")
        close_parser.add_argument("--pnl", type=float, help="Manual PnL override")
        close_parser.add_argument("--notes", help="Exit notes")
        
        list_parser = subparsers.add_parser("list", help="List trades")
        list_parser.add_argument("--status", choices=["open", "closed"], help="Filter by status")
        list_parser.add_argument("--limit", type=int, default=20, help="Limit results")
        
        args = parser.parse_args(sys.argv[2:])
        
        if args.subcommand == "add":
            trade_id = add_trade(
                token=args.token,
                side_type=args.side,  # long or short (positional)
                amount_usdt=args.amount,
                entry_price=args.entry,
                exchange=args.exchange,
                strategy=args.strategy,
                paper=not args.real,
                stop_loss=args.sl,
                target=args.target,
                server=args.server,
                signal=args.signal,
                address=args.address,
                confidence=args.confidence,
                sl_group=args.sl_group,
                sl_distance=args.sl_distance,
                trailing_activation=args.trailing_activation or None,
                trailing_distance=args.trailing_distance or None,
                trailing_phase2_dist=args.trailing_phase2 or None,
                leverage=args.leverage,
                experiment=args.experiment,
                flipped_from_trade=args.flipped
            )
            if trade_id is None:
                sys.exit(1)  # Signal was rejected — propagate failure to caller
            print(f"✓ Added trade #{trade_id}: {args.side.upper()} {args.amount} USDT {args.token} @ ${args.entry}")
            print(f"  Exchange: {args.exchange} | Server: {args.server} | Paper: {not args.real} | Signal: {args.signal or 'N/A'} | Lev: {args.leverage}x")
        
        elif args.subcommand == "close":
            close_trade(args.id, args.exit_price, args.pnl, args.notes)
            print(f"✓ Closed trade #{args.id} @ ${args.exit_price}")
        
        elif args.subcommand == "list":
            trades = list_trades(args.status, args.limit)
            print(f"\n{'ID':<4} {'Token':<10} {'Side':<6} {'Amount':<10} {'Entry':<10} {'Exit':<8} {'PnL%':<8} {'Status':<8} {'Server':<8}")
            print("-" * 80)
            for t in trades:
                pnl = t.get('pnl_pct', 0) or 0
                exit_price = t.get('exit_price') or 0
                amount = t.get('amount_usdt') or 0
                entry = t.get('entry_price') or 0
                print(f"{t['id']:<4} {t['token']:<10} {t.get('direction', 'N/A'):<6} ${amount:<9.2f} ${entry:<9.2f} ${exit_price:<8.2f} {pnl:>6.2f}% {t['status']:<8} {t.get('server', 'Tokyo'):<8}")
        
        else:
            parser.print_help()
        sys.exit(0)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
