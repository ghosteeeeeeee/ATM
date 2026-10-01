#!/usr/bin/env python3
"""Independent audit: gate unfreeze analysis.
Joins PG trades with BTC continuum history, buckets by score, computes WR/PnL.
Read-only analysis. Run: python3 audit_gate_unfreeze.py
"""
import sys, os, json, sqlite3
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/scripts')
import psycopg2

BRAIN_DB = {'host': '/var/run/postgresql', 'dbname': 'brain', 'user': 'postgres', 'password': 'postgres'}
CONTINUUM_DB = '/root/.hermes/data/continuum.db'

def load_continuum():
    conn = sqlite3.connect(CONTINUUM_DB, timeout=10)
    rows = conn.execute(
        "SELECT ts, state_score, zscore_tier, market_phase, ema300_position, linreg_direction "
        "FROM continuum_states WHERE token='BTC' AND timeframe='1m' ORDER BY ts"
    ).fetchall()
    conn.close()
    return rows

def continuum_lookup(rows, epoch_ts):
    """Binary search: latest continuum row with ts <= epoch_ts."""
    lo, hi = 0, len(rows) - 1
    ans = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if rows[mid][0] <= epoch_ts:
            ans = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return rows[ans] if ans >= 0 else None

def score_bucket(s):
    if s is None: return 'unknown'
    if s < 5: return 'a: <5'
    if s < 10: return 'b: 5-10'
    if s < 30: return 'c: 10-30'
    if s < 60: return 'd: 30-60'
    if s < 80: return 'e: 60-80'
    return 'f: >=80'

def z_bucket(z):
    return z if z else 'unknown'

def stats(trades, label):
    n = len(trades)
    if n == 0:
        return None
    wins = sum(1 for t in trades if t['pnl'] > 0)
    pnl = sum(t['pnl'] for t in trades)
    pnl_pct = sum(t['pnl_pct'] for t in trades)
    avg = pnl / n
    return {'n': n, 'wr': wins / n * 100, 'pnl': pnl, 'pnl_pct': pnl_pct, 'avg': avg}

