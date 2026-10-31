#!/usr/bin/env python3
"""
Independent (fresh-eyes) replay of the mfe-exit claim. Written from the
RULE SPEC, does not import jup_exit_sim or copy its functions.

Rules audited (as claimed):
  cohort   : trades WHERE signal LIKE '%jup_yolo%' AND status='closed'
             AND entry_price IS NOT NULL AND exit_price IS NOT NULL
  horizon  : entry_ts .. entry_ts + 12h, 5m closed candles, token.upper()
  floors   : price stop = entry * (1 - min(CUT_LOSER/lev, ATR_SL))  (0.8%)
  tp       : entry * (1 + 2.0%)
  mfe-exit : peak fav% tracked from bar highs (prior-bar peak), exit when
             price gives back 30% of peak -> exit at 70% of peak (price %)
  pm-trail : arms at +0.40% peak, trails 0.20% off peak
  intra-bar (as claimed): floor checked first, then profit layer (gap at
             open fills at open), then TP; peak updated after checks.
  pnl      : leveraged % units = unleveraged price % * leverage
"""
import os
import sqlite3
import sys
import datetime as dt
from itertools import combinations

sys.path.insert(0, '/root/.hermes/scripts')
import psycopg2
from _secrets import BRAIN_DB_DICT

HORIZON_S = 12 * 3600
GIVEBACK = 0.30            # 30% of peak given back  (MFE_EXIT_GIVEBACK_PCT)
ARM_MFE = 0.0              # literal spec (any positive peak)
ARM_MFE_040 = 0.40         # armed variant claim
PM_ARM = 0.40              # PM_TRAIL_ACTIVATE_PCT*100
PM_DIST = 0.20             # PM_TRAIL_DISTANCE_PCT*100
ATR_SL = 2.50              # compute_atr_sl_pct(1.0) in %  (verified separately)
ATR_TP = 2.00              # compute_atr_tp_pct(1.0) in %
FLOOR_ACC = 4.0            # CUT_LOSER_PNL account % (absolute)
CANDLE_DB = '/root/.hermes/data/candles.db'


# ────────────────────────────── data loading (own SQL) ──────────────────────
def load_trades():
    cfg = BRAIN_DB_DICT.copy()
    cfg.setdefault('port', 5432)
    conn = psycopg2.connect(**cfg)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(
        "SELECT id, token, direction, entry_price, exit_price, pnl_pct, "
        "open_time, close_time, close_reason, leverage, signal "
        "FROM trades WHERE signal LIKE %s AND status='closed' "
        "AND entry_price IS NOT NULL AND exit_price IS NOT NULL ORDER BY id",
        ('%jup_yolo%',))
    out = []
    for r in cur.fetchall():
        out.append(dict(id=r[0], token=r[1], dir=r[2], entry=float(r[3]),
                        exit=float(r[4]), pnl=float(r[5] or 0), open_t=r[6],
                        close_t=r[7], reason=r[8], lev=float(r[9] or 1),
                        sig=r[10]))
    cur.close()
    conn.close()
    return out


def load_candles(token, t0, t1):
    con = sqlite3.connect(CANDLE_DB, timeout=5)
    try:
        rows = con.execute(
            "SELECT ts, open, high, low, close FROM candles_5m "
            "WHERE token=? AND is_closed=1 AND ts>=? AND ts<? ORDER BY ts",
            (token, t0, t1)).fetchall()
    finally:
        con.close()
    return rows


# ────────────────────────────── my own replay ───────────────────────────────
def pnl_pct(direction, entry, px):
    if direction == 'LONG':
        return (px / entry - 1.0) * 100.0
    return (1.0 - px / entry) * 100.0


