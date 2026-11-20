#!/usr/bin/env python3
"""Rider fade-guard threshold walk + enforce-read (disposition amplify-rider-fade-threshold-walk).

Replays BTC_PUMP_RIDER_FADE_MIN_DRIFT_PCT thresholds over pc+ LONG fires (30d),
then runs the enforce-read limb from the hermes_constants comment:
  >=15 shadow would-block lines AND blocked live-cohort net negative AND
  0 would-blocked live winners AND review-queue sign-off.

Units: fire cohort outcomes are price-move % (fwd30/fwd60); live limb is
pnl_usdt vs pnl_usdt only (never stored leveraged pnl_pct — #193).
ponytail: replay reads closed candles <= fire ts (live guard reads the partial
candle) — drift differs by at most the current 1m bar; acceptance noted.
"""
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, '/root/.hermes/scripts')
from paths import SIGNALS_DB, CANDLES_DB  # noqa: E402
from hermes_constants import BTC_PUMP_RIDER_FADE_MIN_DRIFT_PCT as FADE_THR  # noqa: E402

import psycopg2  # noqa: E402

THR_LIST = (0.05, 0.10, 0.15, 0.20)
BLOCK_COUNT_MIN, BLOCK_COUNT_MAX = 10, 40
HORIZONS = (30, 60)  # minutes
LOG = '/var/www/hermes/logs/signals.log'


def drift_from_rows(rows):
    """rows oldest-first (ts,o,h,l,c,v) — replica of btc_pump_rider._fade_pre15_drift."""
    if len(rows) < 16 or rows[-16][4] <= 0:
        return None
    return (rows[-1][4] / rows[-16][4] - 1) * 100


def pre15_at(token, epoch):
    conn = sqlite3.connect(CANDLES_DB, timeout=5)
    try:
        cur = conn.cursor()
        cur.execute("SELECT ts, open, high, low, close, volume FROM candles_1m "
                    "WHERE token=? AND ts<=? ORDER BY ts DESC LIMIT 20",
                    (token.upper(), int(epoch)))
        rows = cur.fetchall()
        rows.reverse()
        return drift_from_rows(rows)
    finally:
        conn.close()


def fwd_pct(token, start_epoch, fire_price, minutes):
    """Price move % from fire_price to nearest close at >= start+minutes."""
    target = int(start_epoch) + minutes * 60
    conn = sqlite3.connect(CANDLES_DB, timeout=5)
    try:
        cur = conn.cursor()
        cur.execute("SELECT ts, close FROM candles_1m WHERE token=? AND ts>=? "
                    "ORDER BY ts ASC LIMIT 1", (token.upper(), target))
        row = cur.fetchone()
        if not row or not fire_price or row[0] - target > 120:
            return None  # gap bound: collector outage must not silently widen horizon
        return (row[1] / fire_price - 1) * 100
    finally:
        conn.close()


def load_fires(days=30):
    conn = sqlite3.connect(SIGNALS_DB, timeout=5)
    try:
        cur = conn.cursor()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("""SELECT id, token, created_at, price FROM signals
                       WHERE source LIKE '%btc-pump-rider%' AND direction='LONG'
                         AND created_at >= ? ORDER BY created_at""", (cutoff,))
        return cur.fetchall()
    finally:
        conn.close()


def load_live_trades(days=30):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    try:
        cur = conn.cursor()
        cur.execute(f"""SELECT id, token, open_time, entry_price, pnl_usdt, status
                       FROM trades WHERE signal LIKE '%btc-pump-rider%'
                         AND direction='LONG' AND status='closed'
                         AND open_time > NOW() - INTERVAL '{int(days)} days'""")
        return cur.fetchall()
    finally:
        conn.close()


def fire_cohort(fires):
    """Attach drift + fwd30/fwd60 to each fire; drop uncovered."""
    out, missed = [], 0
    for fid, token, created_at, price in fires:
        try:
            epoch = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S').replace(
                tzinfo=timezone.utc).timestamp()
        except (TypeError, ValueError):
            missed += 1
            continue
        d = pre15_at(token, epoch)
        if d is None:
            missed += 1
            continue
        rec = {'id': fid, 'token': token, 'epoch': epoch, 'drift': d,
               'fwds': {m: fwd_pct(token, epoch, price, m) for m in HORIZONS}}
        out.append(rec)
    return out, missed


