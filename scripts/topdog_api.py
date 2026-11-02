#!/usr/bin/env python3
"""
topdog_api.py — Top-Dog Tracker dashboard data (T 2026-11-01).

Writes /var/www/hermes/data/topdogs.json — polled every 15s by
web/topdogs.html, regenerated every 60s by hermes-topdog.timer.

Sources:
  - data/jup_yolo_leaderboard.json (jup-yolo-leaderboard.timer, 10min) —
    per-wallet stats: pnl / wr / trades / volume (+7d/24h windows)
  - https://jup.ag/yolo/api/watch/positions (public, no auth) — LIVE
    positions of tracked wallets: owner, market, side, leverage, margin

Output sections (each guarded — one failure never aborts the run, and the
file is always written with a fresh 'updated'; atomic replace so readers
never see a partial/zero-byte file — the copy_trader lesson):
  tiers    — top TOPDOG_TIER_PCT by composite percentile of pnl+wr+volume,
             with their live positions
  coins    — per market: unique-trader long/short counts (tier + all),
             cluster flag, member chips
  clusters — same coin+side held by >= TOPDOG_CLUSTER_MIN unique tracked
             wallets right now (the mirror's cluster bonus, surfaced)
  events   — NEW positions since the previous run, newest first; each
             carries tier-at-the-time and the cluster size it landed in

The positions feed has no equity field: "portfolio size" in the composite
uses volume (documented in hermes_constants TOPDOG block).
"""
import json
import math
import os
import sys
import time
import traceback
import urllib.request
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, WWW_DATA
from hermes_constants import (
    TOPDOG_TIER_PCT, TOPDOG_MIN_TRADES, TOPDOG_CLUSTER_MIN,
    TOPDOG_EVENT_RETAIN, TOPDOG_STATE_TTL_SEC,
)

POSITIONS_URL = "https://jup.ag/yolo/api/watch/positions"
LEADERBOARD_FILE = os.path.join(HERMES_DATA, 'jup_yolo_leaderboard.json')
STATE_FILE = os.path.join(HERMES_DATA, 'topdog_state.json')
OUT = os.path.join(WWW_DATA, 'topdogs.json')
# served page: repo web/ copy -> /var/www/hermes (nothing else re-copies it;
# a plain `cp` from web/ yields mode 600 because the source is 600 -> 403)
PAGE_SRC = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'web', 'topdogs.html')
PAGE_DST = os.path.join(os.path.dirname(WWW_DATA), 'topdogs.html')


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _usd(raw):
    """positions feed raw units: 6-decimal fixed point (200000000 -> $200).

    Accepts str/int/float (the feed has used both str and numeric JSON);
    bool and anything non-numeric -> None (rendered as '–' downstream).
    """
    try:
        if isinstance(raw, bool):
            return None
        if isinstance(raw, (int, float)):
            val = float(raw)
        else:
            val = float(str(raw).strip())
        return round(val / 1_000_000.0, 2)
    except (TypeError, ValueError):
        return None


def _pid(p):
    """Position id — multileg ids come back as list/dict (monitor fix)."""
    v = p.get('id', '') or p.get('positionId', '')
    if isinstance(v, (list, dict)):
        return json.dumps(v, sort_keys=True)
    return str(v)


def _load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, KeyError, TypeError):
        return default


