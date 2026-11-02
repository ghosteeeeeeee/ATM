#!/usr/bin/env python3
"""Contrarian shadow outcome-join — unblocks Oct 27 PROMOTE decision.

For each contrarian_shadow.jsonl entry (pre-classified LOSER at write time),
look at 5m candles after the signal timestamp and compute what the
CONTRARIAN direction would have done.

Classification rule (pre-registered, mirrors trail-arm logic):
  WINNER  = contrarian direction reached +0.40% favorable before -0.40% adverse
  LOSER   = adverse hit first, or neither within 30 candles (2.5h)
  SHALLOW = never moved ±0.40% either way within 30 candles

Units: price-move % only (no leverage). Compare same units per UNITS RULE.
"""
import json, sqlite3, sys, os
from datetime import datetime, timezone
from collections import defaultdict

CANDLES = '/root/.hermes/data/candles.db'
CONTINUUM = '/root/.hermes/data/continuum.db'
SHADOW = '/root/.hermes/data/contrarian_shadow.jsonl'
ARM_PCT = 0.40   # favorable threshold (matches trail arm)
ADV_PCT = 0.40   # adverse threshold (matches hard stop distance)
MAX_CANDLES = 30 # 30 × 5m = 2.5h horizon
TAPE_SLACK_S = 600  # matches decider_run live stamp guard (<600), tape_state_arm_census
MIN_TOKEN_N = 10    # token cells below this are noise for the heterogeneity test

def ts_to_unix(ts_str):
    """ISO '2026-10-13T17:12' → unix seconds."""
    try:
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return int(dt.timestamp())
    except Exception:
        return None

def classify(entry, conn):
    """Return (outcome, max_fav_pct, max_adv_pct, candles_used) for contrarian direction."""
    ts_unix = ts_to_unix(entry.get('ts', ''))
    token = entry.get('token', '').upper()
    entry_price = entry.get('entry_price')
    contra_dir = entry.get('contrarian_direction', '').upper()
    if not ts_unix or not token or not entry_price or not contra_dir:
        return None
    entry_price = float(entry_price)
    if entry_price <= 0:
        return None

    cur = conn.cursor()
    cur.execute("""
        SELECT ts, open, high, low, close FROM candles_5m
        WHERE token = ? AND ts > ? AND is_closed = 1
        ORDER BY ts ASC LIMIT ?
    """, (token, ts_unix, MAX_CANDLES))
    rows = cur.fetchall()
    if not rows:
        return ('NO_DATA', 0, 0, 0)

    max_fav = 0.0
    max_adv = 0.0
    outcome = 'SHALLOW'
    for i, (_, o, h, l, c) in enumerate(rows):
        if contra_dir == 'LONG':
            fav = (h - entry_price) / entry_price * 100
            adv = (entry_price - l) / entry_price * 100
        else:  # SHORT
            fav = (entry_price - l) / entry_price * 100
            adv = (h - entry_price) / entry_price * 100
        max_fav = max(max_fav, fav)
        max_adv = max(max_adv, adv)
        if max_fav >= ARM_PCT and max_adv < ADV_PCT:
            outcome = 'WINNER'
            break
        if max_adv >= ADV_PCT and max_fav < ARM_PCT:
            outcome = 'LOSER'
            break
        # both crossed: check which crossed first (approximate by candle order)
        if max_fav >= ARM_PCT and max_adv >= ADV_PCT:
            # whichever hit on this candle — if fav hit at or before adv, call it WINNER
            # conservative: if both same candle, check close direction
            if c >= entry_price:
                outcome = 'WINNER'
            else:
                outcome = 'LOSER'
            break
    else:
        # loop completed without break
        if max_fav >= ARM_PCT:
            outcome = 'WINNER'
        elif max_adv >= ADV_PCT:
            outcome = 'LOSER'
        else:
            outcome = 'SHALLOW'

    return (outcome, round(max_fav, 3), round(max_adv, 3), len(rows))


def btc_tape_at(ts_str, con=None):
    """BTC ema300_position at ts_str, or None. Mirrors tape_state_arm_census.tape_at."""
    ts_unix = ts_to_unix(ts_str)
    if not ts_unix:
        return None
    own = con is None
    try:
        if own:
            con = sqlite3.connect(CONTINUUM, timeout=10)
        row = con.execute(
            "SELECT ema300_position, ts FROM continuum_states "
            "WHERE token='BTC' AND timeframe='1m' AND ts<=? "
            "ORDER BY ts DESC LIMIT 1", (ts_unix,)).fetchone()
    except Exception:
        return None
    finally:
        if own and con is not None:
            con.close()
    if not row or ts_unix - row[1] >= TAPE_SLACK_S:
        return None
    return row[0] or 'UNKNOWN'


