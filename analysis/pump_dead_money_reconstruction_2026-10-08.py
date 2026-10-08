#!/usr/bin/env python3
"""pump_exit_dead_money rule reconstruction (2026-10-08, night).

Question: the live 2h/2% dead-money rule can kill home runs — quantify exactly
how often, at what cost, and whether the velocity clause protects them.

Live rule (position_manager.py, verified in code today):
  fires when ALL of:
    (1) hold >= PUMP_EXIT_TIME_HOURS (2.0h) since open
    (2) direction-aware unrealized profit < PUMP_EXIT_TIME_THRESHOLD (2.0%,
        unleveraged price move; LONG (cur-entry)/entry, SHORT inverse)
    (3) velocity fading: newest completed 5m interval velocity < 0 for LONG
        (>0 for SHORT) — (c[0]-c[1])/c[1], c[0]=newest close
  Scope: signals routed to 'pump_exit' in SIGNAL_EXIT_CONFIG = pump-chain+
  (LONG) (+ combo trades containing it). Evaluated every ~1min cycle; we
  approximate at completed 5m bar closes (candle close semantics).

Replay: walk candles_5m from open; first bar >=2h where (2)+(3) hold = fire;
simulated exit at that bar's close; sim $ = move% x notional (actual pnl_usdt
excludes fees, verified). Validation: replay should predict most actual
exit_reason='pump_exit_dead_money' trades.

Run: python3 analysis/pump_dead_money_reconstruction_2026-10-08.py
"""
import sqlite3
import psycopg2
from datetime import timezone

C = sqlite3.connect("/root/.hermes/data/candles.db")
PG = psycopg2.connect(host="/var/run/postgresql", dbname="brain", user="postgres")
cur = PG.cursor()

TIME_H = 2.0        # PUMP_EXIT_TIME_HOURS
TIME_THR = 2.0      # PUMP_EXIT_TIME_THRESHOLD

cur.execute("""
    SELECT id, token, direction, entry_price, pnl_usdt, pnl_pct, amount_usdt, leverage,
           exit_reason, strategy, open_time, close_time
    FROM trades
    WHERE status='closed' AND paper='f' AND pnl_usdt IS NOT NULL AND entry_price > 0
      AND amount_usdt > 0 AND (strategy LIKE '%pump-chain+%' OR strategy LIKE '%pump_chain+%' OR strategy = 'pump_chain')
    ORDER BY open_time""")
TR = cur.fetchall()
print(f"pump_exit-scope trades (pump-chain+ etc.): {len(TR)}")
hrs = [r for r in TR if r[5] is not None and float(r[5]) >= 10]
print(f"home runs in scope: {len(hrs)} -> {[(r[0], r[1], r[5]) for r in hrs]}")

fires = []
for (tid, tok, dire, entry, pnlu, pnlp, amt, lev, xr, strat, ot, ct) in TR:
    entry = float(entry)
    ots = int(ot.replace(tzinfo=timezone.utc).timestamp())
    cts = int(ct.replace(tzinfo=timezone.utc).timestamp())
    bars = C.execute(
        "SELECT ts, close FROM candles_5m WHERE token=? AND is_closed=1 AND ts>=? AND ts<=? ORDER BY ts",
        (tok.upper(), ots - 300, cts + 300)).fetchall()
    if len(bars) < 3:
        continue
    fire = None
    for i in range(2, len(bars)):
        ts, cl = bars[i]
        hold_min = (ts - ots) / 60.0
        if hold_min < TIME_H * 60:
            continue
        # profit at bar close (closest bar at/after checkpoint semantics: evaluate every bar)
        move = (cl - entry) / entry * 100 * (1 if dire == 'LONG' else -1)
        if move >= TIME_THR:
            continue
        vel = (bars[i][1] - bars[i-1][1]) / bars[i-1][1] * 100
        fading = (vel < 0) if dire == 'LONG' else (vel > 0)
        if fading:
            fire = (ts, cl, round(move, 3), round(vel, 3), hold_min)
            break
    if fire:
        ts, cl, move, vel, hold_min = fire
        sim_usd = move / 100 * float(amt)
        fires.append(dict(id=tid, tok=tok, dire=dire, sig=strat, xr=str(xr),
                          sim=round(sim_usd, 3), actual=round(float(pnlu), 3),
                          pnlp=float(pnlp or 0), amt=float(amt), lev=float(lev or 1),
                          fire_h=round(hold_min / 60, 2), move=move, vel=vel,
                          ot=ot, ct=ct, fire_ts=ts))

print(f"\nREPLAY FIRES (dead-money, velocity clause modeled): {len(fires)}")
actual_dm = [f for f in fires if 'dead_money' in f['xr']]
print(f"  of which actual exit_reason = pump_exit_dead_money: {len(actual_dm)} (validation)")
actual_dm_ids = {r[0] for r in TR if r[8] and 'dead_money' in str(r[8])}
replay_ids = {f['id'] for f in fires}
print(f"  actual dead_money exits overall: {len(actual_dm_ids)}; replay predicts "
      f"{len(actual_dm_ids & replay_ids)} of them; replay fires on "
      f"{len(replay_ids - actual_dm_ids)} trades that exited another way")

