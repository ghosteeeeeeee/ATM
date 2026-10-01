#!/usr/bin/env python3
"""Audit part 2: Gate-3 velocity analysis, regime proxy, significance, log event counts."""
import sys, os, json, sqlite3, math, random, re
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, '/root/.hermes/scripts')
import psycopg2
from chop_detector import _classify_signal

BRAIN_DB = {'host': '/var/run/postgresql', 'dbname': 'brain', 'user': 'postgres', 'password': 'postgres'}
CANDLES = '/root/.hermes/data/candles.db'
CONTINUUM_DB = '/root/.hermes/data/continuum.db'

def load_btc_candles():
    conn = sqlite3.connect(CANDLES, timeout=10)
    rows = conn.execute("SELECT ts, close FROM candles_1m WHERE token='BTC' ORDER BY ts").fetchall()
    conn.close()
    return rows

def load_continuum():
    conn = sqlite3.connect(CONTINUUM_DB, timeout=10)
    rows = conn.execute(
        "SELECT ts, state_score, zscore_tier, market_phase, ema300_position, linreg_direction "
        "FROM continuum_states WHERE token='BTC' AND timeframe='1m' ORDER BY ts"
    ).fetchall()
    conn.close()
    return rows

def bisect_latest(rows, epoch_ts, val_idx=0):
    lo, hi, ans = 0, len(rows) - 1, -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if rows[mid][val_idx] <= epoch_ts:
            ans = mid; lo = mid + 1
        else:
            hi = mid - 1
    return ans

def btc_velocity(candles, epoch_ts, minutes=30):
    """% change of BTC over `minutes` ending at epoch_ts. Uses nearest candle <= ts."""
    i = bisect_latest(candles, epoch_ts)
    if i < minutes:
        return None
    p_now = candles[i][1]
    p_then = candles[i - minutes][1]
    if not p_then:
        return None
    return (p_now - p_then) / p_then * 100.0

def btc_ema300_pos(candles, epoch_ts):
    """EMA300 position of BTC at epoch_ts using last 400 closes."""
    i = bisect_latest(candles, epoch_ts)
    if i < 400:
        return None, None
    closes = [c[1] for c in candles[i-399:i+1]]
    k = 2 / (300 + 1)
    ema = closes[0]
    for c in closes[1:]:
        ema = c * k + ema * (1 - k)
    price = closes[-1]
    return ('ABOVE' if price >= ema else 'BELOW'), (price - ema) / ema * 100

def btc_slope_4h(candles, epoch_ts, bars=240):
    """Simple % slope over last 4h (240 x 1m bars)."""
    i = bisect_latest(candles, epoch_ts)
    if i < bars:
        return None
    p_now = candles[i][1]
    p_then = candles[i - bars][1]
    if not p_then:
        return None
    return (p_now - p_then) / p_then * 100.0

def score_bucket(s):
    if s is None: return 'unknown'
    if s < 5: return 'a:<5'
    if s < 10: return 'b:5-10'
    if s < 30: return 'c:10-30'
    if s < 60: return 'd:30-60'
    if s < 80: return 'e:60-80'
    return 'f:>=80'

def stats(cell):
    n = len(cell)
    if n == 0:
        return None
    pnls = [t['pnl'] for t in cell]
    wins = sum(1 for p in pnls if p > 0)
    mean = sum(pnls) / n
    var = sum((p - mean) ** 2 for p in pnls) / (n - 1) if n > 1 else 0
    se = math.sqrt(var / n) if n > 1 else 0
    return {'n': n, 'wr': wins / n * 100, 'pnl': sum(pnls), 'mean': mean, 'se': se,
            't': (mean / se) if se > 0 else 0}

def fmt(s, label):
    if not s:
        return f"  {label:<38} n=0"
    return (f"  {label:<38} n={s['n']:>4} WR={s['wr']:>5.1f}% PnL={s['pnl']:>+8.2f} "
            f"avg={s['mean']:>+7.4f} se={s['se']:>7.4f} t={s['t']:>+6.2f}")

