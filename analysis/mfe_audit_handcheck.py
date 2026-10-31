#!/usr/bin/env python3
"""Bar-by-bar hand-check of 3 trades: 2 where mfe-exit should fire, 1 where the
floor should fire.  Prints every 5m bar with the peak/threshold arithmetic so
the decisive bar can be verified by hand. Independent of jup_exit_sim."""
import sys
import sqlite3
import datetime as dt

sys.path.insert(0, '/root/.hermes/analysis')
import mfe_audit_replay as M

IDS = [int(x) for x in (sys.argv[1:] or ['16540', '16573', '16564'])]
trades = {t['id']: t for t in M.load_trades()}

con = sqlite3.connect(M.CANDLE_DB)

for tid in IDS:
    t = trades[tid]
    ot = int(t['open_t'].timestamp())
    hz = ot + 12 * 3600
    bars = con.execute(
        "SELECT ts, open, high, low, close FROM candles_5m "
        "WHERE token=? AND is_closed=1 AND ts>=? AND ts<? ORDER BY ts",
        (t['token'].upper(), ot - 300, hz + 300)).fetchall()
    long_ = t['dir'] == 'LONG'
    entry = t['entry']
    floor_frac = min(4.0 / t['lev'], 2.5) / 100.0
    floor_px = entry * (1 - floor_frac) if long_ else entry * (1 + floor_frac)
    tp_px = entry * (1 + 0.02) if long_ else entry * (1 - 0.02)

    print("=" * 118)
    print(f"trade {tid}  {t['token']} {t['dir']}  entry={entry}  lev={t['lev']}  "
          f"open={t['open_t']}  actual_close={t['close_t']} reason={t['reason']} "
          f"actual_pnl={t['pnl']:+.4f} (leveraged)")
    print(f"floor(-4% acct / {t['lev']}x) = {floor_frac*100:.3f}% price -> "
          f"{floor_px:.6f}   |  ATR SL 2.5% -> "
          f"{entry*(1-0.025) if long_ else entry*(1+0.025):.6f}  (floor = tightest)")
    print(f"ATR TP 2.0% -> {tp_px:.6f}   |  horizon = "
          f"{dt.datetime.utcfromtimestamp(hz)}")
    print(f"{'bar start':<20} {'open':>10} {'high':>10} {'low':>10} {'close':>10} "
          f"| {'prior peak%':>11} {'thr%=0.7*pk':>12} {'thr px':>11} | notes")
    peak = 0.0
    exited = None
    for ts, o, h, l, c in bars:
        if ts < ot:
            print(f"{dt.datetime.utcfromtimestamp(ts):%Y-%m-%d %H:%M}  "
                  f"SKIPPED (bar contains entry)")
            continue
        if ts > hz:
            break
        fav = ((h / entry) - 1) * 100 if long_ else (1 - l / entry) * 100
        thr = peak * 0.7
        thr_px = entry * (1 + thr / 100) if long_ else entry * (1 - thr / 100)
        notes = []
        if peak > 0:
            if (l <= thr_px) if long_ else (h >= thr_px):
                at_open = (o <= thr_px) if long_ else (o >= thr_px)
                notes.append(f"MFE-THRESHOLD {'TOUCHED' if not at_open else 'AT OPEN'}"
                             f" fill={o if at_open else thr_px:.6f}")
        if (l <= floor_px) if long_ else (h >= floor_px):
            notes.append(f"FLOOR touched (floor_px={floor_px:.6f})")
        if (h >= tp_px) if long_ else (l <= tp_px):
            notes.append("ATR-TP touched")
        print(f"{dt.datetime.utcfromtimestamp(ts):%Y-%m-%d %H:%M}  "
              f"{o:>10.5f} {h:>10.5f} {l:>10.5f} {c:>10.5f} | "
              f"{peak:>11.5f} {thr:>12.5f} {thr_px:>11.5f} | {' '.join(notes)}")
        # single-pass state advance, mirroring the documented rule
        if exited is None:
            # (1) floor first
            if (l <= floor_px) if long_ else (h >= floor_px):
                exited = (floor_px, ts, 'floor')
            else:
                cand = None
                if peak > 0:
                    tf = peak * 0.7
                    if tf > 0:
                        cand = (entry * (1 + tf / 100) if long_
                                else entry * (1 - tf / 100))
                if cand is not None:
                    at_open = (o <= cand) if long_ else (o >= cand)
                    touched = (l <= cand) if long_ else (h >= cand)
                    if at_open or touched:
                        fill = o if at_open else cand
                        tp_hit = (h >= tp_px) if long_ else (l <= tp_px)
                        if tp_hit and ((tp_px < fill) if long_ else (tp_px > fill)):
                            exited = (tp_px, ts, 'atr_tp')
                        else:
                            exited = (fill, ts, 'mfe_exit')
                    elif (h >= tp_px) if long_ else (l <= tp_px):
                        exited = (tp_px, ts, 'atr_tp')
                elif (h >= tp_px) if long_ else (l <= tp_px):
                    exited = (tp_px, ts, 'atr_tp')
            if exited is None and fav > peak:
                peak = fav
            elif exited is not None:
                pass
        if exited:
            print(f"  >>> EXIT at {dt.datetime.utcfromtimestamp(exited[1])} "
                  f"px={exited[0]:.6f} tag={exited[2]}")
            # the rest of the bars are only shown for context
    if exited:
        px = exited[0]
        raw = (px / entry - 1) * 100 if long_ else (1 - px / entry) * 100
        print(f"  HAND PNL: price% = ({px:.6f}/{entry} - 1)*100 = {raw:+.6f}  "
              f"x lev {t['lev']:.0f} = {raw*t['lev']:+.4f}  (account %)")
        # independent second computation with plain arithmetic
        raw2 = (px - entry) / entry * 100 if long_ else (entry - px) / entry * 100
        print(f"  cross-check alt formula: {raw2:+.6f}% x {t['lev']:.0f} = "
              f"{raw2*t['lev']:+.4f}")
    print()
con.close()
