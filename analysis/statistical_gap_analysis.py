#!/usr/bin/env python3
"""STATISTICIAN — 30-day statistical gap analysis of brain.trades.

Outputs:
  - Overall performance + Wilson CIs + bootstrap mean CI
  - Signal-level PnL (flag n<10 NEEDS MORE DATA)
  - Direction (LONG vs SHORT)
  - Volatility regime
  - Time-of-day / day-of-week
  - Exit-reason breakdown
  - Edge detection (two-proportion tests vs breakeven, sign test)
"""
import math
import sys
import random
from collections import defaultdict
from datetime import datetime, timedelta

import psycopg2

sys.path.insert(0, "/root/.hermes/scripts")
from _secrets import BRAIN_DB_DICT  # noqa: E402

# ─────────────────────────────── statistics helpers ───────────────────────────
def wilson_ci(wins, n, z=1.96):
    """Wilson score interval for a proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def bootstrap_mean_ci(values, n_boot=5000, alpha=0.05, seed=42):
    """Percentile bootstrap CI for the mean."""
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_boot):
        s = sum(values[rng.randrange(n)] for _ in range(n))
        means.append(s / n)
    means.sort()
    lo = means[int(alpha / 2 * n_boot)]
    hi = means[int((1 - alpha / 2) * n_boot)]
    return (lo, hi)


def two_prop_z_test(w1, n1, w2, n2):
    """Two-proportion z-test. Returns (z, p_two_sided)."""
    if n1 == 0 or n2 == 0:
        return (0.0, 1.0)
    p1, p2 = w1 / n1, w2 / n2
    p = (w1 + w2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return (0.0, 1.0)
    z = (p1 - p2) / se
    # two-sided p via normal approximation
    p_val = 2 * (1 - _norm_cdf(abs(z)))
    return (z, p_val)


def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def sign_test(pnls):
    """Exact binomial sign test on PnL != 0. Returns (wins, losses, p)."""
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    n = wins + losses
    if n == 0:
        return (0, 0, 1.0)
    # two-sided exact binomial
    p = 0.0
    for k in range(0, n + 1):
        prob = math.comb(n, k) * (0.5 ** n)
        if prob <= math.comb(n, wins) * (0.5 ** n) + 1e-12:
            p += prob
    return (wins, losses, min(1.0, 2 * p))


def fmt_pnl(x):
    return f"{x:+.2f}"


# ─────────────────────────────── data loading ─────────────────────────────────
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()

cur.execute("SELECT MAX(open_time) FROM trades WHERE open_time IS NOT NULL")
max_ts = cur.fetchone()[0]
cutoff = max_ts - timedelta(days=30)
print(f"Data window: {cutoff}  ->  {max_ts}  (30 days back from latest open_time)")

cur.execute("""
    SELECT id, token, direction, signal, strategy, pnl_usdt, pnl_pct,
           amount_usdt, status, open_time, close_time, exit_reason,
           volatility_regime, paper, confidence, leverage, fees,
           entry_rsi_14, mfe_pct, mae_pct, _signal_metadata, exit_conditions
    FROM trades
    WHERE open_time >= %s
      AND status IN ('CLOSED', 'closed', 'TP', 'SL', 'EXPIRED', 'MANUAL')
      AND pnl_usdt IS NOT NULL
    ORDER BY open_time
