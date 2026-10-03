#!/usr/bin/env python3
"""STATISTICIAN pass 3 — exit-engine calibration + blocked-trade counterfactual.

Part 1: exit levels actually realized vs intended thresholds
Part 2: forward-return simulation of BLOCKED signals (Sep29-Oct3 logs vs candles.db)
Part 3: validate the simulation model against ACTUAL executed trades
"""
import gzip
import math
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import psycopg2

sys.path.insert(0, "/root/.hermes/scripts")
from _secrets import BRAIN_DB_DICT  # noqa: E402

conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("SELECT MAX(open_time) FROM trades WHERE open_time IS NOT NULL")
max_ts = cur.fetchone()[0]
cutoff = max_ts - timedelta(days=30)

# ══════════════ PART 1: exit calibration ══════════════
print("=" * 70)
print("PART 1 — EXIT-LEVEL CALIBRATION (pnl_pct actually realized per engine)")
print("=" * 70)

cur.execute("""
    SELECT exit_reason, pnl_pct, pnl_usdt, trade_duration, direction, open_time
    FROM trades
    WHERE open_time >= %s AND pnl_usdt IS NOT NULL AND pnl_pct IS NOT NULL
""", (cutoff,))
rows1 = cur.fetchall()

def engine_of(er):
    er = (er or "").lower()
    if "profit-monster" in er:
        return "PM trail"
    if "cut-loser" in er or "cl-t1" in er:
        return "cut-loser"
    if "atr_sl_hit" in er:
        return "ATR SL"
    if "hard_sl" in er:
        return "hard SL"
    if "hard_max_loss" in er:
        return "hard max-loss"
    if "rr_engine" in er:
        return "RR engine"
    if "atr_trail" in er:
        return "ATR trail"
    if "hard_tp" in er:
        return "hard TP"
    return "other"

by_eng = defaultdict(list)
for er, pp, pu, dur, d, ot in rows1:
    by_eng[engine_of(er)].append((float(pp), float(pu), float(dur or 0), d))

for eng in ["PM trail", "cut-loser", "ATR SL", "hard SL", "hard max-loss", "RR engine", "ATR trail"]:
    ps = by_eng.get(eng, [])
    if not ps:
        continue
    pcts = sorted(p[0] for p in ps)
    durs = [p[2] for p in ps if p[2] > 0]
    n = len(pcts)
    print(f"\n{eng}: n={n}")
    print(f"  pnl_pct: min={pcts[0]:+.2f}%  p10={pcts[n//10]:+.2f}%  median={pcts[n//2]:+.2f}%  "
          f"p90={pcts[-n//10 if n>=10 else -1]:+.2f}%  max={pcts[-1]:+.2f}%")
    if durs:
        ds = sorted(durs)
        print(f"  duration(min): median={ds[len(ds)//2]:.1f}  p90={ds[-len(ds)//10 if len(ds)>=10 else -1]:.1f}")
    # how many cut-loser exits happened WORSE than the -3% hard stop?
    if eng in ("cut-loser", "hard max-loss"):
        worse3 = sum(1 for p in pcts if p < -3.0)
        worse25 = sum(1 for p in pcts if p < -2.5)
        worse15 = sum(1 for p in pcts if p < -1.5)
        print(f"  exits beyond tier ranges: < -1.5%: {worse15} ({worse15/n*100:.0f}%)  "
              f"< -2.5%: {worse25} ({worse25/n*100:.0f}%)  < -3.0%: {worse3} ({worse3/n*100:.0f}%)")

# implied calc_notional per trade
imp = []
for er, pp, pu, dur, d, ot in rows1:
    if pp and abs(float(pp)) > 0.01:
        raw_move = float(pp) / 5.0 / 100  # assume median leverage 5
        if raw_move:
            imp.append(float(pu) / raw_move)
imp.sort()
if imp:
    print(f"\nimplied calc_notional (pnl_usdt/raw_move@lev5): median={imp[len(imp)//2]:.3f}  "
          f"p25={imp[len(imp)//4]:.3f}  p75={imp[-len(imp)//4]:.3f}")
# empirical pnl_usdt per pnl_pct ratio
ratios = []
for er, pp, pu, dur, d, ot in rows1:
    if pp and abs(float(pp)) > 0.05:
        ratios.append(float(pu) / float(pp))
ratios.sort()
ratio_med = ratios[len(ratios)//2] if ratios else 0.03
print(f"empirical USDT per pnl_pct point: median={ratio_med:.4f} (p25={ratios[len(ratios)//4]:.4f}, "
      f"p75={ratios[-len(ratios)//4]:.4f})")

# ══════════════ PART 2: blocked-trade counterfactual ══════════════
print("\n" + "=" * 70)
print("PART 2 — BLOCKED-TRADE COUNTERFACTUAL (pipeline logs Sep29-Oct3 vs candles)")
print("=" * 70)

pat = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\S*\s*\[([A-Z0-9_\-]+)\]\s+"
    r"([A-Za-z0-9/\-]+)\s+(LONG|SHORT)\s+(?:BLOCKED|blocked)\s*(.*)$"
)

