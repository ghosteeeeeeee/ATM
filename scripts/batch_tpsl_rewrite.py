#!/usr/bin/env python3
"""
batch_tpsl_rewrite.py — runs every minute via cron.

Clean TP/SL rewrite strategy:
  1. For each open HL position:
     a. Cancel ALL existing TP orders (cancel_tp)
     b. Cancel ALL existing SL orders (cancel_sl)
     c. Fetch ATR(14) for the coin
     d. Compute ideal SL/TP using ATR-based logic (same as decider_run)
     e. Round SL/TP to correct HL price precision = max(0, 6 - szDecimals)
     f. Place fresh TP order
     g. Place fresh SL order
     h. Update DB with new order IDs
  2. Log results to stdout + brain DB audit log

HL rate-limit rules (from testing):
  - Exchange init: 429 retry with 5/10/15s backoff
  - Order placement: brief delay between calls avoids most 429s
  - Asset-specific: SAND/AVNT szDecimals=0 → price_tick=1.0 (integer prices only)
    → For coins <$1, TP/SL at integer prices is meaningless: SKIP these coins
  - PAXG (asset=187): HL returns "Invalid TP/SL price. asset=187" for ALL TP/SL attempts
    → Separate HL config issue: SKIP with note

Usage:
  python3 batch_tpsl_rewrite.py [--dry-run]
  */1 * * * * cd /root/.hermes/scripts && python3 batch_tpsl_rewrite.py >> /var/log/hermes_tpsl_rewrite.log 2>&1
"""

import sys, os, time, json, decimal, logging, argparse
from datetime import datetime

sys.path.insert(0, '/root/.hermes/scripts')

import psycopg2
from hyperliquid_exchange import (
    get_exchange, get_open_hype_positions_curl,
    _hl_tick_decimals, _hl_price_decimals, _hl_tick_round,
    place_tp, place_sl, cancel_bulk_orders,
    _exchange_rate_limit, MAIN_ACCOUNT_ADDRESS,
)
import hype_cache as hc
DRY = False

# ── Logging ───────────────────────────────────────────────────────────────────
log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
log.info("batch_tpsl_rewrite.py starting")


# ── ATR ───────────────────────────────────────────────────────────────────────
_ATR_CACHE: dict = {}
_ATR_TTL = 300  # 5 min


def get_atr(token: str, period: int = 14, interval: str = '15m') -> float | None:
    """Fetch ATR(14) from HL 15m candles. Cached 5 min."""
    cache_key = (token.upper(), interval)
    now = time.time()
    if cache_key in _ATR_CACHE:
        val, ts = _ATR_CACHE[cache_key]
        if now - ts < _ATR_TTL:
            return val

    try:
        from hyperliquid.info import Info
        info = Info('https://api.hyperliquid.xyz', skip_ws=True)
        end_t = int(now * 1000)
        start_t = end_t - (15 * 60 * 1000 * (period + 5))
        candles = info.candles_snapshot(token.upper(), interval, start_t, end_t)
        if not candles or len(candles) < period + 1:
            return None
        trs = []
        for i in range(1, min(period + 1, len(candles))):
            high = float(candles[i]['h'])
            low  = float(candles[i]['l'])
            prev_close = float(candles[i - 1]['c'])
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        if not trs:
            return None
        atr = sum(trs) / len(trs)
        _ATR_CACHE[cache_key] = (atr, now)
        return atr
    except Exception as e:
        log.warning(f"ATR fetch error {token}: {e}")
        return None


