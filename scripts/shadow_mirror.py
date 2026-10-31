#!/usr/bin/env python3
"""
shadow_mirror.py — SHADOW ENGINE, OWN LEADERBOARD, TRUST TIERS.

T directive 2026-10-31: "sort of shadow mode the traders, we compile our own
leaderboard, and the top top traders we mirror exactly — we have to find
traders we trust."

What it does (daily systemd timer + manual):
  1. Replays EVERY tracked wallet's fills from hl_copy.db through OUR copy
     rules over SHADOW_WINDOW_DAYS — their claimed stats are never trusted,
     only what WE would have earned:
       • excluded markets (synthetic @/xyz: coins, non-HL names)
       • their exit = our exit (pure mirror measurement of THEIR edge)
       • scaled to OUR notional (DEFAULT_TRADE_SIZE_USDT)
       • entry latency penalty (SHADOW_LATENCY_SEC): measured mean signed
         slippage from candles_1m at fill_time+latency, applied per trade
  2. Compiles OUR leaderboard (sorted by shadow PnL after latency).
  3. Assigns trust tiers with hysteresis:
       T1 EXACT MIRROR  — n>=20, wr>=0.65, pnl_after_latency>=5, fresh
       T2 STANDARD COPY — n>=10 (evidence exists, below T1 bar)
       T3 SHADOW ONLY   — insufficient evidence (no real signals)
     Demotion needs T1_DEMOTE_BAD_DAYS consecutive failing recalcs.
  4. Writes HERMES_DATA/copy_trust.json (engine input, trust_tiers.py) and
     WWW_DATA/copy_trader_trust.json (dashboard).

Fail-safe: any per-wallet error skips that wallet (never crashes the run);
tier map semantics documented in trust_tiers.py (missing/stale → all T2).

Run: python3 shadow_mirror.py            (full run + report)
     python3 shadow_mirror.py --quiet    (timer)
"""

import json
import os
import sys
import time
from collections import defaultdict

from paths import HERMES_DATA, CANDLES_DB

try:
    from paths import WWW_DATA
except ImportError:
    WWW_DATA = '/var/www/hermes/data'

from hermes_constants import (
    SHADOW_WINDOW_DAYS,
    SHADOW_LATENCY_SEC,
    SHADOW_ENTRY_MAX_FILLS,
    T1_MIN_SHADOW_N,
    T1_MIN_SHADOW_WR,
    T1_MIN_SHADOW_PNL_USD,
    T1_DEMOTE_BAD_DAYS,
    T1_MAX_STALE_DAYS,
    DEFAULT_TRADE_SIZE_USDT,
)

TRUST_FILE = os.path.join(HERMES_DATA, 'copy_trust.json')
TRUST_DASH_FILE = os.path.join(WWW_DATA, 'copy_trader_trust.json')
OUR_NOTIONAL = float(DEFAULT_TRADE_SIZE_USDT)


def _bad_coin(coin: str) -> bool:
    """Synthetic/non-HL instruments we could never trade."""
    if not coin:
        return True
    return coin.startswith('@') or coin.startswith('xyz:') or ':' in coin


