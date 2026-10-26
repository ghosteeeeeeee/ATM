#!/usr/bin/env python3
"""Exit-ladder candle OOS (escalation #17 continuation) — brain_auditor run #164, 2026-10-26.

Extends analysis/exit_ladder_tat_grid_2026-10-17.py (which covered pump-chain-/bb-squeeze/
pump-chain+) to the families it did NOT cover, and adds the OOS leg that escalation #17 owes.

Mechanism as-coded (position_manager.py): still open at age>=T AND live_pnl (unleveraged %)
< ARM => close. Units verified: pnl_pct in PG is LEVERAGED %, live_pnl is unleveraged price %.
cf$ = amount_usdt * lp/100 (amount_usdt is NOTIONAL). benefit = cf - actual (+= firing helps).

BARS — locked in this docstring BEFORE any result was read:
  b1 ALIVE n >= 20        (alive = held to age T, i.e. the rule could fire on it)
  b2 fired >= 5
  b3 fk%  <= 20% of ALIVE winners
  b4 net  > 0
  b5 OOS: net same sign in BOTH halves (cohort split at its own median open_time)
PASS = b1 AND b2 AND b3 AND b4 AND b5. One-variable discipline: best T reported per family
among PASS cells only.

DENOMINATOR (self-audited same run, 2026-10-26 16:00): a trade that closed BEFORE age T can
never be fired on, so counting it as a possible FK victim dilutes fk% and inflates n — both
anti-conservative. The first cut inherited the Oct-17 grid's whole-cohort denominators and that
is the ONLY thing its single PASS (bb-squeeze T=55, fk 12.0%) survives on; on alive-only it is
fk 46.2% = FAIL. Both are printed; verdict uses ALIVE. Tightening post-data toward the stricter
side, so no loosening risk.

Run:  python3 brain/analysis/exit_ladder_oos_2026-10-26.py [--selfcheck]
"""
import sqlite3
import sys
from datetime import datetime, timezone

import psycopg2

ARM = 0.40  # % unleveraged = PM_TRAIL_ACTIVATE_PCT / TRAILING_ACTIVATION_PCT
TS = (30, 40, 45, 50, 55, 60, 80)

# (family_label, signal_substr, direction)  — none of these were in the Oct-17 grid
FAMILIES = [
    ("bb-bounce-v2-LONG", "bb-bounce-v2-long", "LONG"),
    ("volume-buildup-SHORT", "volume-buildup-", "SHORT"),
    ("r2v2-long3-LONG", "r2v2-long3", "LONG"),
    ("hl-copy-LONG", "hl_copy_trader", "LONG"),
    ("hl-copy-SHORT", "hl_copy_trader", "SHORT"),
    ("bb-squeeze-LONG", "bb-squeeze", "LONG"),  # OOS re-verify of Oct-17 T=55 PASS
]

CDB = "file:/root/.hermes/data/candles.db?mode=ro"


def to_dt(x):
    if isinstance(x, str):
        x = datetime.fromisoformat(x.replace("Z", "+00:00"))
    if x.tzinfo is None:
        x = x.replace(tzinfo=timezone.utc)
    return x


def live_pnl_at(cdb, token, entry, t_min, open_time, direction):
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
    return (entry - r[0]) / entry * 100.0


def score_cohort(cdb, cohort, T, split_ts):
    """Return per-T stats. split_ts (epoch s) separates the two OOS halves.

    Denominators are ALIVE (held to age T): a trade closed before T can never be
    fired on, so it must not count as a possible FK victim or as sample.
    `*_cohort` variants are retained for comparison with the Oct-17 grid only.
    """
    fired = fk = miss = early = 0
    alive_n = winners_alive = winners_cohort = 0
    net = save = cost = 0.0
    net_a = net_b = 0.0
    for (tid, token, signal, direc, entry, pnl_usdt, pnl_pct, amt, lev, ot, ct, xr) in cohort:
        end_u = float(pnl_pct) / float(lev)
        if end_u > 0:
            winners_cohort += 1
        hm = (to_dt(ct) - to_dt(ot)).total_seconds() / 60.0
        if hm < T:
            early += 1
            continue
        alive_n += 1
        if end_u > 0:
            winners_alive += 1
        lp = live_pnl_at(cdb, token, entry, T, ot, direc)
        if lp is None:
            miss += 1
            continue
        if lp < ARM:
            fired += 1
            cf = float(amt) * (lp / 100.0)
            benefit = cf - float(pnl_usdt)
            net += benefit
            if to_dt(ot).timestamp() < split_ts:
                net_a += benefit
            else:
                net_b += benefit
            if end_u > 0:
                fk += 1
                cost += benefit
            else:
                save += benefit
    fk_pct = 100.0 * fk / winners_alive if winners_alive else 0.0
    fk_pct_cohort = 100.0 * fk / winners_cohort if winners_cohort else 0.0
    return dict(cohort=len(cohort), alive=alive_n, early=early, miss=miss, fired=fired, fk=fk,
                winners=winners_alive, winners_cohort=winners_cohort,
                fk_pct=round(fk_pct, 1), fk_pct_cohort=round(fk_pct_cohort, 1),
                net=round(net, 2), save=round(save, 2), cost=round(cost, 2),
                net_a=round(net_a, 2), net_b=round(net_b, 2))


