#!/usr/bin/env python3
"""Hermes trades + signals API — outputs JSON for the web dashboard."""
import sys, json, os, sqlite3, time, fcntl, logging
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import init_db
from paths import *
import psycopg2
from datetime import datetime, timezone

# Configure logging for get_trades() exceptions
logging.basicConfig(level=logging.WARNING,
                    format='[%(asctime)s] %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
_log = logging.getLogger(__name__)
try:
    from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
    from tokens import is_solana_only
except Exception:
    SHORT_BLACKLIST = set()
    LONG_BLACKLIST = set()
    is_solana_only = lambda t: False

BRAIN_DB   = "host=/var/run/postgresql dbname=brain user=postgres password=***"
PRICE_DB   = STATIC_DB
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


def live_macd(token, fast=12, slow=26, sig=9, max_closes=200):
    """
    Compute live MACD for dashboard display.
    Limits to max_closes=200 — sufficient for display (~1-2 days of 1m candles).
    Returns (macd_line, histogram) or (None, None) if insufficient data.
    """
    _load_prices(token)
    data = _px_cache.get(token, [])
    if len(data) < slow + sig + 1:
        return None, None
    # Limit to last max_closes closes for performance (dashboard doesn't need more)
    closes = [p for _, p in data[-max_closes:]]

    k_fast = 2 / (fast + 1)
    k_slow = 2 / (slow + 1)
    k_sig = 2 / (sig + 1)

    # Single-pass iterative EMA for MACD line
    ema_f = closes[0]
    ema_s = closes[0]
    for v in closes[1:]:
        ema_f = v * k_fast + ema_f * (1 - k_fast)
        ema_s = v * k_slow + ema_s * (1 - k_slow)

    macd_line = ema_f - ema_s

    # Build MACD series from slow onward with running EMAs
    macd_vals = []
    # Initialize EMA at first close
    ef = closes[0]
    es = closes[0]
    for i in range(1, len(closes)):
        # Iterative EMA: new_ema = price * k + prev_ema * (1 - k)
        ef = closes[i] * k_fast + ef * (1 - k_fast)
        es = closes[i] * k_slow + es * (1 - k_slow)
        if i >= slow - 1:
            macd_vals.append(ef - es)

    if len(macd_vals) < sig:
        return round(macd_line, 6), None

    # Signal line: EMA of MACD series
    sig_val = sum(macd_vals[-sig:]) / sig  # seed
    for m in macd_vals[-sig:]:
        sig_val = m * k_sig + sig_val * (1 - k_sig)

    return round(macd_line, 6), round(macd_vals[-1] - sig_val, 6)


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
OUT_TRADES   = TRADES_JSON
OUT_SIGNALS  = SIGNALS_JSON
from signal_schema import RUNTIME_DB as SIGNALS_DB
os.makedirs("/var/www/hermes/data", exist_ok=True)


def _live_trailing_sl(trade_id, direction, entry_price, current_price, trail_act, trail_dist):
    """
    Compute the live trailing SL for an open position using trailing_stops.json.
    Returns None if not yet activated.
    """
    import json
    try:
        with open(TRAILING_STOPS_FILE) as f:
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
    except Exception as e:
        _log.warning(f"[get_trades] DB query failed: {e}")
        return []


def get_signals_from_db(limit=100):
    """Read recent signals from SQLite."""
    if not os.path.exists(SIGNALS_DB):
        return []
    try:
        conn = sqlite3.connect(SIGNALS_DB)
        c = conn.cursor()
        # Exclude blacklisted signal sources (rsi-confluence: 0% WR)
        c.execute("""
            SELECT token, direction, confidence, signal_type, source, price,
                   z_score, rsi_14, macd_hist, decision, created_at
            FROM signals
            WHERE source != 'rsi-confluence'
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
            "coin": r[1], "direction": r[2],
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

        # FIX (2026-04-15): Use PostgreSQL current_price (r[4]) which is updated
        # every minute by position_manager.refresh_current_prices() with live HL mids.
        # Fall back to SQLite price_history only if PostgreSQL current_price is null/0.
        current_px_pg = float(r[4]) if r[4] else 0
        current_px_sqlite = _get_current_price(token)
        if current_px_pg > 0:
            current_px = current_px_pg
        elif current_px_sqlite and current_px_sqlite > 0:
            current_px = round(current_px_sqlite, 6)
        else:
            current_px = entry_px  # last resort fallback

        # FIX (2026-04-15): Use PostgreSQL pnl_pct/pnl_usdt (r[5], r[6]) which are
        # computed by HL's unrealized_pnl in refresh_current_prices(). More accurate
        # than deriving from (potentially stale) SQLite prices. Recompute only if
        # PostgreSQL values are null — for edge cases like tokens not yet confirmed on HL.
        pnl_pct_pg = float(r[5]) if r[5] else None
        pnl_usdt_pg = float(r[6]) if r[6] else None
        if pnl_pct_pg is not None and entry_px > 0:
            # Recompute from fresh current_px (post-PostgreSQL update above) for accuracy
            if direction and direction.upper() == 'SHORT':
                pnl_pct = round((entry_px - current_px) / entry_px * 100, 4)
            else:
                pnl_pct = round((current_px - entry_px) / entry_px * 100, 4)
            pnl_usdt = round(pnl_pct / 100 * amt, 4)
        else:
            # No PostgreSQL PnL — compute from SQLite price (legacy fallback)
            if entry_px > 0:
                if direction and direction.upper() == 'SHORT':
                    pnl_pct = round((entry_px - current_px) / entry_px * 100, 4)
                else:
                    pnl_pct = round((current_px - entry_px) / entry_px * 100, 4)
                pnl_usdt = round(pnl_pct / 100 * amt, 4)
            else:
                pnl_pct = 0
                pnl_usdt = 0

        out.append({
            "coin": token,
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
    Read the authoritative hot-set from hotset.json (written by signal_compactor.py).
    Enrich each entry with live RSI/MACD computed from price_history for the
    web dashboard. Returns None if the file is missing.

    STALENESS: Uses file mtime (filesystem modification time), NOT the JSON-internal
    timestamp field. This avoids a race where signal_compactor writes the file AFTER
    the API already checked the old JSON timestamp (which hadn't been updated yet).
    Threshold: 20 minutes. If hotset.json hasn't been written in 20 min, the
    compaction pipeline may be stuck — do NOT fall back to DB.
    """
    HOTSET_FILE = '/var/www/hermes/data/hotset.json'
    try:
        # Use file mtime for staleness — this is the actual last-write time.
        # Do NOT use the JSON 'timestamp' field (written after file save, causes races).
        file_mtime = os.fstat(os.open(HOTSET_FILE, os.O_RDONLY)).st_mtime
        if (time.time() - file_mtime) > 1200:
            print(f"[hotset] hotset.json stale ({time.time()-file_mtime:.0f}s by mtime) — returning empty (signal_compactor should refresh)")
            return []
        with open(HOTSET_FILE) as f:
            data = json.load(f)
        entries = data.get('hotset', [])
        if not entries:
            return None

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
                'entry_count':    e.get('entries_count', e.get('compact_rounds', 1)),  # distinct signal sources
                'price':          live_price or e.get('price', 0),
                'rsi':            rsi_val,
                'macd':           macd_val,
                'zscore':         e.get('z_score', 0),       # was: z_score (key was never written)
                'rounds':         e.get('survival_round', 0), # was: compact_rounds (wrong direction)
                'survival':       e.get('survival_score', 0), # was: survival_score (key was never written)
                'last_seen':      str(e.get('timestamp', file_mtime)),
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

        c_rt.execute("SELECT DISTINCT token FROM signals WHERE hot_cycle_count > 0 AND executed = 0")
        for (tok,) in c_rt.fetchall():
            _load_prices(tok)

        c_rt.execute("""
            SELECT
                s.token,
                s.direction,
                MAX(s.hot_cycle_count) as max_rounds,
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
            WHERE s.hot_cycle_count >= 1
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
            # entry_count = total raw source entries (comma-separated count)
            _src_str = r['sources'] or ''
            parts = [p.strip() for p in _src_str.split(',') if p.strip()]
            entry_count = len(parts) if parts else 1
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
    """
    Export signals from DB + win rate stats for the web dashboard.

    Key insight: The raw signals table has EXPIRED/REJECTED rows dominating
    (70k+ rows). A simple LIMIT 200 query returns mostly old EXPIRED rows,
    cutting off recent APPROVED and EXECUTED signals from the output.

    Instead, query each decision category separately and merge them:
      - APPROVED: hot_set (from hotset.json) + DB APPROVED not in hot_set
      - EXECUTED: direct query, last 100
      - SKIPPED: blocked signals (price suspicious, speed=0%, already open, etc.)
      - EXPIRED: signals that exited the hot-set
      - PENDING: recent PENDING from DB
      - signals[]: APPROVED + PENDING + EXECUTED + SKIPPED + EXPIRED (for the table view)
    """
    # ── APPROVED: hot_set (authoritative) + DB APPROVED not in hot_set ─────────────
    hot_set = _get_hotset_from_file()
    if not hot_set:
        hot_set = _build_hotset_from_db()
    if not hot_set:
        hot_set = []

    # Demote hot_set entries that have a newer EXPIRED entry in the DB.
    # This handles the stale-cache window: signals.json was written before
    # signal_compactor evicted a token, so hot_set still shows APPROVED
    # but the DB already recorded the EXPIRED transition.
    # Demoted entries are removed from hot_set so they don't appear in the APPROVED tab.
    from datetime import datetime
    try:
        conn_d = sqlite3.connect(SIGNALS_DB)
        c_d = conn_d.cursor()
        to_remove = []
        for s in hot_set:
            c_d.execute(
                "SELECT created_at FROM signals WHERE token=? AND direction=? AND decision='EXPIRED' ORDER BY created_at DESC LIMIT 1",
                (s['token'], s['direction'])
            )
            row = c_d.fetchone()
            if row:
                # Compare: EXPIRED created_at vs hot_set timestamp
                # hot_set timestamp is Unix epoch float string, EXPIRED is 'YYYY-MM-DD HH:MM:SS'
                expired_ts = datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').timestamp()
                hotset_ts = float(s.get('last_seen', 0))
                if expired_ts > hotset_ts:
                    s['decision'] = 'EXPIRED'
                    s['time'] = row[0]
                    to_remove.append(s)
        conn_d.close()
        for s in to_remove:
            hot_set.remove(s)
    except Exception:
        pass

    hot_tokens = {s['token'] for s in hot_set}

    # ── DB APPROVED: candidates not in hot_set ────────────────────────────────────
    try:
        conn_ap = sqlite3.connect(SIGNALS_DB)
        conn_ap.row_factory = sqlite3.Row
        c_ap = conn_ap.cursor()
        c_ap.execute(
            "SELECT token, direction, confidence, signal_type, source, price, "
            "z_score, rsi_14, macd_hist, decision, created_at FROM signals "
            "WHERE decision='APPROVED' AND source!='rsi-confluence' "
            "ORDER BY created_at DESC LIMIT 100"
        )
        db_approved_rows = c_ap.fetchall()
        conn_ap.close()
        db_approved_signals = [{
            'token': r[0], 'direction': r[1], 'confidence': float(r[2]) if r[2] else 0,
            'type': r[3], 'source': r[4], 'price': float(r[5]) if r[5] else 0,
            'zscore': float(r[6]) if r[6] else None,
            'rsi': float(r[7]) if r[7] else None,
            'macd': float(r[8]) if r[8] else None,
            'decision': r[9] or 'APPROVED',
            'time': r[10]
        } for r in db_approved_rows]
        # Filter out tokens already in hot_set (same token+direction), then deduplicate
        seen = set()
        filtered = []
        for s in db_approved_signals:
            key = f"{s['token']}:{s['direction']}"
            if s['token'] not in hot_tokens and key not in seen:
                seen.add(key)
                filtered.append(s)
        db_approved_signals = filtered
    except Exception:
        db_approved_signals = []

    approved_list = hot_set + db_approved_signals

    # ── EXECUTED: separate query (not truncated by LIMIT 200) ─────────────────────
    try:
        conn_exec = sqlite3.connect(SIGNALS_DB)
        conn_exec.row_factory = sqlite3.Row
        c_exec = conn_exec.cursor()
        c_exec.execute(
            "SELECT token, direction, confidence, signal_type, source, price, "
            "z_score, rsi_14, macd_hist, decision, created_at FROM signals "
            "WHERE decision='EXECUTED' ORDER BY created_at DESC LIMIT 100"
        )
        executed_rows = c_exec.fetchall()
        conn_exec.close()
        # Deduplicate: keep most recent EXECUTED per token (ORDER BY created_at DESC, GROUP BY token)
        seen_tokens = set()
        executed_list = []
        for r in executed_rows:
            key = f"{r[0]}:{r[1]}"
            if key not in seen_tokens:
                seen_tokens.add(key)
                executed_list.append({
                    'token': r[0], 'direction': r[1], 'confidence': float(r[2]) if r[2] else 0,
                    'type': r[3], 'source': r[4], 'price': float(r[5]) if r[5] else 0,
                    'zscore': float(r[6]) if r[6] else None,
                    'rsi': float(r[7]) if r[7] else None,
                    'macd': float(r[8]) if r[8] else None,
                    'decision': r[9] or 'EXECUTED',
                    'time': r[10]
                })
    except Exception:
        executed_list = []

    # ── Cross-reference EXECUTED signals against trades.json ─────────────────────
    # decision=EXECUTED means "trade actually placed on Hyperliquid".
    # Only show signals that have a corresponding trade in trades.json.
    try:
        with open(OUT_TRADES) as f:
            td = json.load(f)
        traded_keys = {f"{t['coin']}:{t['direction']}" for t in td.get('open', []) + td.get('closed', [])}
        executed_list = [s for s in executed_list if f"{s['token']}:{s['direction']}" in traded_keys]
    except Exception:
        pass  # Keep executed_list as-is if trades.json unavailable

    # ── SKIPPED: blocked signals (price suspicious, speed=0%, already open, etc.) ───
    # These are valid signals that didn't execute — tracked since Bug-1 fix (2026-04-28).
    try:
        conn_sk = sqlite3.connect(SIGNALS_DB)
        conn_sk.row_factory = sqlite3.Row
        c_sk = conn_sk.cursor()
        c_sk.execute(
            "SELECT token, direction, confidence, signal_type, source, price, "
            "z_score, rsi_14, macd_hist, decision, created_at FROM signals "
            "WHERE decision='SKIPPED' ORDER BY created_at DESC LIMIT 200"
        )
        skipped_rows = c_sk.fetchall()
        conn_sk.close()
        skipped_list = [{
            'token': r[0], 'direction': r[1], 'confidence': float(r[2]) if r[2] else 0,
            'type': r[3], 'source': r[4], 'price': float(r[5]) if r[5] else 0,
            'zscore': float(r[6]) if r[6] else None,
            'rsi': float(r[7]) if r[7] else None,
            'macd': float(r[8]) if r[8] else None,
            'decision': r[9] or 'SKIPPED',
            'time': r[10]
        } for r in skipped_rows]
    except Exception:
        skipped_list = []

    # ── EXPIRED: signals that exited the hot-set ─────────────────────────────────
    # These are valid signals that survived at least one compaction round but were
    # eventually evicted (stale, de-escalated, or replaced by better signals).
    try:
        conn_ex = sqlite3.connect(SIGNALS_DB)
        conn_ex.row_factory = sqlite3.Row
        c_ex = conn_ex.cursor()
        c_ex.execute(
            "SELECT token, direction, confidence, signal_type, source, price, "
            "z_score, rsi_14, macd_hist, decision, created_at FROM signals "
            "WHERE decision='EXPIRED' ORDER BY created_at DESC LIMIT 200"
        )
        expired_rows = c_ex.fetchall()
        conn_ex.close()
        expired_list = [{
            'token': r[0], 'direction': r[1], 'confidence': float(r[2]) if r[2] else 0,
            'type': r[3], 'source': r[4], 'price': float(r[5]) if r[5] else 0,
            'zscore': float(r[6]) if r[6] else None,
            'rsi': float(r[7]) if r[7] else None,
            'macd': float(r[8]) if r[8] else None,
            'decision': r[9] or 'EXPIRED',
            'time': r[10]
        } for r in expired_rows]
    except Exception:
        expired_list = []

    # ── PENDING: recent PENDING from DB ──────────────────────────────────────────
    try:
        conn_p = sqlite3.connect(SIGNALS_DB)
        conn_p.row_factory = sqlite3.Row
        c_p = conn_p.cursor()
        c_p.execute(
            "SELECT token, direction, confidence, signal_type, source, price, "
            "z_score, rsi_14, macd_hist, decision, created_at FROM signals "
            "WHERE decision='PENDING' AND source!='rsi-confluence' "
            "ORDER BY created_at DESC LIMIT 200"
        )
        pending_rows = c_p.fetchall()
        conn_p.close()
        pending_list = [{
            'token': r[0], 'direction': r[1], 'confidence': float(r[2]) if r[2] else 0,
            'type': r[3], 'source': r[4], 'price': float(r[5]) if r[5] else 0,
            'zscore': float(r[6]) if r[6] else None,
            'rsi': float(r[7]) if r[7] else None,
            'macd': float(r[8]) if r[8] else None,
            'decision': r[9] or 'PENDING',
            'time': r[10]
        } for r in pending_rows]
    except Exception:
        pending_list = []

    # ── Win rate stats from PostgreSQL ───────────────────────────────────────────
    conn = psycopg2.connect(BRAIN_DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM trades WHERE status='closed' "
        "AND (server='Hermes' OR server IS NULL) "
        "AND entry_price>0 AND exit_price>0 "
        "AND exit_price/entry_price BETWEEN 0.01 AND 100 "
        "AND pnl_pct IS NOT NULL"
    )
    total_closed = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FILTER(WHERE pnl_pct>0), COUNT(*) FILTER(WHERE pnl_pct<=0), "
        "SUM(pnl_pct), AVG(pnl_pct) FROM trades WHERE status='closed' "
        "AND (server='Hermes' OR server IS NULL) "
        "AND entry_price>0 AND exit_price>0 "
        "AND exit_price/entry_price BETWEEN 0.01 AND 100 "
        "AND pnl_pct IS NOT NULL"
    )
    row = cur.fetchone()
    wins = row[0] or 0
    losses = row[1] or 0
    total_pnl = float(row[2] or 0)
    avg_pnl = float(row[3] or 0)
    win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
    cur.close(); conn.close()

    # ── Build signals[] for table view: APPROVED + PENDING + EXECUTED + SKIPPED + EXPIRED ─
    signals = approved_list + pending_list + executed_list + skipped_list + expired_list

    result = {
        "updated": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "approved": approved_list, "executed": executed_list, "pending": pending_list,
        "skipped": skipped_list, "expired": expired_list,
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