hr_kills = [f for f in fires if f['pnlp'] >= 10]
print(f"\nHOME-RUN KILLS (actual pnl_pct>=10, rule fires first): {len(hr_kills)}")
for f in hr_kills:
    print(f"  #{f['id']} {f['tok']:<7} {f['sig'][:28]:<28} fired at {f['fire_h']}h "
          f"(profit {f['move']:+.2f}%, vel {f['vel']:+.2f}%) | actual {f['pnlp']:+.1f}% "
          f"(${f['actual']:+.2f}) | sim-at-fire ${f['sim']:+.2f} | GAVE UP ${f['actual']-f['sim']:+.2f}")

total_delta = sum(f['sim'] - f['actual'] for f in fires)
saved = sum(f['sim'] - f['actual'] for f in fires if f['actual'] < 0)
gaveup = sum(f['sim'] - f['actual'] for f in fires if f['actual'] >= 0)
print(f"\nRULE ECONOMICS (all fires, sim-vs-actual, fee-neutral):")
print(f"  fires={len(fires)}  net delta=${total_delta:+.2f}  (saved on eventual losers ${saved:+.2f}, "
      f"gave up on eventual winners ${gaveup:+.2f})")
print(f"  fired trades that ended positive (would-be small winners cut): "
      f"{sum(1 for f in fires if f['actual'] > 0)}/{len(fires)}")
print(f"  fired trades that were HRs: {len(hr_kills)} (gave up ${sum(f['actual']-f['sim'] for f in hr_kills):+.2f})")

# fires by month (is rule firing more as fixes landed?)
from collections import Counter
byweek = Counter(f['ot'].date().isocalendar()[1] for f in fires)
print(f"  fires by ISO week: {dict(sorted(byweek.items()))}")

# actual-fired trades: post-fire drift (opportunity cost check on the 26-ish real exits)
print("\nACTUAL dead_money exits — post-fire 5m drift (did price recover after we exited?)")
cur.execute("""
    SELECT id, token, direction, entry_price, close_time, exit_price, pnl_pct, amount_usdt
    FROM trades WHERE status='closed' AND paper='f' AND exit_reason='pump_exit_dead_money'
    ORDER BY close_time DESC LIMIT 40""")
rows = cur.fetchall()
rec = down = flat = 0
deltas = []
for (tid, tok, dire, entry, ct, xpx, pnlp, amt) in rows:
    if xpx is None:
        continue
    entry, xpx = float(entry), float(xpx)
    cts = int(ct.replace(tzinfo=timezone.utc).timestamp())
    b = C.execute("SELECT close FROM candles_5m WHERE token=? AND is_closed=1 AND ts>=? AND ts<? ORDER BY ts LIMIT 12",
                  (tok.upper(), cts, cts + 3600)).fetchall()
    if len(b) < 6:
        continue
    end = b[-1][0]
    drift = (end - xpx) / xpx * 100 * (1 if dire == 'LONG' else -1)
    deltas.append(drift)
    if drift > 0.3: rec += 1
    elif drift < -0.3: down += 1
    else: flat += 1
if deltas:
    import statistics
    print(f"  n={len(deltas)}  recovered(>+0.3%): {rec}  continued(<-0.3%): {down}  flat: {flat}  "
          f"median 1h drift {statistics.median(deltas):+.2f}%")

# the near-miss question: how many pump-chain+ trades sat below 2% at 2h but escaped (vel positive)?
near = 0
esc_hrs = []
for (tid, tok, dire, entry, pnlu, pnlp, amt, lev, xr, strat, ot, ct) in TR:
    entry = float(entry)
    ots = int(ot.replace(tzinfo=timezone.utc).timestamp())
    cts = int(ct.replace(tzinfo=timezone.utc).timestamp())
    bars = C.execute("SELECT ts, close FROM candles_5m WHERE token=? AND is_closed=1 AND ts>=? AND ts<=? ORDER BY ts",
                     (tok.upper(), ots + 7200 - 300, ots + 7200 + 900)).fetchall()
    if len(bars) < 2:
        continue
    # state at first bar >= 2h
    at2h = [(ts, cl) for ts, cl in bars if (ts - ots) >= 7200]
    if not at2h:
        continue
    ts, cl = at2h[0]
    move = (cl - entry) / entry * 100 * (1 if dire == 'LONG' else -1)
    if move < TIME_THR:
        near += 1
        if pnlp is not None and float(pnlp) >= 10:
            esc_hrs.append((tid, tok, round(float(pnlp), 1)))
print(f"\nAt exactly 2h: {near} in-scope trades below +2%; of those HRs: {len(esc_hrs)} -> {esc_hrs}")

C.close(); PG.close()
print("\nDONE.")