def verdict(r, n_min=20):
    if r["alive"] < n_min:
        return "SKIP-n<20"
    if r["fired"] < 5:
        return "INSUFFICIENT"
    b3 = r["fk_pct"] <= 20.0
    b4 = r["net"] > 0
    b5 = (r["net_a"] > 0) == (r["net_b"] > 0) and r["net_a"] != 0 and r["net_b"] != 0
    return "PASS" if (b3 and b4 and b5) else "FAIL"


def run():
    conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
    cur = conn.cursor()
    cur.execute("""
        SELECT id, token, signal, direction, entry_price, pnl_usdt, pnl_pct, amount_usdt,
               leverage, open_time, close_time, exit_reason
        FROM trades
        WHERE status='closed' AND close_time > NOW() - INTERVAL '30 days'
          AND amount_usdt IS NOT NULL AND leverage IS NOT NULL AND leverage > 0
    """)
    rows = cur.fetchall()
    conn.close()
    cdb = sqlite3.connect(CDB, uri=True)

    print(f"30d trades loaded: {len(rows)}")
    print("BARS: ALIVE n>=20, fired>=5, fk<=20% of ALIVE winners, net>0, OOS same-sign both halves\n")
    hdr = (f"{'family':22} {'T':>4} {'n':>4} {'alive':>5} {'<T':>4} {'noC':>4} {'fire':>5} "
           f"{'FKw':>4} {'winN':>5} {'fk%':>6} {'fk%coh':>7} {'NET$':>7} {'halfA':>7} {'halfB':>7}  verdict")
    print(hdr)
    best = {}
    for fam, sig, direc in FAMILIES:
        cohort = [r for r in rows
                  if sig in (r[2] or "").lower() and (r[3] or "").upper() == direc]
        if not cohort:
            print(f"{fam:22} (no trades in 30d)")
            continue
        times = sorted(to_dt(r[9]).timestamp() for r in cohort)
        split_ts = times[len(times) // 2]
        for T in TS:
            s = score_cohort(cdb, cohort, T, split_ts)
            v = verdict(s)
            print(f"{fam:22} {T:>4} {s['cohort']:>4} {s['alive']:>5} {s['early']:>4} {s['miss']:>4} "
                  f"{s['fired']:>5} {s['fk']:>4} {s['winners']:>5} {s['fk_pct']:>6.1f} "
                  f"{s['fk_pct_cohort']:>7.1f} {s['net']:>+7.2f} {s['net_a']:>+7.2f} {s['net_b']:>+7.2f}  {v}")
            if v == "PASS" and (fam not in best or s["net"] > best[fam]["net"]):
                best[fam] = dict(s, T=T)
        print()
    cdb.close()

    print("=== BEST T PER FAMILY (PASS only) ===")
    if not best:
        print("  NO FAMILY PASSES — no new arm-timeout ships from this run")
    for fam, b in best.items():
        print(f"  {fam}: T={b['T']}m net=${b['net']:+.2f} fk={b['fk_pct']}% "
              f"halves {b['net_a']:+.2f}/{b['net_b']:+.2f}")
    return best


def selfcheck():
    cdb = sqlite3.connect(CDB, uri=True)
    # 1. LONG sign convention against a real candle
    tok, ts, _, _, _, cl = cdb.execute(
        "SELECT token, ts, open, high, low, close FROM candles_1m ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    ot = datetime.fromtimestamp(ts - 30 * 60, tz=timezone.utc)
    lp = live_pnl_at(cdb, tok, cl * 1.01, 30, ot, "LONG")
    assert lp is not None and abs(lp - (cl / (cl * 1.01) - 1) * 100) < 1e-6, "LONG sign"
    lps = live_pnl_at(cdb, tok, cl * 1.01, 30, ot, "SHORT")
    assert abs(lps + lp) < 1e-6, "SHORT is the mirror of LONG"
    # 2. benefit units: cf$ = amount * lp/100, benefit = cf - actual
    amt, lp2, actual = 100.0, -0.5, -1.0
    assert round(amt * lp2 / 100.0 - actual, 6) == 0.5, "benefit arithmetic"
    # 3. fk% = fk / ALIVE winners (a trade closed before T can never be fired on)
    assert round(100.0 * 3 / 12, 1) == 25.0, "fk pct"
    # 4. verdict bars: fk<=20 AND net>0 AND halves same sign AND alive n>=20
    assert verdict(dict(alive=25, fired=9, fk=2, winners=10, fk_pct=20.0,
                        net=1.0, net_a=0.5, net_b=0.5)) == "PASS"
    assert verdict(dict(alive=25, fired=9, fk=3, winners=10, fk_pct=30.0,
                        net=1.0, net_a=0.5, net_b=0.5)) == "FAIL"
    assert verdict(dict(alive=25, fired=9, fk=2, winners=10, fk_pct=20.0,
                        net=1.0, net_a=1.0, net_b=-0.5)) == "FAIL"
    # 5. denominator sensitivity: a big cohort with few alive trades must not claim n>=20
    assert verdict(dict(alive=19, fired=9, fk=2, winners=10, fk_pct=20.0,
                        net=1.0, net_a=0.5, net_b=0.5)) == "SKIP-n<20"
    assert verdict(dict(cohort=65, alive=19, fired=9, fk=2, winners=10, fk_pct=20.0,
                        fk_pct_cohort=12.0, net=1.0, net_a=0.5, net_b=0.5)) == "SKIP-n<20", \
        "cohort-size must never satisfy b1"
    cdb.close()
    print("SELF-CHECK PASS (5 assertions: sign convention, units, fk%, verdict bars, alive-denominator)")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        selfcheck()
    else:
        run()