def walk_thresholds(cohort, horizon=60):
    """Per-threshold block stats + split-halves on blocked net (price-move %)."""
    rows = [r for r in cohort if r['fwds'].get(horizon) is not None]
    if not rows:
        return {}
    mid = sorted(r['epoch'] for r in rows)[len(rows) // 2]
    wins = sum(1 for r in rows if r['fwds'][horizon] > 0)
    res = {}
    for thr in THR_LIST:
        blocked = [r for r in rows if r['drift'] < thr]
        kept = [r for r in rows if r['drift'] >= thr]
        n_win_blocked = sum(1 for r in blocked if r['fwds'][horizon] > 0)
        older = [r for r in blocked if r['epoch'] < mid]
        newer = [r for r in blocked if r['epoch'] >= mid]
        net = lambda rs: sum(r['fwds'][horizon] for r in rs) / len(rs) if rs else None
        res[thr] = {
            'n': len(rows), 'n_blocked': len(blocked),
            'kept_wr': round(100.0 * sum(1 for r in kept if r['fwds'][horizon] > 0) / len(kept), 1) if kept else None,
            'blocked_wr': round(100.0 * sum(1 for r in blocked if r['fwds'][horizon] > 0) / len(blocked), 1) if blocked else None,
            'kept_net': round(net(kept), 4) if kept else None,
            'blocked_net': round(net(blocked), 4) if blocked else None,
            'fk_pct': round(100.0 * n_win_blocked / wins, 1) if wins else None,
            'older_blocked_net': round(net(older), 4) if older else None,
            'newer_blocked_net': round(net(newer), 4) if newer else None,
            'halves_same_sign_negative': bool(older and newer and net(older) < 0 and net(newer) < 0),
            'count_in_range': BLOCK_COUNT_MIN <= len(blocked) <= BLOCK_COUNT_MAX,
        }
    return res


def enforce_read(live_trades, thr=FADE_THR):
    """Enforce-read limb: shadow line bar + live blocked-cohort net + fk-live."""
    try:
        n_lines = int(subprocess.check_output(
            ['grep', '-ac', 'RIDER-FADE-SHADOW', LOG], text=True).strip())
    except subprocess.CalledProcessError as e:
        n_lines = int((e.output or '0').strip() or 0)  # grep exits 1 on 0 matches
    except Exception:
        n_lines = -1
    live = []
    for tid, token, open_time, price, pnl, status in live_trades:
        epoch = open_time.replace(tzinfo=timezone.utc).timestamp()
        d = pre15_at(token, epoch)
        if d is None:
            continue
        live.append({'id': tid, 'drift': d, 'pnl': float(pnl or 0)})
    blocked = [t for t in live if t['drift'] < thr]
    blocked_net = round(sum(t['pnl'] for t in blocked), 4)
    blocked_winners = [t for t in blocked if t['pnl'] > 0]
    return {
        'shadow_lines': n_lines,
        'line_bar_15': n_lines >= 15,
        'live_n': len(live), 'live_blocked_n': len(blocked),
        'live_blocked_net_pnl_usdt': blocked_net,
        'blocked_net_negative': blocked_net < 0,
        'live_blocked_winner_ids': [t['id'] for t in blocked_winners],
        'fk_live_zero': len(blocked_winners) == 0,
        'units': 'pnl_usdt',
    }


def selfcheck() -> int:
    # 1. drift math (mirror module selfcheck)
    up = [(0, 0, 0, 0, 100.0, 0)] * 15 + [(0, 0, 0, 0, 101.5, 0)]
    dn = [(0, 0, 0, 0, 100.0, 0)] * 15 + [(0, 0, 0, 0, 99.5, 0)]
    assert drift_from_rows(up) is not None and drift_from_rows(up) > 0.10
    assert drift_from_rows(dn) < 0.10
    assert drift_from_rows([(0, 0, 0, 0, 100.0, 0)] * 3) is None
    assert abs(drift_from_rows(up) - 1.5) < 1e-9, drift_from_rows(up)
    # module replica agreement (NOTE: importing btc_pump_rider runs its
    # os.makedirs(logs-dir) module-level side effect — existing dir, no-op)
    try:
        sys.path.insert(0, '/root/.hermes/scripts/signals')
        from btc_pump_rider import _fade_pre15_drift as mod_drift
        assert abs(mod_drift(up) - drift_from_rows(up)) < 1e-9
        assert abs(mod_drift(dn) - drift_from_rows(dn)) < 1e-9
        print('module replica agreement: PASS')
    except ImportError:
        print('module replica agreement: SKIP (import failed)')
    # 2. threshold walk on fixture: 4 fires, known drifts/fwd
    base = 1_700_000_000
    fix = [
        {'id': 1, 'token': 'A', 'epoch': base, 'drift': 0.30, 'fwds': {60: +1.0}},
        {'id': 2, 'token': 'B', 'epoch': base + 100, 'drift': -0.20, 'fwds': {60: -1.0}},
        {'id': 3, 'token': 'C', 'epoch': base + 200, 'drift': 0.08, 'fwds': {60: +2.0}},
        {'id': 4, 'token': 'D', 'epoch': base + 300, 'drift': 0.02, 'fwds': {60: -2.0}},
    ]
    w = walk_thresholds(fix, horizon=60)
    assert w[0.10]['n_blocked'] == 3, w[0.10]          # drift 0.08/0.02/-0.20 < 0.10
    assert w[0.10]['blocked_wr'] == 33.3, w[0.10]      # blocked=B,C,D; only C wins => 33.3
    assert w[0.05]['n_blocked'] == 2, w[0.05]           # 0.02, -0.20
    assert w[0.20]['n_blocked'] == 3, w[0.20]           # 0.08, 0.02, -0.20 (0.30 kept)
    assert w[0.10]['fk_pct'] == 50.0, w[0.10]           # winners A,C; blocked winner C => 50
    assert abs(w[0.10]['blocked_net'] - (-1.0 + 2.0 - 2.0) / 3) < 1e-3, w[0.10]  # 4dp rounding
    assert w[0.10]['halves_same_sign_negative'] is False  # older B=-1.0, newer C+D=0.0
    # 2b. empty blocked set + blocked confined to one half must NOT crash (bug_hunter HIGH)
    high = [dict(f, drift=0.30) for f in fix]
    wh = walk_thresholds(high, horizon=60)
    assert wh[0.20]['n_blocked'] == 0 and wh[0.20]['older_blocked_net'] is None \
        and wh[0.20]['newer_blocked_net'] is None, wh[0.20]
    one = [dict(f) for f in fix]
    one[0]['drift'], one[1]['drift'], one[2]['drift'] = 0.30, 0.30, 0.30  # only D(0.02) blocks
    wo = walk_thresholds(one, horizon=60)
    assert wo[0.05]['n_blocked'] == 1 and wo[0.05]['older_blocked_net'] is None, wo[0.05]
    # 3. enforce limb: run the REAL function with pre15_at patched (never touches pnl_pct)
    import datetime as _dt
    fake_rows = [(11, 'X', _dt.datetime(2026, 11, 1, 0, 0, 0), 1.0, +0.10, 'closed'),
                 (12, 'Y', _dt.datetime(2026, 11, 1, 1, 0, 0), 1.0, -0.20, 'closed'),
                 (13, 'Z', _dt.datetime(2026, 11, 1, 2, 0, 0), 1.0, -0.05, 'closed')]
    drifts = {'X': 0.30, 'Y': -0.10, 'Z': 0.05}
    global pre15_at
    real_pre15 = pre15_at
    pre15_at = lambda token, epoch: drifts.get(token)  # noqa: E731
    try:
        er = enforce_read(fake_rows)
    finally:
        pre15_at = real_pre15
    assert er['live_n'] == 3 and er['live_blocked_n'] == 2, er
    assert er['live_blocked_net_pnl_usdt'] == -0.25, er
    assert er['fk_live_zero'] is True and er['live_blocked_winner_ids'] == [], er
    assert er['units'] == 'pnl_usdt', er
    # break-test: a would-blocked live winner must flip fk to False
    fake_rows2 = fake_rows + [(14, 'W', _dt.datetime(2026, 11, 1, 3, 0, 0), 1.0, +0.15, 'closed')]
    drifts['W'] = 0.02
    pre15_at = lambda token, epoch: drifts.get(token)  # noqa: E731
    try:
        er2 = enforce_read(fake_rows2)
    finally:
        pre15_at = real_pre15
    assert er2['fk_live_zero'] is False and er2['live_blocked_winner_ids'] == [14], er2
    print('rider_fade_threshold_walk selfcheck PASS')
    return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--selfcheck':
        return selfcheck()
    fires = load_fires(30)
    cohort, missed = fire_cohort(fires)
    print(f'fires 30d={len(fires)} walkable={len(cohort)} uncovered={missed}')
    for h in HORIZONS:
        w = walk_thresholds(cohort, horizon=h)
        print(f'--- threshold walk (fwd{h}%, price-move units) ---')
        for thr, s in w.items():
            mark = 'KEEP' if thr == FADE_THR else ''
            print(f'  thr<{thr}: n={s["n"]} blocked={s["n_blocked"]} '
                  f'kept_wr={s["kept_wr"]}% net={s["kept_net"]} | blocked_wr={s["blocked_wr"]}% '
                  f'net={s["blocked_net"]} fk={s["fk_pct"]}% | halves({s["older_blocked_net"]},'
                  f'{s["newer_blocked_net"]}) same_neg={s["halves_same_sign_negative"]} '
                  f'count_ok={s["count_in_range"]} {mark}')
    w60 = walk_thresholds(cohort, horizon=60)
    better = [thr for thr, s in w60.items()
              if thr != FADE_THR and s['halves_same_sign_negative'] and s['count_in_range']
              and s['blocked_net'] is not None]
    beats = [thr for thr in better
             if w60[FADE_THR]['blocked_net'] is not None
             and w60[thr]['blocked_net'] < w60[FADE_THR]['blocked_net']
             and w60[thr]['kept_net'] is not None
             and (w60[FADE_THR]['kept_net'] is None or w60[thr]['kept_net'] >= w60[FADE_THR]['kept_net'])]
    print(f'threshold verdict: keep {FADE_THR} (adjacent beating in both halves same-sign: {beats or "none"})')
    er = enforce_read(load_live_trades(30))
    print('--- enforce-read limb ---')
    for k, v in er.items():
        print(f'  {k}: {v}')
    signoff = er['line_bar_15'] and er['blocked_net_negative'] and er['fk_live_zero']
    print(f'bar triplet (lines>=15, blocked net<0, fk_live=0): {"PASS" if signoff else "FAIL"} '
          f'+ review-queue sign-off still required => default NO FLIP until signed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