def _atomic_write(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(obj, f, default=str)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def compute_tier(wallets):
    """Top TOPDOG_TIER_PCT by mean percentile rank of pnl / wr / volume.

    Percentiles (not raw sums) so the three metrics are scale-free; volume
    stands in for portfolio size (no equity field on the leaderboard API).
    wallets is {addr: stats} — entries do NOT carry a 'wallet' field (the
    address is the dict key; verified against the stored file).
    Returns (tier_set, ranked) where ranked = [(score, addr, stats)]
    best-first over every eligible wallet.
    """
    eligible = [(a, w) for a, w in wallets.items()
                if isinstance(w, dict)
                and int(_f(w.get('trades'))) >= TOPDOG_MIN_TRADES
                and w.get('pnl') is not None]
    n = len(eligible)
    if n < 2:
        return set(), []
    metrics = {'pnl': [], 'wr': [], 'volume': []}
    for _, w in eligible:
        for m in metrics:
            metrics[m].append(_f(w.get(m)))
    # pct rank per metric: best (highest) -> 1.0
    pcts = {}
    for m, vals in metrics.items():
        order = sorted(range(n), key=lambda i: vals[i])  # asc
        rank_of = {}
        for pos, idx in enumerate(order):
            rank_of[idx] = pos / (n - 1)
        pcts[m] = rank_of
    ranked = []
    for i, (addr, w) in enumerate(eligible):
        score = sum(pcts[m][i] for m in metrics) / len(metrics)
        ranked.append((score, addr, w))
    ranked.sort(key=lambda x: -x[0])
    tier_n = max(1, math.ceil(n * TOPDOG_TIER_PCT))
    tier_set = {addr for _, addr, _ in ranked[:tier_n]}
    return tier_set, ranked


def main():
    now = int(time.time())
    out = {'updated': now, 'api_ok': False, 'errors': []}

    # ── wallet stats (10-min leaderboard refresh) ──
    lb = _load_json(LEADERBOARD_FILE, {})
    if not isinstance(lb, dict):          # valid JSON but wrong shape
        lb = {}
        out['errors'].append('leaderboard file is not a JSON object')
    wallets = lb.get('wallets') or {}
    if not isinstance(wallets, dict):
        wallets = {}
        out['errors'].append('leaderboard wallets entry is not a JSON object')
    bad_w = sum(1 for v in wallets.values() if not isinstance(v, dict))
    if bad_w:
        out['errors'].append(f'leaderboard: {bad_w} non-object wallet entries dropped')
        wallets = {k: v for k, v in wallets.items() if isinstance(v, dict)}
    if not wallets:
        out['errors'].append('leaderboard file missing/empty')
    tier_set, ranked = compute_tier(wallets)
    score_by_addr = {addr: round(score, 3) for score, addr, _ in ranked}
    out['wallets_n'] = len(wallets)
    out['tier_n'] = len(tier_set)
    out['tier_pct'] = TOPDOG_TIER_PCT
    out['leaderboard_updated'] = lb.get('updated')

    # ── live positions ──
    positions = []
    try:
        req = urllib.request.Request(POSITIONS_URL,
                                     headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        positions = data.get('positions') or []
        out['api_ok'] = True
    except Exception as e:
        out['errors'].append(f'positions fetch: {type(e).__name__}: {e}')

    # parse feed rows (one bad record must not kill the cycle — monitor rule)
    rows = []
    for p in positions:
        try:
            owner = p.get('owner', '')
            market = p.get('market', '')
            side = p.get('side', '')
            if not (isinstance(owner, str) and isinstance(market, str)
                    and side in ('long', 'short') and owner and market):
                continue
            executed_at = int(_f(p.get('executedAt')))
            market_u = market.upper()
            # id-less row: synthetic key so it still counts for clusters but
            # can never collide on the shared '' key (would swallow events
            # for every other id-less position in the feed)
            pid = _pid(p) or f'noid:{owner}:{market_u}:{side}:{executed_at}'
            rows.append({
                'owner': owner, 'market': market_u, 'side': side,
                'pid': pid,
                'leverage': int(_f(p.get('leverage'))),
                'margin': _usd(p.get('margin')),
                'notional': _usd(p.get('notional')),
                'executed_at': executed_at,
            })
        except Exception as re_:
            out['errors'].append(f'row parse: {type(re_).__name__}: {re_}')

    # unique traders per (market, side) — cluster basis, UNIQUE wallets
    owners_ms = defaultdict(set)
    positions_by_owner = defaultdict(list)
    for r in rows:
        owners_ms[(r['market'], r['side'])].add(r['owner'])
        positions_by_owner[r['owner']].append(r)

    # ── clusters now ──
    clusters = []
    for (market, side), owners in sorted(owners_ms.items()):
        if len(owners) >= TOPDOG_CLUSTER_MIN:
            tier_owners = [o for o in owners if o in tier_set]
            mem = [r for r in rows
                   if r['market'] == market and r['side'] == side]
            clusters.append({
                'market': market, 'side': side,
                'wallets': len(owners), 'tier_wallets': len(tier_owners),
                'tracked': sum(1 for o in owners if o in wallets),
                'labels': sorted((wallets.get(o, {}).get('label') or o[:4])
                                 for o in owners),
                'notional': round(sum(r['notional'] or 0 for r in mem), 2),
            })
    clusters.sort(key=lambda c: (-c['tier_wallets'], -c['wallets']))
    out['clusters'] = clusters

    # ── per-coin cards ──
    coins = {}
    for (market, side), owners in owners_ms.items():
        c = coins.setdefault(market, {
            'tier_long': 0, 'tier_short': 0,
            'all_long': 0, 'all_short': 0,
            'cluster_long': False, 'cluster_short': False,
            'members': [],
        })
        tier_n = sum(1 for o in owners if o in tier_set)
        if side == 'long':
            c['all_long'] = len(owners)
            c['tier_long'] = tier_n
            c['cluster_long'] = len(owners) >= TOPDOG_CLUSTER_MIN
        else:
            c['all_short'] = len(owners)
            c['tier_short'] = tier_n
            c['cluster_short'] = len(owners) >= TOPDOG_CLUSTER_MIN
    for (market, side), owners in owners_ms.items():
        for o in owners:
            w = wallets.get(o, {})
            mem_rows = [r for r in rows if r['owner'] == o
                        and r['market'] == market and r['side'] == side]
            coins[market]['members'].append({
                'wallet': o, 'label': w.get('label') or o[:4],
                'side': side, 'tier': o in tier_set,
                'tracked': o in wallets,
                'positions': len(mem_rows),
                'leverage': max((r['leverage'] for r in mem_rows), default=0),
                'margin': round(sum(r['margin'] or 0 for r in mem_rows), 2),
                'score': score_by_addr.get(o),
            })
    out['coins'] = coins

    # ── tier table ──
    tiers = []
    for score, addr, w in ranked:
        if addr not in tier_set:
            continue
        held = positions_by_owner.get(addr, [])
        tiers.append({
            'wallet': addr, 'label': w.get('label') or addr[:4],
            'rank': w.get('rank'), 'score': round(score, 3),
            'pnl': w.get('pnl'), 'pnl_7d': w.get('pnl_7d'),
            'pnl_24h': w.get('pnl_24h'),
            'wr': w.get('wr'), 'wr_7d': w.get('wr_7d'),
            'trades': w.get('trades'), 'volume': w.get('volume'),
            'positions': [{'market': r['market'], 'side': r['side'],
                           'leverage': r['leverage'], 'margin': r['margin']}
                          for r in held],
        })
    out['tiers'] = tiers

    # ── events: new position ids since last run ──
    state = _load_json(STATE_FILE, None)
    if state is not None and not isinstance(state, dict):
        # valid JSON but wrong shape (partial/corrupt state) — reseeds
        # silently instead of crashing every subsequent run
        out['errors'].append('state file has unexpected shape — reseeding')
        state = None
    first_run = state is None
    if first_run:
        state = {'seen': {}, 'events': []}
    seen = state.get('seen')
    if not isinstance(seen, dict):
        seen = {}
    events = state.get('events')
    if not isinstance(events, list):
        events = []
    events = [e for e in events if isinstance(e, dict) and 'eid' in e]
    # prune seen entries whose position vanished long ago (> TTL)
    live_pids = {r['pid'] for r in rows}
    seen = {k: v for k, v in seen.items()
            if k in live_pids or (now - int(_f(v, now))) < TOPDOG_STATE_TTL_SEC}
    new_events = []
    if first_run:
        # bootstrap: the whole live book becomes 'seen' — no alert storm
        for r in rows:
            seen[r['pid']] = now
    else:
        for r in rows:
            if r['pid'] in seen:
                continue
            seen[r['pid']] = now
            owners = owners_ms[(r['market'], r['side'])]
            ev = {
                'eid': r['pid'], 'ts': now,
                'wallet': r['owner'],
                'label': (wallets.get(r['owner'], {}).get('label')
                          or r['owner'][:4]),
                'market': r['market'], 'side': r['side'],
                'leverage': r['leverage'], 'margin': r['margin'],
                'executed_at': r['executed_at'],
                'tier': r['owner'] in tier_set,
                'tracked': r['owner'] in wallets,
                'cluster': len(owners),
            }
            new_events.append(ev)
    if new_events:
        events = new_events + events
        events = events[:TOPDOG_EVENT_RETAIN]
    out['events'] = events
    out['new_events'] = len(new_events)

    _atomic_write(OUT, out)
    _atomic_write(STATE_FILE, {'seen': seen, 'events': events})
    print(f"[topdog_api] wallets={len(wallets)} tier={len(tier_set)} "
          f"positions={len(rows)} clusters={len(clusters)} "
          f"new_events={len(new_events)} errors={len(out['errors'])} -> {OUT}")
    for e in out['errors']:
        print(f"[topdog_api] ! {e}")


if __name__ == '__main__':
    main()
