#!/usr/bin/env python3
"""Hermes trades + signals API — outputs JSON for the web dashboard."""
import sys, json, os, sqlite3, time, fcntl
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import init_db
import psycopg2
from datetime import datetime, timezone
try:
    from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
    from tokens import is_solana_only
except Exception:
    SHORT_BLACKLIST = set()
    LONG_BLACKLIST = set()
    is_solana_only = lambda t: False

BRAIN_DB   = "host=/var/run/postgresql dbname=brain user=postgres password=***"
PRICE_DB   = '/root/.hermes/data/signals_hermes.db'
_px_cache  = {}    # token -> [(ts, price), ...]
_px_at     = 0     # last load timestamp
_LOCK_FILE = '/var/www/hermes/data/.trades-lock'


def _atomic_write(data: dict, path: str):
    """Write JSON atomically using flock — safe for concurrent writers."""
    lock_path = path + '.lock'
    with open(lock_path, 'w') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _load_prices(token):
    """Load price history for token (module-level memoised, refreshed <60s)."""
    global _px_cache, _px_at
    now = time.time()
    if token in _px_cache and (now - _px_at) < 60:
        return
    try:
        conn_p = sqlite3.connect(PRICE_DB)
        cur_p = conn_p.cursor()
        cur_p.execute(
            "SELECT timestamp, price FROM price_history WHERE token=? ORDER BY timestamp ASC",
            (token,)
        )
        rows = cur_p.fetchall()
        conn_p.close()
        _px_cache[token] = [(r[0], r[1]) for r in rows] if rows else []
        _px_at = now
    except Exception:
        _px_cache[token] = []


def _get_current_price(token):
    """Get the most recent price for a token, bypassing cache freshness check."""
    try:
        conn_p = sqlite3.connect(PRICE_DB)
        cur_p = conn_p.cursor()
        cur_p.execute(
            "SELECT price FROM price_history WHERE token=? ORDER BY timestamp DESC LIMIT 1",
            (token,)
        )
        row = cur_p.fetchone()
        conn_p.close()
        return float(row[0]) if row else None
    except Exception:
        return None


def live_rsi(token, period=14):
    _load_prices(token)
    data = _px_cache.get(token, [])
    if len(data) < period + 1:
        return None
    closes = [p for _, p in data[-period - 1:]]
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gain = sum(d for d in deltas if d > 0) / period
    loss = abs(sum(d for d in deltas if d < 0)) / period
    if loss == 0:
        return 100.0
    return round(100 - 100 / (1 + gain / loss), 2)


def live_macd(token, fast=12, slow=26, sig=9):
    _load_prices(token)
    data = _px_cache.get(token, [])
    if len(data) < slow + sig + 1:
        return None, None
    closes = [p for _, p in data]

    def ema(arr, n):
        k = 2 / (n + 1)
        e = arr[0]
        for v in arr[1:]:
            e = v * k + e * (1 - k)
        return e

    macd_vals = [ema(closes[:i], fast) - ema(closes[:i], slow) for i in range(slow, len(closes) + 1)]
    if len(macd_vals) < sig:
        return round(macd_vals[-1], 6), None
    signal_line = round(ema(macd_vals[-sig - 1:], sig), 6)
    return round(macd_vals[-1], 6), round(macd_vals[-1] - signal_line, 6)


def live_zscore(token, window=500):
    _load_prices(token)
    data = _px_cache.get(token, [])
    if len(data) < window:
        return None
    window_prices = [p for _, p in data[-window:]]
    mean = sum(window_prices) / len(window_prices)
    variance = sum((p - mean) ** 2 for p in window_prices) / len(window_prices)
    std = variance ** 0.5
    if std == 0:
        return None
    return round((window_prices[-1] - mean) / std, 4)
OUT_TRADES   = "/var/www/hermes/data/trades.json"
OUT_SIGNALS  = "/var/www/hermes/data/signals.json"
from signal_schema import RUNTIME_DB as SIGNALS_DB
os.makedirs("/var/www/hermes/data", exist_ok=True)


