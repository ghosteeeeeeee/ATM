#!/usr/bin/env python3
"""
hedge_watcher.py — event trigger for the hedge-shadow session (no LLM until an event).

Armed by the DSH session as a background job. Polls the brain DB every 30s and
EXITS (which pings the session via the job-completion notice) when either:
  1. a new ai-trader-pending / ai-trader-auto trade is PLACED (any coin), or
  2. any '-hedge' shadow twin CLOSES (exit verification event).

Everything before the event is pure psycopg2 — zero model involvement.
On start it baselines to the CURRENT max trade id / now, so pre-existing
history never fires it. State is also persisted so a re-arm after handling
an event does not re-fire on the same rows.

Usage: python3 hedge_watcher.py
"""
import json
import os
import sys
import time

import psycopg2

STATE_FILE = '/root/.hermes/data/hedge_watcher_state.json'
POLL_S = 30
AI_SIGNALS = ('ai-trader-pending', 'ai-trader-auto')


def connect():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _secrets import BRAIN_PASSWORD, BRAIN_HOST
    return psycopg2.connect(host=BRAIN_HOST, dbname='brain', user='postgres',
                            password=BRAIN_PASSWORD, connect_timeout=5)


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, ValueError, OSError):
        return None


def save_state(state):
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def baseline(cn):
    cur = cn.cursor()
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM trades WHERE signal IN %s",
                (AI_SIGNALS,))
    max_main = cur.fetchone()[0]
    state = {'armed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
             'last_main_id': int(max_main)}
    cur.close()
    save_state(state)
    return state


def fmt(rows, cols):
    return ' | '.join('='.join(str(v) for v in zip(cols, r)) for r in rows)


def check(cn, state):
    cur = cn.cursor()
    # Event 1: new ai-trader trade placed (any coin — BTC gets the hedge check,
    # other coins get a "no hedge applies" note)
    cur.execute("""
        SELECT id, token, direction, signal, status, entry_price, amount_usdt,
               open_time, stop_loss, target
        FROM trades
        WHERE signal IN %s AND id > %s
        ORDER BY id
    """, (AI_SIGNALS, state['last_main_id']))
    new_mains = cur.fetchall()

    # Event 2: any hedge twin closed since arming (exit verification)
    cur.execute("""
        SELECT id, token, direction, signal, status, entry_price, exit_price,
               pnl_usdt, exit_reason, close_time, open_time, _signal_metadata
        FROM trades
        WHERE signal LIKE '%%-hedge' AND status = 'closed'
          AND close_time > %s
        ORDER BY close_time
    """, (state['armed_at'],))
    closed_hedges = cur.fetchall()
    cur.close()

    if not new_mains and not closed_hedges:
        return None

    out = {'new_ai_trader_trades': [
        {'id': r[0], 'token': r[1], 'direction': r[2], 'signal': r[3],
         'status': r[4], 'entry_price': str(r[5]), 'amount_usdt': str(r[6]),
         'open_time': str(r[7]), 'stop_loss': str(r[8]), 'target': str(r[9])}
        for r in new_mains],
        'closed_hedge_twins': [
        {'id': r[0], 'token': r[1], 'direction': r[2], 'signal': r[3],
         'entry_price': str(r[5]), 'exit_price': str(r[6]),
         'pnl_usdt': str(r[7]), 'exit_reason': r[8],
         'close_time': str(r[9]), 'open_time': str(r[10])}
        for r in closed_hedges]}
    return out


def main():
    cn = connect()
    state = load_state()
    if state is None:
        state = baseline(cn)
    print(f"[hedge_watcher] armed: main_id>{state['last_main_id']} "
          f"since {state['armed_at']} — waiting for ai-trader fill or hedge close",
          flush=True)

    while True:
        try:
            if cn.closed:
                cn = connect()
            event = check(cn, state)
        except Exception as e:
            print(f"[hedge_watcher] DB error (retrying): {type(e).__name__}: {e}",
                  flush=True)
            try:
                cn.close()
            except Exception:
                pass
            cn = None
            time.sleep(POLL_S * 2)
            continue

        if event:
            # Advance state BEFORE exiting so a re-armed watcher skips this event
            if event['new_ai_trader_trades']:
                state['last_main_id'] = max(state['last_main_id'],
                    max(t['id'] for t in event['new_ai_trader_trades']))
            state['armed_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            save_state(state)
            print(json.dumps(event, indent=2), flush=True)
            for t in event['new_ai_trader_trades']:
                print(f"EVENT: ai-trader trade placed #{t['id']} {t['token']} "
                      f"{t['direction']} ({t['signal']})", flush=True)
            for h in event['closed_hedge_twins']:
                print(f"EVENT: hedge twin closed #{h['id']} {h['token']} "
                      f"{h['direction']} pnl={h['pnl_usdt']} ({h['exit_reason']})",
                      flush=True)
            cn.close()
            return 0

        time.sleep(POLL_S)


if __name__ == '__main__':
    sys.exit(main())
