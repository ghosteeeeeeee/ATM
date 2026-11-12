#!/usr/bin/env python3
"""
auto_trader — orchestrator for the autonomous BTC loop (spec v2, phase 0).

run_cycle(): ANALYZE → DECIDE → JOURNAL → TRACK HYPOTHETICALS →
ATTRIBUTE RESOLUTIONS → SELF-TUNE LOG → PAUSE CHECKS.

Phase 0 (shadow): everything writes to auto_trader.db. Orders are NOT
placed — hypotheticals are paper-tracked against real price. Zero live
effect. Live phases reuse this same cycle with mode != shadow.

Called from trade_watchdog after analyze, gated by config.enabled.
"""
import os
import sys
import json
import time
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA
import auto_trader_db as DB
import auto_analysis as AA

CONFIG_PATH = os.path.join(HERMES_DATA, 'auto_trader_config.json')


def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {'enabled': False, 'mode': 'shadow', 'coin_whitelist': ['BTC']}


def get_open_btc():
    """Open BTC positions from brain PostgreSQL (empty on failure)."""
    try:
        import psycopg2
        from _secrets import BRAIN_PASSWORD, BRAIN_HOST
        conn = psycopg2.connect(host=BRAIN_HOST, dbname='brain', user='postgres',
                                password=BRAIN_PASSWORD, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT id, token, direction, entry_price, current_price, "
                    "stop_loss, target, pnl_pct, signal FROM trades "
                    "WHERE status='open' AND token='BTC'")
        rows = [{'id': r[0], 'token': r[1], 'direction': r[2],
                 'entry_price': r[3], 'current_price': r[4], 'stop_loss': r[5],
                 'target': r[6], 'pnl_pct': r[7], 'signal': r[8]}
                for r in cur.fetchall()]
        cur.close()
        conn.close()
        return rows
    except Exception:
        return None  # DB failure — caller decides (fail-safe: no decision)


def track_hypotheticals(cfg, size):
    """Advance shadow hypotheticals: armed → hit → stopped/tp/expired."""
    events = []
    price = None
    try:
        ind = AA.tf_indicators('BTC', '1m')
        price = ind['price'] if ind else None
    except Exception:
        return events
    if not price:
        return events

    now = time.time()
    for h in DB.get_hypotheticals('armed'):
        # HIT: price crossed the trigger — direction from trigger_dir (which
        # side price must cross). Legacy rows (armed before the §12 mapping
        # flip) were fade-style: long fired below / short above; migration
        # backfills those, this fallback covers anything older.
        tdir = h['trigger_dir'] or ('below' if h['direction'] == 'long' else 'above')
        hit = (price <= h['trigger']) if tdir == 'below' \
            else (price >= h['trigger'])
        if hit:
            # BUG A fix: NO attribution at hit — one row per resolution only
            # (trade_id UNIQUE; the zero-pnl hit row diluted the scorecard
            # and tripped pause after 2 losses).
            DB.update_hypothetical(h['order_id'], status='hit',
                                   ts_hit=now,
                                   exit_price=h['trigger'],
                                   regime_at_entry=h['regime_at_entry'])
            events.append(f"{h['order_id']} shadow HIT at trigger {h['trigger']}")
        elif now - h['ts_armed'] > 48 * 3600:
            DB.update_hypothetical(h['order_id'], status='expired',
                                   ts_closed=now, exit_price=price)
            events.append(f"{h['order_id']} expired (48h)")
    for h in DB.get_hypotheticals('hit'):
        direction = h['direction']
        sl_hit = (price <= h['sl']) if direction == 'long' else (price >= h['sl'])
        tp_hit = (price >= h['tp']) if direction == 'long' else (price <= h['tp'])
        if sl_hit or tp_hit:
            # conservative: if ambiguous same-evaluation, SL wins
            exit_px, won = (h['sl'], 0) if sl_hit else (h['tp'], 1)
            move = ((exit_px - h['trigger']) / h['trigger'] * 100
                    if direction == 'long' else
                    (h['trigger'] - exit_px) / h['trigger'] * 100)
            pnl_usd = move / 100 * h['size']
            exit_reason = 'shadow_sl' if sl_hit else 'shadow_tp'
            # R:R: planned from armed levels; real with the skill's slip buffer
            # = max(0.12% of trigger, 150pt floor — the skill's BTC chop floor,
            # bug_hunter parity fix; ~97pt at 81k was below the 150-250 range).
            if direction == 'long':
                reward, risk = h['tp'] - h['trigger'], h['trigger'] - h['sl']
            else:
                reward, risk = h['trigger'] - h['tp'], h['sl'] - h['trigger']
            slip = max(h['trigger'] * 0.0012, 150.0)
            planned_rr = round(reward / risk, 2) if risk > 0 else None
            real_rr = round(reward / (risk + slip), 2) if risk > 0 else None
            # Attribution BEFORE the status flip (crash-between protection:
            # INSERT OR IGNORE dedupes if we crash after this and the next
            # cycle re-resolves from 'hit'; the old order lost the row).
            DB.record_attribution({
                'trade_id': f"shadow:{h['order_id']}",
                'direction': direction, 'regime_at_entry': h['regime_at_entry'],
                'entry_quality': 'shadow_triggered',
                'planned_rr': planned_rr, 'real_rr': real_rr,
                'pnl_pct': round(move, 4), 'pnl_usdt': round(pnl_usd, 4),
                'exit_reason': exit_reason, 'won': won,
                'lesson_tags': ['shadow', exit_reason]})
            DB.update_hypothetical(h['order_id'], status='stopped' if sl_hit else 'tp',
                                   ts_closed=time.time(), exit_price=exit_px,
                                   pnl_pct=round(move, 4),
                                   pnl_usdt=round(pnl_usd, 4))
            events.append(f"{h['order_id']} shadow {'TP' if won else 'SL'} "
                          f"({move:+.2f}%)")
    return events


