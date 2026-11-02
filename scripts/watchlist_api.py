#!/usr/bin/env python3
"""
watchlist_api.py — Watchlist dashboard data (T 2026-11-02).

Writes /var/www/hermes/data/watchlist.json — polled every 15s by
web/watchlist.html, regenerated every 60s by hermes-watchlist.timer.

The user's own wallet list (data/watchlist.json, edited from the page via
watchlist_server.py on 127.0.0.1:3463) gets the SAME engine as the topdog
tracker: per-coin net-bias boxes, clusters, new-position events, $50 margin
floor. Reuses topdog_api helpers (parse/atomic-write/tier) so the two
dashboards cannot drift apart.

DATA COVERAGE (honest limits — jup exposes no per-wallet endpoint):
  stats    — only when the address sits in a yolo top-100 window (leaderboard
             file, refreshed 10min). Otherwise the table shows – and the
             coverage badge says so.
  live     — only when the address is in jup's watch feed (positions feed).
  activity — global trades feed (2 pages x100) gives last-seen trading per
             watched owner even when it has no live position.

State: data/watchlist_state.json (first-run bootstrap = no alert storm;
absence-TTL semantics: live ids refresh their seen-ts every cycle).
"""
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, WWW_DATA
from hermes_constants import (
    TOPDOG_TIER_PCT, TOPDOG_CLUSTER_MIN, TOPDOG_EVENT_RETAIN,
    TOPDOG_STATE_TTL_SEC, TOPDOG_MIN_MARGIN_USD,
    WATCHLIST_MAX_WALLETS, WATCHLIST_TRADES_LIMIT,
)
# helpers + tier engine shared with the topdog tracker (import-safe: module
# main is guarded) — single source of truth for parsing/atomic writes
from topdog_api import (
    _f, _usd, _pid, _load_json, _atomic_write, _sync_page,
    POSITIONS_URL, compute_tier,
)

TRADES_URL = "https://yolo-api.jup.ag/trades"
WATCHLIST_FILE = os.path.join(HERMES_DATA, 'watchlist.json')
STATE_FILE = os.path.join(HERMES_DATA, 'watchlist_state.json')
OUT = os.path.join(WWW_DATA, 'watchlist.json')
PAGE_SRC = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'web', 'watchlist.html')
PAGE_DST = os.path.join(os.path.dirname(WWW_DATA), 'watchlist.html')


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _fetch_positions():
    return _get(POSITIONS_URL).get('positions') or []


def _fetch_recent_trades(limit):
    """One wide page of global recent trades (limit≈30min of activity).

    Cursor paging was probed 2026-11-02: the feed only accepts `after`
    (forward tail, n=0 when asked for older) — backward paging 400s — so a
    single wide page is the only depth available. Returns [] on any failure:
    activity is a bonus column, never a hard dependency.
    """
    try:
        d = _get(f"{TRADES_URL}?limit={int(limit)}", timeout=15)
        return d.get('trades') or []
    except Exception as e:
        print(f"[watchlist_api] trades fetch failed: "
              f"{type(e).__name__}: {e}", file=sys.stderr)
        return []


def load_watchlist():
    """{addr: {label, added}} with shape guards (bug_hunter rule: a corrupt
    file degrades to an empty list + logged error, never a crash)."""
    raw = _load_json(WATCHLIST_FILE, None)
    errors = []
    if raw is None:
        if os.path.exists(WATCHLIST_FILE):
            errors.append('watchlist file unreadable — treating as empty')
        raw = {}
    wallets = raw.get('wallets') if isinstance(raw, dict) else None
    if not isinstance(wallets, dict):
        if wallets is not None:
            errors.append('watchlist.wallets not a dict — treating as empty')
        wallets = {}
    clean = {}
    for a, v in wallets.items():
        if not isinstance(a, str) or not a:
            continue
        v = v if isinstance(v, dict) else {}
        clean[a] = {'label': str(v.get('label') or '')[:24],
                    'added': int(_f(v.get('added')))}
    if len(clean) > WATCHLIST_MAX_WALLETS:
        # keep oldest additions (stable across runs), log the trim
        keep = sorted(clean, key=lambda a: clean[a]['added'])[:WATCHLIST_MAX_WALLETS]
        errors.append(f'watchlist over cap — trimmed to {WATCHLIST_MAX_WALLETS}')
        clean = {a: clean[a] for a in keep}
    return clean, errors


def _label_for(addr, wl_entry, lb_entry, fallback_prefix=4):
    return (wl_entry.get('label')
            or (lb_entry or {}).get('label')
            or addr[:fallback_prefix])


