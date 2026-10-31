#!/usr/bin/env python3
"""
JUP YOLO Leaderboard Scraper — refreshes the tracked wallet list (hawk tracking).

PRIMARY: https://yolo-api.jup.ag/leaderboard?sort=pnl&window=all&limit=100
  Direct JSON — FULL Solana addresses + realized PnL, win rate, trades, volume.
  (CEO 2026-10-30: the /yolo/leaderboard page ?period=all&category=pnl board.)

SECONDARY: sidebar Top uPnL scrape on the trading page (Playwright) — merges
  any additional current-session wallets not present in any API window.

Writes /root/.hermes/data/jup_yolo_leaderboard.json — consumed every 60s by
jup_yolo_monitor.py. Timer: jup-yolo-leaderboard.timer (10 min, Persistent).

CEO 2026-10-30: "stats are nuts" — track the top realized-PnL traders live.
"""
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

LEADERBOARD_FILE = os.path.join(HERMES_DATA, 'jup_yolo_leaderboard.json')
# API windows: all-time + 7d + 24h (CEO 2026-10-30: track hot traders too,
# not just all-time money leaders — a wallet crushing it TODAY shows up on
# the 24h board long before it climbs the all-time list)
LEADERBOARD_API = "https://yolo-api.jup.ag/leaderboard?sort=pnl&window={window}&limit=100"
TRACK_WINDOWS = ("all", "7d", "24h")
SIDEBAR_URL = "https://jup.ag/yolo/?market=BTC&mode=classic"
POSITIONS_URL = "https://jup.ag/yolo/api/watch/positions"
TRADES_URL = "https://yolo-api.jup.ag/trades?limit=100"

# Track the top N by realized all-time PnL — these are the money leaders
TRACK_TOP_N = 50
# Hot traders: top N on the 7d and 24h boards (currently active wallets)
TRACK_TOP_RECENT_N = 30
# Plus any consistency players deeper in the list (skilled, lower volume)
QUALITY_MIN_WR = 0.60
QUALITY_MIN_TRADES = 20
QUALITY_MIN_PNL = 500.0

