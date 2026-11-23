#!/usr/bin/env python3
"""Pending-order machine regression suite (committed per agent-4 I-3).

Covers the 2026-11-20/21 stack: multi-touch two-style entries, the
straight-line escape, the no-burn taxonomy, the add-path (direction
gate + caps), the round-anchor arithmetic, and the stack-leader stop.
Stdlib + mocks only; runs against the SHIPPED source.

Run: python3 analysis/test_pending_machine.py
"""
import json
import math
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, '/root/.hermes/scripts')
import paths  # noqa: E402

_tmp = tempfile.mkdtemp()
paths.HERMES_DATA = _tmp

import auto_trader as AT        # noqa: E402
import position_manager as PM   # noqa: E402
import trade_watchdog as TW     # noqa: E402

TW._acquire_pending_lock = lambda: open(os.path.join(_tmp, '.lk'), 'w')
TW._release_pending_lock = lambda f: f.close()
_file_loader = TW._load_orders_state   # real file reader (groups 4/5 patch it)
# E1 (deep run 20261122T220223Z): fills now require momentum confirmation.
# The MACHINE tests exercise state/fill discipline — stub the confirmation
# to 'confirmed' so the synthetic crosses fill as asserted; the helper's
# own contract is tested for real in group 11 (flag-off / ATR-miss paths
# need no candles; the confirmed/unconfirmed paths are covered by the
# deep's selfcheck_20261122T220223Z_e1.py + the bug-hunter round).
# _momentum_confirm is NESTED inside the monitor impl (module patching is
# dead) — the designed toggle is the FLAG: OFF -> _MOM_OFF sentinel ->
# byte-identical legacy behavior, which is exactly what the machine tests
# exercise. Group 11 tests the real helper with the flag in both states.
import hermes_constants as _HC0
_mom_flag_orig = getattr(_HC0, 'MOMENTUM_CONFIRM_ENABLED', True)
_HC0.MOMENTUM_CONFIRM_ENABLED = False

# --- DB/open-position mock (psycopg2 imported inside the gate) ---------
import psycopg2  # noqa: E402

MODE = ['ok']       # ok | dbdown
OPEN = [None]       # (id, direction) | None
COUNT = [0]
NOTIONAL = [0.0]    # Σ amount_usdt for the heat numerator
EQUITY = [1000.0]   # account_value for the heat denominator


class _SC:
    def execute(self, sql, *a):
        if 'COUNT(*)' in sql:
            self._last = ('count',)
        elif 'SUM(' in sql:
            self._last = ('sum',)
        else:
            self._last = ('row',)

    def fetchone(self):
        if MODE[0] == 'dbdown':
            raise RuntimeError('db down')
        # psycopg2 returns tuples: COUNT(*) -> (n,)
        if self._last == ('count',):
            return (COUNT[0],)
        if self._last == ('sum',):
            return (NOTIONAL[0],)
        return OPEN[0]

    def close(self):
        pass


class _CN:
    def cursor(self):
        return _SC()

    def close(self):
        pass


psycopg2.connect = lambda **k: _CN()

CAPTURE = {'cmd': None, 'out': '', 'rc': 0}


def _fake_run(cmd, **kw):
    CAPTURE['cmd'] = cmd

    class R:
        pass
    r = R()
    r.returncode = CAPTURE['rc']
    r.stdout = CAPTURE['out']
    r.stderr = ""
    return r


TW.subprocess.run = _fake_run


def mk(oid, trig, d='short', serial=True, style='continuation'):
    o = {"id": oid, "coin": "BTC", "direction": d,
         "trigger": ("above" if d == 'long' else "below"),
         "trigger_price": trig, "amount_usdt": 22.2, "leverage": 10,
         "sl": trig + (400 if d == 'short' else -400),
         "target": trig + (-2000 if d == 'short' else 2000),
         "confidence": 60, "serial": serial, "note": "t"}
    if style:
        o['entry_style'] = style
    return o


def setup(orders, states=None):
    json.dump({"orders": orders},
              open(os.path.join(_tmp, 'pending_orders.json'), 'w'))
    json.dump(states or {},
              open(os.path.join(_tmp, 'pending_orders_state.json'), 'w'))


def stt():
    return json.load(open(os.path.join(_tmp, 'pending_orders_state.json')))


def steers(s, oid):
    return [x for x in s if x.get('action', {}).get('type') == 'execute_order'
            and x['action']['order']['id'] == oid]


