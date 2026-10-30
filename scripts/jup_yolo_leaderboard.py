#!/usr/bin/env python3
"""
JUP YOLO Leaderboard Scraper — refreshes the tracked wallet list.

Scrapes https://jup.ag/yolo/?market=BTC for the Top uPnL leaderboard
(page is an SPA — requires headless Chromium), then resolves truncated
labels (e.g. "9tRB…5VA6") to full Solana addresses by cross-referencing
the public positions + trades APIs (prefix/suffix match).

Writes /root/.hermes/data/jup_yolo_leaderboard.json — consumed by
jup_yolo_monitor.py each 60s poll. Runs every 30 min via
jup-yolo-leaderboard.timer.

CEO 2026-10-09: track the leaderboard LIVE, not a one-shot wallet list.
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
YOLO_URL = "https://jup.ag/yolo/?market=BTC&mode=classic"
POSITIONS_URL = "https://jup.ag/yolo/api/watch/positions"
TRADES_URL = "https://yolo-api.jup.ag/trades?limit=100"

# Seed wallets used when the scraper fails (verified 2026-10-09, 13/13 prefix match)
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


def scrape_leaderboard_rows() -> list:
    """Scrape Top uPnL rows from the YOLO page. Returns [{rank,label,lev,side,pnl,upnl}]."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        try:
            page = browser.new_page()
            page.goto(YOLO_URL, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(8000)
            text = page.inner_text('body')
        finally:
            browser.close()

    m = re.search(r'Top uPnL.*?Auto watch', text, re.DOTALL)
    if not m:
        return []
    block = m.group(0)

    # FIX: leverage can be "1,000×" (comma) — earlier regex \d+ missed those rows,
    # silently dropping 15/20 leaderboard entries.
    pattern = re.compile(
        r'(\d+)\s*\n'
        r'([1-9A-HJ-NP-Za-km-z]{4,8})…([1-9A-HJ-NP-Za-km-z]{4})\s*\n'
        r'([\d,]+)× (Long|Short)\s*\n'
        r'\+\$([\d,\.]+)\s*\n'
        r'\+([\d,]+)%'
    )
    rows = []
    for r in pattern.finditer(block):
        rows.append({
            "rank": int(r.group(1)),
            "label": f"{r.group(2)}…{r.group(3)}",
            "prefix": r.group(2),
            "suffix": r.group(3),
            "leverage": int(r.group(4).replace(',', '')),
            "side": r.group(5),
            "pnl": float(r.group(6).replace(',', '')),
            "upnl_pct": int(r.group(7).replace(',', '')),
        })
    return rows


def resolve_addresses(rows: list) -> dict:
    """Map truncated labels to full Solana addresses via positions+trades APIs."""
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

    wallets = {}
    unresolved = []
    for r in rows:
        hits = [a for a in addrs if a.startswith(r['prefix']) and a.endswith(r['suffix'])]
        if hits:
            wallets[hits[0]] = (r['prefix'], r['upnl_pct'])
        else:
            unresolved.append(r['label'])
    return wallets, unresolved


def main():
    started = time.time()
    print(f"[lb] Scraping YOLO leaderboard...")

    try:
        rows = scrape_leaderboard_rows()
    except Exception as e:
        print(f"[lb] scrape failed: {e}")
        rows = []

    print(f"[lb] parsed {len(rows)} leaderboard rows")
    wallets, unresolved = resolve_addresses(rows) if rows else ({}, [])

    used_seed = False
    if not wallets:
        # scrape failed entirely — fall back to verified seed list
        wallets = dict(SEED_WALLETS)
        used_seed = True
        print(f"[lb] ⚠️ scrape returned nothing — using {len(SEED_WALLETS)} seed wallets")
    elif unresolved:
        print(f"[lb] unresolved labels (not in API feeds): {unresolved}")

    out = {
        "updated": int(time.time()),
        "used_seed": used_seed,
        "row_count": len(rows),
        "unresolved": unresolved,
        # {wallet: (label, upnl_pct)} — same shape the monitor expects
        "wallets": {w: list(v) for w, v in wallets.items()},
    }
    tmp = LEADERBOARD_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(out, f, indent=2)
    os.replace(tmp, LEADERBOARD_FILE)

    print(f"[lb] ✅ {len(wallets)} wallets tracked (seed={used_seed}) "
          f"in {time.time()-started:.0f}s → {LEADERBOARD_FILE}")


if __name__ == '__main__':
    main()
