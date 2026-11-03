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
  activity — ONE wide page of the global trades feed (WATCHLIST_TRADES_LIMIT)
             gives last-seen trading per watched owner even when it has no
             live position (cursor only accepts `after` — probed 2026-11-02).

State: data/watchlist_state.json (first-run bootstrap = no alert storm;
absence-TTL semantics: live ids refresh their seen-ts every cycle).
"""
import fcntl
import json
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
    WATCHLIST_MIN_MARGIN_USD,
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
LB_FILE = os.path.join(HERMES_DATA, 'jup_yolo_leaderboard.json')
LOCK_FILE = os.path.join(HERMES_DATA, 'watchlist_api.lock')
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


def _fetch_recent_trades(limit, errors=None):
    """One wide page of global recent trades (limit≈30min of activity).

    Cursor paging was probed 2026-11-02: the feed only accepts `after`
    (forward tail, n=0 when asked for older) — backward paging 400s — so a
    single wide page is the only depth available. A failure is reported into
    `errors` (the payload must never claim a clean cycle while the activity
    column is silently empty) and returns [].
    """
    try:
        d = _get(f"{TRADES_URL}?limit={int(limit)}", timeout=15)
        return d.get('trades') or []
    except Exception as e:
        print(f"[watchlist_api] trades fetch failed: "
              f"{type(e).__name__}: {e}", file=sys.stderr)
        if errors is not None:
            errors.append(f'trades fetch: {type(e).__name__}: {e}')
        return []


def load_watchlist():
    """{addr: {label, added}} with shape guards (bug_hunter rule: a corrupt
    file degrades to an empty list + logged error, never a crash). Every
    wrong shape must surface in errors[] — a silently-empty list that looks
    like "user cleared their watchlist" hides corruption."""
    exists = os.path.exists(WATCHLIST_FILE)
    raw = _load_json(WATCHLIST_FILE, None)
    errors = []
    wallets = None
    if raw is None:
        # missing file = fresh install (no error); an existing-but-unreadable
        # or JSON-null file IS corruption and must say so
        if exists:
            errors.append('watchlist file unreadable or JSON null — treating as empty')
    elif not isinstance(raw, dict):
        errors.append('watchlist file not a JSON object — treating as empty')
    else:
        wallets = raw.get('wallets')
        if not isinstance(wallets, dict):
            errors.append('watchlist.wallets missing or not a dict — treating as empty')
            wallets = None
    if wallets is None:
        wallets = {}
    bad = sum(1 for v in wallets.values() if not isinstance(v, dict))
    if bad:
        errors.append(f'watchlist: {bad} non-object wallet entries dropped')
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
    # shape-guarded: a non-dict entry (corrupt leaderboard/state) must degrade
    # to the address prefix, never AttributeError-crash the whole cycle
    wl = wl_entry if isinstance(wl_entry, dict) else {}
    lb = lb_entry if isinstance(lb_entry, dict) else {}
    return (wl.get('label') or lb.get('label') or addr[:fallback_prefix])


def main():
    """One serialized run (bug_hunter f82944f8/95e39a32).

    The 60s timer and the write server's inline refresh (95e39a32) can run
    watchlist_api.py CONCURRENTLY: both use the same fixed .tmp paths in
    _atomic_write/_sync_page (interleaved bytes -> corrupt JSON/HTML gets
    published) and do last-writer-wins on the state file (a lost 'seen' entry
    re-alerts that position on the next cycle). Blocking flock: the second
    run simply waits for the first, then sees its writes.
    """
    with open(LOCK_FILE, 'w') as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        _run_locked()


def _run_locked():
    now = int(time.time())
    out = {'updated': now, 'api_ok': False, 'errors': [],
           'watchlist_n': 0, 'tiers': [], 'coins': {}, 'clusters': [],
           'events': [], 'dust_filtered': 0, 'new_events': 0,
           'scored_n': 0, 'live_n': 0,
           'min_margin_usd': WATCHLIST_MIN_MARGIN_USD,
           'min_trades': TOPDOG_MIN_TRADES,
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
              f"{OUT} errors={len(out['errors'])}")
        for e in out['errors']:
            print(f"[watchlist_api] ! {e}", file=sys.stderr)
        return

    lb = _load_json(LB_FILE, None)
    lb_wallets = None
    if lb is None:
        out['errors'].append('leaderboard file missing/empty')
    elif not isinstance(lb, dict):
        out['errors'].append('leaderboard file not a JSON object — no stats this cycle')
    else:
        lb_wallets = lb.get('wallets')
    if not isinstance(lb_wallets, dict):
        if lb is not None and isinstance(lb, dict):
            out['errors'].append('leaderboard.wallets not a dict — no stats this cycle')
        lb_wallets = {}
    else:
        # topdog parity: a non-dict entry used to crash _label_for for
        # label-less watched wallets — drop them with an honest count
        bad_w = sum(1 for v in lb_wallets.values() if not isinstance(v, dict))
        if bad_w:
            out['errors'].append(f'leaderboard: {bad_w} non-object wallet entries dropped')
            lb_wallets = {k: v for k, v in lb_wallets.items()
                          if isinstance(v, dict)}
        if not lb_wallets:
            out['errors'].append('leaderboard file missing/empty')

    # ── stats + tier among watchlist members that have leaderboard data ──
    stats_subset = {a: lb_wallets[a] for a in wallets if a in lb_wallets}
    tier_set, ranked = compute_tier(stats_subset) if stats_subset else (set(), [])
    score_by = {addr: round(score, 3) for score, addr, _ in ranked}
    # "has leaderboard stats" (display truth) is NOT "eligible for the
    # composite" — a solo watchlist (n<2) can't be percentile-ranked, but its
    # pnl/wr/volume must still render instead of a row of dashes
    stats_addrs = set(stats_subset)

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
            if margin is not None and margin < WATCHLIST_MIN_MARGIN_USD:
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
        for t in _fetch_recent_trades(WATCHLIST_TRADES_LIMIT, out['errors']):
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
    for addr in wallets:          # members the composite couldn't rank, last
        if addr in scored:
            continue
        lw = lb_wallets.get(addr)
        has_stats = isinstance(lw, dict)
        cov = ['stats'] if has_stats else []
        if positions_by_owner.get(addr):
            cov.append('live')
        if addr in last_trade:
            cov.append('activity')
        traders.append({
            'wallet': addr,
            'label': _label_for(addr, wallets.get(addr, {}), lw),
            'rank': lw.get('rank') if has_stats else None,
            'score': None, 'tier': False,
            # raw leaderboard stats still render when the composite can't run
            # (n<2 eligible members, or trades < TOPDOG_MIN_TRADES): hiding
            # them made a solo watchlist show a full row of dashes + "0 have
            # leaderboard stats" while the file held the numbers
            'pnl': lw.get('pnl') if has_stats else None,
            'pnl_7d': lw.get('pnl_7d') if has_stats else None,
            'pnl_24h': lw.get('pnl_24h') if has_stats else None,
            'wr': lw.get('wr') if has_stats else None,
            'wr_7d': lw.get('wr_7d') if has_stats else None,
            'trades': lw.get('trades') if has_stats else None,
            'volume': lw.get('volume') if has_stats else None,
            'last_trade': last_trade.get(addr),
            'positions': [{'market': r['market'], 'side': r['side'],
                           'leverage': r['leverage'], 'margin': r['margin']}
                          for r in positions_by_owner.get(addr, [])],
            'coverage': cov or ['none'],
        })
    out['tiers'] = traders
    out['scored_n'] = len(stats_addrs)
    out['live_n'] = len(positions_by_owner)

    # ── events: new watchlist position ids since the last run (same
    # semantics as the audited topdog tracker: first-run bootstrap = no
    # alert storm; prune = absence-TTL; live ids refresh their ts each
    # cycle so a feed blip can never cause a false re-alert) ──
    state = _load_json(STATE_FILE, None)
    first_run = state is None
    top_bad = False
    if state is not None and not isinstance(state, dict):
        # valid JSON but wrong top-level shape (list/str/number): topdog
        # guards this — without the guard state.get() AttributeError-crashed
        # EVERY run, the payload froze and the page went silently stale
        out['errors'].append('state file not a JSON object — reseeding '
                             '(history loss only)')
        state = None
        first_run = True
        top_bad = True
    seen = state.get('seen') if isinstance(state, dict) else None
    events = state.get('events') if isinstance(state, dict) else None
    # a missing file is a healthy first run (no error); an EXISTING state
    # with broken children is corruption and must say so
    if not (first_run or top_bad) and (not isinstance(seen, dict)
                                       or not isinstance(events, list)):
        out['errors'].append('state file shape bad — reseeding (history loss only)')
    # a corrupt/absent `seen` must BOOTSTRAP (seed live ids, emit nothing):
    # reusing {} as-is re-alerted every open position of every wallet at once
    seed_only = first_run or not isinstance(seen, dict)
    seen = seen if isinstance(seen, dict) else {}
    events = events if isinstance(events, list) else []
    events = [e for e in events if isinstance(e, dict) and 'eid' in e]
    live_pids = {r['pid'] for r in rows}
    seen = {k: v for k, v in seen.items()
            if k in live_pids or (now - int(_f(v, now))) < TOPDOG_STATE_TTL_SEC}
    new_events = []
    if seed_only:
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
    # retro-clean sub-$50 backlog (parse filter only covers new events) —
    # fail-open on an unparseable margin (same rule as the row parser: never
    # hide data we couldn't measure; a bare float() here used to ValueError
    # and kill the whole run on one corrupt event)
    events = [e for e in events
              if (mv := _f(e.get('margin'), None)) is None
              or mv >= WATCHLIST_MIN_MARGIN_USD]
    # drop events from wallets no longer on the list (T 2026-11-02: removal
    # must also clean the visible feed — stale rows from removed wallets
    # read as bugs). State keeps them (48h prune governs `seen`).
    events = [e for e in events
              if isinstance(e, dict) and e.get('wallet') in wallets]
    out['events'] = events
    out['new_events'] = len(new_events)

    _atomic_write(OUT, out)
    _atomic_write(STATE_FILE, {'seen': seen, 'events': events})
    _sync_page(PAGE_SRC, PAGE_DST, 'watchlist_api')
    print(f"[watchlist_api] wallets={len(wallets)} stats={len(stats_addrs)} "
          f"scored={len(scored)} positions={len(rows)} clusters={len(clusters)} "
          f"new_events={len(new_events)} last_trade={len(last_trade)} "
          f"errors={len(out['errors'])} -> {OUT}")
    for e in out['errors']:
        print(f"[watchlist_api] ! {e}", file=sys.stderr)


def _fatal_payload(msg):
    """Full-shape error payload so the page renders 'feed DOWN' + the crash
    reason instead of freezing on a stale file that still claims api_ok=True
    (topdog/copy_trader zero-byte lesson — without this a single corrupt
    state file made every 60s run exit 1 with the old payload untouched)."""
    return {
        'updated': int(time.time()), 'api_ok': False, 'errors': [msg],
        'watchlist_n': 0, 'tiers': [], 'coins': {}, 'clusters': [],
        'events': [], 'new_events': 0, 'dust_filtered': 0,
        'scored_n': 0, 'live_n': 0,
        'min_margin_usd': WATCHLIST_MIN_MARGIN_USD,
        'min_trades': TOPDOG_MIN_TRADES, 'tier_pct': TOPDOG_TIER_PCT,
    }


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        msg = f'watchlist_api crash: {type(e).__name__}: {e}'
        print(f'[watchlist_api] !! {msg}', file=sys.stderr)
        try:
            _atomic_write(OUT, _fatal_payload(msg))
        except Exception as we:
            print(f'[watchlist_api] !! fallback write failed: {we}',
                  file=sys.stderr)
        sys.exit(1)