def live_attribution(cfg):
    """Phase 1+: attribute real closed ai-trader-auto% trades (no-op in shadow
    unless real trades exist from live phases)."""
    try:
        import psycopg2
        from _secrets import BRAIN_PASSWORD, BRAIN_HOST
        conn = psycopg2.connect(host=BRAIN_HOST, dbname='brain', user='postgres',
                                password=BRAIN_PASSWORD, connect_timeout=5)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, direction, pnl_pct, pnl_usdt, exit_reason, signal "
            "FROM trades WHERE status='closed' AND signal LIKE 'ai-trader-auto%' "
            "AND close_time > NOW() - INTERVAL '2 hours' ORDER BY close_time DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception:
        return []
    done = [r[0] for r in DB._exec(
        "SELECT trade_id FROM attribution WHERE trade_id LIKE 'trade:%'",
        fetch='all')]
    out = []
    for r in rows:
        tid = f"trade:{r[0]}"
        if tid in done:
            continue
        pnl_pct = float(r[2] or 0)
        DB.record_attribution({
            'trade_id': tid, 'direction': r[1].lower(),
            'regime_at_entry': 'unknown', 'entry_quality': 'live',
            'pnl_pct': pnl_pct, 'pnl_usdt': float(r[3] or 0),
            'exit_reason': r[4], 'won': 1 if pnl_pct > 0 else 0,
            'lesson_tags': ['live', r[4] or '']})
        out.append(tid)
    return out


def bounded_self_tune(cfg):
    """Shadow-safe: compute size multiplier from scorecard, LOG only + apply
    to future hypothetical sizes. Never touches leverage/SL/caps/skills."""
    sc = DB.get_scorecard()
    if not sc or sc.get('n', 0) < 10:
        return None
    bounds = cfg.get('self_tuning_bounds', {'min': 0.5, 'max': 1.0})
    # BUG C fix: wr=0.0 is falsy — `or 50` made a 0% scorecard look like 50%
    wr = 50 if sc.get('wr') is None else sc['wr']
    # size mult: WR 40% → 0.5, WR 60% → 1.0 (linear within bounds)
    mult = round(max(bounds.get('min', 0.5),
                     min(bounds.get('max', 1.0), 0.5 + (wr - 40) * 0.025)), 2)
    prev = DB._exec("SELECT new_value FROM self_tuning "
                    "WHERE parameter='size_mult' ORDER BY ts DESC LIMIT 1",
                    fetch='one')
    old = prev['new_value'] if prev else 1.0
    if abs(old - mult) >= 0.05:
        DB.record_self_tune('size_mult', old, mult, json.dumps(bounds),
                            f"scorecard wr={wr}% n={sc.get('n')}")
        return {'old': old, 'new': mult, 'wr': wr}
    return None