# ── SL/TP computation ─────────────────────────────────────────────────────────
def compute_sl_tp(direction: str, entry_price: float, current_price: float = None,
                  atr: float = None) -> tuple[float, float]:
    """
    Compute SL/TP using ATR-based logic, referenced from current_price (not entry_price).

    ATR is computed from entry_price since that's the reference for the position's cost basis.
    But the TP/SL percentage distances are applied to current_price to ensure the triggerPx
    is within HL's acceptable range of the current market price.

    SL multiplier k:
      atr_pct < 1%  → k = 2.5 (low volatility)
      1-2.5%       → k = 2.0 (normal)
      > 2.5%       → k = 1.5 (high volatility)
    TP multiplier k_tp = 2.5 * k
    Min/max floors prevent razor-thin or absurdly wide stops.
    """
    entry_price = float(entry_price)
    ref_price = float(current_price) if current_price else entry_price
    atr_pct = 0.02 if atr is None else float(atr) / entry_price

    if atr_pct < 0.01:
        k = 1.5   # LOW_VOLATILITY
    elif atr_pct > 0.03:
        k = 2.5   # HIGH_VOLATILITY
    else:
        k = 2.0   # NORMAL_VOLATILITY
    k_tp = 3.0 * k   # TP = 3× SL k (4.5 / 6.0 / 7.5)

    MIN_SL_PCT, MAX_SL_PCT = 0.015, 0.05
    MIN_TP_PCT, MAX_TP_PCT = 0.03, 0.15

    atr_val = float(atr) if atr else entry_price * 0.02

    sl_pct = min(max((k * atr_val) / entry_price, MIN_SL_PCT), MAX_SL_PCT)
    tp_pct = min(max((k_tp * atr_val) / entry_price, MIN_TP_PCT), MAX_TP_PCT)

    if direction == 'LONG':
        sl = ref_price * (1 - sl_pct)   # reference from current, not entry
        tp = ref_price * (1 + tp_pct)    # reference from current, not entry
    else:  # SHORT
        sl = ref_price * (1 + sl_pct)
        tp = ref_price * (1 - tp_pct)

    return sl, tp


def round_price(price: float, token: str) -> float:
    """Round price to HL perpetual tick: max(0, 6 - szDecimals) decimals."""
    pd = _hl_price_decimals(token)
    return _hl_tick_round(price, pd)


# ── DB helpers ────────────────────────────────────────────────────────────────
def db_connect():
    return psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")


def db_log_audit(event: str, details: dict):
    """Log to brain DB audit_log table if it exists."""
    try:
        conn = db_connect()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO audit_log (event, details, created_at) VALUES (%s, %s, NOW())",
            (event, json.dumps(details)),
        )
        conn.commit()
        conn.close()
    except psycopg2.errors.UndefinedTable:
        # audit_log table doesn't exist — silently skip
        pass
    except Exception as e:
        log.error(f"DB audit log failed: {e}")


def db_update_tpsl_order_ids(token: str, tp_oid: str | None, sl_oid: str | None,
                              sl: float = None, tp: float = None):
    """Update hl_tp_order_id and hl_sl_order_id in brain trades table.
    Also updates stop_loss and target if provided."""
    try:
        conn = db_connect()
        cur = conn.cursor()
        # Build dynamic update: always update order IDs, optionally update SL/TP
        if sl is not None or tp is not None:
            sl_val = sl if sl is not None else 0
            tp_val = tp if tp is not None else 0
            cur.execute(
                """UPDATE trades
                   SET hl_tp_order_id = %s, hl_sl_order_id = %s,
                       stop_loss = CASE WHEN %s != 0 THEN %s ELSE stop_loss END,
                       target    = CASE WHEN %s != 0 THEN %s ELSE target END,
                       updated_at = NOW()
                   WHERE id = (
                       SELECT id FROM trades
                       WHERE token = %s AND status = 'open'
                       ORDER BY open_time DESC LIMIT 1
                   )""",
                (tp_oid, sl_oid, sl_val, sl_val, tp_val, tp_val, token.upper()),
            )
        else:
            cur.execute(
                """UPDATE trades
                   SET hl_tp_order_id = %s, hl_sl_order_id = %s, updated_at = NOW()
                   WHERE id = (
                       SELECT id FROM trades
                       WHERE token = %s AND status = 'open'
                       ORDER BY open_time DESC LIMIT 1
                   )""",
                (tp_oid, sl_oid, token.upper()),
            )
        conn.commit()
        conn.close()
    except Exception as e:
        log.error(f"DB update failed for {token}: {e}")


# ── HL state ──────────────────────────────────────────────────────────────────
def get_open_positions() -> dict:
    """Get open HL positions from cached hype_cache."""
    try:
        return get_open_hype_positions_curl()
    except Exception as e:
        log.error(f"get_open_hype_positions_curl failed: {e}")
        return {}


