#!/usr/bin/env python3
"""
study_winning_combos.py — 4x/day analysis of which signal combinations worked.

Purpose: T's A/B tester. Find awesome trades, study them, identify what variables
worked, and build a permanent record of the winning combos so we can:
  1. Absorb winning combos into Hermes natively
  2. Kill patterns that produce false positives
  3. Adjust OpenClaw/Hermes signal weights based on real evidence

Run: Every 6 hours via cron.
Output: Structured log + human-readable summary to logs/study_winning_combos.log
        + key findings appended to logs/study_history.log for long-term tracking.
"""

import psycopg2
import sqlite3
import os
import json
import time
from datetime import datetime, timedelta

# ─── Config ───────────────────────────────────────────────────────────────────
LOG_FILE   = '/root/.hermes/logs/study_winning_combos.log'
HIST_FILE   = '/root/.hermes/logs/study_history.log'
HL_TRADE_DB = '/root/.hermes/data/hl_paper_trades.db'
PG_CREDS = dict(host='/var/run/postgresql', dbname='brain',
                user='postgres', password='postgres')
RT_DB     = '/root/.hermes/data/signals_hermes_runtime.db'
STUDY_HRS = 24   # look back window

# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg, fp=None):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    if fp:
        fp.write(line + '\n')

def pnl_emoji(pnl):
    if pnl is None:
        return '?'
    if pnl >= 3.0:
        return '💰'
    if pnl >= 1.0:
        return '✅'
    if pnl >= 0:
        return '🟡'
    if pnl >= -1.0:
        return '🟠'
    return '❌'

def get_recent_trades(hours=STUDY_HRS):
    """Get closed paper trades from brain.trades in the study window."""
    cutoff = datetime.now() - timedelta(hours=hours)
    conn = psycopg2.connect(**PG_CREDS)
    c = conn.cursor()
    c.execute("""
        SELECT token, direction, signal, confidence, pnl_pct, status,
               exit_reason, close_reason, open_time, close_time,
               entry_price, exit_price, leverage, regime, exit_conditions,
               entry_rsi_14, entry_macd_hist, entry_atr_14
        FROM trades
        WHERE paper = true
        AND close_time IS NOT NULL
        AND close_time >= %s
        ORDER BY close_time DESC
    """, (cutoff,))
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return rows

def get_signal_sources_for_trade(token, direction, trade_open_time, window_minutes=120):
    """Get the signal sources that contributed to a trade within the window."""
    cutoff = (trade_open_time - timedelta(minutes=window_minutes)).strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect(RT_DB)
    c = conn.cursor()
    c.execute("""
        SELECT source, confidence, signal_type, momentum_state,
               rsi_14, macd_hist, z_score, created_at
        FROM signals
        WHERE token=? AND direction=? AND decision IN ('APPROVED','EXECUTED','PENDING')
        AND created_at >= ?
        ORDER BY created_at DESC
        LIMIT 10
    """, (token.upper(), direction.upper(), cutoff))
    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, r)) for r in c.fetchall()]
    conn.close()
    return rows

def classify_sources(signals):
    """Separate OpenClaw (mtf-*) from Hermes sources."""
    mtf      = sorted(set(s['source'] for s in signals if s['source'] and s['source'].startswith('mtf-')))
    hermes   = sorted(set(s['source'] for s in signals if s['source'] and not s['source'].startswith('mtf-')))
    has_mtf  = bool(mtf)
    has_hermes = bool(hermes)
    combo_type = 'both' if (has_mtf and has_hermes) else ('mtf_only' if has_mtf else ('hermes_only' if has_hermes else 'unknown'))
    return mtf, hermes, combo_type

def winning_combo_key(signals):
    """Build a sortable key string for the source combination."""
    mtf, hermes, _ = classify_sources(signals)
    mtf_part  = '+'.join(sorted(mtf)) if mtf else 'none'
    hermes_part = '+'.join(sorted(hermes)) if hermes else 'none'
    return f'mtf[{mtf_part}]|hermes[{hermes_part}]'

# ─── Main Study ────────────────────────────────────────────────────────────────