def _live_trailing_sl(trade_id, direction, entry_price, current_price, trail_act, trail_dist):
    """
    Compute the live trailing SL for an open position using trailing_stops.json.
    Returns None if not yet activated.
    """
    import json
    try:
        with open("/var/www/hermes/data/trailing_stops.json") as f:
            data = json.load(f)
    except:
        return None

    entry = float(entry_price or 0)
    current = float(current_price or 0)
    direction = str(direction or '').upper()
    trail_act_pct = float(trail_act or 0.01) * 100
    trail_dist_pct = float(trail_dist or 0.01)

    if entry <= 0 or current <= 0:
        return None

    if direction == 'LONG':
        pnl_pct = (current - entry) / entry * 100
    elif direction == 'SHORT':
        pnl_pct = (entry - current) / entry * 100
    else:
        return None

    if pnl_pct < trail_act_pct:
        return None  # trailing not yet active

    # Get best_price from trailing_stops.json
    ts = data.get(str(trade_id), {})
    if not ts.get('active'):
        return None

    best_price = float(ts.get('best_price', current))

    if direction == 'LONG':
        return round(best_price * (1 - trail_dist_pct), 8)
    else:
        return round(best_price * (1 + trail_dist_pct), 8)


def get_trades(status='open', limit=20, offset=0):
    try:
        conn = psycopg2.connect(BRAIN_DB)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, direction, entry_price, current_price, pnl_pct, pnl_usdt,
                   stop_loss, target, exchange, open_time, close_time, status, close_reason,
                   signal, confidence, leverage, amount_usdt,
                   trailing_activation, trailing_distance, exit_price
            FROM trades
            WHERE (server = 'Hermes' OR server IS NULL) AND status = %s
            ORDER BY
                CASE WHEN %s = 'open' THEN id END DESC,
                CASE WHEN %s = 'closed' THEN close_time END DESC
            LIMIT %s OFFSET %s
        """, (status, status, status, limit, offset))
        rows = cur.fetchall()
        cur.close(); conn.close()
        return rows
    except:
        return []


def get_signals_from_db(limit=100):
    """Read recent signals from SQLite."""
    if not os.path.exists(SIGNALS_DB):
        return []
    try:
        conn = sqlite3.connect(SIGNALS_DB)
        c = conn.cursor()
        c.execute("""
            SELECT token, direction, confidence, signal_type, source, price,
                   z_score, rsi_14, macd_hist, decision, created_at
            FROM signals
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        conn.close()
        return [{
            'token': r[0], 'direction': r[1], 'confidence': float(r[2]) if r[2] else 0,
            'type': r[3], 'source': r[4], 'price': float(r[5]) if r[5] else 0,
            'zscore': float(r[6]) if r[6] else None,
            'rsi': float(r[7]) if r[7] else None,
            'macd': float(r[8]) if r[8] else None,
            'decision': r[9] or 'PENDING',
            'time': r[10]
        } for r in rows]
    except:
        return []


def write_trades():
    # Get open trades
    open_t = get_trades('open', 100)

    # Get total closed count
    try:
        conn = psycopg2.connect(BRAIN_DB)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM trades WHERE (server = 'Hermes' OR server IS NULL) AND status = 'closed'"
        )
        total_closed = cur.fetchone()[0]
        cur.close(); conn.close()
    except:
        total_closed = 0

    # Get closed trades — 50 per page, page from query param (default 1)
    # The API will return all closed trades with pagination info
    # We'll write a separate endpoint approach: fetch all IDs, split into pages
    # For simplicity, write a flat list with pagination metadata
    closed_t = get_trades('closed', 200)  # enough for 4 pages

    result = {
        "updated": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "open_count": len(open_t),
        "closed_count": total_closed,
        "page_size": 50,
        "open": _build_open_trades(open_t),
        "closed": [{
            "token": r[1], "direction": r[2],
            "entry": float(r[3]) if r[3] else 0,
            "exit": float(r[20]) if r[20] else 0,
            "closed": str(r[11]) if r[11] else "",
            "pnl_pct": round(float(r[5]), 2) if r[5] else 0,
            # pnl_usdt from DB already includes leverage — use directly (FIX: was * leverage)
            "pnl_usdt": round(float(r[6]), 2) if r[6] else 0,
            "exchange": r[9], "opened": str(r[10]) if r[10] else "",
            "status": r[12], "signal": r[14],
            "confidence": float(r[15]) if r[15] else 0,
            "leverage": float(r[16]) if r[16] else 1,
            "amount_usdt": float(r[17]) if r[17] else 50.0,
            "close_reason": r[13] if r[13] else ""
        } for r in closed_t]
    }
    _atomic_write(result, OUT_TRADES)