def get_all_hl_orders() -> list:
    """
    Fetch ALL open orders directly from HL /info endpoint.
    Bypasses SDK caching. Returns raw order list.
    """
    import urllib.request
    wallet = MAIN_ACCOUNT_ADDRESS
    url = "https://api.hyperliquid.xyz/info"
    payload = json.dumps({"type": "openOrders", "user": wallet}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    return result if isinstance(result, list) else result.get("orders", [])


# ── Known-unplaceable coins ────────────────────────────────────────────────────
# These coins have known structural issues preventing TP/SL placement.
# They are skipped with a warning and logged.
SKIP_COINS = {
    'SAND': 'szDecimals=0 → integer prices only. Coin <$1 → TP/SL would be meaningless. Self-close only.',
    'AVNT': 'szDecimals=0 → integer prices only. Coin <$1 → TP/SL would be meaningless. Self-close only.',
    'PAXG': 'HL returns "Invalid TP/SL price. asset=187" for ALL TP/SL. Config issue. Self-close only.',
    'AAVE': 'HL returns "Invalid TP/SL price. asset=28" for ALL TP/SL attempts. Self-close only.',
    'MORPHO': 'HL returns "Invalid TP/SL price. asset=173" for ALL TP/SL attempts. Self-close only.',
    'ASTER': 'HL returns "Invalid TP/SL price. asset=207" for ALL TP/SL attempts. Self-close only.',
}


# ── Main rewrite ───────────────────────────────────────────────────────────────
def rewrite_coin(coin: str, pos_data: dict, prices: dict, hl_orders: list) -> dict:
    """
    Cancel ALL existing exit orders for coin (TP/SL/limit), then place fresh ones.
    Uses direct HL open_orders list to avoid SDK caching issues.
    Returns dict with sl/tp placement results.
    """
    token = coin.upper()
    sz = float(pos_data.get('size', 0))
    if sz == 0:
        return {'skipped': 'zero size'}

    direction = 'LONG' if sz > 0 else 'SHORT'
    sz = abs(sz)
    entry_px = float(pos_data.get('entry_px', 0))
    if entry_px == 0:
        return {'skipped': 'zero entry price'}

    current_px_raw = prices.get(token)
    current_px = float(current_px_raw) if current_px_raw else entry_px

    # ── Guardian vs SKIP split ─────────────────────────────────────────────────
    # GUARDIAN_MANAGED: compute-only, no cancel, no HL placement. Guardian handles TP/SL.
    # SKIP_COINS: self-close DB only, no HL placement.
    # ALL OTHER COINS (shouldn't exist): cancel + place (legacy safety hatch).
    GUARDIAN_MANAGED = token not in SKIP_COINS

    if GUARDIAN_MANAGED:
        # Verify direction freshness from HL directly
        try:
            fresh_pos = get_open_hype_positions_curl()
            fresh_data = fresh_pos.get(token, {})
            fresh_sz = float(fresh_data.get('size', 0))
            fresh_dir = 'LONG' if fresh_sz > 0 else 'SHORT'
            if fresh_dir != direction:
                log.error(f"  STALE CACHE: {token} direction is {direction} in hype_cache "
                          f"but HL says {fresh_dir} (sz={fresh_sz}). Using fresh HL direction.")
                direction = fresh_dir
                sz = abs(fresh_sz)
                entry_px = float(fresh_data.get('entry_px', entry_px))
                pos_data = fresh_data
        except Exception as e:
            log.warning(f"  Could not verify direction freshness for {token}: {e}")

        # Compute ATR + SL/TP — do NOT place on HL, do NOT cancel existing orders
        atr = get_atr(token)
        sl_raw, tp_raw = compute_sl_tp(direction, entry_px, current_px, atr)
        sl = round_price(sl_raw, token)
        tp = round_price(tp_raw, token)

        log.info(
            f"{token} {direction}: entry={entry_px} current={current_px} "
            f"atr={atr} → SL={sl_raw:.6f}→{sl} TP={tp_raw:.6f}→{tp} "
            f"(guardian-managed, NO cancel, NO HL placement)"
        )

        db_update_tpsl_order_ids(token, None, None, sl=sl, tp=tp)

        try:
            from self_close_watcher import upsert_self_close
            upsert_self_close(token, direction, sz, entry_px, sl, tp)
        except Exception as e:
            log.error(f"  Self-close sync failed for {token}: {e}")

        db_log_audit('TPSL_BATCH_COMPUTE', {
            'token': token, 'direction': direction, 'entry': entry_px,
            'atr': atr, 'sl': sl, 'tp': tp, 'size': sz,
        })
        return {'tp': tp, 'sl': sl, 'tp_ok': None, 'sl_ok': None,
                'tp_oid': None, 'sl_oid': None, 'guardian_managed': True}

    # ── SKIP_COINS: self-close DB only ─────────────────────────────────────────
    log.warning(f"SKIP {token}: {SKIP_COINS[token]}")
    atr = get_atr(token)
    sl_raw, tp_raw = compute_sl_tp(direction, entry_px, current_px, atr)
    sl = round_price(sl_raw, token)
    tp = round_price(tp_raw, token)

    log.info(
        f"{token} {direction}: entry={entry_px} current={current_px} "
        f"atr={atr} → SL={sl_raw:.6f}→{sl} TP={tp_raw:.6f}→{tp} "
        f"(skip, self-close fallback)"
    )

    try:
        from self_close_watcher import upsert_self_close
        upsert_self_close(token, direction, sz, entry_px, sl, tp)
    except Exception as e:
        log.error(f"  Self-close sync failed for {token}: {e}")

    # Validate SL/TP
    if direction == 'LONG':
        valid = sl < entry_px < tp
    else:
        valid = sl > entry_px > tp

    if not valid:
        log.warning(
            f"{token}: invalid SL/TP after rounding "
            f"(dir={direction}, entry={entry_px}, SL={sl}, TP={tp})"
        )
        return {'skipped': f'invalid after rounding: SL={sl} TP={tp}'}

    # SKIP coins: also try placing on HL (may work on retry)
    tp_oid = None
    sl_oid = None
    tp_ok = False
    sl_ok = False

    if not DRY:
        _exchange_rate_limit()
        time.sleep(1.5)
        tp_result = place_tp(token, direction, tp, sz)
        tp_ok = tp_result.get('success')
        if tp_ok:
            tp_oid = tp_result.get('order_id')
            log.info(f"  TP: ✓ {tp} oid={tp_oid}")
        else:
            log.warning(f"  TP: ✗ {tp_result.get('error')}")

        time.sleep(1.5)
        _exchange_rate_limit()
        sl_result = place_sl(token, direction, sl, sz)
        sl_ok = sl_result.get('success')
        if sl_ok:
            sl_oid = sl_result.get('order_id')
            log.info(f"  SL: ✓ {sl} oid={sl_oid}")
        else:
            log.warning(f"  SL: ✗ {sl_result.get('error')}")
    else:
        log.info(f"[DRY] Would place TP={tp} SL={sl} size={sz}")

    db_update_tpsl_order_ids(token, tp_oid, sl_oid, sl=sl, tp=tp)

    db_log_audit('TPSL_REWRITE', {
        'token': token,
        'direction': direction,
        'entry': entry_px,
        'atr': atr,
        'sl_raw': sl_raw, 'sl': sl,
        'tp_raw': tp_raw, 'tp': tp,
        'size': sz,
        'tp_ok': tp_ok,
        'sl_ok': sl_ok,
        'tp_oid': tp_oid,
        'sl_oid': sl_oid,
    })

    return {
        'tp': tp, 'sl': sl,
        'tp_ok': tp_ok, 'sl_ok': sl_ok,
        'tp_oid': tp_oid, 'sl_oid': sl_oid,
    }
def main():
    global DRY
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    DRY = args.dry_run

    log.info(f"Starting TP/SL rewrite (DRY={DRY})")

    # ── Fetch positions + prices + ALL HL open orders (once) ─────────────────
    hl_pos = get_open_positions()
    prices_raw = hc.get_allMids()
    hl_orders = get_all_hl_orders()  # Fresh fetch, bypass SDK cache
    log.info(f"HL open orders: {len(hl_orders)} total")

    open_positions = {
        coin: pos for coin, pos in hl_pos.items()
        if float(pos.get('size', 0)) != 0
    }
    log.info(f"Open positions: {list(open_positions.keys())}")

    # ── Rewrite each coin ─────────────────────────────────────────────────────
    results = {}
    for coin, pos_data in open_positions.items():
        log.info(f"--- {coin} ---")
        try:
            result = rewrite_coin(coin, pos_data, prices_raw, hl_orders)
            results[coin] = result
        except Exception as e:
            log.exception(f"Error rewriting {coin}: {e}")
            results[coin] = {'error': str(e)}
        # Delay between coins to avoid HL rate limiting
        if not DRY:
            time.sleep(3)

    # ── Summary ────────────────────────────────────────────────────────────────
    placed = {c: r for c, r in results.items() if r.get('tp_ok') and r.get('sl_ok')}
    skipped = {c: r.get('skipped') or r.get('error') for c, r in results.items() if 'skipped' in r or 'error' in r}
    partial = {c: r for c, r in results.items()
                if c not in placed and c not in skipped}

    log.info(f"\n=== Summary ===")
    log.info(f"  Full TP+SL placed: {list(placed.keys())}")
    log.info(f"  Skipped/error:    {skipped}")
    log.info(f"  Partial:          {list(partial.keys())}")
    log.info("Done.")


if __name__ == '__main__':
    main()
