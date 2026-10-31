#!/usr/bin/env python3
"""Probe the REAL jup_exit_sim (unmodified, imported as a module) and dump its
per-trade walker exits to JSON, so an independent implementation can be
compared trade-by-trade instead of only on aggregates."""
import sys, json, inspect

sys.path.insert(0, '/root/.hermes/scripts')
import jup_exit_sim as S

state = {'trade': None, 'trades': None, 'per': {}}

_orig_load_trades = S.load_trades
def load_trades():
    rows = _orig_load_trades()
    state['trades'] = rows
    return rows
S.load_trades = load_trades

_orig_load_candles = S.load_candles
def load_candles(token, t0, t1):
    for t in state['trades'] or []:
        if int(t['open_t'].timestamp()) - 300 == t0 and t['token'].upper() == token:
            state['trade'] = t['id']
            break
    return _orig_load_candles(token, t0, t1)
S.load_candles = load_candles

_orig_walk = S.replay_layers
def walk(*a, **kw):
    entry, direction, candles, entry_ts, horizon_ts, layers, floor_px, tp_px = a[:8]
    r = _orig_walk(*a, **kw)
    key = str(state['trade'])
    state['per'].setdefault(key, []).append(
        {'layers': [l[0] for l in layers], 'exit_px': r[0],
         'exit_ts': r[1], 'tag': r[2]})
    return r
S.replay_layers = walk

S.main()

# pm_actual per trade (straight from DB rows the sim loaded)
actual = {}
for t in state['trades']:
    actual[str(t['id'])] = {'actual_pnl': float(t['pnl_pct'] or 0),
                            'token': t['token'], 'dir': t['dir'],
                            'entry': float(t['entry']),
                            'lev': float(t['lev'] or 1),
                            'open_ts': int(t['open_t'].timestamp()),
                            'close_ts': int(t['close_t'].timestamp()),
                            'reason': t['reason']}
out = {'per_trade_walkers': state['per'], 'trades': actual}
with open('/root/.hermes/analysis/mfe_audit_sim_probe.json', 'w') as f:
    json.dump(out, f, indent=1, default=str)
print("\nprobe -> mfe_audit_sim_probe.json  (n trades =", len(actual), ")")
