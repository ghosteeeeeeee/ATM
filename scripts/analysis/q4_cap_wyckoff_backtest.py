#!/usr/bin/env python3
"""q4_cap_wyckoff_backtest.py — CEO pickup 2026-10-09 (orchestrator 06:28).

Two backtests, no live changes:

1. Q4 Portfolio Cap — counterfactual caps on 30d closed trades (brain PG).
   Caps: (A) max 2 alt-LONGs when market regime=SHORT_BIAS
         (B) max 3 same-direction opens / 30min rolling
         (C) both
   Alt = token not in (BTC, ETH). Market regime from regime_log (4h snaps,
   signals_hermes.db) mapped to open_time — trades.regime is NEUTRAL-noise.
   Acceptance: net positive AND home-run cost < 30% of saved losses.

2. Wyckoff STANDALONE_BYPASS — wyckoff+ fires from runtime signals DB (14d),
   forward returns via expiry_shadow engine (imported, not rebuilt).
   Baseline: pump-chain+ closed events in expiry_shadow.db.
   Acceptance: ex4h expectancy >= +0.10% AND n>=30. Else keep confluence-gated.
"""
import sys
import os
import sqlite3
import calendar
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psycopg2

RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
STATIC_DB = '/root/.hermes/data/signals_hermes.db'
CANDLES_DB = '/root/.hermes/data/candles.db'
SHADOW_DB = '/root/.hermes/brain/expiry_shadow.db'
PLANS_DIR = '/root/.hermes/plans'
BRAIN_PG = {'host': '/var/run/postgresql', 'dbname': 'brain', 'user': 'postgres'}

MAJORS = {'BTC', 'ETH'}
HOME_RUN_PCT = 5.0
ROLLING_MIN = 30


def log(msg):
    print(msg, flush=True)


# ═══════════════════════════════════════════════════════════════════════════
# BACKTEST 1 — Q4 PORTFOLIO CAP
# ═══════════════════════════════════════════════════════════════════════════