def main():
    # ── 1. multi-touch: first break never fills ────────────────────────
    MODE[0] = 'ok'; OPEN[0] = None; COUNT[0] = 0
    setup([mk('a', 63000, style=None)])
    s = TW.monitor_pending_orders(62900.0)
    assert not steers(s, 'a') and stt()['a']['status'] == 'first_break'
    TW.monitor_pending_orders(63500.0)                  # reclaim
    assert stt()['a']['status'] == 'retested'
    s = TW.monitor_pending_orders(62500.0)              # cross#2
    assert len(steers(s, 'a')) == 1, 're-cross must fill'
    print('1 multi-touch: first_break -> reclaim -> cross#2 FILL ✓')

    # ── 2. straight-line escape ────────────────────────────────────────
    setup([mk('a', 63000, style=None)])
    TW.monitor_pending_orders(62900.0)                  # first_break
    s = TW.monitor_pending_orders(62650.0)              # -0.58% past, no retest
    assert len(steers(s, 'a')) == 1, 'escape must fill'
    print('2 straight-line escape fills on a one-way slice ✓')

    # ── 3. continuation fills on cross, never records first_break ──────
    setup([mk('c', 58000)])
    s = TW.monitor_pending_orders(57900.0)
    # fills on cross; the steer persists 'triggered' but the machine
    # never records first_break for a continuation rung
    assert len(steers(s, 'c')) == 1 and stt()['c']['status'] == 'triggered'
    print('3 continuation: fill on cross, no state ✓')

    # ── 4. no-burn taxonomy (exact marker) ─────────────────────────────
    st = {}
    TW._load_orders_state = lambda: st
    for out, rc, want in [
            ("[brain.py] \u274c REJECTED: BTC SHORT — knife 35\n", 1, 'rejected'),
            ("Traceback...\n  raise X('brain.py] \u274c REJECTED quoted')\n", 1, 'error'),
            ("connection refused\n", 1, 'error'),
            ("✓ Added trade #17099: SHORT", 0, 'fired')]:
        st.clear()
        CAPTURE['out'], CAPTURE['rc'] = out, rc
        TW._execute_pending_order_impl(mk('t', 59000))
        assert st['t']['status'] == want, (out[:30], st['t']['status'])
    print('4 taxonomy: marker->rejected / traceback+real->error / ok->fired ✓')

    # ── 5. add-path: direction gate + caps + fail-safe ─────────────────
    st = {}
    TW._load_orders_state = lambda: st
    CAPTURE['out'], CAPTURE['rc'] = "✓ Added trade #17100", 0
    TW._execute_pending_order_impl(mk('btc-auto-ladder-1', 57000))
    assert '--force' in CAPTURE['cmd'] and '--prearmed' in CAPTURE['cmd']
    CAPTURE['cmd'] = None
    TW._execute_pending_order_impl(mk('btc-auto-other', 57000))
    assert '--force' not in (CAPTURE['cmd'] or []), 'non-ladder belt intact'
    MODE[0] = 'dbdown'
    setup([mk('a', 57000)])
    assert not steers(TW.monitor_pending_orders(56900.0), 'a'), 'dbdown defers'
    MODE[0] = 'ok'; OPEN[0] = ('1', 'SHORT', 1.5); COUNT[0] = 6
    setup([mk('a', 57000)])
    assert not steers(TW.monitor_pending_orders(56900.0), 'a'), 'cap defers'
    COUNT[0] = 2
    setup([mk('a', 57000)])
    assert len(steers(TW.monitor_pending_orders(56900.0), 'a')) == 1, 'same-dir ADD'
    OPEN[0] = ('1', 'LONG')
    setup([mk('a', 57000)])
    assert not steers(TW.monitor_pending_orders(56900.0), 'a'), 'opposite waits'
    print('5 add-path: ladder --force, dbdown defer, cap defer, ADD, opposite-wait ✓')

    # ── 6. round-anchor arithmetic (the CEO spec) ──────────────────────
    def rs(price, stop, be=0.0):
        rt = math.ceil(price / 500.0) * 500
        return rt if (rt > price and rt < stop and (not be or rt <= be)) else None
    def rl(price, stop, be=0.0):
        rt = int(price // 500.0) * 500
        return rt if (rt < price and rt > stop and (not be or rt >= be)) else None
    assert rs(55400, 56693, be=56693.6) == 55500   # the CEO spec case
    assert rs(55500, 56693) is None                 # at the round: no instant close
    assert rs(54900, 55500) == 55000                # ratchets down
    assert rs(56100, 55500) is None                 # bounce: never raises
    assert rs(55400, 60000, be=55450) is None       # BE-cap respected
    assert rl(55600, 55000, be=55500) == 55500      # long mirror
    print('6 round-anchor: spec case, no-instant-close, ratchet, no-raise, BE, long ✓')

    # ── 7. stack-leader (the production pattern: full list + filter) ───
    rows = [
        {"id": 17014, "token": "BTC", "direction": "SHORT",
         "current_price": 55700, "stop_loss": 56000, "target": 53000,
         "signal": "test-signal"},
        {"id": 17020, "token": "BTC", "direction": "SHORT",
         "current_price": 55700, "stop_loss": 55600, "target": 53000,
         "signal": "test-signal"},
    ]
    R = 'hit_reason'
    def prod_hits(positions):
        out = []
        for pos in positions:
            out += [h for h in PM.check_atr_tp_sl_hits(positions)
                    if h.get('trade_id') == pos.get('id')]
        return out
    hits = prod_hits(rows)
    assert not any(h[R] == 'atr_sl_hit' for h in hits), \
        'follower tight stop must not fire while stacked'
    rows[0]['current_price'] = rows[1]['current_price'] = 56100
    hits = prod_hits(rows)
    assert any(h['trade_id'] == 17014 and h[R] == 'atr_sl_hit' for h in hits), \
        'leader stop must fire the stack'
    solo = [dict(rows[1], current_price=55700)]
    assert any(h[R] == 'atr_sl_hit' for h in prod_hits(solo)), 'flat self-governs'
    print('7 stack-leader: follower ignored / leader fires / flat self-governs ✓')

    # ── 8. D3 heat gate + D2.3 band flag (CEO deep-run 2026-11-21) ─────
    TW._load_orders_state = _file_loader   # undo group 4/5's closure leak
    import hyperliquid_exchange as HLE
    _orig_equity = getattr(HLE, 'get_account_value_curl', None)
    HLE.get_account_value_curl = lambda: {'account_value': EQUITY[0]}
    MODE[0] = 'ok'; OPEN[0] = None; COUNT[0] = 0
    NOTIONAL[0] = 50.0; EQUITY[0] = 1000.0        # heat 0.05 < 0.15
    # the heat gate is SCOPED to ladder ids (btc-auto-*) by design —
    # hand-arms bypass; the tests must use a ladder id or they test
    # nothing (my first version used 'a' and passed for the wrong reason)
    setup([mk('btc-auto-ladder-h', 57000)])
    assert len(steers(TW.monitor_pending_orders(56900.0), 'btc-auto-ladder-h')) == 1, \
        'heat under cap must fire'
    NOTIONAL[0] = 200.0                           # heat 0.20 > 0.15
    setup([mk('btc-auto-ladder-h', 57000)])
    assert not steers(TW.monitor_pending_orders(56900.0), 'btc-auto-ladder-h'), \
        'heat over cap must defer'
    HLE.get_account_value_curl = lambda: (_ for _ in ()).throw(RuntimeError('hl down'))
    NOTIONAL[0] = 50.0
    setup([mk('btc-auto-ladder-h', 57000)])
    assert not steers(TW.monitor_pending_orders(56900.0), 'btc-auto-ladder-h'), \
        'equity failure must defer (fail-safe)'
    HLE.get_account_value_curl = lambda: {'account_value': 1000.0}
    # hand-arm (btc-ceo-*) bypasses the heat gate even over cap
    NOTIONAL[0] = 200.0
    setup([mk('btc-ceo-x', 57000)])
    assert len(steers(TW.monitor_pending_orders(56900.0), 'btc-ceo-x')) == 1, \
        'hand-arms bypass heat'
    # ADD branch carries the band flag; flat fill does not
    NOTIONAL[0] = 50.0; OPEN[0] = ('1', 'SHORT', 1.5); COUNT[0] = 1
    setup([mk('a', 57000)])
    s = TW.monitor_pending_orders(56900.0)
    assert steers(s, 'a')[0]['action']['order'].get('prearmed_add') is True, \
        'ADD must carry the band flag'
    OPEN[0] = None; COUNT[0] = 0
    setup([mk('a', 57000)])
    s = TW.monitor_pending_orders(56900.0)
    assert not steers(s, 'a')[0]['action']['order'].get('prearmed_add'), \
        'flat first fill must NOT carry the band flag'
    # executor appends --prearmed-add only for the flagged order
    st = {}
    TW._load_orders_state = lambda: st
    CAPTURE['out'], CAPTURE['rc'] = "✓ Added trade #17101", 0
    _flagged = mk('btc-auto-ladder-7', 57000)
    _flagged['prearmed_add'] = True
    TW._execute_pending_order_impl(_flagged)
    assert '--prearmed-add' in CAPTURE['cmd'] and '--prearmed' in CAPTURE['cmd']
    CAPTURE['cmd'] = None
    TW._execute_pending_order_impl(mk('btc-auto-ladder-8', 57000))
    assert '--prearmed-add' not in (CAPTURE['cmd'] or []), 'unflagged gets no band flag'
    if _orig_equity is not None:
        HLE.get_account_value_curl = _orig_equity
    print('8 D3 heat gate (under/over/equity-fail/hand-arm-bypass) + D2.3 flag plumbing ✓')

    # ── 9. D2.3 band predicate (brain) ─────────────────────────────────
    import brain as BRAIN
    assert BRAIN._prearmed_add_band_ok('SHORT', 24.6) is False   # #17027-class add
    assert BRAIN._prearmed_add_band_ok('SHORT', 50.0) is True
    assert BRAIN._prearmed_add_band_ok('LONG', 83.39) is False
    assert BRAIN._prearmed_add_band_ok('LONG', 70.0) is True
    assert BRAIN._prearmed_add_band_ok('SHORT', None) is True     # fail-open
    print('9 D2.3 band predicate: oversold-short blocked / overbought-long blocked / mid+None pass ✓')

    # ── 10. equity parse (the D3 BLOCKER) + band guard (agent-5) ───────
    # The REAL clearinghouseState shape: accountValue nested under
    # marginSummary, numeric strings — the old parse read a nonexistent
    # top-level key and returned None forever (dark ladder).
    _orig_hl_info = HLE._hl_info
    HLE._hl_info = lambda q: {
        'marginSummary': {'accountValue': '16.11', 'withdrawable': '8.02'},
        'crossMarginSummary': {},
        'assetPositions': [],
    }
    acct = HLE.get_account_value_curl()
    assert acct['account_value'] == 16.11, acct          # nested + coerced
    assert acct['withdrawable'] == 8.02, acct
    HLE._hl_info = lambda q: {}                          # HL rate-limit shape
    acct = HLE.get_account_value_curl()
    assert acct.get('account_value') is None, acct       # None -> heat defers
    HLE._hl_info = _orig_hl_info
    import brain as BRAIN2
    assert BRAIN2._prearmed_add_band_ok('SHORT', 'garbage') is True   # fail-open
    assert BRAIN2._prearmed_add_band_ok('LONG', [1]) is True          # fail-open
    print('10 equity parse (nested/coerced/None) + band uncoercible-RSI fail-open ✓')

    # ── 11. E1 helper contract (the REAL nested helper, via the flag) ──
    import hermes_constants as HC
    import atr_cache as _AC
    _orig_atr = getattr(_AC, 'get_atr', None)
    try:
        # flag OFF (the module-level state these tests ran under) -> OFF
        # sentinel, no queries
        r = TW._momentum_confirm('x', 'BTC', 'long', 60000.0, {})
        assert r is TW._MOM_OFF, r
        # flag ON + ATR miss -> DEFER (fail-safe, no candles needed)
        HC.MOMENTUM_CONFIRM_ENABLED = True
        if _orig_atr is not None:
            _AC.get_atr = lambda *a, **k: None
            try:
                r = TW._momentum_confirm('y', 'BTC', 'long', 60000.0, {})
                assert r is TW._MOM_DEFER, r
            finally:
                _AC.get_atr = _orig_atr
        print('11 E1 helper: flag-off -> OFF; flag-on + ATR-miss -> DEFER ✓')
    finally:
        HC.MOMENTUM_CONFIRM_ENABLED = False   # leave the machine tests' state

    shutil.rmtree(_tmp, ignore_errors=True)
    print('\nALL PENDING-MACHINE TESTS PASS')


if __name__ == '__main__':
    main()