def _build_open_trades(open_t):
    """Build open trades with live P&L calculated from current market prices."""
    out = []
    for r in open_t:
        token     = r[1]
        direction = r[2]
        entry_px  = float(r[3]) if r[3] else 0
        lev       = float(r[16]) if r[16] else 1
        amt       = float(r[17]) if r[17] else 50.0

        # Get live current price (most recent from price_history)
        current_px = _get_current_price(token)
        if not current_px or current_px <= 0:
            current_px = entry_px  # fallback to entry if no live price

        # Compute live P&L from current market price
        if entry_px > 0:
            if direction and direction.upper() == 'SHORT':
                pnl_pct = round((entry_px - current_px) / entry_px * 100, 4)
            else:  # LONG or unknown
                pnl_pct = round((current_px - entry_px) / entry_px * 100, 4)
            pnl_usdt = round(pnl_pct / 100 * amt, 4)
        else:
            pnl_pct = 0
            pnl_usdt = 0

        out.append({
            "token": token,
            "direction": direction,
            "entry": entry_px,
            "current": round(current_px, 6),
            "pnl_pct": round(pnl_pct, 2),
            "pnl_usdt": round(pnl_usdt, 2),
            "sl": round(float(r[7]), 6) if r[7] else 0,
            "tp": round(float(r[8]), 6) if r[8] else 0,
            "exchange": r[9],
            "opened": str(r[10]) if r[10] else "",
            "signal": r[14],
            "confidence": float(r[15]) if r[15] else 0,
            "leverage": lev,
            "amount_usdt": amt,
            "effective_size": round(amt * lev, 2),
            "trailing_activation": float(r[18]) if r[18] else 0.01,
            "trailing_distance": float(r[19]) if r[19] else 0.01,
            "trailing_sl": _live_trailing_sl(r[0], direction, entry_px, current_px, float(r[18]) if r[18] else 0.01, float(r[19]) if r[19] else 0.01)
        })
    return out


# ── Helper: read hot_set from hotset.json ─────────────────────────────────────
def _get_hotset_from_file():
    """
    Read the authoritative hot-set from hotset.json (written by ai_decider).
    Enrich each entry with live RSI/MACD computed from price_history for the
    web dashboard. Returns None if the file is missing or stale (>11 min).
    """
    HOTSET_FILE = '/var/www/hermes/data/hotset.json'
    try:
        with open(HOTSET_FILE) as f:
            data = json.load(f)
        entries = data.get('hotset', [])
        if not entries:
            return None
        # Stale check: if hotset.json is stale (>20 min), return empty — do NOT fall back to DB.
        # Fallback uses token_speeds table which has incomplete/NULL speed_percentile → all 50%.
        # ONE writer only: ai_decider.py writes hotset.json. Everyone else reads it.
        # Keep threshold at 20 min (timer fires every 10 min, pipeline takes ~2 min).
        ts = data.get('timestamp', 0)
        if ts > 0 and (time.time() - ts) > 1200:
            print(f"[hotset] hotset.json stale ({time.time()-ts:.0f}s) — returning empty (ai_decider should refresh)")
            return []

        # Pre-load prices for all tokens (batch, single call per token)
        for entry in entries:
            _load_prices(entry['token'])

        result = []
        for e in entries:
            tok = e['token']
            rsi_val = live_rsi(tok)
            _, macd_val = live_macd(tok)
            live_price = _px_cache[tok][-1][1] if tok in _px_cache and _px_cache[tok] else 0

            result.append({
                'token':          tok,
                'direction':      e.get('direction', 'SHORT'),
                'type':           'hot set',
                'sources':        e.get('source', ''),       # was: signal_type (wrong)
                'confidence':     round(e.get('confidence', 0), 1),
                'base_conf':      round(e.get('confidence', 0), 1),
                'entry_count':    e.get('compact_rounds', 1), # was: review_count (wrong)
                'price':          live_price or e.get('price', 0),
                'rsi':            rsi_val,
                'macd':           macd_val,
                'zscore':         e.get('z_score', 0),       # was: z_score (key was never written)
                'rounds':         e.get('survival_round', 0), # was: compact_rounds (wrong direction)
                'survival':       e.get('survival_score', 0), # was: survival_score (key was never written)
                'last_seen':      str(e.get('timestamp', ts)),
                # SPEED FEATURE fields (from hotset.json)
                'speed_pctl':     round(e.get('speed_percentile') or e.get('momentum_score') or 50.0, 1),
                'vel_5m':         round(e.get('price_velocity_5m') or 0, 3),
                'accel':          round(e.get('price_acceleration', 0), 3),
                'is_stale':       False,
                # Additional enrichments from hotset.json
                'wave_phase':     e.get('wave_phase', 'neutral'),
                'is_overextended': e.get('is_overextended', False),
            })
        print(f"[hotset] loaded {len(result)} tokens from hotset.json")
        # Safety cap: hot-set should never exceed 20 tokens
        if len(result) > 20:
            result = result[:20]
        return result
    except FileNotFoundError:
        print("[hotset] hotset.json not found — using fallback DB query")
        return None
    except Exception as ex:
        print(f"[hotset] error reading hotset.json: {ex} — using fallback DB query")
        return None


