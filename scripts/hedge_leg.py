#!/usr/bin/env python3
"""
Hedge leg — opposite-position experiment (spec: plans/2026-11-23_btc-hedge-account-spec.md).

When a main ai-trader BTC trade opens on Hyperliquid, open a 1:1 opposite leg
as its OWN trades row so both legs are tracked and stopped INDEPENDENTLY by
the existing exit machinery (manual_exit_manager trail + position_manager hit
checks + close_paper_position).

Modes (hermes_constants.HEDGE_MODE):
  off     — never open a hedge leg.
  shadow  — insert a paper=true row (signal '<orig>-hedge') linked to the main
            trade via _signal_metadata.hedge_of. Existing paper machinery runs
            the leg; zero real money. THIS IS THE CURRENT MODE.
  live    — REFUSES to open. Account-2 exit routing (guardian closes / TPSL /
            reconciliation against HEDGE_ACCOUNT_ADDRESS) is not built yet —
            fail-closed so flipping the constant cannot strand unmanageable
            real positions. Build the live path per spec before enabling.

Hazard contract (why '-hedge' rows are excluded from ~30 queries elsewhere):
  * guardian / cut_loser / profit_monster / sniper close HL positions BY TOKEN
    on the MAIN account — they must never act on a hedge row (it would close
    the main leg's real position).
  * position counts / dup guards / watchdog gates must not see shadow rows
    (shadow = zero impact on real trading decisions).
  * position_manager MUST see them (exit management) — that is the one place
    they belong: get_open_positions + the per-row close/trail paths.
"""
import json
import psycopg2
import psycopg2.extras

from hermes_constants import HEDGE_MODE, HEDGE_SIGNALS, HEDGE_COINS, HEDGE_SIZE_MULT

HEDGE_SUFFIX = '-hedge'


def is_hedge_signal(signal) -> bool:
    """True for hedge-leg rows (e.g. 'ai-trader-pending-hedge')."""
    return str(signal or '').endswith(HEDGE_SUFFIX)


def should_hedge(main_row: dict) -> bool:
    """Gate the experiment: mode, scope (signal), coin, real main trade only."""
    if HEDGE_MODE not in ('shadow', 'live'):
        return False
    if not main_row:
        return False
    if main_row.get('paper'):
        return False                      # hedge pairs with REAL main legs only
    if str(main_row.get('signal') or '') not in HEDGE_SIGNALS:
        return False
    return str(main_row.get('token') or '').upper() in {
        c.upper() for c in HEDGE_COINS}


def _flip_level(level, entry: float):
    """Mirror a price level around entry: LONG stop below → SHORT stop same
    distance above. Distance-preserving, so both legs honor the trade's own
    SL/TP distances with sides flipped."""
    if level is None:
        return None
    try:
        lvl = float(level)
    except (TypeError, ValueError):
        return None
    if lvl <= 0 or entry <= 0:
        return None
    return round(2 * entry - lvl, 8)


def build_hedge_row(main: dict, mode: str) -> dict:
    """Flip the main row into its opposite-direction hedge twin (1:1 notional)."""
    direction = 'SHORT' if str(main.get('direction') or '').upper() == 'LONG' else 'LONG'
    entry = float(main.get('hl_entry_price') or main.get('entry_price') or 0)
    if entry <= 0:
        raise ValueError(f"hedge: main row has no entry price (id={main.get('id')})")
    mult = float(HEDGE_SIZE_MULT or 1.0)
    amount = (float(main.get('amount_usdt') or 0)) * mult
    notional = main.get('hl_notional_usdt')
    notional = (float(notional) * mult) if notional is not None else None

    # Seed peak columns exactly like brain.py does for a fresh trade.
    highest = entry if direction == 'LONG' else 0
    lowest = entry if direction == 'SHORT' else 0

    try:
        meta = dict(main.get('_signal_metadata') or {})
        if isinstance(main.get('_signal_metadata'), str):
            meta = json.loads(main['_signal_metadata'])
    except (ValueError, TypeError):
        meta = {}
    meta['hedge_of'] = main.get('id')
    meta['hedge_mode'] = mode

    return {
        'token': main.get('token'),
        'direction': direction,
        'amount_usdt': amount,
        'entry_price': entry,
        'exchange': main.get('exchange') or 'Hyperliquid',
        'strategy': main.get('strategy'),
        'paper': True,                    # shadow = paper; live path (future) sets False
        'stop_loss': _flip_level(main.get('stop_loss'), entry),
        'target': _flip_level(main.get('target'), entry),
        'server': main.get('server') or 'Hermes',
        'status': 'open',
        'signal': f"{main.get('signal')}{HEDGE_SUFFIX}",
        'confidence': main.get('confidence'),
        'sl_distance': main.get('sl_distance'),
        'trailing_activation': main.get('trailing_activation'),
        'trailing_distance': main.get('trailing_distance'),
        'trailing_phase2_dist': main.get('trailing_phase2_dist'),
        'leverage': main.get('leverage'),
        'experiment': main.get('experiment'),
        'flipped_from_trade': 0,
        'flip_variant': main.get('flip_variant'),
        'hl_entry_price': entry,
        'hl_notional_usdt': notional,
        'highest_price': highest,
        'lowest_price': lowest,
        'signal_z_score': main.get('signal_z_score'),
        'signal_rsi_14': main.get('signal_rsi_14'),
        'signal_macd_hist': main.get('signal_macd_hist'),
        'signal_macd_value': main.get('signal_macd_value'),
        'signal_macd_signal': main.get('signal_macd_signal'),
        'signal_momentum_state': main.get('signal_momentum_state'),
        'signal_z_score_tier': main.get('signal_z_score_tier'),
        'signal_decision': main.get('signal_decision'),
        'signal_leverage': main.get('signal_leverage'),
        'signal_created_at': main.get('signal_created_at'),
        'test_sl_variant': main.get('test_sl_variant'),
        'test_timing_variant': main.get('test_timing_variant'),
        'test_trailing_variant': main.get('test_trailing_variant'),
        '_signal_metadata': json.dumps(meta, default=str),
        '_exp_metadata': main.get('_exp_metadata') or '{}',
        'regime': main.get('regime'),
        'volatility_regime': main.get('volatility_regime'),
    }


