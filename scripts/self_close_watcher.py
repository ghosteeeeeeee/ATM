#!/usr/bin/env python3
"""
Self-Close Watcher — Final fallback for coins that cannot have HL TP/SL.

Coins in UNPROTECTABLE_COINS have their TP/SL stored in brain DB.
This script runs every minute, checks if any stored TP/SL has been hit,
and closes the position via market order if so.

Usage:
    python3 self_close_watcher.py [--dry-run]

Systemd: hermes-self-close-watcher.service + hermes-self-close-watcher.timer
"""

import sys, os, json, time, argparse, logging
from datetime import datetime

sys.path.insert(0, '/root/.hermes/scripts')

import hype_cache as hc
from hyperliquid_exchange import (
    get_exchange, _exchange_rate_limit, get_open_hype_positions_curl,
    MAIN_ACCOUNT_ADDRESS, cancel_bulk_orders
)
from hyperliquid.utils.signing import TriggerOrderType

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_FILE = "/root/.hermes/logs/self_close_watcher.log"
ERR_FILE = "/root/.hermes/logs/self_close_watcher.err.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    handlers=[
        logging.FileHandler(ERR_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("self_close")

# ── Config ───────────────────────────────────────────────────────────────────
DRY = False
SELF_CLOSE_TABLE = "tpsl_self_close"  # brain DB table
UNPROTECTABLE_COINS = {'AAVE', 'MORPHO', 'ASTER', 'PAXG', 'BTC', 'AVNT'}

# Retry logic for rate-limited closes
MAX_RETRIES = 2
RETRY_DELAY = 5  # seconds


# ── DB helpers ────────────────────────────────────────────────────────────────
def db_connect():
    import psycopg2
    return psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")


def ensure_table():
    """Create the self-close table if it doesn't exist."""
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tpsl_self_close (
            id SERIAL PRIMARY KEY,
            coin VARCHAR(16) NOT NULL,
            direction VARCHAR(8) NOT NULL,
            size REAL NOT NULL,
            entry_px REAL NOT NULL,
            sl_price REAL NOT NULL,
            tp_price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            last_checked_at TIMESTAMP,
            triggered_at TIMESTAMP,
            close_result JSONB,
            UNIQUE(coin)
        )
    """)
    conn.commit()
    conn.close()


def upsert_self_close(coin: str, direction: str, size: float,
                       entry_px: float, sl_price: float, tp_price: float):
    """Store or update SL/TP for a coin (called by batch when it skips a coin)."""
    try:
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tpsl_self_close (coin, direction, size, entry_px, sl_price, tp_price, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (coin) DO UPDATE SET
                direction = EXCLUDED.direction,
                size = EXCLUDED.size,
                entry_px = EXCLUDED.entry_px,
                sl_price = EXCLUDED.sl_price,
                tp_price = EXCLUDED.tp_price,
                updated_at = NOW(),
                last_checked_at = NOW()
        """, (coin, direction, size, entry_px, sl_price, tp_price))
        conn.commit()
        conn.close()
        log.info(f"  Stored self-close TP/SL for {coin}: SL={sl_price} TP={tp_price}")
    except Exception as e:
        log.error(f"  DB upsert failed for {coin}: {e}")


def get_all_self_close() -> list:
    """Load all stored self-close TP/SP from DB."""
    try:
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("SELECT coin, direction, size, entry_px, sl_price, tp_price FROM tpsl_self_close")
        rows = cur.fetchall()
        conn.close()
        return [{'coin': r[0], 'direction': r[1], 'size': r[2],
                 'entry_px': r[3], 'sl_price': r[4], 'tp_price': r[5]} for r in rows]
    except Exception as e:
        log.error(f"Failed to load self-close records: {e}")
        return []