def cell_block(rows):
    """WINNER/LOSER/SHALLOW counts + flip-WR for a row slice (decided-only WR)."""
    d = {'WINNER': 0, 'LOSER': 0, 'SHALLOW': 0}
    for r in rows:
        d[r['_outcome']] = d.get(r['_outcome'], 0) + 1
    decided = d['WINNER'] + d['LOSER']
    d['n'] = sum(d.values())
    d['decided'] = decided
    d['flip_wr'] = round(100.0 * d['WINNER'] / decided, 1) if decided else None
    return d


def token_heterogeneity(rows, min_n=MIN_TOKEN_N):
    """chi2 across token cells with decided n>=min_n. p small = tokens genuinely differ."""
    by_tok = defaultdict(list)
    for r in rows:
        by_tok[r['token']].append(r)
    table, toks = [], []
    for tok, rs in sorted(by_tok.items()):
        d = cell_block(rs)
        if d['decided'] >= min_n:
            table.append([d['WINNER'], d['LOSER']])
            toks.append(tok)
    if len(table) < 3:
        return {'tokens': len(table), 'n': sum(sum(t) for t in table),
                'chi2': None, 'p': None, 'note': 'fewer than 3 cells >= n=%d' % min_n}
    try:
        from scipy.stats import chi2_contingency
        chi2, p, dof, _ = chi2_contingency(table)
    except Exception as e:  # noqa: BLE001 — report, never crash the join
        return {'tokens': len(table), 'n': sum(sum(t) for t in table),
                'chi2': None, 'p': None, 'note': 'scipy unavailable: %s' % e}
    return {'tokens': len(table), 'n': sum(sum(t) for t in table),
            'chi2': round(chi2, 2), 'df': dof, 'p': float(p)}


