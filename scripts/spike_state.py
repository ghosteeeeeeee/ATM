"""MTF spike-state detection (CEO 2026-11-23 — the standing rules).

"detect the spike and set short levels closer, set longs for
completion of pullback (spike dying)... we should almost be trying
not to get into a trade... wait for higher high maybe. we want moves
with the momentum. continuing."

`spike_state(coin)` returns ('up'/'down'/None, reason) from any of:
  1. the 1m RSI top/bottom (>= RIP_RSI_TOP / <= 100-RIP_RSI_TOP
     within RIP_RSI_WINDOW bars) — the 64,500 case's tell (the 92.6
     top 41min before the price peak);
  2. the continuum z-tier STRONG (POS -> up / NEG -> down);
  3. the window's close-range >= SPIKE_RANGE_PCT (the vertical move)
     with the last close in the top/bottom third.

The keeper uses it for the spike-mode PLACEMENT (both sides at the
band's near edge: the closer shorts + the pullback-completion longs);
the trade_watchdog gates own the FILL deferral (the RIP-CLIMAX
gates) — the placement is ready, the fill waits for the higher high.
Shared module (no watchdog<->auto_trader import — that is circular).
"""
import json
import os
import sqlite3
import time

from paths import HERMES_DATA


def _continuum_tier():
    try:
        try:
            from paths import WWW_DATA as _www   # F-5: via paths
        except Exception:
            _www = '/var/www/hermes/data'
        # the module global is the test seam; production reads paths
        www = globals().get('WWW_DATA') or _www
        with open(os.path.join(www, 'continuum_data.json')) as f:
            return str((json.load(f).get('current') or {})
                       .get('zscore_tier', '') or '')
    except Exception:
        return ''


def spike_state(coin='BTC'):
    """(dir, reason): 'up' | 'down' | None. Fail-open (no data -> None):
    a missing read must never force the placement mode by itself — the
    other detectors carry the state."""
    try:
        import hermes_constants as hc
        top = float(getattr(hc, 'RIP_RSI_TOP', 90.0) or 0)
        win = int(getattr(hc, 'RIP_RSI_WINDOW', 180) or 180)
        rng = float(getattr(hc, 'SPIKE_RANGE_PCT', 3.0) or 0)
    except Exception:
        return None, ''
    if not (top and win and rng):
        return None, ''   # REVERT (RIP_RSI_TOP=0) no-ops the state too
    bottom = 100.0 - top
    # 2) the z-tier
    tier = _continuum_tier()
    if 'STRONG' in tier.upper():
        return ('up' if 'POS' in tier.upper() else 'down',
                f"z-tier {tier} (the STRONG tier)")
    try:
        db = os.path.join(HERMES_DATA, 'candles.db')
        con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
        try:
            cur = con.cursor()
            cur.execute(
                "SELECT close FROM candles_1m WHERE token=? "
                "AND is_closed=1 ORDER BY ts DESC LIMIT ?",
                (coin, max(win, 200)))
            closes = [r[0] for r in cur.fetchall()]
        finally:
            con.close()
    except Exception:
        return None, ''
    if len(closes) < 60:
        return None, ''
    closes.reverse()   # chronological
    # 1) the RSI top/bottom (the most recent 14 of the window)
    g, l = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        g.append(max(0.0, d)); l.append(max(0.0, -d))
    p = 14
    if len(g) >= p:
        ag, al = sum(g[:p]) / p, sum(l[:p]) / p
        rsi = [100.0 - 100.0 / (1 + ag / al) if al > 0 else 100.0]
        for i in range(p, len(closes)):
            ag = (ag * (p - 1) + g[i - 1]) / p
            al = (al * (p - 1) + l[i - 1]) / p
            rsi.append(100.0 - 100.0 / (1 + ag / al) if al > 0 else 100.0)
        w = rsi[-min(win, len(rsi)):]
        if w and max(w) >= top:
            return 'up', f"the 1m RSI topped {max(w):.0f} (>= {top:.0f}) in the window"
        if w and min(w) <= bottom:
            return 'down', f"the 1m RSI bottomed {min(w):.0f} (<= {bottom:.0f}) in the window"
    # 3) the vertical range (the top/bottom third = the direction)
    w = closes[-min(win, len(closes)):]
    lo, hi = min(w), max(w)
    span = (hi - lo) / lo * 100.0 if lo else 0
    if span >= rng:
        pos = (closes[-1] - lo) / (hi - lo) if hi > lo else 0.5
        if pos >= 2.0 / 3.0:
            return 'up', f"the window range {span:.1f}% >= {rng:g}% with the close at the top third"
        if pos <= 1.0 / 3.0:
            return 'down', f"the window range {span:.1f}% >= {rng:g}% with the close at the bottom third"
    return None, ''
