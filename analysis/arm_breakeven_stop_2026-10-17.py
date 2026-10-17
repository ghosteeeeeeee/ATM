#!/usr/bin/env python3
"""Breakeven-stop-after-trail-arm candle backtest (brain_auditor 2026-10-17 18:45Z).

Creative idea from 12:20 run: EXTREME armed-then-reverse cohort (24T/7d, MFE 0.82
gave back to -1.77% acct) is distinct from never-armed chop; trail floor is wide
(D3 trail floor -0.60% price), so armed trades can round-trip to hard losses.
Mechanism tested: once live_pnl (unleveraged %) touches +0.40 (= PM_TRAIL_ACTIVATE_PCT),
if it ever returns to <= 0.00, counterfactual exit AT BREAKEVEN (cf$ = 0).
Trades that never arm, or never round-trip, keep actual outcome.

Units per exit-ladder methodology: pnl_pct in PG is LEVERAGED; live_pnl is unleveraged
price %; cf$ = amount_usdt * lp/100 (amount is NOTIONAL). Winner = end_u > 0.
Bar: fk <= 20% of ARMED winners, net > 0, fired >= 5. Fees ignored (same as grid).
"""
import sqlite3
from datetime import datetime, timezone
import psycopg2

ARM = 0.40   # % unleveraged, = PM_TRAIL_ACTIVATE_PCT
BE = 0.00    # breakeven exit level (unleveraged %)
MAX_WALK_MIN = 24 * 60

conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
cur = conn.cursor()
cur.execute("""
    SELECT id, token, signal, direction, entry_price, pnl_usdt, pnl_pct, amount_usdt, leverage,
           open_time, close_time, exit_reason, volatility_regime
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


def path_outcome(token, entry, direction, ot, ct):
    """Walk 1m path. Return (armed, be_hit, arm_ts, be_ts, miss)."""
    t0 = int(to_dt(ot).timestamp())
    t1 = min(int(to_dt(ct).timestamp()), t0 + MAX_WALK_MIN * 60)
    cands = cdb.execute(
        "SELECT ts, close FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ORDER BY ts",
        (token, t0, t1),
    ).fetchall()
    if not cands:
        return None, None, None, None, True
    entry = float(entry)
    armed = False
    arm_ts = None
    for ts, close in cands:
        lp = ((close - entry) / entry * 100.0) if direction == "LONG" else ((entry - close) / entry * 100.0)
        if not armed and lp >= ARM:
            armed = True
            arm_ts = ts
            continue
        if armed and lp <= BE:
            return True, True, arm_ts, ts, False
    return armed, False, arm_ts, None, False


def evaluate(cohort, label):
    n = miss = fired = fk = winners = armed_n = 0
    net = save = cost = 0.0
    arm_to_be_mins = []
    fk_details = []
    save_details = []
    for (tid, token, signal, direc, entry, pnl_usdt, pnl_pct, amt, lev, ot, ct, xr, vol) in cohort:
        n += 1
        end_u = float(pnl_pct) / float(lev)
        armed, be_hit, arm_ts, be_ts, miss_flag = path_outcome(token, entry, direc, ot, ct)
        if miss_flag:
            miss += 1
            continue
        if not armed:
            continue
        armed_n += 1
        if end_u > 0:
            winners += 1
        if not be_hit:
            continue
        fired += 1
        benefit = 0.0 - float(pnl_usdt)  # cf$ at BE = 0
        net += benefit
        mins = (be_ts - arm_ts) / 60.0
        arm_to_be_mins.append(mins)
        if end_u > 0:
            fk += 1
            cost += benefit
            fk_details.append((token, signal, direc, f"end{end_u:+.2f}%", f"ben{benefit:+.2f}", vol, xr))
        else:
            save += benefit
            save_details.append((token, signal, direc, f"end{end_u:+.2f}%", f"ben{benefit:+.2f}", vol, xr))
    armed_winners = winners  # fk denominator = armed winners
    fk_pct = 100.0 * fk / armed_winners if armed_winners else 0.0
    verdict = "PASS" if (fk_pct <= 20.0 and net > 0 and fired >= 5) else (
        "INSUFFICIENT" if fired < 5 else "FAIL")
    med = sorted(arm_to_be_mins)[len(arm_to_be_mins) // 2] if arm_to_be_mins else None
    print(f"\n## {label}")
    print(f"  n={n} miss={miss} armed={armed_n} armed_winners={armed_winners} fired={fired} "
          f"fk={fk} fk%={fk_pct:.1f} NET={net:+.2f} save={save:+.2f} cost={cost:+.2f} "
          f"med_arm_to_BE={med}m  {verdict}")
    if save_details:
        print("  saves (top):")
        for d in sorted(save_details, key=lambda x: -float(x[4][3:]))[:6]:
            print("   ", d)
    if fk_details:
        print("  false-kills (top):")
        for d in sorted(fk_details, key=lambda x: -float(x[4][3:]))[:6]:
            print("   ", d)
    return verdict, net, fk_pct, fired


print(f"30d trades loaded: {len(rows)}  ARM={ARM} BE={BE}")

# Universe
evaluate(rows, "UNIVERSE 30d")

# Top signal families
fams = {}
for r in rows:
    sig = (r[2] or "None").lower()
    fam = "pump-chain+" if "pump-chain+" in sig else (
          "pump-chain-" if "pump-chain-" in sig else (
          "bb-squeeze" if "bb-squeeze" in sig else (
          "bb-bounce" if "bb-bounce" in sig else (
          "ai-trader+" if "ai-trader+" in sig else (
          "volume-" if "volume-" in sig else "other")))))
    fams.setdefault(fam, []).append(r)
for fam in ("pump-chain+", "pump-chain-", "bb-squeeze", "bb-bounce", "ai-trader+", "volume-", "other"):
    if fam in fams:
        evaluate(fams[fam], f"family {fam}")

# Regime split on universe fired set (aggregate only)
ext = [r for r in rows if (r[12] or "").upper() == "EXTREME"]
non = [r for r in rows if (r[12] or "").upper() != "EXTREME"]
evaluate(ext, "regime EXTREME")
evaluate(non, "regime non-EXTREME")