""", (cutoff,))

COLS = [d[0] for d in cur.description]
rows = [dict(zip(COLS, r)) for r in cur.fetchall()]
cur.close()
conn.close()

print(f"Closed trades in window: {len(rows)}")
if not rows:
    print("NO DATA — aborting")
    sys.exit(1)

# filter to only real PnL rows (pnl not None)
trades = [r for r in rows if r["pnl_usdt"] is not None]
n_all = len(trades)
pnls = [float(r["pnl_usdt"]) for r in trades]
total_pnl = sum(pnls)
wins = [p for p in pnls if p > 0]
losses = [p for p in pnls if p < 0]
flats = [p for p in pnls if p == 0]
n_win, n_loss, n_flat = len(wins), len(losses), len(flats)
n_dec = n_win + n_loss  # non-flat for win-rate
win_rate = n_win / n_dec if n_dec else 0.0
avg_win = sum(wins) / n_win if n_win else 0.0
avg_loss = sum(losses) / n_loss if n_loss else 0.0
avg_trade = total_pnl / n_all
expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss if n_dec else 0.0

ci_lo, ci_hi = wilson_ci(n_win, n_dec)
b_lo, b_hi = bootstrap_mean_ci(pnls)

print("\n" + "=" * 70)
print("SECTION 1 — OVERALL PERFORMANCE (30 days)")
print("=" * 70)
print(f"Total trades (closed):          {n_all}")
print(f"  wins: {n_win}  losses: {n_loss}  flat: {n_flat}")
print(f"Total PnL:                      {fmt_pnl(total_pnl)} USDT")
print(f"Win rate (excl. flat):          {win_rate*100:.2f}%  ({n_win}/{n_dec})")
print(f"95% Wilson CI for win rate:     [{ci_lo*100:.2f}%, {ci_hi*100:.2f}%]")
print(f"Avg win:                        {fmt_pnl(avg_win)}")
print(f"Avg loss:                       {fmt_pnl(avg_loss)}")
print(f"Avg trade (all):                {avg_trade:+.4f}")
print(f"Expectancy (WR*avgW+(1-WR)*avgL): {expectancy:+.4f}")
print(f"Bootstrap 95% CI mean PnL:      [{fmt_pnl(b_lo)} .. {fmt_pnl(b_hi)}]")
print(f"Profit factor:                  ", end="")
gross_win = sum(wins)
gross_loss = abs(sum(losses))
print(f"{gross_win/gross_loss:.3f}" if gross_loss else "inf (no losses)")
print(f"Total traded notional (sum amount_usdt): {sum(float(r['amount_usdt'] or 0) for r in trades):.2f}")
# win rate is significantly different from coin flip?
z_coin, p_coin = two_prop_z_test(n_win, n_dec, 1, 2)  # dummy
_, p_vs50 = two_prop_z_test(n_win, n_dec, n_dec // 2, n_dec) if n_dec else (0, 1)
# simpler: binomial test vs 50%
p_sign, _, p_sign_p = sign_test(pnls)
print(f"Sign test (win vs loss count):  {p_sign}W / {p_sign_p*100:.2f}% of trades are flat; "
      f"p={sign_test([p for p in pnls if p!=0])[2]:.4f} vs 50%")
# how far is win rate from breakeven given avg win/loss?
breakeven_wr = avg_loss / (avg_win + avg_loss) if (avg_win + avg_loss) else 0
print(f"Breakeven win rate needed:      {breakeven_wr*100:.2f}%  (gap: {(win_rate-breakeven_wr)*100:+.2f} pp)")

# ── per-day PnL for trend
by_day = defaultdict(float)
for r in trades:
    d = r["open_time"].date()
    by_day[d] += float(r["pnl_usdt"])
print("\nDaily PnL (last 30 days):")
cum = 0.0
for d in sorted(by_day):
    cum += by_day[d]
    bar = "#" * int(min(40, abs(by_day[d]) * 2)) if by_day[d] >= 0 else "-" * int(min(40, abs(by_day[d]) * 2))
    print(f"  {d}  {fmt_pnl(by_day[d]):>8}  cum={fmt_pnl(cum):>9}  {bar}")

# ─────────────────────────────── SECTION 2 — signals ──────────────────────────
print("\n" + "=" * 70)
print("SECTION 2 — SIGNAL PERFORMANCE")
print("=" * 70)

by_sig = defaultdict(list)
for r in trades:
    sig = (r["signal"] or "").strip()
    if not sig:
        sig = f"(none)/strategy={r['strategy']}"
    by_sig[sig].append(float(r["pnl_usdt"]))

sig_stats = []
for sig, ps in by_sig.items():
    nw = sum(1 for p in ps if p > 0)
    nl = sum(1 for p in ps if p < 0)
    nd = nw + nl
    wr = nw / nd if nd else 0.0
    tp = sum(ps)
    lo, hi = wilson_ci(nw, nd)
    sig_stats.append((sig, len(ps), nw, nl, wr, tp, lo, hi,
                      sum(ps) / len(ps) if ps else 0.0))

sig_stats.sort(key=lambda x: -x[5])  # by total PnL
print(f"{'signal':<34} {'n':>4} {'W':>3} {'L':>3} {'WR%':>6} {'PnL':>9} {'avg':>7}  95%CI  flag")
for sig, n, nw, nl, wr, tp, lo, hi, avg in sig_stats:
    flag = ""
    if n < 10:
        flag = "NEEDS MORE DATA"
    elif n < 30:
        flag = "low-n"
    if lo > 0.5:
        flag = (flag + " ").strip() + " <WR sig>"
    elif hi < 0.5:
        flag = (flag + " ").strip() + " <WR sig below 50>"
    print(f"{sig[:34]:<34} {n:>4} {nw:>3} {nl:>3} {wr*100:>5.1f}% {fmt_pnl(tp):>9} {avg:>+7.3f}  "
          f"[{lo*100:.0f}-{hi*100:.0f}]  {flag}")

n_sig10 = sum(1 for s in sig_stats if s[1] >= 10)
n_sig10_pos = sum(1 for s in sig_stats if s[1] >= 10 and s[5] > 0)
n_sig10_neg = sum(1 for s in sig_stats if s[1] >= 10 and s[5] < 0)
print(f"\nSignals with n>=10: {n_sig10}  | positive PnL: {n_sig10_pos}  | negative PnL: {n_sig10_neg}")

# ─────────────────────────────── SECTION 3 — direction ────────────────────────
print("\n" + "=" * 70)
print("SECTION 3 — DIRECTION ANALYSIS")
print("=" * 70)

by_dir = defaultdict(list)
for r in trades:
    d = (r["direction"] or "UNKNOWN").upper()
    by_dir[d].append(float(r["pnl_usdt"]))

dir_rows = []
for d, ps in sorted(by_dir.items()):
    nw = sum(1 for p in ps if p > 0)
    nl = sum(1 for p in ps if p < 0)
    nd = nw + nl
    wr = nw / nd if nd else 0.0
    lo, hi = wilson_ci(nw, nd)
    tp = sum(ps)
    b1, b2 = bootstrap_mean_ci(ps)
    dir_rows.append((d, len(ps), nw, nl, wr, tp, lo, hi, b1, b2))
    print(f"{d:<8} n={len(ps):<5} W={nw:<4} L={nl:<4} WR={wr*100:>5.1f}%  CI[{lo*100:.1f}-{hi*100:.1f}]  "
          f"PnL={fmt_pnl(tp):>9}  bootCI[{fmt_pnl(b1)}..{fmt_pnl(b2)}]  avg={tp/len(ps):+.4f}")

if len(dir_rows) >= 2:
    a, b = dir_rows[0], dir_rows[1]
    z, p = two_prop_z_test(a[2], a[2] + a[3], b[2], b[2] + b[3])
    print(f"\nWR difference {a[0]} vs {b[0]}: z={z:.3f}, p={p:.4f} "
          f"{'SIGNIFICANT' if p < 0.05 else 'not significant'} at 95%")

# ─────────────────────────────── SECTION 4 — regime ───────────────────────────
print("\n" + "=" * 70)
print("SECTION 4 — VOLATILITY REGIME ANALYSIS")
print("=" * 70)

by_reg = defaultdict(list)
for r in trades:
    reg = (r["volatility_regime"] or "UNKNOWN").upper()
    by_reg[reg].append(float(r["pnl_usdt"]))

for reg, ps in sorted(by_reg.items(), key=lambda x: -sum(x[1])):
    nw = sum(1 for p in ps if p > 0)
    nl = sum(1 for p in ps if p < 0)
    nd = nw + nl
    wr = nw / nd if nd else 0.0
    lo, hi = wilson_ci(nw, nd)
    tp = sum(ps)
    flag = "NEEDS MORE DATA" if len(ps) < 10 else ("low-n" if len(ps) < 30 else "")
    print(f"{reg:<10} n={len(ps):<5} W={nw:<4} L={nl:<4} WR={wr*100:>5.1f}%  CI[{lo*100:.1f}-{hi*100:.1f}]  "
          f"PnL={fmt_pnl(tp):>9}  avg={tp/len(ps):+.4f}  {flag}")

# regime x direction
print("\nRegime x Direction PnL:")
rd = defaultdict(list)
for r in trades:
    rd[((r["volatility_regime"] or "?").upper(), (r["direction"] or "?").upper())].append(float(r["pnl_usdt"]))
for (reg, d), ps in sorted(rd.items()):
    nw = sum(1 for p in ps if p > 0)
    flag = "NEEDS MORE DATA" if len(ps) < 10 else ""
    print(f"  {reg:<10} {d:<6} n={len(ps):<4} WR={nw/len(ps)*100 if ps else 0:>5.1f}%  PnL={fmt_pnl(sum(ps)):>8}  {flag}")

# ─────────────────────────────── SECTION 5 — exit reason ──────────────────────
print("\n" + "=" * 70)
print("SECTION 5 — EXIT REASON BREAKDOWN")
print("=" * 70)

by_exit = defaultdict(list)
for r in trades:
    ex = (r["exit_reason"] or r["exit_conditions"] or "UNKNOWN")
    if isinstance(ex, str) and len(ex) > 40:
        ex = ex[:40]
    by_exit[str(ex)].append(float(r["pnl_usdt"]))

for ex, ps in sorted(by_exit.items(), key=lambda x: -abs(sum(x[1])))[:20]:
    nw = sum(1 for p in ps if p > 0)
    tp = sum(ps)
    flag = "NEEDS MORE DATA" if len(ps) < 10 else ""
    print(f"  {ex:<40} n={len(ps):<4} WR={nw/len(ps)*100 if ps else 0:>5.1f}%  PnL={fmt_pnl(tp):>8}  {flag}")

# ─────────────────────────────── SECTION 6 — time ─────────────────────────────
print("\n" + "=" * 70)
print("SECTION 6 — TIME ANALYSIS (UTC)")
print("=" * 70)

by_hour = defaultdict(list)
by_dow = defaultdict(list)
for r in trades:
    t = r["open_time"]
    by_hour[t.hour].append(float(r["pnl_usdt"]))
    by_dow[t.strftime("%A")].append(float(r["pnl_usdt"]))

print("By hour (UTC):")
for h in range(24):
    ps = by_hour.get(h, [])
    if not ps:
        continue
    nw = sum(1 for p in ps if p > 0)
    tp = sum(ps)
    flag = "NEEDS MORE DATA" if len(ps) < 10 else ""
    print(f"  {h:02d}:00  n={len(ps):<4} WR={nw/len(ps)*100:>5.1f}%  PnL={fmt_pnl(tp):>8}  {flag}")

print("\nBy day of week (UTC):")
dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
for d in dow_order:
    ps = by_dow.get(d, [])
    if not ps:
        continue
    nw = sum(1 for p in ps if p > 0)
    tp = sum(ps)
    flag = "NEEDS MORE DATA" if len(ps) < 10 else ""
    print(f"  {d:<10} n={len(ps):<4} WR={nw/len(ps)*100:>5.1f}%  PnL={fmt_pnl(tp):>8}  {flag}")

# ─────────────────────────────── SECTION 7 — edge detection ───────────────────
print("\n" + "=" * 70)
print("SECTION 7 — EDGE DETECTION")
print("=" * 70)

nw_all, nl_all, p_sign = sign_test(pnls)
print(f"Sign test on all {n_all} trades (PnL>0 vs PnL<0): {nw_all}W/{nl_all}L, p={p_sign:.4f}")
print(f"  -> {'SIGNIFICANT' if p_sign < 0.05 else 'NOT significant'} vs coin-flip at 95%")

print(f"\nMean PnL CI excludes zero?  bootstrap [{fmt_pnl(b_lo)} .. {fmt_pnl(b_hi)}]: "
      f"{'YES — statistically significant mean PnL' if (b_lo > 0 or b_hi < 0) else 'NO — mean PnL CI includes zero'}")

# best/worst signals with n>=10 and their significance vs breakeven
print("\nTop signals by PnL (n>=10), tested vs breakeven WR:")
print(f"{'signal':<34} {'n':>4} {'WR%':>6} {'BE%':>6} {'PnL':>8} {'p(WR<BE)':>9} verdict")
for sig, n, nw, nl, wr, tp, lo, hi, avg in sig_stats:
    if n < 10:
        continue
    ps = by_sig[sig]
    # breakeven WR for this signal
    sw = [p for p in ps if p > 0]
    sl = [p for p in ps if p < 0]
    aw = sum(sw) / len(sw) if sw else 0
    al = abs(sum(sl)) / len(sl) if sl else 0
    be = al / (aw + al) if (aw + al) else 0
    # z-test observed WR vs breakeven (if be<1)
    if 0 < be < 1 and (nw + nl) > 0:
        # one-sample prop test
        p_pool = be
        se = math.sqrt(p_pool * (1 - p_pool) / (nw + nl))
        z = (wr - p_pool) / se if se else 0
        p_val = 2 * (1 - _norm_cdf(abs(z)))
    else:
        p_val = 1.0
    verdict = ""
    if n < 30:
        verdict = "low-n, INCONCLUSIVE"
    elif p_val < 0.05 and tp > 0:
        verdict = "SIGNIFICANT edge"
    elif p_val < 0.05 and tp < 0:
        verdict = "SIGNIFICANT loser"
    else:
        verdict = "inconclusive"
    print(f"{sig[:34]:<34} {n:>4} {wr*100:>5.1f}% {be*100:>5.1f}% {fmt_pnl(tp):>8} {p_val:>9.4f} {verdict}")

# ─────────────────────────────── SECTION 8 — costs ────────────────────────────
print("\n" + "=" * 70)
print("SECTION 8 — FEES / COST IMPACT")
print("=" * 70)
fee_sum = 0.0
fee_count = 0
for r in trades:
    f = r.get("fees")
    if f:
        try:
            fee_sum += abs(float(f))
            fee_count += 1
        except (TypeError, ValueError):
            pass
print(f"Trades with numeric fee field: {fee_count}, sum abs(fees) = {fee_sum:.2f}")

# ─────────────────────────────── SECTION 9 — paper vs live ────────────────────
print("\n" + "=" * 70)
print("SECTION 9 — PAPER vs LIVE")
print("=" * 70)
by_paper = defaultdict(list)
for r in trades:
    by_paper["PAPER" if r["paper"] else "LIVE"].append(float(r["pnl_usdt"]))
for k, ps in by_paper.items():
    nw = sum(1 for p in ps if p > 0)
    tp = sum(ps)
    flag = "NEEDS MORE DATA" if len(ps) < 10 else ""
    print(f"  {k:<7} n={len(ps):<5} WR={nw/len(ps)*100 if ps else 0:>5.1f}%  PnL={fmt_pnl(tp):>9}  {flag}")

# ─────────────────────────────── SECTION 10 — leverage ────────────────────────
print("\n" + "=" * 70)
print("SECTION 10 — LEVERAGE BREAKDOWN")
print("=" * 70)
by_lev = defaultdict(list)
for r in trades:
    by_lev[str(r["leverage"] or "?")].append(float(r["pnl_usdt"]))
for lev, ps in sorted(by_lev.items(), key=lambda x: -len(x[1])):
    nw = sum(1 for p in ps if p > 0)
    tp = sum(ps)
    flag = "NEEDS MORE DATA" if len(ps) < 10 else ""
    print(f"  lev={lev:<5} n={len(ps):<5} WR={nw/len(ps)*100 if ps else 0:>5.1f}%  PnL={fmt_pnl(tp):>9}  {flag}")

print("\n" + "=" * 70)
print("END OF ANALYSIS")
print("=" * 70)