def run_study():
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    summary = []

    with open(LOG_FILE, 'a') as lf, open(HIST_FILE, 'a') as hf:
        log('═' * 70, lf)
        log(f'STUDY RUN — {ts} (lookback: {STUDY_HRS}h)', lf)
        log('═' * 70, lf)

        trades = get_recent_trades(hours=STUDY_HRS)
        if not trades:
            log('No closed trades in window. Nothing to study.', lf)
            return

        log(f'Found {len(trades)} closed trades. Analyzing...', lf)

        # ── Per-trade breakdown ────────────────────────────────────────────
        combo_stats = {}   # combo_key -> {wins, losses, total_pnl, trades:[]}
        win_signals  = []  # mtf signals from winning trades
        loss_signals = []  # mtf signals from losing trades

        for trade in trades:
            token     = trade['token']
            direction = trade['direction']
            pnl       = trade['pnl_pct']
            conf      = trade['confidence']
            signal    = trade['signal']      # e.g. 'conf-3s'
            exit_rsn  = trade['exit_reason'] or trade['close_reason'] or ''
            open_t    = trade['open_time']
            entry     = trade['entry_price']
            exit_p    = trade['exit_price']
            lev       = trade['leverage']
            regime    = trade['regime']
            rsi       = trade['entry_rsi_14']
            macd      = trade['entry_macd_hist']
            atr       = trade['entry_atr_14']
            e_cond    = trade['exit_conditions']

            signals = get_signal_sources_for_trade(token, direction, open_t)
            mtf, hermes, combo_type = classify_sources(signals)
            ck = winning_combo_key(signals)

            emoji = pnl_emoji(pnl)
            is_win = pnl is not None and pnl > 0

            # Log per-trade
            log(f'  {emoji} {token:10s} {direction:5s} pnl={pnl:+.2f}% conf={conf}% '
                f'lev={lev}x signal={signal} close={exit_rsn[:30]} '
                f'mtf=[{",".join(mtf) if mtf else "-"}] '
                f'hermes=[{",".join(hermes) if hermes else "-"}]', lf)

            # Aggregate combo stats
            if ck not in combo_stats:
                combo_stats[ck] = {'wins': 0, 'losses': 0, 'breakeven': 0,
                                   'total_pnl': 0, 'trades': []}
            combo_stats[ck]['trades'].append({
                'token': token, 'pnl': pnl, 'conf': conf, 'signal': signal,
                'exit_rsn': exit_rsn, 'lev': lev, 'combo_type': combo_type
            })
            if is_win:
                combo_stats[ck]['wins'] += 1
                win_signals.extend(mtf)
            else:
                combo_stats[ck]['losses'] += 1
                loss_signals.extend(mtf)

            if pnl is not None:
                combo_stats[ck]['total_pnl'] += pnl

        # ── Combo leaderboard ──────────────────────────────────────────────
        log('', lf)
        log('── WINNING COMBINATION LEADERBOARD ─────────────────────────────', lf)

        sorted_combos = sorted(combo_stats.items(),
                               key=lambda x: (x[1]['wins'], x[1]['total_pnl']),
                               reverse=True)

        top_combo = None
        for i, (ck, stats) in enumerate(sorted_combos):
            total  = stats['wins'] + stats['losses'] + stats['breakeven']
            win_rt = stats['wins'] / total * 100 if total > 0 else 0
            avg_pnl = stats['total_pnl'] / total if total > 0 else 0
            mtf_s  = ck.split('|')[0].replace('mtf[', '').replace(']', '')
            hermes_s = ck.split('|')[1].replace('hermes[', '').replace(']', '')

            badge = '🥇' if i == 0 else ('🥈' if i == 1 else ('🥉' if i == 2 else '  '))
            log(f'  {badge} #{i+1} win_rate={win_rt:.0f}% avg_pnl={avg_pnl:+.2f}% '
                f'({stats["wins"]}W/{stats["losses"]}L/{stats["breakeven"]}B n={total})', lf)
            log(f'      mtf:      [{mtf_s}]', lf)
            log(f'      hermes:   [{hermes_s}]', lf)

            if i == 0:
                top_combo = (ck, stats, mtf_s, hermes_s, win_rt, avg_pnl)

        # ── MTF signal breakdown ────────────────────────────────────────────
        if win_signals or loss_signals:
            log('', lf)
            log('── MTF SIGNAL WIN RATES ───────────────────────────────────────', lf)
            from collections import Counter
            win_c  = Counter(win_signals)
            loss_c = Counter(loss_signals)
            all_mtf = set(win_c.keys()) | set(loss_c.keys())
            for src in sorted(all_mtf, key=lambda s: win_c.get(s, 0) - loss_c.get(s, 0), reverse=True):
                w = win_c.get(src, 0)
                l = loss_c.get(src, 0)
                total = w + l
                wr = w / total * 100 if total > 0 else 0
                log(f'  {src:30s}  win_rate={wr:.0f}%  ({w}W/{l}L n={total})')

        # ── Key findings ────────────────────────────────────────────────────
        log('', lf)
        log('── KEY FINDINGS ──────────────────────────────────────────────', lf)

        findings = []

        if top_combo:
            ck, stats, mtf_s, hermes_s, win_rt, avg_pnl = top_combo
            if win_rt >= 60 and stats['wins'] >= 2:
                finding = f'STRONG: mtf=[{mtf_s}] + hermes=[{hermes_s}] wins {win_rt:.0f}% avg {avg_pnl:+.2f}%'
                findings.append(('STRONG', finding))
                log(f'  💡 {finding}', lf)
            elif win_rt >= 50 and stats['wins'] >= 2:
                finding = f'PROMISING: mtf=[{mtf_s}] + hermes=[{hermes_s}] wins {win_rt:.0f}% avg {avg_pnl:+.2f}%'
                findings.append(('PROMISING', finding))
                log(f'  ⚠️  {finding}', lf)

        # Check for mtf-only wins
        mtf_only_wins = sum(
            1 for ck, s in combo_stats.items()
            if 'mtf[' in ck and 'hermes[none]' in ck and s['wins'] > 0
        )
        hermes_only_wins = sum(
            1 for ck, s in combo_stats.items()
            if 'hermes[' in ck and 'mtf[none]' in ck and s['wins'] > 0
        )
        both_wins = sum(
            1 for ck, s in combo_stats.items()
            if 'mtf[none]' not in ck and 'hermes[none]' not in ck and s['wins'] > 0
        )
        log(f'  📊 mtf-only combos:    {mtf_only_wins} winning patterns', lf)
        log(f'  📊 hermes-only combos: {hermes_only_wins} winning patterns', lf)
        log(f'  📊 combined combos:    {both_wins} winning patterns', lf)

        # ── Persist to history log ──────────────────────────────────────────
        if top_combo:
            ck, stats, mtf_s, hermes_s, win_rt, avg_pnl = top_combo
            hist_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            hist_line = (f'{hist_ts} | n={stats["wins"]+stats["losses"]+stats["breakeven"]} '
                         f'| top_combo_mtf=[{mtf_s}] '
                         f'| top_combo_hermes=[{hermes_s}] '
                         f'| win_rate={win_rt:.0f}% '
                         f'| avg_pnl={avg_pnl:+.2f}% '
                         f'| mtf_only={mtf_only_wins} '
                         f'| hermes_only={hermes_only_wins} '
                         f'| combined={both_wins}')
            hf.write(hist_line + '\n')
            hf.flush()
            log(f'  📝 Persisted to {HIST_FILE}', lf)

        total_trades = len(trades)
        wins = sum(1 for t in trades if t['pnl_pct'] is not None and t['pnl_pct'] > 0)
        losses = sum(1 for t in trades if t['pnl_pct'] is not None and t['pnl_pct'] <= 0)
        total_pnl = sum(t['pnl_pct'] or 0 for t in trades)
        log(f'  📈 Overall: {wins}W/{losses}L ({wins/(wins+losses)*100:.0f}% win rate) '
            f'Total PnL: {total_pnl:+.2f}% across {total_trades} trades', lf)
        log('', lf)

        print(f'\n=== STUDY COMPLETE ===')
        print(f'Trades studied: {total_trades}')
        print(f'Overall win rate: {wins}/{wins+losses} = {wins/(wins+losses)*100:.0f}%')
        print(f'Total PnL: {total_pnl:+.2f}%')
        print(f'Top combo: mtf=[{top_combo[2] if top_combo else "N/A"}] hermes=[{top_combo[3] if top_combo else "N/A"}]')
        print(f'Full log: {LOG_FILE}')


if __name__ == '__main__':
    run_study()