def pause_checks(cfg, summary):
    """Consecutive LIVE losses (config count) or daily cap → event + pause flag.
    Shadow rows never trip it (they are hypotheticals, not risk taken);
    hardcoded count replaced by config consecutive_loss_pause."""
    sc = DB.get_scorecard()
    need = int(cfg.get('consecutive_loss_pause', 3))
    # Live-prefixed rows only — 'trade:%' (BUG A note: shadow: rows mixed in
    # would trip pause from hypothetical losses)
    live = DB._exec("SELECT won FROM attribution WHERE trade_id LIKE 'trade:%' "
                    "ORDER BY ts_closed DESC LIMIT ?", (need,), fetch='all')
    if len(live) == need and all(r['won'] == 0 for r in live):
        DB.log_event('ESCALATE', f"{need} consecutive LIVE losses — pause "
                                 f"flagged for CEO (config unchanged by system)")
        summary['pause_flag'] = f'{need}_consecutive_losses'
    pnl = (sc.get('pnl_usdt') or 0) if sc else 0
    if sc and pnl <= cfg.get('daily_loss_cap_pct', -3.0):
        DB.log_event('ESCALATE', "daily loss cap reached — shadow pause "
                                 "flagged for CEO")
        summary.setdefault('pause_flag', 'daily_cap')


def _structure_sl(decision, leg):
    """Structure-break stop at BIRTH: just beyond the MAJOR (1h) swing —
    the trade exits when MAJOR structure actually breaks. (CEO 2026-11-10:
    the 15m reference got stop-hunted by the flag's own interior whipsaw —
    #16851/52's 15m stop 74114 was hunted at 74285, then the real drop
    came; #16846's trailed stop 74727 died on the 74,5xx retest. Flags
    hunt their interior — the stop references the PATTERN BOUNDARY.
    15m fallback if the 1h snapshot is missing.)"""
    sd = (decision.get('structure_detail') or {}).get('1h') or {}
    if not (sd.get('sh') and sd.get('sl') and sd.get('atr')):
        sd = (decision.get('structure_detail') or {}).get('15m') or {}
    sh, sl, atr = sd.get('sh'), sd.get('sl'), sd.get('atr')
    if not (sh and sl and atr):
        return None
    if leg == 'long':
        return round(float(sl) - 0.10 * float(atr), 8)
    return round(float(sh) + 0.10 * float(atr), 8)


def _arm_real_leg(order_id, leg, o, size, cfg, atr_1h):
    """mode=live (spec v2 §2): write a GATED bracket leg into the real
    pending-orders config — the 1-minute pipeline monitor
    (pending_order_monitor) executes it. Gates already ran upstream
    (shape checklist, ITM skip, real R:R >= 1.0). Dedupe: skip when an
    unfired same-direction order sits within 0.3x 1h-ATR of this trigger
    (stacking twins from both callers). Returns 'armed'|'covered'|'error'.
    """
    path = os.path.join(HERMES_DATA, 'pending_orders.json')
    try:
        with open(path) as f:
            pcfg = json.load(f)
    except Exception:
        pcfg = {}
    orders = pcfg.get('orders') if isinstance(pcfg, dict) else None
    if not isinstance(orders, list):
        orders = []
    # F4 (bug_hunter MED): a CONSUMED order (fired/error in the one-shot
    # state) must not 'cover' a new arm — covering a filled order would
    # leave shadow/live divergence (hypothetical armed, no real order).
    # LOW-3: unreadable state fails CLOSED (refuse to arm — the fire path
    # refuses to trade under the same condition; failing open here would
    # recreate the divergence exactly under corruption).
    try:
        with open(os.path.join(HERMES_DATA, 'pending_orders_state.json')) as f:
            pstate = json.load(f)
        if not isinstance(pstate, dict):
            raise ValueError('state not a dict')
    except Exception as e:
        DB.log_event('WARN', f'arm skipped FAIL-CLOSED — one-shot state '
                             f'unreadable: {e}')
        return 'error:state-unreadable'
    # 0.5x ATR (was 0.3): the engine kept re-arming a same-direction twin
    # ~230pts from the CEO's level — overlapping triggers broke the
    dedupe = 0.5 * (atr_1h or 400)
    for ex in orders:
        if ex.get('direction') != leg:
            continue
        _st = pstate.get(ex.get('id'))
        if not isinstance(_st, dict):       # LOW-2: truthy non-dict guard
            _st = {}
        if _st.get('status') in ('fired', 'error'):
            continue                      # consumed — covers nothing
        if abs(float(ex.get('trigger_price') or 0) - o['trigger']) < dedupe:
            # covered = idempotent skip, but an AUTO-owned order's SL syncs
            # to the structure stop (never CEO-owned orders — those levels
            # are the CEO's). Keeps real order == hypothetical after the
            # structure-at-birth change.
            if (str(ex.get('id', '')).startswith('btc-auto-')
                    and abs(float(ex.get('sl') or 0) - float(o['sl'])) > 1):
                ex['sl'] = float(o['sl'])
                try:
                    tmp = path + '.tmp'
                    with open(tmp, 'w') as f:
                        json.dump({'orders': orders}, f, indent=1)
                    os.replace(tmp, path)
                except Exception:
                    pass
            return 'covered'
    tdir = o.get('trigger_dir') or ('above' if leg == 'long' else 'below')
    new = {
        'id': order_id,
        'coin': 'BTC',
        'direction': leg,
        'trigger': tdir,
        'trigger_price': float(o['trigger']),
        'amount_usdt': round(float(size), 2),
        'leverage': int(cfg.get('leverage_max', 5)),
        'sl': float(o['sl']),
        'target': float(o['tp']),
        'confidence': 60,
        'dynamic_sl': False,
        'note': (f'auto_trader LIVE arm (spec v2 §2, mode=live phase 1, '
                 f'cycle {order_id}). Gates: shape checklist OK, not ITM, '
                 f'real R:R >= 1.0 with 0.12%/150pt slip. Mapping: lower '
                 f'break = SHORT / upper = LONG via trigger_dir={tdir}. '
                 f'dynamic_sl=false — structure-fixed stop: the watchdog '
                 f'full-analysis tweak owns the SL (stop beyond retest per '
                 f'CEO 2026-11-09 #16827 lesson); BE/trail stands down. '
                 f'Shadow evidence: 18d / 54 resolved hypotheticals.'),
    }
    orders.append(new)
    try:
        tmp = path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump({'orders': orders}, f, indent=1)
        os.replace(tmp, path)
        return 'armed'
    except Exception as e:
        return f'error:{e}'


