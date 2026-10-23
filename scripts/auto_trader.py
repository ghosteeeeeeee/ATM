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
        # HIT: price crossed the trigger
        hit = (price <= h['trigger']) if h['direction'] == 'long' \
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
            # R:R backfill (gap fix): planned from armed levels, real with the
            # standard slip buffer (~0.12% of trigger ≈ 100pts at 81k) — same
            # convention as the full-analysis skill's planned-vs-real quoting.
            if direction == 'long':
                reward, risk = h['tp'] - h['trigger'], h['trigger'] - h['sl']
            else:
                reward, risk = h['trigger'] - h['tp'], h['sl'] - h['trigger']
            slip = h['trigger'] * 0.0012
            planned_rr = round(reward / risk, 2) if risk > 0 else None
            real_rr = round(reward / (risk + slip), 2) if risk > 0 else None
            DB.update_hypothetical(h['order_id'], status='stopped' if sl_hit else 'tp',
                                   ts_closed=time.time(), exit_price=exit_px,
                                   pnl_pct=round(move, 4),
                                   pnl_usdt=round(pnl_usd, 4))
            DB.record_attribution({
                'trade_id': f"shadow:{h['order_id']}",
                'direction': direction, 'regime_at_entry': h['regime_at_entry'],
                'entry_quality': 'shadow_triggered',
                'planned_rr': planned_rr, 'real_rr': real_rr,
                'pnl_pct': round(move, 4), 'pnl_usdt': round(pnl_usd, 4),
                'exit_reason': exit_reason, 'won': won,
                'lesson_tags': ['shadow', exit_reason]})
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
    summary = {'enabled': True, 'mode': cfg.get('mode', 'shadow')}

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

    # 3 TRACK existing hypotheticals FIRST (E4 fix: resolve hits before any
    # supersede logic can touch them — a leg crossed this cycle but
    # structure-shifted would have been superseded, losing the fill)
    events = track_hypotheticals(cfg, size)
    summary['hypo_events'] = events
    for e in events:
        DB.log_event('INFO', f"hypothetical: {e}")

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
                if keep:
                    continue  # fresh armed leg exists for this direction
                # E2 checklist: never arm an already-crossed (ITM) level
                already = (price_now <= o['trigger']) if leg == 'long' \
                    else (price_now >= o['trigger'])
                if already:
                    DB.log_event('WARN', f"cycle {cycle_id}: {leg} trigger "
                                         f"{o['trigger']} already crossed by "
                                         f"price {price_now} — leg skipped")
                    continue
                order_id = f"btc-auto-{cycle_id}-{leg}"
                DB.record_order(did, leg, {**o, 'order_id': order_id},
                                'shadow_armed', size, cfg.get('leverage_max', 5))
                DB.upsert_hypothetical(
                    {'order_id': order_id, 'direction': leg,
                     'trigger': o['trigger'], 'sl': o['sl'], 'tp': o['tp']},
                    decision['regime_state'], size)
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