events = []  # (ts_str, gate, token, direction, reason)
for path in ["/root/.hermes/logs/pipeline.log",
             "/root/.hermes/logs/pipeline.log.20261003_015254.gz"]:
    try:
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rt", errors="replace") as f:
            for line in f:
                m = pat.match(line.rstrip())
                if m:
                    events.append(m.groups())
    except FileNotFoundError:
        pass

print(f"raw blocked events parsed: {len(events)}")

# dedupe: first event per (token, direction, gate, date)
seen = set()
uniq = []
for ts, gate, token, direction, reason in events:
    key = (token.upper(), direction, gate, ts[:10])
    if key in seen:
        continue
    seen.add(key)
    uniq.append((ts, gate, token.upper(), direction, reason))
print(f"unique (token,dir,gate,day) blocked events: {len(uniq)}")

# candle access
candles = sqlite3.connect("/root/.hermes/data/candles.db", timeout=15)
ccur = candles.cursor()
ccur.execute("SELECT DISTINCT token FROM candles_1m")
candle_tokens = {r[0].upper() for r in ccur.fetchall()}
covered = [e for e in uniq if e[2] in candle_tokens]
print(f"blocked events with candle coverage: {len(covered)}/{len(uniq)}")
missing = Counter(e[2] for e in uniq if e[2] not in candle_tokens)
print(f"tokens without candles (top): {missing.most_common(10)}")

# build per-token time-sorted candle arrays (lazy cache)
cache = {}

def get_candles(token):
    if token in cache:
        return cache[token]
    rows = ccur.execute(
        "SELECT ts, close FROM candles_1m WHERE token=? ORDER BY ts", (token,)
    ).fetchall()
    cache[token] = rows
    return rows

def bisect_ts(rows, ts):
    lo, hi, ans = 0, len(rows) - 1, -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if rows[mid][0] <= ts:
            ans = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return ans

def simulate(rows, t0, direction, hold_min=120):
    """Simulate system exits on forward 1m path. Returns modeled pnl_pct (leveraged-ish,
    expressed as raw % move of price, NOT multiplied by leverage) or None."""
    i = bisect_ts(rows, t0)
    if i < 0 or i >= len(rows) - 5:
        return None, None, None
    entry = rows[i][1]
    if not entry or entry <= 0:
        return None, None, None
    sgn = 1 if direction == "LONG" else -1
    peak = 0.0       # max favorable since entry
    activated = False
    mfe = mae = 0.0
    for j in range(i + 1, min(i + 1 + hold_min, len(rows))):
        fav = (rows[j][1] - entry) / entry * 100 * sgn   # % favorable
        mfe = max(mfe, fav)
        mae = min(mae, fav)
        # hard adverse cut at -1.0% (CL T1 band) — path check first
        if fav <= -1.0:
            return fav, mfe, mae   # cut at current (approx -1.0)
        # PM trail logic
        if fav >= 0.4:
            activated = True
        if activated:
            peak = max(peak, fav)
            if fav <= peak - 0.2 and peak >= 0.4:
                return peak - 0.2, mfe, mae   # trail exit
            if fav >= 2.0:
                return 2.0, mfe, mae          # T2 cap
        if fav >= 3.0:
            return fav, mfe, mae               # runaway winner, take it
    # still open at hold_min — close at current
    i_end = min(i + hold_min, len(rows) - 1)
    fav_end = (rows[i_end][1] - entry) / entry * 100 * sgn
    return fav_end, mfe, mae

gate_stats = defaultdict(lambda: {"n": 0, "wins": 0, "pnls": [], "mfes": [], "maes": []})
no_candle = 0
for ts, gate, token, direction, reason in covered:
    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    t0 = int(dt.timestamp())
    rows = get_candles(token)
    pnl, mfe, mae = simulate(rows, t0, direction)
    if pnl is None:
        no_candle += 1
        continue
    st = gate_stats[gate]
    st["n"] += 1
    st["pnls"].append(pnl)
    st["mfes"].append(mfe)
    st["maes"].append(mae)
    if pnl > 0:
        st["wins"] += 1