# ── Helper: fallback hot-set from DB (legacy logic) ────────────────────────────
def _build_hotset_from_db():
    """
    Fallback: build hot-set directly from DB.
    Used only when hotset.json is missing or stale.
    Preserves the original flip-protection + live RSI/MACD/Zscore logic.
    """
    hot_set = []
    try:
        conn_rt = sqlite3.connect(SIGNALS_DB)
        conn_rt.row_factory = sqlite3.Row
        c_rt = conn_rt.cursor()

        c_rt.execute("SELECT DISTINCT token FROM signals WHERE compact_rounds > 0 AND executed = 0")
        for (tok,) in c_rt.fetchall():
            _load_prices(tok)

        c_rt.execute("""
            SELECT
                s.token,
                s.direction,
                MAX(s.review_count) as max_rounds,
                MAX(s.survival_score) as max_survival,
                MAX(s.confidence) as max_conf,
                AVG(s.confidence) as avg_conf,
                COUNT(*) as entry_count,
                GROUP_CONCAT(DISTINCT s.source) as sources,
                MAX(s.last_compact_at) as last_seen,
                MAX(s.created_at) as created,
                MAX(s.price) as price,
                sp.speed_percentile,
                sp.price_velocity_5m,
                sp.price_acceleration,
                sp.is_stale
            FROM signals s
            LEFT JOIN token_speeds sp ON UPPER(s.token) = UPPER(sp.token)
            WHERE s.review_count >= 1
              AND s.executed = 0
              AND s.decision IN ('PENDING', 'APPROVED', 'WAIT')
              AND s.confidence >= 70
              AND (sp.speed_percentile IS NULL OR sp.speed_percentile > 0)
            GROUP BY s.token, s.direction
            HAVING COUNT(*) >= 1
            ORDER BY max_rounds DESC, max_survival DESC, avg_conf DESC
            LIMIT 20
        """)
        raw = c_rt.fetchall()
        conn_rt.close()

        best = {}
        for r in raw:
            t = r['token']
            if t not in best or (r['max_rounds'] or 0) > (best[t]['max_rounds'] or 0) or (
                (r['max_rounds'] or 0) == (best[t]['max_rounds'] or 0) and
                (r['max_survival'] or 0) > (best[t]['max_survival'] or 0)
            ):
                best[t] = r

        for r in raw:
            t = r['token']
            if best[t]['direction'] != r['direction']:
                continue

            tok = r['token']
            avg_conf = float(r['avg_conf']) if r['avg_conf'] else 0
            entry_count = int(r['entry_count']) if r['entry_count'] else 1
            combined_conf = round(avg_conf + (entry_count - 1) * 2.0, 1)
            max_r = int(r['max_rounds']) if r['max_rounds'] else 0

            rsi_val = live_rsi(tok)
            _, macd_val = live_macd(tok)
            z_val = live_zscore(tok)
            live_price = _px_cache[tok][-1][1] if tok in _px_cache and _px_cache[tok] else 0

            missing = []
            if z_val is None:      missing.append('z_score')
            if rsi_val is None:   missing.append('rsi_14')
            if macd_val is None:  missing.append('macd_hist')
            if live_price <= 0:   missing.append('price')
            if missing:
                import logging as _log
                _log.warning(f"HOT_SET_DISQUALIFIED: {tok} missing [{','.join(missing)}]")
                continue

            # T's filters (2026-04-05): confidence >= 70 and momentum > 0
            conf = float(r['avg_conf']) if r['avg_conf'] else 0.0
            if conf < 70.0:
                continue
            speed = float(r['speed_percentile']) if r['speed_percentile'] is not None else 50.0
            if speed == 0.0:
                continue

            # Blacklist filters
            direction = r['direction'].upper()
            if direction == 'SHORT' and tok in SHORT_BLACKLIST:
                continue
            if direction == 'LONG' and tok in LONG_BLACKLIST:
                continue
            if is_solana_only(tok):
                continue

            hot_set.append({
                'token': tok,
                'direction': r['direction'],
                'type': 'hot set',
                'sources': r['sources'],
                'confidence': min(combined_conf, 99.9),
                'base_conf': round(avg_conf, 1),
                'entry_count': entry_count,
                'price': live_price or float(r['price']) if r['price'] else 0,
                'rsi': rsi_val,
                'macd': macd_val,
                'zscore': z_val,
                'rounds': max_r,
                'survival': float(r['max_survival']) if r['max_survival'] else 0,
                'last_seen': r['last_seen'] or str(r['created']),
                'speed_pctl': round(float(r['speed_percentile']), 1) if r['speed_percentile'] is not None else 50.0,
                'vel_5m':    round(float(r['price_velocity_5m']), 3)  if r['price_velocity_5m'] is not None else 0.0,
                'accel':     round(float(r['price_acceleration']), 3) if r['price_acceleration'] is not None else 0.0,
                'is_stale':  bool(r['is_stale']) if r['is_stale'] is not None else False,
            })
        print(f"[hotset] fallback DB query returned {len(hot_set)} tokens")
    except Exception as e:
        import traceback
        print(f"Hot set query failed: {e}")
        traceback.print_exc()
    return hot_set