def tweak_structure_fixed(decision, open_positions):
    """Fluid structure-follow stop tuning (CEO 2026-11-10: "the stop is
    trailing so we book profits... fluid enough to allow the chop and
    survive unless structure is broken... the watchdog is adjusting the
    stops as the trade progresses").

    Runs on EVERY managed open trade (ai-trader-*) — the mxm trail books
    profits on 2-min pipeline cycles with the fluid profile (skip-BE /
    wide giveback / min-lock), THIS tweak follows structure every 30-min
    watchdog cycle. The two coexist without fighting:
      R1 structure-follow — risk-side stop (short: stop ≥ entry, long:
         stop ≤ entry) ALIGNS to structure either direction (survival IS
         structure — the #16834 fix: stop pinned 130pts above structure
         in the noise, move ran +691; ±0.5% entry cap removed 2026-11-09).
         Profit-side stop: only DEEPENS (never relaxes a lock) — so the
         watchdog can't undo what the trail booked, and the trail's
         ratchet can't undo an alignment. Never onto the live price side.
      R2 rule-10 TP — a TP overshooting the FIRST opposing structure by
         more than 1 ATR snaps into it (short: 15m SL + 0.05 ATR;
         long: 15m SH − 0.05 ATR), price-side guarded (F3).
    Returns tweak dicts for the cycle summary.
    """
    tweaks = []
    # R1 stops follow MAJOR (1h) structure — CEO 2026-11-10 (15m interior
    # swings get hunted by flag whipsaws: #16851/52 stop 74114 hunted at
    # 74285, real drop followed; the stop references the pattern boundary).
    sd = (decision.get('structure_detail') or {}).get('15m') or {}
    sh, sl, atr = sd.get('sh'), sd.get('sl'), sd.get('atr')   # R2 TP side (15m first-opposing)
    sd_h = (decision.get('structure_detail') or {}).get('1h') or {}
    sh_h, sl_h, atr_h = sd_h.get('sh'), sd_h.get('sl'), sd_h.get('atr')
    if not (sh and sl and atr):
        return tweaks
    try:
        import psycopg2
        from _secrets import BRAIN_PASSWORD, BRAIN_HOST
        conn = psycopg2.connect(host=BRAIN_HOST, dbname='brain',
                                user='postgres', password=BRAIN_PASSWORD,
                                connect_timeout=5)
    except Exception:
        return tweaks
    try:
        cur = conn.cursor()

        def _apply_stop(new_val, old, pid):
            """CAS stop write + log. Returns True on rowcount."""
            new_val = round(new_val, 8)
            cur.execute("UPDATE trades SET stop_loss=%s WHERE id=%s "
                        "AND status='open' AND stop_loss=%s",
                        (new_val, pid, old))
            if cur.rowcount:
                conn.commit()
                t = {'trade': pid, 'field': 'stop_loss',
                     'old': old, 'new': new_val, 'rule': 'R1'}
                tweaks.append(t)
                DB.log_event('INFO', f"tweak {t}")
                return True
            return False

        # ── STRUCTURE-LAG TRAILING (CEO 2026-11-12): "stops should only
        # move when new structure is formed — we bump the stop to the now
        # OLD structure, so if that is broken we get taken out."
        # The stop NEVER moves on interior noise (the #16871 lesson: stop
        # sat at the CURRENT structure, a 74121 bounce tagged it, +0.99%
        # taken, direction kept going to 73584). It steps ONLY when the
        # 1h zigzag confirms a new swing, and it steps to the PREVIOUS
        # (now-old) swing — one full structure behind the newest.
        # State: data/tweak_struct_state.json (72h prune on save).
        import os as _os, json as _json
        from paths import HERMES_DATA as _HD
        _st_path = _os.path.join(_HD, 'tweak_struct_state.json')
        try:
            with open(_st_path) as _f:
                _smap = _json.load(_f)
        except Exception:
            _smap = {}
        _st_dirty = [False]           # nonlocal-ish for nested helper

        def _lag_stop(pid, side, cur_sh, cur_sl, cur_atr, price, stop):
            key = str(pid)
            prev = _smap.get(key)
            if side == 'SHORT':
                if not (cur_sh and cur_atr):
                    return
                # birth → current structure; after that → the now-old one
                base = cur_sh if prev is None else float(prev['sh'])
                want = base + 0.10 * cur_atr
                want = max(want, price * 1.001)     # never at/below price
            else:
                if not (cur_sl and cur_atr):
                    return
                base = cur_sl if prev is None else float(prev['sl'])
                want = base - 0.10 * cur_atr
                if want >= price:
                    want = price * 0.999           # never at/above price
            if prev is None:
                if abs(stop - want) > 1:
                    _apply_stop(want, stop, pid)
                _smap[key] = {'sh': cur_sh, 'sl': cur_sl, 'ts': time.time()}
                _st_dirty[0] = True
                return
            if cur_sh != prev['sh'] or cur_sl != prev['sl']:
                # NEW structure formed → bump to the now-old structure
                if abs(stop - want) > 1:
                    _apply_stop(want, stop, pid)
                _smap[key] = {'sh': cur_sh, 'sl': cur_sl, 'ts': time.time()}
                _st_dirty[0] = True
            # structure unchanged → the stop is NOT touched (the whole rule)

        for pos in open_positions or []:
            # Gate CHANGED 2026-11-10: no longer dynamic_sl-false only —
            # trail (2-min mxm, fluid profile) and this structure-follow
            # (30-min) now coexist on the same trade per CEO synthesis.
            sig = str(pos.get('signal') or '')
            if not any(t in sig for t in ('ai-trader-manual', 'ai-trader-pending',
                                          'ai-trader-auto')):
                continue
            entry = float(pos.get('entry_price') or 0)
            stop = float(pos.get('stop_loss') or 0)
            target = float(pos.get('target') or 0)
            price = float(pos.get('current_price') or 0)
            if not (entry and stop and target and price):
                continue
            d = str(pos.get('direction') or '').upper()
            if d == 'SHORT':
                # STRUCTURE-LAG trailing (CEO 2026-11-12): the stop moves
                # ONLY when the 1h zigzag forms a new swing, and then only
                # to the now-OLD swing — interior bounces never touch it
                # (#16871: current-structure stop tagged by a 74121 bounce,
                # +0.99% taken while direction ran to 73584).
                _lag_stop(pos['id'], 'SHORT', sh_h, sl_h, atr_h, price, stop)
                # F3 (bug_hunter MED): TP must stay BELOW live price for a
                # short — a structure snap already crossed = instant exit.
                if target < (sl - atr) and (sl + 0.05 * atr) < price * 0.999:
                    new_tp = round(sl + 0.05 * atr, 8)
                    cur.execute("UPDATE trades SET target=%s WHERE id=%s "
                                "AND status='open' AND target=%s",
                                (new_tp, pos['id'], target))
                    if cur.rowcount:
                        conn.commit()
                        t = {'trade': pos['id'], 'field': 'target',
                             'old': target, 'new': new_tp, 'rule': 'R2'}
                        tweaks.append(t)
                        DB.log_event('INFO', f"tweak {t}")
            elif d == 'LONG':
                # STRUCTURE-LAG mirror (CEO 2026-11-12): same rule —
                # move only on new 1h structure, bump to the now-old swing.
                _lag_stop(pos['id'], 'LONG', sh_h, sl_h, atr_h, price, stop)
                # F3 mirror: TP must stay ABOVE live price for a long
                if target > (sh + atr) and (sh - 0.05 * atr) > price * 1.001:
                    new_tp = round(sh - 0.05 * atr, 8)
                    cur.execute("UPDATE trades SET target=%s WHERE id=%s "
                                "AND status='open' AND target=%s",
                                (new_tp, pos['id'], target))
                    if cur.rowcount:
                        conn.commit()
                        t = {'trade': pos['id'], 'field': 'target',
                             'old': target, 'new': new_tp, 'rule': 'R2'}
                        tweaks.append(t)
                        DB.log_event('INFO', f"tweak {t}")
        # persist structure-lag state (72h prune, atomic — mirrors mxm)
        if _st_dirty[0]:
            _now = time.time()
            _smap = {k: v for k, v in _smap.items()
                     if float((v or {}).get('ts') or _now) > _now - 72 * 3600}
            _tmp = _st_path + '.tmp'
            with open(_tmp, 'w') as _f:
                _json.dump(_smap, _f)
            _os.replace(_tmp, _st_path)
        cur.close()
    finally:
        conn.close()
    return tweaks