def main():
    selfcheck = '--selfcheck' in sys.argv
    if selfcheck:
        # minimal self-check: verify ts parsing and direction logic
        assert ts_to_unix('2026-10-13T17:12') > 0
        assert ts_to_unix('bad') is None
        # cell_block / wr_of on a fixture (2 win, 1 loss, 1 shallow)
        fx = [{'_outcome': 'WINNER'}, {'_outcome': 'WINNER'},
              {'_outcome': 'LOSER'}, {'_outcome': 'SHALLOW'}]
        b = cell_block(fx)
        assert b == {'WINNER': 2, 'LOSER': 1, 'SHALLOW': 1,
                     'n': 4, 'decided': 3, 'flip_wr': 66.7}, b
        # heterogeneity: identical cells must NOT be significant, split cells must be
        same = []
        for t in ('A', 'B', 'C', 'D'):
            same += [{'token': t, '_outcome': 'WINNER' if i % 2 else 'LOSER'} for i in range(40)]
        h = token_heterogeneity(same)
        assert h['p'] is not None and h['p'] > 0.05, h
        split = []
        for t, o in (('A', 'WINNER'), ('B', 'WINNER'), ('C', 'LOSER'), ('D', 'LOSER')):
            split += [{'token': t, '_outcome': o} for _ in range(30)]
        h2 = token_heterogeneity(split)
        assert h2['p'] is not None and h2['p'] < 0.001, h2
        # btc_tape_at must not crash on garbage / out-of-range
        assert btc_tape_at('bad') is None
        v = btc_tape_at('2026-11-01T00:00:00+00:00')
        assert v is None or v in ('ABOVE', 'AT', 'BELOW', 'UNKNOWN'), v
        print('SELF-CHECK PASS')
        return

    entries = []
    with open(SHADOW) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    print(f'Contrarian shadow entries: {len(entries)}')

    conn = sqlite3.connect(CANDLES, timeout=10)
    results = []
    no_data = 0
    for e in entries:
        r = classify(e, conn)
        if r is None:
            continue
        outcome, fav, adv, n_candles = r
        if outcome == 'NO_DATA':
            no_data += 1
            continue
        results.append({**e, '_outcome': outcome, '_max_fav': fav, '_max_adv': adv, '_candles': n_candles})
    conn.close()

    print(f'Joinable: {len(results)}  No-data: {no_data}')

    # Stats by signal
    by_sig = defaultdict(lambda: defaultdict(int))
    pnl_by_sig = defaultdict(lambda: {'WINNER': 0, 'LOSER': 0, 'SHALLOW': 0})
    for r in results:
        sig = r.get('signal', '?')
        oc = r['_outcome']
        by_sig[sig][oc] += 1

    print(f'\n=== CONTRARIAN OUTCOME-JOIN (contrarian direction) ===')
    print(f'{"Signal":35s} {"n":>5s} {"WIN":>5s} {"LOSS":>5s} {"SHAL":>5s} {"flip-WR":>8s}')
    total = defaultdict(int)
    for sig in sorted(by_sig, key=lambda s: -(by_sig[s]['WINNER'] + by_sig[s]['LOSER'])):
        d = by_sig[sig]
        n = d['WINNER'] + d['LOSER'] + d['SHALLOW']
        decided = d['WINNER'] + d['LOSER']
        wr = 100.0 * d['WINNER'] / decided if decided else 0
        print(f'{sig:35s} {n:5d} {d["WINNER"]:5d} {d["LOSER"]:5d} {d["SHALLOW"]:5d} {wr:7.1f}%')
        total['WINNER'] += d['WINNER']
        total['LOSER'] += d['LOSER']
        total['SHALLOW'] += d['SHALLOW']

    n_total = sum(total.values())
    decided = total['WINNER'] + total['LOSER']
    wr = 100.0 * total['WINNER'] / decided if decided else 0
    print(f'\n{"TOTAL":35s} {n_total:5d} {total["WINNER"]:5d} {total["LOSER"]:5d} {total["SHALLOW"]:5d} {wr:7.1f}%')
    print(f'\nFlip-WR (contrarian direction, decided only): {wr:.1f}%  (n={decided})')
    print(f'SHALLOW (never moved ±{ARM_PCT}% in {MAX_CANDLES}×5m): {total["SHALLOW"]}/{n_total} = {100*total["SHALLOW"]/max(n_total,1):.1f}%')

    # ── cell splits: by token / by BTC tape position, + per-signal heterogeneity ──
    # brain_auditor #218 (2026-11-02): amplifies amplify-pc-fade-cell-split — the join
    # was signal-level only, so we could not see whether an edge concentrates in a cell.
    by_token, by_regime = defaultdict(list), defaultdict(list)
    tape_cache = {}
    cont = sqlite3.connect(CONTINUUM, timeout=10)
    try:
        for r in results:
            sig = r.get('signal', '?')
            by_token[(sig, r.get('token', '?'))].append(r)
            ts = r.get('ts', '')
            if ts not in tape_cache:
                tape_cache[ts] = btc_tape_at(ts, cont)
            by_regime[(sig, tape_cache[ts] or 'NO_TAPE')].append(r)
    finally:
        cont.close()

    token_out = {f'{s}|{t}': cell_block(rs) for (s, t), rs in
                 sorted(by_token.items(), key=lambda kv: (kv[0][0], -len(kv[1])))}
    regime_out = {f'{s}|{p}': cell_block(rs) for (s, p), rs in
                  sorted(by_regime.items(), key=lambda kv: (kv[0][0], kv[0][1]))}
    het_out = {sig: token_heterogeneity([r for r in results if r.get('signal') == sig])
               for sig in sorted(by_sig)}

    print('\n=== BY TOKEN (decided n >= %d) ===' % MIN_TOKEN_N)
    for key, d in token_out.items():
        if d['decided'] >= MIN_TOKEN_N:
            print(f'  {key:42s} n={d["n"]:4d} decided={d["decided"]:4d} flip-WR={d["flip_wr"]}%')
    print('\n=== BY BTC TAPE (ema300_position at signal ts) ===')
    for key, d in sorted(regime_out.items()):
        wrs = 'n/a' if d['flip_wr'] is None else f'{d["flip_wr"]}%'
        print(f'  {key:42s} n={d["n"]:4d} decided={d["decided"]:4d} flip-WR={wrs}')
    print('\n=== TOKEN HETEROGENEITY (chi2 across cells n>=%d) ===' % MIN_TOKEN_N)
    for sig, h in het_out.items():
        p = 'n/a' if h.get('p') is None else f'{h["p"]:.4g}'
        print(f'  {sig:35s} tokens={h.get("tokens")} n={h.get("n")} chi2={h.get("chi2")} p={p}'
              + (f'  [{h["note"]}]' if h.get('note') else ''))
        if h.get('p') is not None:
            verdict = 'HETEROGENEOUS' if h['p'] < 0.05 else 'uniform (cell split not warranted)'
            print(f'      -> {verdict}')

    # Write output
    out_path = '/root/.hermes/data/contrarian_outcome_join.json'
    with open(out_path, 'w') as f:
        json.dump({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'params': {'arm_pct': ARM_PCT, 'adv_pct': ADV_PCT, 'max_candles': MAX_CANDLES, 'timeframe': '5m'},
            'total': dict(total),
            'flip_wr': round(wr, 1),
            'decided': decided,
            'no_data': no_data,
            'by_signal': {s: dict(d) for s, d in by_sig.items()},
            'by_token': token_out,
            'by_regime': regime_out,
            'token_heterogeneity': het_out,
            'split_params': {'min_token_n': MIN_TOKEN_N, 'tape_slack_s': TAPE_SLACK_S,
                             'tape_source': 'continuum.db continuum_states BTC 1m ema300_position'},
        }, f, indent=2)
    print(f'\nWritten: {out_path}')

if __name__ == '__main__':
    main()
