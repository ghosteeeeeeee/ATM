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
import paths  # noqa: F401 — single source of truth for paths
import subprocess
import time as _time
import random
from datetime import datetime

# ── Loss cooldown helpers ─────────────────────────────────────────────────────
from hermes_file_lock import FileLock
from hermes_constants import LOSS_COOLDOWN_FILE, LOSS_COOLDOWN_BASE, LOSS_COOLDOWN_MAX, DEFAULT_TRADE_SIZE_USDT, HL_MIN_NOTIONAL_USDT
from pnl_utils import compute_close_pnl

def _load_cooldowns() -> dict:
    try:
        with open(LOSS_COOLDOWN_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def _save_cooldowns(data: dict) -> None:
    try:
        with FileLock('loss_cooldowns'):
            with open(LOSS_COOLDOWN_FILE, 'w') as f:
                json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[_save_cooldowns] FAILED: {e}")

def _record_loss_cooldown(token: str, direction: str) -> None:
    """Record a loss cooldown for token+direction. Guards against duplicates."""
    key = f"{token.upper()}:{direction.upper()}"
    data = _load_cooldowns()
    existing = data.get(key, {})
    if existing.get('reason') == 'loss':
        return  # pipeline already wrote it
    entry = data.get(key)
    if entry is None:
        streak = 1
    elif isinstance(entry, dict):
        streak = entry.get('streak', 0) + 1
    else:
        streak = 1
    hours = min(LOSS_COOLDOWN_BASE * (2 ** (streak - 1)), LOSS_COOLDOWN_MAX)
    expiry = _time.time() + (hours * 3600)
    data[key] = {'expires': expiry, 'streak': streak, 'hours': hours, 'reason': 'brain'}
    _save_cooldowns(data)
    print(f"[brain.close_trade] LOSS COOLDOWN: {token} {direction} streak={streak} blocked for {hours:.1f}h")

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
               exchange: str = "Hyperliquid", strategy: str = None, paper: bool = False,
               stop_loss: float = None, target: float = None, server: str = "Hermes",
               signal: str = None, confidence: float = None, address: str = None,
               sl_group: str = "control", sl_distance: float = None,
               trailing_activation: float = None, trailing_distance: float = None,
               trailing_phase2_dist: float = None,
               leverage: int = 1, experiment: str = None,
               flipped_from_trade: bool = False,
               # ── Signal indicator fields (captured at entry from hotset) ──
               signal_z_score: float = None,
               signal_rsi_14: float = None,
               signal_macd_hist: float = None,
               signal_macd_value: float = None,
               signal_macd_signal: float = None,
               signal_momentum_state: str = None,
               signal_z_score_tier: str = None,
               signal_decision: str = None,
               signal_leverage: int = None,
               signal_created_at: str = None,
               # ── A/B test variant tags ──
               test_sl_variant: str = None,
               test_timing_variant: str = None,
               test_trailing_variant: str = None,
               # ── JSONB catch-all for future signal indicators ──
               # Stores arbitrary signal values: {accel_300: {conf: 85}, rs: {bounce: true}}
               # Eliminates need for per-signal columns — new signals just write to this dict.
               signal_metadata: dict = None,
               exp_metadata: dict = None):
    """
    Add a new trade. HL-first: open on Hyperliquid FIRST, write to local DB only
    if HL confirms. Eliminates phantom trades (DB writes deleted when HL fails,
    leaving consumed signals with no corresponding position).
    """
    import sys, os, random

    # ── Normalize direction ──────────────────────────────────────────────
    side_type = side_type.lower() if side_type else 'long'
    direction = 'LONG' if side_type == 'long' else 'SHORT'

    # ── Step 1: Pre-flight checks ───────────────────────────────────────

    # Block conf-1s at the trade entry level
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

    # Block noisy signal sources
    NOISE_SIGNALS = {'pct-hermes', 'vel-hermes', 'rsi-hermes'}
    if signal in NOISE_SIGNALS:
        print(f"✗ REJECTED: {token} {side_type} — noisy signal source '{signal}' blocklisted")
        return None

    # ── Step 2: HL-first — open on Hyperliquid before any DB write ─────
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    # paths already imported at module level (line 13)
    from hyperliquid_exchange import (mirror_open, hype_coin,
                                       is_live_trading_enabled, is_delisted)

    # ── AUDIT: Log open attempt BEFORE any HL/DB call ──────────────────────────
    try:
        from audit_logger import (trade_open_attempt, trade_open_success, trade_open_failed)
        trade_open_attempt(
            token=token.upper(), direction=direction,
            signal=signal or '', entry_price=float(entry_price),
            amount_usdt=float(amount_usdt) if amount_usdt else 0.0,
            source='add_trade')
    except Exception as _a:
        pass  # Never let audit crash the trade path

    print(f"[brain.py] DEBUG is_live_trading_enabled() = {is_live_trading_enabled()}")
    if not is_live_trading_enabled():
        print(f"[brain.py] ❌ REJECTED: {token} {direction} — live_trading is DISABLED")
        print(f"[brain.py] DEBUG token={token}, direction={direction}, entry_price={entry_price}, paper={paper}")
        return None

    if is_delisted(token):
        print(f"[brain.py] ❌ REJECTED: {token} {direction} — delisted on Hyperliquid")
        return None

    hype_token = hype_coin(token)

    # Blacklist check
    from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
    if (direction == 'SHORT' and hype_token in SHORT_BLACKLIST) or \
       (direction == 'LONG'  and hype_token in LONG_BLACKLIST):
        bl = 'SHORT_BLACKLIST' if direction == 'SHORT' else 'LONG_BLACKLIST'
        print(f"[brain.py] ❌ REJECTED: {token} {direction} — blocked by {bl}")
        return None

    # ── Minimum notional check: reject trades below HL minimum ─────────────
    # HL minimum notional is $11 (HL_MIN_NOTIONAL_USDT = $10 + $1 buffer).
    # Trades below this may fail on HL or have severe slippage.
    # Check signal-level amount_usdt as a proxy since actual HL notional
    # isn't known until after mirror_open fills.
    effective_amount = amount_usdt if amount_usdt is not None else DEFAULT_TRADE_SIZE_USDT
    if effective_amount < HL_MIN_NOTIONAL_USDT:
        print(f"[brain.py] ❌ REJECTED: {token} {direction} — amount_usdt={effective_amount} < HL_MIN={HL_MIN_NOTIONAL_USDT} (would fail on HL)")
        return None

    # Duplicate open check (local DB constraint)
    conn_check = get_db_connection()
    cur_check = conn_check.cursor()
    cur_check.execute(
        "SELECT id FROM trades WHERE token=%s AND server=%s AND status='open'", (token, server))
    dup_row = cur_check.fetchone()
    if dup_row:
        print(f"[brain.py] ❌ REJECTED: {token} {direction} — DUPLICATE: open trade exists in PostgreSQL (id={dup_row[0]})")
        cur_check.close(); conn_check.close()
        return None
    cur_check.close(); conn_check.close()
    print(f"[brain.py] ✔ no duplicate open in PostgreSQL for {token}")

    # ── Stale orphan check: reject if DB has a zombie open trade with no HL position ──
    # These are trades left behind by failed mirror_open attempts or guardian orphan
    # closes that didn't clean up properly. Re-opening over them causes double entries.
    try:
        conn_orphan = get_db_connection()
        cur_orphan = conn_orphan.cursor()
        cur_orphan.execute("""
            SELECT id, paper, hl_entry_price, open_time
            FROM trades
            WHERE token=%s AND server=%s AND status='open'
              AND (hl_entry_price IS NULL OR hl_entry_price = 0)
            LIMIT 1
        """, (token, server))
        orphan_row = cur_orphan.fetchone()
        cur_orphan.close(); conn_orphan.close()
        if orphan_row:
            oid, paper_val, hl_ep, open_time = orphan_row
            age_hrs = (datetime.now() - open_time).total_seconds() / 3600 if open_time else 0
            print(f"[brain.py] 🏚️ STALE ORPHAN: {token} id={oid} hl_ep={hl_ep} age={age_hrs:.1f}h — rejecting to prevent double-entry")
            return None
    except Exception as orphan_err:
        print(f"[brain.py] stale orphan check error for {token}: {orphan_err} — proceeding anyway")

    # A/B params (needed for HL order sizing)
    if sl_distance is None:
        groups = {"control": 0.03, "test_a": 0.015, "test_b": 0.01}
        sl_group = random.choice(list(groups.keys()))
        sl_distance = groups[sl_group]
    if trailing_activation is None:
        trailing_activation = 0.01
    if trailing_distance is None:
        trailing_distance = 0.01

    leverage = max(1, min(int(leverage), 5))  # cap at 5x

    # ── Step 3: mirror_open on HL ──────────────────────────────────────
    print(f"[brain.py] → mirror_open({hype_token}, {direction}, entry_price={entry_price}, leverage={leverage})")
    result = mirror_open(hype_token, direction, float(entry_price), leverage=leverage)
    print(f"[brain.py] ← mirror_open returned: success={result.get('success')}, "
          f"size={result.get('size')}, total_sz={result.get('total_sz')}, "
          f"notional_usdt={result.get('notional_usdt')}, entry_price={result.get('entry_price')}")
    if not result.get("success"):
        print(f"[brain.py] ❌ mirror_open FAILED for {hype_token}: {result.get('message')}")
        return None   # ← NO DB write, signal stays alive for retry

    # ── VERIFY: Confirm HL actually has the position before writing to DB ────
    # mirror_open returning success=True means the order was SENT, not that it filled.
    # We must verify the position appears in /info before committing to DB.
    # This prevents phantom DB records when HL fills are rejected (margin, delist, etc.)
    try:
        from hyperliquid_exchange import get_open_hype_positions
        verify_positions = get_open_hype_positions()
        if not any(p.get('coin', '').upper() == hype_token.upper() and float(p.get('size', 0)) != 0
                   for p in verify_positions):
            print(f"[brain.py] ❌ mirror_open reported success but {hype_token} not in HL positions — rolling back")
            try:
                from hyperliquid_exchange import close_position
                close_position(hype_token)  # clean up any partial fill
            except Exception:
                pass
            return None
        print(f"[brain.py]    ✅ {hype_token} confirmed on HL (verification passed)")
    except Exception as verify_err:
        print(f"[brain.py] ⚠️ HL verification error for {hype_token}: {verify_err} — proceeding on HL confirmation")
        # Proceed if verification fails — mirror_open already succeeded, guardian will catch orphans

    # ── Step 4: HL confirmed — write to local DB ───────────────────────
    hl_entry = result.get("hl_entry_price") or result.get("entry_price")
    sz = result.get("size")
    # Compute actual HL notional from fill data: total_sz × entry_price
    # This is what was actually sent to HL (differs from signal-level size_usdt)
    total_sz = result.get("total_sz")
    fill_px   = result.get("entry_price") or result.get("hl_entry_price")
    if total_sz and fill_px:
        hl_notional = round(total_sz * fill_px, 4)
        print(f"[brain.py]    ✓ hl_notional computed: total_sz={total_sz} × fill_px={fill_px} = {hl_notional}")
    else:
        # [FIX-BUG2] mirror_get_entry_fill fell back — do NOT use signal-level size_usdt
        # Store None so guardian knows to use hype_realized_pnl_usdt as ground truth
        # instead of a corrupted inflated notional
        hl_notional = None
        print(f"[brain.py]    ⚠️ total_sz or fill_px missing — hl_notional=None (guardian will use HL realized PnL)")
        print(f"[brain.py]       total_sz={total_sz}, fill_px={fill_px}, notional_usdt={result.get('notional_usdt')}")
    print(f"[brain.py] → PostgreSQL INSERT for {token} {direction} trade "
          f"(hl_entry={hl_entry}, sz={sz}, hl_notional={hl_notional})")

    conn = get_db_connection()
    cur = conn.cursor()
    # Build _exp_metadata_str BEFORE _params so it can be used as a placeholder
    _exp_metadata_str = json.dumps(exp_metadata, default=str) if exp_metadata else '{}'
    try:
        # DEBUG: Log the tuple construction so we can see exactly what brain.py sends
        # ── DEBUG: log the column-to-position mapping before INSERT ─────────────
        # CRITICAL: column numbers in _col_map MUST match SQL column ordinal position (1-44)
        # SQL has 44 columns: 11 before open_time, open_time=DEFAULT, 32 after
        # TOTAL = 11 + 1 + 32 = 44 columns, 44 placeholders (open_time uses DEFAULT keyword, not %s)
        _col_map = [
            # Col  Name                   Value
            (1,   'token',               token),
            (2,   'direction',           direction),
            (3,   'amount_usdt',          amount_usdt),
            (4,   'entry_price',          hl_entry),
            (5,   'exchange',             exchange),
            (6,   'strategy',             strategy),
            (7,   'paper',                paper),
            (8,   'stop_loss',            stop_loss),
            (9,   'target',               target),
            (10,  'server',               server),
            (11,  'status',               'open'),
            (12,  'open_time',            'now'),  # ← added: was DEFAULT, now explicit param
            (13,  'signal',              signal),
            (14,  'confidence',          confidence),
            (15,  'token_address',        None),
            (16,  'pnl_usdt',            0.0),
            (17,  'pnl_pct',             0.0),
            (18,  'sl_distance',          sl_distance),
            (19,  'trailing_activation',  trailing_activation),
            (20,  'trailing_distance',    trailing_distance),
            (21,  'trailing_phase2_dist', trailing_phase2_dist),
            (22,  'leverage',            leverage),
            (23,  'experiment',           experiment),
            (24,  'flipped_from_trade',   int(flipped_from_trade) if flipped_from_trade else 0),
            (25,  'flip_variant',         'signal-flip'),
            (26,  'hl_entry_price',       hl_entry),
            (27,  'hl_notional_usdt',     hl_notional),
            (28,  'highest_price',        hl_entry if direction == 'LONG' else 0),
            (29,  'lowest_price',         hl_entry if direction == 'SHORT' else 0),
            (30,  'signal_z_score',       signal_z_score),
            (31,  'signal_rsi_14',        signal_rsi_14),
            (32,  'signal_macd_hist',     signal_macd_hist),
            (33,  'signal_macd_value',    signal_macd_value),
            (34,  'signal_macd_signal',   signal_macd_signal),
            (35,  'signal_momentum_state', signal_momentum_state),
            (36,  'signal_z_score_tier',  signal_z_score_tier),
            (37,  'signal_decision',      signal_decision),
            (38,  'signal_leverage',      signal_leverage),
            (39,  'signal_created_at',    signal_created_at),
            (40,  'test_sl_variant',      test_sl_variant),
            (41,  'test_timing_variant',  test_timing_variant),
            (42,  'test_trailing_variant', test_trailing_variant),
            (43,  '_signal_metadata',     json.dumps(signal_metadata, default=str) if signal_metadata else '{}'),
            (44,  '_exp_metadata',        _exp_metadata_str),
        ]
        _params = [row[2] for row in _col_map]
        print(f"[brain.py] DEBUG _col_map: {len(_col_map)} entries → {len(_params)} params")

        # Validate: 44 params must match 44 %s in VALUES
        if len(_params) != 44:
            print(f"[brain.py] ❌ MISMATCH: params={len(_params)} (need 44)")
            for i, (col_num, col_name, val) in enumerate(_col_map):
                print(f"  [{i:2d}] col={col_num:2d} {col_name:30s} = {repr(val)[:60]}")
        else:
            print(f"[brain.py] ✅ 44 params ready")

        # ── ACTUAL INSERT with verbose error capture ─────────────────────────
        # VALUES: 44 %s matching 44 _col_map params (open_time is explicit 'now' string)
        try:
            cur.execute("""
            INSERT INTO trades (token, direction, amount_usdt, entry_price,
                      exchange, strategy, paper, stop_loss, target, server, status, open_time,
                      signal, confidence, token_address, pnl_usdt, pnl_pct,
                      sl_distance, trailing_activation, trailing_distance,
                      trailing_phase2_dist, leverage, experiment,
                      flipped_from_trade, flip_variant,
                      hl_entry_price, hl_notional_usdt,
                      highest_price, lowest_price,
                      signal_z_score, signal_rsi_14, signal_macd_hist,
                      signal_macd_value, signal_macd_signal,
                      signal_momentum_state, signal_z_score_tier,
                      signal_decision, signal_leverage, signal_created_at,
                      test_sl_variant, test_timing_variant, test_trailing_variant,
                      _signal_metadata, _exp_metadata)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """, tuple(_params))
        except Exception as _insert_err:
            print(f"[brain.py] ❌ INSERT EXCEPTION: type={type(_insert_err).__name__} msg={_insert_err}")
            print(f"[brain.py]    params len={len(_params)} first={_params[0] if _params else 'EMPTY'}")
            raise
        trade_id = cur.fetchone()[0]
        conn.commit()
        print(f"[brain.py] ✅ {hype_token} {direction} trade #{trade_id} confirmed on HL @ ${hl_entry:.6f}")
        print(f"[brain.py]    📊 PnL notional: signal-level=${result.get('notional_usdt', 'N/A')} → actual HL=${hl_notional} "
              f"(ratio: {round(hl_notional / float(result.get('notional_usdt', 1)) * 100, 1) if (hl_notional and result.get('notional_usdt')) else 'N/A'}%)")
        # ── AUDIT: Log success ───────────────────────────────────────────────
        try:
            from audit_logger import trade_open_success
            trade_open_success(token=token.upper(), direction=direction,
                               trade_id=int(trade_id), hl_entry_price=float(hl_entry),
                               signal=signal or '', source='add_trade')
        except Exception as _a:
            pass
    except Exception as e:
        # CRITICAL: mirror_open already succeeded — HL has this position live.
        # If DB write fails we MUST roll back the HL position to avoid a phantom live trade.
        # Capture full exception details for debugging
        import traceback
        error_details = traceback.format_exc()
        print(f"[brain.py] ❌ DB INSERT FAILED for {hype_token}: {e}")
        print(f"[brain.py]    Exception type: {type(e).__name__}")
        print(f"[brain.py]    Full traceback:\n{error_details}")
        print(f"[brain.py]    INSERT params: token={token}, direction={direction}, entry={hl_entry}, exchange={exchange}")
        print(f"[brain.py]    hl_notional={hl_notional}, total_sz={total_sz}, fill_px={fill_px}")
        print(f"[brain.py]    Rolling back HL position to prevent phantom live trade...")
        try:
            conn.rollback()
        except Exception as rb_exc:
            print(f"[brain.py]    ⚠️ conn.rollback() failed: {rb_exc}")
        try:
            # Bug-Fix (2026-05-20): mirror_close raises RuntimeError if
            # LIVE_TRADING_ENABLED=False (kill switch), but we need to close
            # the position even when the kill switch is off — the position was
            # already opened under live trading. Use close_position (lower-level,
            # no is_live_trading_enabled() gate) so rollback always works.
            from hyperliquid_exchange import close_position
            result = close_position(hype_token)
            if result and result.get('success'):
                print(f"[brain.py]    ✅ HL rollback succeeded for {hype_token}")
            else:
                print(f"[brain.py]    ⚠️ HL rollback returned: {result}")
        except Exception as mc_err:
            print(f"[brain.py]    ⚠️ HL rollback failed: {mc_err} — {hype_token} may be orphaned on HL!")
            # ── AUDIT: Log failure with orphan flag ─────────────────────────
            try:
                from audit_logger import trade_open_failed
                trade_open_failed(token=token.upper(), direction=direction,
                                  reason=f'DB INSERT failed then HL rollback failed: {mc_err}',
                                  hl_position_left_open=True, source='add_trade')
            except Exception:
                pass
            # [AUDIT] Log the full state at failure point for post-mortem
            print(f"[brain.py]    === AUDIT: DB INSERT FAILURE STATE ===")
            print(f"[brain.py]       coin={hype_token} direction={direction} leverage={leverage}")
            print(f"[brain.py]       hl_entry={hl_entry} sz={sz} hl_notional={hl_notional}")
            print(f"[brain.py]       total_sz={total_sz} fill_px={fill_px}")
            print(f"[brain.py]       signal={signal} confidence={confidence}")
            print(f"[brain.py]       exception={type(mc_err).__name__}: {mc_err}")
            print(f"[brain.py]       HL position may be orphaned — guardian must detect on next sync")
            # Exit with non-zero code so decider_run's signal rollback fires
            # (decider_run.py line 1933 handles sig_id rollback when brain.py returns non-zero)
            sys.exit(1)
    finally:
        cur.close(); conn.close()

    # ── Step 5: Place SL + TP on HL ── DISABLED 2026-05-17 ───────────────
    # TP/SL is now managed LOCALLY by position_manager via DB.
    # HL trigger orders are NOT placed — guardian reads ATR levels from DB.
    if sz and stop_loss:
        pass  # DISABLED — see _execute_atr_bulk_updates (disabled 2026-05-15)

    print(f"[brain.py] ✅ {hype_token} {direction} trade #{trade_id} confirmed on HL @ ${hl_entry:.6f}")
    return trade_id

