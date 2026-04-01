#!/usr/bin/env python3
"""
Rebuild ab_results from all archived + current closed trades.
Aggregates all trades per (test_name, variant_id), computes net PnL after fees,
then does a single upsert per variant.

Usage: python3 /tmp/rebuild_ab_results.py
"""
import psycopg2, json, sys
from decimal import Decimal

PG = dict(host='/var/run/postgresql', dbname='brain', user='postgres', password='postgres')

def to_f(v):
    """Convert PostgreSQL Decimal/None to float."""
    return float(v) if v is not None else 0.0

def parse_experiment(exp):
    """Extract list of (test_name, variant_id) from experiment JSON/string."""
    if not exp:
        return []
    if isinstance(exp, dict):
        exp_str = exp.get('experiment', '')
    elif isinstance(exp, str) and exp.startswith('{'):
        try:
            exp_str = json.loads(exp).get('experiment', '')
        except Exception:
            return []
    else:
        exp_str = str(exp)

    result = []
    for part in exp_str.split('|'):
        if ':' in part:
            test, variant = part.split(':', 1)
            result.append((test.strip(), variant.strip()))
    return result

def get_net_pnl(pnl_usdt, fees_json):
    """Compute net PnL after fees."""
    if fees_json:
        try:
            fees = json.loads(fees_json) if isinstance(fees_json, str) else fees_json
            net = fees.get('net_pnl')
            if net is not None:
                return float(net)
        except Exception:
            pass
    return to_f(pnl_usdt)  # fallback: use raw

def main():
    conn = psycopg2.connect(**PG)
    conn.autocommit = True
    cur = conn.cursor()

    # Snapshot before
    cur.execute("SELECT COUNT(*), COALESCE(SUM(wins),0), COALESCE(SUM(losses),0) FROM ab_results")
    before = cur.fetchone()
    print(f"Before: {before[0]} variants | {before[1]} wins | {before[2]} losses")

    # Collect all trades
    archives = [
        'trades_archive_20260331', 'trades_archive_20260331_1622',
        'trades_archive_20260331_1627', 'trades_archive_20260331_1718',
        'trades_archive_20260331_214839', 'trades_archive_20260331_2224',
    ]

    all_trades = []
    for tbl in archives:
        try:
            cur.execute(f'SELECT id, token, pnl_usdt, pnl_pct, fees, experiment FROM "{tbl}" WHERE experiment IS NOT NULL')
            all_trades.extend([(r, tbl) for r in cur.fetchall()])
        except Exception as e:
            print(f"  SKIP {tbl}: {e}", file=sys.stderr)

    cur.execute('SELECT id, token, pnl_usdt, pnl_pct, fees, experiment FROM trades WHERE status=%s AND experiment IS NOT NULL', ('closed',))
    all_trades.extend([(r, 'live') for r in cur.fetchall()])
    print(f"Loaded {len(all_trades)} trades with experiment data")

    # Aggregate per (test_name, variant_id)
    stats = {}  # key -> {trades, wins, losses, total_pnl_pct, total_pnl_usdt}

    for (row, src) in all_trades:
        trade_id, token, pnl_usdt, pnl_pct, fees_json, experiment = row
        pnl_usd = to_f(pnl_usdt)
        pnl_pct_f = to_f(pnl_pct)
        net = get_net_pnl(pnl_usdt, fees_json)
        is_win = net > 0

        for test_name, variant_id in parse_experiment(experiment):
            key = (test_name, variant_id)
            if key not in stats:
                stats[key] = dict(trades=0, wins=0, losses=0, total_pnl_pct=0.0, total_pnl_usdt=0.0)
            s = stats[key]
            s['trades'] += 1
            s['total_pnl_pct'] += pnl_pct_f
            s['total_pnl_usdt'] += net
            if is_win:
                s['wins'] += 1
            else:
                s['losses'] += 1

    print(f"Aggregated into {len(stats)} variants")

    # Clear and rebuild ab_results
    cur.execute("DELETE FROM ab_results")

    # Upsert each variant as a single aggregated row
    cur2 = conn.cursor()
    for (test_name, variant_id), s in sorted(stats.items()):
        n = s['trades']
        w = s['wins']
        l = s['losses']
        pnl_pct_total = s['total_pnl_pct']
        pnl_usd_total = s['total_pnl_usdt']
        wr = (w / n * 100) if n > 0 else 0.0
        avg_win_pct = (pnl_pct_total / w) if w > 0 else 0.0
        avg_loss_pct = (pnl_pct_total / l) if l > 0 else 0.0
        # avg_r: avg win - avg loss (a rough Sharpe-like)
        avg_r = avg_win_pct + avg_loss_pct

        cur2.execute("""
            INSERT INTO ab_results
                (test_name, variant_id, trades, wins, losses,
                 total_pnl_pct, total_pnl_usdt,
                 avg_win_pct, avg_loss_pct, win_rate_pct, avg_r, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (test_name, variant_id) DO UPDATE SET
                trades          = EXCLUDED.trades,
                wins            = EXCLUDED.wins,
                losses          = EXCLUDED.losses,
                total_pnl_pct   = EXCLUDED.total_pnl_pct,
                total_pnl_usdt  = EXCLUDED.total_pnl_usdt,
                avg_win_pct     = EXCLUDED.avg_win_pct,
                avg_loss_pct    = EXCLUDED.avg_loss_pct,
                win_rate_pct    = EXCLUDED.win_rate_pct,
                avg_r           = EXCLUDED.avg_r,
                updated_at      = NOW()
        """, (test_name, variant_id, n, w, l,
              pnl_pct_total, pnl_usd_total,
              avg_win_pct, avg_loss_pct, wr, avg_r))

    conn.close()

    # Final report
    conn2 = psycopg2.connect(**PG)
    conn2.autocommit = True
    cur2 = conn2.cursor()
    print(f"\nAfter: {len(stats)} variants rebuilt")
    print(f"\n{'─'*95}")
    print(f"  {'TEST':30s} {'VARIANT':18s} {'N':4s} {'W':4s} {'L':4s} {'WR%':5s} {'AVG_PNL':9s} {'TOTAL_PNL':11s}")
    print(f"{'─'*95}")

    cur2.execute("""
        SELECT test_name, variant_id, trades, wins, losses, win_rate_pct, total_pnl_pct
        FROM ab_results
        ORDER BY win_rate_pct DESC, total_pnl_pct DESC
    """)
    for r in cur2.fetchall():
        test, variant, n, w, l, wr, pnl = r
        print(f"  {test:30s} {variant:18s} {n:4d} {w:4d} {l:4d} {wr:5.1f} {pnl:+.2f}%")

    print(f"{'─'*95}")
    print(f"\nBy test:")
    cur2.execute("""
        SELECT test_name,
               COUNT(*) as variants,
               SUM(trades) as trades,
               SUM(wins) as wins,
               AVG(win_rate_pct) as avg_wr,
               SUM(total_pnl_pct) as total_pnl
        FROM ab_results
        GROUP BY test_name
        ORDER BY avg_wr DESC
    """)
    for r in cur2.fetchall():
        test, vcnt, n, w, wr, pnl = r
        overall_wr = (w / n * 100) if n > 0 else 0
        print(f"  {test:30s} {vcnt:3d} var | {n:4d} trades | {w:3d} wins | {overall_wr:5.1f}% WR | {pnl:+.2f}% total")

    conn2.close()

if __name__ == '__main__':
    main()