def walk(t, candles, strategy, entry_bar=False, peak_before=False,
         floor_first=True):
    """Return (exit_price, exit_ts, tag) for one strategy.

    strategy in {'bg','mfe30','mfe30a040','pmwalk','pm_mfe30','pm_mfe30a'}
    Conventions follow the CLAIM (floor first, prior-bar peak) unless the
    sensitivity flags say otherwise.
    """
    entry = t['entry']
    long_ = t['dir'] == 'LONG'
    entry_ts = int(t['open_t'].timestamp())
    horizon = entry_ts + HORIZON_S

    floor_frac = min(FLOOR_ACC / t['lev'], ATR_SL) / 100.0
    floor_px = entry * (1 - floor_frac) if long_ else entry * (1 + floor_frac)
    tp_frac = ATR_TP / 100.0
    tp_px = entry * (1 + tp_frac) if long_ else entry * (1 - tp_frac)

    layers = []
    if strategy in ('mfe30', 'pm_mfe30'):
        layers.append(('mfe', ARM_MFE))
    if strategy in ('mfe30a040', 'pm_mfe30a'):
        layers.append(('mfe', ARM_MFE_040))
    if strategy in ('pmwalk', 'pm_mfe30', 'pm_mfe30a'):
        layers.append(('pm', 0.0))
    use_mfe = any(k == 'mfe' for k, _ in layers)
    use_pm = any(k == 'pm' for k, _ in layers)

    peak = 0.0
    last = None
    for ts, o, h, l, c in candles:
        if ts < entry_ts and not (entry_bar and ts + 300 > entry_ts):
            continue           # default: skip the bar that contains entry
        if ts > horizon:
            break
        last = (ts, c)

        def thresholds(pk):
            """candidate profit thresholds from peak pk (favourable %)"""
            cands = []
            if pk > 0:
                if use_mfe:
                    arm = ARM_MFE_040 if ('mfe', ARM_MFE_040) in layers else ARM_MFE
                    if pk >= arm and pk > 0:
                        tf = pk * (1.0 - GIVEBACK)
                        if tf > 0:
                            px = (entry * (1 + tf / 100.0) if long_
                                  else entry * (1 - tf / 100.0))
                            cands.append((px, 'mfe_exit'))
                if use_pm and pk >= PM_ARM:
                    tf = pk - PM_DIST
                    if tf > 0:
                        px = (entry * (1 + tf / 100.0) if long_
                              else entry * (1 - tf / 100.0))
                        cands.append((px, 'pm_trail'))
            if not cands:
                return None
            if long_:
                return max(cands, key=lambda z: z[0])
            return min(cands, key=lambda z: z[0])

        pk_now = ((h / entry) - 1.0) * 100.0 if long_ else (1.0 - l / entry) * 100.0
        if peak_before:                      # sensitivity: use this bar's peak
            cand = thresholds(max(peak, pk_now))
        else:                                # claim: prior-bar peak
            cand = thresholds(peak)

        floor_hit = (l <= floor_px) if long_ else (h >= floor_px)
        tp_hit = (h >= tp_px) if long_ else (l <= tp_px)

        if floor_first and floor_hit:
            return floor_px, ts, 'floor'

        if cand is not None:
            px, tag = cand
            at_open = (o <= px) if long_ else (o >= px)
            touched = (l <= px) if long_ else (h >= px)
            if at_open or touched:
                fill = o if at_open else px
                if tp_hit and ((tp_px < fill) if long_ else (tp_px > fill)):
                    return tp_px, ts, 'atr_tp'
                return fill, ts, tag
            # (threshold not reached this bar; fall through to TP check)

        if not floor_first and floor_hit:
            return floor_px, ts, 'floor'
        if tp_hit:
            return tp_px, ts, 'atr_tp'

        if not peak_before:                   # update AFTER checks
            if pk_now > peak:
                peak = pk_now
    if last:
        return last[1], last[0], 'timeout'
    return None, None, None


def candles_cache(trades):
    cache = {}
    for t in trades:
        ot = int(t['open_t'].timestamp())
        cache[t['id']] = load_candles(
            t['token'].upper(), ot - 300, ot + HORIZON_S + 300)
    return cache


