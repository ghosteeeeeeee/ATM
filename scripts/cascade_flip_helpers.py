"""
cascade_flip_helpers.py
=======================
Shared helpers for cascade-flip lifecycle:
  - Pipeline cycle tracking  (persisted to pipeline_cycle.json)
  - Flip eviction metadata   (read/write flip_counts.json hotset_evicted flag)
  - Post-flip DB INSERT      (synchronous DB entry for post-flip positions)
  - Post-flip ATR k override (tokens that were recently flipped)

Imported by:
  position_manager.py  (cascade_flip, _collect_atr_updates)
  signal_compactor.py  (hot-set builder)
  run_pipeline.py      (cycle counter increment)
"""

from typing import Optional
import json, os, sys
from datetime import datetime, timezone

# ── Constants ────────────────────────────────────────────────────────────────

FLIP_COUNTS_FILE  = '/var/www/hermes/data/flip_counts.json'
PIPELINE_CYCLE_FILE = '/var/www/hermes/data/pipeline_cycle.json'

# How many pipeline cycles a token stays evicted from the hot-set after a flip.
# 1 cycle = 1 minute (pipeline runs every 1 min via systemd timer).
# 10 cycles ≈ 10 minutes.
FLIP_EVICTION_CYCLES = 10

# ── Pipeline Cycle Tracking ───────────────────────────────────────────────────

def get_pipeline_cycle() -> int:
    """Return the current pipeline cycle number (0 if file doesn't exist yet)."""
    try:
        with open(PIPELINE_CYCLE_FILE) as f:
            return json.load(f).get('cycle', 0)
    except Exception:
        return 0