def mark_triggered(coin: str, result: dict):
    """Record that we triggered a self-close."""
    try:
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            UPDATE tpsl_self_close
            SET triggered_at = NOW(), close_result = %s, last_checked_at = NOW()
            WHERE coin = %s
        """, (json.dumps(result), coin))
        conn.commit()
        conn.close()
    except Exception as e:
        log.error(f"Failed to mark triggered for {coin}: {e}")


# ── Guarded close ─────────────────────────────────────────────────────────────
def guarded_close_position(coin: str, direction: str, size: float,
                            reason: str = "SL/TP trigger") -> dict:
    """
    Attempt to close a position for a coin that cannot have HL TP/SL.
    Uses a plain market order (no TP/SL attached).
    Returns dict with outcome. Never raises — always returns a result dict.
    """
    coin = coin.upper()
    size = abs(float(size))

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            mids = hc.get_allMids()
            price = float(mids.get(coin, 0))
            if price == 0:
                return {"ok": False, "error": f"No mid price for {coin}", "coin": coin}

            _exchange_rate_limit()
            exchange = get_exchange()

            # Close LONG → sell (is_buy=False), Close SHORT → buy (is_buy=True)
            is_buy = direction.upper() == "SHORT"

            log.info(f"  Self-close {coin} {direction} sz={size} at ~{price} ({reason})")

            result = exchange.order(coin, is_buy, size, price, None, reduce_only=True)
            statuses = result.get("response", {}).get("data", {}).get("statuses", [])
            error = statuses[0].get("error") if statuses else None

            if error:
                log.error(f"  Self-close {coin} failed: {error}")
                if attempt < MAX_RETRIES:
                    log.info(f"  Retrying in {RETRY_DELAY}s (attempt {attempt+1}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY)
                    continue
                return {"ok": False, "error": error, "coin": coin, "attempt": attempt}

            oid = statuses[0].get("ok", {}).get("oid") if statuses else None
            log.info(f"  Self-close {coin} OK — oid={oid}")
            return {"ok": True, "coin": coin, "size": size, "close_price": price,
                    "direction": direction, "oid": oid, "reason": reason}

        except Exception as e:
            log.error(f"  Self-close {coin} exception: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
            return {"ok": False, "error": str(e), "coin": coin}


# ── Main check ────────────────────────────────────────────────────────────────
def check_and_close():
    """
    For each coin in UNPROTECTABLE_COINS that has an open position:
    1. Fetch current mid price
    2. Load stored SL/TP from DB
    3. Check if price has crossed SL or TP
    4. If crossed → call guarded_close_position()
    5. Update DB with result
    """
    log.info("=== Self-Close Watcher Run ===")

    # Ensure table exists
    ensure_table()

    # Get open positions
    open_pos = get_open_hype_positions_curl()
    active_unprot = {
        coin: data for coin, data in open_pos.items()
        if coin in UNPROTECTABLE_COINS and float(data.get('size', 0)) != 0
    }

    if not active_unprot:
        log.info("  No unprotectable coins with open positions — nothing to do")
        return

    log.info(f"  Active unprotectable positions: {list(active_unprot.keys())}")

    # Load all stored TP/SL records
    stored = {r['coin']: r for r in get_all_self_close()}

    # Get current mids
    mids = hc.get_allMids()

    for coin, pos_data in active_unprot.items():
        sz = float(pos_data.get('size', 0))
        entry_px = float(pos_data.get('entry_px', 0))
        direction = 'LONG' if sz > 0 else 'SHORT'
        sz = abs(sz)
        current_px = float(mids.get(coin, entry_px))

        log.info(f"  Checking {coin}: {direction} sz={sz} current={current_px} entry={entry_px}")

        # Get stored TP/SL
        record = stored.get(coin)
        if not record:
            # No stored TP/SL — compute from defaults (2% ATR)
            atr_pct = 0.02
            k, k_tp = 2.0, 5.0
            sl_pct = max(0.015, min(0.05, k * atr_pct))
            tp_pct = max(0.03, min(0.15, k_tp * atr_pct))
            if direction == 'LONG':
                sl_price = current_px * (1 - sl_pct)
                tp_price = current_px * (1 + tp_pct)
            else:
                sl_price = current_px * (1 + sl_pct)
                tp_price = current_px * (1 - tp_pct)
            # Store for future runs
            upsert_self_close(coin, direction, sz, entry_px, sl_price, tp_price)
            log.info(f"  {coin}: no prior record, computed SL={sl_price:.6f} TP={tp_price:.6f}")
            continue  # Skip this run, let next run check with stored values

        sl_price = record['sl_price']
        tp_price = record['tp_price']

        # Determine trigger
        if direction == 'LONG':
            triggered = (current_px <= sl_price) or (current_px >= tp_price)
            trigger_reason = None
            if current_px <= sl_price:
                trigger_reason = f"SL triggered (px={current_px} <= sl={sl_price})"
            elif current_px >= tp_price:
                trigger_reason = f"TP triggered (px={current_px} >= tp={tp_price})"
        else:  # SHORT
            triggered = (current_px >= sl_price) or (current_px <= tp_price)
            if current_px >= sl_price:
                trigger_reason = f"SL triggered (px={current_px} >= sl={sl_price})"
            elif current_px <= tp_price:
                trigger_reason = f"TP triggered (px={current_px} <= tp={tp_price})"

        if not triggered:
            log.info(f"  {coin}: OK — SL={sl_price:.6f} TP={tp_price:.6f} (no trigger)")
            # Update last_checked_at
            try:
                conn = db_connect()
                cur = conn.cursor()
                cur.execute("UPDATE tpsl_self_close SET last_checked_at=NOW() WHERE coin=%s", (coin,))
                conn.commit()
                conn.close()
            except Exception:
                pass
            continue

        # TRIGGERED — attempt close
        log.error(f"  !!! {coin} TRIGGERED: {trigger_reason}")
        result = guarded_close_position(coin, direction, sz, trigger_reason)
        mark_triggered(coin, result)

        if result['ok']:
            log.info(f"  {coin} self-close SUCCESS")
        else:
            log.error(f"  {coin} self-close FAILED: {result.get('error')}")

    log.info("=== Self-Close Watcher Done ===")


# ── Bootstrap from batch ─────────────────────────────────────────────────────
def sync_from_batch():
    """
    Called by batch_tpsl_rewrite.py after it skips a coin.
    Batch passes coin, direction, size, sl, tp via env for cross-process comm.
    Reads from /tmp/hermes_self_close_pending.json
    """
    pending_file = "/tmp/hermes_self_close_pending.json"
    if not os.path.exists(pending_file):
        return

    try:
        with open(pending_file) as f:
            pending = json.load(f)
        os.remove(pending_file)

        for record in pending:
            upsert_self_close(
                record['coin'], record['direction'], record['size'],
                record['entry_px'], record['sl_price'], record['tp_price']
            )
        log.info(f"Synced {len(pending)} self-close records from batch")
    except Exception as e:
        log.error(f"Failed to sync from batch: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    DRY = args.dry_run

    if DRY:
        log.info("DRY RUN — no orders will be placed")

    sync_from_batch()
    check_and_close()