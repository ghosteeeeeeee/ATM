"""MTF SPIKE STATE tests (CEO 2026-11-23 — the placement rules).

spike_state.spike_state(): the three detectors (the RSI top/bottom,
the z-tier, the vertical range), the calm tape, the revert, the
fail-open — and the keeper's spike-mode placement (both sides at the
band's near edge) vs the calm structure placement.
Run: python3 analysis/test_spike_state.py
"""
import os, sys, json, sqlite3, shutil, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import paths
import hermes_constants as HC
import spike_state as SS
import auto_trader as AT

TMP = tempfile.mkdtemp(prefix='spike-')
ORIG_HD = paths.HERMES_DATA


def _mkdb(closes_1m):
    db = os.path.join(TMP, 'candles.db')
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("CREATE TABLE candles_1m (token TEXT, ts INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL, is_closed INTEGER)")
    for i, c in enumerate(closes_1m):
        cur.execute("INSERT INTO candles_1m VALUES ('BTC', ?, ?, ?, ?, ?, 1, 1)",
                    (1700000000 + i * 60, c, c, c, c))
    con.commit(); con.close()


def _set(tier='NEUTRAL', closes=None):
    if closes is not None:
        _mkdb(closes)
    paths.HERMES_DATA = TMP
    SS.HERMES_DATA = TMP
    www = os.path.join(TMP, 'www')
    os.makedirs(www, exist_ok=True)
    with open(os.path.join(www, 'continuum_data.json'), 'w') as f:
        json.dump({'current': {'zscore_tier': tier}}, f)
    SS.WWW_DATA = www


def _rally():
    c = [100.0]
    for i in range(150):
        c.append(c[-1] + 0.6)
    return c


def _calm():
    c = [100.0]
    for i in range(150):
        c.append(c[-1] + (0.02 if i % 3 else -0.01))
    return c