def load_trades_30d():
    conn = psycopg2.connect(**BRAIN_PG)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, direction, signal,
                   open_time, close_time,
                   pnl_usdt::float, pnl_pct::float
            FROM trades
            WHERE close_time >= now() - interval '30 days'
              AND pnl_usdt IS NOT NULL
            ORDER BY open_time
        """)
        rows = cur.fetchall()
    finally:
        conn.close()
    return [{
        'id': r[0], 'token': r[1].upper(), 'direction': r[2],
        'signal': r[3] or '', 'open_time': r[4], 'close_time': r[5],
        'pnl_usdt': r[6], 'pnl_pct': r[7],
    } for r in rows]


def load_regime_map():
    """4h regime snaps -> lookup by unix ts. Returns sorted list of (ts, regime)."""
    conn = sqlite3.connect(STATIC_DB)
    try:
        rows = conn.execute(
            "SELECT timestamp, regime FROM regime_log"
            " WHERE timestamp >= strftime('%s','2026-09-09')"
            " ORDER BY timestamp"
        ).fetchall()
    finally:
        conn.close()
    return [(ts, reg) for ts, reg in rows]


def regime_at(regime_map, dt):
    """Market regime at datetime dt (most recent snap <= dt)."""
    target = calendar.timegm(dt.timetuple())
    lo, hi = 0, len(regime_map)
    while lo < hi:
        mid = (lo + hi) // 2
        if regime_map[mid][0] <= target:
            lo = mid + 1
        else:
            hi = mid
    if lo == 0:
        return None
    return regime_map[lo - 1][1]


def simulate_cap_a(trades, regime_map):
    """Max 2 concurrent alt-LONGs when market regime=SHORT_BIAS at open."""
    open_alts = []  # list of (close_time, id) currently open alt-LONGs
    blocked = []
    for t in trades:
        # retire finished positions
        open_alts = [(ct, i) for ct, i in open_alts if ct > t['open_time']]
        if (t['direction'] == 'LONG' and t['token'] not in MAJORS):
            reg = regime_at(regime_map, t['open_time'])
            if reg == 'SHORT_BIAS' and len(open_alts) >= 2:
                blocked.append(t)
                continue
        if t['direction'] == 'LONG' and t['token'] not in MAJORS:
            open_alts.append((t['close_time'], t['id']))
    return blocked


def simulate_cap_b(trades):
    """Max 3 same-direction opens per 30min rolling window."""
    windows = {'LONG': deque(), 'SHORT': deque()}
    blocked = []
    for t in trades:
        d = t['direction']
        if d not in windows:
            continue
        w = windows[d]
        cutoff = t['open_time'] - timedelta(minutes=ROLLING_MIN)
        while w and w[0] < cutoff:
            w.popleft()
        if len(w) >= 3:
            blocked.append(t)
            continue
        w.append(t['open_time'])
    return blocked


def cap_stats(all_trades, blocked_ids):
    blocked = [t for t in all_trades if t['id'] in blocked_ids]
    if not blocked:
        return {'n': 0, 'net_impact': 0.0, 'saved_losses': 0.0,
                'missed_wins': 0.0, 'home_runs': 0, 'home_run_cost': 0.0}
    net = -sum(t['pnl_usdt'] for t in blocked)
    saved = -sum(t['pnl_usdt'] for t in blocked if t['pnl_usdt'] < 0)
    missed = sum(t['pnl_usdt'] for t in blocked if t['pnl_usdt'] > 0)
    hrs = [t for t in blocked if t['pnl_pct'] > HOME_RUN_PCT]
    return {
        'n': len(blocked),
        'net_impact': net,
        'saved_losses': saved,
        'missed_wins': missed,
        'home_runs': len(hrs),
        'home_run_cost': sum(t['pnl_usdt'] for t in hrs),
        'blocked_trades': blocked,
    }


def verdict_line(name, st):
    if st['n'] == 0:
        return f"{name}: 0 trades blocked — NO-OP. REJECT (no effect)."
    hr_ok = st['home_run_cost'] < 0.30 * st['saved_losses'] if st['saved_losses'] > 0 else st['home_run_cost'] == 0
    net_ok = st['net_impact'] > 0
    ok = net_ok and hr_ok
    return (f"{name}: blocked={st['n']}  net_impact=${st['net_impact']:+.2f}  "
            f"saved_losses=${st['saved_losses']:.2f}  missed_wins=${st['missed_wins']:.2f}  "
            f"home_runs={st['home_runs']} (cost=${st['home_run_cost']:.2f})  "
            f"→ {'ACCEPT' if ok else 'REJECT'}"
            f" (net {'+' if net_ok else '−'}, hr {'ok' if hr_ok else 'FAIL'}: "
            f"${st['home_run_cost']:.2f} vs 30%×${st['saved_losses']:.2f}=${0.30*st['saved_losses']:.2f})")


def run_backtest_1():
    log('═══ BACKTEST 1: Q4 PORTFOLIO CAP ═══')
    trades = load_trades_30d()
    regime_map = load_regime_map()
    log(f'trades loaded: {len(trades)}  regime snaps: {len(regime_map)}')

    total_pnl = sum(t['pnl_usdt'] for t in trades)
    log(f'baseline 30d PnL: ${total_pnl:+.2f}  '
        f'(wins={sum(1 for t in trades if t["pnl_usdt"]>0)})')

    # Cap A
    blocked_a = simulate_cap_a(trades, regime_map)
    st_a = cap_stats(trades, {t['id'] for t in blocked_a})
    log(verdict_line('CAP A (max 2 alt-LONGs @ SHORT_BIAS)', st_a))

    # Cap B
    blocked_b = simulate_cap_b(trades)
    st_b = cap_stats(trades, {t['id'] for t in blocked_b})
    log(verdict_line('CAP B (max 3 same-dir opens / 30min)', st_b))

    # Cap C — sequential: apply A first, then B on remaining
    remaining = [t for t in trades if t['id'] not in {x['id'] for x in blocked_a}]
    blocked_c2 = simulate_cap_b(remaining)
    blocked_c_ids = {t['id'] for t in blocked_a} | {t['id'] for t in blocked_c2}
    st_c = cap_stats(trades, blocked_c_ids)
    log(verdict_line('CAP C (A then B)', st_c))

    # Oct 8 incident check: would any cap have blocked the GRASS/FOGO/IOTA/BLUR cluster?
    cluster_ids = {t['id'] for t in trades
                   if t['token'] in ('GRASS', 'FOGO', 'IOTA', 'BLUR')
                   and t['open_time'].strftime('%Y-%m-%d') == '2026-10-08'
                   and t['direction'] == 'LONG'}
    for name, ids in (('A', {t['id'] for t in blocked_a}),
                      ('B', {t['id'] for t in blocked_b}),
                      ('C', blocked_c_ids)):
        hit = cluster_ids & ids
        log(f'  Oct-8 cluster ({len(cluster_ids)} trades): cap {name} blocks {len(hit)}')

    # Write verdict
    best = None
    for name, st in (('A', st_a), ('B', st_b), ('C', st_c)):
        if st['n'] == 0:
            continue
        hr_ok = st['home_run_cost'] < 0.30 * st['saved_losses'] if st['saved_losses'] > 0 else st['home_run_cost'] == 0
        if st['net_impact'] > 0 and hr_ok:
            if best is None or st['net_impact'] > best[1]['net_impact']:
                best = (name, st)

    lines = [
        '# Verdict — Q4 Portfolio Cap Backtest (2026-10-09)',
        '',
        f'Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} — orchestrator pickup, no live changes.',
        '',
        f'Window: last 30d closed trades (brain PG). n={len(trades)}, baseline PnL=${total_pnl:+.2f}.',
        'Alt = token not in (BTC, ETH). Market regime from regime_log 4h snaps (trades.regime is NEUTRAL-noise).',
        'For each blocked trade: missed outcome = actual pnl_usdt (no simulation).',
        'Acceptance: net_impact > 0 AND home_run_cost < 30% × saved_losses.',
        '',
        '## Results',
        '',
        '| Cap | Blocked | Net impact | Saved losses | Missed wins | Home runs | HR cost | Verdict |',
        '|-----|---------|------------|--------------|-------------|-----------|---------|---------|',
    ]
    for name, st in (('A (max 2 alt-LONGs @ SHORT_BIAS)', st_a),
                     ('B (max 3 same-dir / 30min)', st_b),
                     ('C (A then B)', st_c)):
        if st['n'] == 0:
            lines.append(f'| {name} | 0 | $0.00 | $0.00 | $0.00 | 0 | $0.00 | NO-OP REJECT |')
        else:
            hr_ok = st['home_run_cost'] < 0.30 * st['saved_losses'] if st['saved_losses'] > 0 else st['home_run_cost'] == 0
            net_ok = st['net_impact'] > 0
            ok = net_ok and hr_ok
            lines.append(
                f'| {name} | {st["n"]} | ${st["net_impact"]:+.2f} | ${st["saved_losses"]:.2f} '
                f'| ${st["missed_wins"]:.2f} | {st["home_runs"]} | ${st["home_run_cost"]:.2f} '
                f'| {"ACCEPT" if ok else "REJECT"} |')

    lines += [
        '',
        '## Oct 8 incident (GRASS/FOGO/IOTA/BLUR −$0.48 cluster)',
        '',
    ]
    for name, ids in (('A', {t['id'] for t in blocked_a}),
                      ('B', {t['id'] for t in blocked_b}),
                      ('C', blocked_c_ids)):
        hit = cluster_ids & ids
        lines.append(f'- Cap {name} blocks {len(hit)}/{len(cluster_ids)} of the cluster trades.')

    lines += [
        '',
        '## Verdict',
        '',
    ]
    if best:
        lines.append(f'**ACCEPT cap {best[1] and best[0]}** — net ${best[1]["net_impact"]:+.2f}, '
                     f'home-run cost within budget. Recommend CEO GO to implement as portfolio-level gate.')
    else:
        lines.append('**REJECT all caps** — no cap meets acceptance (net positive AND home-run cost < 30% of saved losses).')
        lines.append('Correlated-cluster bleed is real (Oct 8: −$0.48) but the 30d counterfactual does not show a clean edge.')
        lines.append('Recommendation: do NOT implement. Revisit when cluster frequency increases or with signal-family-level caps (pump-chain only).')

    path = os.path.join(PLANS_DIR, '2026-10-09-q4-portfolio-cap-verdict.md')
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    log(f'wrote {path}')
    return best


# ═══════════════════════════════════════════════════════════════════════════
# BACKTEST 2 — WYCKOFF STANDALONE_BYPASS
# ═══════════════════════════════════════════════════════════════════════════

def run_backtest_2():
    log('═══ BACKTEST 2: WYCKOFF STANDALONE_BYPASS ═══')

    # Import forward-return engine from expiry_shadow (reuse, don't rebuild)
    sys.path.insert(0, '/root/.hermes/scripts')
    import expiry_shadow as es

    # 1. Wyckoff fires from runtime DB, last 14d
    conn = sqlite3.connect(RUNTIME_DB)
    try:
        fires = conn.execute("""
            SELECT id, token, direction, signal_type, source, confidence,
                   decision, decision_reason, created_at
            FROM signals
            WHERE source LIKE 'wyckoff%'
              AND created_at >= datetime('now', '-14 days')
            ORDER BY created_at
        """).fetchall()
    finally:
        conn.close()
    log(f'wyckoff fires (14d runtime): {len(fires)}')

    # 2. Closed events already in expiry_shadow (same engine)
    sh = sqlite3.connect(SHADOW_DB)
    try:
        shadow_wyck = sh.execute("""
            SELECT signal_id, token, direction, confidence, created_at,
                   fwd_1h, fwd_4h, excess_1h, excess_4h, mfe_4h
            FROM events
            WHERE source LIKE 'wyckoff%' AND closed=1 AND fwd_4h IS NOT NULL
        """).fetchall()
        # pump-chain+ baseline
        baseline = sh.execute("""
            SELECT COUNT(*), AVG(excess_4h), AVG(fwd_4h),
                   SUM(CASE WHEN excess_4h > 0 THEN 1 ELSE 0 END)
            FROM events
            WHERE source = 'pump-chain+' AND closed=1 AND fwd_4h IS NOT NULL
        """).fetchone()
    finally:
        sh.close()
    log(f'wyckoff closed shadow events: {len(shadow_wyck)}')
    log(f'pump-chain+ baseline: n={baseline[0]} avg_ex4h={baseline[1]:.3f}% '
        f'avg_fwd4h={baseline[2]:.3f}% pos_rate={baseline[3]}/{baseline[0]}')

    # 3. Close any unclosed wyckoff fires that are now old enough (>4.5h)
    #    using the same engine — import _fwd_metrics / _load_candles
    newly_closed = []
    now = datetime.now(timezone.utc)
    for sid, tok, d, created in [
        (f[0], f[1], f[2], f[8]) for f in fires
    ]:
        # skip if already in shadow closed
        if any(s[0] == sid for s in shadow_wyck):
            continue
        try:
            entry_ts = calendar.timegm(
                datetime.strptime(created, '%Y-%m-%d %H:%M:%S').timetuple())
        except (ValueError, TypeError):
            continue
        age_h = (now.timestamp() - entry_ts) / 3600.0
        if age_h < 4.5:
            continue
        rows = es._load_candles(tok)
        if not rows:
            continue
        fm = es._fwd_metrics(rows, entry_ts, d)
        if fm is None:
            continue
        mb1 = es._market_mean(entry_ts, 12)
        mb4 = es._market_mean(entry_ts, 48)
        sgn = 1 if d == 'LONG' else -1
        ex1 = fm['fwd_1h'] - (mb1 if d == 'LONG' else -mb1) if mb1 is not None else None
        ex4 = fm['fwd_4h'] - (mb4 if d == 'LONG' else -mb4) if mb4 is not None else None
        newly_closed.append((sid, tok, d, created, fm['fwd_1h'], fm['fwd_4h'], ex1, ex4, fm['mfe_4h']))
    log(f'newly closed wyckoff fires: {len(newly_closed)}')

    # 4. Aggregate wyckoff-alone expectancy
    all_closed = []
    for s in shadow_wyck:
        all_closed.append({'sid': s[0], 'token': s[1], 'dir': s[2], 'conf': s[3],
                           'created': s[4], 'fwd_1h': s[5], 'fwd_4h': s[6],
                           'ex_1h': s[7], 'ex_4h': s[8], 'mfe': s[9]})
    for n in newly_closed:
        all_closed.append({'sid': n[0], 'token': n[1], 'dir': n[2], 'conf': None,
                           'created': n[3], 'fwd_1h': n[4], 'fwd_4h': n[5],
                           'ex_1h': n[6], 'ex_4h': n[7], 'mfe': n[8]})

    n_fires = len(fires)
    n_closed = len(all_closed)
    if n_closed:
        avg_ex4h = sum(c['ex_4h'] for c in all_closed if c['ex_4h'] is not None) / \
                   max(1, sum(1 for c in all_closed if c['ex_4h'] is not None))
        avg_fwd4h = sum(c['fwd_4h'] for c in all_closed if c['fwd_4h'] is not None) / \
                    max(1, sum(1 for c in all_closed if c['fwd_4h'] is not None))
        pos = sum(1 for c in all_closed if c['ex_4h'] is not None and c['ex_4h'] > 0)
        n_ex = sum(1 for c in all_closed if c['ex_4h'] is not None)
    else:
        avg_ex4h = avg_fwd4h = 0.0
        pos = n_ex = 0

    log(f'wyckoff-alone: fires={n_fires} closed={n_closed} '
        f'avg_ex4h={avg_ex4h:.3f}% avg_fwd4h={avg_fwd4h:.3f}% pos={pos}/{n_ex}')

    # 5. Acceptance
    n_ok = n_fires >= 30
    ex_ok = avg_ex4h >= 0.10
    accept = n_ok and ex_ok

    # 6. Per-fire detail
    detail_rows = []
    for c in sorted(all_closed, key=lambda x: x['created']):
        detail_rows.append(
            f"| {c['created'][:16]} | {c['token']} | {c['dir']} | {c['conf'] or '—'} "
            f"| {c['fwd_1h']:.2f}% | {c['fwd_4h']:.2f}% "
            f"| {c['ex_1h']:.2f}% | {c['ex_4h']:.2f}% | {c['mfe']:.2f}% |")

    # Unfired / recent fires detail
    recent = []
    for f in fires:
        if not any(s[0] == f[0] for s in shadow_wyck) and \
           not any(n[0] == f[0] for n in newly_closed):
            recent.append(f'| {f[8][:16]} | {f[1]} | {f[2]} | {f[5]} | {f[6]} | too recent / no candles |')

    lines = [
        '# Verdict — Wyckoff STANDALONE_BYPASS Backtest (2026-10-09)',
        '',
        f'Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} — orchestrator pickup, no live changes.',
        '',
        '## Spec recap',
        '',
        '- Reconstruct wyckoff± fires from runtime signals DB, last 14d.',
        '- Forward returns via expiry_shadow engine (imported, not rebuilt).',
        '- Baseline: pump-chain+ (known standalone-bypass signal).',
        '- Acceptance: wyckoff-alone ex4h expectancy ≥ +0.10% AND n ≥ 30 fires.',
        '- Otherwise: keep confluence-gated, pair with volume/rs source.',
        '',
        '## Results',
        '',
        f'- **Wyckoff fires (14d):** {n_fires}',
        f'- **Closed with fwd data:** {n_closed}',
        f'- **Avg excess 4h:** {avg_ex4h:+.3f}%',
        f'- **Avg raw fwd 4h:** {avg_fwd4h:+.3f}%',
        f'- **Positive excess rate:** {pos}/{n_ex}'
        + (f' ({pos/n_ex*100:.0f}%)' if n_ex else ''),
        f'- **pump-chain+ baseline:** n={baseline[0]} avg_ex4h={baseline[1]:+.3f}% '
        f'pos={baseline[3]}/{baseline[0]}'
        + (f' ({baseline[3]/baseline[0]*100:.0f}%)' if baseline[0] else ''),
        '',
        '## Acceptance check',
        '',
        f'- n ≥ 30: **{"PASS" if n_ok else "FAIL"}** ({n_fires} fires)',
        f'- ex4h ≥ +0.10%: **{"PASS" if ex_ok else "FAIL"}** ({avg_ex4h:+.3f}%)',
        f'- **Overall: {"ACCEPT" if accept else "REJECT"}**',
        '',
        '## Per-fire detail (closed)',
        '',
        '| Created | Token | Dir | Conf | fwd_1h | fwd_4h | ex_1h | ex_4h | MFE_4h |',
        '|---------|-------|-----|------|--------|--------|-------|-------|--------|',
    ]
    lines += detail_rows
    if recent:
        lines += [
            '',
            '## Fires without fwd data (too recent / no candles)',
            '',
            '| Created | Token | Dir | Conf | Decision | Note |',
            '|---------|-------|-----|------|----------|------|',
        ]
        lines += recent

    lines += [
        '',
        '## Verdict',
        '',
    ]
    if accept:
        lines.append('**ACCEPT** — wyckoff-alone shows positive expectancy at sufficient sample.')
        lines.append('Recommend CEO GO + independent audit before adding STANDALONE_BYPASS.')
    else:
        lines.append('**REJECT** — keep confluence-gated.')
        if not n_ok:
            lines.append(f'- Sample too small: {n_fires} fires < 30 required. '
                         f'Wyckoff wired Oct 7; only ~2d of runtime data available.')
        if not ex_ok:
            lines.append(f'- Expectancy below threshold: {avg_ex4h:+.3f}% < +0.10%.')
        if n_closed and avg_ex4h < 0:
            lines.append(f'- Direction is negative: closed events average {avg_ex4h:+.3f}% excess — '
                         f'bypass would LOSE money on available evidence.')
        lines.append('- Pairing with a volume/rs co-source (signal_analyst) remains the correct path.')
        lines.append(f'- pump-chain+ baseline ({baseline[1]:+.3f}% ex4h, n={baseline[0]}) is the bar wyckoff fails to clear.')

    path = os.path.join(PLANS_DIR, '2026-10-09-wyckoff-bypass-verdict.md')
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    log(f'wrote {path}')
    return accept


if __name__ == '__main__':
    best_cap = run_backtest_1()
    log('')
    wyckoff_ok = run_backtest_2()
    log('')
    log('═══ SUMMARY ═══')
    log(f'Portfolio cap: {"ACCEPT cap " + str(best_cap[0]) if best_cap else "REJECT all"}')
    log(f'Wyckoff bypass: {"ACCEPT" if wyckoff_ok else "REJECT"}')
