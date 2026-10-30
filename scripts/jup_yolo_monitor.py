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
# live leaderboard file (written by jup_yolo_leaderboard.py every 30 min) is
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


def load_wallets() -> dict:
    """Return {wallet: (label, upnl_pct)} — LIVE leaderboard file if fresh, else seed.

    CEO 2026-10-09: leaderboard must be scanned regularly, not a one-shot list.
    jup_yolo_leaderboard.py refreshes LEADERBOARD_FILE every 30 min.
    """
    try:
        with open(LEADERBOARD_FILE) as f:
            lb = json.load(f)
        if time.time() - lb.get('updated', 0) < LEADERBOARD_STALE_SEC and lb.get('wallets'):
            return {w: tuple(v) for w, v in lb['wallets'].items()}
        print("[jup_yolo] ⚠️ leaderboard file stale (>2h) — using seed wallets")
    except (FileNotFoundError, json.JSONDecodeError, OSError, KeyError):
        pass
    return dict(JUP_YOLO_WALLETS)

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


def emit_signal(coin: str, direction: str, wallet: str, upnl_pct: int,
                leverage: int, margin_usd: float) -> bool:
    """Write a mirrored signal to the Hermes pipeline via add_signal().

    FIX (bug_hunter M2): returns add_signal()'s actual result — a blocked
    signal (blacklist, floor, trend) must NOT be marked as seen, or it is
    permanently suppressed and never retried.
    """
    from signal_schema import add_signal

    price = get_hl_price(coin)
    if price <= 0:
        print(f"[jup_yolo] SKIP {coin} — no price available")
        return False

    # Confidence from leaderboard rank + leverage conviction
    # FIX (bug_hunter L6): cap at 88 — add_signal's MAX_CONFIDENCE=88 always
    # wins; computing 95 was dead code that misrepresented stored value.
    base_conf = 70
    upnl_bonus = min(15, upnl_pct / 150)        # up to +15 for 2250%+
    lev_bonus = min(3, leverage / 333)            # up to +3 for 1000x
    confidence = min(88, base_conf + upnl_bonus + lev_bonus)

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
            'jup_wallet_short': wallet[:4],
            'jup_upnl_pct': upnl_pct,
            'jup_leverage': leverage,
            'jup_margin_usd': margin_usd,
            'jup_market': coin,
            'jup_side': direction,
            'mirror_source': 'jup_ag_yolo_leaderboard',
        },
    )
    if sig_id is None:
        # add_signal returned None = some gate blocked it (blacklist etc.)
        # Do NOT print MIRRORED — caller must not mark this position seen.
        print(f"[jup_yolo] ⛔ BLOCKED {wallet[:4]} {coin} {direction} "
              f"(add_signal returned None — will retry next cycle)")
        return False

    print(f"[jup_yolo] 🪞 MIRRORED {wallet[:4]} {coin} {direction} "
          f"({leverage}x, upnl {upnl_pct}%) conf={confidence:.0f} sig_id={sig_id}")
    return True


MAX_EMIT_ATTEMPTS = 5  # retry blocked/priceless positions before permanent skip
REEMIT_AFTER_SEC = 900  # 15 min — held positions re-mirror if their signal died


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

    # LIVE wallet list — refreshed by jup_yolo_leaderboard.py every 30 min
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

            if pid in seen:
                # RE-EMIT: held position whose signal died at an exec gate
                # (SKIPPED/EXPIRED) — retry every REEMIT_AFTER_SEC. Without this,
                # a transient vol-storm/max-positions kill silenced the position
                # permanently even though the leaderboard trader still holds it.
                age = now_ts - seen_ts.get(pid, 0)
                if age < REEMIT_AFTER_SEC:
                    continue
                if _live_signal_exists(market, direction):
                    continue  # signal alive (PENDING/APPROVED) — let it work
                # dead signal + aged → fall through to emit again, refresh ts
                print(f"[jup_yolo] 🔄 re-mirror {market} {direction} "
                      f"(attempt age {age//60}m, previous signal dead)")

            if market not in TRADEABLE_MARKETS:
                # not mirrorable — never retry (e.g. removed market)
                seen_list.append((pid, now_ts))
                continue

            label, upnl_pct = wallets[owner]
            leverage = int(p.get('leverage', 0) or 0)
            margin = float(p.get('margin', 0) or 0) / 1_000_000

            if emit_signal(market, direction, owner, upnl_pct, leverage, margin):
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
        wl = load_wallets()
        print(f"=== Tracked JUP YOLO Leaderboard Wallets ({len(wl)}) ===")
        for w, (label, upnl) in sorted(wl.items(), key=lambda x: -x[1][1]):
            print(f"  {label}… {w}  (+{upnl}%)")
        return

    # FIX (bug_hunter M4): runs on its own 60s systemd timer (not behind the
    # 22-min bulk scan) — YOLO positions live minutes at 1000x. FileLock guards
    # against overlapping timer runs double-firing the same position.
    from hermes_file_lock import FileLock
    try:
        # timeout=5: if another run holds the lock, skip fast (timer would
        # otherwise queue 60s behind interval and add latency to a 60s cycle)
        with FileLock('jup_yolo', timeout=5, interval=1):
            wl = load_wallets()
            print(f"[jup_yolo] Monitoring {len(wl)} leaderboard wallets...")
            sigs = monitor_once()
            print(f"[jup_yolo] Emitted {sigs} signals")
    except Exception as e:
        print(f"[jup_yolo] skipped (lock held or error): {e}")


if __name__ == '__main__':
    main()
