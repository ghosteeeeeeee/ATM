#!/usr/bin/env python3
"""STATISTICIAN pass 2 — deeper: R:R structure, signal families, filter-blocked
trades, sizing, MFE/MAE, exit-engine comparison, losing-segment drill-down."""
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import psycopg2

sys.path.insert(0, "/root/.hermes/scripts")
from _secrets import BRAIN_DB_DICT  # noqa: E402


def wilson_ci(wins, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def one_prop_p(wins, n, p0):
    if n == 0:
        return 1.0
    se = math.sqrt(p0 * (1 - p0) / n)
    if se == 0:
        return 1.0
    z = (wins / n - p0) / se
    return 2 * (1 - norm_cdf(abs(z)))


conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("SELECT MAX(open_time) FROM trades WHERE open_time IS NOT NULL")
max_ts = cur.fetchone()[0]
cutoff = max_ts - timedelta(days=30)

cur.execute("""
    SELECT id, token, direction, signal, strategy, pnl_usdt, pnl_pct,
           amount_usdt, status, open_time, close_time, exit_reason,
           volatility_regime, paper, confidence, leverage, fees,
           entry_rsi_14, mfe_pct, mae_pct, _signal_metadata, exit_conditions,
           trade_duration, stop_loss, target, entry_price, exit_price,
           hype_pnl_usdt, hype_realized_pnl_usdt, hl_notional_usdt,
           sl_distance, trailing_stop_pct
    FROM trades
    WHERE open_time >= %s AND pnl_usdt IS NOT NULL
      AND status NOT IN ('OPEN', 'open', 'PENDING', 'pending', 'CANCELLED', 'cancelled')
    ORDER BY open_time
""", (cutoff,))
COLS = [d[0] for d in cur.description]
trades = [dict(zip(COLS, r)) for r in cur.fetchall()]
cur.close()
conn.close()

trades = [t for t in trades if t["pnl_usdt"] is not None]
n = len(trades)
print(f"Trades loaded: {n}")


def primary_signal(sig):
    """Normalize messy combined signal strings to primary family."""
    if not sig:
        return "(none)"
    s = str(sig).strip()
    # take first token before comma; strip trailing +/- and digits after _ variants
    first = s.split(",")[0].strip()
    # strip trailing direction suffix markers like +, -, or long/short keep
    # normalize case and underscores
    first = first.replace(" ", "_").lower()
    # remove trailing +/- signs
    first = first.rstrip("+-")
    # collapse _vN versions into base where useful? keep distinct but also make family
    return first


def signal_family(sig):
    """Roll variant versions into family (e.g. bb_bounce_v2_long -> bb_bounce)."""
    s = primary_signal(sig)
    s = re.sub(r"_v\d+", "", s)
    s = re.sub(r"-\d+$", "", s)  # r2-trend-long8 -> r2-trend-long
    s = re.sub(r"_long$|_short$|-long$|-short$", "", s)
    return s


# ═══════════════════════ A. R:R structure — THE key question ══════════════════
print("\n" + "=" * 70)
print("A. RISK/REWARD STRUCTURE — why 53.8% WR still loses")
print("=" * 70)
pnls = [float(t["pnl_usdt"]) for t in trades]
wins = [p for p in pnls if p > 0]
losses = [p for p in pnls if p < 0]
aw = sum(wins) / len(wins)
al = abs(sum(losses)) / len(losses)
be_wr = al / (aw + al)
print(f"avg win  = +{aw:.4f}")
print(f"avg loss = -{al:.4f}")
print(f"win/loss ratio (R:R) = {aw/al:.3f}")
print(f"Breakeven WR needed  = {be_wr*100:.2f}%")
print(f"Observed WR          = {len(wins)/(len(wins)+len(losses))*100:.2f}%")
obs_wr = len(wins) / (len(wins) + len(losses))
print(f"GAP (pp)             = {(obs_wr - be_wr)*100:+.2f}")
print(f"→ to break even at current WR, avg loss must drop to {aw*obs_wr/(1-obs_wr):.4f} (now {al:.4f})")
print(f"→ to break even at current WR, avg win must rise to  {al*(1-obs_wr)/obs_wr:.4f} (now {aw:.4f})")

# win-size distribution
print("\nWin size distribution (USDT):")
for lo, hi in [(0, 0.01), (0.01, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.50), (0.50, 1e9)]:
    c = sum(1 for w in wins if lo <= w < hi)
    label = f"{hi:.2f}" if hi < 1e8 else "inf"
    print(f"  {lo:.2f} - {label}: {c:>4} ({c/len(wins)*100:.1f}%)")
print("Loss size distribution (USDT):")
for lo, hi in [(0, 0.01), (0.01, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.50), (0.50, 1e9)]:
    c = sum(1 for l in losses if lo <= l < hi)
    label = f"{hi:.2f}" if hi < 1e8 else "inf"
    print(f"  {lo:.2f} - {label}: {c:>4} ({c/len(losses)*100:.1f}%)")

# ═══════════════════════ B. SIGNAL FAMILY (normalized) ════════════════════════
print("\n" + "=" * 70)
print("B. SIGNAL FAMILY PERFORMANCE (normalized primary signal)")
print("=" * 70)

fam = defaultdict(list)
fam_dir = defaultdict(list)
for t in trades:
    f = signal_family(t["signal"])
    fam[f].append(float(t["pnl_usdt"]))
    fam_dir[(f, (t["direction"] or "?").upper())].append(float(t["pnl_usdt"]))

rows = []
for f, ps in fam.items():
    nw = sum(1 for p in ps if p > 0)
    nl = sum(1 for p in ps if p < 0)
    nd = nw + nl
    wr = nw / nd if nd else 0
    tp = sum(ps)
    sw = [p for p in ps if p > 0]
    sl = [p for p in ps if p < 0]
    aw_ = sum(sw) / len(sw) if sw else 0
    al_ = abs(sum(sl)) / len(sl) if sl else 0
    be_ = al_ / (aw_ + al_) if (aw_ + al_) else 0
    p_bev = one_prop_p(nw, nd, be_) if 0 < be_ < 1 and nd else 1.0
    rows.append((f, len(ps), nw, nl, wr, tp, aw_, al_, be_, p_bev))

rows.sort(key=lambda x: x[5])
print(f"{'family':<28}{'n':>5}{'W':>4}{'L':>4}{'WR%':>7}{'PnL':>9}{'avgW':>7}{'avgL':>7}{'BE%':>7}{'p(WR>BE)':>10}  verdict")
for f, cnt, nw, nl, wr, tp, aw_, al_, be_, p_bev in rows:
    if cnt < 5:
        continue
    if cnt < 10:
        verdict = "NEEDS MORE DATA"
    elif p_bev < 0.05 and tp > 0:
        verdict = "EDGE (sig vs BE)"
    elif p_bev < 0.05 and tp < 0:
        verdict = "SIG LOSER"
    else:
        verdict = "inconclusive"
    print(f"{f[:28]:<28}{cnt:>5}{nw:>4}{nl:>4}{wr*100:>6.1f}%{tp:>+9.2f}{aw_:>+7.3f}{al_:>+7.3f}{be_*100:>6.1f}%{p_bev:>10.4f}  {verdict}")

# families with n<5 collapsed
small = [(f, c, tp) for f, c, nw, nl, wr, tp, *rest in rows if c < 5]
print(f"\nSmall families (n<5, combined): count={len(small)}, combined PnL={sum(s[2] for s in small):+.2f}")

# ═══════════════════════ C. EXIT ENGINE — the real PnL driver ═════════════════
print("\n" + "=" * 70)
print("C. EXIT ENGINE COMPARISON (which exit mechanism makes/loses money)")
print("=" * 70)

def engine_of(exit_reason, exit_conditions):
    er = (exit_reason or "").lower()
    ec = (exit_conditions or "").lower() if isinstance(exit_conditions, str) else ""
    if "profit-monster" in er or "profit-monster" in ec:
        return "profit-monster trail"
    if "cut-loser" in er or "cut-loser" in ec or "cl-t1" in er:
        return "cut-loser"
    if "atr_sl_hit" in er or "atr_sl" in er:
        return "ATR stop-loss"
    if "hard_sl" in er or "hard sl" in er:
        return "hard SL"
    if "rr_engine" in er:
        return "RR engine"
    if "pump_exit" in er or "dead_money" in er:
        return "pump dead-money exit"
    if "hard_tp" in er:
        return "hard TP"
    if "atr_trail" in er:
        return "ATR trail"
    if "hard_max_loss" in er:
        return "hard max-loss"
    if "trail" in er:
        return "generic trail"
    return f"other:{er[:30] if er else 'none'}"

eng = defaultdict(list)
for t in trades:
    eng[engine_of(t["exit_reason"], t["exit_conditions"])].append(float(t["pnl_usdt"]))

eng_rows = []
for e, ps in eng.items():
    nw = sum(1 for p in ps if p > 0)
    tp = sum(ps)
    eng_rows.append((e, len(ps), nw, tp, tp / len(ps) if ps else 0))
eng_rows.sort(key=lambda x: -x[3])
print(f"{'engine':<32}{'n':>5}{'W':>4}{'WR%':>7}{'PnL':>10}{'avg':>8}")
for e, cnt, nw, tp, avg in eng_rows:
    print(f"{e[:32]:<32}{cnt:>5}{nw:>4}{nw/cnt*100 if cnt else 0:>6.1f}%{tp:>+10.2f}{avg:>+8.4f}")

# ═══════════════════════ D. SIZING — is loss bigger because position bigger? ═══
print("\n" + "=" * 70)
print("D. POSITION SIZING — winners vs losers")
print("=" * 70)
amt_w = [float(t["amount_usdt"] or 0) for t in trades if float(t["pnl_usdt"] or 0) > 0]
amt_l = [float(t["amount_usdt"] or 0) for t in trades if float(t["pnl_usdt"] or 0) < 0]
amt_f = [float(t["amount_usdt"] or 0) for t in trades if float(t["pnl_usdt"] or 0) == 0]
print(f"avg amount_usdt winners: {sum(amt_w)/len(amt_w):.2f} (n={len(amt_w)})")
print(f"avg amount_usdt losers:  {sum(amt_l)/len(amt_l):.2f} (n={len(amt_l)})")
print(f"avg amount_usdt flats:   {sum(amt_f)/len(amt_f):.2f} (n={len(amt_f)})")
# pnl_pct distribution — per-trade return
pp_w = [float(t["pnl_pct"] or 0) for t in trades if float(t["pnl_usdt"] or 0) > 0]
pp_l = [float(t["pnl_pct"] or 0) for t in trades if float(t["pnl_usdt"] or 0) < 0]
print(f"avg pnl_pct winners: {sum(pp_w)/len(pp_w):+.4f}%")
print(f"avg pnl_pct losers:  {sum(pp_l)/len(pp_l):+.4f}%")
print(f"→ pnl_pct win/loss ratio = {abs(sum(pp_w)/len(pp_w))/(abs(sum(pp_l))/len(pp_l)):.3f}")

# ═══════════════════════ E. MFE/MAE — exit quality ════════════════════════════
print("\n" + "=" * 70)
print("E. MFE/MAE — are we leaving money on the table?")
print("=" * 70)
with_mfe = [t for t in trades if t["mfe_pct"] is not None]
if with_mfe:
    mfe_all = [float(t["mfe_pct"]) for t in with_mfe]
    mae_all = [float(t["mae_pct"]) for t in with_mfe if t["mae_pct"] is not None]
    print(f"trades with MFE: {len(with_mfe)}/{n}")
    print(f"avg MFE: {sum(mfe_all)/len(mfe_all):+.3f}%  max: {max(mfe_all):+.3f}%")
    if mae_all:
        print(f"avg MAE: {sum(mae_all)/len(mae_all):+.3f}%  min: {min(mae_all):+.3f}%")
    # winners captured vs MFE
    cap_w = []
    for t in with_mfe:
        if float(t["pnl_usdt"] or 0) > 0 and t["mfe_pct"]:
            cap_w.append(float(t["pnl_pct"] or 0) / float(t["mfe_pct"]) if float(t["mfe_pct"]) else 0)
    if cap_w:
        print(f"winners: avg pnl_pct/MFE capture ratio: {sum(cap_w)/len(cap_w)*100:.1f}%")
    # how many trades had MFE > 2% but ended flat/negative?
    big_mfe_loss = [t for t in with_mfe if float(t["mfe_pct"] or 0) > 2.0 and float(t["pnl_usdt"] or 0) <= 0]
    print(f"trades with MFE>2% that ended <=0 (winners turned to losers): {len(big_mfe_loss)}, "
          f"combined PnL={sum(float(t['pnl_usdt'] or 0) for t in big_mfe_loss):+.2f}")
    big_mfe_loss_short = [t for t in big_mfe_loss if (t["direction"] or "").upper() == "SHORT"]
    print(f"  of which SHORTs: {len(big_mfe_loss_short)}, PnL={sum(float(t['pnl_usdt'] or 0) for t in big_mfe_loss_short):+.2f}")
else:
    print("NO MFE DATA in window")

# ═══════════════════════ F. LOSING SEGMENT DRILL-DOWN ═════════════════════════
print("\n" + "=" * 70)
print("F. LOSING SEGMENTS — combined cuts")
print("=" * 70)

def seg_report(label, subset):
    ps = [float(t["pnl_usdt"] or 0) for t in subset]
    if not ps:
        print(f"  {label}: NO TRADES")
        return
    nw = sum(1 for p in ps if p > 0)
    nl = sum(1 for p in ps if p < 0)
    nd = nw + nl
    wr = nw / nd if nd else 0
    tp = sum(ps)
    lo, hi = wilson_ci(nw, nd)
    flag = "NEEDS MORE DATA" if len(ps) < 10 else ""
    print(f"  {label:<48} n={len(ps):<4} WR={wr*100:>5.1f}% CI[{lo*100:.1f}-{hi*100:.1f}] PnL={tp:>+8.2f} {flag}")

seg_report("ALL", trades)
seg_report("SHORT only", [t for t in trades if (t["direction"] or "").upper() == "SHORT"])
seg_report("LONG only", [t for t in trades if (t["direction"] or "").upper() == "LONG"])
seg_report("SHORT + NORMAL regime", [t for t in trades if (t["direction"] or "").upper() == "SHORT" and (t["volatility_regime"] or "").upper() == "NORMAL"])
seg_report("SHORT + HIGH regime", [t for t in trades if (t["direction"] or "").upper() == "SHORT" and (t["volatility_regime"] or "").upper() == "HIGH"])
seg_report("SHORT + EXTREME regime", [t for t in trades if (t["direction"] or "").upper() == "SHORT" and (t["volatility_regime"] or "").upper() == "EXTREME"])
seg_report("LONG + NORMAL regime", [t for t in trades if (t["direction"] or "").upper() == "LONG" and (t["volatility_regime"] or "").upper() == "NORMAL"])
seg_report("LONG + HIGH regime", [t for t in trades if (t["direction"] or "").upper() == "LONG" and (t["volatility_regime"] or "").upper() == "HIGH"])
seg_report("LONG + EXTREME regime", [t for t in trades if (t["direction"] or "").upper() == "LONG" and (t["volatility_regime"] or "").upper() == "EXTREME"])
seg_report("Tuesday trades", [t for t in trades if t["open_time"].strftime("%A") == "Tuesday"])
seg_report("02:00-05:59 UTC", [t for t in trades if 2 <= t["open_time"].hour <= 5])
seg_report("ema300_dip family (all dirs)", [t for t in trades if "ema300_dip" in signal_family(t["signal"])])
seg_report("ema300_dip SHORT", [t for t in trades if "ema300_dip" in signal_family(t["signal"]) and (t["direction"] or "").upper() == "SHORT"])
seg_report("atr_sl_hit exits", [t for t in trades if "atr_sl" in (t["exit_reason"] or "").lower()])
seg_report("cut-loser exits", [t for t in trades if "cut-loser" in (t["exit_reason"] or "").lower() or "cl-t1" in (t["exit_reason"] or "").lower()])

# what fraction of cut-loser exits were on trades that had MFE>0 at some point?
cl = [t for t in trades if "cut-loser" in (t["exit_reason"] or "").lower() or "cl-t1" in (t["exit_reason"] or "").lower()]
cl_mfe = [t for t in cl if t["mfe_pct"] is not None]
if cl_mfe:
    cl_win_mfe = sum(1 for t in cl_mfe if float(t["mfe_pct"] or 0) > 0)
    print(f"\ncut-loser exits with MFE>0 (were in profit at some point): {cl_win_mfe}/{len(cl_mfe)}")

# ═══════════════════════ G. FILTER IMPACT — blocked-trade evidence ════════════
print("\n" + "=" * 70)
print("G. FILTER IMPACT — evidence from DB + logs")
print("=" * 70)

# 1. missed_opportunity flag
cur2 = psycopg2.connect(**BRAIN_DB_DICT).cursor()
cur2.execute("""
    SELECT COUNT(*), SUM(pnl_usdt) FROM trades
    WHERE open_time >= %s AND missed_opportunity = true
""", (cutoff,))
mo = cur2.fetchone()
print(f"missed_opportunity=true trades in window: {mo[0]}, sum pnl={mo[1]}")

# 2. signals table? check for a signals table or blocked log table
cur2.execute("""SELECT table_name FROM information_schema.tables WHERE table_schema='public'""")
tables = [r[0] for r in cur2.fetchall()]
print(f"tables: {tables}")

# 3. hotset failures json
for path in ["/var/www/hermes/data/hotset-failures.json", "/var/www/hermes/data/hotset_failures.json"]:
    try:
        with open(path) as fh:
            data = json.load(fh)
        print(f"\n{path}: type={type(data).__name__}, ", end="")
        if isinstance(data, dict):
            print(f"keys={list(data.keys())[:10]}")
            print(json.dumps(data, indent=1)[:2000])
        elif isinstance(data, list):
            print(f"len={len(data)}")
            print(json.dumps(data[:5], indent=1)[:2000])
    except Exception as e:
        print(f"{path}: {e}")

# 4. audit log
import os
for p in ["/var/www/hermes/data/audit.log", "/root/.hermes/logs/audit.log"]:
    if os.path.exists(p):
        sz = os.path.getsize(p)
        print(f"\n{p}: {sz} bytes")
        with open(p, errors="replace") as fh:
            lines = fh.readlines()
        print(f"  lines: {len(lines)}")
        blocked = [l for l in lines if "BLOCKED" in l or "blocked" in l]
        print(f"  lines containing BLOCKED: {len(blocked)}")
        for l in blocked[:20]:
            print("   ", l.rstrip()[:160])

# 5. signal_cooldowns current state
cur2.execute("SELECT token, direction, reason, expires_at FROM signal_cooldowns ORDER BY expires_at DESC LIMIT 20")
print("\nsignal_cooldowns (latest 20):")
for r in cur2.fetchall():
    print(" ", r)
cur2.execute("SELECT token, reason FROM token_blocklist")
print("token_blocklist:", cur2.fetchall())
cur2.close()

# ═══════════════════════ H. RSI-at-entry sanity check ═════════════════════════
print("\n" + "=" * 70)
print("H. RSI AT ENTRY (BANANA lesson — check entry conditions)")
print("=" * 70)
rsi_w = [float(t["entry_rsi_14"]) for t in trades if t["entry_rsi_14"] is not None and float(t["pnl_usdt"] or 0) > 0]
rsi_l = [float(t["entry_rsi_14"]) for t in trades if t["entry_rsi_14"] is not None and float(t["pnl_usdt"] or 0) < 0]
print(f"avg entry RSI winners: {sum(rsi_w)/len(rsi_w):.2f} (n={len(rsi_w)})" if rsi_w else "no RSI winners")
print(f"avg entry RSI losers:  {sum(rsi_l)/len(rsi_l):.2f} (n={len(rsi_l)})" if rsi_l else "no RSI losers")

# RSI buckets x direction
print("\nRSI bucket x direction:")
for direction in ["LONG", "SHORT"]:
    print(f"  {direction}:")
    for lo, hi in [(0, 20), (20, 30), (30, 40), (40, 50), (50, 60), (60, 70), (70, 80), (80, 101)]:
        sub = [t for t in trades if (t["direction"] or "").upper() == direction and t["entry_rsi_14"] is not None
               and lo <= float(t["entry_rsi_14"]) < hi]
        if not sub:
            continue
        ps = [float(t["pnl_usdt"] or 0) for t in sub]
        nw = sum(1 for p in ps if p > 0)
        tp = sum(ps)
        flag = "NEEDS MORE DATA" if len(ps) < 10 else ""
        print(f"    RSI[{lo:>2}-{hi:>2}) n={len(ps):<4} WR={nw/len(ps)*100:>5.1f}% PnL={tp:>+8.2f} {flag}")

# ═══════════════════════ I. Confidence distribution ═══════════════════════════
print("\n" + "=" * 70)
print("I. SIGNAL CONFIDENCE vs OUTCOME")
print("=" * 70)
for lo, hi in [(0, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 101)]:
    sub = [t for t in trades if t["confidence"] is not None and lo <= float(t["confidence"]) < hi]
    if not sub:
        continue
    ps = [float(t["pnl_usdt"] or 0) for t in sub]
    nw = sum(1 for p in ps if p > 0)
    nd = sum(1 for p in ps if p != 0)
    tp = sum(ps)
    lo2, hi2 = wilson_ci(nw, nd)
    flag = "NEEDS MORE DATA" if len(ps) < 10 else ""
    print(f"  conf[{lo:>2}-{hi:>2}) n={len(ps):<4} WR={nw/nd*100 if nd else 0:>5.1f}% CI[{lo2*100:.1f}-{hi2*100:.1f}] PnL={tp:>+8.2f} {flag}")

print("\nDONE")