def main():
    now = int(time.time())
    out = {'updated': now, 'api_ok': False, 'errors': [],
           'watchlist_n': 0, 'tiers': [], 'coins': {}, 'clusters': [],
           'events': [], 'dust_filtered': 0,
           'min_margin_usd': TOPDOG_MIN_MARGIN_USD,
           'tier_pct': TOPDOG_TIER_PCT}

    wallets, wl_errors = load_watchlist()
    out['errors'].extend(wl_errors)
    out['watchlist_n'] = len(wallets)
    if not wallets:
        # empty list is a valid state — still write so the page renders its
        # empty-state instead of going STALE
        out['api_ok'] = True
        _atomic_write(OUT, out)
        _sync_page(PAGE_SRC, PAGE_DST, 'watchlist_api')
        print("[watchlist_api] empty watchlist -> "
              f"{OUT}")
        return

    lb = _load_json(os.path.join(HERMES_DATA, 'jup_yolo_leaderboard.json'), {})
    lb_wallets = lb.get('wallets') if isinstance(lb, dict) else None
    if not isinstance(lb_wallets, dict):
        lb_wallets = {}
        out['errors'].append('leaderboard file missing/empty')

    # ── stats + tier among watchlist members that have leaderboard data ──
    stats_subset = {a: lb_wallets[a] for a in wallets if a in lb_wallets}
    tier_set, ranked = compute_tier(stats_subset) if stats_subset else (set(), [])
    score_by = {addr: round(score, 3) for score, addr, _ in ranked}

    # ── live positions (jup watch feed), $50 floor, watchlist scope ──
    positions, rows = [], []
    try:
        positions = _fetch_positions()
        out['api_ok'] = True
    except Exception as e:
        out['errors'].append(f'positions fetch: {type(e).__name__}: {e}')
    for p in positions:
        try:
            owner = p.get('owner', '')
            market = p.get('market', '')
            side = p.get('side', '')
            if not (isinstance(owner, str) and isinstance(market, str)
                    and side in ('long', 'short') and owner in wallets
                    and market):
                continue
            executed_at = int(_f(p.get('executedAt')))
            market_u = market.upper()
            pid = _pid(p) or f'noid:{owner}:{market_u}:{side}:{executed_at}'
            margin = _usd(p.get('margin'))
            if margin is not None and margin < TOPDOG_MIN_MARGIN_USD:
                out['dust_filtered'] += 1
                continue
            rows.append({'owner': owner, 'market': market_u, 'side': side,
                         'pid': pid, 'leverage': int(_f(p.get('leverage'))),
                         'margin': margin, 'notional': _usd(p.get('notional')),
                         'executed_at': executed_at})
        except Exception as re_:
            out['errors'].append(f'row parse: {type(re_).__name__}: {re_}')

    # ── last-activity fallback from the global trades feed ──
    last_trade = {}
    try:
        for t in _fetch_recent_trades(WATCHLIST_TRADES_LIMIT):
            o = t.get('owner')
            if o in wallets:
                ts = int(_f(t.get('executedAt')))
                if o not in last_trade or ts > last_trade[o]['ts']:
                    last_trade[o] = {
                        'ts': ts, 'market': str(t.get('market') or '').upper(),
                        'side': str(t.get('side') or ''),
                        'kind': str(t.get('kind') or ''),
                        'margin': _usd(t.get('margin')),
                    }
    except Exception as e:
        out['errors'].append(f'trades scan: {type(e).__name__}: {e}')

    # ── clusters + per-coin boxes (watchlist universe) ──
    owners_ms = defaultdict(set)
    positions_by_owner = defaultdict(list)
    for r in rows:
        owners_ms[(r['market'], r['side'])].add(r['owner'])
        positions_by_owner[r['owner']].append(r)

    clusters = []
    for (market, side), owners in sorted(owners_ms.items()):
        if len(owners) >= TOPDOG_CLUSTER_MIN:
            star = sum(1 for o in owners if o in tier_set)
            mem = [r for r in rows
                   if r['market'] == market and r['side'] == side]
            clusters.append({
                'market': market, 'side': side, 'wallets': len(owners),
                'tier_wallets': star, 'tracked': len(owners),
                'labels': sorted(_label_for(o, wallets.get(o, {}),
                                            lb_wallets.get(o)) for o in owners),
                'notional': round(sum(r['notional'] or 0 for r in mem), 2),
            })
    clusters.sort(key=lambda c: (-c['tier_wallets'], -c['wallets']))
    out['clusters'] = clusters

    coins = {}
    for (market, side), owners in owners_ms.items():
        c = coins.setdefault(market, {
            'tier_long': 0, 'tier_short': 0, 'all_long': 0, 'all_short': 0,
            'cluster_long': False, 'cluster_short': False, 'members': []})
        star = sum(1 for o in owners if o in tier_set)
        if side == 'long':
            c['all_long'], c['tier_long'] = len(owners), star
            c['cluster_long'] = len(owners) >= TOPDOG_CLUSTER_MIN
        else:
            c['all_short'], c['tier_short'] = len(owners), star
            c['cluster_short'] = len(owners) >= TOPDOG_CLUSTER_MIN
    for (market, side), owners in owners_ms.items():
        for o in owners:
            mem_rows = [r for r in rows if r['owner'] == o
                        and r['market'] == market and r['side'] == side]
            coins[market]['members'].append({
                'wallet': o,
                'label': _label_for(o, wallets.get(o), lb_wallets.get(o)),
                'side': side, 'tier': o in tier_set, 'tracked': True,
                'positions': len(mem_rows),
                'leverage': max((r['leverage'] for r in mem_rows), default=0),
                'margin': round(sum(r['margin'] or 0 for r in mem_rows), 2),
                'score': score_by.get(o),
            })
    out['coins'] = coins

    # ── trader table: every watchlist wallet, scored ones get the composite ──
    traders = []
    for score, addr, w in ranked:
        held = positions_by_owner.get(addr, [])
        cov = ['stats']
        if held:
            cov.append('live')
        if addr in last_trade:
            cov.append('activity')
        traders.append({
            'wallet': addr,
            'label': _label_for(addr, wallets.get(addr, {}), w),
            'rank': w.get('rank'), 'score': score_by.get(addr),
            'tier': addr in tier_set,
            'pnl': w.get('pnl'), 'pnl_7d': w.get('pnl_7d'),
            'pnl_24h': w.get('pnl_24h'), 'wr': w.get('wr'),
            'wr_7d': w.get('wr_7d'), 'trades': w.get('trades'),
            'volume': w.get('volume'),
            'last_trade': last_trade.get(addr),
            'positions': [{'market': r['market'], 'side': r['side'],
                           'leverage': r['leverage'], 'margin': r['margin']}
                          for r in held],
            'coverage': cov,
        })
    scored = {t['wallet'] for t in traders}
    for addr in wallets:                      # no-stats members, listed last
        if addr in scored:
            continue
        cov = []
        if positions_by_owner.get(addr):
            cov.append('live')
        if addr in last_trade:
            cov.append('activity')
        traders.append({
            'wallet': addr,
            'label': _label_for(addr, wallets.get(addr, {}),
                                lb_wallets.get(addr)),
            'rank': None, 'score': None, 'tier': False,
            'pnl': None, 'pnl_7d': None, 'pnl_24h': None,
            'wr': None, 'wr_7d': None, 'trades': None, 'volume': None,
            'last_trade': last_trade.get(addr),
            'positions': [{'market': r['market'], 'side': r['side'],
                           'leverage': r['leverage'], 'margin': r['margin']}
                          for r in positions_by_owner.get(addr, [])],
            'coverage': cov or ['none'],
        })
    out['tiers'] = traders
    out['scored_n'] = len(scored)
    out['live_n'] = len(positions_by_owner)

    # ── events: new watchlist position ids since the last run (same
    # semantics as the audited topdog tracker: first-run bootstrap = no
    # alert storm; prune = absence-TTL; live ids refresh their ts each
    # cycle so a feed blip can never cause a false re-alert) ──
    state = _load_json(STATE_FILE, None)
    first_run = state is None
    if first_run:
        state = {'seen': {}, 'events': []}
    seen = state.get('seen') if isinstance(state.get('seen'), dict) else {}
    events = state.get('events') if isinstance(state.get('events'), list) else []
    if not isinstance(state.get('seen'), dict) or not isinstance(state.get('events'), list):
        out['errors'].append('state file shape bad — reseeding (history loss only)')
    events = [e for e in events if isinstance(e, dict) and 'eid' in e]
    live_pids = {r['pid'] for r in rows}
    seen = {k: v for k, v in seen.items()
            if k in live_pids or (now - int(_f(v, now))) < TOPDOG_STATE_TTL_SEC}
    new_events = []
    if first_run:
        for r in rows:
            seen[r['pid']] = now
    else:
        for r in rows:
            is_new = r['pid'] not in seen
            seen[r['pid']] = now      # refresh: TTL measures ABSENCE
            if not is_new:
                continue
            owners = owners_ms[(r['market'], r['side'])]
            new_events.append({
                'eid': r['pid'], 'ts': now, 'wallet': r['owner'],
                'label': _label_for(r['owner'], wallets.get(r['owner'], {}),
                                    lb_wallets.get(r['owner'])),
                'market': r['market'], 'side': r['side'],
                'leverage': r['leverage'], 'margin': r['margin'],
                'executed_at': r['executed_at'],
                'tier': r['owner'] in tier_set, 'tracked': True,
                'cluster': len(owners),
            })
    if new_events:
        events = new_events + events
        events = events[:TOPDOG_EVENT_RETAIN]
    # retro-clean sub-$50 backlog (parse filter only covers new events)
    events = [e for e in events
              if e.get('margin') is None
              or float(e.get('margin')) >= TOPDOG_MIN_MARGIN_USD]
    out['events'] = events
    out['new_events'] = len(new_events)

    _atomic_write(OUT, out)
    _atomic_write(STATE_FILE, {'seen': seen, 'events': events})
    _sync_page(PAGE_SRC, PAGE_DST, 'watchlist_api')
    print(f"[watchlist_api] wallets={len(wallets)} scored={len(scored)} "
          f"positions={len(rows)} clusters={len(clusters)} "
          f"new_events={len(new_events)} last_trade={len(last_trade)} "
          f"errors={len(out['errors'])} -> {OUT}")
    for e in out['errors']:
        print(f"[watchlist_api] ! {e}", file=sys.stderr)


if __name__ == '__main__':
    main()
