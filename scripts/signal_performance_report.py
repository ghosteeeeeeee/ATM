#!/usr/bin/env python3
"""
Signal Performance Reporter — 6h/24h focused view.

Data source: signal_outcomes (signals_hermes_runtime.db)
Output: automation/signal_report.md
Timer: every 6 hours (hermes-signal-report.timer)

Usage:
  python3 signal_performance_report.py
"""

import sys, os, re, fcntl, sqlite3, subprocess
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import RUNTIME_DB

LOCK_FILE = '/tmp/hermes-signal-report.lock'
REPORT_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'automation', 'signal_report.md')
CONSTANTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hermes_constants.py')

# Thresholds
WR_WINNER = 55      # >55% WR → winner
WR_LOSER = 30       # <30% WR → loser
PNL_LOSER = -2      # total PnL < -2% → loser
MIN_TRADES_WIN = 5  # min trades for winner classification
MIN_TRADES_LOSE = 5 # min trades for loser classification
MIN_TRADES_MARGINAL = 2


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    print(f"[{ts}] {msg}")


def query_period(hours):
    """Query signal performance for a time period, grouped by (signal_type, direction)."""
    conn = sqlite3.connect(RUNTIME_DB)
    try:
        c = conn.cursor()
        c.execute("""
            SELECT signal_type, direction,
                   COUNT(*) as trades,
                   SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
                   ROUND(SUM(pnl_pct), 2) as total_pnl,
                   ROUND(AVG(pnl_pct), 3) as avg_pnl
            FROM signal_outcomes
            WHERE created_at > datetime('now', '-' || ? || ' hours')
              AND trade_id IS NOT NULL
            GROUP BY signal_type, direction
            HAVING trades >= ?
            ORDER BY total_pnl DESC
        """, (hours, MIN_TRADES_MARGINAL))
        return c.fetchall()
    finally:
        conn.close()


def get_registry_status():
    """Get enabled/disabled status from hermes_constants.py."""
    status = {}
    try:
        with open(CONSTANTS_FILE) as f:
            content = f.read()
        for match in re.finditer(r'^(\w+_ENABLED)\s*=\s*(True|False)', content, re.MULTILINE):
            status[match.group(1)] = match.group(2) == 'True'
    except Exception as e:
        log(f"Error reading constants: {e}")
    return status


def map_signal_to_flag(signal_type):
    """Map signal_type (DB format) to *_ENABLED flag name. From signal_auditor.py."""
    base = signal_type.split(',')[0].strip()
    suffix = ''
    if base.endswith('+'):
        suffix = '_PLUS'
        base = base[:-1]
    elif base.endswith('-'):
        suffix = '_MINUS'
        base = base[:-1]

    base_underscore = base.replace('-', '_')

    master_overrides = {
        'bb_squeeze': 'BOLLINGER_SQUEEZE',
        'pattern_scanner': 'PATTERN_FLAG',
        'volume_hl': 'VOLUME_HL',
        'atr_compression': 'ATR_COMPRESSION',
    }
    exact_overrides = {
        'accel_300_vel': 'ACCEL_300_VELOCITY',
        'inv_accel_300': 'INVERSE_ACCEL_300',
        'tl_break_long': 'TL_BREAK_PLUS',
        'tl_break_short': 'TL_BREAK_MINUS',
        'ema9_sma20': 'EMA9_SMA20',
        'ma_cross_5m': 'MA_CROSS_5M',
        'gap_300': 'GAP_300',
        'mtp_zscore': 'MTP_ZSCORE',
    }

    if base_underscore in master_overrides:
        flag_base = master_overrides[base_underscore]
        return f'{flag_base}{suffix}_ENABLED' if suffix else f'{flag_base}_ENABLED'
    if base_underscore in exact_overrides:
        flag_base = exact_overrides[base_underscore]
        return f'{flag_base}{suffix}_ENABLED' if suffix else f'{flag_base}_ENABLED'

    flag_base = base_underscore.upper()
    return f'{flag_base}{suffix}_ENABLED' if suffix else f'{flag_base}_ENABLED'


