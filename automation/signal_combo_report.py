#!/usr/bin/env python3
"""
signal_combo_report.py — Analyze signal combo performance (read-only).

Generates a report of winning/losing combos without updating any files.
Safe to run alongside self_learner.py which handles weight updates.

Output: /root/.hermes/automation/signal_combo_report.md
"""
import os
import sys
import sqlite3
from datetime import datetime, timezone

sys.path.insert(0, '/root/.hermes/scripts')
from paths import RUNTIME_DB

# ── Config ──────────────────────────────────────────────────────────────
REPORT_FILE = '/root/.hermes/automation/signal_combo_report.md'
MIN_TRADES = 5
LOOKBACK_DAYS = 14


def _get_combo_stats():
    """Query signal combo performance from PostgreSQL."""
    conn = None
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT signal, direction, COUNT(*) as n,
                   SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END)*1.0/COUNT(*) as wr,
                   AVG(pnl_pct) as avg_pnl,
                   SUM(pnl_usdt) as total_pnl
            FROM trades
            WHERE status = 'closed'
            AND close_time > NOW() - INTERVAL '{LOOKBACK_DAYS} days'
            GROUP BY signal, direction
            HAVING COUNT(*) >= {MIN_TRADES}
            ORDER BY total_pnl DESC
        """)
        return cur.fetchall()
    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def generate_report():
    """Generate signal combo report."""
    combos = _get_combo_stats()

    # Categorize
    winners = []
    losers = []
    neutral = []

    for signal_type, direction, n, wr, avg_pnl, total_pnl in combos:
        entry = {
            'signal': signal_type,
            'direction': direction,
            'trades': n,
            'wr': round(wr * 100, 1),
            'avg_pnl': round(avg_pnl or 0, 3),
            'total_pnl': round(total_pnl or 0, 2),
        }
        if total_pnl and total_pnl > 0 and wr >= 0.55:
            winners.append(entry)
        elif total_pnl and total_pnl < -0.05:
            losers.append(entry)
        else:
            neutral.append(entry)

    # Generate markdown
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    md = f"""# Signal Combo Report

**Generated**: {now}
**Period**: Last {LOOKBACK_DAYS} days
**Min trades**: {MIN_TRADES}

## Summary
- **Winning combos**: {len(winners)}
- **Losing combos**: {len(losers)}
- **Neutral combos**: {len(neutral)}
- **Total PnL**: ${sum(w['total_pnl'] for w in winners) + sum(l['total_pnl'] for l in losers):.2f}

## Winning Combos (WR ≥ 55%, PnL > 0)

| Signal | Direction | Trades | WR | Avg PnL | Total PnL |
|--------|-----------|--------|-----|---------|-----------|
"""
    for w in winners[:15]:
        md += f"| {w['signal'][:45]} | {w['direction']} | {w['trades']} | {w['wr']}% | {w['avg_pnl']:+.3f}% | ${w['total_pnl']:+.2f} |\n"

    md += f"""
## Losing Combos (PnL < -$0.05)

| Signal | Direction | Trades | WR | Avg PnL | Total PnL |
|--------|-----------|--------|-----|---------|-----------|
"""
    for l in losers[:15]:
        md += f"| {l['signal'][:45]} | {l['direction']} | {l['trades']} | {l['wr']}% | {l['avg_pnl']:+.3f}% | ${l['total_pnl']:+.2f} |\n"

    md += f"""
## Recommendations

### Boost (WR ≥ 60%, PnL > 0)
"""
    for w in winners[:10]:
        if w['wr'] >= 60:
            md += f"- **{w['signal']}** ({w['direction']}): {w['wr']}% WR, ${w['total_pnl']:+.2f} — boost weight\n"

    md += f"""
### Suppress (WR < 45% or PnL < -$0.10)
"""
    for l in losers[:10]:
        if l['wr'] < 45 or l['total_pnl'] < -0.10:
            md += f"- **{l['signal']}** ({l['direction']}): {l['wr']}% WR, ${l['total_pnl']:+.2f} — suppress weight\n"

    md += f"""
### Disable (WR < 30% with 10+ trades)
"""
    for l in losers:
        if l['wr'] < 30 and l['trades'] >= 10:
            md += f"- **{l['signal']}** ({l['direction']}): {l['wr']}% WR, {l['trades']} trades — consider disabling\n"

    return md


def main():
    """Generate and save report."""
    md = generate_report()
    with open(REPORT_FILE, 'w') as f:
        f.write(md)
    print(f"Report saved to {REPORT_FILE}")


if __name__ == '__main__':
    main()