# Seed wallets (verified prefix/suffix 2026-10-09) — used only if ALL sources fail
SEED_WALLETS = {
    "9tRBvY5zotGawm9CPitxX1gsmQS9uhNJdiQeiSZG5VA6": ("9tRB", 4264),
    "S1NFULzFDRBf3bXetEq9enLjsZvKGt7qanofpdtNy4e":  ("S1NF", 1830),
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


def _fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def fetch_window(window: str) -> list:
    """Fetch one leaderboard window (all/7d/24h). Returns raw leader rows."""
    data = _fetch(LEADERBOARD_API.format(window=window))
    out = []
    for l in data.get('leaders', []):
        owner = l.get('owner', '')
        if not owner:
            continue
        out.append({
            "window": window,
            "wallet": owner,
            "rank": int(l.get('rank', 0) or 0),
            "pnl": float(l.get('pnl', 0) or 0),
            "wr": round(float(l.get('winRate', 0) or 0), 4),
            "trades": int(l.get('trades', 0) or 0),
            "volume": float(l.get('volume', 0) or 0),
        })
    return out


def fetch_leaderboards_all_windows() -> tuple:
    """Fetch all three windows and merge into per-wallet stats.

    Base keys (pnl/wr/trades/rank/volume) = all-time for back-compat with
    monitor confidence math; recent windows stored as pnl_7d/pnl_24h/etc.

    Returns (entries, api_ok) where entries are merged wallet dicts.
    """
    by_wallet = {}
    fetched = {}
    for win in TRACK_WINDOWS:
        try:
            rows = fetch_window(win)
            fetched[win] = len(rows)
        except Exception as e:
            print(f"[lb] ⚠️ window={win} failed: {e}")
            continue
        for r in rows:
            w = r["wallet"]
            if win == "all":
                # base = all-time stats (back-compat shape: pnl/wr/trades/rank/volume)
                entry = {
                    "wallet": w,
                    "label": w[:4],
                    "pnl": r["pnl"],
                    "wr": r["wr"],
                    "trades": r["trades"],
                    "volume": r["volume"],
                    "rank": r["rank"],
                    "source": "api",
                    "windows": [win],
                }
                # first-wins on repeated all-time rows
                by_wallet.setdefault(w, entry)
                by_wallet[w].setdefault("windows", [])
                if win not in by_wallet[w]["windows"]:
                    by_wallet[w]["windows"].append(win)
            else:
                # recent window: enrich existing or create recent-only entry
                if w not in by_wallet:
                    # FIX (bug_hunter NEW-1): adopt base ONCE, at creation.
                    # Old code re-adopted on every window (checked rank is None,
                    # which stays true forever) → 24h silently overwrote the 7d
                    # base for 21 dual-board wallets (e.g. $689 → $198,
                    # 3.5x understated), and suppressed their 🔥7d marker.
                    # TRACK_WINDOWS order = (all, 7d, 24h) → base = first
                    # recent window seen (7d); later windows stay in pnl_24h etc.
                    by_wallet[w] = {
                        "wallet": w, "label": w[:4],
                        "pnl": r["pnl"], "wr": r["wr"],
                        "trades": r["trades"], "volume": r["volume"],
                        "rank": None,
                        "source": "api", "windows": [win],
                        "base_from": win,
                    }
                e = by_wallet[w]
                # per-window store (always — even for the just-created entry,
                # so pnl_7d/rank_7d are recorded alongside the adopted base)
                e[f"pnl_{win}"] = r["pnl"]
                e[f"wr_{win}"] = r["wr"]
                e[f"trades_{win}"] = r["trades"]
                e[f"rank_{win}"] = r["rank"]
                if win not in e.get("windows", []):
                    e.setdefault("windows", []).append(win)

    api_ok = bool(fetched)
    print(f"[lb] API windows: {fetched}")
    return list(by_wallet.values()), api_ok


def scrape_sidebar_labels() -> list:
    """SECONDARY: Top uPnL sidebar rows from the trading page (truncated labels)."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            try:
                page = browser.new_page()
                page.goto(SIDEBAR_URL, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(7000)
                text = page.inner_text('body')
            finally:
                browser.close()
    except Exception as e:
        print(f"[lb] sidebar scrape failed: {e}")
        return []

    m = re.search(r'Top uPnL.*?Auto watch', text, re.DOTALL)
    if not m:
        return []
    # FIX: leverage can be "1,000×" (comma) — plain \d+ dropped 15/20 rows
    pattern = re.compile(
        r'(\d+)\s*\n'
        r'([1-9A-HJ-NP-Za-km-z]{4,8})…([1-9A-HJ-NP-Za-km-z]{4})\s*\n'
        r'([\d,]+)× (Long|Short)\s*\n'
        r'\+\$([\d,\.]+)\s*\n'
        r'\+([\d,]+)%'
    )
    rows = []
    for r in pattern.finditer(m.group(0)):
        rows.append({
            "label": f"{r.group(2)}…{r.group(3)}",
            "prefix": r.group(2),
            "suffix": r.group(3),
            "rank": int(r.group(1)),
            "leverage": int(r.group(4).replace(',', '')),
            "side": r.group(5),
            "pnl": float(r.group(6).replace(',', '')),
            "upnl_pct": int(r.group(7).replace(',', '')),
            "source": "sidebar",
        })
    return rows


def resolve_sidebar_labels(rows: list) -> list:
    """Resolve truncated sidebar labels to full addresses via positions+trades APIs."""
    addrs = set()
    try:
        for p in _fetch(POSITIONS_URL).get('positions', []):
            addrs.add(p.get('owner', ''))
    except Exception as e:
        print(f"[lb] positions fetch failed: {e}")
    try:
        for t in _fetch(TRADES_URL).get('trades', []):
            addrs.add(t.get('owner', ''))
    except Exception as e:
        print(f"[lb] trades fetch failed: {e}")

    resolved = []
    for r in rows:
        hits = [a for a in addrs if a.startswith(r['prefix']) and a.endswith(r['suffix'])]
        if hits:
            resolved.append({
                # FIX (bug_hunter LOW-5): sorted() — hits is a set; [0] on a set
                # iteration is nondeterministic across processes (hash randomization)
                # when 2+ addresses share the same 4+4 prefix/suffix.
                "wallet": sorted(hits)[0],
                "label": r['prefix'],
                # FIX (bug_hunter LOW-4): sidebar rank is SESSION uPnL rank, not
                # all-time realized rank — conflating them made the list show two
                # "rank#8"s and put misleading values in jup_rank metadata.
                "rank": None,
                "session_rank": r['rank'],
                "pnl": r['pnl'],
                "wr": None,           # sidebar has no win rate
                "trades": None,
                "volume": None,
                "upnl_pct": r['upnl_pct'],
                "source": "sidebar",
            })
    return resolved


def select_tracked(entries: list) -> dict:
    """Track top TRACK_TOP_N all-time + top TRACK_TOP_RECENT_N per recent window
    + consistency players (high WR).

    CEO 2026-10-30: also track 24h/7d hot boards — a wallet printing money
    TODAY gets mirrored long before it climbs the all-time list.

    Returns {wallet: {label, pnl, wr, trades, volume, rank, session_rank,
                      pnl_7d, pnl_24h, wr_7d, wr_24h, rank_7d, rank_24h,
                      windows, source}}.
    """
    # de-dupe by wallet — entries are already merged per-wallet by
    # fetch_leaderboards_all_windows(); sidebar rows are separate wallets
    # (their 'api' counterparts, if any, arrive merged and win on collision)
    by_wallet = {}
    for e in entries:
        w = e['wallet']
        if w not in by_wallet or e.get('source') == 'api':
            by_wallet[w] = e

    all_entries = list(by_wallet.values())
    selected_wallets = set()

    # all-time money leaders — ONLY true all-time board members.
    # FIX (bug_hunter check-2): recent-only entries carry an adopted base pnl
    # that competed in this slice and silently displaced real all-time wallets
    # (2 lost today, incl. seed wallet CJN3 at rank#50/$549). Recent-only
    # wallets enter selection through their own board slice below.
    ranked_all = sorted((e for e in all_entries if e.get('rank') is not None),
                        key=lambda x: -(x.get('pnl') or 0))
    for e in ranked_all[:TRACK_TOP_N]:
        selected_wallets.add(e['wallet'])

    # hot traders from 7d and 24h boards (top TRACK_TOP_RECENT_N per window —
    # this is where recent-only wallets get selected)
    for win in ('7d', '24h'):
        key = f'pnl_{win}'
        ranked_win = sorted((e for e in all_entries if e.get(key) is not None),
                            key=lambda x: -(x.get(key) or 0))
        for e in ranked_win[:TRACK_TOP_RECENT_N]:
            selected_wallets.add(e['wallet'])

    # consistency players deeper in the all-time list
    for e in ranked_all[TRACK_TOP_N:]:
        wr = e.get('wr')
        trades = e.get('trades')
        if (wr is not None and trades is not None
                and wr >= QUALITY_MIN_WR and trades >= QUALITY_MIN_TRADES
                and (e.get('pnl') or 0) >= QUALITY_MIN_PNL):
            selected_wallets.add(e['wallet'])

    # sidebar-only session wallets: always tracked — they hold CURRENT positions
    # on the feed we poll (API-collided wallets already tracked via source='api')
    for e in all_entries:
        if e.get('source') == 'sidebar':
            selected_wallets.add(e['wallet'])

    out = {}
    for e in all_entries:
        if e['wallet'] not in selected_wallets:
            continue
        out[e['wallet']] = {
            "label": e.get('label', e['wallet'][:4]),
            "pnl": round(e.get('pnl') or 0, 2),
            "wr": e.get('wr'),
            "trades": e.get('trades'),
            "volume": e.get('volume'),
            "rank": e.get('rank'),
            "session_rank": e.get('session_rank'),  # sidebar Top-uPnL rank (not all-time)
            # per-window (recent) stats — present only if wallet is on that board
            "pnl_7d": round(e['pnl_7d'], 2) if e.get('pnl_7d') is not None else None,
            "pnl_24h": round(e['pnl_24h'], 2) if e.get('pnl_24h') is not None else None,
            "wr_7d": e.get('wr_7d'),
            "wr_24h": e.get('wr_24h'),
            "rank_7d": e.get('rank_7d'),
            "rank_24h": e.get('rank_24h'),
            "windows": e.get('windows', []),
            "source": e.get('source', '?'),
        }
    return out


def main():
    started = time.time()
    print(f"[lb] Refreshing YOLO leaderboard...")

    entries = []
    api_ok = False
    try:
        # all three windows: all-time + 7d + 24h (errors per-window, not fatal)
        api_entries, api_ok = fetch_leaderboards_all_windows()
        entries.extend(api_entries)
        n_recent = len({e['wallet'] for e in api_entries
                        if e.get('pnl_7d') is not None or e.get('pnl_24h') is not None})
        print(f"[lb] API: {len(api_entries)} wallets merged ({n_recent} on a recent board)")
    except Exception as e:
        print(f"[lb] ⚠️ leaderboard API failed: {e}")

    # sidebar adds current-session wallets not on the all-time board
    sidebar = scrape_sidebar_labels()
    if sidebar:
        resolved = resolve_sidebar_labels(sidebar)
        new = [r for r in resolved if r['wallet'] not in {e['wallet'] for e in entries}]
        entries.extend(new)
        print(f"[lb] sidebar: {len(sidebar)} rows → {len(resolved)} resolved, {len(new)} new")

    wallets = select_tracked(entries)

    used_seed = False
    if not wallets:
        wallets = {w: {"label": lbl, "pnl": None, "wr": None, "trades": None,
                       "volume": None, "rank": None, "source": "seed"}
                   for w, (lbl, _u) in SEED_WALLETS.items()}
        used_seed = True
        print(f"[lb] ⚠️ ALL sources failed — using {len(SEED_WALLETS)} seed wallets")

    # ── CEO giants-light fixes 3+4: sticky wallets + first_seen tenure ──────
    # Fix 3: sidebar label resolution needs the wallet to be in the LIVE
    # positions feed — once a tracked trader CLOSES their positions (like every
    # snapshot winner the user watched profit), their label can't resolve on the
    # next 10-min scrape and they silently fall off the tracked list (observed:
    # Dohj + 4mYM lost mid-session). Keep previously-tracked wallets alive for
    # TRACKY_STICKY_TTL_SEC after their first_seen; API-sourced wallets
    # re-resolve regardless, so this only rescues the churn class.
    # first_seen powers freshness policy (b) in the monitor: a wallet tracked
    # BEFORE a position opened gets the 60-min window (our latency, not a
    # stale entry); a wallet first seen mid-hold keeps the strict 10-min gate.
    TRACKY_STICKY_TTL_SEC = 24 * 3600
    prev_wallets = {}
    if not used_seed and os.path.exists(LEADERBOARD_FILE):
        try:
            with open(LEADERBOARD_FILE) as _pf:
                prev_wallets = json.load(_pf).get('wallets') or {}
        except (json.JSONDecodeError, OSError, KeyError, AttributeError):
            prev_wallets = {}
    now_i = int(time.time())
    for _w, _s in wallets.items():
        _prev = prev_wallets.get(_w)
        _fs = _prev.get('first_seen') if isinstance(_prev, dict) else None
        _s['first_seen'] = int(_fs) if _fs else now_i
    sticky_added = 0
    for _w, _prev in prev_wallets.items():
        if _w in wallets or not isinstance(_prev, dict):
            continue
        _fs = int(_prev.get('first_seen') or 0)
        if 0 < now_i - _fs <= TRACKY_STICKY_TTL_SEC:
            _prev = dict(_prev)
            _prev['sticky'] = True
            wallets[_w] = _prev
            sticky_added += 1
    if len(wallets) > 200:  # hard bound under pathological churn
        wallets = dict(sorted(wallets.items(),
                              key=lambda kv: -(kv[1].get('first_seen') or 0))[:200])
    if sticky_added:
        print(f"[lb] 📌 sticky: +{sticky_added} recently-tracked wallets kept "
              f"despite selection churn (24h TTL)")

    out = {
        "updated": int(time.time()),
        "used_seed": used_seed,
        "api_ok": api_ok,
        "row_count": len(entries),
        "wallet_count": len(wallets),
        # {wallet: {label, pnl, wr, trades, volume, rank, source}}
        "wallets": wallets,
    }
    tmp = LEADERBOARD_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(out, f, indent=2)
    os.replace(tmp, LEADERBOARD_FILE)

    top3 = sorted(wallets.items(), key=lambda x: -(x[1].get('pnl') or 0))[:3]
    # FIX (bug_hunter MED-1): seed wallets have pnl=None — formatting None
    # crashed the seed-fallback path with TypeError after the file was written,
    # failing the systemd unit exactly when all sources are already down.
    topstr = ', '.join(f"{v['label']}(${(v.get('pnl') or 0):,.0f})" for _, v in top3)
    print(f"[lb] ✅ {len(wallets)} wallets tracked (seed={used_seed}, api={api_ok}) "
          f"in {time.time()-started:.0f}s → top: {topstr}")


if __name__ == '__main__':
    main()