def check_inversions(hours=24):
    """Check for direction mismatches (signal says LONG but direction is SHORT, or vice versa)."""
    conn = sqlite3.connect(RUNTIME_DB)
    try:
        c = conn.cursor()
        c.execute("""
            SELECT token, signal_type, direction, is_win, pnl_pct, created_at
            FROM signal_outcomes
            WHERE created_at > datetime('now', '-' || ? || ' hours')
              AND trade_id IS NOT NULL
              AND (
                  (signal_type LIKE '%long%' AND direction = 'SHORT')
                  OR (signal_type LIKE '%short%' AND direction = 'LONG')
              )
            ORDER BY created_at DESC LIMIT 20
        """, (hours,))
        return c.fetchall()
    finally:
        conn.close()


def get_overall_stats():
    """Get total trade stats."""
    conn = sqlite3.connect(RUNTIME_DB)
    try:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
                   ROUND(SUM(pnl_pct), 2) as total_pnl,
                   MIN(created_at) as first,
                   MAX(created_at) as last
            FROM signal_outcomes WHERE trade_id IS NOT NULL
        """)
        return c.fetchone()
    finally:
        conn.close()


def status_str(flag, registry):
    """Return ENABLED/DISABLED string for a flag."""
    if flag is None:
        return '❓'
    is_on = registry.get(flag)
    return 'ENABLED' if is_on else ('DISABLED' if is_on is not None else '❓')


def format_pct(val):
    """Format percentage with sign."""
    return f"{val:+.1f}%" if val is not None else "—"


def format_pnl(val):
    """Format PnL with sign."""
    return f"{val:+.2f}" if val is not None else "—"


def get_param_change_log(days=7):
    """Get recent param changes to hermes_constants.py from git log."""
    changes = []
    try:
        result = subprocess.run(
            ['git', 'log', f'--since={days} days', '--oneline', '--no-merges',
             '-20', '--', 'scripts/hermes_constants.py'],
            capture_output=True, text=True, cwd='/root/.hermes'
        )
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split(' ', 1)
            if len(parts) == 2:
                commit_hash, message = parts
                # Get the date from git log
                date_result = subprocess.run(
                    ['git', 'log', '-1', '--format=%ai', commit_hash],
                    capture_output=True, text=True, cwd='/root/.hermes'
                )
                date_str = date_result.stdout.strip()[:10] if date_result.stdout.strip() else 'unknown'
                changes.append({
                    'commit': commit_hash,
                    'message': message.strip(),
                    'date': date_str,
                })
    except Exception as e:
        log(f"Error getting param change log: {e}")
    return changes


def main():
    log("=== Signal Performance Reporter ===")

    lock_fd = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_fd.close()
        log("Another instance running, exiting")
        return

    try:
        registry = get_registry_status()

        # Query both periods
        rows_6h = query_period(6)
        rows_24h = query_period(24)
        log(f"6h: {len(rows_6h)} signal combos | 24h: {len(rows_24h)} signal combos")

        # Merge into unified view: key = (signal_type, direction)
        signals = defaultdict(lambda: {'6h': {}, '24h': {}})

        for sig_type, direction, trades, wins, total_pnl, avg_pnl in rows_6h:
            wr = round(wins / trades * 100, 1) if trades else 0
            signals[(sig_type, direction)]['6h'] = {
                'trades': trades, 'wins': wins, 'wr': wr,
                'total_pnl': total_pnl, 'avg_pnl': avg_pnl,
            }

        for sig_type, direction, trades, wins, total_pnl, avg_pnl in rows_24h:
            wr = round(wins / trades * 100, 1) if trades else 0
            signals[(sig_type, direction)]['24h'] = {
                'trades': trades, 'wins': wins, 'wr': wr,
                'total_pnl': total_pnl, 'avg_pnl': avg_pnl,
            }

        # Categorize
        winners = []
        losers = []
        marginal = []
        disabled_but_good = []

        for (sig_type, direction), periods in signals.items():
            flag = map_signal_to_flag(sig_type)
            is_enabled = registry.get(flag)
            s24 = periods.get('24h', {})
            s6 = periods.get('6h', {})

            # Use 24h as primary, 6h as confirmation
            wr = s24.get('wr', s6.get('wr', 0))
            total_pnl = s24.get('total_pnl', s6.get('total_pnl', 0))
            trades = s24.get('trades', 0)

            entry = {
                'signal_type': sig_type,
                'direction': direction,
                'flag': flag,
                'is_enabled': is_enabled,
                's6': s6,
                's24': s24,
                'wr': wr,
                'total_pnl': total_pnl,
                'trades': trades,
            }

            # Loser: WR < 30% over 5+ trades AND PnL < -2%
            if wr < WR_LOSER and trades >= MIN_TRADES_LOSE and total_pnl < PNL_LOSER:
                losers.append(entry)
            # Winner: WR > 55% over 5+ trades AND PnL > 0
            elif wr > WR_WINNER and trades >= MIN_TRADES_WIN and total_pnl > 0:
                winners.append(entry)
            # Marginal: 30-50% WR with small sample
            elif 30 <= wr <= 50:
                marginal.append(entry)

            # Disabled but good: disabled signal with decent recent performance
            if is_enabled is False and wr >= WR_WINNER and trades >= MIN_TRADES_WIN:
                disabled_but_good.append(entry)

        # Sort
        winners.sort(key=lambda x: x.get('s24', {}).get('total_pnl', 0), reverse=True)
        losers.sort(key=lambda x: x.get('s24', {}).get('total_pnl', 0))
        marginal.sort(key=lambda x: x.get('s24', {}).get('total_pnl', 0))

        # Signal inversions
        inversions = check_inversions(24)

        # Overall stats
        overall = get_overall_stats()

        # Generate report
        ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        lines = []
        lines.append(f"# Signal Performance Report")
        lines.append(f"**Generated:** {ts} | **Period:** Last 6h + 24h")
        lines.append("")

        # Overall stats
        total, wins, total_pnl, first, last = overall
        wr = round(wins / total * 100, 1) if total else 0
        lines.append("## Overall Stats")
        lines.append(f"- **Total trades (all time):** {total:,} | **WR:** {wr}% | **PnL:** {total_pnl:+.2f}%")
        lines.append(f"- **Date range:** {first[:10]} → {last[:10]}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Winners
        lines.append("## WINNERS (WR > 55%, PnL > 0)")
        lines.append("")
        if winners:
            lines.append("| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |")
            lines.append("|--------|-----|------|-------|--------|-------|--------|---------|--------|")
            for e in winners:
                s6, s24 = e['s6'], e['s24']
                status = status_str(e['flag'], registry)
                lines.append(f"| {e['signal_type'][:35]} | {e['direction']} "
                    f"| {s6.get('trades', '—')} | {s6.get('wr', '—')}% | {format_pnl(s6.get('total_pnl'))} "
                    f"| {s24.get('trades', '—')} | {s24.get('wr', '—')}% | {format_pnl(s24.get('total_pnl'))} "
                    f"| {status} |")
        else:
            lines.append("None found.")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Losers
        lines.append("## LOSERS (WR < 30%, PnL < -2%)")
        lines.append("")
        if losers:
            lines.append("| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |")
            lines.append("|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|")
            for e in losers:
                s6, s24 = e['s6'], e['s24']
                status = status_str(e['flag'], registry)
                lines.append(f"| {e['signal_type'][:35]} | {e['direction']} "
                    f"| {s6.get('trades', '—')} | {s6.get('wr', '—')}% | {format_pnl(s6.get('total_pnl'))} "
                    f"| {s24.get('trades', '—')} | {s24.get('wr', '—')}% | {format_pnl(s24.get('total_pnl'))} "
                    f"| {status} | **DISABLE** |")
        else:
            lines.append("None found.")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Marginal
        lines.append("## MARGINAL (30-50% WR)")
        lines.append("")
        if marginal:
            lines.append("| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |")
            lines.append("|--------|-----|-------|--------|---------|--------|------|")
            for e in marginal:
                s24 = e['s24']
                status = status_str(e['flag'], registry)
                note = "Needs more data" if e['trades'] < MIN_TRADES_LOSE else "Borderline"
                lines.append(f"| {e['signal_type'][:35]} | {e['direction']} "
                    f"| {s24.get('trades', '—')} | {s24.get('wr', '—')}% | {format_pnl(s24.get('total_pnl'))} "
                    f"| {status} | {note} |")
        else:
            lines.append("None found.")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Disabled but good
        lines.append("## DISABLED BUT GOOD (candidates for re-enabling)")
        lines.append("")
        if disabled_but_good:
            lines.append("| Signal | Dir | Last WR | Last PnL | Recommendation |")
            lines.append("|--------|-----|---------|----------|----------------|")
            for e in disabled_but_good:
                s24 = e['s24'] or e['s6']
                lines.append(f"| {e['signal_type'][:35]} | {e['direction']} "
                    f"| {s24.get('wr', '—')}% | {format_pnl(s24.get('total_pnl'))} "
                    f"| **WATCH** — re-enable candidate |")
        else:
            lines.append("None found. Top performers are already enabled.")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Signal inversions
        lines.append("## SIGNAL INVERSIONS (24h)")
        lines.append("")
        if inversions:
            lines.append(f"**⚠️ {len(inversions)} inversion(s) found:**")
            lines.append("")
            lines.append("| Token | Signal | Dir | Win | PnL | Time |")
            lines.append("|-------|--------|-----|-----|-----|------|")
            for token, sig, direction, win, pnl, ts_str in inversions[:10]:
                lines.append(f"| {token} | {sig[:30]} | {direction} | {'W' if win else 'L'} | {pnl:+.2f}% | {ts_str[:16]} |")
            lines.append("")
            lines.append("**Action required:** Investigate signal_type vs direction mismatch.")
        else:
            lines.append("**No inversions found.** All signals respect their direction labels.")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Recommendations
        lines.append("## RECOMMENDATIONS")
        lines.append("")
        rec_num = 1
        rec_lines = []

        for e in losers:
            flag = e['flag']
            s24 = e['s24']
            lines.append(f"{rec_num}. **[DISABLE] {e['signal_type']} {e['direction']}** — "
                f"WR={e['wr']}%, PnL={e['total_pnl']:+.2f}% over {e['trades']} trades (24h).")
            rec_num += 1

        for e in marginal:
            lines.append(f"{rec_num}. **[WATCH] {e['signal_type']} {e['direction']}** — "
                f"WR={e['wr']}%, PnL={e['total_pnl']:+.2f}% over {e['trades']} trades. Monitor next cycle.")
            rec_num += 1

        if winners:
            winner_names = ", ".join(e['signal_type'][:20] for e in winners[:5])
            lines.append(f"{rec_num}. **[KEEP] {len(winners)} winning combos** — {winner_names}. LONG side dominant.")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*Report auto-generated. Next report: ~6h from now.*")

        # Param change log
        param_changes = get_param_change_log(7)
        if param_changes:
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append("## PARAM CHANGE LOG (last 7 days)")
            lines.append("")
            lines.append("| Date | Commit | Change |")
            lines.append("|------|--------|--------|")
            for c in param_changes[:10]:
                msg = c['message'][:60] + ('...' if len(c['message']) > 60 else '')
                lines.append(f"| {c['date']} | {c['commit'][:7]} | {msg} |")
            lines.append("")
            lines.append("*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*")

        # Write atomically
        os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
        tmp = REPORT_MD + '.tmp'
        with open(tmp, 'w') as f:
            f.write('\n'.join(lines))
        os.replace(tmp, REPORT_MD)

        log(f"Report written: {REPORT_MD}")
        log(f"Winners: {len(winners)} | Losers: {len(losers)} | Marginal: {len(marginal)} | Disabled-but-good: {len(disabled_but_good)}")
        if inversions:
            log(f"⚠️ {len(inversions)} signal inversions detected!")

    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == '__main__':
    main()
