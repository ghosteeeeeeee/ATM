#!/usr/bin/env python3
"""
Jupiter YOLO Mirror — follows top leaderboard wallets and fires Hermes signals.

The YOLO wallets are Solana-based (cannot be copied on Hyperliquid directly),
so we MIRROR their direction: when they go LONG/SHORT on a tradeable coin,
we emit a Hermes signal and execute on Hyperliquid.

Data source: https://jup.ag/yolo/api/watch/positions (public, no auth)
Leaderboard: https://jup.ag/yolo/?market=BTC (top uPnL traders)

CEO 2026-10-09: Track the big-dog winners, mirror their conviction.
"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

YOLO_POSITIONS_URL = "https://jup.ag/yolo/api/watch/positions"
STATE_FILE = os.path.join(HERMES_DATA, 'jup_yolo_state.json')
LEADERBOARD_FILE = os.path.join(HERMES_DATA, 'jup_yolo_leaderboard.json')

# Static seed — verified prefix/suffix match 2026-10-09. Used only when the
# live leaderboard file (written by jup_yolo_leaderboard.py every 10 min) is
# missing or stale. Prefer load_wallets() over touching this directly.
JUP_YOLO_WALLETS = {
    # rank: (wallet, label, upnl_pct)
    "9tRBvY5zotGawm9CPitxX1gsmQS9uhNJdiQeiSZG5VA6": ("9tRB", 4264),
    "S1NFULzFDRBf3bXetEq9enLjsZvKGt7qanofpdtNy4e":  ("S1NF", 1830),  # bot, ranks 2-7
    "5mgemxgXkEE9ks3zga4ZELAdhAb6RF7ngAxmBHE5kfzh": ("5mge", 2052),
    "DohjxeYVCxx3MefFrrg6rUdpVxhVEA88P4Cn4wXTTzXc": ("Dohj", 2153),
    "FhVZTEpa1BZEN4eL3EtDFSsDs7Gak2DK61aNpnwMZawd": ("FhVZ", 2092),
    "CJN3qXUuvHcuqdvpB5YJnDgHkwtEVAcTznRTDZrgsQXe": ("CJN3", 1940),
    "84Rvf598ZTkdEC2pBQtNMZcMYQgpNf12hgaENgestFCS": ("84Rv", 163),
    "6QJVgNETqdXNt8X4V31uq7fi7jeLkBKB9FArBrTTzStv": ("6QJV", 537),
    "4mYMEZhimKe1mCbnr34fSRXzzGo8fwVXXWL7B1peqU8M": ("4mYM", 2250),
    "2WYsmvyThohY9f3DgeT4dLHK2XGJrRZHikwTgjFymJmE": ("2WYs", 1807),
    "usa4YpHpKh8nUgViRtv3mnQVa5d6RZWdkZoGmRzXG3A":  ("usa4", 1257),
    "FSG4XbDyJWJKVuvmwMbyypTh4Cqnoc8xR4gTr3ViNuLc": ("FSG4", 2045),
    "AyvQ9wnZLPYEq9CKHmZAUAuNf6qQGsZyfy3MqNKE5Spd": ("AyvQ", 588),
}

LEADERBOARD_STALE_SEC = 2 * 3600  # fall back to seed if file older than 2h
LEADERBOARD_WARN_SEC = 20 * 60    # warn loudly if older than 2x the 10min refresh


def _seed_as_stats() -> dict:
    """Convert legacy seed tuples (label, upnl_pct) to the rich stats dict shape."""
    return {w: {"label": lbl, "pnl": None, "wr": None, "trades": None,
                "volume": None, "rank": None, "source": "seed"}
            for w, (lbl, _u) in JUP_YOLO_WALLETS.items()}


def load_wallets(quiet: bool = False) -> dict:
    """Return {wallet: {label, pnl, wr, trades, volume, rank, source}}.

    LIVE leaderboard file (refreshed every 10 min by jup_yolo_leaderboard.py
    from the 3-window all/7d/24h realized-PnL API) if fresh; else seed fallback.
    Freshness is printed EVERY mirror cycle so staleness is visible in the
    log without grep archaeology (CEO hawk-tracking requirement).
    """
    try:
        with open(LEADERBOARD_FILE) as f:
            lb = json.load(f)
        age_sec = time.time() - lb.get('updated', 0)
        age_min = age_sec / 60
        n = len(lb.get('wallets', {}))
        marker = 'fresh' if age_sec < LEADERBOARD_WARN_SEC else '⚠️ STALE'
        if not quiet:
            print(f"[jup_yolo] 📋 leaderboard {marker}: {age_min:.0f}min old, {n} wallets, "
              f"seed={lb.get('used_seed')}, api={lb.get('api_ok')}, rows={lb.get('row_count', '?')}")
        if age_sec > LEADERBOARD_WARN_SEC and not quiet:
            print(f"[jup_yolo] ⚠️ leaderboard STALE >{LEADERBOARD_WARN_SEC//60}min — "
                  f"check jup-yolo-leaderboard.timer + logs/jup_yolo_lb.err.log")
        if age_sec < LEADERBOARD_STALE_SEC and lb.get('wallets'):
            raw = lb['wallets']
            # FIX (bug_hunter MED-2): non-dict file must fall back, not propagate —
            # load_wallets() sits outside monitor_once's try, and an AttributeError
            # would land in main()'s broad except → monitor silently skips every
            # 60s while appearing alive.
            if not isinstance(raw, dict):
                raise TypeError(f"wallets is {type(raw).__name__}, expected dict")
            out = {}
            for w, v in raw.items():
                if isinstance(v, dict):
                    out[w] = v
                elif isinstance(v, (list, tuple)) and len(v) >= 2:
                    # legacy tuple format (label, upnl_pct) → stats dict
                    out[w] = {"label": v[0], "pnl": None, "wr": None,
                              "trades": None, "volume": None, "rank": None,
                              "source": "legacy"}
                else:
                    # corrupt per-entry value → skip entry, keep the rest
                    continue
            if out:
                return out
            raise ValueError("wallets dict contained no usable entries")
        print("[jup_yolo] ⚠️ leaderboard file stale (>2h) — using seed wallets")
    # FIX (bug_hunter MED-2): AttributeError/TypeError included — a corrupt or
    # future-format file must degrade to seed, never crash the cycle silently.
    except (FileNotFoundError, json.JSONDecodeError, OSError, KeyError,
            AttributeError, TypeError, ValueError) as e:
        print(f"[jup_yolo] ⚠️ leaderboard file unreadable ({e}) — using seed wallets")
    return _seed_as_stats()

# Coins we can trade on Hyperliquid (YOLO market -> HL market)
# FIX (bug_hunter M1): ZEC removed — blacklisted BOTH directions in
# hermes_constants (SHORT_BLACKLIST + LONG_BLACKLIST). It was a dead path
# that logged "MIRRORED" while add_signal silently returned None.
TRADEABLE_MARKETS = {'BTC', 'SOL', 'ETH', 'HYPE'}


def _fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _norm_seen_entry(e) -> tuple:
    """Normalize a seen entry to (position_id, ts).

    FIX (bug_hunter M3 followup): state may contain three generations of
    format — plain 'id', ['id', ts], and a double-wrapped [['id', ts], 0]
    produced by a faulty migration. Walk nested lists to the innermost string
    instead of assuming shape, so the corruption self-heals on next save.
    """
    ts = 0
    cur = e
    pid = None
    for _ in range(5):  # bounded unwrap
        if isinstance(cur, str):
            pid = cur
            break
        if isinstance(cur, (list, tuple)) and cur:
            # numeric second element = timestamp
            if len(cur) == 2 and isinstance(cur[1], (int, float)) and not isinstance(cur[1], bool):
                ts = int(cur[1])
            cur = cur[0]
        else:
            break
    if pid is None:
        pid = str(e)
    return (pid, ts)


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        state = {}
    state['seen_ids'] = [_norm_seen_entry(e) for e in state.get('seen_ids', [])]
    state.setdefault('attempts', {})
    return state


def save_state(state: dict):
    # FIX (bug_hunter M3): FIFO eviction — entries arrive in insertion order
    # as (id, ts) tuples; sort by ts then keep newest 500. Never destroys
    # insertion order like the old list(set) did (which evicted live ids).
    entries = state.get('seen_ids', [])
    entries = [list(_norm_seen_entry(e)) for e in entries]
    # dedupe by pid (keep newest ts) — re-mirror path can append a second
    # (pid, ts) tuple for the same position before the next save
    dedup = {}
    for pid, ts in entries:
        if pid in dedup:
            dedup[pid] = max(dedup[pid], ts)
        else:
            dedup[pid] = ts
    entries = [[pid, ts] for pid, ts in dedup.items()]
    entries.sort(key=lambda e: e[1])
    state['seen_ids'] = entries[-500:]
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def get_hl_price(coin: str) -> float:
    """Get current price from local DB (candles_1m), fallback to HL API."""
    try:
        import sqlite3
        from paths import CANDLES_DB
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        try:
            row = conn.execute(
                "SELECT close FROM candles_1m WHERE token=? ORDER BY ts DESC LIMIT 1",
                (coin.upper(),)
            ).fetchone()
        finally:
            conn.close()
        if row:
            return float(row[0])
    except Exception:
        pass
    try:
        from hyperliquid_exchange import get_price
        return float(get_price(coin))
    except Exception:
        return 0.0


def emit_signal(coin: str, direction: str, wallet: str, stats: dict,
                leverage: int, margin_usd: float, cluster_size: int = 1) -> bool:
    """Write a mirrored signal to the Hermes pipeline via add_signal().

    stats: {label, pnl, wr, trades, volume, rank, source} from the live
    3-window realized-PnL leaderboard (seed fallback has pnl/wr=None).

    Confidence driven by REALIZED skill, not sidebar uPnL%:
      base 70 + win-rate (-20..+20) + PnL (0..8) + leverage (0..3)
      + hot top-30 (0..2) + CLUSTER (0..15), floor 50 cap 88.

    Cluster (CEO 2026-10-30): cluster_size = unique tracked wallets holding
    this coin+direction in the live feed. 2 wallets → +3, 3 → +6, capped at
    JUP_YOLO_CLUSTER_MAX_BONUS. Multiple positions by the SAME wallet
    (S1NF bot) count once — it's trader confluence, not order count.

    FIX (bug_hunter M2): returns add_signal()'s actual result — a blocked
    signal (blacklist, floor, trend) must NOT be marked as seen, or it is
    permanently suppressed and never retried.
    """
    from signal_schema import add_signal

    try:
        from hermes_constants import (
            JUP_YOLO_CLUSTER_ENABLED,
            JUP_YOLO_CLUSTER_BONUS_PER_TRADER,
            JUP_YOLO_CLUSTER_MAX_BONUS,
        )
    # FIX (bug_hunter): ImportError-only caught nothing else — a broken
    # hermes_constants (SyntaxError/RuntimeError) escaped into monitor_once's
    # per-position handler as a misleading 'position parse error' and silently
    # halted ALL mirroring every cycle. Catch Exception: degrade to fallback
    # with a loud, correctly-attributed warning.
    except Exception as _e:
        print(f"[jup_yolo] ⚠️ cluster constants unavailable "
              f"({type(_e).__name__}: {_e}) — using fallback 3/15")
        JUP_YOLO_CLUSTER_ENABLED = True
        JUP_YOLO_CLUSTER_BONUS_PER_TRADER = 3
        JUP_YOLO_CLUSTER_MAX_BONUS = 15

    price = get_hl_price(coin)
    if price <= 0:
        print(f"[jup_yolo] SKIP {coin} — no price available")
        return False

    base_conf = 70
    # win rate: 0.20 → -8, 0.50 → 0, 0.78 → +11.2
    wr = stats.get('wr')
    wr_bonus = ((wr - 0.50) * 40
                if isinstance(wr, (int, float)) and not isinstance(wr, bool)
                else 0)
    # realized pnl: $1k → +1, $8k+ → +8 (capped)
    pnl = stats.get('pnl') or 0
    pnl_bonus = min(8, max(0, pnl / 1000))
    # leverage conviction: 1000x → +3
    lev_bonus = min(3, leverage / 333)
    # hotness: TOP-30 on today's 24h board → +2, top-30 on 7d → +1.
    # FIX (bug_hunter NEW-2): enrichment covers the full fetched top-100, so
    # without the rank<=HOT_RANK_MAX gate a wallet at 7d#84 still got +1 —
    # "hot" must mean top-30 (matches the TRACK_TOP_RECENT_N selection slice).
    HOT_RANK_MAX = 30
    hot_bonus = 0
    r24 = stats.get('rank_24h')
    r7 = stats.get('rank_7d')
    if isinstance(r24, int) and 0 < r24 <= HOT_RANK_MAX:
        hot_bonus = 2
    elif isinstance(r7, int) and 0 < r7 <= HOT_RANK_MAX:
        hot_bonus = 1
    # CLUSTER: 2 wallets → +3, 3 → +6 ... capped (CEO 2026-10-30 rank higher
    # when multiple pros hold the same position in one check cycle)
    cluster_bonus = 0
    if (JUP_YOLO_CLUSTER_ENABLED and isinstance(cluster_size, int)
            and cluster_size >= 2):
        cluster_bonus = min(JUP_YOLO_CLUSTER_MAX_BONUS,
                            (cluster_size - 1) * JUP_YOLO_CLUSTER_BONUS_PER_TRADER)
    confidence = min(88, max(50, base_conf + wr_bonus + pnl_bonus + lev_bonus
                             + hot_bonus + cluster_bonus))

    signal_type = 'jup_yolo_long' if direction == 'LONG' else 'jup_yolo_short'

    sig_id = add_signal(
        token=coin,
        direction=direction,
        signal_type=signal_type,
        source='jup_yolo_mirrored',
        confidence=round(confidence, 1),
        price=price,
        exchange='hyperliquid',
        timeframe='5m',
        signal_metadata={
            'jup_wallet': wallet,
            'jup_wallet_short': stats.get('label', wallet[:4]),
            'jup_realized_pnl': stats.get('pnl'),
            'jup_win_rate': stats.get('wr'),
            'jup_trades': stats.get('trades'),
            'jup_rank': stats.get('rank'),
            'jup_pnl_24h': stats.get('pnl_24h'),       # recent-window board stats
            'jup_pnl_7d': stats.get('pnl_7d'),
            'jup_rank_24h': stats.get('rank_24h'),
            'jup_rank_7d': stats.get('rank_7d'),
            'jup_hot_window': ('24h' if stats.get('rank_24h') is not None
                               else '7d' if stats.get('rank_7d') is not None else None),
            'jup_leverage': leverage,
            'jup_margin_usd': margin_usd,
            'jup_market': coin,
            'jup_side': direction,
            # cluster confluence (CEO 2026-10-30)
            'jup_cluster_size': cluster_size,
            'jup_cluster_bonus': cluster_bonus,
            'mirror_source': 'jup_ag_yolo_leaderboard_3window',
        },
    )
    if sig_id is None:
        # add_signal returned None = some gate blocked it (blacklist etc.)
        # Do NOT print MIRRORED — caller must not mark this position seen.
        print(f"[jup_yolo] ⛔ BLOCKED {wallet[:4]} {coin} {direction} "
              f"(add_signal returned None — will retry next cycle)")
        return False

    if cluster_bonus:
        print(f"[jup_yolo] 🔥 CLUSTER: {coin} {direction} — {cluster_size} pros "
              f"hold it (+{cluster_bonus} conf)")
    hot = stats.get('rank_24h') or stats.get('rank_7d')
    hot_s = f" hot#{hot}" if hot else ""
    clu_s = f" 🔥×{cluster_size}" if cluster_bonus else ""
    print(f"[jup_yolo] 🪞 MIRRORED {wallet[:4]} {coin} {direction} "
          f"({leverage}x, ${pnl:,.0f} pnl, wr={wr if wr is not None else '?'}"
          f"{'*' if wr is not None else ''}{hot_s}{clu_s}) "
          f"conf={confidence:.0f} sig_id={sig_id}")
    return True


MAX_EMIT_ATTEMPTS = 5  # retry blocked/priceless positions before permanent skip
try:
    from hermes_constants import (
        JUP_YOLO_MAX_MIRROR_AGE_SEC, JUP_YOLO_REEMIT_AFTER_SEC)
except Exception:
    # fallback must match hermes_constants defaults (see CLUSTER import fix:
    # catch Exception, not just ImportError — a broken constants file must
    # degrade loudly upstream, never silently re-enable stale mirrors)
    JUP_YOLO_MAX_MIRROR_AGE_SEC = 600
    JUP_YOLO_REEMIT_AFTER_SEC = 180
REEMIT_AFTER_SEC = JUP_YOLO_REEMIT_AFTER_SEC  # 3 min — retry inside the freshness window


def _live_signal_exists(token: str, direction: str) -> bool:
    """True if a jup_yolo signal for token+direction is still live (PENDING/APPROVED).

    Used so a held position whose signal died at an exec gate (SKIPPED/EXPIRED)
    gets re-mirrored every REEMIT_AFTER_SEC — a one-shot emit meant transient
    gate kills (vol storm, max positions) silenced the position permanently.
    """
    try:
        import sqlite3
        from paths import RUNTIME_DB
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        try:
            row = conn.execute("""
                SELECT 1 FROM signals
                WHERE source = 'jup_yolo_mirrored'
                  AND token = ? AND direction = ?
                  AND decision IN ('PENDING','APPROVED')
                  AND created_at > datetime('now', '-30 minutes')
                LIMIT 1
            """, (token.upper(), direction.upper())).fetchone()
            return row is not None
        finally:
            conn.close()
    except Exception:
        return False  # fail-open: allow re-mirror if DB unreadable


def monitor_once() -> int:
    """One poll cycle. Uses POSITIONS feed (leaderboard wallets are holders, not churners).

    Detects NEW positions by position id — fires a mirrored Hermes signal.
    Returns number of signals emitted.

    FIX (bug_hunter L1): failed emits are RETRIED (up to MAX_EMIT_ATTEMPTS)
    instead of being marked seen forever — a transient price/blacklist miss
    would otherwise permanently suppress the mirror.
    FIX (bug_hunter L2): explicit side parsing — unknown side is skipped,
    not silently mirrored as SHORT.
    FIX (bug_hunter L3): per-position try/except so one malformed record
    cannot abort the loop and skip save_state (which caused batch re-fires).
    FIX (bug_hunter M3): seen entries are ordered (id, ts) tuples, FIFO evicted.
    """
    state = load_state()
    # load_state already normalized entries to (id, ts) via _norm_seen_entry
    seen_list = list(state.get('seen_ids', []))
    seen = {e[0] for e in seen_list}
    attempts = state.get('attempts', {})
    now_ts = int(time.time())

    # LIVE wallet list — refreshed by jup_yolo_leaderboard.py every 10 min
    wallets = load_wallets()

    # PRIMARY: positions feed — leaderboard wallets are high-x holders
    try:
        data = _fetch(YOLO_POSITIONS_URL)
    except Exception as e:
        print(f"[jup_yolo] positions fetch error: {e}")
        return 0

    positions = data.get('positions', [])
    new_signals = 0

    # PRUNE: positions that closed since last poll — free their id so a
    # re-open (fresh id) mirrors again. Without this, a wallet that opens
    # → closes → re-opens is permanently silent after its first position.
    live_pids = set()
    for p in positions:
        _pid = p.get('id', '')
        if isinstance(_pid, (list, dict)):   # FIX: multileg id can be a list
            _pid = json.dumps(_pid, sort_keys=True)
        if _pid:
            live_pids.add(str(_pid))
    seen_list = [e for e in seen_list if e[0] in live_pids]
    seen = {e[0] for e in seen_list}
    seen_ts = {e[0]: e[1] for e in seen_list}  # pid -> first-emit epoch
    # attempts bookkeeping only matters for LIVE positions — prune closed
    # pids so failed/stale entries can't accumulate unbounded in state
    attempts = {k: v for k, v in attempts.items() if k in live_pids}

    # CLUSTER MAP (CEO 2026-10-30): unique tracked wallets holding each
    # coin+direction in the live feed. A new/dead signal whose (market, dir)
    # has 2+ wallets (incl. itself) is a cluster — ranked higher at emit.
    # UNIQUE wallets: the S1NF bot holding SOL x3 counts once. Computed
    # feed-wide (not cycle-local) so opens straddling the 60s boundary still
    # cluster — "2-3 pros in the same position" is confluence regardless of
    # which 60s window each opened in.
    cluster_map = {}
    for p in positions:
        # FIX (bug_hunter): this loop sat OUTSIDE any per-position try —
        # an unhashable owner/market (list/dict) raised TypeError here,
        # aborted monitor_once before save_state, and (per L3 history)
        # caused batch re-fires. One bad record must degrade to "not
        # clustered", never kill the cycle.
        try:
            _c = p.get('owner', '')
            _m = p.get('market', '')
            _s = p.get('side', '')
            if not (isinstance(_c, str) and isinstance(_m, str)):
                continue
            if _c not in wallets or _m not in TRADEABLE_MARKETS:
                continue
            if _s == 'long':
                _d = 'LONG'
            elif _s == 'short':
                _d = 'SHORT'
            else:
                continue
            cluster_map.setdefault((_m, _d), set()).add(_c)
        except Exception as _ce:
            print(f"[jup_yolo] cluster-map record skipped: {type(_ce).__name__}: {_ce}")
            continue

    for p in positions:
        try:
            owner = p.get('owner', '')
            market = p.get('market', '')
            side = p.get('side', '')
            pid = p.get('id', '')
            # FIX (unhashable type: 'list'): coerce non-str ids (multileg
            # positions return a list) before any set/dict membership test.
            if isinstance(pid, (list, dict)):
                pid = json.dumps(pid, sort_keys=True)
            pid = str(pid) if pid else ''
            if not pid:
                continue

            if owner not in wallets:
                continue

            # explicit side parse: unknown side is SKIPPED (never default to SHORT)
            if side == 'long':
                direction = 'LONG'
            elif side == 'short':
                direction = 'SHORT'
            else:
                print(f"[jup_yolo] ⚠️ unknown side '{side}' for {market} — skipping")
                continue

            # FIX (bug_hunter): non-tradeable markets checked BEFORE the
            # re-mirror branch — previously ZEC re-mirrored loudly every cycle
            # interval with no action line after it (log said "re-mirror" then
            # did nothing), burning the re-mirror cadence for a dead path.
            if market not in TRADEABLE_MARKETS:
                # not mirrorable — never retry (e.g. blacklisted/removed market)
                if pid not in seen:
                    seen_list.append((pid, now_ts))
                continue

            if pid in seen:
                # RE-EMIT: held position whose signal died at an exec gate
                # (SKIPPED/EXPIRED) — retry every REEMIT_AFTER_SEC (3 min, must
                # fit inside the freshness gate). Without this, a transient
                # vol-storm kill silenced the position even though the trader
                # still holds it.
                age = now_ts - seen_ts.get(pid, 0)
                if age < REEMIT_AFTER_SEC:
                    continue
                # permanent give-up: bounded retries exhausted OR stale-blocked
                # (attempts pinned to MAX by the freshness gate). Without this
                # guard "giving up" was a lie — it re-mirrored forever every
                # REEMIT interval. (attempts popped on success.)
                if attempts.get(pid, 0) >= MAX_EMIT_ATTEMPTS:
                    continue
                if _live_signal_exists(market, direction):
                    continue  # signal alive (PENDING/APPROVED) — let it work
                # dead signal + aged → fall through to emit again, refresh ts
                print(f"[jup_yolo] 🔄 re-mirror {market} {direction} "
                      f"(attempt age {age//60}m, previous signal dead)")

            # ── FRESHNESS GATE (CEO 2026-10-30): "older than 5-10 mins is
            # useless" — we copy the ENTRY, not the ride. Covers first-emit AND
            # re-mirror fall-through. Steady-state tracked-wallet opens arrive
            # at age ~1min (60s poll); stale paths are newly-tracked wallets
            # mid-hold, state re-seeds, and late retries.
            _ea_raw = p.get('executedAt') or 0
            try:
                exec_at = int(_ea_raw)
            except (TypeError, ValueError):
                exec_at = 0
            if exec_at > 0:
                pos_age = now_ts - exec_at
                if pos_age > JUP_YOLO_MAX_MIRROR_AGE_SEC:
                    print(f"[jup_yolo] ⏰ STALE SKIP {market} {direction} "
                          f"— pro opened {pos_age // 60}m ago "
                          f"(> {JUP_YOLO_MAX_MIRROR_AGE_SEC // 60}m gate), not chasing")
                    if pid not in seen:
                        seen_list.append((pid, now_ts))
                    # pin attempts → terminal: re-mirror guard goes silent
                    attempts[pid] = MAX_EMIT_ATTEMPTS
                    continue
            else:
                # no executedAt in feed (unexpected — API always sends it):
                # fail-open so a feed format change can't silently kill mirrors
                print(f"[jup_yolo] ⚠️ {market} {direction} — no executedAt, treating as fresh")

            stats = wallets[owner]   # {label, pnl, wr, trades, rank, source}
            leverage = int(p.get('leverage', 0) or 0)
            margin = float(p.get('margin', 0) or 0) / 1_000_000
            cluster_size = len(cluster_map.get((market, direction), ()))

            if emit_signal(market, direction, owner, stats, leverage, margin,
                           cluster_size=cluster_size):
                new_signals += 1
                seen_list.append((pid, now_ts))   # duplicate-append is pruned/normalized on save
                attempts.pop(pid, None)
            else:
                # transient failure — bounded retry
                n = attempts.get(pid, 0) + 1
                if n >= MAX_EMIT_ATTEMPTS:
                    print(f"[jup_yolo] giving up on {pid[:24]}... after {n} attempts")
                    seen_list.append((pid, now_ts))
                    attempts.pop(pid, None)
                else:
                    attempts[pid] = n
        except Exception as e:
            print(f"[jup_yolo] position parse error: {e}")
            continue  # L3: keep looping, still save_state below

    state['seen_ids'] = seen_list
    state['attempts'] = attempts
    save_state(state)
    return new_signals


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        wl = load_wallets(quiet=True)
        n24 = sum(1 for s in wl.values() if s.get('rank_24h') is not None)
        n7 = sum(1 for s in wl.values() if s.get('rank_7d') is not None)
        print(f"=== Tracked JUP YOLO Leaderboard Wallets ({len(wl)}) ===")
        print(f"    boards: {n24} on 24h, {n7} on 7d, all-time ranks shown as rank#")
        for w, s in sorted(wl.items(), key=lambda x: -(x[1].get('pnl') or 0)):
            pnl = s.get('pnl')
            wr = s.get('wr')
            tr = s.get('trades')
            rk = s.get('rank')
            pnl_s = f"${pnl:,.0f}" if pnl is not None else "$?"
            wr_s = (f"wr={wr:.0%}"
                    if isinstance(wr, (int, float)) and not isinstance(wr, bool)
                    else "wr=?")
            tr_s = f"{tr} trades" if tr is not None else "trades=?"
            rk_s = f"rank#{rk} " if rk else ""
            # recent-board hotness marker (24h wins over 7d)
            hot_s = ""
            if s.get('rank_24h') is not None:
                hot_s = f" 🔥24h#{s['rank_24h']} +${(s.get('pnl_24h') or 0):,.0f}"
            elif s.get('rank_7d') is not None:
                hot_s = f" 🔥7d#{s['rank_7d']} +${(s.get('pnl_7d') or 0):,.0f}"
            print(f"  {rk_s}{s.get('label','?')}… {w}  {pnl_s} {wr_s} {tr_s}{hot_s} [{s.get('source','?')}]")
        return

    # FIX (bug_hunter M4): runs on its own 60s systemd timer (not behind the
    # 22-min bulk scan) — YOLO positions live minutes at 1000x. FileLock guards
    # against overlapping timer runs double-firing the same position.
    from hermes_file_lock import FileLock
    try:
        # timeout=5: if another run holds the lock, skip fast (timer would
        # otherwise queue 60s behind interval and add latency to a 60s cycle)
        with FileLock('jup_yolo', timeout=5, interval=1):
            # quiet — monitor_once prints the freshness line itself (once per cycle)
            wl = load_wallets(quiet=True)
            print(f"[jup_yolo] Monitoring {len(wl)} leaderboard wallets...")
            sigs = monitor_once()
            print(f"[jup_yolo] Emitted {sigs} signals")
    except Exception as e:
        print(f"[jup_yolo] skipped (lock held or error): {e}")


if __name__ == '__main__':
    main()
