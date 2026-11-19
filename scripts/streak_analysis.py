#!/usr/bin/env python3
"""
streak_analysis.py — read-only analysis: Wallace ideas 1+2 vs LOSS_COOLDOWN / KILL_MAX_CONSEC.

Q1: After N consecutive losses on a unit, is next-trade WR better (Wallace) or
    worse (our LOSS_COOLDOWN's implicit assumption)?
Q2: Is the first win after a >=2-loss streak larger (MFE) than a typical win?
Q3: Streak-length distribution (tail headroom — historical max is NOT a bound).

Units:
  primary   = TOKEN:DIRECTION  (LOSS_COOLDOWN key, brain.py:44)
  secondary = signal           (KILL_MAX_CONSEC consumer, self_learner.py:57)

Definitions (aligned with position_manager close path):
  win  = pnl_usdt > 0          (brief's win definition; clears cooldown streak)
  loss = pnl_usdt <= 0         (non-win extends streak; pnl==0 is ~4% of sample
                                and neither sets nor clears the cooldown — counted
                                as non-win here; see caveats in result file)
  entry_streak for trade i = count of non-wins since the last win in that unit
  baseline = entry_streak == 0 (first trade after a win, or unit's first trade)

Read-only: SELECT only. No writes, no constants changes.
"""
import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import *  # noqa: F401

import psycopg2
from _secrets import BRAIN_DB_DICT
from scipy import stats

# ── header constants (analysis params; tunables live here, not in hermes_constants) �
DEFAULT_DAYS = 90
DEFAULT_TRAIN_DAYS = 60          # derive on first N days of window, validate on rest
MIN_CELL = 30                    # below this we flag underpowered, do not overclaim
STREAK_BUCKETS = ((1, 1), (2, 2), (3, None))  # after exactly-1, exactly-2, >=3