def main():
    ok = 0

    # 1) the RSI-top detector (the 64,500 shape: the rally -> the top)
    _set('NEUTRAL', _rally())
    d, why = SS.spike_state('BTC')
    print(f'1 rsi-top: {d} ({why[:60]})')
    assert d == 'up', (d, why)
    ok += 1

    # 2) the z-tier detectors
    _set('STRONG_POS', _calm())
    d, why = SS.spike_state('BTC')
    print(f'2a z POS: {d} ({why[:50]})')
    assert d == 'up'
    _set('STRONG_NEG', _calm())
    d, why = SS.spike_state('BTC')
    print(f'2b z NEG: {d} ({why[:50]})')
    assert d == 'down'
    ok += 1

    # 3) the vertical range: an interleaved grind (the RSI stays mid —
    #    below the 90/10 detectors — so the RANGE detector is what trips)
    c = [100.0]
    for i in range(150):
        c.append(c[-1] + (0.10 if i % 3 else -0.03))   # the net ~+5%
    _set('NEUTRAL', c)
    d, why = SS.spike_state('BTC')
    print(f'3 vertical up: {d} ({why[:60]})')
    assert d == 'up' and 'range' in why, (d, why)
    c2 = [105.0]
    for i in range(150):
        c2.append(c2[-1] + (-0.10 if i % 3 else 0.03))  # the net ~-8% (mirrors the up)
    _set('NEUTRAL', c2)
    d, why = SS.spike_state('BTC')
    print(f'3 vertical down: {d} ({why[:60]})')
    assert d == 'down' and 'range' in why, (d, why)
    ok += 1

    # 4) the calm tape (no detector) -> None
    _set('NEUTRAL', _calm())
    d, why = SS.spike_state('BTC')
    print(f'4 calm: {d}')
    assert d is None
    ok += 1

    # 5) the revert (RIP_RSI_TOP=0) no-ops the state
    old = HC.RIP_RSI_TOP
    HC.RIP_RSI_TOP = 0.0
    try:
        _set('NEUTRAL', _rally())
        d, why = SS.spike_state('BTC')
        print(f'5 revert: {d}')
        assert d is None
        ok += 1
    finally:
        HC.RIP_RSI_TOP = old

    # 6) the fail-open (no candles.db): the z-tier can still trip, the
    #    rest returns None (never a forced state from a missing read)
    empty = tempfile.mkdtemp(prefix='spike-empty-')
    paths.HERMES_DATA = empty
    SS.HERMES_DATA = empty
    _set('STRONG_POS')          # the STRONG tier, no candles.db
    SS.HERMES_DATA = empty      # _set reset it — keep the DB missing
    d, why = SS.spike_state('BTC')
    print(f'6 no-db with a STRONG tier: {d} ({why[:40]})')
    assert d == 'up'   # the z-tier tripped before the DB read
    SS.WWW_DATA = os.path.join(TMP, 'www-missing')  # no continuum either
    d, why = SS.spike_state('BTC')
    print(f'6 no-db no-tier: {d}')
    assert d is None
    shutil.rmtree(empty, ignore_errors=True)
    ok += 1

    # 7) the KEEPER's spike-mode: both sides derive at the near edge
    import psycopg2
    class SC:
        rowcount = 1
        def execute(self, *a, **k): pass
        def close(self): pass
    class CN:
        def cursor(self): return SC()
        def commit(self): pass
        def close(self): pass
    psycopg2.connect = lambda **k: CN()
    AT.DB.log_event = lambda lvl, msg: None
    AT.DB.recent_attribution = lambda n: [{'direction': 'SHORT', 'pnl_pct': 9.9}]
    price = 61152.0
    # sl1h 59,989 -> the structure trig 59,929 = the band's FAR edge
    # (in-reach: reach_lo = 61,152-3*520 = 59,592) — the calm keeps the
    # far edge while the spike forces the near edge, so the two modes
    # are distinguishable in these tests
    sd = {'15m': {'sh': 61800, 'sl': 60300, 'atr': 350},
          '1h': {'sh': 62100, 'sl': 59989, 'atr': 520}}
    # the SPIKE state (the z-tier trips it — no DB dependence)
    _set('STRONG_POS')
    json.dump({"orders": []}, open(os.path.join(TMP, 'pending_orders.json'), 'w'))
    json.dump({}, open(os.path.join(TMP, 'pending_orders_state.json'), 'w'))
    AT._ladder_keeper({'price': price, 'structure_detail': sd}, {})
    got = json.load(open(os.path.join(TMP, 'pending_orders.json')))
    shorts = [o for o in got['orders'] if o['direction'] == 'short']
    longs = [o for o in got['orders'] if o['direction'] == 'long']
    print(f'7 spike-mode: short {shorts[0]["trigger_price"] if shorts else None} '
          f'long {longs[0]["trigger_price"] if longs else None}')
    # the near edges: 61152*0.99 = 60540.5 -> the in-band 250-round
    # 61152*1.01 = 61763.5 -> the in-band 250-round
    if shorts:
        assert abs(shorts[0]['trigger_price'] - 60500) <= 250, shorts[0]
        assert shorts[0]['trigger_price'] >= 59929   # >= the far edge (2%)
        # F-1 (agent-12 HIGH): the SL travels WITH the trigger — the
        # shape must be valid (sl > trigger) or the watchdog shape-
        # skips the arm every cycle (the dark short side)
        assert shorts[0]['sl'] > shorts[0]['trigger_price'], (
            "F-1: the spike short's SL must sit above the trigger: "
            f"sl={shorts[0]['sl']} trig={shorts[0]['trigger_price']}")
        # F-2 (agent-12 MEDIUM): the note must name the spike (F7)
        assert 'SPIKE MODE' in shorts[0].get('note', ''), (
            "F-2: the spike arm's note must name the spike: "
            f"{shorts[0].get('note', '')[:80]}")
        if longs:
            assert longs[0]['sl'] < longs[0]['trigger_price'], (
                "the long shape: the SL must sit below the trigger")
    if longs:
        assert abs(longs[0]['trigger_price'] - 61750) <= 250, longs[0]
        assert longs[0]['trigger_price'] <= 62375    # <= the far edge (2%)
    ok += 1

    # 8) the CALM state: the structure placement (the far 1h level)
    _set('NEUTRAL', _calm())
    json.dump({"orders": []}, open(os.path.join(TMP, 'pending_orders.json'), 'w'))
    json.dump({}, open(os.path.join(TMP, 'pending_orders_state.json'), 'w'))
    AT._ladder_keeper({'price': price, 'structure_detail': sd}, {})
    got = json.load(open(os.path.join(TMP, 'pending_orders.json')))
    shorts = [o for o in got['orders'] if o['direction'] == 'short']
    print(f'8 calm-mode: short {shorts[0]["trigger_price"] if shorts else None} '
          f'(the structure 58500-60 = 58440, clamped to the band)')
    if shorts:
        # the calm: the structure level (58440) is out-of-band-far ->
        # the clamp pulls it to the FAR edge (2% = 59930-ish), NOT the
        # near edge — the spike-mode is what forces the near edge
        assert abs(shorts[0]['trigger_price'] - 60000) <= 250, shorts[0]
        assert shorts[0]['trigger_price'] != 60500, 'the calm must not use the near edge'
    ok += 1

    shutil.rmtree(TMP, ignore_errors=True)
    paths.HERMES_DATA = ORIG_HD
    print(f'MTF SPIKE STATE: ALL PASS ({ok}/8)')


if __name__ == '__main__':
    main()
