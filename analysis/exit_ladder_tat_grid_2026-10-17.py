#!/usr/bin/env python3
"""Exit-ladder P0: signal-scoped trail-arm-timeout candle OOS grid (brain_auditor 2026-10-17 14:30Z).

The8x-requested exit-ladder backtest, run by brain_auditor after self_learner undelivered.
Signal-scoped ONLY (universal MFE-CUT dead per same-day verdict). Mechanism as-coded
(position_manager.py:3565-3595): still open at age>=T AND live_pnl (unleveraged %) < 0.40 => close.

Units (verified): pnl_pct in PG is LEVERAGED %. live_pnl is unleveraged price %.
pnl_usdt = amount_usdt * unleveraged_move/100 (amount is NOTIONAL; lev is margin metadata).
cf$ = amount_usdt * lp/100. benefit = cf - actual (+ = firing helps).
Winner = end_u > 0 (matches 11:46 verdict methodology). Bar: fk<=20% of cohort winners AND net>0.
"""
import sqlite3
from datetime import datetime, timezone
import psycopg2

ARM = 0.40  # % unleveraged, = PM_TRAIL_ACTIVATE_PCT

# (label, signal_substr, direction, T_minutes)
COHORTS = []
for t in (30, 40, 45, 50, 55, 60, 80):
    COHORTS.append((f"pc-minus-SHORT-T{t}", "pump-chain-", "SHORT", t))
for t in (40, 45, 50, 55, 60):
    COHORTS.append((f"bb-squeeze-LONG-T{t}", "bb-squeeze", "LONG", t))
for t in (50, 55, 60):
    COHORTS.append((f"pc-plus-LONG-T{t}", "pump-chain+", "LONG", t))

conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
cur = conn.cursor()
cur.execute("""
    SELECT id, token, signal, direction, entry_price, pnl_usdt, pnl_pct, amount_usdt, leverage,
           open_time, close_time, exit_reason
    FROM trades
    WHERE status='closed' AND close_time > NOW() - INTERVAL '30 days'
      AND amount_usdt IS NOT NULL AND leverage IS NOT NULL AND leverage > 0
""")
rows = cur.fetchall()
conn.close()

cdb = sqlite3.connect("file:/root/.hermes/data/candles.db?mode=ro", uri=True)

def to_dt(x):
    if isinstance(x, str):
        x = datetime.fromisoformat(x.replace("Z", "+00:00"))
    if x.tzinfo is None:
        x = x.replace(tzinfo=timezone.utc)
    return x

def live_pnl_at(token, entry, t_min, open_time, direction):
    target = int(to_dt(open_time).timestamp()) + t_min * 60
    r = cdb.execute(
        "SELECT close FROM candles_1m WHERE token=? AND ts<=? ORDER BY ts DESC LIMIT 1",
        (token, target),
    ).fetchone()
    if r is None:
        return None
    entry = float(entry)
    if direction == "LONG":
        return (r[0] - entry) / entry * 100.0
    return (entry - r[0]) / entry * 100.0  # SHORT: price drop = positive pnl

results = []
for name, sig, direction, T in COHORTS:
    cohort = [r for r in rows
              if sig in (r[2] or "").lower() and (r[3] or "").upper() == direction]
    fired = fk = miss = early = 0
    net_usdt = save_usdt = cost_usdt = 0.0
    winners_n = 0
    fk_details = []
    for (tid, token, signal, direc, entry, pnl_usdt, pnl_pct, amt, lev, ot, ct, xr) in cohort:
        end_u = float(pnl_pct) / float(lev)
        if end_u > 0:
            winners_n += 1
        hm = (to_dt(ct) - to_dt(ot)).total_seconds() / 60.0
        if hm < T:
            early += 1
            continue
        lp = live_pnl_at(token, entry, T, ot, direction)
        if lp is None:
            miss += 1
            continue
        if lp < ARM:
            fired += 1
            cf = float(amt) * (lp / 100.0)
            benefit = cf - float(pnl_usdt)
            net_usdt += benefit
            if end_u > 0:
                fk += 1
                cost_usdt += benefit
                fk_details.append((token, f"T{lp:+.2f}%", f"end{end_u:+.2f}%", f"ben{benefit:+.2f}", xr))
            else:
                save_usdt += benefit
    alive_scored = (len(cohort) - early) - miss
    fk_pct = 100.0 * fk / winners_n if winners_n else 0.0
    verdict = "PASS" if (fk_pct <= 20.0 and net_usdt > 0 and fired >= 5) else (
        "INSUFFICIENT" if fired < 5 else "FAIL")
    results.append(dict(name=name, T=T, cohort=len(cohort), early=early, miss=miss,
                        fired=fired, fk=fk, winners=winners_n, fk_pct=round(fk_pct, 1),
                        net=round(net_usdt, 2), save=round(save_usdt, 2),
                        cost=round(cost_usdt, 2), verdict=verdict, fk_details=fk_details))

print(f"30d trades loaded: {len(rows)}\n")
print(f"{'cohort':24} {'cohort':>6} {'<T':>5} {'noC':>4} {'fire':>5} {'FKw':>4} {'winN':>5} {'fk%':>6} {'NET$':>7} {'save$':>7} {'cost$':>7}  verdict")
for r in results:
    print(f"{r['name']:24} {r['cohort']:>6} {r['early']:>5} {r['miss']:>4} {r['fired']:>5} "
          f"{r['fk']:>4} {r['winners']:>5} {r['fk_pct']:>6.1f} {r['net']:>+7.2f} "
          f"{r['save']:>+7.2f} {r['cost']:>+7.2f}  {r['verdict']}")

print("\n=== PASS cells: FK detail (top by |benefit|) ===")
for r in results:
    if r["verdict"] == "PASS":
        print(f"\n{r['name']}: {r['fk']} FK winners of {r['winners']} (fk {r['fk_pct']}%)")
        for d in sorted(r["fk_details"], key=lambda x: abs(float(x[3][3:])), reverse=True)[:8]:
            print(f"  {d}")

# One-variable discipline: within each signal family, show best-T by net among PASS
print("\n=== BEST T PER FAMILY (PASS only) ===")
for fam in ("pc-minus-SHORT", "bb-squeeze-LONG", "pc-plus-LONG"):
    passes = [r for r in results if r["name"].startswith(fam) and r["verdict"] == "PASS"]
    if passes:
        best = max(passes, key=lambda r: r["net"])
        print(f"  {fam}: T={best['T']}m net=${best['net']:+.2f} fk={best['fk_pct']}% "
              f"(baseline/live: {'60m' if 'squeeze' in fam else '45m' if 'pc-plus' in fam else 'NONE'})")
    else:
        print(f"  {fam}: NO PASS — keep current state (live TAT or no mechanism)")
