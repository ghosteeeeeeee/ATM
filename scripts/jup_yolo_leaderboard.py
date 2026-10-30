#!/usr/bin/env python3
"""
JUP YOLO Leaderboard Scraper — refreshes the tracked wallet list (hawk tracking).

PRIMARY: https://yolo-api.jup.ag/leaderboard?sort=pnl&window=all&limit=100
  Direct JSON — FULL Solana addresses + realized PnL, win rate, trades, volume.
  (CEO 2026-10-30: the /yolo/leaderboard page ?period=all&category=pnl board.)

SECONDARY: sidebar Top uPnL scrape on the trading page (Playwright) — merges
  any additional current-session wallets not present in the all-time API.

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
LEADERBOARD_API = "https://yolo-api.jup.ag/leaderboard?sort=pnl&window=all&limit=100"
SIDEBAR_URL = "https://jup.ag/yolo/?market=BTC&mode=classic"
POSITIONS_URL = "https://jup.ag/yolo/api/watch/positions"
TRADES_URL = "https://yolo-api.jup.ag/trades?limit=100"

# Track the top N by realized all-time PnL — these are the money leaders
TRACK_TOP_N = 50
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


def fetch_leaderboard_api() -> list:
    """PRIMARY: all-time realized-PnL board with FULL addresses + stats."""
    data = _fetch(LEADERBOARD_API)
    leaders = data.get('leaders', [])
    out = []
    for l in leaders:
        owner = l.get('owner', '')
        if not owner:
            continue
        pnl = float(l.get('pnl', 0) or 0)
        wr = float(l.get('winRate', 0) or 0)
        trades = int(l.get('trades', 0) or 0)
        out.append({
            "wallet": owner,
            "label": owner[:4],
            "rank": int(l.get('rank', 0) or 0),
            "pnl": pnl,
            "wr": round(wr, 4),
            "trades": trades,
            "volume": float(l.get('volume', 0) or 0),
            "source": "api",
        })
    return out


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
                "wallet": hits[0],
                "label": r['prefix'],
                "rank": r['rank'],
                "pnl": r['pnl'],
                "wr": None,           # sidebar has no win rate
                "trades": None,
                "volume": None,
                "upnl_pct": r['upnl_pct'],
                "source": "sidebar",
            })
    return resolved


def select_tracked(entries: list) -> dict:
    """Track top TRACK_TOP_N by realized PnL + consistency players (high WR).

    Returns {wallet: {label, pnl, wr, trades, volume, rank, source}}.
    """
    # de-dupe by wallet — API entry wins (has full stats)
    by_wallet = {}
    for e in entries:
        w = e['wallet']
        if w not in by_wallet or e['source'] == 'api':
            by_wallet[w] = e

    # sort by realized PnL descending
    ranked = sorted(by_wallet.values(), key=lambda x: -(x.get('pnl') or 0))
    selected = ranked[:TRACK_TOP_N]

    # consistency players deeper in the list
    selected_wallets = {e['wallet'] for e in selected}
    for e in ranked[TRACK_TOP_N:]:
        wr = e.get('wr')
        trades = e.get('trades')
        if (wr is not None and trades is not None
                and wr >= QUALITY_MIN_WR and trades >= QUALITY_MIN_TRADES
                and (e.get('pnl') or 0) >= QUALITY_MIN_PNL):
            selected.append(e)
            selected_wallets.add(e['wallet'])

    out = {}
    for e in selected:
        out[e['wallet']] = {
            "label": e.get('label', e['wallet'][:4]),
            "pnl": round(e.get('pnl') or 0, 2),
            "wr": e.get('wr'),
            "trades": e.get('trades'),
            "volume": e.get('volume'),
            "rank": e.get('rank'),
            "source": e.get('source', '?'),
        }
    return out


def main():
    started = time.time()
    print(f"[lb] Refreshing YOLO leaderboard...")

    entries = []
    api_ok = False
    try:
        api_entries = fetch_leaderboard_api()
        entries.extend(api_entries)
        api_ok = bool(api_entries)
        print(f"[lb] API: {len(api_entries)} leaders (all-time realized PnL)")
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
    topstr = ', '.join(f"{v['label']}(${v['pnl']:,.0f})" for _, v in top3)
    print(f"[lb] ✅ {len(wallets)} wallets tracked (seed={used_seed}, api={api_ok}) "
          f"in {time.time()-started:.0f}s → top: {topstr}")


if __name__ == '__main__':
    main()
