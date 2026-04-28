#!/usr/bin/env python3
"""
Backtest: hwave BONUS THRESHOLDS only — regime filter disabled.
Tests clean_thresh (|avg_z_abs| < X → +5) and vel_thresh (|avg_vel| > X → +5).
The regime filter (z_direction check) is disabled to isolate bonus parameter effects.

Why: signal_gen's z_direction is computed by get_momentum() using phase+velocity,
not a simple 50-bar z-score. We can't replicate it accurately without importing
the full signal_gen state machine. So we test the bonus params in isolation.
"""
import bisect, sqlite3, statistics, sys, os, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import *

DB = '/root/.hermes/data/candles.db'
bisect_right = bisect.bisect_right

TOKENS=['BTC','ETH','SOL','AVAX','APT','ARB','OP','MATIC','FIL','LDO',
        'DOT','ADA','LINK','XRP','UNI','ATOM','NEAR','APE','GALA',
        'SUI','SEI','TIA','STRK','ZK','NIL','PROMPT','AVNT','LIT','AXS',
        'COMP','MKR','SNX','AAVE','CRV','RUNE','KAVA','OSMO','STX','ICP',
        'NEON','PEPE','SHIB','BONK','WIF','FLOKI']

# Reference TF: 15m gives ~26h of data = ~104 15m bars per token
REF_TF = '15m'
TFS_HIGHER = ['1h', '4h']  # confluence with higher TFs

TF_Z_WINDOWS = {'15m': 15, '1h': 60, '4h': 240}