_COLS = [
    'token', 'direction', 'amount_usdt', 'entry_price', 'exchange', 'strategy',
    'paper', 'stop_loss', 'target', 'server', 'status', 'signal', 'confidence',
    'sl_distance', 'trailing_activation', 'trailing_distance',
    'trailing_phase2_dist', 'leverage', 'experiment', 'flipped_from_trade',
    'flip_variant', 'hl_entry_price', 'hl_notional_usdt', 'highest_price',
    'lowest_price', 'signal_z_score', 'signal_rsi_14', 'signal_macd_hist',
    'signal_macd_value', 'signal_macd_signal', 'signal_momentum_state',
    'signal_z_score_tier', 'signal_decision', 'signal_leverage',
    'signal_created_at', 'test_sl_variant', 'test_timing_variant',
    'test_trailing_variant', '_signal_metadata', '_exp_metadata', 'regime',
    'volatility_regime',
]


def _connect():
    from _secrets import BRAIN_PASSWORD, BRAIN_HOST
    return psycopg2.connect(host=BRAIN_HOST, dbname='brain', user='postgres',
                            password=BRAIN_PASSWORD, connect_timeout=5)


def maybe_open_hedge(main_trade_id, conn=None) -> dict:
    """Open the hedge twin for a just-opened main trade. Never raises — the
    main trade must not be affected by hedge failures.

    `conn` is for tests (caller-owned transaction, rolled back by the caller);
    production passes None and gets its own short-lived connection.
    """
    result = {'success': False, 'reason': 'not_eligible'}
    own_conn = None
    try:
        if HEDGE_MODE not in ('shadow', 'live'):
            return result
        own_conn = conn is None
        cn = conn or _connect()
        try:
            cur = cn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT * FROM trades WHERE id = %s", (int(main_trade_id),))
            main = cur.fetchone()
            if not main:
                return {'success': False, 'reason': 'main_row_missing'}
            main = dict(main)
            if not should_hedge(main):
                return result
            if HEDGE_MODE == 'live':
                # Fail-closed: account-2 exit routing not built yet (spec).
                print(f"[hedge_leg] ❌ HEDGE_MODE='live' but account-2 exit routing "
                      f"is NOT implemented — refusing to open a real hedge leg for "
                      f"trade #{main_trade_id} ({main.get('token')}). Main trade unaffected.")
                return {'success': False, 'reason': 'live_routing_not_implemented'}

            row = build_hedge_row(main, HEDGE_MODE)
            sql = (f"INSERT INTO trades ({', '.join(_COLS)}, open_time) "
                   f"VALUES ({', '.join(['%s'] * len(_COLS))}, NOW()) RETURNING id")
            cur.execute(sql, tuple(row[c] for c in _COLS))
            hedge_id = cur.fetchone()['id']
            if conn is None:
                cn.commit()
            print(f"[hedge_leg] 🧪 {HEDGE_MODE} hedge leg opened: trade #{hedge_id} "
                  f"{row['token']} {row['direction']} @ {row['entry_price']} "
                  f"(pair of #{main_trade_id} {main.get('signal')})")
            result = {'success': True, 'hedge_trade_id': hedge_id,
                      'direction': row['direction'], 'entry_price': row['entry_price']}
            return result
        finally:
            if own_conn:
                cn.close()
    except Exception as e:
        print(f"[hedge_leg] ⚠️ hedge open failed for main #{main_trade_id}: "
              f"{type(e).__name__}: {e} — main trade unaffected")
        return {'success': False, 'reason': f'error: {type(e).__name__}: {e}'}


if __name__ == '__main__':
    # Self-check: gate logic + row flip math (no DB writes).
    fake = {'id': 1, 'token': 'BTC', 'direction': 'LONG', 'paper': False,
            'signal': 'ai-trader-pending', 'hl_entry_price': 100000.0,
            'stop_loss': 99000.0, 'target': 103000.0, 'amount_usdt': 22.0,
            'hl_notional_usdt': 110.0, 'leverage': 5, 'server': 'Hermes'}
    r = build_hedge_row(fake, 'shadow')
    assert r['direction'] == 'SHORT', r['direction']
    assert r['stop_loss'] == 101000.0, r['stop_loss']       # mirrored +1%
    assert r['target'] == 97000.0, r['target']              # mirrored −3%
    assert r['signal'] == 'ai-trader-pending-hedge'
    assert r['paper'] is True and r['hl_entry_price'] == 100000.0
    assert json.loads(r['_signal_metadata'])['hedge_of'] == 1
    assert is_hedge_signal('ai-trader-pending-hedge')
    assert not is_hedge_signal('ai-trader-pending')
    assert should_hedge(fake) is True
    assert should_hedge({**fake, 'paper': True}) is False
    assert should_hedge({**fake, 'signal': 'ai-trader-manual'}) is False
    assert should_hedge({**fake, 'token': 'HYPE'}) is False
    print("hedge_leg self-check OK")