print(f"events simulated: {sum(s['n'] for s in gate_stats.values())}  (no-data: {no_candle})")
print(f"\n{'gate':<32}{'n':>5}{'modWR%':>8}{'avg fav%':>10}{'modPnL%':>10}{'modUSDT*':>10}  note")
gate_rows = []
for gate, st in sorted(gate_stats.items(), key=lambda x: -x[1]["n"]):
    n = st["n"]
    wr = st["wins"] / n * 100 if n else 0
    avg = sum(st["pnls"]) / n if n else 0
    tot_pct = sum(st["pnls"])
    # usdt = raw_pct x leverage x ratio_med   (ratio_med = usdt per leveraged-pct point)
    tot_usdt = tot_pct * 5 * ratio_med
    gate_rows.append((gate, n, wr, avg, tot_pct, tot_usdt))
    print(f"{gate:<32}{n:>5}{wr:>7.1f}%{avg:>+9.3f}%{tot_pct:>+9.2f}%{tot_usdt:>+9.2f}  "
          f"MFE avg={sum(st['mfes'])/n:+.2f}% MAE avg={sum(st['maes'])/n:+.2f}%")

total_mod_usdt = sum(g[5] for g in gate_rows)
print(f"\nTOTAL modeled PnL if ALL blocked trades had executed: {total_mod_usdt:+.2f} USDT "
      f"(over {sum(g[1] for g in gate_rows)} unique blocked events, ~5 days)")
print("  *USDT uses median empirical ratio; NOT fee-adjusted; modeled exits only.")

# which blocked tokens are the biggest modeled winners / losers?
per_tok = defaultdict(float)
per_tok_n = Counter()
for ts, gate, token, direction, reason in covered:
    dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    rows = get_candles(token)
    pnl, mfe, mae = simulate(rows, int(dt.timestamp()), direction)
    if pnl is None:
        continue
    per_tok[token] += pnl * ratio_med
    per_tok_n[token] += 1
print("\nTop blocked tokens by modeled PnL (positive = blocking HURT us):")
for tok, v in sorted(per_tok.items(), key=lambda x: -x[1])[:10]:
    print(f"  {tok:<8} modeled={v:+.2f} USDT (n={per_tok_n[tok]} events)")
print("Top blocked tokens by modeled PnL (negative = blocking SAVED us):")
for tok, v in sorted(per_tok.items(), key=lambda x: x[1])[:10]:
    print(f"  {tok:<8} modeled={v:+.2f} USDT (n={per_tok_n[tok]} events)")

# ══════════════ PART 3: model validation on actual trades ══════════════
print("\n" + "=" * 70)
print("PART 3 — MODEL VALIDATION (same sim vs actual executed trades, Sep29-Oct3)")
print("=" * 70)

vcut = max_ts - timedelta(days=5)
cur.execute("""
    SELECT token, direction, open_time, entry_price, pnl_pct, exit_reason
    FROM trades
    WHERE open_time >= %s AND pnl_usdt IS NOT NULL AND entry_price IS NOT NULL
      AND token IS NOT NULL
""", (vcut,))
actual = cur.fetchall()
print(f"actual trades in validation window: {len(actual)}")

matched = 0
bias = []
abs_err = []
act_pnls = []
mod_pnls = []
for token, direction, ot, entry, pnl_pct, er in actual:
    tok = (token or "").upper()
    if tok not in candle_tokens:
        continue
    rows = get_candles(tok)
    t0 = int(ot.timestamp())
    mod, mfe, mae = simulate(rows, t0, (direction or "LONG").upper())
    if mod is None:
        continue
    matched += 1
    act = float(pnl_pct) / 5.0  # de-leverage (lev 5) → raw % for comparability
    act_pnls.append(act)
    mod_pnls.append(mod)
    bias.append(mod - act)
    abs_err.append(abs(mod - act))

print(f"matched trades (candle coverage + sim ok): {matched}")
if matched > 5:
    mean_bias = sum(bias) / len(bias)
    mae_err = sum(abs_err) / len(abs_err)
    act_mean = sum(act_pnls) / len(act_pnls)
    mod_mean = sum(mod_pnls) / len(mod_pnls)
    print(f"actual mean raw-move%:  {act_mean:+.3f}%")
    print(f"modeled mean raw-move%: {mod_mean:+.3f}%")
    print(f"model bias (mod-act):   {mean_bias:+.3f}%   mean abs error: {mae_err:.3f}%")
    # correlation
    n = len(act_pnls)
    ma = sum(act_pnls) / n
    mm = sum(mod_pnls) / n
    cov = sum((a - ma) * (m - mm) for a, m in zip(act_pnls, mod_pnls)) / n
    va = sum((a - ma) ** 2 for a in act_pnls) / n
    vm = sum((m - mm) ** 2 for m in mod_pnls) / n
    corr = cov / math.sqrt(va * vm) if va and vm else 0
    print(f"correlation(actual, modeled): {corr:.3f}")
    print("→ model" + (" is usable for directional conclusions" if abs(mean_bias) < 0.5 and corr > 0.3
                        else " is ROUGH — treat Part 2 numbers as order-of-magnitude only"))

candles.close()
cur.close()
conn.close()
print("\nDONE")