def fetch_trades(days: int) -> list:
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, open_time, close_time, token, direction, signal,
                   pnl_usdt, hype_realized_pnl_usdt, mfe_pct
            FROM trades
            WHERE status = 'closed'
              AND close_time > NOW() - make_interval(days => %s)
            ORDER BY close_time ASC
            """,
            (days,),
        )
        cols = [d[0] for d in cur.description]
        rows = []
        for r in cur.fetchall():
            d = dict(zip(cols, r))
            d['pnl_usdt'] = float(d['pnl_usdt']) if d['pnl_usdt'] is not None else None
            d['hype_realized_pnl_usdt'] = (
                float(d['hype_realized_pnl_usdt'])
                if d['hype_realized_pnl_usdt'] is not None else None
            )
            d['mfe_pct'] = float(d['mfe_pct']) if d['mfe_pct'] is not None else None
            d['close_time'] = d['close_time']
            rows.append(d)
        return rows
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def win_pnl(row) -> bool:
    p = row['pnl_usdt']
    return p is not None and p > 0


def win_hype(row) -> bool:
    """Sensitivity: hype_realized_pnl_usdt where NOT NULL (position_manager prefers
    it when non-zero on paper closes), else pnl_usdt."""
    h = row['hype_realized_pnl_usdt']
    if h is not None and h != 0:
        return h > 0
    return win_pnl(row)


def unit_key(row, unit: str) -> str:
    if unit == 'token_dir':
        return f"{(row['token'] or '?').upper()}:{(row['direction'] or '?').upper()}"
    return row['signal'] or '?'


def annotate(rows: list, win_fn) -> list:
    """Chronological within unit (input must be sorted by close_time globally;
    group then preserve order). Sets entry_streak per trade."""
    by_unit = defaultdict(list)
    for r in rows:
        by_unit[unit_key(r, r['_unit'])].append(r)
    out = []
    for _, seq in by_unit.items():
        streak = 0
        for r in seq:
            r = dict(r)
            r['entry_streak'] = streak
            out.append(r)
            if win_fn(r):
                streak = 0
            else:
                streak += 1
    out.sort(key=lambda x: x['close_time'])
    return out


def completed_streaks(rows: list, win_fn) -> list:
    """Lengths of finished non-win runs per unit (tail headroom)."""
    by_unit = defaultdict(list)
    for r in rows:
        by_unit[unit_key(r, r['_unit'])].append(r)
    all_streaks = []
    per_unit_max = {}
    for k, seq in by_unit.items():
        cur, mx = 0, 0
        for r in seq:
            if win_fn(r):
                if cur > 0:
                    all_streaks.append(cur)
                cur = 0
            else:
                cur += 1
                mx = max(mx, cur)
        if cur > 0:
            all_streaks.append(cur)
        per_unit_max[k] = mx
    return all_streaks, per_unit_max


def pct(vals, q):
    if not vals:
        return float('nan')
    s = sorted(vals)
    idx = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[idx]


def bucket_of(streak: int) -> str:
    if streak == 0:
        return 'baseline'
    if streak == 1:
        return 'after1'
    if streak == 2:
        return 'after2'
    return 'after3plus'


def summarize_buckets(annotated: list, win_fn) -> dict:
    b = defaultdict(lambda: {'n': 0, 'wins': 0, 'pnls': [], 'mfes': []})
    for r in annotated:
        k = bucket_of(r['entry_streak'])
        c = b[k]
        c['n'] += 1
        if win_fn(r):
            c['wins'] += 1
        if r['pnl_usdt'] is not None:
            c['pnls'].append(r['pnl_usdt'])
        if r['mfe_pct'] is not None:
            c['mfes'].append(r['mfe_pct'])
    return b


def fisher_p(a_win, a_loss, b_win, b_loss):
    """after-cell vs baseline-cell, two-sided Fisher exact."""
    if min(a_win + a_loss, b_win + b_loss) == 0:
        return float('nan')
    _, p = stats.fisher_exact([[a_win, a_loss], [b_win, b_loss]])
    return p


def welch_p(a, b):
    if len(a) < 2 or len(b) < 2:
        return float('nan')
    # identical arrays → scipy returns nan; guard
    if len(set(a)) == 1 and len(set(b)) == 1 and a[0] == b[0]:
        return 1.0
    try:
        return float(stats.ttest_ind(a, b, equal_var=False).pvalue)
    except Exception:
        return float('nan')


def fmt_p(p):
    if p != p:  # NaN
        return 'n/a'
    if p < 0.001:
        return '<0.001'
    return f'{p:.3f}'


def flag_n(n):
    return ' **(n<30)**' if n < MIN_CELL else ''


def bucket_table(b: dict, title: str) -> str:
    base = b.get('baseline', {'n': 0, 'wins': 0, 'pnls': []})
    base_wr = base['wins'] / base['n'] if base['n'] else float('nan')
    base_pnl = sum(base['pnls']) / len(base['pnls']) if base['pnls'] else float('nan')
    lines = [
        f'### {title}',
        '',
        '| group | n | wins | WR | ΔWR vs base | p (Fisher) | mean pnl_usdt | Δpnl | p (Welch) |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for label, key in (('baseline (after win / first)', 'baseline'),
                       ('after exactly 1 loss', 'after1'),
                       ('after exactly 2 losses', 'after2'),
                       ('after ≥3 losses', 'after3plus')):
        c = b.get(key, {'n': 0, 'wins': 0, 'pnls': []})
        n = c['n']
        wr = c['wins'] / n if n else float('nan')
        mp = sum(c['pnls']) / len(c['pnls']) if c['pnls'] else float('nan')
        if key == 'baseline':
            lines.append(
                f'| {label} | {n} | {c["wins"]} | {wr:.1%} | — | — | {mp:+.4f} | — | — |'
            )
        else:
            p_f = fisher_p(c['wins'], n - c['wins'], base['wins'], base['n'] - base['wins'])
            p_w = welch_p(c['pnls'], base['pnls'])
            d_wr = (wr - base_wr) if n and base['n'] else float('nan')
            d_pnl = (mp - base_pnl) if c['pnls'] and base['pnls'] else float('nan')
            wr_s = f'{wr:.1%}' + flag_n(n)
            d_wr_s = f'{d_wr:+.1%}' if d_wr == d_wr else 'n/a'
            mp_s = f'{mp:+.4f}' if mp == mp else 'n/a'
            d_pnl_s = f'{d_pnl:+.4f}' if d_pnl == d_pnl else 'n/a'
            lines.append(
                f'| {label} | {n} | {c["wins"]} | {wr_s} | {d_wr_s} | {fmt_p(p_f)} '
                f'| {mp_s} | {d_pnl_s} | {fmt_p(p_w)} |'
            )
    lines.append('')
    return '\n'.join(lines)


def mfe_table(annotated: list, win_fn, title: str) -> str:
    after = [r['mfe_pct'] for r in annotated
             if r['entry_streak'] >= 2 and win_fn(r) and r['mfe_pct'] is not None]
    typ = [r['mfe_pct'] for r in annotated
           if r['entry_streak'] < 2 and win_fn(r) and r['mfe_pct'] is not None]
    ma = sum(after) / len(after) if after else float('nan')
    mt = sum(typ) / len(typ) if typ else float('nan')
    p_t = welch_p(after, typ)
    try:
        p_mw = (float(stats.mannwhitneyu(after, typ, alternative='two-sided').pvalue)
                if after and typ else float('nan'))
    except Exception:
        p_mw = float('nan')
    lines = [
        f'### {title}',
        '',
        '| group | n (wins w/ MFE) | mean mfe_pct |',
        '|---|---:|---:|',
        f'| first win after ≥2 losses | {len(after)}{flag_n(len(after))} | {ma:.3f} |'
        if after else f'| first win after ≥2 losses | 0 | n/a |',
        f'| typical win (not after ≥2 losses) | {len(typ)} | {mt:.3f} |',
        '',
        f'- Welch t-test p = {fmt_p(p_t)}; Mann-Whitney p = {fmt_p(p_mw)}',
        '',
    ]
    return '\n'.join(lines)


def streak_dist_table(all_streaks, per_unit_max, title) -> str:
    if not all_streaks:
        return f'### {title}\n\n(no completed loss streaks)\n'
    mx = max(all_streaks)
    p95 = pct(all_streaks, 0.95)
    c3 = sum(1 for s in all_streaks if s >= 3)
    c5 = sum(1 for s in all_streaks if s >= 5)
    c10 = sum(1 for s in all_streaks if s >= 10)
    n_units = len(per_unit_max)
    umx = sorted(per_unit_max.values())
    units_10 = sum(1 for v in per_unit_max.values() if v >= 10)
    lines = [
        f'### {title}',
        '',
        '| metric | value |',
        '|---|---:|',
        f'| completed streaks (n) | {len(all_streaks)} |',
        f'| max streak length | {mx} |',
        f'| p95 streak length | {p95} |',
        f'| streaks ≥3 | {c3} |',
        f'| streaks ≥5 | {c5} |',
        f'| streaks ≥10 | {c10} |',
        f'| units (n) | {n_units} |',
        f'| per-unit max: median | {pct(umx, 0.5):.0f} |',
        f'| per-unit max: p95 | {pct(umx, 0.95):.0f} |',
        f'| units with max streak ≥10 | {units_10} |',
        '',
    ]
    return '\n'.join(lines)


def oos_section(annotated: list, win_fn, split_dt, title) -> str:
    train = [r for r in annotated if r['close_time'] <= split_dt]
    test = [r for r in annotated if r['close_time'] > split_dt]
    lines = [
        f'### OOS split — {title}',
        '',
        f'- derive window: close_time ≤ {split_dt} (first 60d of 90d), n={len(train)}',
        f'- validate window: close_time > {split_dt} (last 30d), n={len(test)}',
        '',
        '| after-k cell | train ΔWR | train p | test ΔWR | test p | sign flip? |',
        '|---|---:|---:|---:|---:|---|',
    ]
    for label, key in (('after 1', 'after1'), ('after 2', 'after2'), ('after ≥3', 'after3plus')):
        row_s = []
        deltas = []
        for part in (train, test):
            b = summarize_buckets(part, win_fn)
            base, c = b.get('baseline', {'n': 0, 'wins': 0}), b.get(key, {'n': 0, 'wins': 0})
            if not base['n'] or not c['n']:
                row_s.append(('n/a', 'n/a', 0))
                deltas.append(None)
                continue
            base_wr = base['wins'] / base['n']
            c_wr = c['wins'] / c['n']
            d = c_wr - base_wr
            p = fisher_p(c['wins'], c['n'] - c['wins'], base['wins'], base['n'] - base['wins'])
            row_s.append((f'{d:+.1%}', fmt_p(p), c['n']))
            deltas.append(d)
        if deltas[0] is None or deltas[1] is None:
            flip = 'n/a'
        elif deltas[0] * deltas[1] < 0:
            flip = '**YES**'
        else:
            flip = 'no'
        t_d, t_p, t_n = row_s[0]
        v_d, v_p, v_n = row_s[1]
        lines.append(
            f'| {label} | {t_d} (n={t_n}) | {t_p} | {v_d} (n={v_n}) | {v_p} | {flip} |'
        )
    lines.append('')
    return '\n'.join(lines)


def verdict_block(ann_td, ann_sig, win_fn, split_dt) -> str:
    """Honest read: cooldown direction = after-k WR < baseline."""
    lines = ['## Verdict', '']
    for title, ann in (('TOKEN:DIRECTION', ann_td), ('signal', ann_sig)):
        b = summarize_buckets(ann, win_fn)
        base = b.get('baseline', {'n': 0, 'wins': 0})
        if not base['n']:
            lines.append(f'- **{title}:** no baseline trades — indeterminate.')
            continue
        base_wr = base['wins'] / base['n']
        parts = []
        supported = 0
        wallace = 0
        tested = 0
        underpowered = 0
        for key in ('after1', 'after2', 'after3plus'):
            c = b.get(key, {'n': 0, 'wins': 0})
            if not c['n']:
                parts.append(f'{key}: n=0')
                continue
            wr = c['wins'] / c['n']
            p = fisher_p(c['wins'], c['n'] - c['wins'], base['wins'], base['n'] - base['wins'])
            d = wr - base_wr
            tag = ''
            if c['n'] < MIN_CELL:
                tag = ' (underpowered)'
                underpowered += 1
            elif p < 0.05:
                tested += 1
                if d < 0:
                    supported += 1
                else:
                    wallace += 1
            parts.append(
                f'{key}: {wr:.1%} vs {base_wr:.1%} (Δ{d:+.1%}, p={fmt_p(p)}, n={c["n"]}){tag}'
            )
        lines.append(f'- **{title}** (base WR {base_wr:.1%}): ' + '; '.join(parts))
        if tested == 0:
            lines.append(
                f'  - → **indeterminate at this n** ({underpowered} cells n<{MIN_CELL}, '
                'none significant). No ruling either way.'
            )
        elif supported > wallace:
            lines.append(
                f'  - → LOSS_COOLDOWN direction (worse after losses) supported in '
                f'{supported} significant cell(s), Wallace in {wallace}.'
            )
        elif wallace > supported:
            lines.append(
                f'  - → Wallace direction (better after losses) supported in '
                f'{wallace} significant cell(s), cooldown in {supported}.'
            )
        else:
            lines.append('  - → split decision — mixed signs, no clean ruling.')
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser(description='Read-only loss-streak analysis (Wallace 1+2)')
    ap.add_argument('--days', type=int, default=DEFAULT_DAYS,
                    help=f'lookback window in days (default {DEFAULT_DAYS})')
    ap.add_argument('--train-days', type=int, default=DEFAULT_TRAIN_DAYS,
                    help=f'first N days = derive window (default {DEFAULT_TRAIN_DAYS})')
    ap.add_argument('--unit', choices=['both', 'token', 'signal'], default='both')
    args = ap.parse_args()

    rows = fetch_trades(args.days)
    if not rows:
        print('No trades in window.')
        return

    now = rows[-1]['close_time']  # anchor on data, not wall clock
    window_start = rows[0]['close_time']
    split_dt = now - timedelta(days=args.days - args.train_days)

    hype_null = sum(1 for r in rows if r['hype_realized_pnl_usdt'] is None)
    print(f'# Streak analysis — {args.days}d window')
    print()
    print(f'- trades (status=closed): **{len(rows)}**')
    print(f'- window: {window_start} → {now} (data-anchored)')
    print(f'- OOS split at: {split_dt} (train={args.train_days}d / test={args.days - args.train_days}d)')
    print(f'- hype_realized_pnl_usdt NULL: {hype_null}/{len(rows)} (sensitivity falls back to pnl_usdt)')
    print()

    win_fns = [('pnl_usdt > 0 (primary)', win_pnl),
               ('hype_realized where NOT NULL (sensitivity)', win_hype)]

    units_to_run = []
    if args.unit in ('both', 'token'):
        units_to_run.append(('token_dir', 'TOKEN:DIRECTION (LOSS_COOLDOWN key)'))
    if args.unit in ('both', 'signal'):
        units_to_run.append(('signal', 'signal (KILL_MAX_CONSEC consumer)'))

    all_output = []
    verdict_inputs = {}
    for unit_code, unit_title in units_to_run:
        for r in rows:
            r['_unit'] = unit_code
        # annotate per win_fn (streak state depends on win definition)
        for wf_name, win_fn in win_fns:
            tag = f'{unit_title} | win={wf_name}'
            ann = annotate(list(rows), win_fn)
            all_streaks, per_unit_max = completed_streaks(rows, win_fn)
            b = summarize_buckets(ann, win_fn)
            all_output.append(f'## {tag}\n')
            all_output.append(streak_dist_table(all_streaks, per_unit_max,
                                                f'Streak distribution — {unit_title}'))
            all_output.append(bucket_table(b, f'Next-trade WR/pnl by prior streak — {unit_title}'))
            all_output.append(mfe_table(ann, win_fn,
                                        f'First-win-after-streak MFE — {unit_title}'))
            all_output.append(oos_section(ann, win_fn, split_dt,
                                          f'{unit_title} ({wf_name})'))
            if wf_name.startswith('pnl'):
                verdict_inputs[unit_title] = ann

        # per-signal max streak headroom (secondary unit detail)
        if unit_code == 'signal':
            _, pum = completed_streaks(rows, win_pnl)
            top = sorted(pum.items(), key=lambda x: -x[1])[:15]
            all_output.append('### Top signals by max loss streak (primary win def)\n')
            all_output.append('| signal | max streak |')
            all_output.append('|---|---:|')
            for k, v in top:
                all_output.append(f'| {k} | {v} |')
            all_output.append('')

    print('\n'.join(all_output))

    print(verdict_block(
        verdict_inputs.get('TOKEN:DIRECTION (LOSS_COOLDOWN key)', []),
        verdict_inputs.get('signal (KILL_MAX_CONSEC consumer)', []),
        win_pnl, split_dt,
    ))

    print('## Caveats')
    print()
    print('- Fisher/Welch assume independent trades; trades within a unit are clustered '
          '— p-values are optimistic under clustering.')
    print('- entry_streak computed per unit on the full window; OOS split does not '
          're-derive streaks inside each partition (state carries across the cut).')
    print('- pnl_usdt == 0 (breakeven) counted as non-win for streaks; the live cooldown '
          'only increments on pnl < 0 and only clears on pnl > 0.')
    print('- Historical max streak is in-sample, never a bound (Wallace known-flaw note).')
    print('- This is observational: entries that survived the cooldown are selected — '
          'it cannot prove what blocked trades would have done.')
    print()
    print('## Reproduce')
    print()
    print('```bash')
    print(f'python3 /root/.hermes/scripts/streak_analysis.py --days {args.days} '
          f'--train-days {args.train_days}')
    print('```')


if __name__ == '__main__':
    main()