def _mean_signed_slip_pct(wallets, window_start, conn_fills):
    """Entry-latency slip: for sampled OPEN fills of candidate wallets, compare
    their fill px to the candles_1m close at fill_time+SHADOW_LATENCY_SEC.
    Returns {wallet: mean_signed_pct} (LONG entries: positive = we'd pay more).

    Bounded: at most SHADOW_ENTRY_MAX_FILLS lookups per wallet.
    """
    import sqlite3
    slips = {}
    try:
        cand = tuple(w for w in wallets)
        if not cand:
            return slips
        qmarks = ','.join('?' * len(cand))
        rows = conn_fills.execute(f"""
            SELECT wallet, coin, side, px, time FROM trader_fills
            WHERE is_open = 1 AND time >= ? AND wallet IN ({qmarks})
            ORDER BY time DESC
        """, (window_start, *cand)).fetchall()
    except Exception:
        return slips
    per_wallet = defaultdict(list)
    for w, coin, side, px, t_ms in rows:
        if len(per_wallet[w]) >= SHADOW_ENTRY_MAX_FILLS:
            continue
        if _bad_coin(coin) or not px or not t_ms:
            continue
        per_wallet[w].append((coin, side, float(px), int(t_ms)))
    if not per_wallet:
        return slips
    try:
        candles = sqlite3.connect(CANDLES_DB, timeout=5)
    except Exception:
        return slips
    try:
        for w, entries in per_wallet.items():
            vals = []
            for coin, side, their_px, t_ms in entries[:SHADOW_ENTRY_MAX_FILLS]:
                try:
                    tgt = (t_ms // 1000) + SHADOW_LATENCY_SEC
                    row = candles.execute(
                        "SELECT close FROM candles_1m WHERE token = ? AND ts >= ? "
                        "ORDER BY ts LIMIT 1", (coin.upper(), tgt)).fetchone()
                    if not row or not row[0]:
                        continue
                    slip_pct = (float(row[0]) - their_px) / their_px * 100.0
                    # normalize to "worse for us" = positive.
                    # FIX (bug_hunter): 'B' = LONG (hl_copy_signal: direction =
                    # 'LONG' if side == 'B'). Raw is already worse-positive for
                    # LONG (pay more when price rose by our +60s). The old flip
                    # INVERTED longs and left shorts raw → sign cancellation on
                    # mixed-side wallets (measured 19x under-penalty).
                    if side != 'B':  # SHORT entry: selling later on a dip = worse
                        slip_pct = -slip_pct
                    vals.append(slip_pct)
                except Exception:
                    continue
            if vals:
                slips[w] = sum(vals) / len(vals)
    finally:
        candles.close()
    return slips


def compute_shadow() -> dict:
    import sqlite3
    from paths import HERMES_DATA as _HD
    now = int(time.time())
    window_start = (now - SHADOW_WINDOW_DAYS * 86400) * 1000  # fills.time is ms

    conn = sqlite3.connect(os.path.join(_HD, 'hl_copy.db'), timeout=10)
    conn.row_factory = sqlite3.Row
    stats = defaultdict(lambda: {'n': 0, 'wins': 0, 'pnl_our': 0.0,
                                 'pnl_their': 0.0, 'last_fill': 0})
    try:
        rows = conn.execute("""
            SELECT wallet, coin, side, px, sz, closed_pnl, time FROM trader_fills
            WHERE is_open = 0 AND time >= ?
        """, (window_start,)).fetchall()
        _seen_fills = set()
        for r in rows:
            w = r['wallet']
            if not w or _bad_coin(r['coin']):
                continue
            # FIX (validation): source table contains EXACT duplicate rows (same
            # wallet/coin/side/px/sz/time-ms/closed_pnl — verified: PONS closes
            # repeated verbatim), inflating n and double-counting pnl. Dedupe
            # here (source-table duplication flagged separately).
            _fkey = (w, r['coin'], r['side'], r['px'], r['sz'],
                     r['closed_pnl'], r['time'])
            if _fkey in _seen_fills:
                continue
            _seen_fills.add(_fkey)
            pnl = float(r['closed_pnl'] or 0)
            px = float(r['px'] or 0)
            sz = float(r['sz'] or 0)
            s = stats[w]
            s['n'] += 1
            if pnl > 0:
                s['wins'] += 1
            s['pnl_their'] += pnl
            # scale to OUR notional: their pnl is on px*sz notional — LINEAR
            # share (constant-$11 mirror expectation). Prior [0.01..10] clamps
            # asymmetrically reweighted mixed-size wallets and could flip the
            # sign vs their raw pnl.
            if px > 0 and sz > 0:
                s['pnl_our'] += pnl * (OUR_NOTIONAL / (px * sz))
            s['last_fill'] = max(s['last_fill'], int(r['time'] or 0) // 1000)

        # latency slip for wallets with enough evidence
        candidates = [w for w, s in stats.items() if s['n'] >= T1_MIN_SHADOW_N]
        slips = _mean_signed_slip_pct(candidates, window_start, conn)
    finally:
        conn.close()

    per_trade_slip_usd = {w: (abs(v) / 100.0) * OUR_NOTIONAL
                          for w, v in slips.items()}

    wallets = {}
    for w, s in stats.items():
        n, wins = s['n'], s['wins']
        wr = (wins / n) if n else 0.0
        slip = per_trade_slip_usd.get(w, 0.0)
        pnl_lat = s['pnl_our'] - slip * n  # conservative: every trade pays slip
        wallets[w] = {
            'n': n,
            'wr': round(wr, 4),
            'pnl_our_size': round(s['pnl_our'], 2),
            'pnl_their_size': round(s['pnl_their'], 2),
            'mean_slip_pct': round(slips.get(w, 0.0), 4),
            'pnl_after_latency': round(pnl_lat, 2),
            'last_fill': s['last_fill'],
            'tier': 'T3',
        }
    return {'updated': now, 'window_days': SHADOW_WINDOW_DAYS, 'wallets': wallets}


def _assign_tiers(shadow: dict) -> None:
    """Tier assignment with demotion hysteresis (reads previous file)."""
    prev = {}
    try:
        with open(TRUST_FILE) as f:
            prev = json.load(f).get('wallets') or {}
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError, ValueError):
        prev = {}
    now = shadow['updated']
    for w, s in shadow['wallets'].items():
        p = prev.get(w) if isinstance(prev, dict) else None
        prev_tier = (p or {}).get('tier') if isinstance(p, dict) else None
        fresh = (now - s['last_fill']) <= T1_MAX_STALE_DAYS * 86400
        passes_t1 = (s['n'] >= T1_MIN_SHADOW_N
                     and s['wr'] >= T1_MIN_SHADOW_WR
                     and s['pnl_after_latency'] >= T1_MIN_SHADOW_PNL_USD
                     and fresh)
        if passes_t1:
            s['tier'] = 'T1'
            s['bad_days'] = 0
        elif prev_tier == 'T1':
            bad = int((p or {}).get('bad_days') or 0) + 1
            s['bad_days'] = bad
            s['tier'] = 'T1' if bad < T1_DEMOTE_BAD_DAYS else 'T2'
        elif s['n'] >= 10:
            s['tier'] = 'T2'
            s['bad_days'] = 0
        else:
            s['tier'] = 'T3'
            s['bad_days'] = 0

    # bug_hunter LOW: a prev-T1 wallet with ZERO fills in the window vanished
    # from the new file → instant T2, bypassing the 3-day hysteresis (and up
    # to 16 days early vs T1_MAX_STALE_DAYS=14). Carry absent prev entries
    # forward through the same hysteresis rule so demotion stays consistent.
    for w, p in prev.items():
        if w in shadow['wallets'] or not isinstance(p, dict):
            continue
        prev_tier = str(p.get('tier') or 'T2').upper()
        prev_bad = int(p.get('bad_days') or 0)
        carried = dict(p)
        if prev_tier == 'T1':
            carried['bad_days'] = prev_bad + 1
            carried['tier'] = 'T1' if carried['bad_days'] < T1_DEMOTE_BAD_DAYS else 'T2'
        else:
            carried['tier'] = prev_tier if prev_tier in ('T1', 'T2', 'T3') else 'T2'
            carried['bad_days'] = prev_bad
        carried['carried_no_fills'] = True
        shadow['wallets'][w] = carried


def _write_outputs(shadow: dict) -> None:
    payload = {
        'updated': shadow['updated'],
        'window_days': shadow['window_days'],
        'wallets': shadow['wallets'],
        'leaderboard': sorted(
            ({'wallet': w, **s} for w, s in shadow['wallets'].items()),
            key=lambda x: -x['pnl_after_latency'])[:100],
        'thresholds': {
            'T1': {'n': T1_MIN_SHADOW_N, 'wr': T1_MIN_SHADOW_WR,
                   'pnl_after_latency': T1_MIN_SHADOW_PNL_USD,
                   'max_stale_days': T1_MAX_STALE_DAYS},
            'T2_min_n': 10,
            'our_notional': OUR_NOTIONAL,
            'latency_sec': SHADOW_LATENCY_SEC,
        },
    }
    with open(TRUST_FILE, 'w') as f:
        json.dump(payload, f)
    try:
        os.makedirs(WWW_DATA, exist_ok=True)
        with open(TRUST_DASH_FILE, 'w') as f:
            json.dump(payload, f)
    except OSError as e:
        print(f"[shadow] ⚠️ dashboard write failed: {e}")


def main():
    quiet = '--quiet' in sys.argv
    t0 = time.time()
    shadow = compute_shadow()
    _assign_tiers(shadow)
    _write_outputs(shadow)
    tiers = defaultdict(int)
    for s in shadow['wallets'].values():
        tiers[s['tier']] += 1
    if not quiet:
        print(f"[shadow] replayed {len(shadow['wallets'])} wallets "
              f"({shadow['window_days']}d window) in {time.time()-t0:.1f}s")
        print(f"[shadow] tiers: T1={tiers['T1']} T2={tiers['T2']} T3={tiers['T3']}")
        print("[shadow] OUR leaderboard top 15 (by shadow PnL after our latency+size):")
        board = sorted(shadow['wallets'].items(),
                       key=lambda kv: -kv[1]['pnl_after_latency'])[:15]
        print(f"  {'wallet':<44} {'tier':<4} {'n':>5} {'wr':>6} {'pnl@ours':>9} "
              f"{'after_lat':>9} {'their$':>10}")
        for w, s in board:
            print(f"  {w[:42]:<44} {s['tier']:<4} {s['n']:>5} {s['wr']*100:>5.1f}% "
                  f"${s['pnl_our_size']:>8.2f} ${s['pnl_after_latency']:>8.2f} "
                  f"${s['pnl_their_size']:>9.2f}")
        print(f"[shadow] trust file: {TRUST_FILE}")
        print(f"[shadow] dashboard:  {TRUST_DASH_FILE}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