def main():
    print("Loading BTC candles + continuum...")
    candles = load_btc_candles()
    cont = load_continuum()
    print(f"  candles={len(candles)} span {candles[0][0]}..{candles[-1][0]}")
    print(f"  continuum={len(cont)}")

    conn = psycopg2.connect(**BRAIN_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT direction, signal, pnl_usdt, pnl_pct,
               EXTRACT(EPOCH FROM open_time)::bigint AS open_epoch
        FROM trades
        WHERE status='closed' AND open_time > now() - interval '60 days'
        ORDER BY open_time
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    joined = []
    for direction, signal, pnl, pnl_pct, open_epoch in rows:
        if open_epoch is None or pnl is None:
            continue
        vel = btc_velocity(candles, open_epoch)
        ci = bisect_latest(cont, open_epoch)
        c = cont[ci] if ci >= 0 else None
        sig = (signal or '').lower()
        try:
            family = _classify_signal(sig)
        except Exception:
            family = 'UNKNOWN'
        joined.append({
            'dir': direction, 'signal': signal, 'sig_l': sig, 'family': family,
            'pnl': float(pnl), 'pnl_pct': float(pnl_pct or 0), 'epoch': open_epoch,
            'vel': vel,
            'score': c[1] if c else None, 'z': c[2] if c else None,
            'phase': c[3] if c else None, 'ema': c[4] if c else None, 'linreg': c[5] if c else None,
        })
    print(f"  trades joined: {len(joined)} (vel matched: {sum(1 for t in joined if t['vel'] is not None)})")

    FLAT = 0.20  # BTC_CHOP_GATE_THRESHOLD

    print(f"\n{'='*78}\nGATE 3 ANALYSIS: BTC 30m velocity at trade open (threshold |vel| < {FLAT}%)\n{'='*78}")
    for direction in ('SHORT', 'LONG'):
        sub = [t for t in joined if t['dir'] == direction and t['vel'] is not None]
        mom = [t for t in sub if t['family'] == 'MOMENTUM']
        mr = [t for t in sub if t['family'] == 'MEAN_REVERSION']
        print(f"\n--- {direction} (vel-matched n={len(sub)}; MOMENTUM n={len(mom)}, MEAN_REV n={len(mr)}) ---")
        for label, cell in [
            ('ALL', sub),
            ('MOMENTUM + BTC flat (<0.20)', [t for t in mom if abs(t['vel']) < FLAT]),
            ('MOMENTUM + BTC moving (>=0.20)', [t for t in mom if abs(t['vel']) >= FLAT]),
            ('MEAN_REV + BTC flat (<0.20)', [t for t in mr if abs(t['vel']) < FLAT]),
            ('MEAN_REV + BTC moving (>=0.20)', [t for t in mr if abs(t['vel']) >= FLAT]),
        ]:
            print(fmt(stats(cell), label))

        # momentum + flat, by direction-aligned BTC move
        flat_mom = [t for t in mom if abs(t['vel']) < FLAT]
        aligned = [t for t in flat_mom if (t['dir'] == 'LONG' and t['vel'] > 0) or (t['dir'] == 'SHORT' and t['vel'] < 0)]
        contra = [t for t in flat_mom if (t['dir'] == 'LONG' and t['vel'] < 0) or (t['dir'] == 'SHORT' and t['vel'] > 0)]
        print(fmt(stats(aligned), 'MOM+flat, BTC aligned w/ dir'))
        print(fmt(stats(contra), 'MOM+flat, BTC against dir'))

        # momentum + flat, by continuum phase (what the override allows)
        print(f"  -- MOMENTUM + BTC flat, by BTC continuum phase --")
        pb = defaultdict(list)
        for t in flat_mom:
            pb[t['phase'] or 'none'].append(t)
        for b in sorted(pb):
            print(fmt(stats(pb[b]), f'phase={b}'))

        # velocity bands
        print(f"  -- {direction} MOMENTUM by |BTC 30m vel| band --")
        for lo, hi, label in [(0,0.05,'0-0.05'),(0.05,0.10,'0.05-0.10'),(0.10,0.20,'0.10-0.20'),
                               (0.20,0.40,'0.20-0.40'),(0.40,0.80,'0.40-0.80'),(0.80,99,'>=0.80')]:
            cell = [t for t in mom if t['vel'] is not None and lo <= abs(t['vel']) < hi]
            print(fmt(stats(cell), f'|vel| {label}'))

    # Gate 3 simulation: what if threshold lowered / override fixed
    print(f"\n{'='*78}\nGATE 3 SIMULATIONS (MOMENTUM trades, both dirs)\n{'='*78}")
    mom_all = [t for t in joined if t['family'] == 'MOMENTUM' and t['vel'] is not None]
    for thr in (0.10, 0.15, 0.20, 0.30):
        blocked = [t for t in mom_all if abs(t['vel']) < thr]
        print(fmt(stats(blocked), f'blocked if |vel|<{thr:.2f}'))
    # current override simulation: SHORT allowed when phase DECLINING/STORMY or bearish struct; LONG when RECOVERY/NEUTRAL
    blocked_now = [t for t in mom_all if abs(t['vel']) < FLAT]
    would_pass_override = []
    still_blocked = []
    for t in blocked_now:
        if t['dir'] == 'SHORT' and (t['phase'] in ('DECLINING', 'STORMY') or
            (t['phase'] in ('CALM','RECOVERY') and t['linreg'] in ('LEAN_BEAR','BEAR') and t['ema'] == 'BELOW') or
            (t['linreg'] in ('LEAN_BEAR','BEAR') and t['ema'] == 'BELOW') or
            (t['phase'] == 'RANGING' and t['linreg'] in ('LEAN_BEAR','BEAR'))):
            would_pass_override.append(t)
        elif t['dir'] == 'LONG' and (t['phase'] in ('RECOVERY', 'NEUTRAL') or
            (t['phase'] == 'CALM' and t['linreg'] in ('LEAN_BULL','BULL') and t['ema'] in ('ABOVE','AT'))):
            would_pass_override.append(t)
        else:
            still_blocked.append(t)
    print(fmt(stats(would_pass_override), 'flat MOM that current override ALLOWS'))
    print(fmt(stats(still_blocked), 'flat MOM that override BLOCKS (net block)'))
    print(f"  breakdown of still-blocked by dir/phase:")
    sb = defaultdict(list)
    for t in still_blocked:
        sb[f"{t['dir']}/{t['phase']}"].append(t)
    for b in sorted(sb):
        print(fmt(stats(sb[b]), b))

    # Gate 2 proxy: token-level NEUTRAL can't be replayed, use BTC 4h slope as market-trend proxy
    print(f"\n{'='*78}\nGATE 2 PROXY: BTC 4h slope at open (market-trend proxy for 'NEUTRAL')\n{'='*78}")
    for direction in ('SHORT', 'LONG'):
        sub = [t for t in joined if t['dir'] == direction]
        for t in sub:
            t['slope4h'] = btc_slope_4h(candles, t['epoch'])
        sub = [t for t in sub if t['slope4h'] is not None]
        print(f"\n--- {direction} by BTC 4h slope band (n={len(sub)}) ---")
        for lo, hi, label in [(-99,-0.5,'<-0.5% (down)'),(-0.5,-0.15,'-0.5..-0.15'),(-0.15,0.15,'|slope|<0.15 ~flat'),
                               (0.15,0.5,'0.15..0.5'),(0.5,99,'>0.5% (up)')]:
            cell = [t for t in sub if lo <= t['slope4h'] < hi]
            print(fmt(stats(cell), f'slope {label}'))
        # score x flatness cross
        print(f"  -- {direction}: score bucket x BTC-flat (|vel|<0.2) --")
        for flat_flag, flabel in [(True, 'BTC flat'), (False, 'BTC moving')]:
            for sb_ in ('c:10-30','d:30-60','e:60-80','f:>=80'):
                cell = [t for t in sub if t['vel'] is not None and (abs(t['vel']) < FLAT) == flat_flag and score_bucket(t['score']) == sb_]
                print(fmt(stats(cell), f'{flabel} / score {sb_}'))

    # Combined freeze simulation: currently allowed vs blocked under all 3 gates
    print(f"\n{'='*78}\nCOMBINED FREEZE SIMULATION (60d matched trades)\n{'='*78}")
    matched = [t for t in joined if t['vel'] is not None and t['score'] is not None]
    results = defaultdict(lambda: {'allowed': [], 'blocked': []})
    for t in matched:
        reasons = []
        # Gate 1 SHORT-CONTINUUM
        if t['dir'] == 'SHORT' and t['score'] > 10 and t['z'] != 'STRONG_NEG':
            reasons.append('SHORT-CONTINUUM')
        # Gate 2 LONG-NEUTRAL proxy: BTC 4h slope flat AND BTC vel flat (approximation of the token-neutral+btc-flat combo)
        # NOTE: real gate uses token regime; this is an approximation
        sl = btc_slope_4h(candles, t['epoch'])
        btc_flat_market = sl is not None and abs(sl) < 0.15
        if t['dir'] == 'LONG' and btc_flat_market and abs(t['vel']) < FLAT:
            reasons.append('LONG-NEUTRAL~proxy')
        # Gate 3 BTC-CHOP-GATE: momentum + btc flat, minus override
        if t['family'] == 'MOMENTUM' and abs(t['vel']) < FLAT:
            ov = False
            if t['dir'] == 'SHORT' and (t['phase'] in ('DECLINING','STORMY') or
                (t['phase'] in ('CALM','RECOVERY') and t['linreg'] in ('LEAN_BEAR','BEAR') and t['ema']=='BELOW') or
                (t['linreg'] in ('LEAN_BEAR','BEAR') and t['ema']=='BELOW') or
                (t['phase']=='RANGING' and t['linreg'] in ('LEAN_BEAR','BEAR'))):
                ov = True
            if t['dir'] == 'LONG' and (t['phase'] in ('RECOVERY','NEUTRAL') or
                (t['phase']=='CALM' and t['linreg'] in ('LEAN_BULL','BULL') and t['ema'] in ('ABOVE','AT'))):
                ov = True
            if not ov:
                reasons.append('BTC-CHOP-GATE')
        key = t['dir']
        if reasons:
            results[key]['blocked'].append((t, reasons))
        else:
            results[key]['allowed'].append(t)

    for key in ('SHORT', 'LONG'):
        al = results[key]['allowed']
        bl = [x[0] for x in results[key]['blocked']]
        print(f"\n{key}: allowed n={len(al)} PnL={sum(t['pnl'] for t in al):+.2f} | "
              f"blocked-by-3-gates n={len(bl)} PnL={sum(t['pnl'] for t in bl):+.2f}")
        rc = defaultdict(list)
        for t, reasons in results[key]['blocked']:
            rc['+'.join(sorted(reasons))].append(t)
        for r in sorted(rc):
            print(fmt(stats(rc[r]), f'  blocked: {r}'))

    # Log event analysis
    print(f"\n{'='*78}\nPIPELINE LOG: distinct blocked signal events (last ~3 days)\n{'='*78}")
    log_path = '/root/.hermes/logs/pipeline.log'
    gate_pat = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}):\d{2}\s+.*\[([A-Z0-9-]+)\]\s+(\S+)\s+(LONG|SHORT)\b.*(?:BLOCKED|blocked)')
    events = defaultdict(set)  # gate -> set of (day, token, direction)
    daily_gate_tokens = defaultdict(lambda: defaultdict(set))
    with open(log_path, errors='replace') as f:
        for line in f:
            m = gate_pat.match(line)
            if m:
                ts_min, gate, token, direction = m.groups()
                day = ts_min[:10]
                events[gate].add((day, token, direction))
                daily_gate_tokens[day][gate].add(token)
    print(f"{'gate':<28} {'distinct(token,dir,day)':>22} {'distinct tokens':>16}")
    for gate in sorted(events, key=lambda g: -len(events[g])):
        toks = {e[1] for e in events[gate]}
        print(f"{gate:<28} {len(events[gate]):>22} {len(toks):>16}")
    print("\nPer-day distinct blocked tokens by top gates:")
    all_days = sorted(daily_gate_tokens)
    top_gates = ['SHORT-CONTINUUM','LONG-NEUTRAL','SHORT-NEUTRAL','BTC-CHOP-GATE','PUMP-CHAIN-SHORT-HIGH','LONG-RSI-BLOCK']
    print(f"{'day':<12}" + "".join(f"{g[:16]:>18}" for g in top_gates))
    for day in all_days:
        print(f"{day:<12}" + "".join(f"{len(daily_gate_tokens[day].get(g,set())):>18}" for g in top_gates))

    # Recent trade volume (what actually fired)
    conn = psycopg2.connect(**BRAIN_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT date(open_time) d, direction, COUNT(*), SUM(pnl_usdt)
        FROM trades WHERE open_time > now() - interval '10 days' AND status='closed'
        GROUP BY 1,2 ORDER BY 1,2
    """)
    print("\nActual trades fired per day (last 10 days):")
    print(f"{'date':<12} {'dir':<7} {'n':>4} {'pnl':>8}")
    for d, direction, n, pnl in cur.fetchall():
        print(f"{str(d):<12} {direction:<7} {n:>4} {float(pnl or 0):>+8.2f}")
    cur.close(); conn.close()

if __name__ == '__main__':
    main()