def write_signals():
    """Export signals from DB + win rate stats for the web dashboard."""
    signals = get_signals_from_db(200)

    # ── HOT SET: read from hotset.json (authoritative) ──────────────────────────
    # hotset.json is written by ai_decider after every compaction pass.
    # It is the SOLE source of truth. NO FALLBACK WRITER — if file is missing
    # or stale, we return empty rather than rebuilding from DB with no filters.
    hot_set = _get_hotset_from_file()

    # _get_hotset_from_file() returns:
    #   - None  : file not found or read error
    #   - []    : file is stale (>11 min) or empty
    #   - [..]  : valid enriched hot-set
    # In all cases, treat None or [] the same — return empty to dashboard.
    if not hot_set:
        hot_set = []

    # Compute win rate from brain DB using pnl_pct (after fees)
    # Filter out corrupted trades: exit_price sanity check
    # (some trades have exit prices 1000x entry price — data errors)
    conn = psycopg2.connect(BRAIN_DB)
    cur = conn.cursor()

    # Count ALL closed trades for total_executed
    cur.execute("""
        SELECT COUNT(*)
        FROM trades
        WHERE status = 'closed'
          AND (server = 'Hermes' OR server IS NULL)
          AND entry_price > 0 AND exit_price > 0
          AND exit_price / entry_price BETWEEN 0.01 AND 100
          AND pnl_pct IS NOT NULL
    """)
    total_closed = cur.fetchone()[0]

    # Get stats using pnl_pct (fees already deducted)
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE pnl_pct > 0) as wins,
            COUNT(*) FILTER (WHERE pnl_pct <= 0) as losses,
            SUM(pnl_pct) as total_pnl,
            AVG(pnl_pct) as avg_pnl
        FROM trades
        WHERE status = 'closed'
          AND (server = 'Hermes' OR server IS NULL)
          AND entry_price > 0 AND exit_price > 0
          AND exit_price / entry_price BETWEEN 0.01 AND 100
          AND pnl_pct IS NOT NULL
    """)
    row = cur.fetchone()
    wins = row[0] or 0
    losses = row[1] or 0
    total_pnl = float(row[2] or 0)
    avg_pnl = float(row[3] or 0)
    win_rate = (wins / total_closed * 100) if total_closed > 0 else 0

    cur.close(); conn.close()

    pending_list  = [s for s in signals if s['decision'] == 'PENDING']
    approved_list = [s for s in signals if s['decision'] == 'APPROVED']
    executed_list = [s for s in signals if s['decision'] == 'EXECUTED']

    result = {
        "updated": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "approved": approved_list, "executed": executed_list, "pending": pending_list,
        "total": len(signals),
        "stats": {
            "total_executed": total_closed,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 4),
        },
        "signals": signals,
        "hot_set": hot_set,
    }
    _atomic_write(result, OUT_SIGNALS)


def main():
    write_trades()
    write_signals()
    print(f"trades.json: written | signals.json: written")


if __name__ == '__main__':
    main()
