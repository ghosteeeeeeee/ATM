"""RIP-CLIMAX GATES (CEO 2026-11-23, the 64,603 wick autopsy).

Tests _rip_climax_defer against the real failure mode and its
counter-cases: the divergence (the RSI topped >=90 and collapsed at the
price high), the creek zone (within 1x ATR1h below the recent peak),
the z-tier STRONG, the revert (RIP_RSI_TOP=0), and the fail-open.
Run: python3 analysis/test_rip_climax.py
"""
import os, sys, json, sqlite3, shutil, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import paths
import hermes_constants as HC
import trade_watchdog as TW

TMP = tempfile.mkdtemp(prefix='ripclimax-')
ORIG_HD, ORIG_WD = paths.HERMES_DATA, getattr(paths, 'WWW_DATA', None)


def _mkdb(closes_1m, rows_1h):
    db = os.path.join(TMP, 'candles.db')
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute("CREATE TABLE candles_1m (token TEXT, ts INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL, is_closed INTEGER)")
    cur.execute("CREATE TABLE candles_1h (token TEXT, ts INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL, is_closed INTEGER)")
    for i, c in enumerate(closes_1m):
        cur.execute("INSERT INTO candles_1m VALUES ('BTC', ?, ?, ?, ?, ?, 1, 1)",
                    (1700000000 + i * 60, c, c, c, c))
    for i, (h, l, c) in enumerate(rows_1h):
        cur.execute("INSERT INTO candles_1h VALUES ('BTC', ?, ?, ?, ?, ?, 1, 1)",
                    (1700000000 + i * 3600, c, h, l, c))
    con.commit(); con.close()


def _rally_then_top():
    """The 64,500 shape: a rally (the RSI -> 95+), then a grinding top
    whose closes stay within 0.5% of the high while the RSI collapses
    below 75 (the real case: the 92.6 top at 13:46, 48.6 at the 14:28
    fill, the price 0.42% below its window high)."""
    closes = [100.0]
    for i in range(60):                       # the rally
        closes.append(closes[-1] + 1.0 + (i % 3) * 0.3)
    peak = closes[-1]
    # 40 bars of the grinding top: the closes erode but stay within
    # 0.5% of the peak (0.5% of ~160 = 0.8 — the drift caps at 0.6)
    for i in range(40):
        drift = min(0.015 * i, 0.6)
        closes.append(peak - drift + (0.12 if i % 2 == 0 else -0.12))
    return closes


def _flat_rising():
    """A fresh rip: the RSI rises (no >=90 top) — no defer."""
    closes = [100.0]
    for i in range(120):
        closes.append(closes[-1] + 0.5 + (0.2 if i % 4 else -0.05))
    return closes


def _install(closes_1m, rows_1h, tier='NEUTRAL'):
    _mkdb(closes_1m, rows_1h)
    paths.HERMES_DATA = TMP
    www = os.path.join(TMP, 'www')
    os.makedirs(www, exist_ok=True)
    with open(os.path.join(www, 'continuum_data.json'), 'w') as f:
        json.dump({'current': {'zscore_tier': tier}}, f)
    paths.WWW_DATA = www
    sys.modules['paths'].WWW_DATA = www


def main():
    ok = 0

    # 1) THE EXACT FAILURE: the RSI topped 92.6, collapsed at the high
    closes = _rally_then_top()
    _install(closes, [(165.0, 100.0, 160.0)] * 30)   # the peak 165, ATR ~
    defer, why = TW._rip_climax_defer('BTC', closes[-1])
    print(f'1 divergence: defer={defer} ({why[:70]})')
    assert defer and 'divergence' in why, why
    ok += 1

    # 2) FRESH RIP: no >=90 top → no defer (the price is at new highs)
    closes = _flat_rising()
    _install(closes, [(closes[-1] + 1.0, closes[-1] - 1.0, closes[-1])] * 30)
    defer, why = TW._rip_climax_defer('BTC', closes[-1])
    print(f'2 fresh rip: defer={defer}')
    assert not defer, why
    ok += 1

    # 3) THE CREEK ZONE: the price within 1x ATR1h below the recent
    #    hour's high (the RSI not collapsing <75 → falls through to the
    #    zone trip; the price condition also separates it from (a))
    closes = [100.0]
    for i in range(70):                        # the rise (the RSI -> ~95)
        closes.append(closes[-1] + 0.25)
    peak = closes[-1]                          # 117.5
    for i in range(10):                        # the shallow pullback
        closes.append(peak - 0.08 * (i + 1))   # the last = 116.7 (0.7 below)
    _install(closes, [(peak + 1.0, peak - 1.0, peak)] * 30)  # ATR1h ~2
    defer, why = TW._rip_climax_defer('BTC', closes[-1])
    print(f'3 creek zone: defer={defer} ({why[:70]})')
    assert defer and 'creek zone' in why, why
    ok += 1

    # 4) ABOVE THE PEAK (the confirmation / the fresh breakout): no defer
    defer, why = TW._rip_climax_defer('BTC', peak + 0.5)
    print(f'4 above the peak: defer={defer}')
    assert not defer, why
    ok += 1

    # 5) THE Z-TIER STRONG: the spike context (the RSI not diverging,
    #    the price not in the zone)
    closes = _flat_rising()
    _install(closes, [(closes[-1] + 50.0, closes[-1] - 1.0, closes[-1])] * 30,
             tier='STRONG_POS')
    defer, why = TW._rip_climax_defer('BTC', closes[-1])
    print(f'5 z-tier STRONG: defer={defer} ({why[:60]})')
    assert defer and 'z-tier' in why, why
    ok += 1

    # 6) THE REVERT: RIP_RSI_TOP=0 no-ops the gates
    old = HC.RIP_RSI_TOP
    HC.RIP_RSI_TOP = 0.0
    try:
        closes = _rally_then_top()
        _install(closes, [(165.0, 100.0, 160.0)] * 30)
        defer, why = TW._rip_climax_defer('BTC', closes[-1])
        print(f'6 revert (TOP=0): defer={defer}')
        assert not defer, why
        ok += 1
    finally:
        HC.RIP_RSI_TOP = old

    # 7) FAIL-OPEN: no candles.db → the fill proceeds (the level +
    #    precheck + R:R still govern)
    empty = tempfile.mkdtemp(prefix='ripclimax-empty-')
    paths.HERMES_DATA = empty
    defer, why = TW._rip_climax_defer('BTC', 64000.0)
    print(f'7 fail-open (no data): defer={defer}')
    assert not defer, why
    shutil.rmtree(empty, ignore_errors=True)
    ok += 1

    shutil.rmtree(TMP, ignore_errors=True)
    paths.HERMES_DATA, paths.WWW_DATA = ORIG_HD, ORIG_WD
    print(f'RIP-CLIMAX GATES: ALL PASS ({ok}/7)')


if __name__ == '__main__':
    main()