def run_cycle():
    """Main entry. Returns a summary dict for the watchdog output/dashboard."""
    cfg = load_config()
    if not cfg.get('enabled'):
        return {'enabled': False, 'mode': cfg.get('mode', 'shadow')}
    DB.init_db()
    # BUG B fix: uuid suffix — same-second cycles must never collide on
    # order_id (UNIQUE upsert silently swallowed re-arms and reported
    # superseded ids as armed).
    import uuid
    cycle_id = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
    summary = {'enabled': True, 'mode': cfg.get('mode', 'shadow'),
               'shadow_armed': [], 'live_armed': [], 'tweaks': []}

    open_positions = get_open_btc()
    if open_positions is None:
        DB.log_event('WARN', 'brain DB unreachable — cycle skipped (fail-safe)')
        summary['skipped'] = 'db_unreachable'
        return summary

    # 1-2 ANALYZE + DECIDE
    decision = AA.build_decision(cycle_id, open_positions, cfg)
    did = DB.record_decision(decision)
    summary['decision'] = decision['decision']
    summary['scores'] = {'long': decision['score_long'],
                         'short': decision['score_short'],
                         'regime': decision['regime_state']}
    summary['price'] = decision['price']

    # size: config base × last self-tuned multiplier (bounds-clamped there)
    _mt = DB._exec("SELECT new_value FROM self_tuning WHERE parameter='size_mult' "
                   "ORDER BY ts DESC LIMIT 1", fetch='one')
    size = cfg.get('size_usdt', 11.10) * (_mt['new_value'] if _mt else 1.0)
    # HL MINIMUM NOTIONAL FLOOR (CEO 2026-11-09: "$11 incl. leverage or HL
    # will not place the order"): brain.py trade-add REJECTS amounts below
    # HL_MIN_NOTIONAL_USDT (brain.py:550 — a sub-$11 order burns the
    # one-shot state as an error at fire, never trading). Self-tuning's 0.66
    # multiplier had armed two $7.33 orders that would have died exactly
    # that way. Floor wins over the tuned multiplier; mult may still raise.
    from hermes_constants import HL_MIN_NOTIONAL_USDT
    if size < HL_MIN_NOTIONAL_USDT:
        DB.log_event('WARN', f'size {size:.2f} < HL min {HL_MIN_NOTIONAL_USDT} '
                             f'— floored (tuned mult overridden)')
        size = HL_MIN_NOTIONAL_USDT

    # 3 TRACK existing hypotheticals FIRST (E4 fix: resolve hits before any
    # supersede logic can touch them — a leg crossed this cycle but
    # structure-shifted would have been superseded, losing the fill)
    events = track_hypotheticals(cfg, size)
    summary['hypo_events'] = events
    for e in events:
        DB.log_event('INFO', f"hypothetical: {e}")

    # 3b LIVE TUNE (CEO 2026-11-09): with a position open, tune its TP/SL
    # per full-analysis structure — structure-fixed trades only.
    if cfg.get('mode') == 'live' and open_positions:
        try:
            summary['tweaks'] = tweak_structure_fixed(decision, open_positions)
        except Exception as e:
            DB.log_event('WARN', f'tweak_structure_fixed failed: {e}')

    # 4 JOURNAL + SHADOW-ARM hypotheticals
    if decision.get('decision') == 'BRACKET' and decision.get('bracket'):
        price_now = decision.get('price') or 0
        # Pre-write checklist (E2/spec §2): shape validity + not already ITM
        shape_ok = True
        for leg, o in decision['bracket'].items():
            if leg == 'long' and not (o['sl'] < o['trigger'] < o['tp']):
                shape_ok = False
            if leg == 'short' and not (o['tp'] < o['trigger'] < o['sl']):
                shape_ok = False
        if not shape_ok:
            DB.log_event('WARN', f"cycle {cycle_id}: bracket failed shape "
                                 f"checklist — not armed")
        else:
            # PER-LEG refresh (fix: partial supersede used to clear the whole
            # pair and re-arm both — a kept leg ended up armed alongside a new
            # twin of the same direction; observed live at 14:14). Each leg
            # refreshes independently; a direction is never double-armed.
            h1_atr = (decision.get('structure_detail', {}).get('1h') or {}).get('atr', 400) or 400
            armed_now = DB.get_hypotheticals('armed')
            for leg, o in decision['bracket'].items():
                # structure-break stop from birth (CEO 2026-11-09) — applied
                # BEFORE the gates so the real-R:R check prices the real risk
                _ssl = _structure_sl(decision, leg)
                if _ssl:
                    o = {**o, 'sl': _ssl}
                existing = [h for h in armed_now if h['direction'] == leg]
                keep = False
                for h in existing:
                    age_h = (time.time() - h['ts_armed']) / 3600
                    stale = age_h > 12  # E3: levels stale >12h → refresh
                    shifted = abs(o['trigger'] - h['trigger']) >= h1_atr
                    if stale or shifted:
                        DB.update_hypothetical(h['order_id'], status='superseded',
                                               ts_closed=time.time())
                        DB.log_event('INFO', f"superseded {h['order_id']} "
                                             f"({'stale %.0fh' % age_h if stale else 'ATR shift'})")
                    else:
                        keep = True  # levels fresh — this leg stays as-is
                        if cfg.get('mode') == 'live':
                            # Back-fill gap fix (2026-11-09 02:28): a leg
                            # armed while mode was still 'shadow' has NO real
                            # pending order — keep means the levels stand, so
                            # the REAL order must exist too. Dedupe inside
                            # makes repeat calls 'covered' (idempotent).
                            # Structure-break SL at birth (2026-11-09 17:00):
                            # kept legs also get the 15m-swing stop, with the
                            # shadow hypothetical synced so scoring matches
                            # what the real order carries.
                            _bo = {'trigger': h['trigger'], 'sl': h['sl'],
                                   'tp': h['tp'],
                                   'trigger_dir': (h['trigger_dir']
                                                   if 'trigger_dir' in h.keys()
                                                   else None)}
                            _bssl = _structure_sl(decision, leg)
                            if _bssl and abs(_bssl - float(h['sl'])) > 1:
                                _bo['sl'] = _bssl
                                try:
                                    DB.update_hypothetical(h['order_id'],
                                                           sl=_bssl)
                                except Exception:
                                    pass
                            res = _arm_real_leg(
                                h['order_id'], leg, _bo,
                                size, cfg, h1_atr)
                            summary['live_armed'].append(f'{leg}-kept:{res}')
                            if res == 'armed':
                                DB.log_event('INFO',
                                             f"cycle {cycle_id}: live "
                                             f"back-fill {h['order_id']} → armed "
                                             f"SL={_bo['sl']} (structure)")
                if keep:
                    continue  # fresh armed leg exists for this direction
                # E2 checklist: never arm an already-crossed (ITM) level.
                # Polarity from trigger_dir (continuation mapping: long
                # triggers ABOVE, short BELOW — the old direction-keyed
                # polarity skipped both legs as "crossed" after the flip).
                _tdir = o.get('trigger_dir') or \
                    ('above' if leg == 'long' else 'below')
                already = (price_now >= o['trigger']) if _tdir == 'above' \
                    else (price_now <= o['trigger'])
                if already:
                    DB.log_event('WARN', f"cycle {cycle_id}: {leg} trigger "
                                         f"{o['trigger']} already crossed by "
                                         f"price {price_now} — leg skipped")
                    continue
                # Arming gate (skill rule): a leg must clear ≥1.0 REAL R:R
                # (slip = max(0.12%, 150pt floor)) — never arm negative-R:R
                # geometry just because structure shifted.
                if leg == 'long':
                    _rwd, _rsk = o['tp'] - o['trigger'], o['trigger'] - o['sl']
                else:
                    _rwd, _rsk = o['trigger'] - o['tp'], o['sl'] - o['trigger']
                _slip = max(o['trigger'] * 0.0012, 150.0)
                _real = (_rwd / (_rsk + _slip)) if _rsk > 0 else 0
                if _real < 1.0:
                    DB.log_event('WARN', f"cycle {cycle_id}: {leg} real R:R "
                                         f"{_real:.2f} < 1.0 — leg not armed")
                    continue
                order_id = f"btc-auto-{cycle_id}-{leg}"
                _live = cfg.get('mode') == 'live'
                DB.record_order(did, leg, {**o, 'order_id': order_id},
                                'armed' if _live else 'shadow_armed',
                                size, cfg.get('leverage_max', 5))
                DB.upsert_hypothetical(
                    {'order_id': order_id, 'direction': leg,
                     'trigger': o['trigger'], 'sl': o['sl'], 'tp': o['tp'],
                     'trigger_dir': o.get('trigger_dir') or
                     ('above' if leg == 'long' else 'below')},
                    decision['regime_state'], size)
                if _live:
                    res = _arm_real_leg(order_id, leg, o, size, cfg, h1_atr)
                    summary['live_armed'].append(f'{leg}:{res}')
                    DB.log_event('INFO', f"cycle {cycle_id}: live arm "
                                         f"{order_id} {leg} @ {o['trigger']} "
                                         f"→ {res}")
            # Truthful report: whatever is armed in DB AFTER this cycle
            summary['shadow_armed'] = [h['order_id'] for h in
                                       DB.get_hypotheticals('armed')]
            if summary['shadow_armed']:
                DB.log_event('INFO', f"cycle {cycle_id}: shadow-armed "
                                     f"{summary['shadow_armed']} @ {price_now}")

    # 5 LEARN: live attribution + bounded self-tune
    live_attribution(cfg)
    tuned = bounded_self_tune(cfg)
    if tuned:
        summary['self_tuned'] = tuned
        DB.log_event('INFO', f"self-tune size_mult {tuned['old']}→{tuned['new']}")

    # 6 PAUSE CHECKS
    pause_checks(cfg, summary)

    # Dashboard feed
    summary['stats'] = DB.get_scorecard()
    summary['by_regime'] = DB.get_scorecard_by_regime()
    summary['by_direction'] = DB.get_scorecard_by_direction()
    summary['hypotheticals'] = len(DB.get_hypotheticals('armed')) + \
        len(DB.get_hypotheticals('hit'))
    summary['armed_detail'] = [
        {'order_id': h['order_id'], 'direction': h['direction'],
         'trigger': h['trigger'], 'sl': h['sl'], 'tp': h['tp'],
         'size': h['size'], 'regime': h['regime_at_entry'],
         'age_min': int((time.time() - h['ts_armed']) / 60),
         'dist_pct': (round((decision['price'] - h['trigger']) /
                            h['trigger'] * 100, 3)
                      if decision.get('price') and h['trigger'] else None)}
        for h in DB.get_hypotheticals('armed')]
    summary['recent_decisions'] = [
        {'ts': r['ts'], 'price': r['price'], 'regime': r['regime_state'],
         'score_long': r['score_long'], 'score_short': r['score_short'],
         'decision': r['decision']}
        for r in DB.recent_decisions(6)]
    summary['recent_trades'] = [
        {'ts': r['ts_closed'], 'direction': r['direction'],
         'regime': r['regime_at_entry'], 'pnl_pct': r['pnl_pct'],
         'pnl_usdt': r['pnl_usdt'], 'won': r['won'],
         'exit_reason': r['exit_reason']}
        for r in DB.recent_attribution(8)]
    summary['self_tuning_log'] = [
        {'ts': r['ts'], 'parameter': r['parameter'],
         'old': r['old_value'], 'new': r['new_value'], 'reason': r['reason']}
        for r in DB.recent_self_tuning(5)]
    return summary


if __name__ == '__main__':
    s = run_cycle()
    print(json.dumps(s, indent=1, default=str))