def increment_pipeline_cycle() -> int:
    """
    Increment and persist the pipeline cycle counter.
    Called once per pipeline run in run_pipeline.py.

    Returns the new cycle number.
    """
    try:
        os.makedirs(os.path.dirname(PIPELINE_CYCLE_FILE), exist_ok=True)
        try:
            with open(PIPELINE_CYCLE_FILE) as f:
                data = json.load(f)
        except Exception:
            data = {}
        data['cycle'] = data.get('cycle', 0) + 1
        with open(PIPELINE_CYCLE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return data['cycle']
    except Exception as e:
        print(f"  [Pipeline Cycle] ⚠️ Failed to increment cycle: {e}")
        return 0


def get_eviction_deadline() -> int:
    """
    Return the pipeline cycle number at which eviction expires.
    i.e.  current_cycle + FLIP_EVICTION_CYCLES
    """
    return get_pipeline_cycle() + FLIP_EVICTION_CYCLES


# ── Eviction Helpers ─────────────────────────────────────────────────────────

def load_flip_counts() -> dict:
    """Load persisted flip counts. Returns {TOKEN: {flips, last_flip_dir, last_flip_time, hotset_evicted, evicted_until_cycle}}"""
    try:
        if os.path.exists(FLIP_COUNTS_FILE):
            with open(FLIP_COUNTS_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_flip_counts(counts: dict):
    """Persist flip counts to disk."""
    try:
        from hermes_file_lock import FileLock
        with FileLock('flip_counts'):
            os.makedirs(os.path.dirname(FLIP_COUNTS_FILE), exist_ok=True)
            with open(FLIP_COUNTS_FILE, 'w') as f:
                json.dump(counts, f, indent=2)
    except Exception as e:
        print(f"  [Flip Counts] ⚠️ Failed to persist flip counts: {e}")


def is_token_evicted(token: str) -> bool:
    """
    Return True if token is currently evicted from the hot-set.
    Eviction is active when hotset_evicted=True AND current_cycle < evicted_until_cycle.
    """
    fc = load_flip_counts()
    entry = fc.get(token.upper(), {})
    if not entry.get('hotset_evicted'):
        return False
    deadline = entry.get('evicted_until_cycle', 0)
    current  = get_pipeline_cycle()
    return current < deadline


def clear_expired_evictions():
    """
    Remove hotset_evicted flags whose deadline has passed.
    Called at the start of signal_compactor so expired entries are
    cleaned up automatically on the first cycle after eviction ends.
    """
    fc = load_flip_counts()
    changed = False
    current = get_pipeline_cycle()
    for token, entry in fc.items():
        if entry.get('hotset_evicted'):
            deadline = entry.get('evicted_until_cycle', 0)
            if current >= deadline:
                entry.pop('hotset_evicted', None)
                entry.pop('evicted_until_cycle', None)
                changed = True
    if changed:
        save_flip_counts(fc)


def mark_token_flipped(token: str, flip_count: int, opposite_dir: str) -> dict:
    """
    Update flip_counts entry for a token that just underwent a cascade flip.
    Adds hotset_evicted=True and evicted_until_cycle.

    Returns the updated entry dict.
    """
    fc = load_flip_counts()
    entry = fc.get(token.upper(), {})
    deadline = get_eviction_deadline()
    entry.update({
        'flips': flip_count,
        'last_flip_dir': opposite_dir,
        'last_flip_time': datetime.now(timezone.utc).isoformat(),
        'hotset_evicted': True,
        'evicted_until_cycle': deadline,
    })
    fc[token.upper()] = entry
    save_flip_counts(fc)
    return entry


# ── Post-Flip ATR k Override ──────────────────────────────────────────────────

def get_flip_k_multiplier(token: str) -> float:
    """
    Return the ATR k multiplier to use for a post-flip position.
    Returns 1.0 (tightest) for tokens currently in eviction window.
    Returns None if the token is not recently flipped (use normal k).
    """
    if is_token_evicted(token):
        return 1.0
    return None  # signal caller to use normal k


# ── Post-Flip DB Entry ───────────────────────────────────────────────────────

def insert_post_flip_trade(
    token: str,
    direction: str,
    entry_price: float,
    hl_entry_price: float,
    amount_usdt: float,
    leverage: int,
    stop_loss: float,
    target: float,
    signal: str,
    signal_source: str,
) -> Optional[int]:
    """
    Synchronously insert a DB entry for a position opened via cascade flip.
    Sets atr_managed=TRUE so guardian ignores it.

    Returns the new trade_id (int) on success, None on failure.

    The INSERT uses a CTE with a NOT EXISTS guard so it is idempotent —
    if guardian runs before or at the same time, one of the two will succeed.
    """
    try:
        from position_manager import get_db_connection

        conn = get_db_connection()
        cur  = conn.cursor()

        cur.execute("""
            INSERT INTO trades (
                token, direction, entry_price, hl_entry_price,
                amount_usdt, leverage, exchange, paper, status, open_time,
                stop_loss, target, atr_managed, signal, signal_source,
                sl_distance, trailing_activation, trailing_distance,
                guardian_closed, is_guardian_close
            )
            SELECT
                %s, %s, %s, %s,
                %s, %s, 'Hyperliquid', true, 'open', NOW(),
                %s, %s, TRUE, %s, %s,
                0.03, 0.01, 0.01,
                FALSE, FALSE
            WHERE NOT EXISTS (
                SELECT 1 FROM trades
                WHERE token = %s AND status = 'open'
                AND server = 'Hermes'
                AND atr_managed = TRUE
            )
            RETURNING id
        """, (
            token, direction, entry_price, hl_entry_price,
            amount_usdt, leverage,
            stop_loss, target,
            signal, signal_source,
            token,
        ))

        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if row:
            return row[0]
        else:
            # Either we inserted OR guardian already inserted — both are fine.
            # Try to fetch the existing trade_id so callers can use it.
            conn2 = get_db_connection()
            cur2  = conn2.cursor()
            cur2.execute(
                "SELECT id FROM trades WHERE token=%s AND status='open' AND server='Hermes' ORDER BY id DESC LIMIT 1",
                (token,)
            )
            row2 = cur2.fetchone()
            cur2.close()
            conn2.close()
            return row2[0] if row2 else None

    except Exception as e:
        print(f"  [Post-Flip DB] ⚠️ Failed to insert post-flip trade for {token}: {e}")
        return None