# Velocity: exact replica of _compute_zscore_velocity_for_tf
def vel_sig_gen(prices, offset):
    if len(prices) < 60:
        return None
    ago = min(60, len(prices) // 4)
    def z_at(psub):
        if len(psub) < 20:
            return None
        mu  = statistics.mean(psub)
        std = statistics.stdev(psub) if len(psub) > 1 else 1
        return (psub[-1] - mu) / std if std else None
    z_now  = z_at(prices[offset-20:offset])
    z_then = z_at(prices[offset-20-ago:offset-ago]) if len(prices) > ago + 20 else None
    return (z_now - z_then) / ago if z_now is not None and z_then is not None else None

MIN_BARS = 60    # enough for 15m (window=15)
HORIZONS = [4, 8, 16, 24]  # hours forward (4 bars/hr in 15m)

def get_token_tf_data(token):
    out = {}
    for tf in ['15m', '1h', '4h']:
        conn = sqlite3.connect(DB)
        rows = conn.execute(f"SELECT ts, close FROM candles_{tf} WHERE token=? ORDER BY ts ASC", (token,)).fetchall()
        conn.close()
        out[tf] = rows
    return out

def closest_candle_before(rows, ts):
    if not rows:
        return None
    idx = bisect_right(rows, (ts, 1e9)) - 1
    return idx if idx >= 0 else None

def compute_z_at(closes, offset, window):
    if offset < window:
        return None
    chunk = closes[offset-window:offset]
    if len(chunk) < window // 2:
        return None
    mu  = statistics.mean(chunk)
    std = statistics.stdev(chunk) if len(chunk) > 1 else 1
    return (closes[offset] - mu) / std if std else None

def hwave_test(token_data, ref_idx, cap, clean_thresh, vel_thresh):
    """
    Returns (direction, avg_z_signed, avg_z_abs, avg_vel) or None.
    Regime filter DISABLED — we only test the near-mean + velocity filters.
    """
    ref_rows = token_data.get(REF_TF, [])
    if ref_idx >= len(ref_rows):
        return None
    ref_ts    = ref_rows[ref_idx][0]
    closes_ref = [r[1] for r in ref_rows]

    # Reference TF direction (z sign at 15m, window=15)
    z_ref = compute_z_at(closes_ref, ref_idx, TF_Z_WINDOWS['15m'])
    if z_ref is None:
        return None
    dir_ref = 'LONG' if z_ref < -0.2 else 'SHORT' if z_ref > 0.2 else None
    if dir_ref is None:
        return None

    # Collect higher TF data
    valid_tfs     = {}
    bullish_tfs   = 1   # reference TF counts as 1
    bearish_tfs   = 0
    all_vel       = [vel_sig_gen(closes_ref, ref_idx)]

    for tf in TFS_HIGHER:
        tf_rows = token_data.get(tf, [])
        idx_tf  = closest_candle_before(tf_rows, ref_ts)
        if idx_tf is None or idx_tf < TF_Z_WINDOWS[tf]:
            continue
        closes_tf = [r[1] for r in tf_rows]
        zw = TF_Z_WINDOWS[tf]
        z  = compute_z_at(closes_tf, idx_tf, zw)
        v  = vel_sig_gen(closes_tf, idx_tf)
        if z is None or v is None:
            continue
        tf_dir = 'LONG' if z < -0.2 else 'SHORT' if z > 0.2 else None
        if tf_dir is None:
            continue
        valid_tfs[tf] = (z, v)
        all_vel.append(v)
        if tf_dir == 'LONG':
            bullish_tfs += 1
        else:
            bearish_tfs += 1

    # Need ≥2 TFs total
    if bullish_tfs + bearish_tfs < 2:
        return None

    # All TFs must agree (including reference)
    n_total = bullish_tfs + bearish_tfs
    if bullish_tfs != n_total and bearish_tfs != n_total:
        return None  # mixed — skip

    local_dir    = 'LONG' if bullish_tfs > bearish_tfs else 'SHORT'
    all_z        = [z_ref] + [z for z, _ in valid_tfs.values()]
    avg_z_signed = statistics.mean(all_z)
    avg_z_abs    = statistics.mean([abs(z) for z in all_z])
    avg_vel      = statistics.mean([v for v in all_vel if v is not None])

    # Velocity confirmation
    vel_confirmed = (local_dir == 'LONG' and avg_vel > 0) or (local_dir == 'SHORT' and avg_vel < 0)
    if not vel_confirmed:
        return None

    # Near-mean cap
    if abs(avg_z_signed) > cap:
        return None

    # BONUSES (what we're actually testing — not filters)
    bonus_clean = 5 if abs(avg_z_abs) < clean_thresh else 0
    bonus_vel   = 5 if abs(avg_vel) > vel_thresh else 0
    base_conf   = 45 + n_total * 8 + max(bullish_tfs, bearish_tfs) * 5
    conf        = min(85, base_conf + bonus_clean + bonus_vel)

    return (local_dir, avg_z_signed, avg_z_abs, avg_vel, n_total, conf)


def run_backtest(cap, clean_thresh, vel_thresh):
    long_res  = {h: [] for h in HORIZONS}
    short_res = {h: [] for h in HORIZONS}

    for token in TOKENS:
        data = get_token_tf_data(token)
        ref_rows = data.get(REF_TF, [])
        if len(ref_rows) < MIN_BARS + max(HORIZONS) * 4:
            continue

        n_ref     = len(ref_rows)
        closes_ref = [r[1] for r in ref_rows]
        max_bar   = n_ref - max(HORIZONS) * 4 - 1

        for bar in range(MIN_BARS, max_bar):
            result = hwave_test(data, bar, cap, clean_thresh, vel_thresh)
            if result is None:
                continue
            local_dir = result[0]

            for h in HORIZONS:
                idx_f = bar + h * 4
                if idx_f >= n_ref:
                    continue
                ret = (closes_ref[idx_f] - closes_ref[bar]) / closes_ref[bar] * 100
                win = (ret > 0 and local_dir == 'LONG') or (ret < 0 and local_dir == 'SHORT')
                if local_dir == 'LONG':
                    long_res[h].append((ret, win))
                else:
                    short_res[h].append((ret, win))

    return long_res, short_res


def stats(res, h):
    if h not in res or not res[h]:
        return None
    rets = [r for r, _ in res[h]]
    wins = [w for _, w in res[h]]
    return len(res[h]), statistics.mean(rets), sum(wins)/len(wins)*100


# ── Sweep ─────────────────────────────────────────────────────
CAPS         = [0.3, 0.35, 0.4, 0.5, 0.6]
CLEAN_THRESH = [0.10, 0.15, 0.20, 0.25, 0.30]
VEL_THRESH   = [0.03, 0.05, 0.08, 0.10, 0.12, 0.15]

print(f"Reference TF: {REF_TF}")
print(f"Higher TFs: {TFS_HIGHER}")
print(f"CAPS={CAPS}")
print(f"CLEAN_THRESH={CLEAN_THRESH}")
print(f"VEL_THRESH={VEL_THRESH}")
print(f"TOKENS={len(TOKENS)}")
print(f"NOTE: Regime filter DISABLED — testing near-mean + velocity only")
print()

all_results = []

total_combos = len(CAPS) * len(CLEAN_THRESH) * len(VEL_THRESH)
print(f"Testing {total_combos} combos...", flush=True)

for n, (cap, clean, vel) in enumerate(itertools.product(CAPS, CLEAN_THRESH, VEL_THRESH), 1):
    long_res, short_res = run_backtest(cap, clean, vel)

    h4_l = stats(long_res, 4)
    h4_s = stats(short_res, 4)

    l_n = h4_l[0] if h4_l else 0
    l_a = h4_l[1] if h4_l else 0
    l_h = h4_l[2] if h4_l else 0
    s_n = h4_s[0] if h4_s else 0
    s_a = h4_s[1] if h4_s else 0
    s_h = h4_s[2] if h4_s else 0

    score = (l_h/100 * min(l_n/10, 1) + s_h/100 * min(s_n/10, 1)) * 50

    all_results.append({
        'cap': cap, 'clean': clean, 'vel': vel,
        'l_n': l_n, 'l_a': l_a, 'l_h': l_h,
        's_n': s_n, 's_a': s_a, 's_h': s_h,
        'score': score,
    })

    if n % 30 == 0:
        print(f"  {n}/{total_combos} done...", flush=True)

print()
print(f"{'CAP':>5} | {'CLEAN':>6} | {'VEL':>5} | {'N_L':>4} | {'L_4h%':>8} | {'L_HR%':>6} | {'N_S':>4} | {'S_4h%':>8} | {'S_HR%':>6} | {'SCORE':>6}")
print("-" * 100)
for r in sorted(all_results, key=lambda x: -x['score']):
    print(f"{r['cap']:>5.2f} | {r['clean']:>6.3f} | {r['vel']:>5.3f} | {r['l_n']:>4} | {r['l_a']:>+8.3f}% | {r['l_h']:>6.1f}% | {r['s_n']:>4} | {r['s_a']:>+8.3f}% | {r['s_h']:>6.1f}% | {r['score']:>6.2f}")

print()
print("TOP 10 by composite score:")
for r in sorted(all_results, key=lambda x: -x['score'])[:10]:
    print(f"  cap={r['cap']} clean={r['clean']} vel={r['vel']} | LN={r['l_n']}({r['l_a']:+.3f}%) LH={r['l_h']:.0f}% | SN={r['s_n']}({r['s_a']:+.3f}%) SH={r['s_h']:.0f}%")

print()
print("TOP 5 LONG 4h hit rate (min N=20):")
for r in sorted([x for x in all_results if x['l_n'] >= 20], key=lambda x: -x['l_h'])[:5]:
    print(f"  cap={r['cap']} clean={r['clean']} vel={r['vel']} | N={r['l_n']} | avg={r['l_a']:+.3f}% | hr={r['l_h']:.1f}%")

print()
print("TOP 5 SHORT 4h hit rate (min N=20):")
for r in sorted([x for x in all_results if x['s_n'] >= 20], key=lambda x: -x['s_h'])[:5]:
    print(f"  cap={r['cap']} clean={r['clean']} vel={r['vel']} | N={r['s_n']} | avg={r['s_a']:+.3f}% | hr={r['s_h']:.1f}%")

print()
print("SENSITIVITY: clean_thresh at cap=0.4, vel=0.08:")
for ct in CLEAN_THRESH:
    rs = [x for x in all_results if x['clean'] == ct and x['cap'] == 0.4 and x['vel'] == 0.08]
    for r in rs:
        print(f"  clean={ct} | LN={r['l_n']}({r['l_a']:+.3f}%) LH={r['l_h']:.0f}% | SN={r['s_n']}({r['s_a']:+.3f}%) SH={r['s_h']:.0f}%")

print()
print("SENSITIVITY: vel_thresh at cap=0.4, clean=0.20:")
for vt in VEL_THRESH:
    rs = [x for x in all_results if x['vel'] == vt and x['cap'] == 0.4 and x['clean'] == 0.20]
    for r in rs:
        print(f"  vel={vt} | LN={r['l_n']}({r['l_a']:+.3f}%) LH={r['l_h']:.0f}% | SN={r['s_n']}({r['s_a']:+.3f}%) SH={r['s_h']:.0f}%")