def close_trade(trade_id: int, exit_price: float, pnl_usdt: float = None,
                 notes: str = None, close_reason: str = None, skip_hl: bool = False):
    """Close an existing trade. Computes PnL from signal prices (no extra HL API calls).

    Args:
        skip_hl: If True, skip HL /info lookup and use signal-based PnL directly.
                 Saves 1 HL API call per close. Use for automated closes (profit-monster,
                 guardian, etc.) where signal exit price is sufficient.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Get trade metadata
    cur.execute("""SELECT entry_price, amount_usdt, direction, leverage,
                          token, open_time, hl_notional_usdt
                   FROM trades WHERE id = %s""", (trade_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return False

    entry_price, amount_usdt, direction, stored_lev, token, open_time, hl_notional_usdt = row
    lev = float(stored_lev or 1)
    # Bug-fix (2026-05-20): `or` treated 0.0 as falsy. Use explicit None check.
    amount_usdt = float(amount_usdt) if amount_usdt is not None else DEFAULT_TRADE_SIZE_USDT
    # Actual HL notional at open — use this for PnL math when available.
    # Bug-Fix (2026-05-20): was `if hl_notional_usdt` which treated 0.0 as falsy,
    # falling back to amount_usdt (~50) and inflating PnL by ~5x for small positions.
    # Use `is not None` so 0.0 is treated as a real value (valid for tiny positions).
    calc_notional = float(hl_notional_usdt) if hl_notional_usdt is not None else amount_usdt

    # ── Get HL realized PnL (ground truth) — skip if skip_hl ───────────────────
    hype_pnl_usdt = None
    hype_pnl_pct  = None
    hl_exit_price = None

    if not skip_hl:
        try:
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from hyperliquid_exchange import get_realized_pnl
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
                # Use actual HL notional for % calculation — this is ground-truth return
                hype_pnl_pct  = (hype_pnl_usdt / calc_notional * 100) if calc_notional else 0
                hl_exit_price = hl_data.get("exit_price") or exit_price
                print(f"[close_trade] HL ground truth — {token} pnl={hype_pnl_usdt:+.4f} ({hype_pnl_pct:+.2f}%) "
                      f"exit={hl_exit_price:.6f}")
            else:
                print(f"[close_trade] HL no fill data for {token}, using signal calc")

        except Exception as e:
            print(f"[close_trade] HL sync failed (non-fatal): {e}")

    # ── Fallback: signal-based PnL ─────────────────────────────────────────────
    if hype_pnl_usdt is None:
        # Use actual HL notional (calc_notional) when available for accurate sizing.
        # When hl_notional_usdt is set, it reflects what was actually sent to HL
        # (≈$7). When not set (legacy trades), falls back to amount_usdt (≈$50).
        # Centralized via pnl_utils (direction-aware, unleveraged).
        pnl_pct, hype_pnl_usdt, _ = compute_close_pnl(
            float(entry_price or 1), float(exit_price), direction, calc_notional
        )
        # pnl_pct from compute_close_pnl is already unleveraged. hype_pnl_usdt is
        # signed (positive for profit, negative for loss). For brain.py we store
        # hype_pnl_usdt and derive hype_pnl_pct from it to stay consistent.
        hype_pnl_pct = (hype_pnl_usdt / calc_notional * 100) if calc_notional else 0

    # Use HL exit price if available and > 0, else signal-provided exit price
    final_exit = hl_exit_price if hl_exit_price and hl_exit_price > 0 else exit_price

    # ── Write to DB ────────────────────────────────────────────────────────────
    # close_reason: explicit param wins, else default to 'manual_close'
    close_reason_val = close_reason if close_reason else 'manual_close'
    # BUG-FIX (2026-04-19): exit_reason was not being set in close_trade().
    # profit_monster and any other caller using brain.py close_trade() would get
    # NULL exit_reason in the trades table, making exit attribution impossible.
    # Fix: write exit_reason = close_reason_val so both columns are always set.
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
            exit_reason   = %s,
            notes         = COALESCE(%s, '')
        WHERE id = %s AND status = 'open'
    """, (final_exit, hype_pnl_usdt, hype_pnl_pct, hype_pnl_usdt, hype_pnl_pct, close_reason_val, close_reason_val, notes, trade_id))

    conn.commit()

    # ── AUDIT: Log trade close ───────────────────────────────────────────
    try:
        from audit_logger import trade_close
        trade_close(trade_id=int(trade_id),
                    token=str(token).upper() if token else '',
                    direction=str(direction).upper() if direction else '',
                    entry_price=float(entry_price) if entry_price else 0.0,
                    exit_price=float(final_exit),
                    pnl_usdt=float(hype_pnl_usdt) if hype_pnl_usdt is not None else 0.0,
                    pnl_pct=float(hype_pnl_pct) if hype_pnl_pct is not None else 0.0,
                    close_reason=str(close_reason_val),
                    hype_realized_pnl_usdt=float(hype_pnl_usdt) if hype_pnl_usdt is not None else None,
                    is_loss=bool(hype_pnl_usdt < 0) if hype_pnl_usdt is not None else None,
                    source='brain_close_trade')
    except Exception:
        pass

    # ── Loss cooldown: record if this was a losing trade ──────────────────
    # FIX (2026-04-28): brain.close_trade() was closing trades without recording
    # loss cooldowns, allowing immediate re-entry after HL TP/SL closes synced
    # via hype-sync.py or profit-monster closes.
    if hype_pnl_usdt is not None and hype_pnl_usdt < 0:
        _record_loss_cooldown(token, direction)

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
        add_parser.add_argument("--signal-z-score", type=float, dest="signal_z_score",
                                help="z_score at signal entry")
        add_parser.add_argument("--signal-rsi-14", type=float, dest="signal_rsi_14",
                                help="RSI-14 at signal entry")
        add_parser.add_argument("--signal-macd-hist", type=float, dest="signal_macd_hist",
                                help="MACD histogram at signal entry")
        add_parser.add_argument("--signal-macd-value", type=float, dest="signal_macd_value",
                                help="MACD value at signal entry")
        add_parser.add_argument("--signal-macd-signal", type=float, dest="signal_macd_signal",
                                help="MACD signal at signal entry")
        add_parser.add_argument("--signal-momentum-state", dest="signal_momentum_state",
                                help="Momentum state at signal entry")
        add_parser.add_argument("--signal-z-score-tier", dest="signal_z_score_tier",
                                help="z_score tier at signal entry")
        add_parser.add_argument("--signal-decision", dest="signal_decision",
                                help="Signal decision at entry")
        add_parser.add_argument("--signal-leverage", type=int, dest="signal_leverage",
                                help="Leverage at signal entry")
        add_parser.add_argument("--signal-created-at", dest="signal_created_at",
                                help="Signal creation timestamp ISO")
        add_parser.add_argument("--test-sl-variant", dest="test_sl_variant",
                                help="A/B test SL variant tag")
        add_parser.add_argument("--test-timing-variant", dest="test_timing_variant",
                                help="A/B test entry timing variant tag")
        add_parser.add_argument("--test-trailing-variant", dest="test_trailing_variant",
                                help="A/B test trailing variant tag")
        add_parser.add_argument("--signal-metadata-json", dest="signal_metadata_json",
                                help="JSON string of all signal metadata at entry (future-proof catch-all)")
        add_parser.add_argument("--exp-metadata-json", dest="exp_metadata_json",
                                help="JSON string of all experiment metadata at entry")
        
        close_parser = subparsers.add_parser("close", help="Close a trade")
        close_parser.add_argument("id", type=int, help="Trade ID")
        close_parser.add_argument("exit_price", type=float, help="Exit price")
        close_parser.add_argument("--pnl", type=float, help="Manual PnL override")
        close_parser.add_argument("--notes", help="Exit notes")
        close_parser.add_argument("--close-reason", help="Close reason tag (e.g. profit-monster)")
        close_parser.add_argument("--skip-hl", action="store_true",
                                  help="Skip HL /info lookup — use signal-based PnL (saves 1 API call)")
        
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
                flipped_from_trade=args.flipped,
                signal_z_score=args.signal_z_score,
                signal_rsi_14=args.signal_rsi_14,
                signal_macd_hist=args.signal_macd_hist,
                signal_macd_value=args.signal_macd_value,
                signal_macd_signal=args.signal_macd_signal,
                signal_momentum_state=args.signal_momentum_state,
                signal_z_score_tier=args.signal_z_score_tier,
                signal_decision=args.signal_decision,
                signal_leverage=args.signal_leverage,
                signal_created_at=args.signal_created_at,
                test_sl_variant=args.test_sl_variant,
                test_timing_variant=args.test_timing_variant,
                test_trailing_variant=args.test_trailing_variant,
                signal_metadata=json.loads(args.signal_metadata_json) if args.signal_metadata_json else None,
                exp_metadata=json.loads(args.exp_metadata_json) if args.exp_metadata_json else None,
            )
            if trade_id is None:
                sys.exit(1)  # Signal was rejected — propagate failure to caller
            print(f"✓ Added trade #{trade_id}: {args.side.upper()} {args.amount} USDT {args.token} @ ${args.entry}")
            print(f"  Exchange: {args.exchange} | Server: {args.server} | Paper: {not args.real} | Signal: {args.signal or 'N/A'} | Lev: {args.leverage}x")
        
        elif args.subcommand == "close":
            close_trade(args.id, args.exit_price, args.pnl, args.notes, args.close_reason,
                        skip_hl=args.skip_hl)
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