def main():
    print("Loading continuum history...")
    cont = load_continuum()
    print(f"  continuum BTC rows: {len(cont)}, span {cont[0][0]} -> {cont[-1][0]}")

    conn = psycopg2.connect(**BRAIN_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT direction, signal, pnl_usdt, pnl_pct, status,
               EXTRACT(EPOCH FROM open_time)::bigint AS open_epoch,
               entry_regime_4h, regime, _signal_metadata
        FROM trades
        WHERE status='closed' AND open_time > now() - interval '90 days'
        ORDER BY open_time
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    print(f"  closed trades (90d): {len(rows)}")

    joined = []
    for direction, signal, pnl, pnl_pct, status, open_epoch, regime_4h, regime, meta in rows:
        if open_epoch is None or pnl is None:
            continue
        c = continuum_lookup(cont, open_epoch)
        btc_score = c[1] if c else None
        btc_z = c[2] if c else None
        btc_phase = c[3] if c else None
        btc_ema = c[4] if c else None
        # metadata fallback/primary
        m_score = m_z = None
        if meta:
            try:
                m = meta if isinstance(meta, dict) else json.loads(meta)
                m_score = m.get('btc_score')
                m_z = m.get('z_score_tier')
            except Exception:
                pass
        joined.append({
            'dir': direction, 'signal': signal, 'pnl': float(pnl), 'pnl_pct': float(pnl_pct or 0),
            'epoch': open_epoch, 'regime_4h': regime_4h, 'regime': regime,
            'score_cont': btc_score, 'z_cont': btc_z, 'phase': btc_phase, 'ema': btc_ema,
            'score_meta': m_score, 'z_meta': m_z,
        })

    matched = [t for t in joined if t['score_cont'] is not None]
    print(f"  trades matched to continuum: {len(matched)} (unmatched: {len(joined)-len(matched)})")

    for direction in ('SHORT', 'LONG'):
        sub = [t for t in matched if t['dir'] == direction]
        print(f"\n{'='*70}\n{direction} trades: {len(sub)} matched to continuum\n{'='*70}")

        # Bucket by continuum score at open
        print(f"\n--- {direction} by BTC continuum score at open ---")
        print(f"{'bucket':<10} {'n':>5} {'WR%':>7} {'PnL$':>9} {'PnL%':>9} {'avg$':>7}")
        buckets = defaultdict(list)
        for t in sub:
            buckets[score_bucket(t['score_cont'])].append(t)
        for b in sorted(buckets):
            s = stats(buckets[b], b)
            print(f"{b:<10} {s['n']:>5} {s['wr']:>6.1f}% {s['pnl']:>+9.2f} {s['pnl_pct']:>+9.2f} {s['avg']:>+7.3f}")

        # z-score tier
        print(f"\n--- {direction} by BTC zscore_tier at open ---")
        print(f"{'z':<14} {'n':>5} {'WR%':>7} {'PnL$':>9} {'avg$':>7}")
        zb = defaultdict(list)
        for t in sub:
            zb[z_bucket(t['z_cont'])].append(t)
        for b in sorted(zb):
            s = stats(zb[b], b)
            print(f"{b:<14} {s['n']:>5} {s['wr']:>6.1f}% {s['pnl']:>+9.2f} {s['avg']:>+7.3f}")

        # score x z cross-tab (key for gate logic)
        print(f"\n--- {direction} score bucket x z tier (PnL$ / n) ---")
        ztiers = sorted({z_bucket(t['z_cont']) for t in sub})
        sbuckets = sorted({score_bucket(t['score_cont']) for t in sub})
        print(f"{'score':<10}" + "".join(f"{z:<14}" for z in ztiers))
        for sb in sbuckets:
            line = f"{sb:<10}"
            for z in ztiers:
                cell = [t for t in sub if score_bucket(t['score_cont']) == sb and z_bucket(t['z_cont']) == z]
                if cell:
                    line += f"{sum(t['pnl'] for t in cell):>+7.2f}/{len(cell):<5}"
                else:
                    line += f"{'-':<12}"
            print(line)

        # 4h regime distribution
        print(f"\n--- {direction} by entry_regime_4h ---")
        print(f"{'regime':<14} {'n':>5} {'WR%':>7} {'PnL$':>9}")
        rb = defaultdict(list)
        for t in sub:
            rb[t['regime_4h'] or 'unknown'].append(t)
        for b in sorted(rb):
            s = stats(rb[b], b)
            print(f"{b:<14} {s['n']:>5} {s['wr']:>6.1f}% {s['pnl']:>+9.2f}")

        # Pre-filter vs post-filter windows (gate activation dates)
        print(f"\n--- {direction} by period vs gate activation ---")
        # SHORT_NEUTRAL_BLOCK: 2026-08-22, LONG_NEUTRAL_BLOCK: 2026-09-02, SHORT_CONTINUUM: 2026-10-01
        periods = [
            ('before all gates (<2026-08-22)', lambda t: t['epoch'] < 1787356800),  # 2026-08-22 UTC approx
            ('2026-08-22..09-02 (neutral blocks on)', lambda t: 1787356800 <= t['epoch'] < 1788307200),
            ('after 2026-09-02 (all but short-cont)', lambda t: 1788307200 <= t['epoch'] < 1790812800),
            ('2026-10-01+ (short-cont live)', lambda t: t['epoch'] >= 1790812800),
        ]
        print(f"{'period':<38} {'n':>5} {'WR%':>7} {'PnL$':>9} {'avg$':>7}")
        for label, fn in periods:
            cell = [t for t in sub if fn(t)]
            if cell:
                s = stats(cell, label)
                print(f"{label:<38} {s['n']:>5} {s['wr']:>6.1f}% {s['pnl']:>+9.2f} {s['avg']:>+7.3f}")

    # Targeted gate-simulations
    print(f"\n{'='*70}\nGATE SIMULATIONS (matched trades)\n{'='*70}")

    shorts = [t for t in matched if t['dir'] == 'SHORT']
    longs = [t for t in matched if t['dir'] == 'LONG']

    # Gate 1: SHORT-CONTINUUM. Current: block if score>10 AND z!=STRONG_NEG
    print("\n--- Gate 1: SHORT-CONTINUUM threshold sweep ---")
    print("Blocks SHORT when score > T AND z != STRONG_NEG. Positive PnL saved = trades blocked that LOST money.")
    for T in (0, 5, 10, 20, 30, 40, 50, 60):
        blocked = [t for t in shorts if t['score_cont'] is not None and t['score_cont'] > T and t['z_cont'] != 'STRONG_NEG']
        kept = [t for t in shorts if t not in blocked]
        bp = sum(t['pnl'] for t in blocked)
        kp = sum(t['pnl'] for t in kept) if kept else 0
        bw = sum(1 for t in blocked if t['pnl'] > 0) / len(blocked) * 100 if blocked else 0
        kw = sum(1 for t in kept if t['pnl'] > 0) / len(kept) * 100 if kept else 0
        print(f"  T={T:>2}: blocked n={len(blocked):>4} WR={bw:>5.1f}% PnL={bp:>+8.2f} | kept n={len(kept):>4} WR={kw:>5.1f}% PnL={kp:>+8.2f}")

    # Gate 2: LONG-NEUTRAL. Proposed exception: allow LONG when score>60
    print("\n--- Gate 2: LONG score buckets (the proposed score>60 exception) ---")
    for lo, hi, label in [(0,40,'<40'), (40,60,'40-60'), (60,80,'60-80'), (80,101,'>=80')]:
        cell = [t for t in longs if t['score_cont'] is not None and lo <= t['score_cont'] < hi]
        if cell:
            s = stats(cell, label)
            print(f"  score {label:>6}: n={s['n']:>4} WR={s['wr']:>5.1f}% PnL={s['pnl']:>+8.2f} avg={s['avg']:>+7.3f}")
    # score>60 AND ema=ABOVE (momentum LONGs — the ones a score exception would release)
    cell = [t for t in longs if t['score_cont'] and t['score_cont'] > 60 and t['ema'] == 'ABOVE']
    if cell:
        s = stats(cell, 'score>60 ema=ABOVE')
        print(f"  score>60 + ema=ABOVE: n={s['n']} WR={s['wr']:.1f}% PnL={s['pnl']:+.2f} avg={s['avg']:+.3f}")
    cell = [t for t in longs if t['score_cont'] and t['score_cont'] > 60 and t['ema'] != 'ABOVE']
    if cell:
        s = stats(cell, 'score>60 ema!=ABOVE')
        print(f"  score>60 + ema!=ABOVE: n={s['n']} WR={s['wr']:.1f}% PnL={s['pnl']:+.2f} avg={s['avg']:+.3f}")

    # Gate 2b: LONG in NEUTRAL 4h regime specifically
    print("\n--- Gate 2b: LONG in 4h NEUTRAL regime, by continuum score ---")
    neu = [t for t in longs if t['regime_4h'] == 'NEUTRAL']
    print(f"  total LONG trades with 4h=NEUTRAL: {len(neu)}")
    nb = defaultdict(list)
    for t in neu:
        nb[score_bucket(t['score_cont'])].append(t)
    print(f"  {'bucket':<10} {'n':>5} {'WR%':>7} {'PnL$':>9}")
    for b in sorted(nb):
        s = stats(nb[b], b)
        print(f"  {b:<10} {s['n']:>5} {s['wr']:>6.1f}% {s['pnl']:>+9.2f}")
    # Proposed exception impact: LONG + NEUTRAL + score>60
    exc = [t for t in neu if t['score_cont'] and t['score_cont'] > 60]
    if exc:
        s = stats(exc, 'NEUTRAL score>60')
        print(f"  PROPOSED EXCEPTION (NEUTRAL + score>60): n={s['n']} WR={s['wr']:.1f}% PnL={s['pnl']:+.2f} avg={s['avg']:+.3f}")

    # Gate 2c: SHORT in NEUTRAL 4h regime, by score (parallel analysis)
    print("\n--- SHORT in 4h NEUTRAL regime, by continuum score ---")
    sneu = [t for t in shorts if t['regime_4h'] == 'NEUTRAL']
    print(f"  total SHORT trades with 4h=NEUTRAL: {len(sneu)}")
    nb2 = defaultdict(list)
    for t in sneu:
        nb2[score_bucket(t['score_cont'])].append(t)
    print(f"  {'bucket':<10} {'n':>5} {'WR%':>7} {'PnL$':>9}")
    for b in sorted(nb2):
        s = stats(nb2[b], b)
        print(f"  {b:<10} {s['n']:>5} {s['wr']:>6.1f}% {s['pnl']:>+9.2f}")

    # Sample sizes for z=STRONG_NEG shorts (the only shorts currently allowed at high scores)
    print("\n--- Shorts with z=STRONG_NEG (currently allowed regardless of score) ---")
    sn = [t for t in shorts if t['z_cont'] == 'STRONG_NEG']
    s = stats(sn, 'STRONG_NEG') if sn else None
    if s:
        print(f"  n={s['n']} WR={s['wr']:.1f}% PnL={s['pnl']:+.2f} avg={s['avg']:+.3f}")
    for lo, hi, label in [(0,5,'<5'),(5,10,'5-10'),(10,30,'10-30'),(30,60,'30-60'),(60,101,'>=60')]:
        cell = [t for t in sn if lo <= t['score_cont'] < hi]
        if cell:
            s = stats(cell, label)
            print(f"    score {label:>6}: n={s['n']} WR={s['wr']:.1f}% PnL={s['pnl']:+.2f}")

    # Recent window using metadata btc_score (last 14d, cross-check)
    print(f"\n{'='*70}\nCROSS-CHECK: metadata btc_score (last ~14d, n={sum(1 for t in joined if t['score_meta'] is not None)})\n{'='*70}")
    for direction in ('SHORT', 'LONG'):
        sub = [t for t in joined if t['dir'] == direction and t['score_meta'] is not None]
        print(f"\n{direction} by metadata btc_score:")
        mb = defaultdict(list)
        for t in sub:
            mb[score_bucket(t['score_meta'])].append(t)
        print(f"  {'bucket':<10} {'n':>5} {'WR%':>7} {'PnL$':>9}")
        for b in sorted(mb):
            s = stats(mb[b], b)
            print(f"  {b:<10} {s['n']:>5} {s['wr']:>6.1f}% {s['pnl']:>+9.2f}")

if __name__ == '__main__':
    main()