# ────────────────────────────── reporting helpers ───────────────────────────
def agg(vals):
    n = len(vals)
    if not n:
        return None
    w = sum(1 for v in vals if v > 0.05)
    l = sum(1 for v in vals if v < -0.05)
    wl = w + l
    s = sorted(vals)
    return dict(n=n, w=w, l=l, wr=(w / wl * 100 if wl else 0.0),
                net=sum(vals), avg=sum(vals) / n, med=s[n // 2])


def main():
    trades = load_trades()
    cache = candles_cache(trades)
    print(f"cohort n = {len(trades)}")

    strat_names = ['bg', 'mfe30', 'mfe30a040', 'pmwalk', 'pm_mfe30', 'pm_mfe30a']
    per = {}      # id -> {strategy: (px, ts, tag, pnl_lev)}
    for t in trades:
        row = {'pm_actual': (t['exit'], t['close_t'], t['reason'], t['pnl'])}
        for s in strat_names:
            px, xts, tag = walk(t, cache[t['id']], s)
            p = None if px is None else pnl_pct(t['dir'], t['entry'], px) * t['lev']
            row[s] = (px, xts, tag, p)
        per[t['id']] = row

    print("\n=== aggregates, my own replay (n=%d) ===" % len(trades))
    print(f"{'strategy':<12} {'n':>3} {'W':>3} {'L':>3} {'WR%':>5} {'net%':>8}")
    for s in ['pm_actual'] + strat_names:
        vals = [per[t['id']][s][3] for t in trades]
        a = agg(vals)
        print(f"{s:<12} {a['n']:>3} {a['w']:>3} {a['l']:>3} {a['wr']:>5.0f} "
              f"{a['net']:>+8.2f}")
        tg = {}
        for t in trades:
            tg[per[t['id']][s][2]] = tg.get(per[t['id']][s][2], 0) + 1
        print(f"             tags: {tg}")

    # ── does a 45-subset reproduce the CLAIMED numbers? ────────────────────
    CLAIM = dict(pm_actual=-12.20, bg=-68.03, mfe30=29.63, mfe30a040=27.18,
                 pmwalk=26.37, pm_mfe30=30.89, pm_mfe30a=28.65)
    print("\n=== brute-force: which dropped pair best matches the claim? ===")
    full = {s: sum(per[t['id']][s][3] for t in trades)
            for s in ['pm_actual'] + strat_names}
    want = {s: CLAIM[s] - full[s] for s in CLAIM}
    print("needed delta from dropped trades:", {k: round(v, 2)
                                                for k, v in want.items()})
    best = None
    ids = [t['id'] for t in trades]
    for a, b in combinations(ids, 2):
        err = 0.0
        ok = True
        for s in CLAIM:
            got = per[a][s][3] + per[b][s][3]
            if got is None:
                ok = False
                break
            err += (got - want[s]) ** 2
        if ok and (best is None or err < best[0]):
            best = (err, a, b)
    if best:
        err, a, b = best
        print(f"best pair = {a},{b}  rms-err={ (err/len(CLAIM))**0.5 :.3f}")
        for s in CLAIM:
            got = per[a][s][3] + per[b][s][3]
            print(f"   {s:<12} dropped-sum={got:>+8.2f} needed={want[s]:>+8.2f}")

    # ── per-trade table (for hand-checks) ───────────────────────────────────
    print("\n=== per-trade ===")
    hdr = f"{'id':>6} {'tok':<5} {'dir':<5} {'entry':>10} {'lev':>3} " \
          f"{'actual':>8} | " + " ".join(f"{s[:9]:>10}" for s in strat_names)
    print(hdr)
    for t in trades:
        r = per[t['id']]
        cells = []
        for s in strat_names:
            px, xts, tag, p = r[s]
            cells.append(f"{('None' if p is None else f'{p:+.2f}'):>10}")
        print(f"{t['id']:>6} {t['token']:<5} {t['dir']:<5} {t['entry']:>10.4f} "
              f"{t['lev']:>3.0f} {t['pnl']:>+8.2f} | " + " ".join(cells))

    # ── horizon elapsed ─────────────────────────────────────────────────────
    now = dt.datetime.utcnow()
    nel = [t['id'] for t in trades
           if t['open_t'] + dt.timedelta(hours=12) > now]
    print(f"\ntrades whose 12h horizon has NOT fully elapsed yet: {len(nel)} -> {nel}")
    print("bg timeouts on non-elapsed trades:",
          [t['id'] for t in trades if per[t['id']]['bg'][2] == 'timeout'
           and t['open_t'] + dt.timedelta(hours=12) > now])
    print("mfe30 timeouts:",
          [t['id'] for t in trades if per[t['id']]['mfe30'][2] == 'timeout'])

    # ── stats: paired sign test + bootstrap CI ─────────────────────────────
    import math
    import random
    random.seed(20261031)

    def sign_test(diffs):
        pos = sum(1 for d in diffs if d > 0)
        neg = sum(1 for d in diffs if d < 0)
        n = pos + neg
        if n == 0:
            return pos, neg, 1.0
        # two-sided exact binomial
        k = min(pos, neg)
        p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n * 2
        return pos, neg, min(1.0, p)

    def boot(vals, B=20000):
        n = len(vals)
        means = []
        for _ in range(B):
            s = sum(vals[random.randrange(n)] for _ in range(n))
            means.append(s)
        means.sort()
        return means[int(0.025 * B)], means[int(0.975 * B)]

    mfe = [per[t['id']]['mfe30'][3] for t in trades]
    bg = [per[t['id']]['bg'][3] for t in trades]
    act = [per[t['id']]['pm_actual'][3] for t in trades]
    d_bg = [m - b for m, b in zip(mfe, bg)]
    d_ac = [m - a for m, a in zip(mfe, act)]

    print("\n=== statistics (n=%d) ===" % len(trades))
    pos, neg, p = sign_test(d_bg)
    print(f"sign test mfe30 vs bg : +{pos}/-{neg} ties={len(trades)-pos-neg} "
          f"two-sided p={p:.4f}")
    pos, neg, p = sign_test(d_ac)
    print(f"sign test mfe30 vs pm_actual: +{pos}/-{neg} "
          f"ties={len(trades)-pos-neg} two-sided p={p:.4f}")
    lo, hi = boot(mfe)
    print(f"bootstrap 95% CI for mfe30 NET : [{lo:+.2f}, {hi:+.2f}] "
          f"(point {sum(mfe):+.2f})")
    lo, hi = boot(d_bg)
    print(f"bootstrap 95% CI for mfe30-bg  : [{lo:+.2f}, {hi:+.2f}] "
          f"(point {sum(d_bg):+.2f})")
    lo, hi = boot(d_ac)
    print(f"bootstrap 95% CI for mfe30-actual: [{lo:+.2f}, {hi:+.2f}] "
          f"(point {sum(d_ac):+.2f})")
    # how much of mfe30's edge is bg being awful?
    print(f"sum bg={sum(bg):+.2f}  sum actual={sum(act):+.2f}  "
          f"sum mfe30={sum(mfe):+.2f}")
    # fee adjustment
    FEE = 0.045 * 2 * 5          # 0.045%/side notional, round trip, 5x
    print(f"fee/trade (acct %) = {FEE:.2f} ; 47 trades -> {FEE*len(trades):+.2f}")
    for name, v in (('bg', bg), ('mfe30', mfe), ('pm_actual', act)):
        print(f"  net of fees {name:<10} {sum(v) - FEE*len(v):>+8.2f}")

    # ── sensitivity variants ────────────────────────────────────────────────
    print("\n=== sensitivity: mfe30 under alternate conventions ===")
    for label, kw in (
        ('claim (entry bar skipped, prior peak, floor first)',
         dict()),
        ('entry bar INCLUDED', dict(entry_bar=True)),
        ('peak from CURRENT bar', dict(peak_before=True)),
        ('profit layer checked BEFORE floor', dict(floor_first=False)),
        ('all three', dict(entry_bar=True, peak_before=True, floor_first=False)),
    ):
        vals, tags = [], {}
        for t in trades:
            px, xts, tag = walk(t, cache[t['id']], 'mfe30', **kw)
            p = pnl_pct(t['dir'], t['entry'], px) * t['lev']
            vals.append(p)
            tags[tag] = tags.get(tag, 0) + 1
        a = agg(vals)
        print(f"  {label:<50} net={a['net']:+7.2f} WR={a['wr']:3.0f}% tags={tags}")

    # bg under same conventions (for fairness of the delta)
    for label, kw in (('claim', dict()), ('entry bar INCLUDED', dict(entry_bar=True))):
        vals = []
        for t in trades:
            px, xts, tag = walk(t, cache[t['id']], 'bg', **kw)
            vals.append(pnl_pct(t['dir'], t['entry'], px) * t['lev'])
        a = agg(vals)
        print(f"  bg {label:<48} net={a['net']:+7.2f} WR={a['wr']:3.0f}%")

    # ── hand-check candidates: dump walks ───────────────────────────────────
    print("\n=== mfe_exit trades (to hand-check) ===")
    for t in trades:
        px, xts, tag, p = per[t['id']]['mfe30']
        if tag == 'mfe_exit':
            print(f"  id={t['id']} {t['token']} {t['dir']} entry={t['entry']} "
                  f"exit={px:.6f} pnl_lev={p:+.4f} ts={xts}")
    print("\n=== floor trades under mfe30 ===")
    for t in trades:
        px, xts, tag, p = per[t['id']]['mfe30']
        if tag == 'floor':
            print(f"  id={t['id']} {t['token']} {t['dir']} entry={t['entry']} "
                  f"exit={px:.6f} pnl_lev={p:+.4f} ts={xts}")


if __name__ == '__main__':
    main()
